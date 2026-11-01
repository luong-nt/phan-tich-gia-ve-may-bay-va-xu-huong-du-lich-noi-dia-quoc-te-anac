import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from dashboard_v4_analytics import weighted_mean_fare, matched_yoy, heatmap_matrix, pareto, dumbbell_pairs
from data_warehouse.build_fare_distributions import weighted_quantile


def test_weighted_price_correct_denominator():
    d=pd.DataFrame({'GIA_BINH_QUAN':[100,200], 'GHE_CO_GIA':[1,3]})
    assert weighted_mean_fare(d) == 175


def test_yoy_matches_only_available_months():
    d=pd.DataFrame([
        ['2025-04','Noi dia',100,100,100],
        ['2025-05','Noi dia',400,500,400],
        ['2025-06','Noi dia',200,200,200],
        ['2026-04','Noi dia',200,200,200],
        ['2026-06','Noi dia',400,250,400],
    ],columns=['THANG','LOAI_CHUYEN_BAY','SO_GHE_BAN','GIA_BINH_QUAN','GHE_CO_GIA'])
    y=matched_yoy(d,'Noi dia',2026,[4,5,6])
    assert y['months']==[4,6]
    assert y['seats_yoy']==100
    assert y['seats_current']==600
    assert y['seats_prev']==300
    assert y['fare_current']==(200*200+250*400)/600


def test_yoy_no_previous_period_returns_none():
    d=pd.DataFrame([['2024-01','Noi dia',100,100,100]],columns=['THANG','LOAI_CHUYEN_BAY','SO_GHE_BAN','GIA_BINH_QUAN','GHE_CO_GIA'])
    assert matched_yoy(d,'Noi dia',2024,[1]) is None


def test_heatmap_missing_month_is_nan():
    d=pd.DataFrame({'THANG':['2026-04','2026-06'],'LOAI_CHUYEN_BAY':['Noi dia','Noi dia'],'GIA_BINH_QUAN':[100,150]})
    m=heatmap_matrix(d,'Noi dia')
    assert pd.isna(m.loc[2026,5])
    assert m.loc[2026,6]==150


def test_pareto_denominator_all_routes():
    d=pd.DataFrame({'LOAI':['Nội địa']*3, 'ORIGEM':['AAA','AAA','AAA'],'DESTINO':['BBB','CCC','DDD'],'ASSENTOS':[60,30,10]})
    p,n=pareto(d,'Nội địa')
    assert n==2
    assert p.cumulative_pct.iloc[-1]==100
    assert p.cumulative_pct.iloc[0]==60


def test_dumbbell_only_shared_routes():
    d=pd.DataFrame({'sale_year':[2024,2024,2025,2025], 'ORIGEM':['AAA']*4,'DESTINO':['BBB','CCC','BBB','DDD'],'ASSENTOS':[100,90,150,10]})
    pairs=dumbbell_pairs(d,2025)
    assert len(pairs)==1
    assert pairs.iloc[0].delta_pct==50


def test_weighted_quantiles_from_raw_prices_not_avg():
    q=weighted_quantile({100:1, 200:3},[.10,.25,.50,.75,.90])
    assert q==[100,100,200,200,200]


def test_invalid_fare_weights_ignored():
    assert weighted_quantile({10:0,20:2},[.5])==[20]
