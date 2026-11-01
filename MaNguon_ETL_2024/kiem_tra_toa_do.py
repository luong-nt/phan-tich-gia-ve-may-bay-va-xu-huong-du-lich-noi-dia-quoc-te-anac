
import pandas as pd
from pathlib import Path

# =====================================
# 1. DUONG DAN
# =====================================

goc = Path(__file__).resolve().parent.parent

file_sb = goc / "DuLieu_SanBay" / "airports.csv"

folder = goc / "KetQua_ETL_2024"

files = [
    "top10_tuyen_noi_dia_2024.csv",
    "top10_tuyen_quoc_te_2024.csv"
]

# =====================================
# 2. DOC DU LIEU SAN BAY
# =====================================

sb = pd.read_csv(
    file_sb,
    encoding="utf-8",
    low_memory=False
)

# Lay cac cot can thiet
sb = sb[
    ["ident", "name", "latitude_deg", "longitude_deg"]
].copy()

# Chuan hoa ma san bay
sb["ident"] = sb["ident"].astype(str).str.strip().str.upper()

# Loai bo ma trung
sb = sb.drop_duplicates(subset="ident")

print("So san bay trong OurAirports:", len(sb))

# =====================================
# 3. GHEP TOA DO CHO TUNG TUYEN
# =====================================

for ten_file in files:

    print(f"\n===== {ten_file} =====")

    df = pd.read_csv(
        folder / ten_file,
        sep=";",
        encoding="utf-8-sig"
    )

    # Chuan hoa ma
    df["ORIGEM"] = df["ORIGEM"].str.strip().str.upper()
    df["DESTINO"] = df["DESTINO"].str.strip().str.upper()

    # Ghep toa do san bay di
    df = df.merge(
        sb,
        left_on="ORIGEM",
        right_on="ident",
        how="left"
    )

    df = df.rename(columns={
        "name": "TEN_DI",
        "latitude_deg": "LAT_DI",
        "longitude_deg": "LON_DI"
    }).drop(columns="ident")

    # Ghep toa do san bay den
    df = df.merge(
        sb,
        left_on="DESTINO",
        right_on="ident",
        how="left"
    )

    df = df.rename(columns={
        "name": "TEN_DEN",
        "latitude_deg": "LAT_DEN",
        "longitude_deg": "LON_DEN"
    }).drop(columns="ident")

    # Kiem tra so tuyen ghep duoc
    hop_le = df[
        ["LAT_DI", "LON_DI", "LAT_DEN", "LON_DEN"]
    ].notna().all(axis=1)

    print("Tong so tuyen:", len(df))
    print("So tuyen co du toa do:", int(hop_le.sum()))
    print("So tuyen thieu toa do:", int((~hop_le).sum()))

    if (~hop_le).any():
        print("\nCac tuyen chua ghep duoc:")
        print(
            df.loc[~hop_le, ["ORIGEM", "DESTINO"]]
            .to_string(index=False)
        )

    # Luu ket qua, chua bo tuyen nao
    ten_out = ten_file.replace(
        ".csv", "_toa_do.csv"
    )

    df.to_csv(
        folder / ten_out,
        sep=";",
        index=False,
        encoding="utf-8-sig"
    )

    print("Da luu:", ten_out)

print("\n===== HOAN THANH =====")
