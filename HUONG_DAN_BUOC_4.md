# BƯỚC 4 — PHÂN TÍCH CHUYÊN SÂU ANAC (DuckDB + SQL)

## Từ mã nguồn cũ đến phiên bản mới

File `analysis.sql` cũ có 3 truy vấn: KPI tháng, tăng trưởng giá vé YoY, Top 10 tuyến nội địa 2024. Bản mới mở rộng thành **17 truy vấn độc lập, chỉ đọc dữ liệu** trong 5 nhóm:

| Nhóm | Query | Mục tiêu |
| --- | --- | --- |
| 4.1. Thời gian & tăng trưởng | Q01–Q06 | KPI theo tháng, MoM đúng tháng liền kề, YoY đúng tháng, tổng hợp năm có trọng số, so sánh 2026 với đúng các tháng 2025 tương ứng, mùa vụ |
| 4.2. Giá và số ghế bán | Q07–Q08 | Tương quan Pearson và dấu hiệu giá–ghế biến động ngược chiều |
| 4.3. Phân tích tuyến/điểm đến | Q09–Q13 | Top tuyến, tăng trưởng 2024–2025, tỷ trọng ghế Top 10 tuyến, sân bay đến từ Brazil, giá tuyến có ngưỡng quy mô |
| 4.4. Bất thường/chất lượng | Q14–Q16 | Ngưỡng cảnh báo MoM, mức độ thiếu tọa độ, kỳ trống trong DW |
| 4.5. Tổng hợp phục vụ Dashboard | Q17 | KPI theo quý nhưng chỉ xuất quý có đủ 3 tháng |

## Cài đặt — KHÔNG sửa file DW hay ETL

Đặt hai file vào:

```text
project/
  data_warehouse/
    anac.duckdb               (giữ nguyên)
    queries/
      analysis.sql            (thay file cũ; có thể sao lưu)
      run_analysis.py         (thêm mới)
```

Chạy ở Terminal VS Code đang đứng trong thư mục `project`:

```powershell
python data_warehouse/queries/run_analysis.py --list
python data_warehouse/queries/run_analysis.py --check
```

Lệnh `--check` mở DuckDB **read-only**, chỉ kiểm tra cú pháp SQL + tên cột/bảng bằng `EXPLAIN`, **không chạy các phép tổng hợp và không xuất file CSV**.

Sau khi tất cả đều PASS, chạy thử riêng truy vấn phân tích MoM:

```powershell
python data_warehouse/queries/run_analysis.py --only Q02
```

Để chạy tất cả truy vấn và xuất 17 file kết quả:

```powershell
python data_warehouse/queries/run_analysis.py --all
```

Kết quả sẽ nằm trong `project/data_warehouse/analysis_results/Q01.csv` ... `Q17.csv`. Dữ liệu kết quả có thể được dùng làm đầu vào báo cáo, Dashboard và các biểu đồ.

## Những nguyên tắc nghiệp vụ bắt buộc

1. **Thời gian**: `THANG` là **tháng bán vé**, không phải ngày/tháng thực hiện chuyến bay.
2. **Số ghế**: `total_seats` là **ghế bán**, không khẳng định số hành khách thực tế đã bay.
3. **Tiền tệ**: nội địa **BRL**, quốc tế **USD**. Chỉ so sánh giá trong cùng thị trường/tiền tệ; không cộng hai loại tiền.
4. **Giá có trọng số**: dùng `SUM(fare_weighted_sum) / SUM(priced_seats)` để gộp nhiều tháng. Không lấy `AVG(avg_fare)` làm giá bình quân của cả năm.
5. **Kỳ thiếu**: nội địa 2026 thiếu tháng 05 trong dữ liệu hiện có, 2026 chưa đủ năm. MoM chỉ tính khi có hai tháng **liền kề thực sự**; Q2/2026 nội địa bị loại khỏi KPI theo quý vì thiếu một tháng.
6. **YoY/YTD**: so cùng tháng hoặc chỉ các tháng xuất hiện ở cả hai năm, không lấy 8 tháng 2026 so với toàn bộ 12 tháng 2025.
7. **Tương quan**: Pearson r mô tả liên hệ thống kê, **không chứng minh giá làm thay đổi lượng ghế bán**; số tháng quan sát còn ít.
8. **Tuyến bay**: chiều `ORIGEM -> DESTINO` khác `DESTINO -> ORIGEM`.
9. **Thiếu tọa độ/quốc gia**: không xóa bản ghi Fact; báo tỷ lệ ảnh hưởng trong Q15. Q12 có lọc thông tin quốc gia nên có thể bỏ qua các sân bay chưa được map đầy đủ.
10. **Cảnh báo bất thường**: Q14 dùng ngưỡng thực hành 20% về giá, 30% về ghế, chỉ là tín hiệu cần xem xét, không khẳng định dữ liệu sai.
11. **Độ phủ giá**: số `price_coverage_pct` phản ánh ghế còn lại trong Fact sau ETL/lọc dữ liệu, không chứng minh độ đầy đủ của CSV nguồn thô.

## Kiểm thử trước khi trình bày Portfolio

- 17/17 câu SQL biên dịch được (`--check`).
- 17/17 câu SQL chạy được (`--all`).
- Q01 trả khoảng 56 dòng KPI với dữ liệu hiện có (24 kỳ năm 2024, 24 kỳ năm 2025, 8 kỳ nội địa năm 2026).
- Q02: tháng 2026-06 nội địa `previous_month_key` là NULL, vì thiếu tháng 05/2026. Không được tự so với 2026-04.
- Q05: chỉ so các tháng nội địa 2026 đang có với những tháng 2025 tương ứng (danh sách tháng được xuất kèm).
- Q16: nêu tháng 05/2026 nội địa trống trong DW; **không tự kết luận ANAC chưa công bố**.
- Q17: loại Q2/2026 nội địa do không đủ ba tháng.
- Nếu bất kỳ mục nào không đúng, dừng việc viết insight và đối chiếu lại dữ liệu / SQL.

## Viết insight có bằng chứng

Khi có kết quả Q01...Q17, dùng mẫu: **Phát hiện → Bằng chứng số liệu (câu truy vấn + tháng + thị trường) → Diễn giải có giới hạn → Hàm ý**. Không đưa kết luận khẳng định nguyên nhân nếu chỉ có tương quan.

## Giới hạn xác minh phiên bản cung cấp

File SQL được xây dựng dựa trên schema đã có (`fact_airfare_route_monthly`, `dim_month`, `dim_market`, `dim_airport`, `vw_monthly_kpi`, `vw_route_ranking`) và kết quả bạn đã chạy trước đó. Chưa thể chạy trên DuckDB riêng của bạn trong môi trường này: hãy dùng `--check` rồi gửi kết quả Terminal để sửa nếu schema thực tế khác.
