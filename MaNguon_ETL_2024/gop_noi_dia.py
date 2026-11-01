
import pandas as pd
from pathlib import Path

# ==================================
# 1. THIẾT LẬP ĐƯỜNG DẪN
# ==================================

goc = Path(__file__).resolve().parent.parent

folder = goc / "Dulieugoc/NoiDia_2024"

# Tạo thư mục lưu dữ liệu trung gian
output = goc / "DuLieu_TrungGian"
output.mkdir(exist_ok=True)

file_out = output / "noi_dia_gop_2024.csv"

# ==================================
# 2. CHUẨN HÓA TÊN CỘT
# ==================================

doi_ten = {
    "nr_ano_referencia": "ANO",
    "nr_mes_referencia": "MES",
    "sg_empresa_icao": "EMPRESA",
    "sg_icao_origem": "ORIGEM",
    "sg_icao_destino": "DESTINO",
    "nr_tarifa": "TARIFA",
    "nr_assentos": "ASSENTOS"
}

cot_chuan = [
    "ANO", "MES", "EMPRESA",
    "ORIGEM", "DESTINO",
    "TARIFA", "ASSENTOS"
]

# ==================================
# 3. GỘP 12 FILE CSV
# ==================================

ds = sorted(folder.glob("*.[cC][sS][vV]"))

if len(ds) != 12:
    raise ValueError(
        f"Cần 12 file CSV, hiện tìm thấy {len(ds)}"
    )

tong = 0
da_ghi = False

with open(file_out, "w", encoding="utf-8-sig",
          newline="") as fo:

    for f in ds:
        so_dong = 0

        # Đọc từng phần 50.000 dòng
        for df in pd.read_csv(
            f,
            sep=";",
            encoding="latin1",
            dtype=str,
            keep_default_na=False,
            chunksize=50000
        ):

            # Chuẩn hóa tên cột
            df.columns = df.columns.str.strip()
            df = df.rename(columns=doi_ten)

            # Kiểm tra cấu trúc
            if df.columns.tolist() != cot_chuan:
                raise ValueError(
                    f"Cấu trúc chưa đúng: {f.name}"
                )

            # Ghi dữ liệu vào file chung
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

# ==================================
# 4. KIỂM TRA KẾT QUẢ
# ==================================

print("\n===== KET QUA GOP DU LIEU =====")
print("Số file đã gộp:", len(ds))
print("Tổng số dòng:", f"{tong:,}")
print("File đầu ra:", file_out)

if tong == 7717161:
    print("OK - Số dòng khớp dữ liệu ban đầu!")
else:
    print("CẦN KIỂM TRA - Số dòng không khớp!")
