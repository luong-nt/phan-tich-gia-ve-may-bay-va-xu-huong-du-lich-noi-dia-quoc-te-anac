"""Load ANAC clean 2024 and optional 2025+ monthly parts to DuckDB.

Run from the project folder, e.g.:
 python data_warehouse/load_warehouse.py --clean-dir "C:/.../Dulieusach" --airports "C:/.../DuLieu_SanBay/airports.csv"

Rebuild is deliberate and repeatable; only modifies data_warehouse/anac.duckdb.
"""
import argparse
import json
import re
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def sql_path(path: Path) -> str:
    return "'" + str(path.resolve()).replace("'", "''") + "'"


def load_2024(conn, path: Path, market_key: int) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Khong tim thay file du lieu sach: {path}")
    # Only aggregated records are inserted into warehouse; DuckDB handles file scanning.
    conn.execute(f"""
      INSERT INTO fact_airfare_route_monthly
      (month_key,market_key,origin_airport_code,destination_airport_code,
       total_seats,priced_seats,fare_weighted_sum,source_record_count)
      SELECT CAST(REPLACE(THANG, '-', '') AS INTEGER), {market_key},
             UPPER(TRIM(ORIGEM)), UPPER(TRIM(DESTINO)),
             CAST(SUM(CAST(ASSENTOS AS BIGINT)) AS BIGINT),
             CAST(SUM(CAST(ASSENTOS AS BIGINT)) AS BIGINT),
             SUM(CAST(TARIFA AS DOUBLE) * CAST(ASSENTOS AS DOUBLE)),
             COUNT(*)
      FROM read_csv({sql_path(path)}, delim=';', header=true, all_varchar=true)
      WHERE CAST(ASSENTOS AS BIGINT) > 0 AND CAST(TARIFA AS DOUBLE) > 0
        AND REGEXP_MATCHES(THANG, '^2024-(0[1-9]|1[0-2])$')
        AND NULLIF(TRIM(ORIGEM),'') IS NOT NULL
        AND NULLIF(TRIM(DESTINO),'') IS NOT NULL
      GROUP BY 1, 3, 4;
    """)


def load_parts(conn, parts_dir: Path) -> int:
    count = 0
    if not parts_dir.exists():
        return count
    for path in sorted(parts_dir.glob('*.csv')):
        # The update pipeline names parts domestic_YYYY-MM.csv / international_YYYY-MM.csv.
        if not (path.name.startswith('domestic_') or path.name.startswith('international_')):
            continue
        market_key = 1 if path.name.startswith('domestic_') else 2
        conn.execute(f"""
          INSERT INTO fact_airfare_route_monthly
          (month_key,market_key,origin_airport_code,destination_airport_code,
           total_seats,priced_seats,fare_weighted_sum,source_record_count)
          SELECT CAST(REPLACE(THANG, '-', '') AS INTEGER), {market_key},
                 UPPER(TRIM(ORIGEM)), UPPER(TRIM(DESTINO)),
                 CAST(SUM(CAST(ASSENTOS AS BIGINT)) AS BIGINT),
                 CAST(SUM(CAST(GHE_CO_GIA AS BIGINT)) AS BIGINT),
                 SUM(CAST(GIA_NHAN_GHE AS DOUBLE)),
                 NULL
          FROM read_csv({sql_path(path)}, header=true, all_varchar=true)
          WHERE CAST(SUBSTR(THANG,1,4) AS INTEGER) >= 2025
          GROUP BY 1,3,4;
        """)
        count += 1
    return count


def load_month_metadata(conn, parts_dir: Path, state_file: Path, part_count: int) -> None:
    """Keep raw-source record counts at month/market grain, never at route grain."""
    if not state_file.is_file():
        raise FileNotFoundError(f"Thieu state.json cho du lieu 2025+: {state_file}")
    state = json.loads(state_file.read_text(encoding='utf-8-sig'))
    months = state.get('months', {})
    if not isinstance(months, dict):
        raise ValueError("state.json: 'months' phai la object")
    conn.execute('''
        CREATE TABLE etl_month_metadata (
            month_key INTEGER NOT NULL REFERENCES dim_month(month_key),
            market_key INTEGER NOT NULL REFERENCES dim_market(market_key),
            source_record_count BIGINT CHECK (source_record_count IS NULL OR source_record_count >= 0),
            source_file VARCHAR NOT NULL,
            PRIMARY KEY (month_key, market_key)
        )
    ''')
    loaded = 0
    for path in sorted(parts_dir.glob('*.csv')):
        match = re.fullmatch(r'(domestic|international)_(\d{4})-(\d{2})\.csv', path.name)
        if not match:
            continue
        market, year, month = match.groups()
        key = f'{market}_{year}-{month}'
        meta = months.get(key)
        if not isinstance(meta, dict):
            raise ValueError(f"Thieu thong tin ky {key} trong state.json")
        # Some historical ETL states contain rows=null. Route-level aggregates
        # cannot recover original source row counts, so preserve SQL NULL.
        raw_rows = meta.get('rows')
        if raw_rows is None or raw_rows == '':
            rows = None
        else:
            if isinstance(raw_rows, bool):
                raise ValueError(f"So ban ghi nguon khong hop le cho {key}: {raw_rows}")
            try:
                rows = int(raw_rows)
            except (ValueError, TypeError, OverflowError) as exc:
                raise ValueError(f"So ban ghi nguon khong hop le cho {key}: {raw_rows}") from exc
            if rows <= 0 or str(raw_rows).strip() not in (str(rows), f'{rows}.0'):
                raise ValueError(f"So ban ghi nguon khong hop le cho {key}: {raw_rows}")
        month_key = int(year + month)
        market_key = 1 if market == 'domestic' else 2
        conn.execute('''
            INSERT INTO etl_month_metadata
            (month_key, market_key, source_record_count, source_file)
            VALUES (?, ?, ?, ?)
        ''', [month_key, market_key, rows, path.name])
        loaded += 1
    if loaded != part_count:
        raise ValueError(f"So metadata ({loaded}) khac so file parts ({part_count})")


def update_monthly_kpi_view(conn) -> None:
    """2024 from detailed clean data; 2025+ from ETL metadata (nullable)."""
    conn.execute('''
        CREATE OR REPLACE VIEW vw_monthly_kpi AS
        WITH fact_kpi AS (
            SELECT f.month_key, f.market_key,
                   SUM(f.total_seats) AS total_seats,
                   SUM(f.priced_seats) AS priced_seats,
                   SUM(f.fare_weighted_sum) AS fare_weighted_sum,
                   SUM(f.source_record_count) AS fact_record_count
            FROM fact_airfare_route_monthly f
            GROUP BY f.month_key, f.market_key
        )
        SELECT f.month_key, d.sale_year, d.sale_month, d.sale_quarter,
               m.market_code, m.market_name, m.currency_code,
               f.total_seats, f.priced_seats,
               f.fare_weighted_sum / NULLIF(f.priced_seats, 0) AS avg_fare,
               f.priced_seats * 100.0 / NULLIF(f.total_seats, 0) AS price_coverage_pct,
               CASE WHEN d.sale_year = 2024 THEN f.fact_record_count
                    ELSE meta.source_record_count END AS source_record_count
        FROM fact_kpi f
        JOIN dim_month d ON d.month_key=f.month_key
        JOIN dim_market m ON m.market_key=f.market_key
        LEFT JOIN etl_month_metadata meta
          ON meta.month_key=f.month_key AND meta.market_key=f.market_key
    ''')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clean-dir', type=Path, required=True,
                        help='Folder containing noi_dia_sach_2024.csv and quoc_te_sach_2024.csv')
    parser.add_argument('--airports', type=Path, required=True, help='OurAirports airports.csv')
    parser.add_argument('--parts-dir', type=Path, help='Optional DuLieu_DaXuLy/_tu_dong/parts')
    parser.add_argument('--state-file', type=Path, help='Optional path to _tu_dong/state.json')
    args = parser.parse_args()
    if not args.airports.is_file():
        parser.error(f'File san bay khong ton tai: {args.airports}')
    HERE.mkdir(exist_ok=True)
    db_path = HERE / 'anac.duckdb'
    # Temp database first; do not overwrite last successful warehouse on failure.
    temp_db = HERE / 'anac_build.duckdb'
    for ext in ('', '.wal'):
        (HERE / ('anac_build.duckdb' + ext)).unlink(missing_ok=True)
    conn = duckdb.connect(str(temp_db))
    try:
        conn.execute((HERE / 'schema.sql').read_text(encoding='utf-8'))
        # Insert airport dimension codes known in the airport reference file.
        conn.execute(f"""
          INSERT INTO dim_airport
          SELECT UPPER(TRIM(ident)), ANY_VALUE(name), ANY_VALUE(municipality),
                 ANY_VALUE(iso_country),
                 TRY_CAST(ANY_VALUE(latitude_deg) AS DOUBLE),
                 TRY_CAST(ANY_VALUE(longitude_deg) AS DOUBLE)
          FROM read_csv({sql_path(args.airports)}, header=true, all_varchar=true)
          WHERE NULLIF(TRIM(ident),'') IS NOT NULL
          GROUP BY 1;
        """)
        # Stage facts first: foreign-key constraints require dimension keys preloaded.
        # Read route codes and months from each source (streamed by DuckDB).
        source_specs = [
            (args.clean_dir / 'noi_dia_sach_2024.csv', 'clean'),
            (args.clean_dir / 'quoc_te_sach_2024.csv', 'clean'),
        ]
        for path, kind in source_specs:
            if not path.exists():
                raise FileNotFoundError(path)
        parts = sorted(args.parts_dir.glob('*.csv')) if args.parts_dir and args.parts_dir.exists() else []
        parts = [p for p in parts if p.name.startswith(('domestic_', 'international_'))]
        queries = []
        for path, _ in source_specs:
            queries.append(f"SELECT THANG AS period, ORIGEM AS origin, DESTINO AS dest FROM read_csv({sql_path(path)}, delim=';', header=true, all_varchar=true)")
        for path in parts:
            queries.append(f"SELECT THANG AS period, ORIGEM AS origin, DESTINO AS dest FROM read_csv({sql_path(path)}, header=true, all_varchar=true)")
        union = ' UNION ALL '.join(queries)
        conn.execute(f"CREATE TEMP TABLE source_keys AS SELECT * FROM ({union})")
        conn.execute("""
          INSERT INTO dim_month
          SELECT DISTINCT CAST(REPLACE(period, '-', '') AS INTEGER),
                 CAST(SUBSTR(period,1,4) AS INTEGER),
                 CAST(SUBSTR(period,6,2) AS INTEGER),
                 CAST(CEIL(CAST(SUBSTR(period,6,2) AS INTEGER)/3.0) AS INTEGER)
          FROM source_keys WHERE REGEXP_MATCHES(period,'^[0-9]{4}-(0[1-9]|1[0-2])$')
        """)
        conn.execute("""
          INSERT INTO dim_airport(airport_code)
          SELECT DISTINCT code FROM (
            SELECT UPPER(TRIM(origin)) AS code FROM source_keys
            UNION ALL SELECT UPPER(TRIM(dest)) AS code FROM source_keys
          ) WHERE code IS NOT NULL AND code <> ''
          ON CONFLICT (airport_code) DO NOTHING
        """)
        conn.execute('DROP TABLE source_keys')
        load_2024(conn, source_specs[0][0], 1)
        load_2024(conn, source_specs[1][0], 2)
        n_parts = load_parts(conn, args.parts_dir) if args.parts_dir else 0
        if n_parts:
            state_file = args.state_file or (args.parts_dir.parent / 'state.json')
            load_month_metadata(conn, args.parts_dir, state_file, n_parts)
            update_monthly_kpi_view(conn)
        # Quality gate: no duplicate grain, no negative fares, no unpriced > total.
        invalid = conn.execute('''SELECT COUNT(*) FROM fact_airfare_route_monthly
          WHERE total_seats <= 0 OR priced_seats <= 0
          OR priced_seats > total_seats OR fare_weighted_sum < 0''').fetchone()[0]
        if invalid:
            raise ValueError(f'{invalid} fact records failed quality checks')
        print('Dim_month:', conn.execute('SELECT COUNT(*) FROM dim_month').fetchone()[0])
        print('Dim_airport:', conn.execute('SELECT COUNT(*) FROM dim_airport').fetchone()[0])
        print('Fact routes/month:', conn.execute('SELECT COUNT(*) FROM fact_airfare_route_monthly').fetchone()[0])
        print('Monthly KPI rows:', conn.execute('SELECT COUNT(*) FROM vw_monthly_kpi').fetchone()[0])
        if n_parts:
            n_meta, n_known = conn.execute("""
                SELECT COUNT(*), COUNT(source_record_count)
                FROM etl_month_metadata
            """).fetchone()
            print('ETL metadata rows:', n_meta)
            print('Months with known source record counts:', n_known)
            if n_known < n_meta:
                missing_periods = conn.execute("""
                    SELECT m.market_code || '_' ||
                           SUBSTR(CAST(e.month_key AS VARCHAR), 1, 4) || '-' ||
                           SUBSTR(CAST(e.month_key AS VARCHAR), 5, 2)
                    FROM etl_month_metadata e
                    JOIN dim_market m ON e.market_key = m.market_key
                    WHERE e.source_record_count IS NULL
                    ORDER BY e.month_key, m.market_code
                """).fetchall()
                print('CANH BAO: Chua co so ban ghi nguon cho', n_meta - n_known, 'thang; giu NULL, khong uoc doan.')
                print('Thang thieu:', ', '.join(x[0] for x in missing_periods))
        print('Update part files:', n_parts)
    except Exception:
        conn.close()
        temp_db.unlink(missing_ok=True)
        raise
    conn.close()
    temp_db.replace(db_path)
    print('OK warehouse:', db_path)


if __name__ == '__main__':
    main()
