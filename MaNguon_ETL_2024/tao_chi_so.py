
import pandas as pd
from pathlib import Path

# 1. Đọc dữ liệu đã tổng hợp
goc = Path(__file__).resolve().parent.parent
folder = goc / "KetQua_ETL_2024"

df = pd.read_csv(
    folder / "tong_hop_theo_thang_2024.csv",
    sep=";",
    encoding="utf-8-sig"
)

# 2. Sắp xếp dữ liệu theo loại chuyến bay và tháng
df = df.sort_values(
    ["LOAI_CHUYEN_BAY", "THANG"]
).reset_index(drop=True)

# 3. Tính số ghế bán tháng trước
df["GHE_THANG_TRUOC"] = (
    df.groupby("LOAI_CHUYEN_BAY")["SO_GHE_BAN"]
    .shift(1)
)

# 4. Tính % tăng/giảm số ghế bán
df["BIEN_DONG_GHE_PCT"] = (
    df.groupby("LOAI_CHUYEN_BAY")["SO_GHE_BAN"]
    .pct_change() * 100
).round(2)

# 5. Tính giá vé tháng trước
df["GIA_THANG_TRUOC"] = (
    df.groupby("LOAI_CHUYEN_BAY")["GIA_BINH_QUAN"]
    .shift(1)
)

# 6. Tính chênh lệch giá vé
df["CHENH_LECH_GIA"] = (
    df["GIA_BINH_QUAN"] - df["GIA_THANG_TRUOC"]
).round(2)

# 7. Tính tỷ trọng số ghế bán theo tháng
tong_ghe_thang = df.groupby("THANG")["SO_GHE_BAN"].transform("sum")

df["TY_TRONG_GHE_PCT"] = (
    df["SO_GHE_BAN"] / tong_ghe_thang * 100
).round(2)

# 8. Lưu bảng chỉ số
file_out = folder / "chi_so_phan_tich_2024.csv"

df.to_csv(
    file_out,
    sep=";",
    index=False,
    encoding="utf-8-sig"
)

# 9. Hiển thị kết quả
print("\n===== CAC CHI SO PHAN TICH =====")

cot = [
    "THANG",
    "LOAI_CHUYEN_BAY",
    "BIEN_DONG_GIA_PCT",
    "BIEN_DONG_GHE_PCT",
    "CHENH_LECH_GIA",
    "TY_TRONG_GHE_PCT"
]

print(df[cot].to_string(index=False))
print("\nDa luu file:", file_out)
