
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# =====================================
# 1. DOC DU LIEU
# =====================================

goc = Path(__file__).resolve().parent.parent

file = (
    goc / "KetQua_ETL_2024"
    / "chi_so_phan_tich_2024.csv"
)

df = pd.read_csv(
    file,
    sep=";",
    encoding="utf-8-sig"
)

# Tach du lieu noi dia va quoc te
nd = df[df["LOAI_CHUYEN_BAY"] == "Noi dia"].copy()
qt = df[df["LOAI_CHUYEN_BAY"] == "Quoc te"].copy()

# =====================================
# 2. TAO HAI BIEU DO PHAN TAN
# =====================================

fig = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=[
        "Nội địa (BRL)",
        "Quốc tế (USD)"
    ],
    horizontal_spacing=0.14
)

ds = [
    (nd, "Nội địa", "#168A9B", 1),
    (qt, "Quốc tế", "#E58A35", 2)
]

# =====================================
# 3. VE CAC DIEM VA DUONG XU HUONG
# =====================================

for data, ten, mau, cot in ds:

    x = data["GIA_BINH_QUAN"].to_numpy()
    y = data["SO_GHE_BAN"].to_numpy()

    # He so tuong quan Pearson
    r = data["GIA_BINH_QUAN"].corr(
        data["SO_GHE_BAN"]
    )

    # Ve cac diem
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers+text",
            text=data["THANG"].str[-2:],
            textposition="top center",
            marker=dict(
                color=mau,
                size=12,
                opacity=0.85
            ),
            name=ten,
            customdata=data["THANG"],
            hovertemplate=(
                "Tháng: %{customdata}<br>"
                "Giá bình quân: %{x:,.2f}<br>"
                "Số ghế bán: %{y:,.0f}"
                "<extra></extra>"
            )
        ),
        row=1,
        col=cot
    )

    # Tinh duong xu huong tuyen tinh
    a, b = np.polyfit(x, y, 1)

    x_line = np.linspace(x.min(), x.max(), 100)
    y_line = a * x_line + b

    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            line=dict(
                color=mau,
                width=2,
                dash="dash"
            ),
            name=f"Xu hướng {ten}",
            showlegend=False,
            hoverinfo="skip"
        ),
        row=1,
        col=cot
    )

    print(f"{ten}: Pearson r = {r:.4f}")

    # Hien thi he so tuong quan
    fig.add_annotation(
        x=0.5,
        y=1.13,
        xref="x domain" if cot == 1 else "x2 domain",
        yref="y domain" if cot == 1 else "y2 domain",
        text=f"Pearson r = {r:.3f}",
        showarrow=False,
        font=dict(size=14, color=mau)
    )

# =====================================
# 4. DINH DANG BIEU DO
# =====================================

fig.update_layout(
    title=dict(
        text=(
            "MỐI LIÊN HỆ GIỮA GIÁ VÉ VÀ "
            "SỐ GHẾ BÁN NĂM 2024"
        ),
        x=0.5
    ),
    template="plotly_white",
    height=650,
    margin=dict(t=150, b=100, l=95, r=65),
    legend=dict(
        orientation="h",
        x=0.5,
        xanchor="center",
        y=-0.22
    )
)

fig.update_xaxes(
    title_text="Giá bình quân (BRL)",
    row=1, col=1
)

fig.update_xaxes(
    title_text="Giá bình quân (USD)",
    row=1, col=2
)

fig.update_yaxes(
    title_text="Số ghế bán",
    tickformat=",",
    row=1, col=1
)

fig.update_yaxes(
    title_text="Số ghế bán",
    tickformat=",",
    row=1, col=2
)

# =====================================
# 5. LUU VA HIEN THI
# =====================================

folder = goc / "BieuDo"
folder.mkdir(exist_ok=True)

file_html = folder / "bieu_do_05_gia_va_so_ghe.html"

fig.write_html(file_html)
fig.show()

print("\nDa tao bieu do 5 thanh cong!")
print("File:", file_html)
