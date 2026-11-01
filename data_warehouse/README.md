# ANAC Data Warehouse — giai đoạn 1

## Phạm vi và logic
- **Grain fact**: một tháng **bán vé** × một thị trường × một sân bay đi × một sân bay đến.
- Hai thị trường có **đơn vị tiền khác nhau**: nội địa BRL, quốc tế USD. Không cộng giá hay tính trung bình giá chung hai thị trường.
- `dim_airport` có 2 vai trò: sân bay đi và sân bay đến. Nếu mã sân bay không có trong OurAirports, vẫn lưu mã và để trống thông tin địa lý; không tự suy đoán tọa độ.
- `total_seats` là số **ghế bán được ghi nhận**, không mặc nhiên là số hành khách du lịch.
- `fare_weighted_sum` và `priced_seats` giúp tính giá bình quân đúng khi gộp nhiều tháng hoặc tuyến. Năm 2024 giá hợp lệ theo ETL cũ; bản cập nhật mới lưu số ghế có giá riêng.
- `source_record_count` của dữ liệu parts 2025+ là NULL vì bảng parts không chứa số dòng gốc. Không bịa số dòng.

## Chuẩn bị dữ liệu
Bản ZIP portfolio không chứa CSV lớn. Cần sử dụng các file đã tạo trước đó:

1. `Dulieusach/noi_dia_sach_2024.csv`
2. `Dulieusach/quoc_te_sach_2024.csv`
3. `DuLieu_SanBay/airports.csv`
4. **Không bắt buộc**, để thêm 2025–2026: các file `DuLieu_DaXuLy/_tu_dong/parts/domestic_YYYY-MM.csv` và `international_YYYY-MM.csv` từ chương trình cập nhật.

Không dùng `top100_...csv` để giả định có tuyến bay theo từng tháng. Các CSV `parts` có mức chi tiết theo tháng/tuyến.

## Cài và chạy trong VS Code (PowerShell)
Mở terminal tại thư mục `project` và chạy:

```powershell
python -m pip install duckdb
python data_warehouse/load_warehouse.py --clean-dir "C:\Users\User\Downloads\ANAC_Brazil_Aviation_Analytics\Dulieusach" --airports "C:\Users\User\Downloads\ANAC_Brazil_Aviation_Analytics\DuLieu_SanBay\airports.csv"
```

Khi đã có bảng parts, thêm tham số:

```powershell
--parts-dir "C:\duong_dan_thuc_te\DuLieu_DaXuLy\_tu_dong\parts"
```

Dữ liệu sẽ được lưu vào `data_warehouse/anac.duckdb`. Tệp warehouse chỉ được thay khi tải thành công; bản trước đó được giữ lại nếu lần tải mới lỗi. Các lần chạy sẽ xây lại từ nguồn, không cộng trùng dữ liệu.

## Truy vấn minh họa
Xem `queries/analysis.sql` với các ví dụ KPI theo tháng, YoY và xếp hạng tuyến bay. Có thể chạy câu lệnh bằng Python `duckdb.connect('data_warehouse/anac.duckdb').sql('SELECT * FROM vw_monthly_kpi LIMIT 5').show()`.

## Giới hạn chưa giải quyết
- Chưa nối trực tiếp dashboard với DuckDB (dashboard cũ tiếp tục dùng CSV).
- Chưa đưa hãng bay/loại vé vào fact: cần nạp từ dữ liệu chi tiết tương ứng, không thể khôi phục từ bảng parts đã gộp theo tuyến.
- Chưa thực thi trên bộ CSV thật trong gói này vì CSV lớn không có trong file ZIP. Phải chạy và đối soát kết quả trên máy người dùng.
- Mặc định chỉ đưa dữ liệu 2025–2026 vào warehouse khi có `parts` thật; không suy ra từ báo cáo.
