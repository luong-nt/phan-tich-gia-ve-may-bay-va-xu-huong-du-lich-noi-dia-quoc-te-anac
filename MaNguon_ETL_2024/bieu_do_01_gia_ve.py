
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# =====================================
# 1. DOC DU LIEU DA XU LY
# =====================================

goc = Path(__file__).resolve().parent.parent

file = goc / "KetQua_ETL_2024" / "chi_so_phan_tich_2024.csv"

df = pd.read_csv(
    file,
    sep=";",
    encoding="utf-8-sig"
)

# Sap xep theo thoi gian
df = df.sort_values("THANG")

# Tach 2 loai chuyen bay
nd = df[df["LOAI_CHUYEN_BAY"] == "Noi dia"]
qt = df[df["LOAI_CHUYEN_BAY"] == "Quoc te"]

# =====================================
# 2. TAO BIEU DO
# =====================================

fig = make_subplots(
    rows=2,
    cols=1,
    subplot_titles=[
        "Giá vé máy bay nội địa (BRL)",
        "Giá vé máy bay quốc tế (USD)"
    ],
    vertical_spacing=0.18
)

# Bieu do noi dia
fig.add_trace(
    go.Scatter(
        x=nd["THANG"],
        y=nd["GIA_BINH_QUAN"],
        mode="lines+markers",
        name="Nội địa",
        line=dict(color="#168A9B", width=3),
        marker=dict(size=8),
        hovertemplate=(
            "Tháng: %{x}<br>"
            "Giá bình quân: %{y:,.2f} BRL"
            "<extra></extra>"
        )
    ),
    row=1,
    col=1
)

# Bieu do quoc te
fig.add_trace(
    go.Scatter(
        x=qt["THANG"],
        y=qt["GIA_BINH_QUAN"],
        mode="lines+markers",
        name="Quốc tế",
        line=dict(color="#E58A35", width=3),
        marker=dict(size=8),
        hovertemplate=(
            "Tháng: %{x}<br>"
            "Giá bình quân: %{y:,.2f} USD"
            "<extra></extra>"
        )
    ),
    row=2,
    col=1
)

# =====================================
# 3. TRANG TRI BIEU DO
# =====================================

fig.update_layout(
    title=dict(
        text="BIẾN ĐỘNG GIÁ VÉ MÁY BAY TẠI BRAZIL NĂM 2024",
        x=0.5
    ),
    template="plotly_white",
    height=950,
    margin=dict(t=140, b=100, l=90, r=60),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        y=-0.12,
        x=0.5,
        xanchor="center"
    )
)

fig.update_xaxes(
    title_text="Tháng",
    type="category",
    row=1,
    col=1
)

fig.update_xaxes(
    title_text="Tháng",
    type="category",
    row=2,
    col=1
)

fig.update_yaxes(
    title_text="Giá vé bình quân (BRL)",
    row=1,
    col=1
)

fig.update_yaxes(
    title_text="Giá vé bình quân (USD)",
    row=2,
    col=1
)

# =====================================
# 4. LUU VA HIEN THI
# =====================================

folder = goc / "BieuDo"
folder.mkdir(exist_ok=True)

file_html = folder / "bieu_do_01_gia_ve.html"

fig.write_html(file_html)

fig.show()

print("Da tao bieu do thanh cong!")
print("File bieu do:", file_html)
