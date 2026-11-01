# ANAC Aviation Analytics — Boxplot 2025–2026

## Mục tiêu

Duy trì Boxplot giá vé **theo các bản ghi giá gốc của ANAC, có trọng số `ASSENTOS`**, không suy đoán từ giá trung bình theo tuyến. Thống kê P10, P25, P50, P75, P90 được tính riêng cho từng tháng bán vé và từng thị trường (nội địa BRL, quốc tế USD).

## Cách đặt file

Trong thư mục `C:\Users\User\Downloads\ANAC_Portfolio_GiaiDoan1\project`:

- `dashboard.py` → thay bản V5 hiện tại, nhớ sao lưu bản cũ.
- `data_warehouse/cap_nhat_phan_phoi_gia.py` → file mới.
- `tests/test_boxplot_2025_2026.py` → file kiểm thử mới.
- `HUONG_DAN_BOXplot_2025_2026.md` → có thể đặt ở `project/docs/`.

**Không thay** `cap_nhat_anac.py`, `data_warehouse/anac.duckdb`, `data_warehouse/build_fare_distributions.py`, `dashboard_v4_analytics.py`, hoặc file 2024 `fare_distribution_by_month.csv` đã tạo.

## Lần đầu, chỉ kiểm tra

Ở VS Code Terminal đang đứng trong thư mục `project`:

```powershell
python data_warehouse/cap_nhat_phan_phoi_gia.py --check
```

Nếu dữ liệu ETL như lần trước (24 tháng năm 2025, 8 tháng năm 2026), dự kiến `Tong thang 2025+ tu ETL: 32` và `Chua co / can tinh lai: 32`.

## Tải và tính **hai tháng mỗi lần**

```powershell
python data_warehouse/cap_nhat_phan_phoi_gia.py --limit 2
```

Chương trình sẽ lần lượt:

1. Đọc trạng thái và URL gốc từ `DuLieu_DaXuLy/_tu_dong/state.json`.
2. Tải từng file ANAC gốc vào thư mục tạm (có thể tốn dung lượng và thời gian; cần internet).
3. Đối chiếu SHA-256 tải về với tệp ANAC đã dùng bởi ETL. Nếu không khớp, **không xuất thống kê tháng đó**.
4. Đọc theo từng khối, tính phân vị giá với trọng số số ghế bán, đối chiếu tổng số ghế có giá với `fare_seats` trong state.
5. Thêm hoặc cập nhật **chỉ tháng phù hợp** vào `data_warehouse/fare_distribution_by_month.csv`, lưu hash tại `data_warehouse/fare_distribution_sync.json`, không thay 2024 hoặc DuckDB.

Chạy lại cùng lệnh để xử lý hai tháng tiếp theo. Có thể xử lý nhiều hơn bằng `--limit 4`; chỉ dùng `--all` nếu chấp nhận tải tất cả file còn thiếu trong cùng lần chạy (có thể nhiều GB).

Lưu ý: thư mục `DuLieu_DaXuLy/_tu_dong/parts/` đã tổng hợp theo tuyến, **không phải dữ liệu giá gốc**. Tuyệt đối không dùng nó làm nguồn trực tiếp cho Boxplot.

## Kiểm tra sau khi chạy

```powershell
python data_warehouse/cap_nhat_phan_phoi_gia.py --check
python -m pytest tests/test_boxplot_2025_2026.py -q
python -m streamlit run dashboard.py
```

Trong Dashboard, nhấn **Làm mới dữ liệu hiển thị**, chọn năm có tháng vừa tính, xem Boxplot và rê chuột vào hộp. Tooltip cần hiện P10/P25/Median/P75/P90 và số ghế có giá. Nếu không thấy, làm mới trang và xác minh file nằm trong `data_warehouse` đúng vị trí.

### Lưu ý về YoY

Khi chọn chỉ năm 2024, phần YoY không hiển thị vì chưa có dữ liệu 2023. Khi đủ cặp tháng 2025 hoặc 2026, YoY vẫn hoạt động, không tự chèn tháng 05/2026 bằng 0.

### Những điều chương trình không làm

- Không cập nhật tự động trên GitHub Actions; việc này cần nối vào workflow ở bước triển khai sau.
- Không sửa bất kỳ giá trị nào trong DuckDB hoặc CSV ETL tổng hợp.
- Không có thống kê cho tháng ANAC chưa được ETL nhận diện hoặc nguồn bị thay đổi khác với ETL. Khi SHA-256 không khớp, cập nhật ETL trước rồi chạy lại chương trình thống kê phân phối.
- Không khẳng định các phân vị là phân vị của số người bay: trọng số là **ghế bán**.

## Kiểm thử

Bản này đã qua **16 bài kiểm thử offline** (8 test logic mới + 8 test analytics Dashboard V4 được đóng gói trước đó) và kiểm tra cú pháp. Chưa có xác minh dữ liệu ANAC trực tuyến trên máy bạn. Việc phát hành chỉ nên coi là hoàn tất khi lệnh trên chạy thành công với dữ liệu thực.
