
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# =====================================
# 1. DOC DU LIEU
# =====================================

goc = Path(__file__).resolve().parent.parent

file = goc / "KetQua_ETL_2024" / "chi_so_phan_tich_2024.csv"

df = pd.read_csv(
    file,
    sep=";",
    encoding="utf-8-sig"
)

# Sap xep theo thang
df = df.sort_values("THANG")

# Bo thang 1 vi khong co thang truoc de so sanh
df = df.dropna(subset=["BIEN_DONG_GIA_PCT"])

nd = df[df["LOAI_CHUYEN_BAY"] == "Noi dia"]
qt = df[df["LOAI_CHUYEN_BAY"] == "Quoc te"]

# =====================================
# 2. TAO 2 BIEU DO COT
# =====================================

fig = make_subplots(
    rows=2,
    cols=1,
    subplot_titles=[
        "Biến động giá vé nội địa",
        "Biến động giá vé quốc tế"
    ],
    vertical_spacing=0.19
)

# Ve bieu do cho tung loai
for i, (data, ten) in enumerate([
    (nd, "Nội địa"),
    (qt, "Quốc tế")
], start=1):

    # Tang gia: xanh, giam gia: do
    mau = [
        "#16A34A" if x >= 0 else "#DC2626"
        for x in data["BIEN_DONG_GIA_PCT"]
    ]

    fig.add_trace(
        go.Bar(
            x=data["THANG"],
            y=data["BIEN_DONG_GIA_PCT"],
            marker_color=mau,
            text=data["BIEN_DONG_GIA_PCT"].map(
                lambda x: f"{x:+.2f}%"
            ),
            textposition="outside",
            cliponaxis=False,
            name=ten,
            hovertemplate=(
                "Tháng: %{x}<br>"
                "Biến động giá: %{y:+.2f}%"
                "<extra></extra>"
            )
        ),
        row=i,
        col=1
    )

# =====================================
# 3. DINH DANG BIEU DO
# =====================================

fig.update_layout(
    title=dict(
        text="TỶ LỆ TĂNG/GIẢM GIÁ VÉ MÁY BAY BRAZIL NĂM 2024",
        x=0.5
    ),
    template="plotly_white",
    height=950,
    margin=dict(t=140, b=90, l=90, r=60),
    showlegend=False,
    bargap=0.35
)

# Duong muc 0%
fig.add_hline(
    y=0,
    line_color="gray",
    line_width=1,
    row=1,
    col=1
)

fig.add_hline(
    y=0,
    line_color="gray",
    line_width=1,
    row=2,
    col=1
)

fig.update_yaxes(
    title_text="Thay đổi (%)",
    ticksuffix="%",
    row=1,
    col=1
)

fig.update_yaxes(
    title_text="Thay đổi (%)",
    ticksuffix="%",
    row=2,
    col=1
)

fig.update_xaxes(
    title_text="Tháng",
    type="category"
)

# =====================================
# 4. LUU VA HIEN THI
# =====================================

folder = goc / "BieuDo"
folder.mkdir(exist_ok=True)

file_html = folder / "bieu_do_02_bien_dong_gia.html"

fig.write_html(file_html)
fig.show()

print("Da tao bieu do 2 thanh cong!")
print("File:", file_html)
