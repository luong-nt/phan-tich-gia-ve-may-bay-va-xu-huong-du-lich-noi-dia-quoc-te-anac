# BƯỚC 3 — BÁO CÁO DATA QUALITY & TESTING

**Dự án:** ANAC Brazil Aviation Analytics Portfolio
**Ngày ghi nhận:** 30/10/2026
**Phạm vi:** ETL cập nhật dữ liệu ANAC, CSV tổng hợp, `state.json`, DuckDB Data Warehouse và cơ chế Incremental Loading.

## 1. Mục tiêu

Kiểm chứng dữ liệu sau ETL, tính nhất quán giữa các tầng dữ liệu, khả năng chạy lặp lại và tính ổn định của các hàm đã có bài kiểm thử trước khi thực hiện phân tích chuyên sâu và phát triển Dashboard.

## 2. Môi trường và dữ liệu kiểm thử

- **Nguồn:** Dữ liệu ANAC được xử lý và lưu theo tháng, kèm dữ liệu nền năm 2024.
- **Data Warehouse:** `data_warehouse/anac.duckdb`, gồm bảng Fact, Dimension, metadata ETL và View `vw_monthly_kpi`.
- **Dữ liệu tổng hợp:** 56 dòng KPI, gồm 24 dòng năm 2024, 24 dòng năm 2025 và 8 dòng nội địa năm 2026.
- **Cập nhật theo tháng:** 32 tệp `parts`; đã khởi tạo đồng bộ SHA-256 với Incremental Loading.
- **Công cụ kiểm thử:** `qa_quality_gate.py`, `pytest`, truy vấn DuckDB, đối chiếu CSV và phép so sánh SHA-256.

## 3. Kết quả kiểm thử

| Hạng mục | Cách kiểm tra / bằng chứng | Kết quả |
|---|---|---|
| Data Quality Gate | Chạy `python qa_quality_gate.py` sau khi nâng cấp incremental | **399 PASS · 0 FAIL · 2 WARN** |
| Unit & Regression Testing | `python -m pytest tests/ -v` | **17 passed, 1 warning** |
| Kiểm tra KPI liên tầng | Đối chiếu CSV tổng hợp với `vw_monthly_kpi` theo khóa tháng và thị trường; đối chiếu số ghế, giá bình quân, số bản ghi và tiền tệ | **56/56 dòng khớp, 0 chênh lệch** |
| ETL Rebuild Idempotency | Chạy `cap_nhat_anac.py --rebuild-only` hai lần; so sánh SHA-256 của bốn CSV và `state.json` | **4/4 CSV PASS; `state.json` không đổi** |
| Khởi tạo Incremental Loading | `incremental_warehouse.py --check` rồi `--apply` | **32/32 kỳ được đánh dấu đồng bộ** |
| Nhận diện dữ liệu không đổi | Chạy lại `incremental_warehouse.py --check` | **32 file không đổi; 0 file cần nạp lại** |
| Unit Test Incremental | `python -m pytest tests/test_incremental_warehouse.py -v` | **5 passed, 1 warning** (nằm trong tổng 17 test khi chạy toàn bộ) |
| Metadata bản ghi nguồn | Nạp lại DuckDB sau khi khôi phục `domestic_2025-01` | **32/32 tháng có số bản ghi nguồn** |

### Đối chiếu trọng điểm tháng 09/2026

- Thị trường: **Nội địa**, đơn vị giá: **BRL**.
- Số ghế bán: **2.551.248**; giá bình quân: **746,62 BRL**.
- Số bản ghi hợp lệ từ ETL: **892.505**.
- DuckDB xác nhận **6.076 tuyến tổng hợp**, **2.551.248 ghế**, **746,62 BRL**. Số tuyến không phải số bản ghi nguồn.

## 4. Cảnh báo dữ liệu (được chấp nhận có điều kiện)

**WARN 01 — Thiếu kỳ nội địa 2026-05.** Bộ kiểm tra phát hiện thiếu tháng 05/2026 trong chuỗi thời gian nội địa. Tại lần kiểm tra danh mục nguồn trước đó, tệp tháng này không xuất hiện. Không coi tháng thiếu là giá trị bằng 0 và không nội suy để tạo số liệu giả. Khi tính tăng trưởng MoM hoặc so sánh liên kỳ, phải kiểm tra kỳ so sánh có thực sự tồn tại.

**WARN 02 — 6.724 dòng Fact có ít nhất một sân bay thiếu tọa độ theo bộ kiểm tra.** Vẫn giữ các dòng trong phân tích giá và lượng ghế nếu hợp lệ; chỉ vẽ tuyến trên bản đồ khi có đủ tọa độ, đồng thời công bố tỷ lệ bao phủ của các tuyến có tọa độ. Việc bổ sung tọa độ cần dựa vào nguồn tham chiếu có thể kiểm chứng.

**Cảnh báo công cụ:** `pytest` ghi nhận **1 warning** liên quan đến cảnh báo tương thích/không khuyến nghị của `CallSpec2`. Không làm thất bại 17 bài test; cần xem lại phụ thuộc và phiên bản ở giai đoạn hoàn thiện môi trường.

## 5. Kết luận và giới hạn kiểm thử

**Kết luận:** Bước 3 **đạt nghiệm thu có điều kiện** đối với bộ quy tắc hiện tại: không có `FAIL`, 17/17 bài test đạt, KPI CSV và DuckDB khớp 56/56 dòng, và chế độ tái tổng hợp ETL cho kết quả ổn định khi chạy lại. Hai cảnh báo dữ liệu được ghi nhận để kiểm soát ở các bước phân tích và trực quan hóa.

**Chưa được khẳng định bởi các kết quả trên:**

1. Chưa có bằng chứng chạy kiểm thử end-to-end theo lịch trên GitHub Actions cho toàn chuỗi ETL → Incremental DuckDB → Dashboard.
2. Chưa có kết quả kiểm thử thực tế theo lịch khi ANAC công bố tháng mới hoặc sửa tháng cũ; các trường hợp này mới được kiểm tra ở mức unit test theo bộ hiện có.
3. Chưa kiểm chứng riêng tính lặp lại của toàn bộ thao tác nạp lại DuckDB bằng so sánh nội dung trước/sau ở môi trường thật sau thay đổi incremental.
4. Quality Gate chỉ chứng minh dữ liệu đạt **những quy tắc đã được cài đặt**, không chứng minh mọi giá trị đều chính xác tuyệt đối.

## 6. Cách chạy lại các phép kiểm tra chính

Chạy từ thư mục gốc `project` trong Terminal PowerShell:

```powershell
python qa_quality_gate.py
python -m pytest tests/ -v
python data_warehouse/incremental_warehouse.py --check
```

Lưu lại log Terminal hoặc ảnh chụp kết quả để làm minh chứng trong README/báo cáo. Tránh chạy `--apply` trên dữ liệu thật chỉ để thử các trường hợp lỗi; nên dùng bản sao DB và dữ liệu mẫu.

## 7. Công việc tiếp theo

- **Bước 4 — Phân tích chuyên sâu:** SQL cho xu hướng MoM/YoY, mức giá có trọng số, tương quan giữa giá và số ghế, tuyến bay, bất thường và độ phủ dữ liệu; có kiểm soát kỳ thiếu.
- **Bước 5 — Dashboard:** kết nối DuckDB, giữ phân biệt **BRL** (nội địa) và **USD** (quốc tế), không vẽ tuyến thiếu tọa độ.
- **Bước 6 — Tự động hóa:** kết nối GitHub Actions với kiểm thử chất lượng và cơ chế phát hành/cập nhật dữ liệu để Dashboard đọc được phiên bản mới.

---

*Tài liệu này ghi nhận các kết quả Terminal đã cung cấp đến thời điểm lập báo cáo; không phải chứng thư kiểm định độc lập của nguồn ANAC.*
