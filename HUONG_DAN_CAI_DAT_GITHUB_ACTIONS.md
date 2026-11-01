# Cài đặt GitHub Actions cho dự án ANAC

**Tên hiển thị:** Phân tích giá vé máy bay và xu hướng du lịch nội địa quốc tế ANAC

**Tên repository (đường dẫn GitHub, không dấu):**
`phan-tich-gia-ve-may-bay-va-xu-huong-du-lich-noi-dia-quoc-te-anac`

GitHub chuẩn hóa tên repository sang ký tự ASCII. Giữ tên tiếng Việt chính xác ở dòng đầu README và mô tả repository.

## 1. Chép file vào project

Thư mục: `C:\Users\User\Downloads\ANAC_Portfolio_GiaiDoan1\project`

- `.github/workflows/cap-nhat-du-lieu.yml` → ghi đè workflow cũ.
- `scripts/validate_anac_auto_update.py` → thêm mới vào thư mục `scripts`.
- `.gitignore` → thêm `state_backup*.json` (có thể chép file mẫu trong ZIP nếu bạn chưa sửa `.gitignore` khác).
- `README.md` → bản README mới với đúng tên đề tài. Sao lưu README cũ trước khi ghi đè.
- Giữ nguyên `dashboard.py`, `cap_nhat_anac.py`, `data_warehouse/cap_nhat_phan_phoi_gia.py`, `anac.duckdb`, dữ liệu ETL, `requirements.txt` và tests.

## 2. Những file PHẢI có trước lần push đầu tiên

- `DuLieu_DaXuLy/_tu_dong/state.json`
- `DuLieu_DaXuLy/_tu_dong/parts/` và `baseline_2024/`
- 4 bảng CSV trong `DuLieu_DaXuLy/`
- `data_warehouse/fare_distribution_by_month.csv` (56 kỳ sau khi bạn đã đồng bộ 32/32)
- `data_warehouse/fare_distribution_sync.json` (chứa SHA/đối chiếu nguồn của 32 kỳ)
- `data_warehouse/build_fare_distributions.py` và `data_warehouse/cap_nhat_phan_phoi_gia.py`
- `requirements.txt` gồm pandas, numpy, requests, pytest và các phụ thuộc cần thiết

Hai file fare_distribution được tạo từ máy bạn, KHÔNG có sẵn trong ZIP này (để tránh dùng dữ liệu giả).

## 3. Kiểm tra OFFLINE trước khi push

```powershell
python scripts/validate_anac_auto_update.py
python -m pytest tests/ -q
git rev-parse --show-toplevel
git status --short
```

Kỳ vọng: validate PASS, pytest PASS, Git root = `.../ANAC_Portfolio_GiaiDoan1/project`.
Nếu validate FAIL thì chưa push. Kiểm tra vị trí và đủ 2 file distribution/sync.

## 4. Tạo repository MỚI trên GitHub

1. Vào GitHub → New repository. Tên repository nhập chính xác (không dấu): `phan-tich-gia-ve-may-bay-va-xu-huong-du-lich-noi-dia-quoc-te-anac`.
2. Description: `Phân tích giá vé máy bay và xu hướng du lịch nội địa quốc tế ANAC | Python, DuckDB, ETL, Streamlit, GitHub Actions`.
3. Chọn Public nếu dùng làm portfolio. KHÔNG tick Initialize with README / .gitignore / license, vì project đã có.
4. Trong thư mục `project`, kiểm tra các file Git sẽ theo dõi và dung lượng file. Tránh đưa dữ liệu raw, tệp `.env`, tài liệu cá nhân hoặc tệp trên 100 MB.
5. Chỉ sau khi kiểm tra và đồng ý danh sách file: `git add ...`, `git commit -m "feat: publish ANAC portfolio with automated updates"`.
6. Kết nối repo:

```powershell
git remote add origin https://github.com/luong-nt/phan-tich-gia-ve-may-bay-va-xu-huong-du-lich-noi-dia-quoc-te-anac.git
git push -u origin main
```

**Chưa chạy các lệnh push nếu chưa tạo repo và chưa kiểm tra file sẽ commit.** Không dùng `--force`. Không xóa repo cũ trước khi repo mới chạy thành công.

## 5. Kiểm tra Actions trên GitHub

1. Vào repo mới → **Actions** → **ANAC | Tu dong cap nhat ETL va Boxplot**.
2. **Run workflow** → chọn `check` để kiểm tra truy cập nguồn và cấu hình (không sửa dữ liệu).
3. Khi `check` thành công, chọn `update` để chạy ETL + Boxplot + validate + tests. Nếu ANAC không có kỳ mới, workflow vẫn có thể kết thúc thành công mà không tạo commit.
4. Lịch tự chạy mỗi ngày lúc **12:23 giờ Việt Nam** (05:23 UTC), thực tế có thể trễ hoặc bỏ qua do tải GitHub Actions. Lịch chạy chỉ hoạt động trên nhánh mặc định `main`. Repo public ít hoạt động 60 ngày có thể bị GitHub tắt lịch chạy và cần bật lại.
5. Kiểm tra nhật ký các bước cập nhật và commit dữ liệu nếu có thay đổi.

## 6. Giới hạn rõ ràng

- Workflow tự động cập nhật bảng CSV ETL + Boxplot; **không tự commit DuckDB**.
- Mã ETL re-check vài kỳ gần nhất để phát hiện ANAC chỉnh sửa; khi không có thay đổi, không commit.
- Nếu mạng ANAC mất kết nối / kiểm thử lỗi, workflow dừng trước khi push; file trên GitHub giữ nguyên.
- Workflow cần 32/32 bản Boxplot bạn đã tạo; không khởi tạo dữ liệu phân phối từ dữ liệu giả.
- Đây là gói đã kiểm tra cú pháp/logic cục bộ, **chưa thể khẳng định đã chạy trên GitHub cho đến khi bạn push và test Actions thực tế**.
