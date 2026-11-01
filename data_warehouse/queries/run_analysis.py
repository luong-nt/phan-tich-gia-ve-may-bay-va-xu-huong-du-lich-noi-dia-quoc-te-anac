"""Run ANAC advanced analysis SQL queries against an EXISTING DuckDB, read-only.

Usage from Portfolio project root:
    python data_warehouse/queries/run_analysis.py --check
    python data_warehouse/queries/run_analysis.py --only Q02
    python data_warehouse/queries/run_analysis.py --all
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("THIEU THU VIEN duckdb. Chay: python -m pip install duckdb")
    sys.exit(2)

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "anac.duckdb"
SQL = HERE / "analysis.sql"
OUTPUT = HERE.parent / "analysis_results"
HEADER = re.compile(r"^-- QUERY (Q\d{2}): (.+)$", re.MULTILINE)


def read_queries(path: Path) -> list[tuple[str, str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    matches = list(HEADER.finditer(text))
    if not matches:
        raise ValueError("Khong tim thay dong '-- QUERY Q01: ...' trong analysis.sql")
    result = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sql = text[start:end].strip()
        if not sql.endswith(";"):
            raise ValueError(f"{match.group(1)}: cau truy van phai ket thuc bang ';'")
        sql = sql[:-1].strip()
        # Loai bo cac dong chu thich dung rieng de xac nhan do la SELECT/CTE.
        sql = "\n".join(
            line for line in sql.splitlines()
            if not line.lstrip().startswith("--")
        ).strip()
        if not sql.upper().startswith(("SELECT", "WITH")):
            raise ValueError(f"{match.group(1)}: chi cho phep SELECT / WITH")
        result.append((match.group(1), match.group(2).strip(), sql))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="ANAC advanced SQL runner (read-only)")
    opts = parser.add_mutually_exclusive_group(required=True)
    opts.add_argument("--check", action="store_true", help="Check that all SQL queries compile; do not execute")
    opts.add_argument("--all", action="store_true", help="Run all queries, export CSV")
    opts.add_argument("--only", metavar="Q01", help="Run one query, export CSV")
    opts.add_argument("--list", action="store_true", help="List query titles")
    args = parser.parse_args()

    try:
        queries = read_queries(SQL)
    except Exception as exc:
        print("LOI PHAN TICH FILE SQL:", exc)
        return 1

    if args.list:
        for code, title, _ in queries:
            print(f"{code}: {title}")
        return 0

    if args.only:
        queries = [q for q in queries if q[0].upper() == args.only.upper()]
        if not queries:
            print("Khong tim thay truy van:", args.only)
            return 1
    if not DB.is_file():
        print("KHONG TIM THAY DUCKDB:", DB)
        return 1

    fail = 0
    con = duckdb.connect(str(DB), read_only=True)
    try:
        for code, title, query in queries:
            try:
                if args.check:
                    con.execute("EXPLAIN " + query).fetchall()
                    print(f"PASS {code} | {title}")
                else:
                    cursor = con.execute(query)
                    headers = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    OUTPUT.mkdir(parents=True, exist_ok=True)
                    target = OUTPUT / f"{code}.csv"
                    with target.open("w", encoding="utf-8-sig", newline="") as handle:
                        writer = csv.writer(handle)
                        writer.writerow(headers)
                        writer.writerows(rows)
                    print(f"PASS {code} | {len(rows)} dong | {target.name}")
                    for row in rows[:2]:
                        print("   ", row)
            except Exception as exc:
                fail += 1
                print(f"FAIL {code} | {type(exc).__name__}: {exc}")
    finally:
        con.close()

    print(f"\nKET QUA: {len(queries) - fail} PASS | {fail} FAIL")
    if not args.check and fail == 0:
        print("CSV KET QUA:", OUTPUT)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
