"""Read-only smoke test for the upgraded ANAC dashboard data sources."""
from pathlib import Path
import sys
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data_warehouse' / 'anac.duckdb'
RESULTS = ROOT / 'data_warehouse' / 'analysis_results'

if not DB.is_file():
    sys.exit(f'FAIL: khong tim thay {DB}')

con = duckdb.connect(str(DB), read_only=True)
try:
    print('=== DASHBOARD V2 | KET NOI DUCKDB ===')
    data = con.execute('''
        SELECT COUNT(*) AS n, MIN(month_key) AS begin_month,
               MAX(month_key) AS end_month
        FROM vw_monthly_kpi
    ''').fetchone()
    print('Monthly KPI:', data[0], '| tu:', data[1], '| den:', data[2])
    if data[0] <= 0:
        raise AssertionError('View KPI rong')

    missing_market = con.execute('''
       SELECT COUNT(*) FROM vw_monthly_kpi
       WHERE market_code NOT IN ('domestic','international')
          OR currency_code NOT IN ('BRL','USD')
          OR total_seats <= 0 OR avg_fare <= 0
    ''').fetchone()[0]
    if missing_market:
        raise AssertionError(f'{missing_market} KPI khong hop le')
    print('KPI market/currency/price: PASS')

    month = con.execute('''
       SELECT market_code, SUM(total_seats),
              ROUND(SUM(avg_fare * priced_seats) / NULLIF(SUM(priced_seats), 0), 2)
       FROM vw_monthly_kpi WHERE month_key = 202609
       GROUP BY 1
    ''').fetchall()
    print('Thang 2026-09:', month)

    routes = con.execute('''
        SELECT COUNT(*), SUM(f.total_seats)
        FROM fact_airfare_route_monthly f
        JOIN dim_market m ON m.market_key = f.market_key
        LEFT JOIN dim_airport a ON a.airport_code = f.origin_airport_code
        LEFT JOIN dim_airport b ON b.airport_code = f.destination_airport_code
        WHERE f.month_key BETWEEN 202501 AND 202509
          AND m.market_code='domestic'
    ''').fetchone()
    if routes[0] <= 0:
        raise AssertionError('Khong truy van duoc Fact/tuyen bay')
    print('Query Fact + Dimension:', routes[0], 'tuyen-thang | PASS')

    dest = con.execute('''
        SELECT COUNT(*) FROM (
          SELECT f.destination_airport_code,
                 COALESCE(NULLIF(TRIM(b.municipality), ''), b.airport_name,
                          f.destination_airport_code) AS DIA_DIEM,
                 SUM(f.total_seats) AS ASSENTOS
          FROM fact_airfare_route_monthly f
          JOIN dim_market m ON m.market_key=f.market_key
          LEFT JOIN dim_airport a ON a.airport_code=f.origin_airport_code
          LEFT JOIN dim_airport b ON b.airport_code=f.destination_airport_code
          WHERE f.month_key BETWEEN 202501 AND 202509
            AND a.country_code='BR'
            AND ((m.market_code='domestic' AND b.country_code='BR')
               OR (m.market_code='international' AND b.country_code IS NOT NULL
                     AND b.country_code<>'BR'))
          GROUP BY 1,2
        )
    ''').fetchone()[0]
    print('Query diem den:', dest, '| PASS')
finally:
    con.close()

available = [RESULTS / f'Q{i:02d}.csv' for i in range(1,18)]
present = [p for p in available if p.exists()]
print(f'Insight snapshots: {len(present)}/17 CSV')
if (RESULTS / 'Q01.csv').exists():
    q1 = pd.read_csv(RESULTS / 'Q01.csv')
    print('Q01 latest month:', int(q1['month_key'].max()))
print('KET LUAN: PASS | Du lieu DuckDB da truy van duoc; chua thay the kiem tra giao dien Streamlit.')
