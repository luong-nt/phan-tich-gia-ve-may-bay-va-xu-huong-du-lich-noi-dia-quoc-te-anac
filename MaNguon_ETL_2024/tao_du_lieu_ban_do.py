
import pandas as pd
from pathlib import Path
import csv

# ==========================================
# 1. DUONG DAN
# ==========================================

goc = Path(__file__).resolve().parent.parent

folder = goc / "KetQua_ETL_2024"
folder_sach = goc / "Dulieusach"
folder.mkdir(parents=True, exist_ok=True)
file_sb = goc / "DuLieu_SanBay" / "airports.csv"

# ==========================================
# 2. HAM NHAN DIEN DAU PHAN CACH
# ==========================================

def tim_dau_phan_cach(duong_dan):
    # Doc phan dau file, loai bo BOM neu co
    with open(
        duong_dan,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        dong_dau = f.readline()

    # CSV cua du an su dung , hoac ;
    if dong_dau.count(";") > dong_dau.count(","):
        return ";"

    return ","


# ==========================================
# 3. DOC DANH SACH SAN BAY
# ==========================================

print("Dang doc du lieu san bay...")

sb = pd.read_csv(
    file_sb,
    encoding="utf-8-sig",
    usecols=[
        "ident",
        "name",
        "latitude_deg",
        "longitude_deg"
    ],
    dtype={"ident": "string"},
    low_memory=False
)

sb["ident"] = (
    sb["ident"]
    .str.strip()
    .str.upper()
)

sb = sb.dropna(subset=["ident"])

sb = sb.drop_duplicates(
    subset="ident"
)

print("So san bay:", len(sb))


# ==========================================
# 4. HAM TAO TOP 100 TUYEN BAY
# ==========================================

def tao_top100(ten_file, loai, ten_output):

    duong_dan = folder_sach / ten_file

    if not duong_dan.exists():
        raise FileNotFoundError(
            f"Khong tim thay file: {duong_dan}"
        )

    print("\n================================")
    print("Dang xu ly:", loai)
    print("File:", ten_file)

    # Nhan dien dau phan cach
    sep = tim_dau_phan_cach(duong_dan)

    print("Dau phan cach:", repr(sep))

    # Chi luu ket qua tong hop tung chunk
    cac_nhom = []

    so_dong = 0

    # ======================================
    # 5. DOC THEO TUNG PHAN
    # ======================================

    for chunk in pd.read_csv(
        duong_dan,
        sep=sep,
        encoding="utf-8-sig",
        usecols=[
            "ORIGEM",
            "DESTINO",
            "ASSENTOS"
        ],
        chunksize=200000,
        low_memory=False
    ):

        so_dong += len(chunk)

        # Chuan hoa ma san bay
        for cot in ["ORIGEM", "DESTINO"]:
            chunk[cot] = (
                chunk[cot]
                .astype("string")
                .str.strip()
                .str.upper()
            )

        # Chuyen cot so ghe sang kieu so
        chunk["ASSENTOS"] = pd.to_numeric(
            chunk["ASSENTOS"],
            errors="coerce"
        )

        # Loai bo dong khong hop le
        chunk = chunk.dropna(
            subset=[
                "ORIGEM",
                "DESTINO",
                "ASSENTOS"
            ]
        )

        chunk = chunk[
            chunk["ASSENTOS"] > 0
        ]

        # Gom so ghe theo tuyen co huong
        nhom = (
            chunk.groupby(
                ["ORIGEM", "DESTINO"]
            )["ASSENTOS"]
            .sum()
        )

        cac_nhom.append(nhom)

        if so_dong % 1000000 < 200000:
            print(
                f"Da doc khoang {so_dong:,} dong"
            )

    if not cac_nhom:
        raise ValueError(
            f"File {ten_file} khong co du lieu."
        )

    # ======================================
    # 6. TONG HOP TOP 100
    # ======================================

    df = (
        pd.concat(cac_nhom)
        .groupby(level=[0, 1])
        .sum()
        .reset_index()
    )

    print("Tong so tuyen phan biet:", len(df))

    df = (
        df.sort_values(
            "ASSENTOS",
            ascending=False
        )
        .head(100)
        .copy()
    )

    df["LOAI"] = loai

    # ======================================
    # 7. GHEP TOA DO SAN BAY DI
    # ======================================

    df = df.merge(
        sb,
        left_on="ORIGEM",
        right_on="ident",
        how="left",
        validate="many_to_one"
    )

    df = df.rename(
        columns={
            "name": "TEN_DI",
            "latitude_deg": "LAT_DI",
            "longitude_deg": "LON_DI"
        }
    ).drop(columns="ident")

    # ======================================
    # 8. GHEP TOA DO SAN BAY DEN
    # ======================================

    df = df.merge(
        sb,
        left_on="DESTINO",
        right_on="ident",
        how="left",
        validate="many_to_one"
    )

    df = df.rename(
        columns={
            "name": "TEN_DEN",
            "latitude_deg": "LAT_DEN",
            "longitude_deg": "LON_DEN"
        }
    ).drop(columns="ident")

    # ======================================
    # 9. BO SUNG TOA DO SPJC
    # ======================================

    # SPJC: san bay Jorge Chavez, Lima, Peru.
    # Toa do tham khao, chi dung cho ban do.

    for huong in ["DI", "DEN"]:

        cot_ma = (
            "ORIGEM"
            if huong == "DI"
            else "DESTINO"
        )

        mask = df[cot_ma] == "SPJC"

        # Chi bo sung neu chua co toa do
        mask = mask & df[f"LAT_{huong}"].isna()

        df.loc[
            mask,
            f"TEN_{huong}"
        ] = "Jorge Chavez International Airport"

        df.loc[
            mask,
            f"LAT_{huong}"
        ] = -12.0219

        df.loc[
            mask,
            f"LON_{huong}"
        ] = -77.1143

    # ======================================
    # 10. KIEM TRA TOA DO
    # ======================================

    cot_toa_do = [
        "LAT_DI",
        "LON_DI",
        "LAT_DEN",
        "LON_DEN"
    ]

    for cot in cot_toa_do:
        df[cot] = pd.to_numeric(
            df[cot],
            errors="coerce"
        )

    hop_le = df[
        cot_toa_do
    ].notna().all(axis=1)

    print("\nKet qua:", loai)
    print("Tong so tuyen Top 100:", len(df))
    print("So tuyen du toa do:", int(hop_le.sum()))
    print("So tuyen thieu toa do:", int((~hop_le).sum()))

    if (~hop_le).any():
        print("\nCac tuyen thieu toa do:")

        print(
            df.loc[
                ~hop_le,
                ["ORIGEM", "DESTINO"]
            ].to_string(index=False)
        )

    # ======================================
    # 11. LUU KET QUA
    # ======================================

    file_out = folder / ten_output

    df.to_csv(
        file_out,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nDa luu:", file_out.name)


# ==========================================
# 12. CHAY HAI BO DU LIEU
# ==========================================

tao_top100(
    ten_file="noi_dia_sach_2024.csv",
    loai="Nội địa",
    ten_output="top100_noi_dia_toa_do.csv"
)

tao_top100(
    ten_file="quoc_te_sach_2024.csv",
    loai="Quốc tế",
    ten_output="top100_quoc_te_toa_do.csv"
)

print("\n================================")
print("HOAN THANH TAO DU LIEU BAN DO!")
print("================================")
