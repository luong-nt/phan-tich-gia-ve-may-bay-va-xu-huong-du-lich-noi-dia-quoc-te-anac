"""Recover missing count of valid ANAC source records for domestic 2025-01.

Place this script in the Portfolio project root, next to cap_nhat_anac.py.
It downloads only the official ANAC 2025-01 source, runs the same ETL
filters, compares all existing route aggregates and optionally the saved
source checksum, then updates only state.json (with a backup).

No writes to parts, baseline, dashboard CSV or DuckDB.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import cap_nhat_anac as etl

KEY = 'domestic_2025-01'
YEAR_MONTH = '2025-01'
EXPECTED_SEATS = 2_877_862  # Cross-checked with the user's Portfolio summary


def _routes_for_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    needed = ('ORIGEM', 'DESTINO', 'ASSENTOS', 'GIA_NHAN_GHE', 'GHE_CO_GIA')
    absent = [field for field in needed if field not in frame.columns]
    if absent:
        raise ValueError(f'Thieu cot trong bang theo tuyen: {absent}')
    result = frame[list(needed)].copy()
    for field in needed[2:]:
        result[field] = pd.to_numeric(result[field], errors='raise')
    if result[['ORIGEM', 'DESTINO']].isna().any().any():
        raise ValueError('Ma san bay bi thieu, khong the doi chieu')
    return (
        result.groupby(['ORIGEM', 'DESTINO'], sort=True)[list(needed[2:])]
        .sum()
        .sort_index()
    )


def main() -> None:
    state_path = etl.STATE
    part_path = etl.PARTS / f'{KEY}.csv'
    if not state_path.is_file() or not part_path.is_file():
        raise FileNotFoundError(
            f'Thieu state hoac parts. State: {state_path}; parts: {part_path}'
        )

    state = json.loads(state_path.read_text(encoding='utf-8'))
    meta = state.get('months', {}).get(KEY)
    if not isinstance(meta, dict):
        raise ValueError(f'Khong co metadata {KEY} trong state.json')
    if meta.get('rows') is not None:
        print(f'{KEY} da co rows = {meta["rows"]}, khong can khoi phuc.')
        return

    original_routes = _routes_for_comparison(etl.read_csv(part_path))
    original_seats = int(round(original_routes['ASSENTOS'].sum()))
    if original_seats != EXPECTED_SEATS:
        raise ValueError(
            'Tong ghe trong parts khong khop CSV tong hop: '
            f'{original_seats} != {EXPECTED_SEATS}. Chua thay doi gi.'
        )
    stored_seats = meta.get('seats')
    if stored_seats is not None and int(round(float(stored_seats))) != original_seats:
        raise ValueError('Tong ghe trong state khac parts; chua thay doi gi.')

    print('Dang tim file 2025-01 tren danh muc ANAC...')
    sess = etl.session()
    links = etl.index_files(sess, 'domestic', 2025)
    source_url = links.get(YEAR_MONTH)
    if not source_url:
        raise ValueError('ANAC chua tra ve file noi dia 2025-01; chua thay doi gi.')

    with tempfile.TemporaryDirectory(prefix='anac_recover_') as temp:
        source = Path(temp) / 'anac_2025_01.csv'
        print('Dang tai va kiem tra duy nhat file domestic_2025-01...')
        downloaded_sha = etl.download(sess, source_url, source)
        stored_sha = meta.get('sha256')
        if stored_sha and stored_sha.lower() != downloaded_sha.lower():
            raise ValueError(
                'ANAC da thay doi noi dung nguon (SHA256 khac state). '
                'Khong the gan so ban ghi moi cho du lieu cu; chua thay doi gi.'
            )

        new_routes, info = etl.read_chunks(source, YEAR_MONTH, 'domestic')

    new_aggregates = _routes_for_comparison(new_routes)
    if not original_routes.index.equals(new_aggregates.index):
        raise ValueError('Tap tuyen bay khac parts hien tai; chua thay doi gi.')
    for field in ('ASSENTOS', 'GHE_CO_GIA', 'GIA_NHAN_GHE'):
        before = original_routes[field].to_numpy(dtype='float64')
        after = new_aggregates[field].to_numpy(dtype='float64')
        if not np.allclose(before, after, rtol=1e-10, atol=0.01, equal_nan=False):
            raise ValueError(f'So lieu {field} khac parts hien tai; chua thay doi gi.')

    rows = int(info['rows'])
    if rows <= 0 or int(round(info['seats'])) != original_seats:
        raise ValueError('So ban ghi hoac so ghe khong hop le; chua thay doi gi.')
    print(f'DOI CHIEU KHOP: {len(original_routes)} tuyen; {original_seats:,} ghe')
    print(f'SO BAN GHI NGUON HOP LE: {rows:,}')

    # Keep the state exactly as it currently is except for the verified count.
    backup = state_path.with_name(
        'state_backup_before_recover_2025_01_'
        + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
        + '.json'
    )
    shutil.copy2(state_path, backup)
    meta['rows'] = rows
    staged = state_path.with_name('state_recover_tmp.json')
    try:
        with staged.open('w', encoding='utf-8', newline='\n') as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(staged, state_path)
    finally:
        staged.unlink(missing_ok=True)
    print('DA CAP NHAT state.json (chi rows cua domestic_2025-01).')
    print('DA SAO LUU:', backup)
    print('Chua thay doi CSV tong hop hay DuckDB.')


if __name__ == '__main__':
    main()
