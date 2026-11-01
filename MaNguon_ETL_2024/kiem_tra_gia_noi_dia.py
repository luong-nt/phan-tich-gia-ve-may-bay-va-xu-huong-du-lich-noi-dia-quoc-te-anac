
import pandas as pd
from pathlib import Path

# Thu muc du lieu goc
goc = Path(__file__).resolve().parent.parent
folder = goc / "Dulieugoc/NoiDia_2024"

# Kiem tra thang 10 va thang 11
for thang in ["202410", "202411"]:

    file = folder / f"{thang}.CSV"

    print(f"\n===== THANG {thang} =====")

    dau_phay = 0
    dau_cham = 0
    ca_hai = 0
    vi_du = []

    for df in pd.read_csv(
        file,
        sep=";",
        encoding="latin1",
        dtype=str,
        keep_default_na=False,
        usecols=["TARIFA"],
        chunksize=50000
    ):

        gia = df["TARIFA"].str.strip()

        co_phay = gia.str.contains(",", regex=False)
        co_cham = gia.str.contains(".", regex=False)

        dau_phay += (co_phay & ~co_cham).sum()
        dau_cham += (co_cham & ~co_phay).sum()
        ca_hai += (co_phay & co_cham).sum()

        # Lay vi du gia ve co dau cham
        if len(vi_du) < 5:
            mau = gia[co_cham].head(
                5 - len(vi_du)
            ).tolist()

            vi_du.extend(mau)

    print("Chi co dau phay:", dau_phay)
    print("Chi co dau cham:", dau_cham)
    print("Co ca hai dau:", ca_hai)
    print("Vi du gia ve:", vi_du)
