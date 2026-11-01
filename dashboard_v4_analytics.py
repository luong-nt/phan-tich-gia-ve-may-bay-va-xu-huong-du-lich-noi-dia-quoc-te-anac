"""Pure, testable analytics for ANAC V4; all dates are SALE months."""
from __future__ import annotations
import numpy as np
import pandas as pd

MARKETS = {'Noi dia': 'Nội địa', 'Quoc te': 'Quốc tế'}


def weighted_mean_fare(frame: pd.DataFrame) -> float:
    if frame.empty:
        return float('nan')
    fares = pd.to_numeric(frame['GIA_BINH_QUAN'], errors='coerce')
    weights = pd.to_numeric(frame['GHE_CO_GIA'], errors='coerce')
    valid = fares.notna() & weights.gt(0)
    if not valid.any():
        return float('nan')
    return float((fares.loc[valid] * weights.loc[valid]).sum() / weights.loc[valid].sum())


def matched_yoy(monthly: pd.DataFrame, market: str, focus_year: int, month_numbers: list[int]):
    """Strictly matched months; omitted months never treated as 0."""
    d = monthly.loc[monthly['LOAI_CHUYEN_BAY'].eq(market)].copy()
    d['year'] = d['THANG'].str[:4].astype(int)
    d['month'] = d['THANG'].str[5:7].astype(int)
    a = d.loc[d.year.eq(focus_year) & d.month.isin(month_numbers)].copy()
    b = d.loc[d.year.eq(focus_year - 1) & d.month.isin(month_numbers)].copy()
    common = sorted(set(a.month) & set(b.month))
    a, b = a.loc[a.month.isin(common)], b.loc[b.month.isin(common)]
    if not common:
        return None
    seats_a, seats_b = float(a.SO_GHE_BAN.sum()), float(b.SO_GHE_BAN.sum())
    fare_a, fare_b = weighted_mean_fare(a), weighted_mean_fare(b)
    return {
        'year': focus_year, 'previous': focus_year - 1, 'months': common,
        'seats_current': seats_a, 'seats_prev': seats_b,
        'seats_yoy': 100 * (seats_a / seats_b - 1) if seats_b > 0 else np.nan,
        'fare_current': fare_a, 'fare_prev': fare_b,
        'fare_yoy': 100 * (fare_a / fare_b - 1) if np.isfinite(fare_b) and fare_b > 0 else np.nan,
    }


def heatmap_matrix(monthly: pd.DataFrame, market: str):
    d = monthly.loc[monthly.LOAI_CHUYEN_BAY.eq(market)].copy()
    d['year'] = d.THANG.str[:4].astype(int)
    d['month'] = d.THANG.str[5:7].astype(int)
    p = d.pivot_table(index='year', columns='month', values='GIA_BINH_QUAN', aggfunc='first')
    return p.reindex(columns=range(1, 13)).sort_index()


def pareto(routes: pd.DataFrame, market_name: str):
    """Use ALL route records, not only plotted top-N; return full denominator."""
    d = routes.loc[routes.LOAI.eq(market_name), ['ORIGEM', 'DESTINO', 'ASSENTOS']].copy()
    d['ASSENTOS'] = pd.to_numeric(d['ASSENTOS'], errors='coerce')
    d = (d.groupby(['ORIGEM', 'DESTINO'], as_index=False).ASSENTOS.sum()
           .query('ASSENTOS > 0').sort_values('ASSENTOS', ascending=False).reset_index(drop=True))
    if d.empty:
        return d, 0
    d['route_label'] = d.ORIGEM.astype(str) + ' → ' + d.DESTINO.astype(str)
    total = float(d.ASSENTOS.sum())
    d['cumulative_pct'] = 100.0 * d.ASSENTOS.cumsum() / total
    count_80 = int(np.searchsorted(d.cumulative_pct.to_numpy(), 80.0, side='left') + 1)
    return d, count_80


def dumbbell_pairs(route_years: pd.DataFrame, focus_year: int, limit=15):
    """Only routes present in BOTH years, rank by current-year seats."""
    x = route_years.loc[route_years.sale_year.eq(focus_year), ['ORIGEM','DESTINO','ASSENTOS']]
    y = route_years.loc[route_years.sale_year.eq(focus_year-1), ['ORIGEM','DESTINO','ASSENTOS']]
    d = x.merge(y, on=['ORIGEM','DESTINO'], how='inner', suffixes=('_current','_prev'))
    if d.empty:
        return d
    d = d.nlargest(limit, 'ASSENTOS_current').copy()
    d['label'] = d.ORIGEM.astype(str) + ' → ' + d.DESTINO.astype(str)
    d['delta_pct'] = np.where(d.ASSENTOS_prev.gt(0), 100 * (d.ASSENTOS_current / d.ASSENTOS_prev - 1), np.nan)
    return d.sort_values('ASSENTOS_current')


def usable_distribution(stats: pd.DataFrame, market_code: str, start: str, end: str):
    """True price distribution statistics from raw-price stage, never from averages."""
    if stats.empty:
        return stats
    d = stats[(stats.market_code == market_code) & stats.THANG.between(start, end)].copy()
    return d.sort_values('THANG')
