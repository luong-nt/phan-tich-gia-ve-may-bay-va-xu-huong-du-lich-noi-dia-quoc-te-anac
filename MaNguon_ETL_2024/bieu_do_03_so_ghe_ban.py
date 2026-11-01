
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

df = df.sort_values("THANG")

nd = df[df["LOAI_CHUYEN_BAY"] == "Noi dia"]
qt = df[df["LOAI_CHUYEN_BAY"] == "Quoc te"]

# =====================================
# 2. TAO HAI BIEU DO DUONG
# =====================================

fig = make_subplots(
    rows=2,
    cols=1,
    subplot_titles=[
        "Số ghế bán trên chuyến bay nội địa",
        "Số ghế bán trên chuyến bay quốc tế"
    ],
    vertical_spacing=0.18
)

# Noi dia
fig.add_trace(
    go.Scatter(
        x=nd["THANG"],
        y=nd["SO_GHE_BAN"],
        mode="lines+markers",
        name="Nội địa",
        line=dict(color="#168A9B", width=3),
        marker=dict(size=9),
        hovertemplate=(
            "Tháng: %{x}<br>"
            "Số ghế bán: %{y:,.0f}"
            "<extra></extra>"
        )
    ),
    row=1,
    col=1
)

# Quoc te
fig.add_trace(
    go.Scatter(
        x=qt["THANG"],
        y=qt["SO_GHE_BAN"],
        mode="lines+markers",
        name="Quốc tế",
        line=dict(color="#E58A35", width=3),
        marker=dict(size=9),
        hovertemplate=(
            "Tháng: %{x}<br>"
            "Số ghế bán: %{y:,.0f}"
            "<extra></extra>"
        )
    ),
    row=2,
    col=1
)

# =====================================
# 3. DINH DANG
# =====================================

fig.update_layout(
    title=dict(
        text="XU HƯỚNG SỐ GHẾ BÁN TRÊN CÁC CHUYẾN BAY NĂM 2024",
        x=0.5
    ),
    template="plotly_white",
    height=950,
    margin=dict(t=140, b=100, l=100, r=60),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        x=0.5,
        y=-0.12,
        xanchor="center"
    )
)

fig.update_xaxes(
    title_text="Tháng",
    type="category"
)

fig.update_yaxes(
    title_text="Số ghế bán",
    rangemode="tozero",
    tickformat=","
)

# =====================================
# 4. LUU VA HIEN THI
# =====================================

folder = goc / "BieuDo"
folder.mkdir(exist_ok=True)

file_html = folder / "bieu_do_03_so_ghe_ban.html"

fig.write_html(file_html)
fig.show()

print("Da tao bieu do 3 thanh cong!")
print("File:", file_html)
