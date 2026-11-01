"""Build weighted fare quantiles from RAW/cleaned ticket-fare records.

For 2024: python data_warehouse/build_fare_distributions.py --clean-dir "C:/.../Dulieusach"
For 2025+: optional --raw-monthly-dir DIR containing domestic_YYYY-MM.csv / international_YYYY-MM.csv.
Produces ONLY `data_warehouse/fare_distribution_by_month.csv` (not .duckdb).
Exact discrete weighted percentiles by ASSENTOS, not percentiles of average fares.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data_warehouse' / 'fare_distribution_by_month.csv'
MARKETS = [('noi_dia_sach_2024.csv', 'domestic'), ('quoc_te_sach_2024.csv', 'international')]


def normalize_number(series):
    s = series.astype('string').str.strip().str.replace(r'[^\d,.\-]', '', regex=True)
    comma = s.str.contains(',', regex=False).fillna(False)
    dot = s.str.contains('.', regex=False).fillna(False)
    both = comma & dot
    c_dec = both & (s.str.rfind(',') > s.str.rfind('.'))
    d_dec = both & ~c_dec
    s.loc[c_dec] = s.loc[c_dec].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    s.loc[d_dec] = s.loc[d_dec].str.replace(',', '', regex=False)
    s.loc[comma & ~dot] = s.loc[comma & ~dot].str.replace(',', '.', regex=False)
    return pd.to_numeric(s, errors='coerce')


def weighted_quantile(fare_weights, probabilities):
    """Exact discrete weighted quantiles; each sold seat is one weight."""
    pairs = sorted((float(price), int(seats)) for price, seats in fare_weights.items() if seats > 0)
    if not pairs:
        return [float('nan')] * len(probabilities)
    prices = np.array([a for a, _ in pairs], dtype=float)
    counts = np.array([b for _, b in pairs], dtype=np.int64)
    cumul = np.cumsum(counts)
    total = int(cumul[-1])
    return [float(prices[min(np.searchsorted(cumul, max(1, np.ceil(total * q)), side='left'), len(prices)-1)])
            for q in probabilities]


def accumulate(path, market, counter, source_mode, expected_period=None):
    with path.open('rb') as f:
        head = f.readline().decode('latin-1')
    sep = ';' if head.count(';') >= head.count(',') else ','
    encoding = 'utf-8-sig' if source_mode == 'clean' else 'latin-1'
    from sys import path as syspath
    if source_mode == 'raw':
        syspath.insert(0, str(ROOT))
        from cap_nhat_anac import col, num
    for chunk in pd.read_csv(path, sep=sep, encoding=encoding, dtype='string', chunksize=90_000,
                             on_bad_lines='error', low_memory=False):
        if source_mode == 'clean':
            cols = {s.upper().strip(): s for s in chunk.columns}
            need = ['THANG', 'TARIFA', 'ASSENTOS']
            if any(n not in cols for n in need):
                raise ValueError(f'{path.name} khong co day du THANG, TARIFA, ASSENTOS')
            periods = chunk[cols['THANG']].astype('string').str.strip()
            fares = normalize_number(chunk[cols['TARIFA']])
            seats = normalize_number(chunk[cols['ASSENTOS']])
        else:
            o, de = col(chunk.columns, 'origin'), col(chunk.columns, 'destination')
            f, s = col(chunk.columns, 'fare'), col(chunk.columns, 'seats')
            y, m = col(chunk.columns, 'year', False), col(chunk.columns, 'month', False)
            group = col(chunk.columns, 'group', False)
            periods = pd.Series(expected_period, index=chunk.index, dtype='string')
            ok = chunk[o].str.strip().str.upper().str.fullmatch(r'[A-Z0-9]{4}', na=False) & chunk[de].str.strip().str.upper().str.fullmatch(r'[A-Z0-9]{4}',na=False)
            if y is not None:
                ok &= num(chunk[y]).eq(int(expected_period[:4])).fillna(False)
            if m is not None:
                ok &= num(chunk[m]).eq(int(expected_period[-2:])).fillna(False)
            if group is not None and market == 'domestic' and int(expected_period[:4]) >= 2026:
                ok &= chunk[group].str.strip().str.upper().isin(['1', 'I', 'GRUPO I', 'GRUPO 1'])
            fares, seats = num(chunk[f]), num(chunk[s])
            fares = fares.where(ok)
        good = fares.gt(0) & seats.gt(0) & seats.mod(1).eq(0) & periods.str.fullmatch(r'20\d\d-(0[1-9]|1[0-2])',na=False)
        if expected_period:
            good &= periods.eq(expected_period)
        if source_mode == 'clean':
            good &= periods.str.startswith('2024')
        sub = pd.DataFrame({'THANG': periods[good], 'TARIFA': fares[good], 'ASSENTOS': seats[good].astype('int64')})
        if sub.empty: continue
        # Group duplicate prices locally, avoiding retention of individual records.
        agg = sub.groupby(['THANG','TARIFA'], observed=True)['ASSENTOS'].sum()
        for (month, price), sold in agg.items():
            counter[(str(month), market)][float(price)] += int(sold)


def build(clean_dir, raw_dir, out):
    agg = defaultdict(lambda: defaultdict(int))
    for name, market in MARKETS:
        path = clean_dir / name
        if not path.is_file(): raise FileNotFoundError(path)
        print('Doc nguon 2024:', path.name, flush=True)
        accumulate(path, market, agg, 'clean')
    if raw_dir is not None:
        for p in sorted(raw_dir.glob('*.csv')):
            match = re.fullmatch(r'(domestic|international)_(20\d{2}-(?:0[1-9]|1[0-2]))\.csv', p.name)
            if not match: continue
            print('Doc nguon hang thang:', p.name, flush=True)
            accumulate(p, match.group(1), agg, 'raw', match.group(2))
    rows = []
    for (month, market), price_counts in sorted(agg.items()):
        p10, p25, p50, p75, p90 = weighted_quantile(price_counts, [.10, .25, .50, .75, .90])
        rows.append(dict(THANG=month, market_code=market, currency_code=('BRL' if market=='domestic' else 'USD'),
                         p10=p10, q1=p25, median=p50, q3=p75, p90=p90,
                         priced_seats=sum(price_counts.values()), method='discrete_quantile_weighted_by_sold_seats'))
    if not rows: raise ValueError('Khong co du lieu gia hop le')
    frame = pd.DataFrame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix('.tmp')
    frame.to_csv(tmp,index=False,encoding='utf-8-sig')
    tmp.replace(out)
    print('HOAN TAT:',len(frame),'dong ->',out)
    print('Luu y: Râu Boxplot = P10/P90; du lieu chi co cac ky da doc raw. Khong suy dien ky thieu.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clean-dir', type=Path, required=True)
    parser.add_argument('--raw-monthly-dir', type=Path)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    args=parser.parse_args()
    build(args.clean_dir,args.raw_monthly_dir,args.out)

if __name__ == '__main__': main()
