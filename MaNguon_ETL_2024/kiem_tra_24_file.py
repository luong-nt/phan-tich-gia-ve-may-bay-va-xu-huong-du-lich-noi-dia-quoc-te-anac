
import pandas as pd
from pathlib import Path

# 1. Đường dẫn thư mục dự án
goc = Path(__file__).resolve().parent.parent

# 2. Danh sách hai nguồn dữ liệu
nguon = {
    "NOI DIA": "Dulieugoc/NoiDia_2024",
    "QUOC TE": "Dulieugoc/QuocTe_2024"
}

# 3. Kiểm tra từng nguồn
for ten, folder in nguon.items():

    print(f"\n===== {ten} =====")

    duong_dan = goc / folder

    # Lấy tất cả file CSV
    ds = sorted(
        f for f in duong_dan.iterdir()
        if f.is_file() and f.suffix.lower() == ".csv"
    )

    print("Số file tìm thấy:", len(ds))

    tong = 0
    cac_cot = set()

    # Đọc lần lượt từng file
    for f in ds:

        df = pd.read_csv(
            f,
            sep=";",
            encoding="latin1",
            keep_default_na=False,
            dtype=str
        )

        # Đếm số dòng
        so_dong = len(df)
        tong += so_dong

        # Kiểm tra cấu trúc
        cac_cot.add(tuple(df.columns))

        print(
            f.name,
            "| Số dòng:", so_dong,
            "| Số cột:", len(df.columns)
        )

        del df

    print("\nTổng số dòng:", tong)
    print("Số cấu trúc cột khác nhau:", len(cac_cot))

    if len(ds) == 12:
        print("Đã tìm thấy đủ 12 file.")
    else:
        print("CẦN KIỂM TRA: Số file khác 12!")

print("\n===== HOAN THANH KIEM TRA =====")
