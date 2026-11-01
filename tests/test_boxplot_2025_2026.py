"""Offline tests for the 2025+ incremental ANAC raw-fare distribution updater."""
from __future__ import annotations
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from data_warehouse import cap_nhat_phan_phoi_gia as m


def baseline() -> pd.DataFrame:
    return pd.DataFrame([
        {'THANG':'2024-01','market_code':'domestic','currency_code':'BRL',
         'p10':50.0,'q1':60.0,'median':70.0,'q3':80.0,'p90':90.0,
         'priced_seats':100, 'method':'discrete_quantile_weighted_by_sold_seats'},
        {'THANG':'2024-01','market_code':'international','currency_code':'USD',
         'p10':100.0,'q1':110.0,'median':120.0,'q3':130.0,'p90':140.0,
         'priced_seats':150, 'method':'discrete_quantile_weighted_by_sold_seats'},
    ])


def sample_raw(path: Path, group_2026: bool=False) -> None:
    if group_2026:
        path.write_text('nr_ano_referencia;nr_mes_referencia;sg_icao_origem;sg_icao_destino;nr_tarifa;nr_assentos;GRUPO\n'
                        '2026;01;SBGR;SBRJ;100,00;2;1\n'
                        '2026;01;SBGR;SBRJ;999,00;50;2\n'
                        '2026;01;SBGR;SBRJ;200,00;3;1\n',encoding='latin-1')
    else:
        path.write_text('nr_ano_referencia;nr_mes_referencia;sg_icao_origem;sg_icao_destino;nr_tarifa;nr_assentos\n'
                        '2025;01;SBGR;SBRJ;100,00;2\n'
                        '2025;01;SBGR;SBRJ;200,00;3\n'
                        '2025;01;SBGR;SBRJ;300,00;1\n'
                        '2025;02;SBGR;SBRJ;999,00;12\n'
                        '2025;01;BAD;SBRJ;900,00;5\n',encoding='latin-1')


def meta(path: Path, market='domestic', period='2025-01', fare_seats=6):
    return {'url':f'https://sas.anac.gov.br/sas/tarifadomestica/{period[:4]}/{period.replace("-", "")}.csv',
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'fare_seats':fare_seats}


def test_compute_discrete_quantiles_from_raw(tmp_path):
    raw=tmp_path/'domestic_2025-01.csv'; sample_raw(raw)
    row=m.summarize_month(raw, 'domestic','2025-01',meta(raw))
    assert row['priced_seats']==6
    assert (row['p10'], row['q1'], row['median'], row['q3'], row['p90']) == (100,100,200,200,300)


def test_reject_seat_mismatch(tmp_path):
    raw=tmp_path/'domestic_2025-01.csv'; sample_raw(raw)
    with pytest.raises(ValueError,match='KHONG KHOP'):
        m.summarize_month(raw,'domestic','2025-01',meta(raw, fare_seats=999))


def test_year_2026_group_filter(tmp_path):
    raw=tmp_path/'domestic_2026-01.csv'; sample_raw(raw,group_2026=True)
    row=m.summarize_month(raw,'domestic','2026-01',meta(raw,period='2026-01',fare_seats=5))
    assert row['priced_seats'] == 5
    assert row['p90'] == 200


def test_plan_detects_new_and_unchanged(tmp_path):
    raw=tmp_path/'domestic_2025-01.csv'; sample_raw(raw)
    metadata=meta(raw)
    key='domestic_2025-01'
    pending,unchanged=m.planned({key:metadata},baseline(),{})
    assert len(pending)==1 and not unchanged
    after= pd.concat([baseline(),pd.DataFrame([m.summarize_month(raw,'domestic','2025-01',metadata)])])
    pending,unchanged=m.planned({key:metadata},after,{key:{'sha256':metadata['sha256']}})
    assert not pending and unchanged == [key]


def test_plan_detects_revised_sha(tmp_path):
    raw=tmp_path/'domestic_2025-01.csv'; sample_raw(raw)
    metadata=meta(raw)
    after=pd.concat([baseline(),pd.DataFrame([m.summarize_month(raw,'domestic','2025-01',metadata)])])
    p,u=m.planned({'domestic_2025-01':metadata},after,{'domestic_2025-01':{'sha256':'0'*64}})
    assert len(p)==1 and not u


def test_atomic_save_preserves_2024_and_is_repeatable(tmp_path, monkeypatch):
    raw=tmp_path/'domestic_2025-01.csv'; sample_raw(raw)
    monkeypatch.setattr(m,'OUTPUT',tmp_path/'fare_distribution_by_month.csv')
    monkeypatch.setattr(m,'SYNC_PATH',tmp_path/'fare_distribution_sync.json')
    baseline().to_csv(m.OUTPUT,index=False)
    metadata=meta(raw)
    first,sync=m.apply_one(raw,'domestic_2025-01','domestic','2025-01',metadata,baseline(),{})
    second,sync=m.apply_one(raw,'domestic_2025-01','domestic','2025-01',metadata,first,sync)
    assert len(first)==3 and len(second)==3
    assert m.read_table().loc[lambda d:d.THANG.eq('2024-01'),'priced_seats'].sum()==250
    assert len(m.read_sync())==1


def test_reject_unexpected_source_domain():
    with pytest.raises(ValueError):
        m.check_url('https://example.com/file.csv','domestic','2025-01')


def test_reject_wrong_raw_namespace():
    with pytest.raises(ValueError):
        m.check_url('https://sas.anac.gov.br/sas/tarifainternacional/2025/x.csv','domestic','2025-01')
