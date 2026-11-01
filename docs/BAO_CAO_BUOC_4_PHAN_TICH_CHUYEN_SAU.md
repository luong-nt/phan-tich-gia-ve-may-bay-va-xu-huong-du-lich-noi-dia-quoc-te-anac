# BƯỚC 4 — PHÂN TÍCH CHUYÊN SÂU DỮ LIỆU GIÁ VÉ ANAC

**Dự án:** Brazil Aviation Analytics — Data Engineering & Analytics Portfolio
**Nguồn phân tích:** DuckDB `anac.duckdb`, 17 truy vấn SQL (Q01–Q17), 17 bảng kết quả CSV do pipeline thực thi sinh ra
**Kỳ dữ liệu:** tháng bán vé từ 01/2024 đến 09/2026, không đồng nghĩa tháng khởi hành của chuyến bay
**Ngày tổng hợp báo cáo:** 30/10/2026
**Trạng thái:** Đã chạy 17/17 truy vấn; 20/20 phép kiểm tra tính nhất quán giữa các bảng kết quả đạt. Chưa phải xác minh độc lập toàn bộ dữ liệu ANAC gốc.

## 1. Tóm tắt điều hành

1. **Năm 2025, số ghế bán tăng trên cả hai thị trường.** Nội địa tăng **9,94%** lên **33.707.514 ghế**; quốc tế tăng **18,87%** lên **2.614.727 ghế** so với 2024. Tuy nhiên, giá vé bình quân có trọng số tăng nhẹ **1,63%** ở nội địa (629,88 → 640,17 BRL), trong khi giảm **7,12%** ở quốc tế (622,95 → 578,58 USD). Giá BRL và USD **không được so sánh trực tiếp**. [Q04]
2. **Năm 2026 chưa đủ dữ liệu để so tổng năm.** Đối chiếu 8 tháng chung **01–04 và 06–09** giữa năm 2025 và 2026 cho thị trường nội địa: số ghế bán giảm **3,42%**, giá vé bình quân có trọng số tăng **7,12%**. Kết luận này chỉ đúng với 8 tháng tương ứng, không phải mức tăng trưởng cả năm. [Q05, Q16]
3. **Số ghế quốc tế tập trung theo tuyến cao hơn nội địa.** Năm 2025, 10 tuyến có hướng lớn nhất chiếm **38,72%** ghế quốc tế so với **11,02%** ở nội địa. Đây là mức độ tập trung **theo tuyến bay**, không phải thị phần hãng hàng không. [Q11]
4. **Giá và số ghế thường biến động trái chiều nhưng không chứng minh quan hệ nhân quả.** Pearson năm 2025: nội địa **r = −0,6207**, quốc tế **r = −0,6092**; mỗi hệ số chỉ dựa trên 12 quan sát theo tháng. [Q07, Q08]
5. **Chất lượng tọa độ cần lưu ý khi vẽ bản đồ.** Có **6.724/221.288** dòng Fact thiếu tọa độ của ít nhất một đầu tuyến (**3,04%**); tương ứng **709.682/90.350.323** ghế bán (**0,79%**). Giữ dữ liệu này trong thống kê tổng hợp và chỉ lọc khi vẽ bản đồ. [Q15]

## 2. Phạm vi, định nghĩa chỉ số và phương pháp

- **Đơn vị thời gian:** tháng tham chiếu bán vé, không phải tháng thực hiện chuyến bay.
- **`total_seats` / `SO_GHE_BAN`:** số ghế bán được ghi nhận trong bộ dữ liệu; **không mặc định tương đương số hành khách thực bay** hoặc lượng khách du lịch.
- **`avg_fare`:** giá vé bình quân theo trọng số ghế có giá; khi gộp nhiều kỳ phải tính `SUM(fare_weighted_sum) / SUM(priced_seats)`, không lấy trung bình cộng các `avg_fare` theo tháng. [Q04, Q05, Q17]
- **Đơn vị tiền tệ:** nội địa BRL, quốc tế USD. Không cộng tiền hay so sánh trực tiếp giá giữa hai thị trường mà không quy đổi.
- **Grain Fact:** tháng × thị trường × sân bay đi × sân bay đến; tuyến **có hướng** (A→B khác B→A).
- **Độ phủ:** 2024 và 2025 có 12 tháng ở mỗi thị trường; 2026 chỉ có 8 tháng **nội địa** (01, 02, 03, 04, 06, 07, 08, 09). Không có dữ liệu quốc tế 2026 trong bản Warehouse được khảo sát. [Q01, Q04, Q16]
- **Giới hạn `price_coverage_pct`:** Q01 cho 100% đối với các dòng *đã được đưa vào Warehouse*. Đây không phải bằng chứng rằng dữ liệu thô ANAC hoàn toàn không thiếu giá; khâu ETL có thể đã lọc các dòng không đủ điều kiện.

## 3. Kết quả phân tích

### 3.1. Quy mô và diễn biến giá năm 2024–2025

| Thị trường | Năm | Số ghế bán | Giá vé bình quân có trọng số | Tiền tệ | Độ phủ |
|---|---:|---:|---:|---|---|
| Nội địa | 2024 | 30.660.967 | 629,88 | BRL | 12 tháng |
| Nội địa | 2025 | 33.707.514 | 640,17 | BRL | 12 tháng |
| Quốc tế | 2024 | 2.199.670 | 622,95 | USD | 12 tháng |
| Quốc tế | 2025 | 2.614.727 | 578,58 | USD | 12 tháng |

**Insight A — Tăng trưởng khối lượng và giá không đồng nhất:** Nội địa năm 2025 tăng số ghế **9,94%** và giá vé **1,63%** so với 2024. Quốc tế tăng ghế **18,87%** nhưng giảm giá vé **7,12%**. Đây là dấu hiệu hai thị trường có diễn biến khác nhau, không đủ để khẳng định nguyên nhân như khuyến mại, thay đổi cạnh tranh hay nhu cầu. [Q04]

**Gợi ý sử dụng:** Trên Dashboard, dùng hai nhóm biểu đồ riêng cho BRL và USD; có thẻ YoY cho số ghế và giá bình quân, kèm chú thích đơn vị tiền tệ.

### 3.2. So sánh cùng tập tháng năm 2026

Do **tháng 05/2026 không có trong Warehouse**, không so 8 tháng năm 2026 với 12 tháng năm 2025. Q05 ghép các tháng cùng số tháng có mặt ở cả hai năm: **01, 02, 03, 04, 06, 07, 08, 09**.

| Chỉ tiêu nội địa | 2025 — 8 tháng đối sánh | 2026 — 8 tháng đối sánh | Chênh lệch |
|---|---:|---:|---:|
| Ghế bán | 21.916.503 | 21.167.445 | **−3,42%** |
| Giá bình quân có trọng số | 639,30 BRL | 684,85 BRL | **+7,12%** |

Riêng **09/2026**, so với 09/2025, số ghế bán giảm **1,82%**, giá vé bình quân tăng **4,10%**; trong tháng 09/2026 có **2.551.248 ghế** và giá bình quân **746,62 BRL**. [Q01, Q03, Q05]

**Insight B — Phân tích cần so sánh đúng kỳ:** 8 tháng nội địa có dữ liệu trong 2026 cho thấy ghế bán thấp hơn, giá bình quân cao hơn cùng tập tháng 2025. Không diễn giải thành tăng trưởng cả năm hoặc tác động của việc thiếu tháng 05. Không điền 0 cho tháng thiếu; MoM tháng 06/2026 phải để trống vì không có tháng 05. [Q02, Q05, Q16]

### 3.3. Mùa vụ — mô tả thận trọng trên 2024–2025

Q06 tổng hợp 12 tháng lịch từ **hai năm có độ phủ đầy đủ**, theo thị trường và trọng số ghế có giá.

| Thị trường | Tháng có giá bình quân thấp nhất | Tháng có giá bình quân cao nhất | Tháng có số ghế trung bình thấp nhất | Tháng cao nhất |
|---|---|---|---|---|
| Nội địa | Tháng 05: **539,02 BRL** | Tháng 12: **748,04 BRL** | Tháng 12: **2.136.943** | Tháng 11: **3.231.872** |
| Quốc tế | Tháng 11: **536,33 USD** | Tháng 02: **687,67 USD** | Tháng 02: **174.511** | Tháng 11: **230.265** |

**Insight C — Mùa vụ có thể khác nhau giữa hai thị trường:** Trong mẫu 2024–2025, tháng có giá cao nhất không trùng giữa nội địa và quốc tế. Đây là quan sát trên **chỉ hai năm**, chưa đủ để xác định quy luật mùa vụ lâu dài hoặc dự báo chắc chắn. [Q06]

### 3.4. Quan hệ giữa giá và số ghế bán

| Năm | Nội địa — Pearson r | Số tháng | Quốc tế — Pearson r | Số tháng |
|---|---:|---:|---:|---:|
| 2024 | −0,2146 | 12 | −0,0349 | 12 |
| 2025 | **−0,6207** | 12 | **−0,6092** | 12 |
| 2026 | −0,1915 | 8 | — | — |

Q08 tìm thấy **39 kỳ MoM** có thay đổi giá và số ghế trái chiều: **22** ở nội địa, **17** ở quốc tế. Cơ sở là các kỳ tháng liền kề có đủ dữ liệu; không ghép tháng 04 với 06/2026 như hai tháng liên tiếp. [Q07, Q08]

**Insight D — Quan hệ nghịch nổi bật hơn ở 2025:** Hệ số r năm 2025 mang dấu âm ở hai thị trường. Tuy nhiên, tương quan không chứng minh giá gây ra thay đổi về số ghế: các yếu tố mùa vụ, đường bay, mức cung ứng và cấu trúc dữ liệu có thể cùng ảnh hưởng. Mẫu chỉ có 12 điểm/thị trường/năm; chưa thực hiện kiểm định ý nghĩa thống kê hoặc mô hình nhân quả.

### 3.5. Tuyến bay, sân bay và mức độ tập trung

**Mức độ tập trung của Top 10 tuyến có hướng:**

| Thị trường | 2024 | 2025 | Thay đổi |
|---|---:|---:|---:|
| Nội địa | 11,09% | **11,02%** | −0,07 điểm phần trăm |
| Quốc tế | 39,71% | **38,72%** | −0,99 điểm phần trăm |

**Insight E — Quốc tế tập trung theo tuyến hơn nội địa:** Top 10 tuyến quốc tế chiếm gần bốn phần mười số ghế, so với khoảng một phần chín ở nội địa. Có thể ưu tiên hiển thị Top tuyến quốc tế riêng; **không diễn giải tỷ trọng tuyến thành thị phần hãng**. [Q11]

**Ví dụ tuyến có số ghế cao:**

- Nội địa: **SBSP → SBRJ** đứng đầu năm 2024 với **570.211 ghế** và năm 2025 với **609.939 ghế**. Tuyến ngược **SBRJ → SBSP** là một tuyến riêng. [Q09]
- Quốc tế: năm 2024 tuyến **SBGR → SCEL** dẫn đầu với **231.676 ghế**; năm 2025 tuyến **SBGL → SCEL** dẫn đầu với **217.530 ghế**. [Q09]
- Tuyến có tỷ lệ tăng ghế nổi bật trong danh sách Q10 là **SBGL → SABE** (quốc tế): **19.288 → 92.159**, **+377,80%**; ví dụ nội địa **SBJP → SBSP**: **15.701 → 41.643**, **+165,23%**. Q10 yêu cầu cả hai năm có ít nhất **10.000 ghế**, chọn 20 tuyến theo **giá trị tuyệt đối của % thay đổi trong hai thị trường gộp**. Vì thế đây không phải danh sách đầy đủ mọi tuyến tăng hoặc giảm, và cũng không phải Top 20 *cho từng thị trường*. [Q10]

**Sân bay đến:** Ở thị trường nội địa, sân bay **SBSP** xếp đầu trong dữ liệu đã lọc năm 2024 (**3.474.714 ghế**) và 2025 (**3.851.270 ghế**). Ở thị trường quốc tế, sân bay **SCEL** đứng đầu với **634.904** (2024) và **666.135** (2025) ghế theo truy vấn có điểm đi từ Brazil và đủ mã quốc gia. Q12 có thể loại một số sân bay thiếu mapping quốc gia. [Q12]

**Giá theo tuyến:** Q13 chỉ xếp hạng các tuyến đạt tối thiểu **10.000 ghế/năm**, nhằm tránh việc tuyến quá nhỏ đứng đầu chỉ vì mẫu giá không ổn định. Ví dụ nội địa 2024 tuyến **SBGR → SBPV** có giá bình quân **1.187,82 BRL** với **16.912 ghế**. [Q13]

### 3.6. Tín hiệu biến động mạnh và giới hạn suy luận

Q14 sử dụng **ngưỡng thực hành**: thay đổi giá MoM từ **20%** hoặc số ghế từ **30%** trở lên. Truy vấn xuất **3 kỳ**, đều ở thị trường nội địa:

| Tháng | Thay đổi giá MoM | Thay đổi ghế MoM | Cờ |
|---|---:|---:|---|
| 01/2025 | −14,77% | +35,39% | Ghế ≥ 30% |
| **12/2025** | **+21,59%** | **−41,12%** | Giá ≥ 20% và ghế ≥ 30% |
| 01/2026 | −17,82% | +39,59% | Ghế ≥ 30% |

**Insight F — Tháng 12/2025 cần được điều tra trước:** Giá và ghế có biến động lớn ngược chiều so với 11/2025. Đây là **cờ cảnh báo theo ngưỡng do dự án chọn**, chưa phải bằng chứng của lỗi dữ liệu hoặc nguyên nhân thị trường. Khi có điều kiện, kiểm tra lại tính đầy đủ nguồn, độ phủ giá, và thành phần tuyến trước khi đưa ra giải thích. [Q02, Q14]

### 3.7. Độ phủ tọa độ và thời gian

Q15 ghi nhận **221.288 dòng Fact**, trong đó **6.724 dòng** thiếu tọa độ của một trong hai sân bay, tương đương **3,04%** dòng Fact. Những dòng này đại diện **709.682 / 90.350.323 ghế** (**0,79%** theo trọng số ghế). Như vậy, dữ liệu đủ tọa độ để hiển thị bản đồ chiếm khoảng **99,21% tổng số ghế** trong phạm vi Fact, nhưng không đồng nghĩa phủ 99,21% sân bay. [Q15]

Q16 phát hiện **một khoảng trống bên trong chuỗi tháng đã có**: **05/2026, nội địa**. Kết quả chỉ có nghĩa là tháng đó **không hiện diện trong Warehouse**. Không thể từ kết quả SQL này khẳng định nguồn ANAC chưa công bố, đang hỏng hay đã được thay thế ở URL khác. [Q16]

Q17 chỉ tổng hợp các quý có **đủ 3 tháng**: **18 dòng** KPI quý. Với nội địa 2026, quý I và quý III có mặt, còn quý II **không được xuất** do thiếu tháng 05. [Q17]

## 4. Đối chiếu độc lập các bảng CSV kết quả

Đã kiểm tra toàn bộ 17 file CSV có mặt và thực hiện **20 phép kiểm tra nhất quán độc lập trong Python**, kết quả **20 PASS / 0 FAIL**. Phạm vi gồm:

- Khóa tháng–thị trường và ánh xạ tiền tệ không trùng/sai; KPI dương, `priced_seats` không vượt `total_seats`.
- MoM (53 so sánh có tháng trước liền kề) và YoY (32 so sánh có cùng tháng năm trước) được tính lại từ Q01, cho phép sai số nhỏ do CSV đã làm tròn giá.
- Tổng năm Q04, so sánh cùng tập tháng Q05, mùa vụ Q06, Pearson Q07, cờ nghịch chiều Q08 và cảnh báo Q14 được đối chiếu.
- Ràng buộc xếp hạng Q09/Q12/Q13, tăng trưởng và ngưỡng của Q10, mức tập trung Q11, độ phủ tọa độ Q15, kỳ thiếu Q16, quý đủ tháng Q17 được xác nhận.

**Giới hạn của kiểm thử:** Đối chiếu các file kết quả của **cùng một Data Warehouse**, không chứng minh mọi bản ghi trong nguồn ANAC gốc đều đúng hoặc mọi join theo sân bay đã hợp lệ. Không thay thế bộ Data Quality & Testing ở Bước 3.

Chạy lại đối chiếu khi cập nhật dữ liệu mới:

```powershell
python data_warehouse/queries/verify_analysis_results.py --results-dir data_warehouse/analysis_results
```

## 5. Khuyến nghị cho Dashboard và Portfolio

1. **Trang Tổng quan:** KPI theo năm/thị trường, tách tiền tệ; ghi rõ kỳ cập nhật đến **09/2026**, phân biệt năm đầy đủ và năm đang cập nhật.
2. **Trang Xu hướng:** Biểu đồ đường giá và ghế, MoM/YoY, chế độ so sánh **cùng kỳ đủ dữ liệu**; khoảng trống 05/2026 phải hiển thị là thiếu, không nối/tính MoM sai.
3. **Trang Mạng lưới:** Top tuyến **có hướng**, thay đổi quy mô giữa hai năm đầy đủ, tập trung Top 10, và bản đồ chỉ dùng tuyến có tọa độ hợp lệ; hiển thị tỷ lệ loại khỏi bản đồ.
4. **Trang Phân tích chuyên sâu:** Scatter giá–ghế theo tháng (không gán nhân quả), Pearson theo từng năm, danh sách cảnh báo theo ngưỡng có ghi chú.
5. **Tài liệu kỹ thuật:** Giữ `analysis.sql`, `run_analysis.py`, 17 file CSV xuất, script đối chiếu và báo cáo này để nhà tuyển dụng có thể kiểm tra toàn bộ chuỗi từ dữ liệu đến insight.

## 6. Những gì chưa thể kết luận từ bộ dữ liệu hiện có

- Không suy ra giá vé tăng/giảm **vì** biến động số ghế; không kết luận mức độ co giãn nhu cầu hoặc ảnh hưởng chính sách.
- Không coi ghế bán là số chuyến bay, hành khách thực bay hoặc số lượt du lịch.
- Không so sánh mức giá BRL và USD trực tiếp; cũng không gộp doanh thu hai thị trường nếu chưa giải quyết đơn vị, cấu trúc giá và phạm vi sản phẩm.
- Không dùng 8 tháng 2026 như thể là năm đủ 12 tháng; không tự điền 0 vào 05/2026.
- Không khẳng định 100% dữ liệu giá nguồn hoàn chỉnh chỉ vì các dòng đã nạp DuckDB đều có giá.
- Các ngưỡng bất thường và tương quan mới mang tính mô tả/khám phá; chưa thực hiện suy luận thống kê, ước lượng sai số hoặc truy tìm nguyên nhân ngoài tập CSV.

## 7. Danh mục 17 truy vấn và bảng minh chứng

| Truy vấn | Chủ đề | Số dòng CSV |
|---|---|---:|
| Q01 | KPI theo tháng | 56 |
| Q02 | MoM chỉ với tháng liền kề | 56 |
| Q03 | YoY cùng tháng | 56 |
| Q04 | KPI theo năm, đánh dấu độ phủ | 5 |
| Q05 | So sánh 2026–2025 theo cùng tập tháng | 1 |
| Q06 | Xu hướng theo tháng lịch 2024–2025 | 24 |
| Q07 | Tương quan Pearson theo năm/thị trường | 5 |
| Q08 | Tháng giá–ghế thay đổi ngược chiều | 39 |
| Q09 | Top 20 tuyến theo năm/thị trường | 80 |
| Q10 | 20 tuyến có % thay đổi lớn nhất trong mẫu chọn | 20 |
| Q11 | Tập trung Top 10 tuyến | 4 |
| Q12 | Top 10 sân bay đến | 40 |
| Q13 | Top 10 tuyến có giá cao, ngưỡng ghế | 40 |
| Q14 | Cờ biến động theo ngưỡng | 3 |
| Q15 | Độ phủ tọa độ | 5 |
| Q16 | Kỳ thiếu trong Warehouse | 1 |
| Q17 | KPI theo quý đủ 3 tháng | 18 |

**Nguồn minh chứng:** `data_warehouse/analysis_results/Q01.csv` đến `Q17.csv` (tệp của chính dự án do bạn đã chạy và gửi). Các chỉ số ở đây phản ánh đúng phiên bản dữ liệu được xuất tại thời điểm kiểm tra. Khi ANAC công bố dữ liệu mới, cần chạy lại truy vấn và cập nhật báo cáo để tránh dùng thông tin cũ.
