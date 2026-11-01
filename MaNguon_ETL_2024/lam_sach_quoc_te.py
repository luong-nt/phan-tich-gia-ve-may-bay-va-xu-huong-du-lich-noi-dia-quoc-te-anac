
import pandas as pd
import os
from pathlib import Path

# =====================================
# 1. DUONG DAN
# =====================================

goc = Path(__file__).resolve().parent.parent

file_in = goc / "DuLieu_TrungGian" / "quoc_te_gop_2024.csv"

folder_out = goc / "Dulieusach"
folder_out.mkdir(exist_ok=True)

file_out = folder_out / "quoc_te_sach_2024.csv"
file_tam = folder_out / "quoc_te_sach_2024.tmp.csv"

# =====================================
# 2. HAM CHUYEN DOI GIA VE
# =====================================

def chuyen_gia(cot):
    s = cot.astype(str).str.strip()

    # Kieu 600,00 hoac 1.654,67
    kieu_phay = s.str.fullmatch(
        r"(?:\d{1,3}(?:\.\d{3})+|\d+),\d{1,2}"
    )

    # Kieu 1654.67 hoac 1,654.67
    kieu_cham = s.str.fullmatch(
        r"(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{1,2}"
    )

    # Kieu so nguyen: 600
    kieu_nguyen = s.str.fullmatch(r"\d+")

    # Phat hien dinh dang chua nhan dien
    hop_le = kieu_phay | kieu_cham | kieu_nguyen

    if not hop_le.all():
        print("Cac gia ve can kiem tra:")
        print(s[~hop_le].head(10))
        raise ValueError("Co dinh dang gia ve chua xu ly")

    gia = pd.Series(index=s.index, dtype="float64")

    # Chuyen dau phay thap phan sang dau cham
    gia.loc[kieu_phay] = pd.to_numeric(
        s.loc[kieu_phay]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    # Giu dau cham thap phan
    gia.loc[kieu_cham] = pd.to_numeric(
        s.loc[kieu_cham]
        .str.replace(",", "", regex=False)
    )

    # Chuyen so nguyen
    gia.loc[kieu_nguyen] = pd.to_numeric(
        s.loc[kieu_nguyen]
    )

    return gia, kieu_phay.sum(), kieu_cham.sum()


# =====================================
# 3. BIEN THONG KE
# =====================================

tong = 0
thieu_ma = 0
tuyen_trung = 0
mot_chieu = 0
khu_hoi = 0
thieu_bat_thuong = 0

so_phay = 0
so_cham = 0

lan_dau = True

# =====================================
# 4. DOC VA LAM SACH DU LIEU
# =====================================

for df in pd.read_csv(
    file_in,
    sep=";",
    encoding="utf-8-sig",
    dtype=str,
    keep_default_na=False,
    chunksize=50000
):

    # Chuan hoa ma hang va san bay
    cac_cot = [
        "EMPRESA", "ORIGEM", "DESTINO",
        "RETORNO", "CLASSE IDA", "CLASSE VOLTA"
    ]

    for cot in cac_cot:
        df[cot] = df[cot].str.strip().str.upper()

    # Kiem tra ma trong
    thieu_ma += (
        df[["EMPRESA", "ORIGEM", "DESTINO"]] == ""
    ).any(axis=1).sum()

    # Kiem tra trung san bay di va den
    tuyen_trung += (
        df["ORIGEM"] == df["DESTINO"]
    ).sum()

    # =================================
    # 5. CHUAN HOA GIA VE
    # =================================

    gia, n_phay, n_cham = chuyen_gia(df["TARIFA"])

    df["TARIFA"] = gia

    so_phay += n_phay
    so_cham += n_cham

    # Chuyen cot so
    for cot in ["ANO", "MES", "ASSENTOS"]:
        df[cot] = pd.to_numeric(
            df[cot], errors="raise"
        ).astype("int64")

    # Kiem tra du lieu
    if not df["ANO"].eq(2024).all():
        raise ValueError("Co nam khac 2024")

    if not df["MES"].between(1, 12).all():
        raise ValueError("Thang khong hop le")

    if df["TARIFA"].isna().any() or (df["TARIFA"] <= 0).any():
        raise ValueError("Gia ve khong hop le")

    if (df["ASSENTOS"] <= 0).any():
        raise ValueError("So ghe khong hop le")

    # =================================
    # 6. PHAN LOAI VE
    # =================================

    la_mot_chieu = df["RETORNO"] == "9999"

    df["LOAI_VE"] = "Co chieu ve"
    df.loc[la_mot_chieu, "LOAI_VE"] = "Mot chieu"

    mot_chieu += la_mot_chieu.sum()
    khu_hoi += (~la_mot_chieu).sum()

    thieu_bat_thuong += (
        (~la_mot_chieu)
        & df["CLASSE VOLTA"].isin(["NA", ""])
    ).sum()

    # =================================
    # 7. TAO CAC COT MOI
    # =================================

    df["THANG"] = (
        df["ANO"].astype(str) + "-"
        + df["MES"].astype(str).str.zfill(2)
    )

    df["LOAI_CHUYEN_BAY"] = "Quoc te"
    df["TIEN_TE"] = "USD"

    # =================================
    # 8. LUU DU LIEU
    # =================================

    # Ghi file tam de tranh file dau ra bi thieu
    df.to_csv(
        file_tam,
        sep=";",
        index=False,
        encoding="utf-8-sig",
        mode="w" if lan_dau else "a",
        header=lan_dau
    )

    lan_dau = False
    tong += len(df)

# Chi thay file dau ra khi xu ly thanh cong
if tong != 663640:
    raise ValueError("Tong so dong khong khop")

os.replace(file_tam, file_out)

# =====================================
# 9. KET QUA
# =====================================

print("\n===== KET QUA LAM SACH QUOC TE =====")

print("Tong so dong:", tong)
print("Gia dinh dang dau phay:", so_phay)
print("Gia dinh dang dau cham:", so_cham)

print("Dong thieu ma hang/san bay:", thieu_ma)
print("Dong trung san bay di/den:", tuyen_trung)

print("Dong ve mot chieu:", mot_chieu)
print("Dong ve co chieu ve:", khu_hoi)
print("Dong NA bat thuong:", thieu_bat_thuong)

print("File sau xu ly:", file_out)
print("OK - Da xu ly du 663640 dong!")
