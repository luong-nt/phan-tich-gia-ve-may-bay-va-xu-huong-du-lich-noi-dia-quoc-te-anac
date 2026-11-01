"""Incremental ANAC -> existing DuckDB warehouse (2025+ monthly aggregate parts).

Does not reload 2024. Uses hashes of parts CSV + source row counts from state.json.
Initial run reconciles existing fact rows before recording tracking hashes.

Usage (from project root):
  python data_warehouse/incremental_warehouse.py --check
  python data_warehouse/incremental_warehouse.py --apply

On --apply, backs up the database and applies all updates in one transaction.
Requires a warehouse previously built by load_warehouse.py with etl_month_metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
PATTERN = re.compile(r"(domestic|international)_(20\d{2})-(0[1-9]|1[0-2])\.csv\Z")
MARKET_IDS = {"domestic": 1, "international": 2}
LABELS = {"domestic": "Nội địa", "international": "Quốc tế"}


def qpath(path: Path) -> str:
    return "'" + str(path.resolve()).replace("'", "''") + "'"


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_rows(value, label: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{label}: rows khong hop le: {value!r}")
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"\d+", value.strip()):
        return int(value.strip())
    if isinstance(value, float) and math.isfinite(value) and value >= 0 and value.is_integer():
        return int(value)
    raise ValueError(f"{label}: rows khong hop le: {value!r}")


@dataclass(frozen=True)
class Part:
    key: str
    path: Path
    month_key: int
    market_key: int
    market: str
    period: str
    checksum: str
    rows: int | None
    state: dict


def find_parts(parts_dir: Path, state_path: Path) -> list[Part]:
    if not parts_dir.is_dir():
        raise FileNotFoundError(f"Khong tim thay parts: {parts_dir}")
    if not state_path.is_file():
        raise FileNotFoundError(f"Khong tim thay state.json: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    entries = state.get("months")
    if not isinstance(entries, dict):
        raise ValueError("state.json: months phai la object")
    found: list[Part] = []
    for path in sorted(parts_dir.glob("*.csv")):
        m = PATTERN.fullmatch(path.name)
        if not m:
            raise ValueError(f"Ten file parts bat thuong: {path.name}")
        market, year, month = m.groups()
        key = f"{market}_{year}-{month}"
        meta = entries.get(key)
        if not isinstance(meta, dict):
            raise ValueError(f"Khong co metadata trong state.json: {key}")
        if meta.get("month") not in (None, f"{year}-{month}"):
            raise ValueError(f"state.json sai thang tai {key}")
        if meta.get("market") not in (None, market):
            raise ValueError(f"state.json sai thi truong tai {key}")
        found.append(Part(key, path, int(year + month), MARKET_IDS[market],
                          market, f"{year}-{month}", digest_file(path),
                          parse_rows(meta.get("rows"), key), meta))
    missing = sorted(set(entries) - {p.key for p in found})
    if missing:
        raise ValueError("state.json co ky thieu file parts: " + ", ".join(missing[:10]))
    if not found:
        raise ValueError("Khong co CSV parts hop le")
    return found


def preflight(conn) -> None:
    required = ("fact_airfare_route_monthly", "dim_month", "dim_airport", "dim_market",
                "etl_month_metadata", "vw_monthly_kpi")
    existing = {x[0] for x in conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()}
    missing = [x for x in required if x not in existing]
    if missing:
        raise ValueError("DW chua duoc tao du boi load_warehouse.py: " + ", ".join(missing))
    markets = conn.execute("SELECT market_key, market_code FROM dim_market").fetchall()
    if any((i, name) not in markets for name, i in MARKET_IDS.items()):
        raise ValueError("dim_market khong tuong thich keys 1/2")


def prepare_stage(conn, part: Part) -> tuple[int, int, int, float]:
    """Load a single month into a temporary staging table, strictly validate its grain."""
    conn.execute("DROP TABLE IF EXISTS _anac_stage")
    conn.execute(f"""
      CREATE TEMP TABLE _anac_stage AS
      SELECT TRIM(THANG) AS period, TRIM(LOAI) AS label,
             UPPER(TRIM(ORIGEM)) AS origin,
             UPPER(TRIM(DESTINO)) AS dest,
             TRY_CAST(ASSENTOS AS BIGINT) AS seats,
             TRY_CAST(GHE_CO_GIA AS BIGINT) AS priced_seats,
             TRY_CAST(GIA_NHAN_GHE AS DOUBLE) AS weighted_fare
      FROM read_csv({qpath(part.path)}, delim=',', header=true, all_varchar=true)
    """)
    bad, total = conn.execute("""
        SELECT COUNT(*) FILTER (WHERE period != ? OR label != ? OR
            NOT regexp_matches(origin, '^[A-Z0-9]{4}$') OR
            NOT regexp_matches(dest, '^[A-Z0-9]{4}$') OR
            seats IS NULL OR seats <= 0 OR priced_seats IS NULL OR
            priced_seats < 0 OR priced_seats > seats OR
            weighted_fare IS NULL OR NOT isfinite(weighted_fare) OR weighted_fare < 0),
            COUNT(*)
        FROM _anac_stage
    """, [part.period, LABELS[part.market]]).fetchone()
    if not total or bad:
        raise ValueError(f"{part.key}: {bad}/{total} dong parts khong hop le")
    duplicate = conn.execute("""
        SELECT COUNT(*) FROM (
          SELECT origin, dest FROM _anac_stage
          GROUP BY origin, dest HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    if duplicate:
        raise ValueError(f"{part.key}: {duplicate} cap tuyen trung trong parts")
    n, seats, priced, fare = conn.execute("""
        SELECT COUNT(*), SUM(seats), SUM(priced_seats), SUM(weighted_fare)
        FROM _anac_stage
    """).fetchone()
    # Cross-check with ETL metadata, where values exist.
    for name, actual, abs_tol in (("seats", seats, 0.0), ("fare_seats", priced, 0.0),
                                   ("fare_weight", fare, 0.01)):
        expected = part.state.get(name)
        if expected is not None and not math.isclose(float(actual), float(expected),
                                                      rel_tol=1e-9, abs_tol=abs_tol):
            raise ValueError(f"{part.key}: {name} trong parts khong khop state.json: {actual} != {expected}")
    return n, seats, priced, fare


def facts_match_stage(conn, part: Part) -> bool:
    """Exact route/seat equality and tolerant floating-point comparison (not only totals)."""
    wrong = conn.execute("""
        SELECT COUNT(*) FROM _anac_stage s
        FULL OUTER JOIN (
            SELECT origin_airport_code AS origin, destination_airport_code AS dest,
                   total_seats AS seats, priced_seats, fare_weighted_sum AS weighted_fare
            FROM fact_airfare_route_monthly
            WHERE month_key = ? AND market_key = ?
        ) f ON s.origin = f.origin AND s.dest = f.dest
        WHERE s.origin IS NULL OR f.origin IS NULL OR
              s.seats <> f.seats OR s.priced_seats <> f.priced_seats OR
              abs(s.weighted_fare - f.weighted_fare) >
                  greatest(0.01, abs(s.weighted_fare)*1e-9)
    """, [part.month_key, part.market_key]).fetchone()[0]
    return wrong == 0


def metadata_matches(conn, part: Part) -> bool:
    current = conn.execute("""
        SELECT source_record_count, source_file FROM etl_month_metadata
        WHERE month_key = ? AND market_key = ?
    """, [part.month_key, part.market_key]).fetchone()
    return current == (part.rows, part.path.name)


def tracking_hash(conn, part: Part) -> str | None:
    exists = conn.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='main' AND table_name='etl_part_sync'
    """).fetchone()
    if not exists:
        return None
    row = conn.execute("""
        SELECT part_sha256 FROM etl_part_sync
        WHERE month_key = ? AND market_key = ?
    """, [part.month_key, part.market_key]).fetchone()
    return row[0] if row else None


def plan_for(conn, part: Part) -> str:
    tracked = tracking_hash(conn, part)
    if tracked == part.checksum:
        return "NO_CHANGE" if metadata_matches(conn, part) else "METADATA_ONLY"
    # First run, or source CSV has changed. Reconcile at route granularity.
    prepare_stage(conn, part)
    if facts_match_stage(conn, part):
        return "BASELINE" if metadata_matches(conn, part) else "METADATA_ONLY"
    return "REPLACE"


def prepare_tracking(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS etl_part_sync (
            month_key INTEGER NOT NULL,
            market_key INTEGER NOT NULL,
            part_sha256 VARCHAR NOT NULL,
            source_record_count BIGINT,
            synced_utc TIMESTAMP NOT NULL,
            PRIMARY KEY(month_key, market_key)
        )
    """)


def update_metadata(conn, part: Part) -> None:
    conn.execute("""DELETE FROM etl_month_metadata WHERE month_key=? AND market_key=?""",
                 [part.month_key, part.market_key])
    conn.execute("""
        INSERT INTO etl_month_metadata (month_key, market_key, source_record_count, source_file)
        VALUES (?, ?, ?, ?)
    """, [part.month_key, part.market_key, part.rows, part.path.name])


def update_fact(conn, part: Part) -> None:
    conn.execute("""
        INSERT INTO dim_month (month_key, sale_year, sale_month, sale_quarter)
        VALUES (?, ?, ?, ?) ON CONFLICT (month_key) DO NOTHING
    """, [part.month_key, part.month_key // 100, part.month_key % 100,
          ((part.month_key % 100 - 1) // 3) + 1])
    conn.execute("""
        INSERT INTO dim_airport (airport_code)
        SELECT all_codes.code FROM (
            SELECT origin AS code FROM _anac_stage
            UNION SELECT dest AS code FROM _anac_stage
        ) AS all_codes
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_airport d WHERE d.airport_code = all_codes.code
        )
    """)
    # Delete/reinsert only this (month, market), rather than entire warehouse.
    conn.execute("""
        DELETE FROM fact_airfare_route_monthly WHERE month_key=? AND market_key=?
    """, [part.month_key, part.market_key])
    conn.execute("""
        INSERT INTO fact_airfare_route_monthly
        (month_key,market_key,origin_airport_code,destination_airport_code,
         total_seats,priced_seats,fare_weighted_sum,source_record_count)
        SELECT ?, ?, origin, dest, seats, priced_seats, weighted_fare, NULL
        FROM _anac_stage
    """, [part.month_key, part.market_key])


def update_tracking(conn, part: Part) -> None:
    conn.execute("DELETE FROM etl_part_sync WHERE month_key=? AND market_key=?",
                 [part.month_key, part.market_key])
    conn.execute("""
        INSERT INTO etl_part_sync VALUES (?, ?, ?, ?, ?)
    """, [part.month_key, part.market_key, part.checksum, part.rows,
          datetime.now(timezone.utc).replace(tzinfo=None)])


def verify(conn, part: Part) -> None:
    if not facts_match_stage(conn, part):
        raise ValueError(f"{part.key}: dw khong khop file parts sau khi cap nhat")
    if not metadata_matches(conn, part):
        raise ValueError(f"{part.key}: metadata khong khop state.json")
    actual = conn.execute("""
        SELECT source_record_count FROM vw_monthly_kpi
        WHERE month_key=? AND market_code=?
    """, [part.month_key, part.market]).fetchone()
    if actual != (part.rows,):
        raise ValueError(f"{part.key}: vw_monthly_kpi khong khop source_record_count")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ANAC DuckDB incremental loading")
    parser.add_argument("--db", type=Path, default=HERE / "anac.duckdb")
    parser.add_argument("--parts-dir", type=Path,
                        default=PROJECT / "DuLieu_DaXuLy" / "_tu_dong" / "parts")
    parser.add_argument("--state-file", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Xem truoc, khong ghi DuckDB")
    mode.add_argument("--apply", action="store_true", help="Dong bo thay doi vao DuckDB")
    args = parser.parse_args(argv)
    db = args.db.resolve()
    state_file = (args.state_file or args.parts_dir.parent / "state.json").resolve()
    parts = find_parts(args.parts_dir.resolve(), state_file)
    if not db.is_file():
        raise FileNotFoundError(f"Chua co Data Warehouse: {db}. Hay chay load_warehouse.py lan dau.")
    with duckdb.connect(str(db)) as conn:
        preflight(conn)
        tasks = [(p, plan_for(conn, p)) for p in parts]
    tally = {k: sum(action == k for _, action in tasks)
             for k in ("NO_CHANGE", "BASELINE", "METADATA_ONLY", "REPLACE")}
    print("=== ANAC DUCKDB INCREMENTAL ===")
    print("Tong so parts:", len(parts))
    for action, label in (("NO_CHANGE", "Khong doi"),
                          ("BASELINE", "Da khop DW, chi danh dau hash"),
                          ("METADATA_ONLY", "Chi doi metadata"),
                          ("REPLACE", "Them/thay the du lieu thang")):
        print(f"{label}: {tally[action]}")
    for p, action in tasks:
        if action not in ("NO_CHANGE", "BASELINE"):
            print("  ", action, p.key)
    if args.check:
        print("CHECK ONLY - khong thay doi DuckDB")
        return 0
    todo = [(p, action) for p, action in tasks if action != "NO_CHANGE"]
    if not todo:
        print("KHONG CO DU LIEU MOI - DuckDB duoc giu nguyen")
        return 0
    # Database is closed before copying a single, reusable local backup.
    backup = db.with_name(db.name + ".before_incremental.bak")
    shutil.copy2(db, backup)
    print("SAO LUU:", backup)
    conn = duckdb.connect(str(db))
    try:
        conn.execute("BEGIN TRANSACTION")
        preflight(conn)
        prepare_tracking(conn)
        for p, expected_action in todo:
            if digest_file(p.path) != p.checksum:
                raise ValueError(f"File thay doi trong khi dang dong bo: {p.path}")
            action = plan_for(conn, p)
            if action != expected_action:
                raise ValueError(f"Du lieu thay doi sau khi kiem tra: {p.key}, {expected_action} -> {action}")
            if action == "REPLACE":
                prepare_stage(conn, p)
                update_fact(conn, p)
                update_metadata(conn, p)
                verify(conn, p)
            elif action == "METADATA_ONLY":
                update_metadata(conn, p)
                prepare_stage(conn, p)
                verify(conn, p)
            # BASELINE: only mark fingerprint; existing warehouse already reconciled.
            update_tracking(conn, p)
            print("DA DONG BO:", p.key, "-", action)
        invalid = conn.execute("""
            SELECT COUNT(*) FROM fact_airfare_route_monthly
            WHERE total_seats <= 0 OR priced_seats < 0 OR priced_seats > total_seats OR
                  fare_weighted_sum < 0
        """).fetchone()[0]
        if invalid:
            raise ValueError(f"Fact co {invalid} dong khong hop le")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        print("DA ROLLBACK - khong ghi thay doi do dong bo that bai", file=sys.stderr)
        raise
    finally:
        conn.close()
    print("THANH CONG:", len(todo), "ky dong bo /", len(parts), "ky")
    print("Luu y: file DuckDB dia phuong KHONG tu dong duoc cap nhat tren GitHub/Streamlit.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("LOI:", exc, file=sys.stderr)
        raise SystemExit(1)
