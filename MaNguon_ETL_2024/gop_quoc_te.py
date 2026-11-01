
import pandas as pd
from pathlib import Path

# 1. Đường dẫn thư mục
goc = Path(__file__).resolve().parent.parent

folder = goc / "Dulieugoc/QuocTe_2024"

output = goc / "DuLieu_TrungGian"
output.mkdir(exist_ok=True)

file_out = output / "quoc_te_gop_2024.csv"

# 2. Danh sách cột chuẩn
cot_chuan = [
    "ANO", "MES", "EMPRESA",
    "ORIGEM", "DESTINO", "RETORNO",
    "CLASSE IDA", "CLASSE VOLTA",
    "TARIFA", "ASSENTOS"
]

# 3. Tìm 12 file CSV
ds = sorted(
    f for f in folder.iterdir()
    if f.is_file() and f.suffix.lower() == ".csv"
)

if len(ds) != 12:
    raise ValueError(
        f"Cần 12 file, hiện có {len(ds)}"
    )

# 4. Gộp dữ liệu
tong = 0
da_ghi = False

with open(file_out, "w",
          encoding="utf-8-sig",
          newline="") as fo:

    for f in ds:
        so_dong = 0

        for df in pd.read_csv(
            f,
            sep=";",
            encoding="latin1",
            dtype=str,
            keep_default_na=False,
            chunksize=50000
        ):

            # Chuẩn hóa khoảng trắng tên cột
            df.columns = df.columns.str.strip()

            # Kiểm tra cấu trúc
            if df.columns.tolist() != cot_chuan:
                raise ValueError(
                    f"Cấu trúc không đúng: {f.name}"
                )

            # Ghi vào file chung
            df.to_csv(
                fo,
                sep=";",
                index=False,
                header=not da_ghi
            )

            da_ghi = True
            so_dong += len(df)

        tong += so_dong
        print(f"{f.name}: {so_dong:,} dòng")

# 5. Kiểm tra kết quả
print("\n===== KET QUA GOP QUOC TE =====")
print("Số file đã gộp:", len(ds))
print("Tổng số dòng:", f"{tong:,}")
print("File đầu ra:", file_out)

if tong == 663640:
    print("OK - Số dòng khớp dữ liệu ban đầu!")
else:
    print("CẦN KIỂM TRA - Số dòng không khớp!")
