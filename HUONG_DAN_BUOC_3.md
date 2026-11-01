# ANAC Portfolio — Bước 3: Data Quality & Testing

Bộ kiểm tra này **không tải dữ liệu, không sửa `state.json`, không ghi vào DuckDB**. 2026 có thể thiếu tháng do nguồn ANAC chưa xuất bản; đây là WARNING, không điền dữ liệu giả.

## Cài đặt vào dự án

Giải nén ZIP và chép `qa_quality_gate.py` vào **thư mục `project`**; chép `tests/test_quality_gate.py` vào **`project/tests`** (giữ file `tests/test_etl.py` hiện có). `HUONG_DAN_BUOC_3.md` đặt ở thư mục `project`.

Trong Terminal VS Code đang đứng tại `project`:

```powershell
python qa_quality_gate.py
```

Quy tắc: Exit 0 khi không có `FAIL`; Exit 1 khi có ít nhất một `FAIL`. `WARN` là vấn đề cần ghi nhận và cân nhắc, không tự động loại bỏ dữ liệu. Nếu script báo FAIL, **chưa được kết luận đã xong Data Quality**.

Tiếp đến, chạy các unit test ETL + Quality Gate (không cần pytest):

```powershell
python -m unittest discover -s tests -v
```

Cần cài `pandas`, `requests`, `duckdb` trong môi trường Python của bạn (những thư viện bạn đang sử dụng trong dự án).

## Nhóm kiểm tra

1. **CSV đầu ra:** file có tồn tại, schema, tháng hợp lệ, không trùng `(THANG, LOAI_CHUYEN_BAY)`, giá và ghế hợp lệ, tiền tệ BRL/USD, MoM đúng tháng liền trước.
2. **Bảo toàn 2024:** đối chiếu 24 khóa và toàn bộ giá trị với baseline theo số học, tránh nhầm `476180` và `476180.0`.
3. **ETL 2025+:** `state.json` đồng bộ từng file parts; từng file không trùng khóa tuyến, dữ liệu giá/ghế hợp lệ; ghế và tổng tiền giá khớp metadata.
4. **Data Warehouse:** kiểm tra ràng buộc bảng Fact/Dimension, khóa, quan hệ tham chiếu, View KPI, tiền tệ, metadata 2025+, đối chiếu đủ các tháng giữa CSV ↔ parts ↔ DuckDB.
5. **Dữ liệu bản đồ:** xác thực tọa độ top tuyến; cảnh báo những dòng Fact thiếu tọa độ.
6. **Unit testing:** kiểm tra CSV `,`/`;`, số thực vs số nguyên, dữ liệu sai, MoM không nối qua tháng thiếu, metadata thiếu, và giữ lại 4 bài test ETL đã có.

## Phạm vi chưa được chứng minh chỉ bằng bộ test này

- Không xác thực mọi dòng ANAC gốc với dữ liệu trực tuyến.
- Không chứng minh các thống kê mang ý nghĩa nhân quả; `ASSENTOS` là ghế đã bán, không phải số người du lịch.
- Chưa tích hợp kiểm thử vào GitHub Actions (làm sau khi bộ kiểm tra trên máy đã chạy đạt).
- Warehouse gắn với máy hiện tại; GitHub Actions không tự cập nhật DuckDB trên máy tính cá nhân.

## Cách đọc kết quả

- `PASS: ...` — một điều kiện đã kiểm tra đạt.
- `FAIL: ...` — một điều kiện vi phạm, cần sửa hoặc giải thích trước khi sang phân tích chuyên sâu.
- `WARN: ...` — khoảng trống dữ liệu/độ phủ không tự động coi là lỗi.

Chạy theo từng bước, gửi phần `FAIL`/`WARN` và 3 dòng tổng kết để đối chiếu.
