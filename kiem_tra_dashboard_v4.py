"""Read-only V4 data smoke test; actual Streamlit UI must still be checked in browser."""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB=ROOT/'data_warehouse'/'anac.duckdb'
STATS=ROOT/'data_warehouse'/'fare_distribution_by_month.csv'
LOGO=ROOT/'assets'/'anac_logo.png'


def main():
    try: import duckdb
    except ImportError:
        sys.exit('FAIL: Thieu thu vien DuckDB. Chay: python -m pip install duckdb')
    print('=== ANAC DASHBOARD V4 | KIEM TRA READ-ONLY ===')
    if not DB.is_file(): sys.exit('FAIL: Khong co data_warehouse/anac.duckdb')
    conn=duckdb.connect(str(DB),read_only=True)
    try:
        k=conn.execute('''SELECT COUNT(*),MIN(month_key),MAX(month_key),
                               COUNT(*) FILTER(WHERE total_seats<=0 OR avg_fare<=0)
                         FROM vw_monthly_kpi''').fetchone()
        if not k[0] or k[3]: raise AssertionError('KPI rong hoac co gia tri khong hop le')
        print(f'KPI {k[0]} dong, thang {k[1]}–{k[2]}: PASS')
        rec=conn.execute('''SELECT m.market_code, SUM(f.total_seats)
             FROM fact_airfare_route_monthly f JOIN dim_market m ON f.market_key=m.market_key
             WHERE f.month_key=? GROUP BY 1''',[k[2]]).fetchall()
        view=conn.execute('SELECT market_code,total_seats FROM vw_monthly_kpi WHERE month_key=?',[k[2]]).fetchall()
        assert {a:int(b) for a,b in rec}=={a:int(b) for a,b in view},'Fact vs KPI lech tong ghe thang cuoi'
        print('Fact vs KPI thang moi nhat: PASS',rec)
        n=conn.execute('''SELECT COUNT(*) FROM fact_airfare_route_monthly
            WHERE total_seats<1 OR priced_seats>total_seats OR priced_seats<=0''').fetchone()[0]
        assert n==0,f'{n} fact rows failed quality checks'
        print('Gia tri Fact co ban: PASS')
    finally:
        conn.close()
    print('Logo:', 'PASS' if LOGO.is_file() else 'WARN: Thieu logo')
    if STATS.exists():
        df=pd.read_csv(STATS,encoding='utf-8-sig')
        assert {'THANG','market_code','p10','q1','median','q3','p90'}.issubset(df.columns)
        valid=(df.p10<=df.q1)&(df.q1<=df['median'])&(df['median']<=df.q3)&(df.q3<=df.p90)
        assert valid.all(), 'Thu tu phan vi Boxplot khong hop le'
        print(f'Phan vi gia ve goc: {len(df)} ky | PASS')
    else:
        print('Boxplot: CHUA CO BANG PHAN VI — CHI HIEN CANH BAO (KHONG GIA DU LIEU)')
    print('KET LUAN: PASS | Ket noi du lieu. Can mo Streamlit de kiem tra giao dien.')

if __name__=='__main__': main()
