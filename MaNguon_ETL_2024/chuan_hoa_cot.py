
import pandas as pd
from pathlib import Path

# Thư mục dữ liệu nội địa
folder = Path(__file__).resolve().parent.parent / "Dulieugoc/NoiDia_2024"

# Bảng quy đổi tên cột
doi_ten = {
    "nr_ano_referencia": "ANO",
    "nr_mes_referencia": "MES",
    "sg_empresa_icao": "EMPRESA",
    "sg_icao_origem": "ORIGEM",
    "sg_icao_destino": "DESTINO",
    "nr_tarifa": "TARIFA",
    "nr_assentos": "ASSENTOS"
}

# Danh sách cột chuẩn
cot_chuan = [
    "ANO", "MES", "EMPRESA",
    "ORIGEM", "DESTINO",
    "TARIFA", "ASSENTOS"
]

print("===== KIEM TRA CHUAN HOA COT =====")

# Duyệt 12 file
for f in sorted(folder.iterdir()):

    if f.suffix.lower() != ".csv":
        continue

    # Chỉ đọc tiêu đề cột
    df = pd.read_csv(
        f,
        sep=";",
        encoding="latin1",
        nrows=0
    )

    # Xóa khoảng trắng ở tên cột
    df.columns = df.columns.str.strip()

    # Chuẩn hóa tên cột
    df = df.rename(columns=doi_ten)

    # Kiểm tra kết quả
    if df.columns.tolist() == cot_chuan:
        print(f.name, "-> OK")
    else:
        print(f.name, "-> CHUA KHOP")
        print(df.columns.tolist())

print("\n===== HOAN THANH =====")
