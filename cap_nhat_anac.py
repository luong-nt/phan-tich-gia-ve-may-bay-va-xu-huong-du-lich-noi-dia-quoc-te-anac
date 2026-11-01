"""ETL ANAC: tự khám phá các CSV theo tháng, chỉ lưu số liệu tổng hợp.
Nguồn ANAC công khai; cấu trúc URL tham khảo từ thư viện flightsbr (IPEA).
Giữ nguyên dữ liệu nền 2024; bổ sung 2025 và các năm sau.

Chạy: python cap_nhat_anac.py --check        (chỉ liệt kê các tệp tìm được)
      python cap_nhat_anac.py                (tải và tổng hợp tối đa N tệp mới)
      python cap_nhat_anac.py --recheck-all  (kiểm tra thay đổi tất cả tháng)
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import re
import shutil
import tempfile
import unicodedata
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'DuLieu_DaXuLy'
AUT = DATA / '_tu_dong'
STATE = AUT / 'state.json'
PARTS = AUT / 'parts'
BASELINE = AUT / 'baseline_2024'
CONFIG = ROOT / 'nguon_anac.json'
OUTPUT = {
    'month': 'tong_hop_theo_thang_2024.csv',
    'domestic': 'top100_noi_dia_toa_do.csv',
    'international': 'top100_quoc_te_toa_do.csv',
    'dest': 'xu_huong_diem_den_2024.csv',
}
ROOT_URL = {
    'domestic': 'https://sas.anac.gov.br/sas/tarifadomestica/',
    'international': 'https://sas.anac.gov.br/sas/tarifainternacional/',
}
ALIASES = {
    'origin': ['ORIGEM', 'AEROPORTO_ORIGEM', 'ICAO_AERODROMO_ORIGEM', 'ICAO_ORIGEM', 'ICAO_AEROPORTO_ORIGEM', 'SG_ICAO_ORIGEM'],
    'destination': ['DESTINO', 'AEROPORTO_DESTINO', 'ICAO_AERODROMO_DESTINO', 'ICAO_DESTINO', 'ICAO_AEROPORTO_DESTINO', 'SG_ICAO_DESTINO'],
    'seats': ['ASSENTOS', 'ASSENTOS_COMERCIALIZADOS', 'QUANTIDADE_ASSENTOS', 'QTDE_ASSENTOS', 'QUANTIDADE_DE_ASSENTOS', 'NR_ASSENTOS'],
    'fare': ['TARIFA', 'VALOR_TARIFA', 'TARIFA_N', 'TARIFA_VOO', 'VALOR_DA_TARIFA', 'VALOR', 'PRECO', 'GIA_VE', 'NR_TARIFA'],
    'year': ['ANO', 'ANO_REFERENCIA', 'ANO_VENDA', 'NR_ANO_REFERENCIA'],
    'month': ['MES', 'MES_REFERENCIA', 'MES_VENDA', 'THANG', 'NR_MES_REFERENCIA'],
    'group': ['GRUPO', 'GRUPO_TARIFA', 'GRUPO_TARIFARIO', 'GRUPO_DA_TARIFA'],
}

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            value = dict(attrs).get('href')
            if value: self.links.append(value)

def normalize(s):
    s = unicodedata.normalize('NFD', str(s))
    s = ''.join(x for x in s if unicodedata.category(x) != 'Mn')
    return re.sub(r'[^A-Z0-9]+', '_', s.upper()).strip('_')

def col(cols, kind, required=True):
    have = {normalize(x): x for x in cols}
    for c in ALIASES[kind]:
        if normalize(c) in have: return have[normalize(c)]
    if required: raise ValueError(f'Không tìm thấy cột {kind}; cột hiện có: {list(cols)}')
    return None

def num(series):
    """Convert BRL decimal commas and US decimal points without destroying decimal points."""
    s = series.astype('string').str.strip().str.replace(r'[^\d,.\-]', '', regex=True)
    comma = s.str.contains(',', regex=False).fillna(False)
    dot = s.str.contains('.', regex=False).fillna(False)
    both = comma & dot
    # Choose the last of two separators as decimal separator.
    comma_decimal = both & (s.str.rfind(',') > s.str.rfind('.'))
    dot_decimal = both & ~comma_decimal
    s.loc[comma_decimal] = s.loc[comma_decimal].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    s.loc[dot_decimal] = s.loc[dot_decimal].str.replace(',', '', regex=False)
    s.loc[comma & ~dot] = s.loc[comma & ~dot].str.replace(',', '.', regex=False)
    return pd.to_numeric(s, errors='coerce')

def session():
    s = requests.Session()
    s.headers.update({'User-Agent':'Mozilla/5.0 (compatible; ANAC-student-ETL/2.0)',
                      'Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8'})
    retry = Retry(total=3, connect=3, read=2, backoff_factor=1.5, status_forcelist=[429,500,502,503,504])
    s.mount('https://', HTTPAdapter(max_retries=retry))
    return s

def index_files(sess, kind, year):
    url = ROOT_URL[kind] + f'{year}/'
    response = sess.get(url, timeout=35)
    response.raise_for_status()
    if '<html' not in response.text.lower() and '<a ' not in response.text.lower():
        raise ValueError(f'ANAC không trả về danh mục HTML: {url}')
    parser = Links(); parser.feed(response.text)
    found = {}
    for href in parser.links:
        name = urlsplit(href).path.rsplit('/',1)[-1]
        if kind == 'domestic':
            match = re.fullmatch(r'(\d{4})(\d{2})\.csv', name, re.I)
        else:
            match = re.fullmatch(r'Internacional_(\d{4})-(\d{2})\.(csv|txt)', name, re.I)
        if not match: continue
        yy, mm = int(match.group(1)), int(match.group(2))
        if yy != year or not 1 <= mm <= 12: continue
        u = urljoin(url, href)
        if urlsplit(u).hostname != 'sas.anac.gov.br': continue
        found[f'{year}-{mm:02d}'] = u
    return found

def download(sess, url, destination, max_bytes=600_000_000):
    if urlsplit(url).scheme != 'https': raise ValueError('Chỉ chấp nhận HTTPS')
    total = 0; sha = hashlib.sha256()
    with sess.get(url, stream=True, timeout=(20,120)) as r:
        r.raise_for_status()
        ct = r.headers.get('content-type','').lower()
        if 'text/html' in ct: raise ValueError('Nguồn trả về HTML, không phải CSV')
        with destination.open('wb') as f:
            for data in r.iter_content(chunk_size=1024*1024):
                if not data: continue
                total += len(data)
                if total > max_bytes: raise ValueError('Tệp nguồn vượt giới hạn 600 MB')
                sha.update(data); f.write(data)
    if total < 40 or destination.open('rb').read(120).lstrip().lower().startswith((b'<!doctype',b'<html')):
        raise ValueError('Tệp tải về rỗng hoặc không phải CSV')
    return sha.hexdigest()

def read_chunks(path, period, kind):
    with path.open('rb') as f:
        head = f.readline().decode('latin-1')
    sep = ';' if head.count(';') >= head.count(',') else ','
    # ANAC frequently uses Latin-1; use it for byte-safe text reading.
    reader = pd.read_csv(path, sep=sep, encoding='latin-1', dtype='string', chunksize=80000,
                         low_memory=False, on_bad_lines='error')
    route_parts=[]; month_seats=0.0; fare_weight=0.0; fare_seats=0.0; valid_rows=0
    for chunk in reader:
        if chunk.empty: continue
        origin=col(chunk.columns,'origin'); dest=col(chunk.columns,'destination')
        seats=col(chunk.columns,'seats'); fare=col(chunk.columns,'fare')
        yy=col(chunk.columns,'year',False); mm=col(chunk.columns,'month',False)
        gg=col(chunk.columns,'group',False)
        if yy is not None:
            mask=num(chunk[yy]).eq(int(period[:4])).fillna(False)
            chunk=chunk.loc[mask].copy()
        if mm is not None:
            mask=num(chunk[mm]).eq(int(period[5:])).fillna(False)
            chunk=chunk.loc[mask].copy()
        if gg is not None and int(period[:4]) >= 2026 and kind=='domestic':
            group=chunk[gg].astype('string').str.strip().str.upper()
            chunk=chunk[group.isin(['1','I','GRUPO I','GRUPO 1'])].copy()
        if chunk.empty: continue
        normalized = pd.DataFrame({
            'ORIGEM':chunk[origin].str.strip().str.upper(),
            'DESTINO':chunk[dest].str.strip().str.upper(),
            'ASSENTOS':num(chunk[seats]), 'TARIFA':num(chunk[fare])
        })
        normalized=normalized.dropna(subset=['ORIGEM','DESTINO','ASSENTOS'])
        normalized=normalized[normalized['ORIGEM'].str.fullmatch(r'[A-Z0-9]{4}',na=False) & normalized['DESTINO'].str.fullmatch(r'[A-Z0-9]{4}',na=False)]
        normalized=normalized[(normalized['ASSENTOS']>0)&(normalized['ASSENTOS']%1==0)]
        if normalized.empty: continue
        normalized['TARIFA_VALID']=normalized['TARIFA'].where(normalized['TARIFA']>0)
        normalized['GIA_NHAN_GHE']=normalized['TARIFA_VALID'].fillna(0)*normalized['ASSENTOS']
        normalized['GHE_CO_GIA']=normalized['ASSENTOS'].where(normalized['TARIFA_VALID'].notna(),0)
        part=normalized.groupby(['ORIGEM','DESTINO'], as_index=False).agg(
            ASSENTOS=('ASSENTOS','sum'), GIA_NHAN_GHE=('GIA_NHAN_GHE','sum'),
            GHE_CO_GIA=('GHE_CO_GIA','sum'))
        route_parts.append(part)
        month_seats += float(normalized['ASSENTOS'].sum())
        fare_weight += float(normalized['GIA_NHAN_GHE'].sum())
        fare_seats += float(normalized['GHE_CO_GIA'].sum())
        valid_rows += len(normalized)
    if not route_parts or month_seats<=0 or fare_seats<=0:
        raise ValueError(f'Không có dữ liệu ghế/giá hợp lệ cho {kind} {period}')
    routes=pd.concat(route_parts).groupby(['ORIGEM','DESTINO'],as_index=False)[['ASSENTOS','GIA_NHAN_GHE','GHE_CO_GIA']].sum()
    routes.insert(0,'THANG',period)
    routes.insert(1,'LOAI','Nội địa' if kind=='domestic' else 'Quốc tế')
    return routes, {'month':period, 'market':kind,'seats':month_seats,'fare_weight':fare_weight,'fare_seats':fare_seats,'rows':valid_rows}

def load_airports(sess, cfg, tempdir):
    cache=AUT/'airports.csv'
    if cache.exists():
        airports=pd.read_csv(cache,low_memory=False)
    else:
        target=tempdir/'airports.csv'
        download(sess, cfg['airports_url'],target,max_bytes=70_000_000)
        airports=pd.read_csv(target,low_memory=False)
        AUT.mkdir(parents=True,exist_ok=True)
        shutil.copy2(target,cache)
    cols=['ident','name','municipality','iso_country','latitude_deg','longitude_deg']
    for c in cols:
        if c not in airports: raise ValueError(f'OurAirports thiếu cột {c}')
    airports=airports[cols].rename(columns={'ident':'CODE','name':'NAME','municipality':'CITY','iso_country':'COUNTRY','latitude_deg':'LAT','longitude_deg':'LON'})
    airports['CODE']=airports['CODE'].astype('string').str.strip().str.upper()
    airports=airports.dropna(subset=['CODE']).drop_duplicates('CODE')
    airports['LAT']=pd.to_numeric(airports['LAT'],errors='coerce')
    airports['LON']=pd.to_numeric(airports['LON'],errors='coerce')
    if not airports['CODE'].eq('SPJC').any():
        airports=pd.concat([airports,pd.DataFrame([{'CODE':'SPJC','NAME':'Jorge Chávez International Airport','CITY':'Lima','COUNTRY':'PE','LAT':-12.0219,'LON':-77.1143}])],ignore_index=True)
    return airports

def read_csv(p):
    """Đọc CSV nội bộ theo đúng dấu phân cách ';' hoặc ','."""
    p = Path(p)
    with p.open('r', encoding='utf-8-sig') as f:
        header = f.readline()
    sep = ';' if header.count(';') > header.count(',') else ','
    df = pd.read_csv(p, sep=sep, encoding='utf-8-sig', low_memory=False)
    if len(df.columns) <= 1:
        raise ValueError(f'Không đọc đúng các cột CSV trong {p}. Kiểm tra dấu phân cách.')
    return df

def save_csv(p, df):
    p.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(p,index=False,encoding='utf-8-sig')

def build_combined(airports, state, staged):
    # Baseline: original 2024 CSV, preserved separately before the first publication.
    oldm=read_csv(BASELINE / OUTPUT['month'])
    oldd=read_csv(BASELINE / OUTPUT['dest'])
    oldr={mk:read_csv(BASELINE / OUTPUT[mk]) for mk in ('domestic','international')}
    if 'NAM' not in oldr['domestic']: oldr['domestic']['NAM']=2024
    if 'NAM' not in oldr['international']: oldr['international']['NAM']=2024
    months=[oldm]; destinations=[oldd]; route_years={mk:[oldr[mk]] for mk in oldr}
    pieces=[]
    for key, meta in state['months'].items():
        p=PARTS / (key+'.csv')
        if not p.exists(): raise FileNotFoundError(f'Thiếu bảng ETL tháng {p}')
        pieces.append(read_csv(p))
    if pieces:
        allroutes=pd.concat(pieces,ignore_index=True)
        parts_for_month=allroutes.groupby(['THANG','LOAI'],as_index=False)[['ASSENTOS','GIA_NHAN_GHE','GHE_CO_GIA']].sum()
        parts_for_month['LOAI_CHUYEN_BAY']=parts_for_month['LOAI'].map({'Nội địa':'Noi dia','Quốc tế':'Quoc te'})
        parts_for_month['SO_GHE_BAN']=parts_for_month['ASSENTOS']
        parts_for_month['GIA_BINH_QUAN']=parts_for_month['GIA_NHAN_GHE']/parts_for_month['GHE_CO_GIA']
        # Use processed valid-row counts recorded in state.json, never infer rows from seats.
        meta_rows = []
        for key, meta in state['months'].items():
            market, period = key.split('_', 1)
            market_label = {'domestic':'Noi dia', 'international':'Quoc te'}.get(market)
            if market_label is None:
                raise ValueError(f'Unknown market in state: {key}')
            meta_rows.append({'THANG': period, 'LOAI_CHUYEN_BAY': market_label,
                              'SO_BAN_GHI': meta.get('rows')})
        counts = pd.DataFrame(meta_rows)
        if counts.duplicated(['THANG','LOAI_CHUYEN_BAY']).any():
            raise ValueError('Duplicate monthly keys in ETL state')
        parts_for_month = parts_for_month.merge(counts, on=['THANG','LOAI_CHUYEN_BAY'], how='left', validate='one_to_one')
        parts_for_month['TIEN_TE'] = parts_for_month['LOAI_CHUYEN_BAY'].map({'Noi dia':'BRL','Quoc te':'USD'})
        months.append(parts_for_month[['THANG','LOAI_CHUYEN_BAY','SO_GHE_BAN','GIA_BINH_QUAN','SO_BAN_GHI','TIEN_TE']])
        # Route aggregates by year & type; keep full month route counts until ranking.
        allroutes['NAM']=allroutes['THANG'].str[:4].astype(int)
        yearly=allroutes.groupby(['NAM','LOAI','ORIGEM','DESTINO'],as_index=False)['ASSENTOS'].sum()
        ori=airports[['CODE','NAME','LAT','LON']].rename(columns={'CODE':'ORIGEM','NAME':'TEN_DI','LAT':'LAT_DI','LON':'LON_DI'})
        dst=airports[['CODE','NAME','LAT','LON']].rename(columns={'CODE':'DESTINO','NAME':'TEN_DEN','LAT':'LAT_DEN','LON':'LON_DEN'})
        yearly=yearly.merge(ori,on='ORIGEM',how='left',validate='many_to_one').merge(dst,on='DESTINO',how='left',validate='many_to_one')
        yearly=yearly.dropna(subset=['LAT_DI','LON_DI','LAT_DEN','LON_DEN'])
        for kind, label in (('domestic','Nội địa'),('international','Quốc tế')):
            selection=yearly[yearly['LOAI']==label].copy()
            selection=selection.sort_values('ASSENTOS',ascending=False).groupby('NAM',group_keys=False).head(100)
            route_years[kind].append(selection.drop(columns='LOAI'))
        # Destination counts depend on location; group routes with BR origin rules.
        cc=airports.set_index('CODE')['COUNTRY'].to_dict()
        oc=allroutes['ORIGEM'].map(cc)
        dc=allroutes['DESTINO'].map(cc)
        eligible=(allroutes['LOAI'].eq('Nội địa')&oc.eq('BR')&dc.eq('BR'))|(allroutes['LOAI'].eq('Quốc tế')&oc.eq('BR')&dc.notna()&dc.ne('BR'))
        newdest=allroutes.loc[eligible.fillna(False)].groupby(['THANG','DESTINO','LOAI'],as_index=False)['ASSENTOS'].sum()
        geo=airports.rename(columns={'CODE':'DESTINO','NAME':'TEN_SAN_BAY','CITY':'THANH_PHO','COUNTRY':'QUOC_GIA'})
        newdest=newdest.merge(geo[['DESTINO','TEN_SAN_BAY','THANH_PHO','QUOC_GIA','LAT','LON']],on='DESTINO',how='left',validate='many_to_one')
        newdest['DIA_DIEM']=newdest['THANH_PHO'].fillna(newdest['TEN_SAN_BAY']).fillna(newdest['DESTINO'])
        destinations.append(newdest)
    # Baseline 2024 may overlap automatic updates if source records include 2024: do not append duplicate baseline months.
    month_out=pd.concat(months,ignore_index=True).sort_values(['LOAI_CHUYEN_BAY','THANG'])
    month_out=month_out.drop_duplicates(['THANG','LOAI_CHUYEN_BAY'],keep='first')
    # Preserve all original 2024 metrics. Compute month-to-month price changes
    # for later periods only when the immediately preceding calendar month exists.
    if 'BIEN_DONG_GIA_PCT' not in month_out:
        month_out['BIEN_DONG_GIA_PCT'] = pd.NA
    month_out['THANG'] = month_out['THANG'].astype(str).str.strip()
    month_out['GIA_BINH_QUAN'] = pd.to_numeric(month_out['GIA_BINH_QUAN'], errors='coerce')
    for label, group in month_out.groupby('LOAI_CHUYEN_BAY'):
        group = group.sort_values('THANG')
        previous = group.set_index('THANG')['GIA_BINH_QUAN']
        for idx, record in group.iterrows():
            if record['THANG'].startswith('2024'):
                continue
            month = pd.Period(record['THANG'], freq='M')
            previous_key = str(month - 1)
            old_price = previous.get(previous_key)
            current_price = record['GIA_BINH_QUAN']
            if old_price is not None and pd.notna(old_price) and old_price > 0 and pd.notna(current_price):
                month_out.loc[idx, 'BIEN_DONG_GIA_PCT'] = (current_price / old_price - 1) * 100
    # Rows for newer periods may legitimately be unavailable for historic state files.
    month_out['SO_BAN_GHI'] = pd.to_numeric(month_out['SO_BAN_GHI'], errors='coerce').astype('Int64')
    if len(month_out.loc[month_out['THANG'].str.startswith('2024')]) != len(oldm):
        raise ValueError('Số kỳ năm 2024 thay đổi; dừng xuất dữ liệu')
    if month_out.duplicated(['THANG','LOAI_CHUYEN_BAY']).any():
        raise ValueError('Trùng khóa tháng và thị trường; dừng xuất dữ liệu')
    dest_out=pd.concat(destinations,ignore_index=True)
    dest_out=dest_out.drop_duplicates(['THANG','DESTINO','LOAI'], keep='first')
    for kind in ('domestic','international'):
        r=pd.concat(route_years[kind],ignore_index=True)
        r=r.drop_duplicates(['NAM','ORIGEM','DESTINO'], keep='first')
        save_csv(staged / OUTPUT[kind],r)
    save_csv(staged / OUTPUT['month'],month_out)
    save_csv(staged / OUTPUT['dest'],dest_out)
    if not month_out['THANG'].str.startswith('2024').any():
        raise ValueError('Mất dữ liệu gốc 2024; không xuất dữ liệu mới')
    return month_out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true',help='Chỉ xem link tệp đã xuất hiện')
    parser.add_argument('--recheck-all',action='store_true')
    parser.add_argument('--rebuild-only', action='store_true', help='Rebuild summary CSVs from existing state and parts, without network')
    args=parser.parse_args()
    if args.rebuild_only:
        if not STATE.exists():
            raise FileNotFoundError(f'Thiếu trạng thái ETL: {STATE}')
        state=json.loads(STATE.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            staged=Path(tmp)/'out'; staged.mkdir()
            # Read local airport cache. Do not access ANAC or modify state/parts.
            airport_cache=AUT/'airports.csv'
            if not airport_cache.exists():
                raise FileNotFoundError(f'Thiếu cache sân bay: {airport_cache}')
            airports=load_airports(None, {}, Path(tmp))
            result=build_combined(airports, state, staged)
            for fn in OUTPUT.values():
                if (staged/fn).stat().st_size < 50:
                    raise ValueError('Dữ liệu tổng hợp không đầy đủ: '+fn)
            for fn in OUTPUT.values():
                (staged/fn).replace(DATA/fn)
        print('TÁI TỔNG HỢP THÀNH CÔNG:', len(result), 'dòng; không tải dữ liệu mới.')
        return
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    year_start=int(cfg.get('start_new_year',2025))
    if year_start < 2025: raise ValueError('Năm tự động phải >=2025 để bảo toàn baseline 2024')
    sess=session(); today=date.today()
    discoveries={}; errors=[]
    for kind in ('domestic','international'):
        for year in range(year_start,today.year+1):
            try:
                files=index_files(sess,kind,year)
                for period,url in files.items():
                    if period > today.strftime('%Y-%m'): continue
                    discoveries[f'{kind}_{period}']=url
                print(f'{kind} {year}: tìm thấy {len(files)} tháng')
            except requests.exceptions.HTTPError as exc:
                # Thư mục của một năm chưa tồn tại: không ngăn cập nhật các nguồn khác.
                status = getattr(exc.response, 'status_code', None)
                if status == 404:
                    print(f'{kind} {year}: chưa có thư mục trên ANAC (404), bỏ qua')
                else:
                    errors.append(f'{kind} {year}: {exc}')
                    print('CẢNH BÁO:', errors[-1])
            except Exception as exc:
                errors.append(f'{kind} {year}: {exc}')
                print('CẢNH BÁO:', errors[-1])
    if args.check:
        for key,url in sorted(discoveries.items()):print(key,url)
        if errors: raise RuntimeError('Không thể truy cập đầy đủ danh mục nguồn ANAC: '+' | '.join(errors))
        return
    if not discoveries:
        raise RuntimeError('Không tìm được nguồn dữ liệu ANAC, giữ nguyên dashboard. '+' | '.join(errors))
    state=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'months':{}}
    known=state.setdefault('months',{})
    pending=[(k,u) for k,u in sorted(discoveries.items()) if k not in known]
    # To catch revisions, re-download recent months even if known.
    recent_months=int(cfg.get('recheck_recent_months',3))
    recent_periods=sorted({k.split('_',1)[1] for k in discoveries})[-recent_months:]
    for k,url in sorted(discoveries.items()):
        if k in known and (args.recheck_all or k.split('_',1)[1] in recent_periods):
            pending.append((k,url))
    pending=list(dict(pending).items())
    limit=int(cfg.get('max_files_per_run',12))
    pending=pending[:max(1,limit)]
    if not pending:
        print('Không có dữ liệu mới; dashboard được giữ nguyên.')
        return
    if not all((DATA / x).exists() for x in OUTPUT.values()):
        raise RuntimeError('Thiếu dữ liệu năm 2024. Hãy giữ nguyên 4 CSV cũ trên GitHub trước khi chạy ETL.')
    PARTS.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        temp=Path(tmp)
        airports=load_airports(sess,cfg,temp)
        updates=[]
        for key,url in pending:
            market,period=key.split('_',1)
            try:
                file=temp/(key+'.csv')
                digest=download(sess,url,file)
                if key in known and known[key].get('sha256')==digest:
                    print('Không đổi:',key);continue
                routes,info=read_chunks(file,period,market)
                target=PARTS/(key+'.csv')
                save_csv(target,routes)
                known[key]={**info,'sha256':digest,'url':url}
                updates.append(key)
                print('ĐÃ XỬ LÝ:',key,'dòng:',info['rows'],'ghế:',int(info['seats']))
            except Exception as exc:
                msg=f'{key}: {exc}'
                errors.append(msg);print('CẢNH BÁO:',msg)
        if not updates:
            if errors: raise RuntimeError('Chưa cập nhật tệp nào; dữ liệu cũ được giữ nguyên. '+' | '.join(errors))
            print('Không có bản sửa dữ liệu.')
            return
        BASELINE.mkdir(parents=True,exist_ok=True)
        for fn in OUTPUT.values():
            original=DATA/fn
            baseline=BASELINE/fn
            if not baseline.exists():shutil.copy2(original,baseline)
        staged=temp/'out';staged.mkdir()
        result=build_combined(airports,state,staged)
        newstate={'last_success_utc':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                  'period':f'{result["THANG"].min()} đến {result["THANG"].max()}',
                  'months':known,'newly_processed':updates,'warnings':errors,
                  'year_coverage':sorted(result['THANG'].str[:4].unique().tolist()),
                  'source':'ANAC Brazil / OurAirports'}
        staged_status=staged/'trang_thai_cap_nhat.json'
        staged_status.write_text(json.dumps({k:v for k,v in newstate.items() if k!='months'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        # All final outputs are validated before replacing them.
        for fn in OUTPUT.values():
            if (staged/fn).stat().st_size < 50: raise ValueError('Dữ liệu tổng hợp không đầy đủ: '+fn)
        for fn in OUTPUT.values(): (staged/fn).replace(DATA/fn)
        staged_status.replace(DATA/'trang_thai_cap_nhat.json')
        AUT.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(newstate,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('CẬP NHẬT THÀNH CÔNG:',len(updates),'tệp, năm:',newstate['year_coverage'])
        if errors: print('CẢNH BÁO CÓ NGUỒN LỖI, đã giữ dữ liệu cũ cho các nguồn đó.')

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    main()
