"""ANAC Boxplot: incrementally build real seat-weighted fare quantiles for 2025+.

Uses ANAC raw URLs and SHA-256 already validated by the main ETL in
DuLieu_DaXuLy/_tu_dong/state.json. Downloads ONLY missing/revised months,
processes each file in chunks, and saves only 5 percentiles + coverage.

Run from project root:
    python data_warehouse/cap_nhat_phan_phoi_gia.py --check
    python data_warehouse/cap_nhat_phan_phoi_gia.py --limit 2
    python data_warehouse/cap_nhat_phan_phoi_gia.py --all

Requires existing data_warehouse/fare_distribution_by_month.csv from 2024.
Does NOT change state.json, monthly ETL parts, .duckdb, or 2024 quantiles.
"""
from __future__ import annotations

import argparse
import time
import hashlib
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

import requests

import pandas as pd
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
DW = Path(__file__).resolve().parent
STATE_PATH = PROJECT / 'DuLieu_DaXuLy' / '_tu_dong' / 'state.json'
PARTS = PROJECT / 'DuLieu_DaXuLy' / '_tu_dong' / 'parts'
OUTPUT = DW / 'fare_distribution_by_month.csv'
SYNC_PATH = DW / 'fare_distribution_sync.json'
CACHE_DIR = DW / '_boxplot_download_cache'  # cached partial public ANAC files; safe to delete when stopped

# The main ETL already implements network retry, safe streaming and checksums.
sys.path.insert(0, str(PROJECT))
from cap_nhat_anac import session, index_files, read_chunks, read_csv  # noqa: E402
from data_warehouse.build_fare_distributions import accumulate, weighted_quantile  # noqa: E402

PERIOD_FILE = re.compile(r'^(domestic|international)_(20\d\d-(?:0[1-9]|1[0-2]))$')
REQUIRED = ('THANG', 'market_code', 'currency_code', 'p10', 'q1', 'median', 'q3', 'p90', 'priced_seats', 'method')


def check_url(url: str, market: str, period: str) -> None:
    """Reject sources outside the original ANAC raw-data namespace."""
    u = urlsplit(url)
    folder = 'tarifadomestica' if market == 'domestic' else 'tarifainternacional'
    if u.scheme != 'https' or u.hostname != 'sas.anac.gov.br' or u.port not in (None, 443) or u.username or u.password:
        raise ValueError(f'Nguon URL khong phai ANAC HTTPS cho {market}_{period}')
    if not u.path.startswith('/sas/' + folder + '/' + period[:4] + '/') or not u.path.lower().endswith(('.csv', '.txt')):
        raise ValueError(f'URL sai thu muc/thang nguon: {market}_{period}')
    if u.query or u.fragment:
        raise ValueError('URL khong duoc chua tham so truy van')


def read_source() -> dict:
    if not STATE_PATH.is_file():
        raise FileNotFoundError(f'Khong tim thay state.json: {STATE_PATH}')
    state = json.loads(STATE_PATH.read_text(encoding='utf-8'))
    months = state.get('months', {})
    if not isinstance(months, dict) or not months:
        raise ValueError('state.json khong co danh sach thang hop le')
    return months


def read_table() -> pd.DataFrame:
    if not OUTPUT.is_file():
        raise FileNotFoundError(
            f'Chua co {OUTPUT.name}. Hay tao du lieu 2024 truoc bang: '
            'python data_warehouse/build_fare_distributions.py --clean-dir ".../Dulieusach"'
        )
    d = pd.read_csv(OUTPUT, encoding='utf-8-sig', dtype={'THANG': 'string', 'market_code': 'string'})
    if not set(REQUIRED).issubset(d.columns):
        raise ValueError('CSV phan phoi gia thieu cot can thiet')
    if d.duplicated(['THANG', 'market_code']).any():
        raise ValueError('CSV phan phoi gia trung khoa (THANG, market_code)')
    if not (d['THANG'].astype(str).str.startswith('2024').any()):
        raise ValueError('CSV khong con du lieu nen 2024; dung lai de bao ve du lieu cu')
    return d


def read_sync() -> dict:
    if not SYNC_PATH.is_file():
        return {}
    value = json.loads(SYNC_PATH.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('fare_distribution_sync.json khong hop le')
    return value


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def valid_sha(value) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r'[a-fA-F0-9]{64}', value))


def planned(months: dict, table: pd.DataFrame, sync: dict) -> tuple[list, list]:
    """Missing historical SHA/URL is pending, NOT a reason to abort --check.

    For those months, apply validates the freshly downloaded file against
    the actual saved ETL per-route aggregates before publishing anything.
    """
    pending, unchanged = [], []
    for key, meta in sorted(months.items()):
        match = PERIOD_FILE.fullmatch(key)
        if not match or int(match.group(2)[:4]) < 2025:
            continue
        market, period = match.groups()
        if not isinstance(meta, dict):
            raise ValueError(f'Metadata sai dang: {key}')
        sha, url = meta.get('sha256'), meta.get('url')
        if sha is not None and not valid_sha(sha):
            raise ValueError(f'SHA-256 sai dinh dang trong state.json: {key}')
        if url is not None:
            if not isinstance(url, str) or not url:
                raise ValueError(f'URL rong/sai dinh dang: {key}')
            check_url(url, market, period)
        have = bool(((table['THANG'].astype(str) == period) & (table['market_code'].astype(str) == market)).any())
        last = sync.get(key, {})
        part = PARTS / (key + '.csv')
        if have and isinstance(last, dict):
            if valid_sha(sha) and last.get('sha256', '').lower() == sha.lower():
                unchanged.append(key)
                continue
            # Historical month without SHA: only trust sync if it was verified
            # against the actual saved parts AND those parts have not changed.
            if (sha is None and last.get('verified_against_parts') is True
                    and valid_sha(last.get('part_sha256')) and part.is_file()
                    and last['part_sha256'].lower() == file_sha256(part)):
                unchanged.append(key)
                continue
        pending.append((key, market, period, meta))
    return pending, unchanged


def _route_summary(frame: pd.DataFrame) -> pd.DataFrame:
    required = ['ORIGEM', 'DESTINO', 'ASSENTOS', 'GIA_NHAN_GHE', 'GHE_CO_GIA']
    if not set(required).issubset(frame.columns):
        raise ValueError('Bang ETL thieu cot so sanh tuyen')
    d = frame[required].copy()
    for col in required[:2]:
        if d[col].isna().any():
            raise ValueError(f'Thieu ma san bay {col} khi doi chieu')
        d[col] = d[col].astype(str).str.strip().str.upper()
    for col in required[2:]:
        d[col] = pd.to_numeric(d[col], errors='raise')
    return d.groupby(['ORIGEM','DESTINO'], sort=True)[required[2:]].sum().sort_index()


def verify_source_against_parts(raw: Path, key: str, market: str, period: str, meta: dict) -> str:
    """Missing checksum fallback: compare raw source against ETL route aggregates.

    For a historical file, this is stronger than checking seats alone. No
    writes to state, parts, baseline, CSV summaries or DuckDB.
    """
    part = PARTS / (key + '.csv')
    if not part.is_file():
        raise FileNotFoundError(f'Thieu ETL parts de doi chieu: {part}')
    saved = _route_summary(read_csv(part))
    recomputed_routes, info = read_chunks(raw, period, market)
    recomputed = _route_summary(recomputed_routes)
    if not saved.index.equals(recomputed.index):
        raise ValueError(f'Khong khop danh sach tuyen bay {key}; khong ghi Boxplot')
    for col in ('ASSENTOS','GHE_CO_GIA','GIA_NHAN_GHE'):
        old = saved[col].to_numpy(dtype='float64')
        new = recomputed[col].to_numpy(dtype='float64')
        if not np.allclose(old,new,rtol=1e-10,atol=0.01,equal_nan=False):
            raise ValueError(f'Khong khop {col} theo tuyen {key}; khong ghi Boxplot')
    for item, field in (('seats', 'seats'), ('fare_seats', 'fare_seats'), ('rows','rows')):
        expected = meta.get(item)
        if expected is not None and abs(float(expected) - float(info[field])) > 0.5:
            raise ValueError(f'Khong khop {item} voi state.json cho {key}; khong ghi Boxplot')
    print(f'DOI CHIEU PARTS KHOP: {key} | {len(saved)} tuyen | {int(info["seats"]):,} ghe',flush=True)
    return file_sha256(part)


def resolve_anac_url(sess, meta: dict, market: str, period: str) -> str:
    url = meta.get('url')
    if not url:
        # Some older state.json entries contain only ETL metrics, no source URL.
        files = index_files(sess, market, int(period[:4]))
        url = files.get(period)
        if not url:
            raise ValueError(f'Khong tim thay URL ANAC cho {market}_{period}')
    check_url(url,market,period)
    return url


def summarize_month(path: Path, market: str, period: str, meta: dict) -> dict:
    agg = defaultdict(lambda: defaultdict(int))
    accumulate(path, market, agg, 'raw', period)
    counts = agg.get((period, market), {})
    if not counts:
        raise ValueError(f'Khong co gia ve hop le: {market}_{period}')
    priced_seats = int(sum(counts.values()))
    expected = meta.get('fare_seats')
    if expected is None:
        raise ValueError(f'State chua co fare_seats: {market}_{period}')
    if abs(float(expected) - priced_seats) > 0.5:
        raise ValueError(
            f'KHONG KHOP ghe co gia {market}_{period}: ANAC={priced_seats:,}, '
            f'ETL state={float(expected):,.0f}. Chua ghi ket qua.'
        )
    p10, q1, median, q3, p90 = weighted_quantile(counts, [0.10, 0.25, 0.50, 0.75, 0.90])
    if not (p10 <= q1 <= median <= q3 <= p90):
        raise ValueError(f'Phan vi khong tang dan: {market}_{period}')
    return {
        'THANG': period, 'market_code': market,
        'currency_code': 'BRL' if market == 'domestic' else 'USD',
        'p10': p10, 'q1': q1, 'median': median, 'q3': q3, 'p90': p90,
        'priced_seats': priced_seats,
        'method': 'discrete_quantile_weighted_by_sold_seats',
    }


def atomic_save(table: pd.DataFrame, sync: dict) -> None:
    # 2024 baseline is retained verbatim in-memory; no unrelated row is dropped.
    if table.duplicated(['THANG', 'market_code']).any():
        raise ValueError('Phan phoi gia bi trung thang/thi truong')
    table = table.sort_values(['THANG', 'market_code']).reset_index(drop=True)
    tmp_csv = OUTPUT.with_suffix('.staging.csv')
    tmp_sync = SYNC_PATH.with_suffix('.staging.json')
    try:
        table.to_csv(tmp_csv, index=False, encoding='utf-8-sig')
        tmp_sync.write_text(json.dumps(sync, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # Write CSV first: if interrupted, next run safely redoes missing sync.
        tmp_csv.replace(OUTPUT)
        tmp_sync.replace(SYNC_PATH)
    finally:
        tmp_csv.unlink(missing_ok=True)
        tmp_sync.unlink(missing_ok=True)



def resilient_download(sess, url: str, key: str, *, max_attempts: int = 5,
                       max_bytes: int = 600_000_000) -> tuple[Path, str]:
    """Download ANAC data, resume interrupted HTTPS transfers when Range is supported.

    A partial file is never used for analysis. It is retained only so a later
    run can continue downloading. If the server ignores Range, restart safely.
    """
    # URL has already passed check_url before calling this method.
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url_tag = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    partial = CACHE_DIR / f'{key}_{url_tag}.part'
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        offset = partial.stat().st_size if partial.is_file() else 0
        if offset > max_bytes:
            partial.unlink(missing_ok=True)
            raise ValueError(f'Raw file exceeds maximum size: {key}')
        headers = {'Accept-Encoding': 'identity'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
        try:
            with sess.get(url, headers=headers, stream=True, timeout=(20, 120)) as resp:
                # Some HTTP servers do not support Range: a 200 response is a
                # full copy, not a continuation. Truncate partial explicitly.
                if resp.status_code == 416 and offset:
                    partial.unlink(missing_ok=True)
                    raise requests.ConnectionError('Range not satisfiable; retry from start')
                resp.raise_for_status()
                if resp.status_code not in (200, 206):
                    raise ValueError(f'Unexpected ANAC HTTP status {resp.status_code}')
                if 'text/html' in resp.headers.get('Content-Type', '').lower():
                    raise ValueError('ANAC returned HTML instead of CSV')
                if resp.status_code == 206:
                    if not offset:
                        raise ValueError('Unexpected partial HTTP response without Range request')
                    cr = resp.headers.get('Content-Range', '')
                    if not cr.startswith(f'bytes {offset}-'):
                        partial.unlink(missing_ok=True)
                        raise requests.ConnectionError('Invalid Content-Range; restart from 0')
                    mode = 'ab'
                else:
                    mode = 'wb'
                    offset = 0
                expected_tail = resp.headers.get('Content-Length')
                remaining = int(expected_tail) if expected_tail and expected_tail.isdigit() else None
                received = 0
                with partial.open(mode) as out:
                    for block in resp.iter_content(chunk_size=512 * 1024):
                        if not block:
                            continue
                        received += len(block)
                        if offset + received > max_bytes:
                            raise ValueError(f'Raw file exceeds {max_bytes} bytes: {key}')
                        out.write(block)
                if remaining is not None and received != remaining:
                    raise requests.ConnectionError(
                        f'Incomplete HTTP body: expected {remaining}, received {received}')
            if partial.stat().st_size < 40:
                raise ValueError(f'ANAC returned an empty or very small file: {key}')
            with partial.open('rb') as probe:
                if probe.read(128).lstrip().lower().startswith((b'<html', b'<!doctype')):
                    raise ValueError(f'ANAC returned HTML instead of CSV: {key}')
            checksum = file_sha256(partial)
            print('TAI HOAN TAT:', key, '| bytes:', f'{partial.stat().st_size:,}', flush=True)
            return partial, checksum
        except (requests.RequestException, OSError) as exc:
            if attempt >= attempts:
                raise RuntimeError(
                    f'Khong tai xong {key} sau {attempts} lan. '
                    f'Co the thu lai sau; file .part da luu de tiep tuc: {partial}. '
                    f'Loi cuoi: {exc}') from exc
            wait = min(2 ** (attempt - 1), 8)
            print(f'KET NOI BI NGAT: {key}, lan {attempt}/{attempts}. '
                  f'Da tai {partial.stat().st_size if partial.exists() else 0:,} bytes; '
                  f'thu lai sau {wait}s.', flush=True)
            time.sleep(wait)
    raise RuntimeError('Unreachable download retry state')


def apply_one(raw: Path, key: str, market: str, period: str, meta: dict,
              table: pd.DataFrame, sync: dict, *, downloaded_sha: str | None = None,
              part_sha256: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Compute, validate, then atomically publish one month. No network here."""
    row = summarize_month(raw, market, period, meta)
    kept = table.loc[~((table['THANG'].astype(str) == period) & (table['market_code'].astype(str) == market))]
    new = pd.concat([kept, pd.DataFrame([row])], ignore_index=True)
    checksum = downloaded_sha or meta.get('sha256')
    if not valid_sha(checksum):
        raise ValueError(f'Chua xac minh duoc SHA-256 nguon: {key}')
    provenance = {'sha256': checksum.lower(), 'priced_seats': row['priced_seats']}
    if part_sha256:
        provenance.update({'verified_against_parts': True, 'part_sha256': part_sha256})
    updated = {**sync, key: provenance}
    atomic_save(new, updated)
    return new, updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Chi kiem tra tien do; khong tai/ghi file')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--all', action='store_true', help='Xu ly toan bo thang con thieu; nhieu GB du lieu')
    group.add_argument('--limit', type=int, default=2, help='So file ANAC goc toi da moi lan (mac dinh 2)')
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit phai >= 1')

    table = read_table()
    months = read_source()
    sync = read_sync()
    pending, unchanged = planned(months, table, sync)
    total = len(pending) + len(unchanged)
    print('=== CAP NHAT BOXPLOT ANAC 2025+ ===')
    print('Tong thang 2025+ tu ETL:', total)
    print('Da dong bo, khong can tai lai:', len(unchanged))
    print('Chua co / can tinh lai:', len(pending))
    if args.check:
        missing_sha = [key for key, market, period, meta in pending if meta.get('sha256') is None]
        if missing_sha:
            print('CAN DOI CHIEU PARTS DO THIEU SHA:', ', '.join(missing_sha[:8]))
        if pending:
            print('Vi du thang chua co:', ', '.join(x[0] for x in pending[:8]))
        print('CHECK ONLY: khong thay doi CSV, state hay DuckDB')
        return
    if not pending:
        print('DA DAY DU: khong can tai lai du lieu')
        return

    batch = pending if args.all else pending[:args.limit]
    succeeded, errors = 0, []
    sess = session()
    try:
        for key, market, period, meta in batch:
            print('DANG TAI ANAC GOC:', key, flush=True)
            try:
                source_url = resolve_anac_url(sess, meta, market, period)
                path, received = resilient_download(sess, source_url, key)
                known_sha = meta.get('sha256')
                verified_part_sha = None
                if valid_sha(known_sha):
                    if received.lower() != known_sha.lower():
                        path.unlink(missing_ok=True)
                        raise ValueError(
                            f'SHA-256 thay doi ({key}). File ANAC co the da duoc sua. '
                            'Hay cap nhat ETL truoc, sau do chay lai Boxplot.'
                        )
                else:
                    print('THIEU SHA CU: Doi chieu du lieu goc voi ETL parts cua',key,flush=True)
                    verified_part_sha = verify_source_against_parts(path,key,market,period,meta)
                table, sync = apply_one(
                    path, key, market, period, meta, table, sync,
                    downloaded_sha=received, part_sha256=verified_part_sha
                )
                # Do not retain completed raw source after verified and saved.
                path.unlink(missing_ok=True)
                succeeded += 1
                print('DA LUU:', key, '| ghe co gia:', sync[key]['priced_seats'], flush=True)
            except Exception as exc:
                errors.append(f'{key}: {exc}')
                print('LOI:', errors[-1], flush=True)
    finally:
        sess.close()
    print('HOAN TAT:', succeeded, 'thang | con lai trong lan kiem tra ban dau:', len(pending) - succeeded)
    print('Dau ra:', OUTPUT)
    if errors:
        raise RuntimeError('Co thang chua the xu ly; cac thang thanh cong da duoc luu. ' + ' | '.join(errors))


if __name__ == '__main__':
    main()
