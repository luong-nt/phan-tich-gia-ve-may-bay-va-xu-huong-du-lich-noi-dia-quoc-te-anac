
import pandas as pd
import plotly.graph_objects as go
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

# =====================================
# 2. TINH LAI TY TRONG TU SO GHE
# =====================================

bang = df.pivot(
    index="THANG",
    columns="LOAI_CHUYEN_BAY",
    values="SO_GHE_BAN"
).sort_index()

# Tong so ghe moi thang
tong = bang["Noi dia"] + bang["Quoc te"]

# Tinh ty trong chinh xac
pct_nd = bang["Noi dia"] / tong * 100
pct_qt = bang["Quoc te"] / tong * 100

# Kiem tra tong ty trong
assert ((pct_nd + pct_qt - 100).abs() < 0.0001).all()

# =====================================
# 3. TAO BIEU DO COT CHONG 100%
# =====================================

fig = go.Figure()

fig.add_trace(
    go.Bar(
        x=bang.index,
        y=pct_nd,
        name="Nội địa",
        marker_color="#168A9B",
        customdata=bang["Noi dia"],
        text=[f"{x:.2f}%" for x in pct_nd],
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate=(
            "Tháng: %{x}<br>"
            "Loại: Nội địa<br>"
            "Số ghế: %{customdata:,.0f}<br>"
            "Tỷ trọng: %{y:.2f}%"
            "<extra></extra>"
        )
    )
)

fig.add_trace(
    go.Bar(
        x=bang.index,
        y=pct_qt,
        name="Quốc tế",
        marker_color="#E58A35",
        customdata=bang["Quoc te"],
        text=[f"{x:.2f}%" for x in pct_qt],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(
            color="white",
            size=12
        ),
        hovertemplate=(
            "Tháng: %{x}<br>"
            "Loại: Quốc tế<br>"
            "Số ghế: %{customdata:,.0f}<br>"
            "Tỷ trọng: %{y:.2f}%"
            "<extra></extra>"
        )
    )
)

# =====================================
# 4. DINH DANG BIEU DO
# =====================================

fig.update_layout(
    title=dict(
        text=(
            "CƠ CẤU SỐ GHẾ BÁN ĐƯỢC GHI NHẬN "
            "TRONG DỮ LIỆU ANAC NĂM 2024"
        ),
        x=0.5,
        font=dict(size=19)
    ),
    barmode="stack",
    template="plotly_white",
    height=720,
    margin=dict(t=120, b=145, l=90, r=60),
    legend=dict(
        orientation="h",
        x=0.5,
        xanchor="center",
        y=-0.16
    ),
    uniformtext=dict(
        minsize=10,
        mode="hide"
    )
)

fig.update_xaxes(
    title_text="Tháng bán vé",
    type="category"
)

fig.update_yaxes(
    title_text="Tỷ trọng (%)",
    range=[0, 100],
    ticksuffix="%"
)

# Ghi chu pham vi du lieu
fig.add_annotation(
    text=(
        "Lưu ý: Tỷ trọng được tính trong phạm vi "
        "hai bộ dữ liệu ANAC, không đại diện "
        "cho toàn bộ thị trường du lịch Brazil."
    ),
    xref="paper",
    yref="paper",
    x=0.5,
    y=-0.27,
    showarrow=False,
    font=dict(size=12, color="#64748B"),
    xanchor="center"
)

# =====================================
# 5. LUU VA HIEN THI
# =====================================

folder = goc / "BieuDo"
folder.mkdir(exist_ok=True)

file_html = folder / "bieu_do_04_ty_trong.html"

fig.write_html(file_html)
fig.show()

print("Da cap nhat bieu do 4 thanh cong!")
print("File:", file_html)
