
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# ==========================================
# 1. CAU HINH
# ==========================================

st.set_page_config(
    page_title="Brazil Flight Route Network",
    page_icon=None,
    layout="wide"
)

goc = Path(__file__).resolve().parent.parent
folder = goc / "KetQua_ETL_2024"

# ==========================================
# 2. CSS - PEARL LIGHT
# ==========================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(
        120deg, #F5F9FD, #FFF8F2
    );
}
.block-container {
    max-width: 1500px;
    padding-top: 1.5rem;
}
h1, h2, h3 {
    color: #2A4863;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. DOC DU LIEU TOP 100
# ==========================================

@st.cache_data
def doc_du_lieu():

    nd = pd.read_csv(
        folder / "top100_noi_dia_toa_do.csv",
        encoding="utf-8-sig"
    )

    qt = pd.read_csv(
        folder / "top100_quoc_te_toa_do.csv",
        encoding="utf-8-sig"
    )

    nd["LOAI"] = "Nội địa"
    qt["LOAI"] = "Quốc tế"

    df = pd.concat(
        [nd, qt],
        ignore_index=True
    )

    cot_so = [
        "ASSENTOS",
        "LAT_DI", "LON_DI",
        "LAT_DEN", "LON_DEN"
    ]

    for cot in cot_so:
        df[cot] = pd.to_numeric(
            df[cot],
            errors="coerce"
        )

    df = df.dropna(subset=cot_so).copy()

    return df


df = doc_du_lieu()

# ==========================================
# 4. TIEU DE
# ==========================================

st.markdown("#### AVIATION INTELLIGENCE / BRAZIL 2024")

st.title("Flight Route Network")

st.caption(
    "Bản đồ các tuyến bay có số ghế bán cao nhất "
    "trong dữ liệu ANAC năm 2024."
)

# ==========================================
# 5. BO LOC TUONG TAC
# ==========================================

cot1, cot2, cot3 = st.columns([1, 1, 2])

with cot1:
    loai = st.selectbox(
        "Loại chuyến bay",
        ["Cả hai", "Nội địa", "Quốc tế"]
    )

with cot2:
    top = st.selectbox(
        "Số tuyến mỗi loại",
        [20, 50, 100],
        index=1,
        format_func=lambda x: f"Top {x}"
    )

with cot3:
    st.markdown(
        """
        <div style="
            padding: 27px 0 0;
            color: #71879B;
            font-size: 13px;
        ">
            Xanh dương: Nội địa &nbsp;&nbsp;&nbsp;
            Cam: Quốc tế
        </div>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# 6. LOC DU LIEU
# ==========================================

if loai == "Cả hai":
    df_loc = df.copy()
else:
    df_loc = df[df["LOAI"] == loai].copy()

df_loc = (
    df_loc
    .sort_values(
        ["LOAI", "ASSENTOS"],
        ascending=[True, False]
    )
    .groupby("LOAI", group_keys=False)
    .head(top)
    .copy()
)

# ==========================================
# 7. TAO BAN DO
# ==========================================

fig = go.Figure()

mau = {
    "Nội địa": "#378FC4",
    "Quốc tế": "#E99568"
}

for _, r in df_loc.iterrows():

    color = mau[r["LOAI"]]

    # Duong bay manh, khong che ban do
    fig.add_trace(
        go.Scattergeo(
            lon=[r["LON_DI"], r["LON_DEN"]],
            lat=[r["LAT_DI"], r["LAT_DEN"]],
            mode="lines",
            line=dict(
                color=color,
                width=1.2
            ),
            opacity=0.48,
            hoverinfo="skip",
            showlegend=False
        )
    )

# ==========================================
# 8. TAO DANH SACH SAN BAY
# ==========================================

san_bay_di = df_loc[
    ["ORIGEM", "TEN_DI", "LAT_DI", "LON_DI"]
].rename(columns={
    "ORIGEM": "MA",
    "TEN_DI": "TEN",
    "LAT_DI": "LAT",
    "LON_DI": "LON"
})

san_bay_den = df_loc[
    ["DESTINO", "TEN_DEN", "LAT_DEN", "LON_DEN"]
].rename(columns={
    "DESTINO": "MA",
    "TEN_DEN": "TEN",
    "LAT_DEN": "LAT",
    "LON_DEN": "LON"
})

san_bay = pd.concat(
    [san_bay_di, san_bay_den],
    ignore_index=True
).drop_duplicates(subset="MA")

# ==========================================
# 9. VE CHAM SAN BAY NHO
# ==========================================

fig.add_trace(
    go.Scattergeo(
        lon=san_bay["LON"],
        lat=san_bay["LAT"],
        mode="markers",

        # Chi 4 px, khong co vong tron to
        marker=dict(
            size=4,
            color="#285876",
            opacity=0.85
        ),

        text=san_bay["MA"],
        customdata=san_bay["TEN"],

        hovertemplate=(
            "<b>%{text}</b><br>"
            "%{customdata}"
            "<extra></extra>"
        ),

        name="Sân bay"
    )
)

# ==========================================
# 10. THEM CHU GIAI
# ==========================================

for ten in ["Nội địa", "Quốc tế"]:

    if (
        loai != "Cả hai"
        and loai != ten
    ):
        continue

    fig.add_trace(
        go.Scattergeo(
            lat=[None],
            lon=[None],
            mode="lines",
            line=dict(
                color=mau[ten],
                width=3
            ),
            name=ten
        )
    )

# ==========================================
# 11. THIET KE BAN DO
# ==========================================

# Chi co noi dia thi zoom vao Brazil.
# Quoc te thi de Plotly tu can khung.
if loai == "Nội địa":
    geo_view = dict(
        projection=dict(type="mercator"),
        lataxis=dict(range=[-35, 7]),
        lonaxis=dict(range=[-76, -32])
    )
else:
    geo_view = dict(
        projection=dict(type="natural earth"),
        fitbounds="locations"
    )

fig.update_layout(
    height=640,

    margin=dict(
        l=5, r=5, t=10, b=5
    ),

    paper_bgcolor="#FFFFFF",

    font=dict(
        family="Arial",
        color="#344F69"
    ),

    legend=dict(
        orientation="h",
        x=0.02,
        y=0.02,
        bgcolor="rgba(255,255,255,0.9)"
    ),

    geo=dict(
        **geo_view,

        showland=True,
        landcolor="#EAF1F7",

        showocean=True,
        oceancolor="#F7FBFF",

        showcountries=True,
        countrycolor="#CBD7E2",

        showcoastlines=True,
        coastlinecolor="#CDD9E3",

        bgcolor="#FFFFFF",

        showframe=False
    )
)

# ==========================================
# 12. HIEN THI BAN DO
# ==========================================

with st.container(border=True):

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": True
        }
    )

# ==========================================
# 13. THONG KE PHIA DUOI
# ==========================================

c1, c2, c3 = st.columns(3)

c1.metric(
    "Số tuyến đang hiển thị",
    f"{len(df_loc):,}"
)

c2.metric(
    "Số sân bay",
    f"{len(san_bay):,}"
)

c3.metric(
    "Tổng ghế bán trên các tuyến đã chọn",
    f"{df_loc['ASSENTOS'].sum():,.0f}"
)

st.caption(
    "Nguồn: ANAC 2024 và tọa độ OurAirports. "
    "Số ghế bán là tổng trong các tuyến được chọn, "
    "không phải toàn bộ thị trường hàng không Brazil."
)

# ==========================================
# 14. BANG CHI TIET TUYEN BAY
# ==========================================

with st.expander("Xem danh sách tuyến bay"):

    bang = df_loc[
        ["LOAI", "ORIGEM", "DESTINO", "ASSENTOS"]
    ].sort_values(
        "ASSENTOS",
        ascending=False
    )

    st.dataframe(
        bang,
        use_container_width=True,
        hide_index=True
    )
