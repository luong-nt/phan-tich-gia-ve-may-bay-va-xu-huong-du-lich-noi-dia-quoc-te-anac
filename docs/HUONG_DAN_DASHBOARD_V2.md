# ANAC Portfolio — Dashboard V2 (giữ phong cách gốc)

## Các phần được giữ nguyên

- Nền xanh trắng `#F2F7FC`, xanh dương `#1689CF`, cam `#F0A35D`, sidebar gradient xanh.
- Hero, card bo góc, logo, font, điều hướng nhanh và **ba trang cũ**.
- Biểu đồ giá vé, số ghế, thay đổi tháng, bản đồ tuyến, Top 10, tương quan và điểm đến.

## Các phần được nâng cấp

1. Nếu `data_warehouse/anac.duckdb` tồn tại, dashboard **đọc View `vw_monthly_kpi` và bảng Fact/Dimension trực tiếp từ DuckDB**, dùng SQL tổng hợp tuyến và điểm đến đúng khoảng tháng đã lọc.
2. Nếu chưa có `.duckdb`, dashboard sử dụng CSV dự phòng và ghi rõ `CSV dự phòng` trên sidebar (chế độ CSV có giới hạn do chỉ lưu Top 100 tuyến).
3. Giá gộp nhiều tháng dùng `priced_seats` làm trọng số khi ở chế độ DuckDB.
4. Không tính MoM khi thiếu tháng liền kề (ví dụ từ 04/2026 sang 06/2026). Đường biểu đồ cũng ngắt khi tháng trống.
5. Trang **02 · Tuyến bay & Chuyên sâu** có thêm các thẻ **Business Insights**: tăng trưởng, giá theo mùa, tương quan, tuyến giảm, tập trung mạng lưới và cảnh báo biến động.
6. Các insight nghiên cứu được đọc từ `data_warehouse/analysis_results/Q01.csv`…`Q17.csv`, **là bản chụp của lần chạy SQL trước**, không tự đổi khi người dùng kéo bộ lọc. Khi DW có kỳ mới mà kết quả SQL chưa có kỳ đó, dashboard cảnh báo về độ mới.
7. Khi dữ liệu địa lý bị thiếu, tuyến vẫn có thể có trong xếp hạng từ DW; chỉ phần bản đồ loại tuyến không đủ tọa độ.

## Cài đặt (không làm thay đổi bản gốc trước khi kiểm thử)

1. Trong `ANAC_Portfolio_GiaiDoan1/project`, đổi `dashboard.py` cũ thành `dashboard_backup.py`.
2. Sao chép file `project/dashboard.py` của gói ZIP này vào `project/dashboard.py`.
3. Sao chép `project/kiem_tra_dashboard_v2.py` vào `project/kiem_tra_dashboard_v2.py`.
4. Giữ nguyên `data_warehouse/anac.duckdb`, `data_warehouse/analysis_results/`, `DuLieu_DaXuLy/` và `assets/` (nếu có).
5. Cài `duckdb` trong môi trường Python chạy Streamlit (máy đã cài thì không cần cài lại):

```powershell
python -m pip install duckdb
```

Trong `requirements.txt` thêm một dòng `duckdb>=1.5,<2` để sau này triển khai lên Cloud; **không cần ghi đè** các thư viện đã có.

## Thử trên máy

```powershell
python -m py_compile dashboard.py
python kiem_tra_dashboard_v2.py
streamlit run dashboard.py
```

Sau khi app mở, kiểm tra sidebar hiện `NGUỒN DASHBOARD: DuckDB`, chọn 2026 và Nội địa; kiểm tra 2026-09, rồi chuyển cả 3 trang, mở Business Insights ở trang 02. Không đưa mã nguồn lên GitHub trước khi kiểm thử thành công.

## Giới hạn được công khai

- Chưa tích hợp lịch GitHub Actions để xuất bản `.duckdb` tự động lên máy chủ Streamlit. Tệp ở Downloads không tự xuất hiện trên Cloud.
- Truy vấn DuckDB được kiểm tra dựa trên schema đã trao đổi; **chưa kiểm thử giao diện thực với cơ sở dữ liệu đặt trên máy của bạn**. Cần chạy lệnh kiểm tra kết nối và Streamlit ở trên.
- Các bảng phân tích Q là snapshot; khi ANAC có tháng mới, phải chạy lại SQL bằng `run_analysis.py --all` để cập nhật insight.
- Tháng 05/2026 nội địa thiếu, và một số tuyến không có tọa độ. Không tự bù số liệu.
- Không so sánh trực tiếp giá BRL và USD, không đồng nhất ghế bán với hành khách thực bay.
