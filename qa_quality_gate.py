"""ANAC Portfolio | Data Quality Gate (offline, read-only).

Put in project root and run: python qa_quality_gate.py
Checks CSV baseline, state/parts, DuckDB dimension/facts/metadata and reconciliation.
Never changes source CSVs, ETL state, DuckDB or dashboard.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

MARKETS = {'Noi dia': ('domestic', 'BRL'), 'Quoc te': ('international', 'USD')}
MONTHLY_NAME = 'tong_hop_theo_thang_2024.csv'
OUTPUTS = [MONTHLY_NAME, 'top100_noi_dia_toa_do.csv',
           'top100_quoc_te_toa_do.csv', 'xu_huong_diem_den_2024.csv']
PART_NAME = re.compile(r'(domestic|international)_(20\d\d)-(0[1-9]|1[0-2])\.csv\Z')
MONTH_NAME = re.compile(r'20\d\d-(0[1-9]|1[0-2])\Z')
REQUIRED_PART = {'THANG', 'LOAI', 'ORIGEM', 'DESTINO', 'ASSENTOS', 'GIA_NHAN_GHE', 'GHE_CO_GIA'}
MONTHLY_COLUMNS = {'THANG', 'LOAI_CHUYEN_BAY', 'SO_GHE_BAN', 'GIA_BINH_QUAN',
                   'SO_BAN_GHI', 'TIEN_TE', 'BIEN_DONG_GIA_PCT'}


def read_csv_auto(path: Path) -> pd.DataFrame:
    """Current ANAC aggregate exports are comma CSV; legacy baseline may be semicolon CSV."""
    with Path(path).open('r', encoding='utf-8-sig') as f:
        header = f.readline()
    sep = ';' if header.count(';') > header.count(',') else ','
    return pd.read_csv(path, sep=sep, encoding='utf-8-sig', low_memory=False)


def close_numbers(a, b, *, absolute=1e-5, relative=1e-10) -> bool:
    """Compare parsed numbers, with actual missingness preserved (NaN == NaN here)."""
    try:
        aa = float(a)
        bb = float(b)
    except (TypeError, ValueError, OverflowError):
        return pd.isna(a) and pd.isna(b)
    if math.isnan(aa) or math.isnan(bb):
        return math.isnan(aa) and math.isnan(bb)
    return math.isfinite(aa) and math.isfinite(bb) and math.isclose(
        aa, bb, rel_tol=relative, abs_tol=absolute
    )


@dataclass
class Reporter:
    ok: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def check(self, condition: bool, message: str, detail: str = '') -> bool:
        if bool(condition):
            self.ok += 1
            print('PASS:', message)
            return True
        problem = message + (': ' + detail if detail else '')
        self.errors.append(problem)
        print('FAIL:', problem)
        return False

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print('WARN:', message)

    def summary(self) -> int:
        print('\n=== KET QUA DATA QUALITY ===')
        print(f'PASS: {self.ok} | FAIL: {len(self.errors)} | WARN: {len(self.warnings)}')
        if self.errors:
            print('Chua dat quality gate. Khong dua du lieu nay len dashboard / deploy.')
            return 1
        print('Quality gate dat voi cac quy tac da kiem tra (khong chung minh moi gia tri deu dung).')
        return 0


def valid_positive_integer_column(s: pd.Series) -> bool:
    x = pd.to_numeric(s, errors='coerce')
    return bool((x.notna() & (x > 0) & (x % 1 == 0)).all())


def audit_monthly(df: pd.DataFrame, report: Reporter, *, require_full_2024=True) -> dict:
    if not report.check(MONTHLY_COLUMNS <= set(df.columns), 'CSV monthly co du 7 cot',
                        ', '.join(sorted(MONTHLY_COLUMNS - set(df.columns)))):
        return {}
    month = df['THANG'].astype('string').str.strip()
    market = df['LOAI_CHUYEN_BAY'].astype('string').str.strip()
    valid_date = month.str.fullmatch(MONTH_NAME.pattern).fillna(False).all()
    report.check(valid_date, 'THANG dung YYYY-MM')
    report.check(market.isin(MARKETS).all(), 'Thi truong chi co Noi dia / Quoc te')
    report.check(not df.assign(_mon=month, _market=market).duplicated(['_mon', '_market']).any(),
                 'Khong trung khoa thang + thi truong')
    report.check(valid_positive_integer_column(df['SO_GHE_BAN']), 'SO_GHE_BAN nguyen duong, khong thieu')
    avg = pd.to_numeric(df['GIA_BINH_QUAN'], errors='coerce')
    report.check(bool((avg.notna() & (avg > 0) & avg.map(math.isfinite)).all()),
                 'GIA_BINH_QUAN duong va huu han')
    report.check(valid_positive_integer_column(df['SO_BAN_GHI']),
                 'SO_BAN_GHI la so nguyen duong cho moi ky')
    expected_ccy = market.map(lambda x: MARKETS.get(x, (None, None))[1])
    report.check(df['TIEN_TE'].astype('string').str.strip().eq(expected_ccy).fillna(False).all(),
                 'Tien te dong nhat: domestic BRL, international USD')
    change = pd.to_numeric(df['BIEN_DONG_GIA_PCT'], errors='coerce')
    observed_bad = 0
    if valid_date and market.isin(MARKETS).all():
        # A 2026 missing month must NOT produce artificial MoM rate from earlier month.
        lookup = {(m, k): float(v) for m, k, v in zip(month, market, avg) if pd.notna(v)}
        for m, k, v, pct in zip(month, market, avg, change):
            if m.startswith('2024'):
                continue  # Legacy 2024 retained exactly, not recomputed.
            previous = str(pd.Period(m, freq='M') - 1)
            if (previous, k) in lookup:
                target = (float(v) / lookup[(previous, k)] - 1) * 100
                if not close_numbers(pct, target, absolute=1e-4):
                    observed_bad += 1
            elif pd.notna(pct):
                observed_bad += 1
        report.check(observed_bad == 0, 'MoM dung ky thang lien ke (khong noi qua thang thieu)',
                     f'{observed_bad} ky khong khop')
        for k in MARKETS:
            observed = set(month[(market == k) & month.str.startswith('2024')])
            expected = {f'2024-{i:02d}' for i in range(1, 13)}
            if require_full_2024:
                report.check(observed == expected, f'2024 {k}: du 12 thang',
                             f'thieu={sorted(expected - observed)}, du={sorted(observed - expected)}')
        for k, grp in df.groupby(market):
            periods = sorted(set(grp['THANG'].astype(str)))
            if len(periods) >= 2:
                seq = pd.period_range(periods[0], periods[-1], freq='M')
                missing = [str(m) for m in seq if str(m) not in periods]
                if missing:
                    report.warn(f'{k}: thieu ky tren dong thoi gian: {", ".join(missing[:15])}')
    return {(m, MARKETS[k][0]): row for m, k, (_, row) in
            zip(month.astype(str), market.astype(str), df.iterrows()) if k in MARKETS}


def audit_baseline(base: pd.DataFrame, cur: pd.DataFrame, report: Reporter) -> None:
    keys = ['THANG', 'LOAI_CHUYEN_BAY']
    if not report.check(set(base.columns) == set(cur.columns),
                        'Baseline va CSV co cung schema',
                        f'baseline={list(base.columns)}, current={list(cur.columns)}'):
        return
    old = base.assign(THANG=base['THANG'].astype(str).str.strip()).set_index(keys)
    recent = cur.loc[cur['THANG'].astype(str).str.startswith('2024')].copy()
    recent['THANG'] = recent['THANG'].astype(str).str.strip()
    new = recent.set_index(keys)
    if not report.check(len(old) == 24 and old.index.is_unique and new.index.is_unique
                        and set(old.index) == set(new.index),
                        'Bao toan 24 khoa baseline 2024'):
        return
    bad = []
    for idx in old.index:
        for c in old.columns:
            x, y = old.loc[idx, c], new.loc[idx, c]
            if c in {'SO_GHE_BAN', 'GIA_BINH_QUAN', 'SO_BAN_GHI', 'BIEN_DONG_GIA_PCT'}:
                equal = close_numbers(x, y)
            else:
                equal = (pd.isna(x) and pd.isna(y)) or (str(x).strip() == str(y).strip())
            if not equal:
                bad.append(f'{idx} {c}: {x!s} != {y!s}')
    report.check(not bad, 'Gia tri baseline 2024 duoc giu nguyen',
                 '; '.join(bad[:4]))


def audit_part(path: Path, state: dict, report: Reporter) -> dict | None:
    match = PART_NAME.fullmatch(path.name)
    if not match:
        report.warn(f'Bo qua file khong dung mau domestic_YYYY-MM.csv: {path.name}')
        return None
    market, year, month = match.groups()
    period = f'{year}-{month}'
    key = f'{market}_{period}'
    meta = state.get(key)
    if not report.check(isinstance(meta, dict), f'{key}: co trong state.json'):
        return None
    df = read_csv_auto(path)
    if not report.check(REQUIRED_PART <= set(df.columns), f'{key}: du cot ETL',
                        ', '.join(sorted(REQUIRED_PART - set(df.columns)))):
        return None
    report.check(df['THANG'].astype(str).str.strip().eq(period).all(), f'{key}: thang dung file')
    label = 'Nội địa' if market == 'domestic' else 'Quốc tế'
    report.check(df['LOAI'].astype(str).str.strip().eq(label).all(), f'{key}: loai thi truong dung')
    codes = (df['ORIGEM'].astype('string').str.fullmatch('[A-Z0-9]{4}').fillna(False) &
             df['DESTINO'].astype('string').str.fullmatch('[A-Z0-9]{4}').fillna(False))
    report.check(bool(codes.all()), f'{key}: ma san bay hop le')
    report.check(not df.duplicated(['THANG', 'LOAI', 'ORIGEM', 'DESTINO']).any(),
                 f'{key}: khong trung khoa tuyen')
    seats = pd.to_numeric(df['ASSENTOS'], errors='coerce')
    priced = pd.to_numeric(df['GHE_CO_GIA'], errors='coerce')
    fare = pd.to_numeric(df['GIA_NHAN_GHE'], errors='coerce')
    valid = (seats.notna() & priced.notna() & fare.notna() &
             (seats > 0) & (seats % 1 == 0) &
             (priced >= 0) & (priced % 1 == 0) & (priced <= seats) &
             (fare >= 0) & fare.map(lambda n: math.isfinite(n) if pd.notna(n) else False) &
             ((priced > 0) | (fare == 0)))
    if not report.check(bool(valid.all()), f'{key}: ghe/gia hop le'):
        return None
    n_seats = int(seats.sum())
    n_priced = int(priced.sum())
    n_fare = float(fare.sum())
    for name, val in (('seats', n_seats), ('fare_seats', n_priced), ('fare_weight', n_fare)):
        report.check(close_numbers(meta.get(name), val, absolute=0.05),
                     f'{key}: part khop state.{name}',
                     f'part={val}, state={meta.get(name)}')
    raw_rows = meta.get('rows')
    try:
        rows = int(raw_rows)
        valid_rows = not isinstance(raw_rows, bool) and rows > 0 and float(raw_rows) == rows
    except (TypeError, ValueError, OverflowError):
        valid_rows = False
        rows = None
    report.check(valid_rows, f'{key}: rows co so ban ghi hop le', str(raw_rows))
    return {'market': market, 'period': period, 'month_key': int(year+month),
            'seats': n_seats, 'priced': n_priced, 'fare_sum': n_fare,
            'rows': rows, 'route_count': len(df), 'file': path.name}


def audit_dw(db: Path, month_map: dict, part_stats: dict, report: Reporter) -> None:
    try:
        import duckdb
    except ImportError as e:
        report.check(False, 'Da cai dat DuckDB', str(e))
        return
    if not report.check(db.is_file(), 'File DuckDB ton tai', str(db)):
        return
    con = duckdb.connect(str(db), read_only=True)
    try:
        tables = {r[0] for r in con.execute('SHOW TABLES').fetchall()}
        required = {'fact_airfare_route_monthly', 'dim_month', 'dim_market',
                    'dim_airport', 'etl_month_metadata', 'vw_monthly_kpi'}
        if not report.check(required <= tables, 'Du bang va view DuckDB',
                            str(required - tables)):
            return
        checks = {
            'Fact khong trung khoa grain': '''SELECT COUNT(*) FROM (
                SELECT month_key, market_key, origin_airport_code, destination_airport_code
                FROM fact_airfare_route_monthly GROUP BY 1,2,3,4 HAVING COUNT(*)>1) x''',
            'Fact ghe va gia hop le': '''SELECT COUNT(*) FROM fact_airfare_route_monthly
                WHERE total_seats <= 0 OR priced_seats < 0 OR priced_seats>total_seats
                OR fare_weighted_sum < 0 OR NOT isfinite(fare_weighted_sum)
                OR (priced_seats=0 AND fare_weighted_sum <> 0)''',
            'Fact toan ven FK month': '''SELECT COUNT(*) FROM fact_airfare_route_monthly f
                LEFT JOIN dim_month d ON f.month_key=d.month_key WHERE d.month_key IS NULL''',
            'Fact toan ven FK market': '''SELECT COUNT(*) FROM fact_airfare_route_monthly f
                LEFT JOIN dim_market m ON f.market_key=m.market_key WHERE m.market_key IS NULL''',
            'Fact toan ven FK san bay di': '''SELECT COUNT(*) FROM fact_airfare_route_monthly f
                LEFT JOIN dim_airport a ON f.origin_airport_code=a.airport_code
                WHERE a.airport_code IS NULL''',
            'Fact toan ven FK san bay den': '''SELECT COUNT(*) FROM fact_airfare_route_monthly f
                LEFT JOIN dim_airport a ON f.destination_airport_code=a.airport_code
                WHERE a.airport_code IS NULL''',
            'Dim_month khong sai thang/quy': '''SELECT COUNT(*) FROM dim_month
                WHERE sale_month NOT BETWEEN 1 AND 12 OR sale_quarter <> CEIL(sale_month/3.0)
                OR month_key <> sale_year * 100 + sale_month''',
            'View KPI khong trung thang + market': '''SELECT COUNT(*) FROM (
                SELECT month_key, market_code FROM vw_monthly_kpi
                GROUP BY 1,2 HAVING COUNT(*)>1) x''',
            'Metadata khong thieu source_record_count': '''SELECT COUNT(*) FROM etl_month_metadata
                WHERE source_record_count IS NULL OR source_record_count<=0''',
        }
        for label, sql in checks.items():
            n = int(con.execute(sql).fetchone()[0])
            report.check(n == 0, label, f'{n} dong vi pham')
        markets = dict(con.execute('SELECT market_code, currency_code FROM dim_market').fetchall())
        report.check(markets.get('domestic') == 'BRL' and markets.get('international') == 'USD',
                     'Dim_market BRL va USD dung')
        rows = con.execute('''SELECT month_key, market_code, currency_code, total_seats,
                                   priced_seats, avg_fare, source_record_count, price_coverage_pct
                              FROM vw_monthly_kpi''').fetchall()
        db_months = {}
        for mk, market, ccy, seats, priced, avg, nrows, coverage in rows:
            period = f'{mk//100:04d}-{mk%100:02d}'
            db_months[(period, market)] = (mk, ccy, seats, priced, avg, nrows, coverage)
        report.check(len(db_months) == len(rows) == len(month_map),
                     'So ky KPI khop CSV monthly',
                     f'db={len(rows)}, csv={len(month_map)}')
        wrong = []
        for key, series in month_map.items():
            entry = db_months.get(key)
            if not entry:
                wrong.append(f'{key}: thieu trong DuckDB')
                continue
            mk, ccy, seats, priced, avg, nrows, coverage = entry
            for name, expected, got, tol in (
                ('currency', series['TIEN_TE'], ccy, 0),
                ('seats', series['SO_GHE_BAN'], seats, 0),
                ('avg_fare', series['GIA_BINH_QUAN'], avg, 0.01),
                ('rows', series['SO_BAN_GHI'], nrows, 0),
            ):
                equal = (str(expected) == str(got)) if name == 'currency' else close_numbers(
                    expected, got, absolute=tol, relative=1e-9)
                if not equal:
                    wrong.append(f'{key} {name}: csv={expected}, dw={got}')
            if not close_numbers(coverage, float(priced)/float(seats)*100, absolute=0.0001):
                wrong.append(f'{key}: price_coverage_pct khong khop')
        report.check(not wrong, 'CSV vs DuckDB: ghe, gia, rows, tien te (toan bo ky)',
                     f'{len(wrong)} sai lech; ' + '; '.join(wrong[:5]))
        metadata_rows = con.execute('''SELECT e.month_key, m.market_code,
                    e.source_record_count, e.source_file
                    FROM etl_month_metadata e
                    JOIN dim_market m ON m.market_key=e.market_key''').fetchall()
        meta_index = {(mk, market): (count, filename) for mk, market, count, filename in metadata_rows}
        report.check(len(metadata_rows) == len(part_stats), 'Metadata khop so file part',
                     f'db={len(metadata_rows)}, file={len(part_stats)}')
        meta_bad = []
        for key, info in part_stats.items():
            value = meta_index.get((info['month_key'], info['market']))
            if not value or value != (info['rows'], info['file']):
                meta_bad.append(f'{key}: db={value}, part={(info["rows"], info["file"])}')
        report.check(not meta_bad, 'Metadata DuckDB khop state va file part',
                     '; '.join(meta_bad[:5]))
        fact_months = con.execute('''SELECT f.month_key, m.market_code,
                         SUM(f.total_seats), SUM(f.priced_seats), SUM(f.fare_weighted_sum), COUNT(*)
                    FROM fact_airfare_route_monthly f
                    JOIN dim_market m ON f.market_key=m.market_key
                    GROUP BY 1,2''').fetchall()
        fact_map = {(int(mk), market): (seats, priced, fare, nroute)
                    for mk, market, seats, priced, fare, nroute in fact_months}
        bad_parts = []
        for key, info in part_stats.items():
            actual = fact_map.get((info['month_key'], info['market']))
            if actual is None:
                bad_parts.append(f'{key}: khong co Fact')
                continue
            for field, a, b, tol in zip(('seats','priced','fare','routes'),
                     (info['seats'], info['priced'], info['fare_sum'], info['route_count']),
                     actual, (0, 0, 0.1, 0)):
                if not close_numbers(a, b, absolute=tol):
                    bad_parts.append(f'{key} {field}: part={a}, dw={b}')
        report.check(not bad_parts, 'ETL parts vs Fact DuckDB: ghe/gia/so tuyen (32 ky)',
                     f'{len(bad_parts)} sai lech; ' + '; '.join(bad_parts[:5]))
        geo_null = con.execute('''SELECT COUNT(*) FROM fact_airfare_route_monthly f
            JOIN dim_airport a ON a.airport_code=f.origin_airport_code
            JOIN dim_airport b ON b.airport_code=f.destination_airport_code
            WHERE a.latitude IS NULL OR b.latitude IS NULL
                  OR a.longitude IS NULL OR b.longitude IS NULL''').fetchone()[0]
        if geo_null:
            report.warn(f'{geo_null} dong Fact co san bay thieu toa do; can loc khi ve map')
    finally:
        con.close()


def run(project: Path) -> int:
    report = Reporter()
    data = project / 'DuLieu_DaXuLy'
    baseline = data / '_tu_dong' / 'baseline_2024'
    parts = data / '_tu_dong' / 'parts'
    state_file = data / '_tu_dong' / 'state.json'
    db = project / 'data_warehouse' / 'anac.duckdb'
    print('=== ANAC DATA QUALITY & TESTING | READ-ONLY ===')
    print('Project:', project)
    print('\n[1] Kiem tra du lieu CSV va baseline')
    missing_files = [str(data / n) for n in OUTPUTS if not (data / n).is_file()]
    if not report.check(not missing_files, '4 CSV xuat ban ton tai', ', '.join(missing_files)):
        return report.summary()
    if not report.check((baseline / MONTHLY_NAME).is_file(), 'Baseline monthly 2024 ton tai'):
        return report.summary()
    monthly = read_csv_auto(data / MONTHLY_NAME)
    original = read_csv_auto(baseline / MONTHLY_NAME)
    month_map = audit_monthly(monthly, report)
    audit_baseline(original, monthly, report)
    # Existing dashboard geo tables are included in the quality gate.
    for filename in OUTPUTS[1:3]:
        t = read_csv_auto(data / filename)
        required = {'ORIGEM','DESTINO','ASSENTOS','LAT_DI','LON_DI','LAT_DEN','LON_DEN'}
        if not report.check(required <= set(t.columns), f'{filename}: du cot top tuyen'):
            continue
        report.check(valid_positive_integer_column(t['ASSENTOS']),
                     f'{filename}: so ghe nguyen duong')
        coords = pd.DataFrame({c: pd.to_numeric(t[c], errors='coerce')
                               for c in ('LAT_DI','LON_DI','LAT_DEN','LON_DEN')})
        valid = (coords['LAT_DI'].between(-90,90) & coords['LAT_DEN'].between(-90,90)
                 & coords['LON_DI'].between(-180,180) & coords['LON_DEN'].between(-180,180))
        report.check(bool(valid.all()), f'{filename}: toa do hop le',
                     f'{int((~valid).sum())} dong loi')
        if 'NAM' in t:
            report.check(not t.duplicated(['NAM','ORIGEM','DESTINO']).any(),
                         f'{filename}: khong trung khoa nam/tuyen')
    print('\n[2] Kiem tra state.json va tung file ETL parts')
    if not report.check(state_file.is_file(), 'state.json ton tai'):
        return report.summary()
    if not report.check(parts.is_dir(), 'Thu muc parts ton tai'):
        return report.summary()
    state_json = json.loads(state_file.read_text(encoding='utf-8-sig'))
    state = state_json.get('months', {})
    if not report.check(isinstance(state, dict), 'state.months dung dinh dang object'):
        return report.summary()
    part_paths = [p for p in sorted(parts.glob('*.csv')) if PART_NAME.fullmatch(p.name)]
    expected_keys = {p.stem for p in part_paths}
    report.check(set(state) == expected_keys, 'state.json va parts dong bo 1-1',
                 f'state_only={sorted(set(state)-expected_keys)[:5]}, part_only={sorted(expected_keys-set(state))[:5]}')
    part_stats = {}
    for i, path in enumerate(part_paths, start=1):
        info = audit_part(path, state, report)
        if info:
            part_stats[path.stem] = info
        if i % 8 == 0 or i == len(part_paths):
            print(f'--- Da kiem tra {i}/{len(part_paths)} parts ---')
    report.check(len(part_stats) == len(part_paths), 'Doc va kiem tra du cac part')
    # Aggregate per-month reconciliation; avoid wrong currency combinations.
    bad_months = []
    for key, info in part_stats.items():
        row = month_map.get((info['period'], info['market']))
        if row is None:
            bad_months.append(key + ': khong co trong CSV monthly')
            continue
        n_fare = info['fare_sum'] / info['priced'] if info['priced'] else None
        for field, value, expected, tol in (
             ('SO_GHE_BAN', row['SO_GHE_BAN'], info['seats'], 0),
             ('GIA_BINH_QUAN', row['GIA_BINH_QUAN'], n_fare, 0.01),
             ('SO_BAN_GHI', row['SO_BAN_GHI'], info['rows'], 0)):
            if not close_numbers(value, expected, absolute=tol):
                bad_months.append(f'{key} {field}: csv={value}, parts={expected}')
    report.check(not bad_months, 'CSV monthly vs state/parts khop 2025+',
                 '; '.join(bad_months[:5]))
    print('\n[3] Kiem tra Data Warehouse DuckDB (read_only=True)')
    try:
        audit_dw(db, month_map, part_stats, report)
    except Exception as exc:
        report.check(False, 'Thuc thi kiem tra DuckDB', str(exc))
    return report.summary()


def main() -> int:
    parser = argparse.ArgumentParser(description='Offline, read-only ANAC quality gate')
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent,
                        help='Thu muc project co DuLieu_DaXuLy va data_warehouse')
    args = parser.parse_args()
    return run(args.project.resolve())


if __name__ == '__main__':
    raise SystemExit(main())
