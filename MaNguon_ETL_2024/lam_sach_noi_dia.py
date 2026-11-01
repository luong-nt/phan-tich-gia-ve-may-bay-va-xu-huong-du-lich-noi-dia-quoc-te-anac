
import pandas as pd
import os
from pathlib import Path

# =====================================
# 1. DUONG DAN DU LIEU
# =====================================

goc = Path(__file__).resolve().parent.parent

file_in = goc / "DuLieu_TrungGian" / "noi_dia_gop_2024.csv"

folder_out = goc / "Dulieusach"
folder_out.mkdir(exist_ok=True)

file_out = folder_out / "noi_dia_sach_2024.csv"
file_tam = folder_out / "noi_dia_sach_2024.tmp.csv"

# =====================================
# 2. HAM CHUAN HOA GIA VE
# =====================================

def chuyen_gia(cot):

    s = cot.astype(str).str.strip()

    # Dang 600,00 hoac 1.600,00
    phay = s.str.fullmatch(
        r"(?:\d{1,3}(?:\.\d{3})+|\d+),\d{1,2}"
    )

    # Dang 600.00 hoac 1,600.00
    cham = s.str.fullmatch(
        r"(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{1,2}"
    )

    # Dang so nguyen: 600
    nguyen = s.str.fullmatch(r"\d+")

    # Kiem tra dinh dang la
    hop_le = phay | cham | nguyen

    if not hop_le.all():
        print("Gia ve chua nhan dien:")
        print(s[~hop_le].head(10))
        raise ValueError("Dinh dang gia ve khong hop le")

    gia = pd.Series(index=s.index, dtype="float64")

    # Xu ly dau phay thap phan
    gia.loc[phay] = pd.to_numeric(
        s.loc[phay]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    # Xu ly dau cham thap phan
    gia.loc[cham] = pd.to_numeric(
        s.loc[cham]
        .str.replace(",", "", regex=False)
    )

    # Xu ly so nguyen
    gia.loc[nguyen] = pd.to_numeric(
        s.loc[nguyen]
    )

    return gia, int(phay.sum()), int(cham.sum()), int(nguyen.sum())


# =====================================
# 3. BIEN THONG KE
# =====================================

tong = 0
so_phay = 0
so_cham = 0
so_nguyen = 0

thieu_ma = 0
tuyen_trung = 0

lan_dau = True

# =====================================
# 4. DOC VA LAM SACH
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
    for cot in ["EMPRESA", "ORIGEM", "DESTINO"]:
        df[cot] = df[cot].str.strip().str.upper()

    # Kiem tra ma trong
    thieu_ma += int((
        df[["EMPRESA", "ORIGEM", "DESTINO"]] == ""
    ).any(axis=1).sum())

    # Kiem tra trung san bay
    tuyen_trung += int((
        df["ORIGEM"] == df["DESTINO"]
    ).sum())

    # =================================
    # 5. CHUAN HOA GIA VE
    # =================================

    gia, n_phay, n_cham, n_nguyen = chuyen_gia(
        df["TARIFA"]
    )

    df["TARIFA"] = gia

    so_phay += n_phay
    so_cham += n_cham
    so_nguyen += n_nguyen

    # Chuyen kieu du lieu so
    for cot in ["ANO", "MES", "ASSENTOS"]:
        df[cot] = pd.to_numeric(
            df[cot], errors="raise"
        ).astype("int64")

    # Kiem tra gia tri hop le
    if not df["ANO"].eq(2024).all():
        raise ValueError("Nam khong hop le")

    if not df["MES"].between(1, 12).all():
        raise ValueError("Thang khong hop le")

    if df["TARIFA"].isna().any() or (df["TARIFA"] <= 0).any():
        raise ValueError("Gia ve khong hop le")

    if (df["ASSENTOS"] <= 0).any():
        raise ValueError("So ghe khong hop le")

    # =================================
    # 6. TAO CAC COT MOI
    # =================================

    df["THANG"] = (
        df["ANO"].astype(str) + "-"
        + df["MES"].astype(str).str.zfill(2)
    )

    df["LOAI_CHUYEN_BAY"] = "Noi dia"
    df["TIEN_TE"] = "BRL"

    # =================================
    # 7. LUU DU LIEU DA XU LY
    # =================================

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

# =====================================
# 8. KIEM TRA VA HOAN THANH
# =====================================

if tong != 7717161:
    raise ValueError("Tong so dong khong khop!")

# Chi thay file cu khi da xu ly xong
os.replace(file_tam, file_out)

print("\n===== KET QUA LAM SACH NOI DIA =====")

print("Tong so dong:", tong)
print("Gia dang dau phay:", so_phay)
print("Gia dang dau cham:", so_cham)
print("Gia dang so nguyen:", so_nguyen)

print("Dong thieu ma:", thieu_ma)
print("Dong trung san bay:", tuyen_trung)

print("File sau xu ly:", file_out)
print("OK - Da lam sach du 7717161 dong!")
