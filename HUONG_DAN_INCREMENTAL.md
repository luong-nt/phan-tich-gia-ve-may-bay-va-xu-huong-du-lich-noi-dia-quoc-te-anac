# ANAC Portfolio — DuckDB Incremental Loading

## Mục tiêu

Không xây lại toàn bộ DuckDB khi nguồn ANAC thay đổi. Chỉ bổ sung/thay thế **đúng kỳ tháng + thị trường** được cập nhật. Không đọc lại CSV sạch năm 2024, không sửa bốn CSV tổng hợp, không thay đổi `state.json`.

**Lưu ý:** Đây là bản nâng cấp riêng của Data Warehouse. Nó chưa tự động chạy trên GitHub Actions, chưa tự đồng bộ file `.duckdb` sang Streamlit. Tầng lưu trữ triển khai và lịch chạy sẽ tích hợp sau.

## Cài đặt

Giải nén ZIP rồi chép đúng cấu trúc vào `C:\Users\User\Downloads\ANAC_Portfolio_GiaiDoan1\project`:

```text
project/
  data_warehouse/
    anac.duckdb             # GIỮ NGUYÊN
    schema.sql              # GIỮ NGUYÊN
    load_warehouse.py       # GIỮ NGUYÊN
    incremental_warehouse.py    # FILE MỚI
  tests/
    test_incremental_warehouse.py  # FILE MỚI
  DuLieu_DaXuLy/
    _tu_dong/
      state.json
      parts/
```

**Không thay thế `load_warehouse.py` hay `schema.sql`.** Chương trình dùng đúng DuckDB đã được tạo từ trước và có `etl_month_metadata`.

## Bước A: Xem trước (không ghi DW)

Trong PowerShell ở thư mục `project`:

```powershell
python data_warehouse/incremental_warehouse.py --check
```

Ở lần chạy đầu, nếu DuckDB đã khớp dữ liệu hiện tại, đa phần kỳ sẽ có dạng "Đã khớp DW, chỉ đánh dấu hash"; đó **không phải** nạp lại. Nếu có `REPLACE`, mã sẽ thay đúng tháng đó khi chạy `--apply`. Nếu số tháng dự kiến thay đổi bất thường, hãy dừng để kiểm tra.

## Bước B: Nạp tăng dần (chỉ khi bước A hợp lý)

```powershell
python data_warehouse/incremental_warehouse.py --apply
```

Script sẽ tạo bản sao lưu `data_warehouse/anac.duckdb.before_incremental.bak` trước khi cập nhật; sau đó thực hiện thao tác trong một transaction. Có lỗi sẽ ROLLBACK. Bản backup **chỉ là một phiên bản gần nhất**, được ghi đè ở lần cập nhật tiếp theo, không thay thế quy trình sao lưu lâu dài.

Các loại thao tác:
- `NO_CHANGE`: CSV part và metadata không đổi → không nạp.
- `BASELINE`: đối chiếu theo tuyến đã khớp DuckDB → chỉ ghi dấu SHA256 lần đầu.
- `METADATA_ONLY`: chỉ cập nhật `source_record_count` khi `state.json` đổi; không nạp lại tuyến.
- `REPLACE`: tháng mới hoặc CSV part thay đổi → kiểm tra chất lượng, xóa rồi chèn **riêng month_key + market_key** trong một transaction.

Không tự xóa dữ liệu DW nếu part từng tồn tại nay biến mất: script báo lỗi khi `state.json` còn kỳ mà file part mất. Không cập nhật lại thông tin tọa độ của sân bay hiện có; muốn đồng bộ dim_airport cần quy trình riêng.

## Bước C: Chạy test bằng dữ liệu mô phỏng (sau khi cài đặt)

```powershell
python -m pytest tests/test_incremental_warehouse.py -v
python qa_quality_gate.py
```

Bộ integration test mới tạo DuckDB tạm, kiểm tra: thêm kỳ; chạy lại không trùng; cập nhật chỉ metadata; thay tháng cũ; không làm thay đổi 2024; dữ liệu nguồn lỗi không cập nhật DW.

## Điều kiện để tự động hoàn toàn

Cần cơ chế lưu DuckDB **bền vững giữa các lần chạy** của GitHub Actions (runner thông thường không giữ file dữ liệu giữa các jobs), và cách dashboard nhận cơ sở dữ liệu mới. Chưa bật workflow cập nhật DW trên GitHub vì cần xác định nơi lưu file `.duckdb`, kích thước file và chế độ truy cập đọc/ghi; không thể chỉ thêm một lệnh rồi coi như hoàn chỉnh.

## Cảnh báo triển khai

- Đóng chương trình đang mở DuckDB để ghi (và tốt nhất tạm dừng Streamlit chạy cục bộ) trước khi `--apply`. Các tiến trình khác có thể giữ lock.
- Không chạy `load_warehouse.py` cùng lúc với incremental loader.
- Tránh commit file `.duckdb` vào GitHub nếu có kích thước lớn hoặc chứa dữ liệu không phù hợp với Git.
- Dashboard chưa chuyển sang đọc DuckDB; cập nhật DuckDB cục bộ chưa tự làm mới dashboard hiện tại.
