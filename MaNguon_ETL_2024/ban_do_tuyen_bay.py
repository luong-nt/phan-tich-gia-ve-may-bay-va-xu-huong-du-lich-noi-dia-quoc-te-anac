
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from html import escape

# ==========================================
# 1. DUONG DAN DU AN
# ==========================================

goc = Path(__file__).resolve().parent.parent

thu_muc_du_lieu = goc / "KetQua_ETL_2024"
thu_muc_bieu_do = goc / "BieuDo"

thu_muc_bieu_do.mkdir(exist_ok=True)

file_noi_dia = (
    thu_muc_du_lieu /
    "top10_tuyen_noi_dia_2024_toa_do.csv"
)

file_quoc_te = (
    thu_muc_du_lieu /
    "top10_tuyen_quoc_te_2024_toa_do.csv"
)

# ==========================================
# 2. DOC DU LIEU
# ==========================================

nd = pd.read_csv(
    file_noi_dia,
    sep=";",
    encoding="utf-8-sig"
)

qt = pd.read_csv(
    file_quoc_te,
    sep=";",
    encoding="utf-8-sig"
)

nd["LOAI"] = "Nội địa"
qt["LOAI"] = "Quốc tế"

# ==========================================
# 3. BO SUNG TOA DO SPJC
# ==========================================

# Toa do tham khao san bay Jorge Chavez,
# Lima, Peru (SPJC).
# Dung de minh hoa vi tri san bay.

qt.loc[
    qt["DESTINO"] == "SPJC",
    "TEN_DEN"
] = "Jorge Chavez International Airport"

qt.loc[
    qt["DESTINO"] == "SPJC",
    "LAT_DEN"
] = -12.0219

qt.loc[
    qt["DESTINO"] == "SPJC",
    "LON_DEN"
] = -77.1143

# ==========================================
# 4. GOP DU LIEU
# ==========================================

df = pd.concat(
    [nd, qt],
    ignore_index=True
)

# Chuyen cac cot sang dang so
cot_so = [
    "LAT_DI", "LON_DI",
    "LAT_DEN", "LON_DEN",
    "ASSENTOS"
]

for cot in cot_so:
    df[cot] = pd.to_numeric(
        df[cot],
        errors="coerce"
    )

# Kiem tra toa do va so ghe
truoc = len(df)

df = df.dropna(
    subset=cot_so
).copy()

print("Tong so tuyen ban dau:", truoc)
print("So tuyen du toa do:", len(df))
print("So tuyen bi loai:", truoc - len(df))

if df.empty:
    raise ValueError(
        "Khong co tuyen bay hop le de ve ban do."
    )

# Tao cot ten tuyen
df["TUYEN_BAY"] = (
    df["ORIGEM"].astype(str)
    + " → " +
    df["DESTINO"].astype(str)
)

# ==========================================
# 5. MAU SAC GIAO DIEN
# ==========================================

mau = {
    "Nội địa": "#328CC1",
    "Quốc tế": "#EE976C"
}

mau_nen = "#F8FAFD"
mau_dat = "#E9F0F6"
mau_bien = "#F3F9FE"
mau_chu = "#304B65"

# ==========================================
# 6. HAM TINH DO DAY DUONG BAY
# ==========================================

min_ghe = df["ASSENTOS"].min()
max_ghe = df["ASSENTOS"].max()

def do_day(so_ghe):
    if max_ghe == min_ghe:
        return 3

    return 1.8 + (
        (so_ghe - min_ghe) /
        (max_ghe - min_ghe)
    ) * 4.5

# ==========================================
# 7. KHOI TAO BAN DO
# ==========================================

fig = go.Figure()

# ==========================================
# 8. VE CAC DUONG BAY
# ==========================================

for _, r in df.iterrows():

    loai = r["LOAI"]
    color = mau[loai]

    ma_di = escape(str(r["ORIGEM"]))
    ma_den = escape(str(r["DESTINO"]))

    ten_di = escape(str(r["TEN_DI"]))
    ten_den = escape(str(r["TEN_DEN"]))

    so_ghe = int(r["ASSENTOS"])

    thong_tin = (
        f"<b>{ma_di} → {ma_den}</b><br>"
        f"Loại chuyến: {loai}<br>"
        f"Sân bay đi: {ten_di}<br>"
        f"Sân bay đến: {ten_den}<br>"
        f"Số ghế bán: {so_ghe:,}"
    )

    fig.add_trace(
        go.Scattergeo(
            lon=[
                r["LON_DI"],
                r["LON_DEN"]
            ],
            lat=[
                r["LAT_DI"],
                r["LAT_DEN"]
            ],
            mode="lines",
            line=dict(
                width=do_day(so_ghe),
                color=color
            ),
            opacity=0.73,
            text=[thong_tin, thong_tin],
            hovertemplate="%{text}<extra></extra>",
            showlegend=False
        )
    )

# ==========================================
# 9. TAO BANG TOA DO SAN BAY
# ==========================================

san_bay_di = df[
    [
        "ORIGEM",
        "TEN_DI",
        "LAT_DI",
        "LON_DI"
    ]
].rename(
    columns={
        "ORIGEM": "MA",
        "TEN_DI": "TEN",
        "LAT_DI": "LAT",
        "LON_DI": "LON"
    }
)

san_bay_den = df[
    [
        "DESTINO",
        "TEN_DEN",
        "LAT_DEN",
        "LON_DEN"
    ]
].rename(
    columns={
        "DESTINO": "MA",
        "TEN_DEN": "TEN",
        "LAT_DEN": "LAT",
        "LON_DEN": "LON"
    }
)

san_bay = pd.concat(
    [san_bay_di, san_bay_den],
    ignore_index=True
)

san_bay = san_bay.drop_duplicates(
    subset="MA"
)

# ==========================================
# 10. VE CAC DIEM SAN BAY
# ==========================================

fig.add_trace(
    go.Scattergeo(
        lon=san_bay["LON"],
        lat=san_bay["LAT"],
        mode="markers+text",
        text=san_bay["MA"],
        textposition="top center",
        textfont=dict(
            size=9,
            color=mau_chu
        ),
        marker=dict(
            size=7,
            color="#315A7D",
            line=dict(
                color="white",
                width=1.5
            )
        ),
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
# 11. CHU GIAI HAI LOAI TUYEN
# ==========================================

for loai, color in mau.items():

    fig.add_trace(
        go.Scattergeo(
            lon=[None],
            lat=[None],
            mode="lines",
            line=dict(
                color=color,
                width=4
            ),
            name=loai
        )
    )

# ==========================================
# 12. THIET KE BAN DO PEARL LIGHT
# ==========================================

fig.update_layout(
    title=dict(
        text=(
            "<b>BRAZIL AVIATION ROUTE MAP</b>"
            "<br>"
            "<span style='font-size:13px;"
            "color:#7C90A4'>"
            "Top 10 tuyến nội địa và "
            "Top 10 tuyến quốc tế theo số ghế bán"
            " | ANAC 2024"
            "</span>"
        ),
        x=0.5,
        xanchor="center",
        font=dict(
            size=21,
            color=mau_chu
        )
    ),

    height=750,

    margin=dict(
        l=15,
        r=15,
        t=100,
        b=15
    ),

    paper_bgcolor=mau_nen,
    plot_bgcolor=mau_nen,

    font=dict(
        family="Arial, sans-serif",
        color=mau_chu
    ),

    legend=dict(
        orientation="h",
        x=0.5,
        xanchor="center",
        y=0.02,
        yanchor="bottom",
        bgcolor="rgba(255,255,255,0.88)",
        bordercolor="#E1E9F0",
        borderwidth=1
    ),

    geo=dict(
        projection=dict(
            type="natural earth"
        ),

        # Tu dong zoom de thay cac tuyen bay
        fitbounds="locations",

        showland=True,
        landcolor=mau_dat,

        showocean=True,
        oceancolor=mau_bien,

        showcountries=True,
        countrycolor="#C6D3DF",

        showcoastlines=True,
        coastlinecolor="#BDCBD8",

        showlakes=True,
        lakecolor=mau_bien,

        # SUA LOI GRIDCOLOR:
        # Mau luoi phai nam trong
        # lataxis va lonaxis
        lataxis=dict(
            showgrid=True,
            gridcolor="#DCE7F0",
            gridwidth=0.5
        ),

        lonaxis=dict(
            showgrid=True,
            gridcolor="#DCE7F0",
            gridwidth=0.5
        ),

        bgcolor=mau_nen
    )
)

# ==========================================
# 13. LUU VA MO BAN DO
# ==========================================

file_html = (
    thu_muc_bieu_do /
    "ban_do_tuyen_bay_2024.html"
)

fig.write_html(
    str(file_html),
    include_plotlyjs=True
)

print("\nDA TAO BAN DO THANH CONG!")
print("File:", file_html)
print("So san bay:", len(san_bay))
print("So tuyen noi dia:", len(nd))
print("So tuyen quoc te:", len(qt))

fig.show()
