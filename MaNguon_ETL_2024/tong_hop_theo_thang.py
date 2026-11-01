
import pandas as pd
from pathlib import Path

# 1. Duong dan
goc = Path(__file__).resolve().parent.parent
folder = goc / "KetQua_ETL_2024"
folder_sach = goc / "Dulieusach"
folder.mkdir(parents=True, exist_ok=True)

ds = [
    ("Noi dia", "noi_dia_sach_2024.csv", "BRL"),
    ("Quoc te", "quoc_te_sach_2024.csv", "USD")
]

ket_qua = []

# 2. Xu ly tung nguon
for loai, ten_file, tien_te in ds:

    thong_ke = {}

    for df in pd.read_csv(
        folder_sach / ten_file,
        sep=";",
        encoding="utf-8-sig",
        usecols=["THANG", "TARIFA", "ASSENTOS"],
        chunksize=50000
    ):

        # Gia ve va so ghe
        gia = df["TARIFA"]
        ghe = df["ASSENTOS"]

        # Tinh gia co trong so
        df["GIA_CO_TRONG_SO"] = gia * ghe

        # Tong hop theo thang
        nhom = df.groupby("THANG").agg(
            so_ghe=("ASSENTOS", "sum"),
            tong_gia=("GIA_CO_TRONG_SO", "sum"),
            so_dong=("ASSENTOS", "size")
        )

        for thang, r in nhom.iterrows():

            if thang not in thong_ke:
                thong_ke[thang] = [0, 0, 0]

            thong_ke[thang][0] += r["so_ghe"]
            thong_ke[thang][1] += r["tong_gia"]
            thong_ke[thang][2] += r["so_dong"]

    # 3. Tao bang tong hop
    for thang, (so_ghe, tong_gia, so_dong) in thong_ke.items():

        ket_qua.append({
            "THANG": thang,
            "LOAI_CHUYEN_BAY": loai,
            "SO_GHE_BAN": int(so_ghe),
            "GIA_BINH_QUAN": round(tong_gia / so_ghe, 2),
            "SO_BAN_GHI": int(so_dong),
            "TIEN_TE": tien_te
        })

# 4. Ket hop hai nguon
kq = pd.DataFrame(ket_qua)

kq = kq.sort_values(
    ["LOAI_CHUYEN_BAY", "THANG"]
).reset_index(drop=True)

# 5. Tinh bien dong gia theo thang
kq["BIEN_DONG_GIA_PCT"] = (
    kq.groupby("LOAI_CHUYEN_BAY")["GIA_BINH_QUAN"]
    .pct_change() * 100
).round(2)

# 6. Luu file
file_out = folder / "tong_hop_theo_thang_2024.csv"

kq.to_csv(
    file_out,
    sep=";",
    index=False,
    encoding="utf-8-sig"
)

print("\n===== TONG HOP HAI NGUON =====")
print("So dong bang tong hop:", len(kq))
print(kq.to_string(index=False))
print("\nFile dau ra:", file_out)
