"""Offline data-quality checks for published ANAC dashboard aggregates.

Run from project root: python kiem_tra_chat_luong.py
No network access and no modifications to datasets.
"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'DuLieu_DaXuLy'
FILES = {
    'monthly': 'tong_hop_theo_thang_2024.csv',
    'domestic': 'top100_noi_dia_toa_do.csv',
    'international': 'top100_quoc_te_toa_do.csv',
}

def main():
    errors, warnings = [], []
    tables = {}
    for kind, name in FILES.items():
        path = DATA / name
        if not path.is_file():
            errors.append(f'Thieu file: {path}')
            continue
        df = pd.read_csv(path, encoding='utf-8-sig', low_memory=False)
        tables[kind] = df
        print(f'{kind}: {len(df):,} dong | {len(df.columns)} cot')
    if errors:
        for err in errors:
            print('FAIL:', err)
        return 1

    monthly = tables['monthly']
    required = {'THANG', 'LOAI_CHUYEN_BAY', 'SO_GHE_BAN', 'GIA_BINH_QUAN'}
    missing = required - set(monthly)
    if missing:
        errors.append(f'Monthly thieu cot: {sorted(missing)}')
    else:
        months = monthly['THANG'].astype(str).str.strip()
        markets = monthly['LOAI_CHUYEN_BAY'].astype(str).str.strip()
        if monthly.assign(_month=months, _market=markets).duplicated(['_month','_market']).any():
            errors.append('Trung khoa THANG + LOAI_CHUYEN_BAY')
        if (~months.str.fullmatch(r'20\d\d-(0[1-9]|1[0-2])')).any():
            errors.append('Co thang sai dinh dang YYYY-MM')
        for market in ['Noi dia','Quoc te']:
            got = set(months[markets.eq(market)])
            missing_2024 = {f'2024-{m:02d}' for m in range(1,13)} - got
            if missing_2024:
                errors.append(f'{market} thieu thang 2024: {sorted(missing_2024)}')
        for col in ['SO_GHE_BAN','GIA_BINH_QUAN']:
            vals = pd.to_numeric(monthly[col],errors='coerce')
            if vals.isna().any() or (vals <= 0).any():
                errors.append(f'{col} co gia tri thieu / khong duong')
        print('Monthly: ', months.min(), '->', months.max())

    for kind in ('domestic','international'):
        df = tables[kind]
        for col in ['ORIGEM','DESTINO','ASSENTOS','LAT_DI','LON_DI','LAT_DEN','LON_DEN']:
            if col not in df:
                errors.append(f'{kind} thieu cot {col}')
        if 'ASSENTOS' in df:
            seats = pd.to_numeric(df['ASSENTOS'],errors='coerce')
            if seats.isna().any() or (seats <= 0).any():
                errors.append(f'{kind}: ASSENTOS thieu / khong duong')
        for lat, lon in [('LAT_DI','LON_DI'),('LAT_DEN','LON_DEN')]:
            if lat in df and lon in df:
                a = pd.to_numeric(df[lat],errors='coerce')
                b = pd.to_numeric(df[lon],errors='coerce')
                invalid = a.isna() | b.isna() | ~a.between(-90,90) | ~b.between(-180,180)
                if invalid.any():
                    errors.append(f'{kind}: {invalid.sum()} dong toa do thieu / ngoai pham vi')
        if {'NAM','ORIGEM','DESTINO'}.issubset(df.columns):
            duplicates = df.duplicated(['NAM','ORIGEM','DESTINO']).sum()
            if duplicates:
                errors.append(f'{kind}: {duplicates} khoa NAM-ORIGEM-DESTINO trung')
        else:
            warnings.append(f'{kind}: chua du cot de kiem tra khoa tuyen theo nam')

    for warn in warnings:
        print('WARN:', warn)
    for err in errors:
        print('FAIL:', err)
    if errors:
        print(f'KET QUA: FAIL ({len(errors)} loi)')
        return 1
    print('KET QUA: PASS - cac kiem tra co ban')
    print('Luu y: PASS khong dong nghia voi du lieu dung het ve nghiep vu.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
