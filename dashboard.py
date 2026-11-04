from pathlib import Path
import os
from html import escape
import base64
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from anac_cloud_warehouse import fetch_release_asset, ensure_snapshot
from dashboard_v4_analytics import (
    weighted_mean_fare, matched_yoy,
    pareto, dumbbell_pairs, usable_distribution,
)

# DuckDB is optional only when deploying the legacy CSV-only dashboard.
try:
    import duckdb
except ImportError:
    duckdb = None

st.set_page_config(page_title='ANAC | Aviation Analytics', layout='wide', initial_sidebar_state='expanded')
ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'DuLieu_DaXuLy'
LOCAL_DB_PATH = ROOT / 'data_warehouse' / 'anac.duckdb'
# Prefer the existing local DuckDB when developing in VS Code.
# Streamlit Cloud has no local DuckDB, so it downloads the published release.
# Set ANAC_WAREHOUSE_SOURCE=release to test cloud mode on your own computer.
USE_REMOTE = (os.getenv('ANAC_WAREHOUSE_SOURCE', '').lower() == 'release'
              or not LOCAL_DB_PATH.is_file())
DB_PATH = ROOT / '.anac_cloud_cache' / 'anac.duckdb' if USE_REMOTE else LOCAL_DB_PATH
ANALYSIS_RESULTS = ROOT / 'data_warehouse' / 'analysis_results'
DISTRIBUTIONS = ROOT / 'data_warehouse' / 'fare_distribution_by_month.csv'
LOGO = ROOT / 'assets' / 'anac_logo.png'
BLUE, ORANGE = '#1689CF', '#F0A35D'
COLORS = {'Noi dia':BLUE,'Quoc te':ORANGE,'Nội địa':BLUE,'Quốc tế':ORANGE}
NAMES = {'Noi dia':'Nội địa','Quoc te':'Quốc tế'}
UNITS = {'Noi dia':'BRL','Quoc te':'USD'}

st.markdown('''
<style>
.stApp {background: #F2F7FC; color:#173F67}
.block-container {max-width:1660px;padding-top:0.8rem;padding-bottom:2rem}
section[data-testid="stSidebar"] {background:linear-gradient(170deg,#076AA9,#084E86 70%,#073E70);border:0}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] label {color:#F6FBFF!important}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#CFEBFA!important}
section[data-testid="stSidebar"] div[role="radiogroup"] label {background:rgba(255,255,255,.09);padding:12px;border-radius:13px;margin-bottom:6px;border:1px solid rgba(255,255,255,.14)}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {background:rgba(255,255,255,.25);border-color:rgba(255,255,255,.55)}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"]>div {background:white;border-radius:11px}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] * {color:#173F67!important}
.brand {font-size:22px;font-weight:850;color:white}.brand-sub {font-size:12px;letter-spacing:1px;color:#D6EDFA;margin-top:3px}
.brand-logo {background:white;border-radius:15px;padding:9px;margin-bottom:12px;text-align:center}.brand-logo img {height:76px;max-width:100%;object-fit:contain}
.hero {background:linear-gradient(115deg,#FFFFFF,#E6F4FF);padding:23px 27px;border:1px solid #D8EAF6;border-radius:21px;box-shadow:0 8px 28px rgba(32,95,145,.06)}
.eyebrow {font-size:13px;letter-spacing:1.3px;font-weight:750;color:#1689CF}
.hero-title {font-size:clamp(22px,2.3vw,34px);font-weight:850;color:#143F68;line-height:1.25;margin:8px 0}
.hero-sub {font-size:16px;color:#61819E}
.section-title {font-size:21px;font-weight:800;color:#173F67;margin:19px 0 11px}
div[data-testid="stVerticalBlockBorderWrapper"] {background:#FFFFFF;border:1px solid #DDEAF5;border-radius:17px;box-shadow:0 6px 23px rgba(33,88,136,.05)}
div[data-testid="stMetric"] {background:white;border:1px solid #DBEAF6;border-radius:15px;padding:12px}
div[data-testid="stMetricLabel"] p {font-size:12px;color:#6D88A0}
div[data-testid="stMetricValue"] {color:#174D77}
.insight {background:linear-gradient(120deg,#E8F5FF,#F7FCFF);border:1px solid #D7EAF7;border-radius:14px;padding:14px;min-height:102px}
.insight .k {font-size:13px;color:#698AA5}.insight .v {font-size:21px;font-weight:800;color:#154B73;margin:7px 0}.insight .n {font-size:13px;color:#287FAF}
.insight-story {background:linear-gradient(120deg,#E8F5FF,#FFFFFF);border:1px solid #D7EAF7;border-radius:16px;padding:18px 20px;margin:9px 0 14px;box-shadow:0 5px 15px rgba(33,88,136,.045)}
.insight-story h4 {font-size:17px;color:#16496E;margin:0 0 9px}
.insight-story p {font-size:14px;color:#315C79;line-height:1.65;margin:6px 0}
.source-chip {background:#DCEFFB;color:#175A84;border-radius:999px;padding:5px 11px;font-size:12px;font-weight:750;display:inline-block;margin:9px 0}
/* Sidebar buttons: white text on a white button caused invisible refresh label. */
section[data-testid="stSidebar"] div.stButton > button,
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
  background:#FFFFFF!important;color:#124D7D!important;border:1px solid #BDDCEC!important;
  border-radius:11px!important;min-height:42px;font-weight:700!important;
}
section[data-testid="stSidebar"] div.stButton > button *,
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] * {
  color:#124D7D!important;-webkit-text-fill-color:#124D7D!important;
}
section[data-testid="stSidebar"] div.stButton > button:hover {
  background:#E7F4FD!important;border-color:#7EC0E9!important;
}
/* Two-column insight cards stay within the existing blue-white visual system. */
.insight-story{height:100%;min-height:205px;margin:0!important;padding:18px!important;}
.insight-story h4{line-height:1.4;margin:0 0 11px}
.insight-story p{margin:7px 0;line-height:1.55}

#MainMenu, footer {visibility:hidden}
/* Keep Streamlit header and sidebar reopening button functional.
   Hide only the Deploy button rather than the entire toolbar. */
[data-testid="stHeader"] {display:flex!important;visibility:visible!important;background:transparent!important;height:3rem!important}
[data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarCollapseButton"] {visibility:visible!important;opacity:1!important}
[data-testid="stDeployButton"] {display:none!important}
/* Sidebar remains the only navigation; no red quick-nav buttons. */
.stButton > button[kind="primary"] {background:#1689CF!important;border-color:#1689CF!important;color:white!important}
/* Force refresh label to stay readable in both default and hover states. */
section[data-testid="stSidebar"] .stButton button p,
section[data-testid="stSidebar"] .stButton button span {color:#124D7D!important;-webkit-text-fill-color:#124D7D!important}


/* Increase text readability in the dashboard */
div[data-testid="stMarkdownContainer"] p {font-size:15px}
div[data-testid="stCaptionContainer"] p {font-size:13px}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {font-size:14px!important}
section[data-testid="stSidebar"] div[role="radiogroup"] label {font-size:14px}
div[data-testid="stMetricLabel"] p {font-size:14px}
div[data-testid="stMetricValue"] {font-size:29px}

</style>
''',unsafe_allow_html=True)

def read_csv(name):
    path = DATA / name
    with path.open('r',encoding='utf-8-sig') as f: head=f.readline()
    sep=';' if head.count(';')>head.count(',') else ','
    return pd.read_csv(path,sep=sep,encoding='utf-8-sig',low_memory=False)

@st.cache_data(ttl=300, show_spinner=False)
def latest_release_asset():
    """Check GitHub metadata at most once every five minutes per cache."""
    return fetch_release_asset()


def db_signature():
    """Use local DuckDB in VS Code or a validated Release snapshot on Cloud."""
    if USE_REMOTE:
        try:
            return ensure_snapshot(latest_release_asset(), DB_PATH)
        except Exception as exc:
            if DB_PATH.is_file():
                st.warning('GitHub Releases tạm thời không truy cập được; đang dùng DuckDB đã tải trước đó.')
                return DB_PATH.stat().st_mtime_ns
            raise RuntimeError(f'Chưa tải được DuckDB từ GitHub Releases: {exc}') from exc
    return DB_PATH.stat().st_mtime_ns if DB_PATH.is_file() else None


@st.fragment(run_every='10m')
def watch_cloud_release(loaded_asset_id):
    """Refresh the full dashboard when GitHub publishes a newer asset."""
    try:
        if str(latest_release_asset()['id']) != str(loaded_asset_id):
            st.rerun()
    except Exception:
        # Temporary API failures must not interrupt a previously loaded dashboard.
        pass


def connect_dw():
    if duckdb is None:
        raise RuntimeError('DuckDB chưa cài: python -m pip install duckdb')
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=3600, show_spinner='Đang đọc Data Warehouse...')
def load_monthly(db_version):
    """Use vw_monthly_kpi as the single source of dashboard KPIs when DB exists."""
    if db_version is not None:
        con = connect_dw()
        try:
            d = con.execute('''SELECT month_key, market_code, currency_code,
                total_seats, priced_seats, avg_fare, source_record_count
                FROM vw_monthly_kpi ORDER BY month_key, market_code''').df()
        finally:
            con.close()
        if d.empty:
            raise ValueError('vw_monthly_kpi không có dữ liệu.')
        d['THANG'] = d['month_key'].astype(int).astype(str).str.slice(0, 4) + '-' + d['month_key'].astype(int).astype(str).str.slice(4, 6)
        d['LOAI_CHUYEN_BAY'] = d['market_code'].map({'domestic':'Noi dia','international':'Quoc te'})
        d['SO_GHE_BAN'] = pd.to_numeric(d['total_seats'], errors='coerce')
        d['GHE_CO_GIA'] = pd.to_numeric(d['priced_seats'], errors='coerce')
        d['GIA_BINH_QUAN'] = pd.to_numeric(d['avg_fare'], errors='coerce')
        d['SO_BAN_GHI'] = pd.to_numeric(d['source_record_count'], errors='coerce')
        d['TIEN_TE'] = d['currency_code']
        return d, 'DuckDB'
    # Transparent fallback: the deployed app may not contain a .duckdb file yet.
    d = read_csv('tong_hop_theo_thang_2024.csv')
    for c in ('SO_GHE_BAN','GIA_BINH_QUAN','SO_BAN_GHI'):
        if c in d:
            d[c] = pd.to_numeric(d[c], errors='coerce')
    d['GHE_CO_GIA'] = d['SO_GHE_BAN']
    d['THANG'] = d['THANG'].astype(str).str.strip()
    d['LOAI_CHUYEN_BAY'] = d['LOAI_CHUYEN_BAY'].astype(str).str.strip()
    return d, 'CSV dự phòng'


@st.cache_data(ttl=3600, show_spinner='Đang truy vấn các tuyến bay...')
def load_dw_routes(db_version, from_month, to_month, selected_markets):
    keys = [1 if code == 'Noi dia' else 2 for code in selected_markets]
    key_marks = ','.join('?' for _ in keys)
    sql = f'''SELECT m.market_name AS LOAI,
           f.origin_airport_code AS ORIGEM,
           f.destination_airport_code AS DESTINO,
           COALESCE(a.airport_name, f.origin_airport_code) AS TEN_DI,
           COALESCE(b.airport_name, f.destination_airport_code) AS TEN_DEN,
           a.latitude AS LAT_DI, a.longitude AS LON_DI,
           b.latitude AS LAT_DEN, b.longitude AS LON_DEN,
           SUM(f.total_seats) AS ASSENTOS
        FROM fact_airfare_route_monthly f
        JOIN dim_market m ON f.market_key=m.market_key
        LEFT JOIN dim_airport a ON a.airport_code=f.origin_airport_code
        LEFT JOIN dim_airport b ON b.airport_code=f.destination_airport_code
        WHERE f.month_key BETWEEN ? AND ? AND f.market_key IN ({key_marks})
        GROUP BY 1,2,3,4,5,6,7,8,9'''
    con = connect_dw()
    try:
        routes = con.execute(sql, [int(from_month.replace('-','')),
                                   int(to_month.replace('-','')), *keys]).df()
    finally:
        con.close()
    for c in ('ASSENTOS','LAT_DI','LON_DI','LAT_DEN','LON_DEN'):
        routes[c] = pd.to_numeric(routes[c], errors='coerce')
    routes['LOAI'] = routes['LOAI'].map({'Noi dia':'Nội địa','Quoc te':'Quốc tế'}).fillna(routes['LOAI'])
    return routes


@st.cache_data(ttl=3600, show_spinner='Đang truy vấn điểm đến...')
def load_dw_destinations(db_version, from_month, to_month, selected_markets):
    keys = [1 if code == 'Noi dia' else 2 for code in selected_markets]
    marks = ','.join('?' for _ in keys)
    sql = f'''SELECT f.month_key, m.market_name AS LOAI,
           f.destination_airport_code AS DESTINO,
           COALESCE(NULLIF(TRIM(b.municipality), ''), b.airport_name,
                    f.destination_airport_code) AS DIA_DIEM,
           b.country_code AS QUOC_GIA, b.latitude AS LAT, b.longitude AS LON,
           SUM(f.total_seats) AS ASSENTOS
        FROM fact_airfare_route_monthly f
        JOIN dim_market m ON f.market_key=m.market_key
        LEFT JOIN dim_airport a ON a.airport_code=f.origin_airport_code
        LEFT JOIN dim_airport b ON b.airport_code=f.destination_airport_code
        WHERE f.month_key BETWEEN ? AND ? AND f.market_key IN ({marks})
          AND a.country_code = 'BR'
          AND ((m.market_code='domestic' AND b.country_code='BR')
            OR (m.market_code='international' AND b.country_code IS NOT NULL
                   AND b.country_code<>'BR'))
        GROUP BY 1,2,3,4,5,6,7'''
    con = connect_dw()
    try:
        d = con.execute(sql, [int(from_month.replace('-','')),
                              int(to_month.replace('-','')), *keys]).df()
    finally:
        con.close()
    d['THANG'] = d['month_key'].astype(int).astype(str).str.slice(0,4) + '-' + d['month_key'].astype(int).astype(str).str.slice(4,6)
    d['LOAI'] = d['LOAI'].map({'Noi dia':'Nội địa','Quoc te':'Quốc tế'}).fillna(d['LOAI'])
    for c in ('ASSENTOS','LAT','LON'):
        d[c] = pd.to_numeric(d[c], errors='coerce')
    return d


@st.cache_data(ttl=3600, show_spinner=False)
def load_routes_for_yoy(db_version, market_code, year, month_numbers):
    """Return complete route aggregates for two years, the SAME month subset."""
    if db_version is None or not month_numbers:
        return pd.DataFrame(columns=['sale_year', 'ORIGEM', 'DESTINO', 'ASSENTOS'])
    periods=[y*100 + int(m) for y in (year-1, year) for m in month_numbers]
    placeholders=','.join('?' for _ in periods)
    q=f"""SELECT d.sale_year, f.origin_airport_code AS ORIGEM,
               f.destination_airport_code AS DESTINO,
               SUM(f.total_seats) AS ASSENTOS
        FROM fact_airfare_route_monthly f
        JOIN dim_month d ON f.month_key=d.month_key
        JOIN dim_market t ON f.market_key=t.market_key
        WHERE t.market_code=? AND f.month_key IN ({placeholders})
        GROUP BY 1,2,3"""
    con=connect_dw()
    try:
        return con.execute(q,[market_code,*periods]).df()
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_csv_routes():
    nd=read_csv('top100_noi_dia_toa_do.csv');nd['LOAI']='Nội địa'
    qt=read_csv('top100_quoc_te_toa_do.csv');qt['LOAI']='Quốc tế'
    r=pd.concat([nd,qt],ignore_index=True)
    r['NAM']=pd.to_numeric(r['NAM'],errors='coerce').fillna(2024).astype(int) if 'NAM' in r else 2024
    for c in ('ASSENTOS','LAT_DI','LON_DI','LAT_DEN','LON_DEN'):
        r[c]=pd.to_numeric(r[c],errors='coerce')
    return r


@st.cache_data(ttl=3600)
def load_csv_destinations():
    d=read_csv('xu_huong_diem_den_2024.csv')
    d['THANG']=d['THANG'].astype(str).str.strip()
    for c in ('ASSENTOS','LAT','LON'):
        d[c]=pd.to_numeric(d[c],errors='coerce')
    return d


try:
    signature=db_signature()
    if USE_REMOTE:
        watch_cloud_release(signature)
    monthly, data_source=load_monthly(signature)
except Exception as exc:
    st.error(f'Không đọc được dữ liệu: {exc}')
    st.info('Nếu muốn dùng DuckDB, bảo đảm file data_warehouse/anac.duckdb tồn tại và đã cài duckdb.')
    st.stop()
monthly=monthly.dropna(subset=['SO_GHE_BAN','GIA_BINH_QUAN'])
monthly=monthly.sort_values(['LOAI_CHUYEN_BAY','THANG']).copy()
months=sorted(monthly['THANG'].unique().tolist())
if not months:
    st.error('Không có dữ liệu theo tháng.');st.stop()

with st.sidebar:
    # The ANAC image includes its own brand text; do not repeat ANAC twice.
    if LOGO.is_file():
        encoded=base64.b64encode(LOGO.read_bytes()).decode('ascii')
        st.markdown(f'<div class="brand-logo"><img src="data:image/png;base64,{encoded}" alt="ANAC"></div>', unsafe_allow_html=True)
        st.markdown('<div class="brand">ANAC Aviation Analytics</div><div class="brand-sub">BRAZIL AIRLINE DATA · 2024+</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="brand">ANAC Aviation Analytics</div><div class="brand-sub">BRAZIL AIRLINE DATA · 2024+</div>', unsafe_allow_html=True)
        st.caption('Logo chưa được tìm thấy: assets/anac_logo.png')
    st.divider();st.markdown('**ĐIỀU HƯỚNG**')
    page=st.radio('Trang dashboard',['01  Tổng quan & Giá vé','02  Tuyến bay & Chuyên sâu','03  Xu hướng du lịch & Điểm đến'],label_visibility='collapsed',key='navigation')
    st.divider();st.markdown('**BỘ LỌC PHÂN TÍCH**')
    market=st.selectbox('Thị trường',['Cả hai','Nội địa','Quốc tế'])
    years=sorted({m[:4] for m in months})
    year=st.selectbox('Năm phân tích',['Tất cả các năm']+years)
    active_months=months if year=='Tất cả các năm' else [m for m in months if m.startswith(year+'-')]
    start,end=st.select_slider('Khoảng tháng',options=active_months,value=(active_months[0],active_months[-1]))
    if page.startswith('02'):
        top=st.selectbox('Số tuyến mỗi loại',[20,50,100],index=1,format_func=lambda x:f'Top {x}')
    else: top=50
    if page.startswith('03'):
        dest_top=st.selectbox('Số điểm đến hiển thị',[5,10,20],index=1,format_func=lambda x:f'Top {x}')
    else: dest_top=10
    st.divider()
    if st.button('↻ Làm mới dữ liệu hiển thị', key='btn_refresh_data', width='stretch', help='Xóa bộ nhớ đệm Streamlit rồi đọc lại DuckDB/CSV có sẵn. Không tự tải dữ liệu ANAC.'):
        st.cache_data.clear()
        st.rerun()
    status_file = DATA / 'trang_thai_cap_nhat.json'
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text(encoding='utf-8'))
            st.caption('Lần ETL thành công: ' + str(status.get('last_success_utc','Chưa rõ')) + ' (UTC)')
            st.caption('Kỳ dữ liệu: ' + str(status.get('period','Chưa rõ')))
        except (ValueError, OSError):
            st.caption('Chưa đọc được trạng thái cập nhật.')
    else:
        st.caption('Dữ liệu gốc 2024; chưa có lần ETL tự động được xác nhận.')
    st.markdown(f'<span class="source-chip">NGUỒN DASHBOARD: {escape(data_source)}</span>',unsafe_allow_html=True)
    if signature is None:
        st.caption('Chưa có DuckDB tại thư mục project; các biểu đồ dùng CSV dự phòng.')
    st.caption('Nguồn gốc: ANAC Brazil / OurAirports')

chosen=['Noi dia','Quoc te'] if market=='Cả hai' else ['Noi dia' if market=='Nội địa' else 'Quoc te']
selected=monthly[monthly['THANG'].between(start,end)&monthly['LOAI_CHUYEN_BAY'].isin(chosen)].copy()
if selected.empty:
    st.warning('Không có dữ liệu cho năm/tháng/thị trường đã chọn. Đây là kỳ chưa có dữ liệu, không phải số ghế bán bằng 0.')
    st.stop()

# A missing calendar month is NOT the previous month. E.g. 2026-04 -> 2026-06.
history=monthly.copy()
history['month_seq']=history['THANG'].str[:4].astype(int)*12 + history['THANG'].str[5:7].astype(int)
grouped=history.groupby('LOAI_CHUYEN_BAY')
adjacent=history['month_seq'].sub(grouped['month_seq'].shift(1)).eq(1)
history['PCT_PRICE']=grouped['GIA_BINH_QUAN'].pct_change(fill_method=None).where(adjacent)*100
history['PCT_SEATS']=grouped['SO_GHE_BAN'].pct_change(fill_method=None).where(adjacent)*100
changes=history[history['THANG'].between(start,end)&history['LOAI_CHUYEN_BAY'].isin(chosen)].copy()

try:
    if signature is not None:
        routes=load_dw_routes(signature,start,end,tuple(chosen))
        rank_routes=routes.sort_values('ASSENTOS',ascending=False).groupby('LOAI',group_keys=False).head(top).copy()
        route_sel=rank_routes.dropna(subset=['LAT_DI','LON_DI','LAT_DEN','LON_DEN']).copy()
    else:
        routes=load_csv_routes()
        route_sel=routes if market=='Cả hai' else routes[routes['LOAI']==market]
        if year!='Tất cả các năm':
            route_sel=route_sel[route_sel['NAM']==int(year)].copy()
        else:
            by=['LOAI','ORIGEM','DESTINO','TEN_DI','TEN_DEN','LAT_DI','LON_DI','LAT_DEN','LON_DEN']
            route_sel=route_sel.groupby(by,dropna=False,as_index=False)['ASSENTOS'].sum()
        rank_routes=route_sel.sort_values('ASSENTOS',ascending=False).groupby('LOAI',group_keys=False).head(top).copy()
        route_sel=rank_routes.dropna(subset=['LAT_DI','LON_DI','LAT_DEN','LON_DEN']).copy()
except Exception as exc:
    st.error(f'Không truy vấn được các tuyến bay: {exc}');st.stop()

def section(t): st.markdown(f'<div class="section-title">{escape(t)}</div>',unsafe_allow_html=True)
def plot(fig,key): st.plotly_chart(fig,width='stretch',config={'displaylogo':False},key=key)
def theme(fig,height=260,y=None):
    fig.update_layout(height=height,margin=dict(l=8,r=8,t=18,b=15),paper_bgcolor='white',plot_bgcolor='white',font=dict(color='#58768E',size=13),xaxis=dict(showgrid=False),yaxis=dict(title=y,showgrid=True,gridcolor='#EBF1F7'),hovermode='closest')
    return fig
def panel(title,sub,fig,key):
    with st.container(border=True):
        st.markdown('**'+title+'**');st.caption(sub);plot(fig,key)
def avg(d):
    # Weigh by priced seats; seats without a valid fare must not distort the price.
    total=d['GHE_CO_GIA'].sum()
    return float((d['GIA_BINH_QUAN']*d['GHE_CO_GIA']).sum()/total) if total>0 else None
def insight(label,value,note):
    st.markdown(f'<div class="insight"><div class="k">{escape(str(label))}</div><div class="v">{escape(str(value))}</div><div class="n">{escape(str(note))}</div></div>',unsafe_allow_html=True)

def line_chart(code,field):
    d=selected[selected['LOAI_CHUYEN_BAY']==code].sort_values('THANG')
    if not d.empty:
        # Insert missing calendar months as NaN, so Plotly never draws a false bridge.
        calendar=[str(m) for m in pd.period_range(d['THANG'].iloc[0], d['THANG'].iloc[-1], freq='M')]
        d=d.set_index('THANG').reindex(calendar).rename_axis('THANG').reset_index()
    f=go.Figure(go.Scatter(x=d['THANG'],y=d[field],mode='lines+markers',connectgaps=False,line=dict(color=COLORS[code],width=2.7),marker=dict(size=6),hovertemplate='%{x}<br>%{y:,.2f}<extra></extra>'))
    return theme(f,255,UNITS[code] if field=='GIA_BINH_QUAN' else 'Số ghế')
def change_chart(code,field):
    d=changes[changes['LOAI_CHUYEN_BAY']==code].dropna(subset=[field]).sort_values('THANG')
    f=go.Figure(go.Bar(x=d['THANG'],y=d[field],marker_color=[BLUE if v>=0 else ORANGE for v in d[field]],hovertemplate='%{x}<br>%{y:+.2f}%<extra></extra>'))
    f.add_hline(y=0,line_color='#BFD0DF',line_width=1)
    return theme(f,235,'%')
def map_chart():
    f=go.Figure()
    for _,r in route_sel.iterrows():
        f.add_trace(go.Scattergeo(lon=[r['LON_DI'],r['LON_DEN']],lat=[r['LAT_DI'],r['LAT_DEN']],mode='lines',line=dict(color=COLORS[r['LOAI']],width=1),opacity=.45,hoverinfo='skip',showlegend=False))
    a=route_sel[['ORIGEM','TEN_DI','LAT_DI','LON_DI']].copy();a.columns=['CODE','NAME','LAT','LON']
    b=route_sel[['DESTINO','TEN_DEN','LAT_DEN','LON_DEN']].copy();b.columns=['CODE','NAME','LAT','LON']
    airports=pd.concat([a,b],ignore_index=True).drop_duplicates('CODE')
    f.add_trace(go.Scattergeo(lon=airports['LON'],lat=airports['LAT'],mode='markers',marker=dict(size=4,color='#21608B'),text=airports['CODE'],customdata=airports['NAME'],hovertemplate='<b>%{text}</b><br>%{customdata}<extra></extra>',name='Sân bay'))
    view=dict(projection=dict(type='mercator'),lataxis=dict(range=[-35,7]),lonaxis=dict(range=[-76,-32])) if market=='Nội địa' else dict(projection=dict(type='natural earth'),fitbounds='locations')
    f.update_layout(height=440,margin=dict(l=0,r=0,t=0,b=0),geo=dict(**view,showland=True,landcolor='#E7F0F8',showocean=True,oceancolor='#F7FBFE',showcountries=True,countrycolor='#C7D8E6',showcoastlines=True,coastlinecolor='#C7D8E6',showframe=False,bgcolor='white'),paper_bgcolor='white')
    return f,len(airports)
def top_chart():
    d=rank_routes.nlargest(10,'ASSENTOS').sort_values('ASSENTOS').copy();d['NAME']=d['ORIGEM'].astype(str)+' → '+d['DESTINO'].astype(str)
    f=go.Figure(go.Bar(x=d['ASSENTOS'],y=d['NAME'],orientation='h',marker_color=[COLORS[v] for v in d['LOAI']],hovertemplate='%{y}<br>%{x:,.0f} ghế<extra></extra>'))
    return theme(f,340)
def share_chart():
    s=selected.groupby('LOAI_CHUYEN_BAY')['SO_GHE_BAN'].sum()
    f=go.Figure(go.Pie(labels=['Nội địa','Quốc tế'],values=[s.get('Noi dia',0),s.get('Quoc te',0)],hole=.65,marker=dict(colors=[BLUE,ORANGE]),textinfo='percent',hovertemplate='%{label}<br>%{value:,.0f} ghế<extra></extra>'))
    f.update_layout(height=290,margin=dict(l=4,r=4,t=6,b=8),legend=dict(orientation='h',x=.5,xanchor='center',y=-.1),paper_bgcolor='white')
    return f
def scatter_chart(code):
    d=selected[selected['LOAI_CHUYEN_BAY']==code]
    f=go.Figure(go.Scatter(x=d['GIA_BINH_QUAN'],y=d['SO_GHE_BAN'],text=d['THANG'],mode='markers',marker=dict(size=9,color=COLORS[code]),hovertemplate='%{text}<br>Giá: %{x:,.2f}<br>Ghế: %{y:,.0f}<extra></extra>'))
    f=theme(f,285,'Số ghế bán');f.update_xaxes(title=f'Giá ({UNITS[code]})')
    r=d['GIA_BINH_QUAN'].corr(d['SO_GHE_BAN']) if len(d)>=3 else np.nan
    return f,r

def ranking_destinations(d, type_name, group_key, n):
    subset=d[d['LOAI']==type_name]
    if group_key=='DIA_DIEM':
        # City and country should be kept together to avoid name collisions.
        sub=subset.copy();sub['NHAN']=sub['DIA_DIEM'].fillna(sub['DESTINO'])+' ('+sub['QUOC_GIA'].fillna('?')+')'
    elif group_key=='QUOC_GIA':
        sub=subset.copy();sub['NHAN']=sub['QUOC_GIA'].fillna('Không rõ')
    else:
        sub=subset.copy();sub['NHAN']=sub['DESTINO']+' · '+sub['DIA_DIEM'].fillna(sub['DESTINO'])
    rank=sub.groupby('NHAN',as_index=False)['ASSENTOS'].sum().sort_values('ASSENTOS',ascending=False).head(n)
    return rank,sub

def ranking_chart(rank,color):
    v=rank.sort_values('ASSENTOS')
    f=go.Figure(go.Bar(x=v['ASSENTOS'],y=v['NHAN'],orientation='h',marker_color=color,hovertemplate='%{y}<br>%{x:,.0f} ghế<extra></extra>'))
    f.update_layout(height=max(270,len(v)*34+75),margin=dict(l=12,r=12,t=12,b=15),paper_bgcolor='white',plot_bgcolor='white',font=dict(color='#58768E',size=13),xaxis=dict(title='Ghế bán',gridcolor='#EBF1F7'),yaxis=dict(title=None,automargin=True))
    return f

def destination_month_chart(sub,rank):
    top_keys=rank['NHAN'].head(5).tolist();t=sub[sub['NHAN'].isin(top_keys)].groupby(['THANG','NHAN'],as_index=False)['ASSENTOS'].sum()
    f=go.Figure()
    for name in top_keys:
        x=t[t['NHAN']==name].sort_values('THANG')
        f.add_trace(go.Scatter(x=x['THANG'],y=x['ASSENTOS'],mode='lines+markers',name=name,marker=dict(size=5)))
    f=theme(f,460,'Ghế bán');f.update_layout(legend=dict(orientation='h',y=-.26,x=.5,xanchor='center',font=dict(size=12)),margin=dict(l=12,r=12,t=25,b=110))
    return f

def destinations_map(d,top_n):
    grouped=d.groupby(['DESTINO','DIA_DIEM','QUOC_GIA','LAT','LON','LOAI'],dropna=False,as_index=False)['ASSENTOS'].sum()
    selected_top=grouped.sort_values('ASSENTOS',ascending=False).groupby('LOAI',group_keys=False).head(top_n)
    selected_top=selected_top.dropna(subset=['LAT','LON'])
    f=go.Figure()
    for kind,g in selected_top.groupby('LOAI'):
        f.add_trace(go.Scattergeo(lat=g['LAT'],lon=g['LON'],mode='markers',marker=dict(size=5,color=COLORS[kind],opacity=.85),text=g['DIA_DIEM'].fillna(g['DESTINO']),hovertext=[f'{city} ({code})<br>{seats:,.0f} ghế' for city,code,seats in zip(g['DIA_DIEM'].fillna(g['DESTINO']),g['DESTINO'],g['ASSENTOS'])],hovertemplate='%{hovertext}<extra></extra>',name=kind))
    view=dict(projection=dict(type='mercator'),lataxis=dict(range=[-35,7]),lonaxis=dict(range=[-76,-32])) if market=='Nội địa' else dict(projection=dict(type='natural earth'),fitbounds='locations')
    f.update_layout(height=370,margin=dict(l=0,r=0,t=0,b=0),geo=dict(**view,showland=True,landcolor='#E7F0F8',showocean=True,oceancolor='#F7FBFE',showcountries=True,countrycolor='#C7D8E6',showcoastlines=True,coastlinecolor='#C7D8E6',showframe=False,bgcolor='white'),legend=dict(orientation='h',x=0,y=0),paper_bgcolor='white')
    return f

# Use contiguous HTML to prevent the Markdown code-block rendering issue.
period_label = f'{min(months)} đến {max(months)}'
# Display the period actually loaded into the dashboard; the ETL status can be stale.
st.markdown('<div class="hero"><div class="eyebrow">ANAC AVIATION INTELLIGENCE | BRAZIL</div><div class="hero-title">Phân tích biến động giá vé máy bay &amp; Xu hướng du lịch nội địa / quốc tế</div><div class="hero-sub">Phân tích giá vé, số ghế bán và mạng lưới tuyến bay nội địa / quốc tế tại Brazil - ' + escape(period_label) + '.</div></div>',unsafe_allow_html=True)

def story(title, evidence, conclusion, limitation):
    st.markdown(
        '<div class="insight-story"><h4>' + escape(title) + '</h4>'
        '<p><b>Bằng chứng:</b> ' + escape(evidence) + '</p>'
        '<p><b>Insight:</b> ' + escape(conclusion) + '</p>'
        '<p><b>Giới hạn:</b> ' + escape(limitation) + '</p></div>',
        unsafe_allow_html=True
    )


def fmt_pct(v):
    return f'{float(v):+.2f}%' if pd.notna(v) else 'không xác định'


def pearson_label(r):
    if pd.isna(r): return 'không đủ dữ liệu'
    strength=abs(float(r))
    word='rất yếu' if strength<.2 else 'yếu' if strength<.4 else 'trung bình' if strength<.6 else 'khá rõ'
    direction='nghịch' if r<0 else 'thuận' if r>0 else 'không có'
    return f'{direction}, {word}'


def period_overlap(code, target_year, current_months):
    """Matched sale months only: prevents unfair partial-year 2026 comparisons."""
    h=monthly[monthly['LOAI_CHUYEN_BAY']==code].copy()
    h['year']=h['THANG'].str[:4].astype(int)
    h['m']=h['THANG'].str[5:7].astype(int)
    this=h[(h['year']==target_year)&h['m'].isin(current_months)]
    prev=h[(h['year']==target_year-1)&h['m'].isin(current_months)]
    common=sorted(set(this['m']) & set(prev['m']))
    return this[this['m'].isin(common)],prev[prev['m'].isin(common)],common


def selected_focus(code):
    d=selected[selected['LOAI_CHUYEN_BAY']==code].copy()
    if d.empty:return None,None,[]
    focus=int(d['THANG'].str[:4].max())
    focus_d=d[d['THANG'].str[:4]==str(focus)]
    mm=sorted(focus_d['THANG'].str[5:7].astype(int).unique().tolist())
    return focus, focus_d, mm


def weighted_price(d):
    w=pd.to_numeric(d.get('GHE_CO_GIA',pd.Series(dtype=float)),errors='coerce').sum()
    return float((d['GIA_BINH_QUAN']*d['GHE_CO_GIA']).sum()/w) if w>0 else np.nan


def render_business_insights():
    section('06 | Business Insights · Theo bộ lọc đang chọn')
    st.caption('Tất cả phát hiện bên dưới được tính lại theo thị trường, năm và khoảng tháng đang chọn; '
               'khi so với năm trước chỉ dùng các tháng có mặt ở CẢ HAI năm. '
               'Giá nội địa BRL và quốc tế USD không so trực tiếp.')
    st.caption(f'Phạm vi: {start} → {end} · {market} · Nguồn KPI: {data_source}. '
               'Các kết luận chỉ mô tả dữ liệu bán vé ANAC, không khẳng định nguyên nhân.')
    focus={code:selected_focus(code) for code in chosen}
    names={code:NAMES[code] for code in chosen}
    cards=[]

    # 01 Annual comparison, with matched months for each market.
    evidence=[]; interpretation=[]
    for code in chosen:
        yr,_,mm=focus[code]
        if yr is None:continue
        a,b,matching=period_overlap(code,yr,mm)
        if not matching:continue
        seats_old=b['SO_GHE_BAN'].sum();seats_new=a['SO_GHE_BAN'].sum()
        pa,pb=weighted_price(a),weighted_price(b)
        if seats_old>0 and pb>0:
            seat_pct=(seats_new/seats_old-1)*100
            fare_pct=(pa/pb-1)*100
            evidence.append(f'{names[code]} {yr} so {yr-1} ({len(matching)} tháng khớp): '
                            f'ghế {fmt_pct(seat_pct)}, giá {fmt_pct(fare_pct)} ({UNITS[code]})')
            interpretation.append('giá và ghế '+('khác chiều' if seat_pct*fare_pct<0 else 'cùng chiều'))
    if evidence:
        cards.append(('01 · Thị trường tăng trưởng như thế nào?',
                      '; '.join(evidence)+'.',
                      'Tăng trưởng không nhất thiết đồng nghĩa giá và số ghế cùng tăng; '
                      'mỗi thị trường cần phân tích riêng.',
                      'So sánh cùng tập tháng xuất hiện ở cả hai năm, không suy luận nguyên nhân.'))
    else:
        cards.append(('01 · So sánh tăng trưởng cùng kỳ',
                      'Phạm vi đang chọn không có cặp năm liền trước và năm hiện tại đủ dữ liệu đối chiếu.',
                      'Không thể kết luận tăng trưởng YoY từ một năm đứng riêng.',
                      'Chọn năm 2025 hoặc 2026, hoặc mở rộng khoảng tháng.'))

    # 02 Highest/lowest fares in exact selected range; cross-year seasonality only with complete years.
    extreme=[]; seasonal=[]
    for code in chosen:
        d=selected[selected['LOAI_CHUYEN_BAY']==code]
        if d.empty:continue
        lo=d.loc[d['GIA_BINH_QUAN'].idxmin()]; hi=d.loc[d['GIA_BINH_QUAN'].idxmax()]
        extreme.append(f'{names[code]}: thấp nhất {lo.THANG} ({lo.GIA_BINH_QUAN:,.2f} {UNITS[code]}), '
                       f'cao nhất {hi.THANG} ({hi.GIA_BINH_QUAN:,.2f} {UNITS[code]})')
        complete=[]
        for y,g in d.groupby(d['THANG'].str[:4]):
            if set(g['THANG'].str[-2:].astype(int))==set(range(1,13)):
                complete.append((int(y), g.loc[g['GIA_BINH_QUAN'].idxmin()]['THANG'][-2:],
                                 g.loc[g['GIA_BINH_QUAN'].idxmax()]['THANG'][-2:]))
        if len(complete)>=2 and len({x[1] for x in complete})==1 and len({x[2] for x in complete})==1:
            seasonal.append(f'{names[code]}: tháng thấp/cao lặp lại trong {len(complete)} năm đầy đủ')
    cards.append(('02 · Khi nào giá vé thấp/cao?',
                  '; '.join(extreme)+'.' if extreme else 'Không có kỳ dữ liệu hợp lệ trong khoảng lọc.',
                  ('; '.join(seasonal)+'; đây là tín hiệu mùa vụ cần nghiên cứu tiếp.'
                   if seasonal else 'Tháng có mức giá cao/thấp thay đổi theo phạm vi lọc; chưa đủ cơ sở khẳng định mùa vụ.'),
                  'So sánh giá trong cùng thị trường/tiền tệ; 2026 thiếu tháng 05 nên không coi là năm đầy đủ.'))

    # 03 Correlation + opposing MONTH-OVER-MONTH moves. Pearson is descriptive only.
    correlations=[]; opp_notes=[]
    for code in chosen:
        d=selected[selected['LOAI_CHUYEN_BAY']==code]
        if len(d)<3:continue
        r=d['GIA_BINH_QUAN'].corr(d['SO_GHE_BAN'])
        correlations.append(f'{names[code]}: r={r:.3f} ({pearson_label(r)}, n={len(d)} tháng)')
        m=changes[changes['LOAI_CHUYEN_BAY']==code].dropna(subset=['PCT_PRICE','PCT_SEATS'])
        m=m[(m['PCT_PRICE']!=0)&(m['PCT_SEATS']!=0)]
        if len(m): opp_notes.append(f'{names[code]}: {int((m.PCT_PRICE*m.PCT_SEATS<0).sum())}/{len(m)} kỳ MoM ngược chiều')
    cards.append(('03 · Giá tăng có làm ghế bán giảm?',
                  '; '.join(correlations+opp_notes)+'.' if correlations else 'Không đủ tháng để xác định tương quan.',
                  ('Mối liên hệ tuyến tính có thể rất yếu; xem biến động từng tháng hữu ích hơn '
                   'là chỉ nhìn một hệ số Pearson.'),
                  'Tương quan và diễn biến đồng/ngược chiều không chứng minh nhân quả; mỗi thị trường tính riêng.'))

    # 04 YoY comparison of routes: top20 overlap computed from all DW facts, not topN CSV.
    route_notes=[]
    if signature is not None:
        for code in chosen:
            yr,_,mm=focus[code]
            if yr is None:continue
            _,_,common=period_overlap(code,yr,mm)
            if not common:continue
            mark='domestic' if code=='Noi dia' else 'international'
            rr=load_routes_for_yoy(signature,mark,yr,tuple(common))
            c=rr[rr.sale_year==yr].nlargest(20,'ASSENTOS')
            p=rr[rr.sale_year==yr-1].nlargest(20,'ASSENTOS')
            joined=c.merge(p,on=['ORIGEM','DESTINO'],suffixes=('_now','_prev'))
            if len(joined):
                down=int((joined['ASSENTOS_now']<joined['ASSENTOS_prev']).sum())
                route_notes.append(f'{names[code]} {yr}: {down}/{len(joined)} tuyến chung Top 20 giảm ghế '
                                   f'({len(common)} tháng tương ứng)')
    cards.append(('04 · Mọi tuyến đều tăng trưởng?',
                  '; '.join(route_notes)+'.' if route_notes else 'Chưa có đủ tuyến Top 20 chung để so sánh trong phạm vi lọc.',
                  ('Tổng thị trường tăng không có nghĩa tất cả tuyến đều tăng.' if route_notes
                   else 'Cần dữ liệu cùng kỳ của hai năm để đánh giá tăng trưởng tuyến.'),
                  'So sánh tuyến có hướng; chỉ xét phần giao Top 20, không đại diện cho toàn mạng lưới.'))

    # 05 Concentration by top10 routes, denominator is ALL seats for market, period.
    concentrates=[]
    if signature is not None:
        for code in chosen:
            d=selected[selected['LOAI_CHUYEN_BAY']==code]
            market_routes=routes[routes['LOAI']==NAMES[code]]
            denom=d['SO_GHE_BAN'].sum()
            if denom>0 and not market_routes.empty:
                top10=market_routes['ASSENTOS'].nlargest(10).sum()
                concentrates.append(f'{names[code]}: Top 10 chiếm {100*top10/denom:.2f}% tổng ghế')
    cards.append(('05 · Ghế bán tập trung vào tuyến lớn?',
                  '; '.join(concentrates)+'.' if concentrates else 'Cần DuckDB để tính tỷ trọng trên toàn bộ tuyến bay.',
                  'Tỷ trọng Top 10 cho biết mức độ tập trung của số ghế bán theo tuyến trong giai đoạn chọn.',
                  'Không phải thị phần hãng bay; không cộng giá trị BRL và USD với nhau.'))

    # 06 Anomalies only comparing real adjacent calendar months, not a missing gap.
    flags=changes.dropna(subset=['PCT_PRICE','PCT_SEATS']).copy()
    flags=flags[(flags['PCT_PRICE'].abs()>=20)|(flags['PCT_SEATS'].abs()>=30)]
    flags=flags.sort_values('THANG')
    flagged=[f"{x.THANG} {NAMES[x.LOAI_CHUYEN_BAY]}: giá {fmt_pct(x.PCT_PRICE)}, ghế {fmt_pct(x.PCT_SEATS)}"
             for x in flags.head(4).itertuples()]
    cards.append(('06 · Tháng nào biến động bất thường?',
                  f'{len(flags)} kỳ vượt ngưỡng (|giá MoM| ≥20% hoặc |ghế MoM| ≥30%). '
                  + ('; '.join(flagged)+'.' if flagged else ''),
                  ('Các kỳ gắn cờ nên kiểm tra sâu theo tuyến và thời gian.' if len(flags)
                   else 'Không phát hiện kỳ vượt ngưỡng trong khoảng đã chọn; không đồng nghĩa không có bất thường.'),
                  'Ngưỡng phân tích tùy chỉnh; không so MoM qua tháng bị thiếu, không khẳng định lỗi/quan hệ nhân quả.'))

    for i in range(0,len(cards),2):
        left,right=st.columns(2,gap='medium')
        with left: story(*cards[i])
        if i+1<len(cards):
            with right: story(*cards[i+1])

    if signature is None:
        st.info('Chế độ CSV dự phòng: insight về tuyến và độ tập trung cần DuckDB để tính đầy đủ.')
    if 'Noi dia' in chosen and '2026-05' not in monthly[monthly.LOAI_CHUYEN_BAY=='Noi dia']['THANG'].tolist() and end>='2026-05' and start<='2026-05':
        st.warning('Tháng 05/2026 nội địa chưa có dữ liệu; không thay bằng 0 và không tính MoM vượt qua khoảng thiếu.')


@st.cache_data(ttl=3600, show_spinner=False)
def load_fare_distributions(file_version):
    if file_version is None:
        return pd.DataFrame()
    d=pd.read_csv(DISTRIBUTIONS,encoding='utf-8-sig')
    required={'THANG','market_code','q1','median','q3','p10','p90','priced_seats'}
    if not required.issubset(d.columns):
        raise ValueError('Thiếu cột phân phối giá trong fare_distribution_by_month.csv')
    d['THANG']=d['THANG'].astype(str)
    for c in ('q1','median','q3','p10','p90','priced_seats'):
        d[c]=pd.to_numeric(d[c],errors='coerce')
    return d


def monthly_price_compare(code):
    d=selected[selected['LOAI_CHUYEN_BAY']==code].copy()
    if d.empty:
        return None, []
    d['year']=d['THANG'].str[:4]
    d['month']=d['THANG'].str[5:7].astype(int)
    years=sorted(d['year'].unique().tolist())
    fig=go.Figure()
    palette=['#1f77b4','#6baed6','#9ecae1'] if code=='Noi dia' else ['#E08D45','#F2B071','#F7CFA0']
    for idx,yr in enumerate(years):
        s=d[d['year']==yr].sort_values('month')
        fig.add_trace(go.Bar(
            x=[f'T{m:02d}' for m in s['month']],
            y=s['GIA_BINH_QUAN'],
            name=str(yr),
            marker_color=palette[idx % len(palette)],
            text=[f'{v:,.1f}' for v in s['GIA_BINH_QUAN']],
            textposition='outside',
            hovertemplate='Năm '+str(yr)+'<br>%{x}<br>Giá: %{y:,.2f} '+UNITS[code]+'<extra></extra>'
        ))
    fig=theme(fig,340,f'Giá ({UNITS[code]})')
    fig.update_layout(
        barmode='group',
        margin=dict(l=12,r=12,t=24,b=16),
        legend=dict(orientation='h', y=1.10, x=0),
        xaxis=dict(title='Tháng'),
        yaxis=dict(title='Giá bình quân')
    )
    return fig, years


def yoy_figure(code):
    focus,_,mm=selected_focus(code)
    value=matched_yoy(monthly,code,focus,mm) if focus is not None else None
    if value is None:
        return None,None
    fig=go.Figure(go.Bar(x=['Số ghế bán','Giá vé bình quân'],
                         y=[value['seats_yoy'],value['fare_yoy']],
                         marker_color=[BLUE if v>=0 else ORANGE for v in (value['seats_yoy'],value['fare_yoy'])],
                         text=[fmt_pct(value['seats_yoy']),fmt_pct(value['fare_yoy'])],textposition='outside',
                         hovertemplate='%{x}: %{y:+.2f}%<extra></extra>'))
    fig.add_hline(y=0,line_color='#A6BBCF',line_width=1)
    fig=theme(fig,280,'% YoY')
    fig.update_layout(margin=dict(l=12,r=12,t=38,b=18))
    return fig,value


def distribution_chart(frame, code):
    d=usable_distribution(frame,'domestic' if code=='Noi dia' else 'international',start,end)
    if d.empty:return None,d
    # Per-month customdata supplies the complete distribution on hover.
    # Whiskers use P10/P90; these are not Tukey 1.5*IQR outlier fences.
    vals=d[['p10','q1','median','q3','p90','priced_seats']].to_numpy(dtype=float)
    tooltip=(
        '<b>%{x}</b><br>'
        'P10: %{customdata[0]:,.2f}<br>'
        'P25: %{customdata[1]:,.2f}<br>'
        'Trung vị (P50): %{customdata[2]:,.2f}<br>'
        'P75: %{customdata[3]:,.2f}<br>'
        'P90: %{customdata[4]:,.2f}<br>'
        'Ghế có giá: %{customdata[5]:,.0f}<br>'
        'Đơn vị: '+UNITS[code]+'<extra></extra>'
    )
    fig=go.Figure(go.Box(x=d.THANG.tolist(), q1=d.q1.tolist(),median=d['median'].tolist(),
                         q3=d.q3.tolist(),lowerfence=d.p10.tolist(),upperfence=d.p90.tolist(),
                         boxpoints=False, marker_color=COLORS[code],line=dict(color=COLORS[code]),
                         customdata=vals, hovertemplate=tooltip,
                         name=NAMES[code]))
    fig=theme(fig,320,f'Giá ({UNITS[code]})')
    fig.update_layout(xaxis=dict(tickangle=-45),hovermode='closest')
    return fig,d


def pareto_chart(code):
    d,n80=pareto(routes,NAMES[code])
    if d.empty:return None,0,0
    shown=d.head(20)
    fig=go.Figure()
    fig.add_trace(go.Bar(x=shown.route_label,y=shown.ASSENTOS,name='Ghế bán',marker_color=COLORS[code],yaxis='y1'))
    fig.add_trace(go.Scatter(x=shown.route_label,y=shown.cumulative_pct,mode='lines+markers',name='Tích lũy (%)',
                             line=dict(color='#E08D45',width=2.5),yaxis='y2'))
    fig.add_hline(y=0,line_color='#D6E4EF',line_width=1)
    fig.update_layout(height=400,paper_bgcolor='white',plot_bgcolor='white',
                      margin=dict(l=16,r=44,t=40,b=90),font=dict(color='#58768E',size=12),
                      xaxis=dict(tickangle=-50),yaxis=dict(title='Số ghế bán',gridcolor='#EBF1F7'),
                      yaxis2=dict(title='Tích lũy (%)',overlaying='y',side='right',range=[0,105],showgrid=False),
                      legend=dict(orientation='h',y=1.12,x=0))
    return fig,n80,len(d)


def dumbbell_chart(code):
    focus,_,mm=selected_focus(code)
    if signature is None or focus is None:
        return None,None
    yoy=matched_yoy(monthly,code,focus,mm)
    if yoy is None:return None,None
    r=load_routes_for_yoy(signature,'domestic' if code=='Noi dia' else 'international',focus,tuple(yoy['months']))
    d=dumbbell_pairs(r,focus,limit=15)
    if d.empty:return None,None
    fig=go.Figure()
    for r in d.itertuples():
        fig.add_trace(go.Scatter(x=[r.ASSENTOS_prev,r.ASSENTOS_current],y=[r.label,r.label],
                                 mode='lines',line=dict(color='#ADC9DE',width=3),showlegend=False,hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=d.ASSENTOS_prev,y=d.label,mode='markers',name=str(focus-1),
                             marker=dict(color='#F0A35D',size=9)))
    fig.add_trace(go.Scatter(x=d.ASSENTOS_current,y=d.label,mode='markers',name=str(focus),
                             marker=dict(color='#1689CF',size=9),
                             customdata=d.delta_pct,hovertemplate='%{y}: %{x:,.0f} ghế<br>YoY %{customdata:+.2f}%<extra></extra>'))
    fig.update_layout(height=max(400,85+28*len(d)),paper_bgcolor='white',plot_bgcolor='white',
                      font=dict(color='#58768E',size=12),margin=dict(l=16,r=12,t=36,b=20),
                      xaxis=dict(title='Số ghế bán',gridcolor='#EBF1F7'),
                      yaxis=dict(title=None,automargin=True),legend=dict(orientation='h',y=1.12,x=0))
    return fig,yoy


def destination_insight(dest):
    section('05 | Insight điểm đến theo bộ lọc')
    for code in chosen:
        kind=NAMES[code]
        d=dest[dest.LOAI.eq(kind)].copy()
        if d.empty: continue
        r=d.groupby(['DESTINO','DIA_DIEM'],dropna=False)['ASSENTOS'].sum().sort_values(ascending=False)
        top_key=r.index[0]; total=r.sum()
        evidence=(f'{kind}: sân bay {top_key[0]} ({top_key[1]}) chiếm '
                  f'{r.iloc[0]/total*100:.2f}% số ghế của nhóm điểm đến đang phân tích '
                  f'trong {start}–{end}.')
        story('Sân bay đến nào nổi bật?',evidence,
              'Ghế bán đến các sân bay có mức độ tập trung khác nhau; cần xét cả xu hướng qua tháng.',
              'Ghế bán không phải số lượt khách thực bay; chỉ xét tập chuyến bay đủ điều kiện điểm đến và bộ lọc.')


def opposing_monthly_chart(code):
    """Comparative MoM series; users can see directions without interpreting an abstract r."""
    d=changes[changes.LOAI_CHUYEN_BAY==code].dropna(subset=['PCT_PRICE','PCT_SEATS']).sort_values('THANG')
    fig=go.Figure()
    fig.add_trace(go.Bar(name='Giá vé (%)',x=d['THANG'],y=d['PCT_PRICE'],marker_color=BLUE))
    fig.add_trace(go.Bar(name='Ghế bán (%)',x=d['THANG'],y=d['PCT_SEATS'],marker_color=ORANGE))
    fig.add_hline(y=0,line_color='#94AEC1',line_width=1)
    fig=theme(fig,300,'% so với tháng trước')
    fig.update_layout(barmode='group',legend=dict(orientation='h',x=0,y=1.17),margin=dict(l=10,r=10,t=48,b=35))
    return fig,len(d),int(((d['PCT_PRICE']*d['PCT_SEATS'])<0).sum())

if page.startswith('01'):
    section('01 | Tổng quan thị trường')
    nd=selected[selected['LOAI_CHUYEN_BAY']=='Noi dia'];qt=selected[selected['LOAI_CHUYEN_BAY']=='Quoc te']
    k1,k2,k3=st.columns(3)
    k1.metric('TỔNG GHẾ BÁN',f"{selected['SO_GHE_BAN'].sum():,.0f}")
    p1,p2=avg(nd),avg(qt)
    k2.metric('GIÁ NỘI ĐỊA',f'{p1:,.2f} BRL' if p1 is not None else 'Không áp dụng')
    k3.metric('GIÁ QUỐC TẾ',f'{p2:,.2f} USD' if p2 is not None else 'Không áp dụng')
    section('02 | Xu hướng giá vé')
    for col,code in zip(st.columns(len(chosen)),chosen):
        with col:panel('Giá vé | '+NAMES[code],'Bình quân có trọng số theo ghế · '+UNITS[code],line_chart(code,'GIA_BINH_QUAN'),'price_'+code)
    section('03 | Biến động giá theo tháng')
    for col,code in zip(st.columns(len(chosen)),chosen):
        with col:panel('Biến động | '+NAMES[code],'So với tháng trước (%)',change_chart(code,'PCT_PRICE'),'change_'+code)
    section('04 | Số ghế bán theo tháng')
    for col,code in zip(st.columns(len(chosen)),chosen):
        with col:panel('Ghế bán | '+NAMES[code],'Tổng ghế bán theo tháng',line_chart(code,'SO_GHE_BAN'),'seat_'+code)
    section('05 | Phát hiện nổi bật trong khoảng đang chọn')
    for code in chosen:
        d=selected[selected['LOAI_CHUYEN_BAY']==code]
        if d.empty:continue
        hi,lo,busy=d.loc[d['GIA_BINH_QUAN'].idxmax()],d.loc[d['GIA_BINH_QUAN'].idxmin()],d.loc[d['SO_GHE_BAN'].idxmax()]
        st.markdown('**'+NAMES[code]+'**')
        a,b,c=st.columns(3)
        with a:insight('GIÁ CAO NHẤT',f"{hi['GIA_BINH_QUAN']:,.2f} {UNITS[code]}",hi['THANG'])
        with b:insight('GIÁ THẤP NHẤT',f"{lo['GIA_BINH_QUAN']:,.2f} {UNITS[code]}",lo['THANG'])
        with c:insight('THÁNG BÁN NHIỀU GHẾ',f"{busy['SO_GHE_BAN']:,.0f}",busy['THANG'])

    section('06 | So sánh giá vé theo tháng giữa các năm')
    st.caption('Phần này dùng biểu đồ cột để đọc mức giá theo tháng rõ hơn Heatmap. Cột cùng tháng được nhóm theo năm; tháng thiếu dữ liệu sẽ không hiển thị cột.')
    for col,code in zip(st.columns(len(chosen)),chosen):
        with col:
            fig_cmp, years_cmp = monthly_price_compare(code)
            if fig_cmp is None:
                st.info(NAMES[code]+': không có dữ liệu trong khoảng đang chọn.')
            else:
                note = 'So sánh ' + ', '.join(str(y) for y in years_cmp) + ' · đơn vị ' + UNITS[code]
                panel('Giá theo tháng | '+NAMES[code], note, fig_cmp, 'price_compare_'+code)
    yoy_panels=[(code,*yoy_figure(code)) for code in chosen]
    if any(fig is not None for _,fig,_ in yoy_panels):
        section('07 | So sánh cùng kỳ năm trước (YoY)')
        st.caption('Chỉ so các tháng có dữ liệu ở cả hai năm; không lấy 2026-05 = 0. Chọn năm để đổi kỳ so sánh.')
        for col,(code,fig,meta) in zip(st.columns(len(chosen)),yoy_panels):
            with col:
                if fig is None:
                    st.caption(NAMES[code]+': chưa đủ dữ liệu hai năm để so sánh.')
                else:
                    panel('YoY | '+NAMES[code],
                          f'{meta["year"]} với {meta["previous"]} · {len(meta["months"])} tháng khớp: '
                          + ', '.join(f'{m:02}' for m in meta['months']),fig,'yoy_'+code)
    section('08 | Boxplot giá vé từ dữ liệu gốc')
    st.caption('Phân phối giá theo số ghế bán (P10, P25, trung vị, P75, P90). Rê chuột vào từng hộp để xem giá trị chi tiết. Râu P10–P90, không phải Tukey 1,5×IQR.')
    distribution_version=DISTRIBUTIONS.stat().st_mtime_ns if DISTRIBUTIONS.is_file() else None
    if distribution_version is None:
        st.warning('Chưa có thống kê phân phối giá để vẽ. Tạo năm 2024 bằng `build_fare_distributions.py`; để bổ sung 2025–2026 từ ANAC gốc, chạy `python data_warehouse/cap_nhat_phan_phoi_gia.py --limit 2`. Không sử dụng file `parts` đã tổng hợp làm dữ liệu giá gốc.')
    else:
        try:
            distributions=load_fare_distributions(distribution_version)
            shown_any=False
            for col,code in zip(st.columns(len(chosen)),chosen):
                with col:
                    f,sub=distribution_chart(distributions,code)
                    if f is None:
                        st.info(NAMES[code]+': chưa có dữ liệu phân phối giá trong khoảng '+start+' – '+end+'.')
                    else:
                        shown_any=True
                        panel('Phân phối giá | '+NAMES[code],f'{len(sub)} tháng có dữ liệu phân phối · '+UNITS[code],f,'box_'+code)
            if not shown_any:
                st.info('Khoảng thời gian đang chọn chưa có dữ liệu phân phối giá để vẽ Boxplot.')
        except Exception as ex:
            st.warning('Không đọc được phân phối giá: '+str(ex))

elif page.startswith('02'):
    section('01 | Mạng lưới tuyến bay ANAC')
    mc,ic=st.columns([2.5,1])
    with mc:
        f,n_air=map_chart();panel('Flight Route Network',f'{market} · Top {top} mỗi loại · {period_label}',f,'route_map')
    with ic:
        st.metric('SỐ TUYẾN HIỂN THỊ',len(route_sel));st.metric('SỐ SÂN BAY',n_air);st.metric('GHẾ CÓ THỂ VẼ BẢN ĐỒ',f"{route_sel['ASSENTOS'].sum():,.0f}")
        st.caption('DuckDB: Top tuyến theo đúng khoảng tháng đã chọn. Ở chế độ CSV dự phòng, xếp hạng tuyến chủ yếu theo năm và chỉ có Top 100/tập.')
    section('02 | Xếp hạng tuyến bay và cơ cấu')
    a,b=st.columns([1.5,1])
    with a:panel('Top 10 tuyến bay','Theo bộ lọc thời gian (DuckDB) hoặc theo năm (CSV)',top_chart(),'top')
    with b:panel('Tỷ trọng ghế trong dữ liệu','Hai tập ANAC, không phải toàn thị trường',share_chart(),'share')
    section('02B | Pareto · Mức độ tập trung số ghế theo tuyến')
    st.caption('Đường tích lũy sử dụng TOÀN BỘ tuyến trong khoảng lọc từ DuckDB; cột chỉ minh họa Top 20.')
    for col,code in zip(st.columns(len(chosen)),chosen):
        with col:
            if signature is None:st.info('Cần DuckDB để tính Pareto toàn mạng lưới cho '+NAMES[code]+'.')
            else:
                f,n80,nall=pareto_chart(code)
                if f is not None:
                    panel('Pareto | '+NAMES[code],f'{n80}/{nall} tuyến tạo nên ít nhất 80% ghế bán trong dữ liệu đã lọc',f,'pareto_'+code)
    section('02C | Dumbbell · Thay đổi ghế bán cùng tuyến qua hai năm')
    st.caption('Chỉ so tuyến xuất hiện ở cả hai năm và các tháng tương ứng; không gán 0 cho tuyến vắng dữ liệu.')
    for col,code in zip(st.columns(len(chosen)),chosen):
        with col:
            f,meta=dumbbell_chart(code)
            if f is None:st.info(NAMES[code]+': chưa có hai năm tương ứng và tuyến trùng để so sánh.')
            else:panel('Dumbbell | '+NAMES[code],
                       f'{meta["year"]} so với {meta["previous"]} · {len(meta["months"])} tháng khớp · Top 15 tuyến chung',
                       f,'dumbbell_'+code)
    section('03 | Biến động số ghế bán')
    for col,code in zip(st.columns(len(chosen)),chosen):
        with col:panel('Ghế bán | '+NAMES[code],'Thay đổi so với tháng trước (%)',change_chart(code,'PCT_SEATS'),'seat_change_'+code)
    section('04 | Giá vé và số ghế bán biến động thế nào?')
    st.caption('So sánh % biến động MoM cho từng tháng có kỳ liền trước. Màu xanh: giá vé; màu cam: số ghế bán. '
               'Đây là mô tả đồng/ngược chiều, không kết luận giá gây ra thay đổi số ghế.')
    for col,code in zip(st.columns(len(chosen)),chosen):
        fig,n,opp=opposing_monthly_chart(code)
        with col:
            panel('Biến động giá & ghế | '+NAMES[code],
                  f'{opp}/{n} kỳ có giá và ghế biến động ngược chiều (có đủ kỳ MoM)' if n else 'Chưa đủ hai tháng liên tiếp',
                  fig,'paired_mom_'+code)
    with st.expander('Xem thêm: Biểu đồ tương quan Pearson (phân tích thống kê)'):
        st.caption('Pearson r ≈ 0 nghĩa là không thấy liên hệ TUYẾN TÍNH rõ ràng trong phạm vi tháng đã lọc. '
                   'r âm không chứng minh tăng giá làm giảm lượng ghế.')
        for col,code in zip(st.columns(len(chosen)),chosen):
            fig,r=scatter_chart(code)
            n=len(selected[selected.LOAI_CHUYEN_BAY==code])
            with col:
                panel('Pearson | '+NAMES[code],
                      f'r = {r:.3f} · {pearson_label(r)} · {n} tháng' if pd.notna(r) else 'Không đủ số kỳ',
                      fig,'corr_'+code)
    render_business_insights()
    section('07 | Dữ liệu chi tiết và tải xuống')
    with st.expander('Bảng dữ liệu theo tháng'):
        st.dataframe(selected,height=260,hide_index=True,width="stretch")
        st.download_button('Tải dữ liệu tháng CSV',selected.to_csv(index=False).encode('utf-8-sig'),'phan_tich_thang.csv','text/csv')
    with st.expander('Danh sách tuyến bay'):
        cols=['LOAI','ORIGEM','DESTINO','ASSENTOS']
        st.dataframe(rank_routes[cols],height=260,hide_index=True,width="stretch")
        st.download_button('Tải tuyến bay CSV',rank_routes[cols].to_csv(index=False).encode('utf-8-sig'),'tuyen_bay.csv','text/csv')

else:
    section('01 | Xu hướng lựa chọn điểm đến')
    try:
        dest=(load_dw_destinations(signature,start,end,tuple(chosen))
              if signature is not None else load_csv_destinations())
    except FileNotFoundError:
        st.warning('Chưa có dữ liệu điểm đến. Hãy chạy: python phan_tich_diem_den.py');st.stop()
    except Exception as e:
        st.error(f'Lỗi đọc dữ liệu điểm đến: {e}');st.stop()
    dest=dest[dest['THANG'].between(start,end)].copy()
    if market!='Cả hai':dest=dest[dest['LOAI']==market].copy()
    st.caption('Xếp hạng dựa trên ghế bán và sân bay đến (DESTINO), không phải số khách du lịch thực tế. Chỉ xét quốc tế xuất phát từ Brazil.')
    if dest.empty:
        st.warning('Không có dữ liệu điểm đến với bộ lọc hiện tại.');st.stop()
    x1,x2,x3=st.columns(3)
    x1.metric('SỐ GHẾ TRONG DỮ LIỆU ĐIỂM ĐẾN',f"{dest['ASSENTOS'].sum():,.0f}")
    x2.metric('SỐ SÂN BAY ĐẾN',dest['DESTINO'].nunique())
    x3.metric('SỐ QUỐC GIA ĐẾN',dest['QUOC_GIA'].nunique())
    for market_name in ['Nội địa','Quốc tế']:
        if market!='Cả hai' and market!=market_name:continue
        subset=dest[dest['LOAI']==market_name]
        if subset.empty:continue
        section(('02' if market_name=='Nội địa' else '03')+' | Điểm đến '+market_name.lower()+' được mua vé nhiều')
        rank,prepared=ranking_destinations(dest,market_name,'DIA_DIEM',dest_top)
        col1,col2=st.columns([1,1.35])
        with col1:panel('Top điểm đến '+market_name.lower(),f'Top {dest_top} thành phố theo ghế bán',ranking_chart(rank,COLORS[market_name]),'dest_rank_'+market_name)
        with col2:panel('Xu hướng mua vé của Top 5', 'Theo tháng bán vé, không phải tháng khởi hành',destination_month_chart(prepared,rank),'dest_month_'+market_name)
        if market_name=='Quốc tế':
            rank_ctry,_=ranking_destinations(dest,market_name,'QUOC_GIA',10)
            panel('Top quốc gia điểm đến','Mã quốc gia ISO 3166-1 alpha-2',ranking_chart(rank_ctry,ORANGE),'countries_rank')
    section('04 | Bản đồ các điểm đến nổi bật')
    with st.container(border=True):
        st.caption('Chấm sân bay nhỏ 5 px. Rê chuột để xem tên điểm đến, mã sân bay và số ghế bán trong khoảng tháng đã chọn.')
        plot(destinations_map(dest,dest_top),'destination_map')
    with st.expander('Bảng chi tiết điểm đến và tải CSV'):
        result=dest.sort_values('ASSENTOS',ascending=False)
        st.dataframe(result,height=290,hide_index=True,width="stretch")
        st.download_button('Tải dữ liệu điểm đến CSV',result.to_csv(index=False).encode('utf-8-sig'),'diem_den.csv','text/csv')
    destination_insight(dest)
    st.caption('Giới hạn: đây là tháng bán vé, không phải tháng khởi hành. Ghế bán không xác nhận hành khách thực đi hay mục đích du lịch. Chỉ các tuyến có sân bay đi thuộc BR và sân bay đến phân loại được mới vào dữ liệu điểm đến.')

st.divider()
st.caption('Nguồn phân tích: '+data_source+'. Dữ liệu gốc: ANAC Brazil và OurAirports. Dữ liệu hiển thị theo các tháng đã được nhập thành công. Giá nội địa (BRL) và quốc tế (USD) không so sánh trực tiếp; định nghĩa thống kê nội địa có thể thay đổi từ 2026. Bản đồ nối sân bay không thể hiện đường bay thực tế.')
