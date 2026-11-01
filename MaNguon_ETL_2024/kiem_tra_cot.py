
import pandas as pd
from pathlib import Path

# Thư mục dữ liệu nội địa
folder = Path(__file__).resolve().parent.parent / "Dulieugoc/NoiDia_2024"

# Lưu các nhóm cấu trúc cột
nhom = {}

# Duyệt từng file CSV
for f in sorted(folder.iterdir()):

    if f.suffix.lower() != ".csv":
        continue

    # Chỉ đọc tên cột, không đọc toàn bộ dữ liệu
    df = pd.read_csv(
        f,
        sep=";",
        encoding="latin1",
        nrows=0
    )

    cot = tuple(df.columns)

    if cot not in nhom:
        nhom[cot] = []

    nhom[cot].append(f.name)

# In kết quả
for i, (cot, files) in enumerate(nhom.items(), 1):

    print(f"\n===== CAU TRUC {i} =====")

    print("Các file có cấu trúc này:")
    for f in files:
        print("-", f)

    print("\nTên các cột:")

    for j, ten in enumerate(cot, 1):
        print(j, repr(ten))

print("\nTổng số cấu trúc khác nhau:", len(nhom))
