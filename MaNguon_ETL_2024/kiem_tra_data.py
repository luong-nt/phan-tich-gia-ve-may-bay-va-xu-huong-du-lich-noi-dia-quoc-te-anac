
import pandas as pd
from pathlib import Path
import re

# ====================================
# 1. XÁC ĐỊNH THƯ MỤC DỮ LIỆU
# ====================================

goc = Path(__file__).resolve().parent.parent

folder_nd = goc / "Dulieugoc/NoiDia_2024"
folder_qt = goc / "Dulieugoc/QuocTe_2024"


# ====================================
# 2. HÀM TÌM FILE CSV THEO THÁNG
# ====================================

def tim_file(folder, thang):
    # Lấy danh sách các file CSV trong thư mục
    ds = sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() == ".csv"
    )

    # Tìm file có chứa năm và tháng
    for f in ds:
        so = re.sub(r"\D", "", f.stem)

        if thang in so:
            return f

    raise FileNotFoundError(
        f"Không tìm thấy file tháng {thang} trong {folder}\n"
        f"Các file hiện có: {[f.name for f in ds]}"
    )


# ====================================
# 3. HÀM ĐỌC DỮ LIỆU CSV
# ====================================

def doc_csv(file):
    try:
        df = pd.read_csv(
            file,
            sep=None,
            engine="python",
            encoding="utf-8-sig"
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            file,
            sep=None,
            engine="python",
            encoding="latin1"
        )

    return df


# ====================================
# 4. ĐỌC DỮ LIỆU NỘI ĐỊA
# ====================================

file_nd = tim_file(folder_nd, "202401")
nd = doc_csv(file_nd)

print("===== DU LIEU NOI DIA =====")
print("Tên file:", file_nd.name)
print("Số dòng, số cột:", nd.shape)
print("Tên các cột:", nd.columns.tolist())
print("\n5 dòng đầu tiên:")
print(nd.head(5).to_string(index=False))


# ====================================
# 5. ĐỌC DỮ LIỆU QUỐC TẾ
# ====================================

file_qt = tim_file(folder_qt, "202401")
qt = doc_csv(file_qt)

print("\n===== DU LIEU QUOC TE =====")
print("Tên file:", file_qt.name)
print("Số dòng, số cột:", qt.shape)
print("Tên các cột:", qt.columns.tolist())
print("\n5 dòng đầu tiên:")
print(qt.head(5).to_string(index=False))


# ====================================
# 6. KIỂM TRA ĐỌC DỮ LIỆU
# ====================================

print("\n===== KET QUA =====")
print("Đã đọc thành công cả 2 nguồn dữ liệu!")

# ====================================
# 7. KIỂM TRA CHẤT LƯỢNG DỮ LIỆU
# ====================================

print("\n===== NOI DIA =====")

# Kiểm tra kiểu dữ liệu từng cột
print("\nKiểu dữ liệu:")
print(nd.dtypes)

# Đếm giá trị thiếu theo từng cột
print("\nSố giá trị thiếu:")
print(nd.isnull().sum())

# Đếm số dòng trùng hoàn toàn
print("\nSố dòng trùng lặp:")
print(nd.duplicated().sum())


print("\n===== QUOC TE =====")

print("\nKiểu dữ liệu:")
print(qt.dtypes)

print("\nSố giá trị thiếu:")
print(qt.isnull().sum())

print("\nSố dòng trùng lặp:")
print(qt.duplicated().sum())

# ====================================
# 8. KIỂM TRA NGUYÊN NHÂN DỮ LIỆU THIẾU
# ====================================

# Tìm các dòng thiếu hạng vé chiều về
thieu = qt[qt["CLASSE VOLTA"].isna()]

print("\n===== KIEM TRA GIA TRI THIEU =====")

print("Tổng số dòng thiếu:", len(thieu))

# Xem mã sân bay chiều về ở các dòng bị thiếu
print("\nGiá trị RETORNO khi CLASSE VOLTA thiếu:")
print(thieu["RETORNO"].value_counts(dropna=False).head(10))

# Kiểm tra mã 9999 (vé một chiều)
mot_chieu = qt["RETORNO"].astype(str).str.strip() == "9999"

print("\nSố dòng RETORNO = 9999:")
print(mot_chieu.sum())

print("\nCLASSE VOLTA của các vé một chiều:")
print(qt.loc[mot_chieu, "CLASSE VOLTA"].value_counts(dropna=False))

# Kiểm tra trường hợp thiếu nhưng không phải vé một chiều
loi = qt["CLASSE VOLTA"].isna() & ~mot_chieu

print("\nSố dòng thiếu nhưng RETORNO khác 9999:")
print(loi.sum())

# ====================================
# 9. KIỂM TRA GIÁ TRỊ GỐC TRONG CSV
# ====================================

# Đọc lại file, không tự chuyển NA thành NaN
qt_goc = pd.read_csv(
    file_qt,
    sep=None,
    engine="python",
    encoding="latin1",
    keep_default_na=False,
    dtype=str
)

# Lọc các vé một chiều
mot_chieu_goc = qt_goc[
    qt_goc["RETORNO"].str.strip() == "9999"
]

print("\n===== KIEM TRA DU LIEU GOC =====")

print("Giá trị CLASSE VOLTA của vé một chiều:")
print(
    mot_chieu_goc["CLASSE VOLTA"]
    .value_counts(dropna=False)
    .head(10)
)

print("\nGiá trị thực tế trong CSV:")
print(repr(mot_chieu_goc["CLASSE VOLTA"].iloc[0]))
