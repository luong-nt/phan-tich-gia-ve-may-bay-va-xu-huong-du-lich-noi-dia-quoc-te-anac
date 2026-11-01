
import pandas as pd
from pathlib import Path

# 1. Thư mục dữ liệu đã gộp
goc = Path(__file__).resolve().parent.parent
folder = goc / "DuLieu_TrungGian"

# 2. Hai file cần kiểm tra
ds = {
    "NOI DIA": "noi_dia_gop_2024.csv",
    "QUOC TE": "quoc_te_gop_2024.csv"
}

# 3. Kiểm tra từng nguồn
for ten, file in ds.items():

    print(f"\n===== {ten} =====")

    tong = 0
    loi_gia = 0
    loi_ghe = 0
    thang = set()

    for df in pd.read_csv(
        folder / file,
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
        chunksize=100000
    ):

        tong += len(df)

        # Kiểm tra các tháng
        thang.update(df["MES"].unique())

        # Thử chuyển giá vé sang số
        gia = df["TARIFA"].str.strip()
        gia = gia.str.replace(".", "", regex=False)
        gia = gia.str.replace(",", ".", regex=False)
        gia = pd.to_numeric(gia, errors="coerce")

        # Thử chuyển số ghế sang số
        ghe = pd.to_numeric(
            df["ASSENTOS"], errors="coerce"
        )

        # Đếm các giá trị cần kiểm tra
        loi_gia += ((gia.isna()) | (gia <= 0)).sum()
        loi_ghe += ((ghe.isna()) | (ghe <= 0)).sum()

    print("Tổng số dòng:", tong)
    print("Các tháng:", sorted(thang, key=int))
    print("Giá vé cần kiểm tra:", loi_gia)
    print("Số ghế cần kiểm tra:", loi_ghe)

print("\n===== HOAN THANH =====")
