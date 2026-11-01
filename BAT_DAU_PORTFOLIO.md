# ANAC Portfolio – Giai đoạn 1: Chuẩn hóa và kiểm chứng

**Đây là bản làm việc riêng**, không tự động thay thế project GitHub/Streamlit đang chạy.

## Các tệp kế thừa
- `MaNguon_ETL_2024/`: mã nguồn ETL và biểu đồ năm 2024 từ gói đã cung cấp.
- `cap_nhat_anac.py`: mã cập nhật và tên được workflow trong gói này gọi.
- `dashboard.py`, `.github/workflows/`, `nguon_anac.json`, `requirements.txt`, `tests/`: giữ lại từ bản dự án gốc.
- `kiem_tra_chat_luong.py`: tệp mới – kiểm tra nhanh bảng tổng hợp đầu ra, **không chỉnh sửa dữ liệu**.

## Lưu ý rất quan trọng về phiên bản
Người dùng có hai tệp `cap_nhat_anac.py` và `cap_nhat_data_anac.py` có nội dung khác nhau. **Không được đổi tên hoặc thay thế một tệp bằng tệp kia khi chưa đối chiếu với workflow và dữ liệu đang triển khai.** Bản này dùng `cap_nhat_anac.py` lấy từ gói ANAC_MoRong_TuDong_2024_2026.zip, tương thích với lệnh gọi trong workflow của chính gói đó. File `cap_nhat_data_anac.py` đã gửi riêng **không được chép đè**.

## Bước 1 – Tạo nhánh an toàn
Trên GitHub, tạo nhánh `portfolio-v2` từ nhánh hiện tại. Giữ nguyên bản đang chạy.

## Bước 2 – Chạy thử bộ kiểm thử mẫu (offline)
Mở terminal tại thư mục project:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Bộ 4 bài kiểm thử mẫu trong gói đã chạy thành công khi kiểm tra nội bộ ngày 14/10/2026. Đây không phải kiểm thử end-to-end với nguồn ANAC thực.

## Bước 3 – Kiểm tra dữ liệu bảng tổng hợp (offline)
Sao chép thư mục `DuLieu_DaXuLy/` **đang sử dụng thực tế** vào project này, rồi chạy:

```powershell
python kiem_tra_chat_luong.py
```

Script này kiểm tra: cấu trúc cột, định dạng tháng, tháng 2024, khóa trùng, giá/ghế không hợp lệ và phạm vi tọa độ. Các thông báo FAIL phải được điều tra – chưa được tự ý sửa dữ liệu. Script chưa kiểm tra tính đúng về nghiệp vụ hay chất lượng nguồn ANAC.

## Mục tiêu khi phỏng vấn
Giải thích được: 1) tại sao cần kiểm tra dữ liệu, 2) các kiểm tra có giới hạn gì, 3) vì sao bảo vệ bản production, 4) cách tái hiện một bài kiểm thử.

## Các giai đoạn tiếp theo (chưa triển khai ở đây)
1. Kiểm tra đầy đủ logic và tính tương thích của hai phiên bản ETL cập nhật.
2. Tách hàm ETL sang module và thêm kiểm thử dữ liệu bất thường.
3. Xây dựng Data Warehouse DuckDB, Star Schema và KPI bằng SQL.
4. Nâng cấp dashboard và README portfolio.
