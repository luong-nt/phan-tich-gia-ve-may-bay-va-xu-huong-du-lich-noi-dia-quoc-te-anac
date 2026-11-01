from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'KetQua_ETL_2024'
DATA_SACH = ROOT / 'Dulieusach'
AIRPORTS = ROOT / 'DuLieu_SanBay' / 'airports.csv'
DATA.mkdir(exist_ok=True)

def read_chunks(path):
    with path.open('r', encoding='utf-8-sig') as f:
        h = f.readline()
    sep = ';' if h.count(';') > h.count(',') else ','
    return pd.read_csv(path, sep=sep, encoding='utf-8-sig', usecols=['THANG','ORIGEM','DESTINO','ASSENTOS'], chunksize=200_000, low_memory=False)

print('Đang đọc danh mục sân bay...')
air = pd.read_csv(AIRPORTS, usecols=['ident','name','municipality','iso_country','latitude_deg','longitude_deg'], encoding='utf-8-sig', dtype={'ident':'string','iso_country':'string'}, low_memory=False)
air['ident'] = air['ident'].str.strip().str.upper()
air = air.dropna(subset=['ident']).drop_duplicates('ident')
lookup = air.set_index('ident')
country = lookup['iso_country'].to_dict()

# SPJC may not exist in the latest airport catalog, but is Lima, Peru.
country.setdefault('SPJC','PE')
extra = pd.DataFrame([{'ident':'SPJC','name':'Jorge Chavez International Airport','municipality':'Lima','iso_country':'PE','latitude_deg':-12.0219,'longitude_deg':-77.1143}])
if 'SPJC' not in set(air['ident']):
    air = pd.concat([air,extra], ignore_index=True)

results = []
for market, filename in [('Nội địa','noi_dia_sach_2024.csv'),('Quốc tế','quoc_te_sach_2024.csv')]:
    print('\nĐang tổng hợp:',market)
    partial = []
    examined = eligible = 0
    for chunk in read_chunks(DATA_SACH / filename):
        examined += len(chunk)
        for c in ('ORIGEM','DESTINO'):
            chunk[c] = chunk[c].astype('string').str.strip().str.upper()
        chunk['ASSENTOS'] = pd.to_numeric(chunk['ASSENTOS'], errors='coerce')
        chunk = chunk.dropna(subset=['ORIGEM','DESTINO','THANG','ASSENTOS'])
        chunk = chunk[chunk['ASSENTOS'] > 0].copy()
        origin_country = chunk['ORIGEM'].map(country)
        dest_country = chunk['DESTINO'].map(country)
        if market == 'Nội địa':
            mask = origin_country.eq('BR') & dest_country.eq('BR')
        else:
            # Outbound only: Brazil -> another country; exclude returns/inbound.
            mask = origin_country.eq('BR') & dest_country.notna() & dest_country.ne('BR')
        chunk = chunk.loc[mask.fillna(False)]
        eligible += len(chunk)
        if len(chunk):
            partial.append(chunk.groupby(['THANG','DESTINO'], observed=True)['ASSENTOS'].sum())
    if not partial:
        print('Không có bản ghi đạt điều kiện:', market)
        continue
    df = pd.concat(partial).groupby(level=[0,1]).sum().reset_index()
    df['LOAI'] = market
    results.append(df)
    print(f'Đã đọc {examined:,} bản ghi; chọn {eligible:,} bản ghi có hướng đi phù hợp.')

if not results:
    raise ValueError('Không tạo được dữ liệu điểm đến, kiểm tra mã sân bay trong OurAirports.')

out = pd.concat(results, ignore_index=True)
air = air.rename(columns={'ident':'DESTINO','name':'TEN_SAN_BAY','municipality':'THANH_PHO','iso_country':'QUOC_GIA','latitude_deg':'LAT','longitude_deg':'LON'})
out = out.merge(air[['DESTINO','TEN_SAN_BAY','THANH_PHO','QUOC_GIA','LAT','LON']], on='DESTINO', how='left', validate='many_to_one')
out['DIA_DIEM'] = out['THANH_PHO'].fillna(out['TEN_SAN_BAY']).fillna(out['DESTINO'])
out = out.sort_values(['LOAI','THANG','ASSENTOS'], ascending=[True,True,False])
outfile = DATA / 'xu_huong_diem_den_2024.csv'
out.to_csv(outfile, index=False, encoding='utf-8-sig')
print('\nĐÃ LƯU:', outfile)
print('Số dòng tổng hợp:',len(out))
print('Số điểm đến theo từng thị trường:')
print(out.groupby('LOAI')['DESTINO'].nunique().to_string())
print('Thiếu tọa độ:',out[['LAT','LON']].isna().any(axis=1).sum())
