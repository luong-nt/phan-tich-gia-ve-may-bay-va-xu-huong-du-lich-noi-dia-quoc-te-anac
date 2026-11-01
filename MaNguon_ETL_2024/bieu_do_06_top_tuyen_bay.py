
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# =====================================
# 1. DUONG DAN
# =====================================

goc = Path(__file__).resolve().parent.parent
folder = goc / "KetQua_ETL_2024"

ds = [
    ("Nội địa", "noi_dia_sach_2024.csv"),
    ("Quốc tế", "quoc_te_sach_2024.csv")
]

ket_qua = {}

# =====================================
# 2. TINH TONG GHE THEO TUYEN
# =====================================

for loai, ten_file in ds:

    print(f"Dang xu ly: {loai}")

    ds_nhom = []

    # Doc theo tung phan de tiet kiem RAM
    for df in pd.read_csv(
        folder / ten_file,
        sep=";",
        encoding="utf-8-sig",
        usecols=["ORIGEM", "DESTINO", "ASSENTOS"],
        chunksize=50000
    ):

        # Chuan hoa ma san bay
        df["ORIGEM"] = df["ORIGEM"].str.strip().str.upper()
        df["DESTINO"] = df["DESTINO"].str.strip().str.upper()

        # Tong ghe theo tuyen trong moi chunk
        nhom = (
            df.groupby(
                ["ORIGEM", "DESTINO"],
                as_index=False
            )["ASSENTOS"]
            .sum()
        )

        ds_nhom.append(nhom)

    # Gop ket qua cac chunk
    tat_ca = pd.concat(ds_nhom, ignore_index=True)

    tong_hop = (
        tat_ca.groupby(
            ["ORIGEM", "DESTINO"],
            as_index=False
        )["ASSENTOS"]
        .sum()
    )

    # Tao ten tuyen bay
    tong_hop["TUYEN_BAY"] = (
        tong_hop["ORIGEM"] + " → "
        + tong_hop["DESTINO"]
    )

    # Lay 10 tuyen co so ghe cao nhat
    top10 = (
        tong_hop.nlargest(10, "ASSENTOS")
        .sort_values("ASSENTOS")
        .copy()
    )

    ket_qua[loai] = top10

    print(f"Da tim thay {len(tong_hop)} tuyen {loai}")

# =====================================
# 3. VE 2 BIEU DO THANH NGANG
# =====================================

fig = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=[
        "Top 10 tuyến bay nội địa",
        "Top 10 tuyến bay quốc tế"
    ],
    horizontal_spacing=0.20
)

mau = {
    "Nội địa": "#168A9B",
    "Quốc tế": "#E58A35"
}

for i, loai in enumerate(["Nội địa", "Quốc tế"], 1):

    data = ket_qua[loai]

    fig.add_trace(
        go.Bar(
            x=data["ASSENTOS"],
            y=data["TUYEN_BAY"],
            orientation="h",
            name=loai,
            marker_color=mau[loai],
            text=data["ASSENTOS"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "Tuyến bay: %{y}<br>"
                "Số ghế bán: %{x:,.0f}"
                "<extra></extra>"
            )
        ),
        row=1,
        col=i
    )

# =====================================
# 4. DINH DANG BIEU DO
# =====================================

fig.update_layout(
    title=dict(
        text="TOP TUYẾN BAY THEO SỐ GHẾ BÁN NĂM 2024",
        x=0.5
    ),
    template="plotly_white",
    height=750,
    margin=dict(t=130, b=100, l=130, r=100),
    showlegend=False
)

fig.update_xaxes(
    title_text="Số ghế bán",
    rangemode="tozero",
    tickformat=","
)

fig.update_yaxes(
    title_text="Tuyến bay"
)

# =====================================
# 5. LUU KET QUA
# =====================================

output = goc / "BieuDo"
output.mkdir(exist_ok=True)

file_html = output / "bieu_do_06_top_tuyen_bay.html"

fig.write_html(file_html)

# Luu top 10 ra CSV de su dung sau
for loai, data in ket_qua.items():

    ten = "noi_dia" if loai == "Nội địa" else "quoc_te"

    data.to_csv(
        folder / f"top10_tuyen_{ten}_2024.csv",
        sep=";",
        index=False,
        encoding="utf-8-sig"
    )

fig.show()

print("\n===== HOAN THANH =====")

for loai, data in ket_qua.items():

    print(f"\nTOP 10 TUYEN {loai.upper()}")

    print(
        data[["TUYEN_BAY", "ASSENTOS"]]
        .sort_values("ASSENTOS", ascending=False)
        .to_string(index=False)
    )

print("\nDa tao bieu do 6 thanh cong!")
print("File:", file_html)
