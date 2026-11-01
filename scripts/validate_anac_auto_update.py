"""Fail CI if the ETL state, monthly parts and Boxplot summaries disagree.

No network or writes. Invoke from the repository root:
    python scripts/validate_anac_auto_update.py

This deliberately checks 2024 baseline and ALL recorded 2025+ periods.
If your repository misses fare_distribution_sync.json, copy it from your
already completed 32/32 local Boxplot project BEFORE the first Git push.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'DuLieu_DaXuLy'
DW = ROOT / 'data_warehouse'
MARKETS = {'domestic': 'BRL', 'international': 'USD'}
REQUIRED_CSV = (
    'tong_hop_theo_thang_2024.csv',
    'top100_noi_dia_toa_do.csv',
    'top100_quoc_te_toa_do.csv',
    'xu_huong_diem_den_2024.csv',
)
DISTRIBUTION_COLUMNS = (
    'THANG', 'market_code', 'currency_code', 'p10', 'q1', 'median',
    'q3', 'p90', 'priced_seats', 'method',
)


def die(message: str) -> None:
    raise ValueError('ANAC CI DATA CHECK FAILED: ' + message)


def number(value: object, title: str) -> float:
    try:
        v = float(value)
    except (ValueError, TypeError):
        die(f'{title} is not numeric')
    if not math.isfinite(v) or v < 0:
        die(f'{title} must be finite and nonnegative')
    return v


def check(root: Path = ROOT) -> tuple[int, int]:
    data = root / 'DuLieu_DaXuLy'
    warehouse = root / 'data_warehouse'
    for name in REQUIRED_CSV:
        file = data / name
        if not file.is_file() or file.stat().st_size < 50:
            die(f'missing/empty dashboard CSV: {file}')
    state_file = data / '_tu_dong' / 'state.json'
    sync_file = warehouse / 'fare_distribution_sync.json'
    dist_file = warehouse / 'fare_distribution_by_month.csv'
    for p in (state_file, sync_file, dist_file):
        if not p.is_file():
            die(f'missing {p}. Include your 32/32 local Boxplot results in the initial commit.')
    state = json.loads(state_file.read_text(encoding='utf-8'))
    sync = json.loads(sync_file.read_text(encoding='utf-8'))
    months = state.get('months')
    if not isinstance(months, dict) or not months:
        die('state.json does not contain a months object')
    if not isinstance(sync, dict):
        die('fare_distribution_sync.json is not a dictionary')
    with dist_file.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not set(DISTRIBUTION_COLUMNS).issubset(reader.fieldnames or []):
            die('fare_distribution_by_month.csv is missing required columns')
        rows = list(reader)
    dist = {}
    for row in rows:
        period = row['THANG'].strip()
        market = row['market_code'].strip()
        if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', period) or market not in MARKETS:
            die(f'invalid distribution month/market: {period}/{market}')
        key = (period, market)
        if key in dist:
            die(f'duplicate fare distribution period: {key}')
        if row['currency_code'].strip() != MARKETS[market]:
            die(f'wrong currency in distribution: {key}')
        quantiles = [number(row[col], f'{key}/{col}') for col in ('p10','q1','median','q3','p90')]
        if quantiles != sorted(quantiles):
            die(f'quantile order is incorrect: {key}')
        seats = number(row['priced_seats'], f'{key}/priced_seats')
        if not seats.is_integer():
            die(f'priced seats are not integer: {key}')
        dist[key] = row
    baseline = {(f'2024-{m:02d}', market) for m in range(1,13) for market in MARKETS}
    if not baseline.issubset(dist):
        die('2024 Boxplot baseline is incomplete (expected 12 months per market)')
    current = set()
    for key, meta in months.items():
        match = re.fullmatch(r'(domestic|international)_(20\d{2}-(0[1-9]|1[0-2]))', key)
        if not match:
            die(f'invalid ETL state key: {key}')
        market, period = match.group(1), match.group(2)
        part = data / '_tu_dong' / 'parts' / (key + '.csv')
        if not part.is_file() or part.stat().st_size == 0:
            die(f'missing/empty ETL part: {part}')
        if int(period[:4]) < 2025:
            continue
        if not isinstance(meta, dict):
            die(f'invalid ETL state entry: {key}')
        current.add((period, market))
        if (period, market) not in dist:
            die(f'missing Boxplot CSV for ETL period: {key}')
        provenance = sync.get(key)
        if not isinstance(provenance, dict):
            die(f'missing Boxplot sync metadata: {key}')
        source_hash = provenance.get('sha256','')
        if not isinstance(source_hash,str) or not re.fullmatch(r'[0-9a-fA-F]{64}',source_hash):
            die(f'invalid Boxplot sync source hash: {key}')
        expected = number(meta.get('fare_seats'), f'{key}/state.fare_seats')
        actual = number(dist[(period,market)]['priced_seats'], f'{key}/priced_seats')
        recorded = number(provenance.get('priced_seats'), f'{key}/sync.priced_seats')
        if expected != actual or expected != recorded:
            die(f'Boxplot seat count does not equal ETL state: {key}: {expected}, {actual}, {recorded}')
        state_hash = meta.get('sha256')
        if state_hash is not None and (
            not isinstance(state_hash, str) or
            state_hash.lower() != source_hash.lower()
        ):
            die(f'Boxplot source SHA differs from ETL state: {key}')
        if state_hash is None:
            if provenance.get('verified_against_parts') is not True:
                die(f'missing ETL SHA and no verified-against-parts proof: {key}')
            old_part_hash = provenance.get('part_sha256', '')
            h = hashlib.sha256()
            with part.open('rb') as src:
                for block in iter(lambda: src.read(1024 * 1024), b''):
                    h.update(block)
            if h.hexdigest().lower() != str(old_part_hash).lower():
                die(f'ETL part checksum changed since Boxplot verification: {key}')
    extra = {k for k in dist if int(k[0][:4]) >= 2025} - current
    if extra:
        die(f'extraneous 2025+ distribution periods: {sorted(extra)}')
    print('PASS: ANAC ETL, 2024 baseline and Boxplot are consistent')
    print(f'2024 baseline periods: {len(baseline)} | ETL 2025+ periods: {len(current)} | Total Boxplot periods: {len(dist)}')
    return len(current), len(dist)


if __name__ == '__main__':
    try:
        check()
    except (OSError, ValueError, json.JSONDecodeError) as err:
        print('FAIL:', err, file=sys.stderr)
        raise SystemExit(1)
