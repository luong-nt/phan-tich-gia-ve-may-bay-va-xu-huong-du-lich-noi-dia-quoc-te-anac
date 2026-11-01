"""Validate selected Business Insights against existing Q01-Q17 CSV outputs.

Read-only. Does not modify source CSV files or DuckDB.
Run from project root:
 python data_warehouse/queries/validate_business_insights.py --results-dir data_warehouse/analysis_results
"""
from __future__ import annotations
import argparse
from pathlib import Path
import math
import pandas as pd


def row(df: pd.DataFrame, **filters):
    mask = pd.Series(True, index=df.index)
    for key, value in filters.items():
        mask &= df[key].eq(value)
    result = df.loc[mask]
    if len(result) != 1:
        raise ValueError(f"Expected one row for {filters}, found {len(result)}")
    return result.iloc[0]


def close(actual, target, atol=0.02):
    return math.isclose(float(actual), float(target), abs_tol=atol, rel_tol=0)


def run(results: Path):
    source = {f"Q{i:02d}": pd.read_csv(results / f"Q{i:02d}.csv") for i in range(1, 18)}
    tests = []

    def check(name, result):
        tests.append((name, bool(result)))
        print(f"{'PASS' if result else 'FAIL'} | {name}")

    a = source['Q01']
    check('56 monthly KPI rows and 56 unique market/month keys',
          len(a) == 56 and not a.duplicated(['month_key', 'market_code']).any())
    c = a.groupby(['sale_year', 'market_code']).size().to_dict()
    check('Coverage 2024/2025 full + 2026 domestic 8', c == {
        (2024, 'domestic'): 12, (2024, 'international'): 12,
        (2025, 'domestic'): 12, (2025, 'international'): 12,
        (2026, 'domestic'): 8})

    y = source['Q04']
    d24 = row(y,sale_year=2024,market_code='domestic')
    d25 = row(y,sale_year=2025,market_code='domestic')
    i24 = row(y,sale_year=2024,market_code='international')
    i25 = row(y,sale_year=2025,market_code='international')
    growth=lambda v0,v1:100*(float(v1)/float(v0)-1)
    check('2025 domestic seats +9.94%',close(growth(d24.total_seats,d25.total_seats),9.94))
    check('2025 international seats +18.87%',close(growth(i24.total_seats,i25.total_seats),18.87))
    check('2025 domestic average fare +1.63%',close(growth(d24.weighted_avg_fare,d25.weighted_avg_fare),1.63))
    check('2025 international average fare -7.12%',close(growth(i24.weighted_avg_fare,i25.weighted_avg_fare),-7.12))
    yoy = source['Q03']
    intl25 = yoy[((yoy.month_key>=202501)&(yoy.month_key<=202512))&(yoy.market_code=='international')]
    dom25 = yoy[((yoy.month_key>=202501)&(yoy.month_key<=202512))&(yoy.market_code=='domestic')]
    check('2025 international all 12 months sold more seats YoY',len(intl25)==12 and int((intl25.yoy_seats_pct>0).sum())==12)
    check('2025 domestic 9 months sold more seats YoY',len(dom25)==12 and int((dom25.yoy_seats_pct>0).sum())==9)

    for market, minmonth, maxmonth in [('domestic',5,12),('international',11,None)]:
        for year in [2024,2025]:
            part=a[(a.sale_year==year)&(a.market_code==market)]
            check(f'{market} {year} min fare month {minmonth}',
                  int(part.loc[part.avg_fare.idxmin(),'sale_month'])==minmonth)
            if maxmonth is not None:
                check(f'{market} {year} max fare month {maxmonth}',
                      int(part.loc[part.avg_fare.idxmax(),'sale_month'])==maxmonth)

    mom=source['Q02']
    dec25=row(mom, month_key=202512,market_code='domestic')
    check('Dec 2025 domestic MoM price +21.59%',close(dec25.mom_fare_pct,21.59))
    check('Dec 2025 domestic MoM seats -41.12%',close(dec25.mom_seats_pct,-41.12))
    corr=source['Q07']
    check('2025 domestic Pearson r -0.6207',close(row(corr,sale_year=2025,market_code='domestic').pearson_r_fare_vs_seats,-0.6207,0.0001))
    check('2025 international Pearson r -0.6092',close(row(corr,sale_year=2025,market_code='international').pearson_r_fare_vs_seats,-0.6092,0.0001))
    opp=source['Q08']
    count_valid={market:int(mom[(mom.market_code==market)].previous_month_key.notna().sum()) for market in ('domestic','international')}
    count_opp={market:int((opp.market_code==market).sum()) for market in ('domestic','international')}
    check('Opposite monthly movement domestic 22/30',count_valid['domestic']==30 and count_opp['domestic']==22)
    check('Opposite monthly movement international 17/23',count_valid['international']==23 and count_opp['international']==17)

    ranks=source['Q09']
    for market, n_both,n_decline in [('domestic',17,3),('international',15,5)]:
        before=ranks[(ranks.market_code==market)&(ranks.sale_year==2024)]
        after=ranks[(ranks.market_code==market)&(ranks.sale_year==2025)]
        joined=before.merge(after,on=['market_code','origin_airport_code','destination_airport_code'],suffixes=('_2024','_2025'))
        check(f'{market}: {n_decline}/{n_both} repeat Top20 routes declined',
              len(joined)==n_both and int((joined.total_seats_2025<joined.total_seats_2024).sum())==n_decline)
    concentration=source['Q11']
    check('2025 domestic Top10 share 11.02%',close(row(concentration,sale_year=2025,market_code='domestic').top10_seat_share_pct,11.02))
    check('2025 international Top10 share 38.72%',close(row(concentration,sale_year=2025,market_code='international').top10_seat_share_pct,38.72))
    ytd=source['Q05']
    check('2026 matched 8 months seats -3.42% and fare +7.12%',
          len(ytd)==1 and int(ytd.iloc[0].matched_months)==8 and close(ytd.iloc[0].seats_yoy_pct,-3.42) and close(ytd.iloc[0].fare_yoy_pct,7.12))
    gap=source['Q16']
    check('Missing 2026-05 domestic',len(gap)==1 and int(gap.iloc[0].missing_month_key)==202605 and gap.iloc[0].market_code=='domestic')
    geo=source['Q15']
    check('6724 fact rows with missing geo, 0.79% seats',int(geo.rows_missing_geo.sum())==6724 and close(100*geo.seats_on_routes_missing_geo.sum()/geo.total_seats.sum(),0.79))
    flags=source['Q14']
    check('3 flagged periods under given custom thresholds',len(flags)==3 and set(flags.month_key)=={202501,202512,202601})
    passed=sum(p for _,p in tests)
    print(f'\nKET QUA BUSINESS INSIGHTS: {passed} PASS | {len(tests)-passed} FAIL')
    return len(tests)-passed


def main():
    parser=argparse.ArgumentParser(description='Read-only checks for ANAC Business Insights report')
    parser.add_argument('--results-dir',type=Path,default=Path('data_warehouse/analysis_results'))
    args=parser.parse_args()
    if not args.results_dir.is_dir():
        parser.error(f'Khong thay thu muc: {args.results_dir}')
    try:
        failures=run(args.results_dir)
    except (FileNotFoundError,ValueError,KeyError) as e:
        parser.error(f'Du lieu Q01-Q17 khong hop le: {e}')
    raise SystemExit(1 if failures else 0)


if __name__=='__main__':
    main()
