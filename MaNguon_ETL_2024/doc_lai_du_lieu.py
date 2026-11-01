
from pathlib import Path
import pandas as pd

# 1. Xac dinh thu muc du an
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Dulieusach"
OUTPUT = ROOT / "KetQua_ETL_2024"

FILES = {
    "Noi dia": "noi_dia_sach_2024.csv",
    "Quoc te": "quoc_te_sach_2024.csv"
}

# 2. Doc lai va kiem tra du lieu
for loai, ten_file in FILES.items():
    path = DATA / ten_file

    print("\n" + "=" * 60)
    print("DOC LAI DU LIEU:", loai)
    print("File:", path.name)
    print("=" * 60)

    if not path.exists():
        print("LOI: Khong tim thay file!")
        continue

    tong_dong = 0
    tong_ghe = 0
    gia_thieu = 0
    ghe_thieu = 0
    ma_thieu = 0
    thang = set()

    for df in pd.read_csv(
        path,
        sep=";",
        encoding="utf-8-sig",
        chunksize=100_000,
        low_memory=False
    ):
        tong_dong += len(df)

        if "THANG" in df.columns:
            thang.update(df["THANG"].dropna().astype(str))

        if "ASSENTOS" in df.columns:
            ghe = pd.to_numeric(
                df["ASSENTOS"], errors="coerce"
            )
            ghe_thieu += int(ghe.isna().sum())
            tong_ghe += float(ghe.sum())

        if "TARIFA" in df.columns:
            gia = pd.to_numeric(
                df["TARIFA"], errors="coerce"
            )
            gia_thieu += int(gia.isna().sum())

        for c in ["ORIGEM", "DESTINO"]:
            if c in df.columns:
                ma_thieu += int(
                    df[c].isna().sum()
                )

    print("So ban ghi:", f"{tong_dong:,}")
    print("So thang:", len(thang))
    print("Tong ghe ban:", f"{tong_ghe:,.0f}")
    print("Gia ve thieu/khong hop le:", gia_thieu)
    print("So ghe thieu/khong hop le:", ghe_thieu)
    print("Ma san bay thieu:", ma_thieu)

    # 3. Doi chieu bang tong hop theo thang
    path_tong_hop = (
        OUTPUT / "tong_hop_theo_thang_2024.csv"
    )

    if path_tong_hop.exists():
        summary = pd.read_csv(
            path_tong_hop,
            sep=";",
            encoding="utf-8-sig"
        )

        market = "Noi dia" if loai == "Noi dia" else "Quoc te"

        subset = summary[
            summary["LOAI_CHUYEN_BAY"] == market
        ]

        ghe_tong_hop = pd.to_numeric(
            subset["SO_GHE_BAN"],
            errors="coerce"
        ).sum()

        print("Ghe trong bang tong hop:",
              f"{ghe_tong_hop:,.0f}")

        if abs(tong_ghe - ghe_tong_hop) < 0.5:
            print("KIEM TRA: KHOP SO GHE")
        else:
            print("CAN KIEM TRA: CHENH LECH SO GHE")

print("\nHOAN THANH DOC LAI VA KIEM TRA DU LIEU!")
