# BUSINESS INSIGHTS & ANALYTICAL FINDINGS

## Phân tích chuyên sâu thị trường vé máy bay Brazil (ANAC), 2024–09/2026

**Dự án:** Brazil Aviation Analytics — Data Engineering / Data Analyst / BI Portfolio
**Dữ liệu phân tích:** 17 bảng kết quả `Q01.csv`–`Q17.csv` sinh từ DuckDB; tải vào ngày 30/10/2026.
**Đơn vị thời gian:** *tháng tham chiếu bán vé*, không phải tháng thực hiện chuyến bay.
**Đơn vị quy mô:** *số ghế bán trong dữ liệu*, không đồng nhất với số hành khách thực bay.
**Đơn vị giá:** nội địa **BRL**, quốc tế **USD**; tuyệt đối không so sánh trực tiếp trị giá giữa hai đơn vị tiền tệ.
**Nguyên tắc:** Phân biệt **số liệu quan sát → diễn giải/insight → hàm ý phân tích → giới hạn/kiểm chứng tiếp**. Giá bình quân gộp nhiều kỳ là trung bình **có trọng số ghế có giá**, không phải trung bình các giá tháng.

---

## Tóm tắt 6 insight đáng trình bày đầu tiên

| Ưu tiên | Phát hiện | Ý nghĩa chính | Bằng chứng |
|---|---|---|---|
| 1 | Số ghế quốc tế 2025 **+18,87%**, giá bình quân **−7,12%** | Tăng trưởng số ghế bán và giá vé không đồng nghĩa cùng chiều | Q04, Q03 |
| 2 | Nội địa có **tháng 05 rẻ nhất**, **tháng 12 đắt nhất** ở **cả 2024 và 2025** | Có dấu hiệu mô hình theo mùa đáng phân tích, chưa chứng minh quy luật dài hạn | Q01, Q06 |
| 3 | 2025: **3/17** tuyến nội địa và **5/15** tuyến quốc tế nằm trong Top 20 ở cả hai năm **giảm ghế bán** | Tăng trưởng thị trường không đồng đều giữa các tuyến | Q09 |
| 4 | 2025, Pearson giá–ghế **−0,6207** nội địa và **−0,6092** quốc tế; 2024 tương ứng **−0,2146** và **−0,0349** | Tương quan nghịch không ổn định qua năm; chưa suy ra quan hệ nhân quả | Q07, Q08 |
| 5 | Nội địa 12/2025: giá MoM **+21,59%**, ghế **−41,12%** | Biến động bất thường đáng ưu tiên phân tích, không mặc định là sai dữ liệu | Q02, Q14 |
| 6 | Top 10 tuyến quốc tế chiếm **38,72%** ghế năm 2025; nội địa **11,02%** | Số ghế quốc tế tập trung hơn vào một số tuyến có hướng | Q11 |

## Câu hỏi 1 — Giá vé tăng mạnh khi nào? Có lặp lại theo năm không?

### A. Số liệu quan sát

**Các lần tăng giá nội địa theo tháng nổi bật** (MoM, chỉ so tháng liền kề có dữ liệu):

| Kỳ | Giá MoM | Ghế bán MoM | Nhận xét |
|---|---:|---:|---|
| 12/2025 | **+21,59%** | **−41,12%** | Biến động mạnh nhất về giá nội địa trong các kỳ có so sánh |
| 06/2025 | +15,78% | −18,86% | Giá tăng cùng lúc ghế giảm |
| 03/2026 | +15,48% | +12,29% | Giá và ghế cùng tăng: quan hệ không phải lúc nào cũng ngược chiều |
| 07/2025 | +12,96% | −0,91% | Giá tăng, số ghế giảm nhẹ |

Đối với **quốc tế**, tháng **02/2024** tăng giá **+15,61%** so với tháng 01/2024, và **02/2025** tăng **+13,65%** so với tháng 01/2025. [Q02]

**Tín hiệu lặp lại có thể kiểm chứng trên từng năm:**

| Thị trường | Năm 2024 | Năm 2025 | Kết luận về mức độ lặp |
|---|---|---|---|
| Nội địa — tháng giá thấp nhất | Tháng 05: **534,32 BRL** | Tháng 05: **543,29 BRL** | **Lặp lại 2/2 năm** |
| Nội địa — tháng giá cao nhất | Tháng 12: **757,01 BRL** | Tháng 12: **739,17 BRL** | **Lặp lại 2/2 năm** |
| Quốc tế — tháng giá thấp nhất | Tháng 11: **536,97 USD** | Tháng 11: **535,85 USD** | **Lặp lại 2/2 năm** |

Khi gộp hai năm theo trọng số ghế, nội địa tháng 05 **539,02 BRL**, tháng 12 **748,04 BRL**; quốc tế tháng 11 **536,33 USD**, tháng 02 **687,67 USD**. [Q01, Q06]

### B. Insight

**Giá vé trong dữ liệu có dấu hiệu mùa vụ theo thị trường, nhưng nhịp cao/thấp không giống nhau.** Đặc biệt, thời điểm giá nội địa thấp nhất (tháng 05) và cao nhất (tháng 12) trùng giữa hai năm quan sát, giúp định hướng việc theo dõi những tháng này trong Dashboard. Không nên kết luận “giá luôn tăng vào cuối năm” bởi giá nội địa tháng **11/2025 giảm 15,62%** so với tháng 10, rồi mới tăng mạnh vào tháng 12. [Q02]

### C. Hàm ý và giới hạn

- **Nên làm:** hiển thị biểu đồ giá theo *tháng trong năm* với hai đường 2024/2025; đánh dấu tháng cực trị và thể hiện khoảng thiếu dữ liệu.
- **Không được kết luận:** đây là quy luật mùa vụ lâu dài hay thời điểm tốt nhất để đặt vé; chỉ có hai năm dữ liệu bán vé và chưa kiểm soát thay đổi cơ cấu tuyến, thời điểm mua trước ngày bay hoặc sự kiện bên ngoài.

## Câu hỏi 2 — Thị trường nào tăng trưởng tốt hơn? Có phải mọi tuyến đều tăng?

### A. Quy mô và giá cả

| Thị trường (2025 so với 2024) | Số ghế 2024 | Số ghế 2025 | Ghế YoY | Giá vé có trọng số YoY |
|---|---:|---:|---:|---:|
| Nội địa | 30.660.967 | 33.707.514 | **+9,94%** | **+1,63% (BRL)** |
| Quốc tế | 2.199.670 | 2.614.727 | **+18,87%** | **−7,12% (USD)** |

Mức tăng tuyệt đối số ghế: nội địa **3.046.547 ghế**, quốc tế **415.057 ghế**. So sánh YoY theo tháng cho thấy **12/12 tháng của quốc tế** và **9/12 tháng của nội địa** năm 2025 có số ghế cao hơn cùng tháng 2024. [Q03, Q04]

### B. Trả lời “mọi tuyến đều tăng?” — KHÔNG

**Chứng cứ trực tiếp:** trong các tuyến *cùng lọt Top 20 tuyến có hướng* của năm 2024 và 2025:

- Nội địa: **17 tuyến cùng xuất hiện**; **3 tuyến giảm** số ghế.
- Quốc tế: **15 tuyến cùng xuất hiện**; **5 tuyến giảm** số ghế.

| Tuyến có hướng | Loại | Ghế 2024 | Ghế 2025 | Mức thay đổi |
|---|---|---:|---:|---:|
| SBSV → SBSP | Nội địa | 271.238 | 257.345 | **−5,12%** |
| SBGR → SCEL | Quốc tế | 231.676 | 179.990 | **−22,31%** |
| SBGR → SAEZ | Quốc tế | 56.648 | 30.903 | **−45,45%** |

*Đây là phép đối chiếu **nhóm giao nhau của hai Top 20**, chưa phải thống kê tăng/giảm của tất cả tuyến.* Q10 hiện chỉ xuất các tuyến có **biến động lớn nhất** theo tiêu chí lọc và không thể đại diện cho toàn mạng lưới. [Q09, Q10]

### C. Insight

**Tăng trưởng 2025 có tính phân hóa:** cả hai thị trường tăng tổng số ghế, nhưng ngay trong các tuyến lớn vẫn có tuyến giảm. Vì vậy, phân tích tổng thị trường đơn thuần có thể che lấp sự dịch chuyển giữa các tuyến.

Đáng chú ý, số **tuyến có hướng được ghi nhận** trong dữ liệu nội địa giảm từ **10.543** (2024) xuống **8.754** (2025), tương đương **−16,97%**, dù tổng số ghế tăng. Quốc tế tăng số tuyến ghi nhận từ **1.947** lên **2.135** (**+9,66%**). Đây là thay đổi **độ phủ tuyến trong bộ dữ liệu**, **không đủ để khẳng định** các đường bay thực tế đã đóng/mở; trước khi suy luận phải kiểm tra phương pháp báo cáo và xử lý dữ liệu giữa hai năm. [Q11]

### D. Hàm ý

Dashboard nên có chức năng lọc và so sánh **tuyến cụ thể giữa hai năm**, đánh dấu tuyến mới/xuất hiện lại, tuyến giảm, và chú thích chiều đi/chiều về là khác nhau. Cần phân tích toàn bộ tuyến (không chỉ Top 20) trước khi kết luận tỷ lệ mạng lưới tăng hoặc giảm.

## Câu hỏi 3 — Giá tăng thì số ghế thường giảm? Có ổn định qua các năm?

### A. Kết quả Pearson r theo tháng

| Năm | Nội địa | Quốc tế | Số quan sát/thị trường |
|---|---:|---:|---|
| 2024 | −0,2146 | −0,0349 | 12 tháng |
| 2025 | **−0,6207** | **−0,6092** | 12 tháng |
| 2026 | −0,1915 | Không có dữ liệu | 8 tháng nội địa |

Trong các lần so sánh tháng liền kề hợp lệ, giá và ghế biến động ngược chiều ở **22/30 lần nội địa (73.3%)** và **17/23 lần quốc tế (73.9%)**. Tính chung là **39/53 lần (73,6%)**. [Q02, Q07, Q08]

### B. Insight

**Mối liên hệ nghịch giữa giá và số ghế nổi bật trong 2025, nhưng không ổn định qua các năm.** Năm 2024, Pearson của quốc tế gần 0, còn năm 2025 giảm xuống khoảng −0,61. Không thể lấy kết quả một năm để khẳng định quan hệ ổn định của thị trường.

Quan hệ ngược chiều cũng **không phải tuyệt đối**: tháng 03/2026 nội địa ghi nhận **giá tăng 15,48%** và **ghế tăng 12,29%** so với tháng trước. [Q02]

### C. Hàm ý và giới hạn

Đây là **tương quan tuyến tính trên dữ liệu tổng hợp theo tháng**, không phải độ co giãn của cầu và không chứng minh “tăng giá gây giảm người mua”. Giá là giá bình quân của các vé đã bán, còn lượng ghế cũng chịu ảnh hưởng của cơ cấu tuyến, cung ghế, mùa vụ, và quy trình ghi nhận. Chưa có kiểm định ý nghĩa thống kê và chưa điều chỉnh biến gây nhiễu.

## Câu hỏi 4 — Số ghế tập trung vào một số tuyến hay phân tán? Tuyến nào nổi bật?

### A. Tỷ lệ tập trung Top 10 tuyến có hướng

| Năm | Nội địa | Quốc tế |
|---|---:|---:|
| 2024 | **11,09%** | **39,71%** |
| 2025 | **11,02%** | **38,72%** |

Năm 2025, Top 10 tuyến quốc tế chiếm khoảng **3,51 lần** tỷ trọng ghế so với Top 10 tuyến nội địa. Mức tập trung Top 10 của cả hai thị trường **giảm nhẹ** so với năm 2024. [Q11]

### B. Tuyến tiêu biểu

- Nội địa **SBSP → SBRJ** đứng đầu số ghế năm 2024 (**570.211**) và 2025 (**609.939**), tăng khoảng **6,97%**. Tuyến chiều ngược lại được tính riêng. [Q09]
- Quốc tế **SBGR → SCEL** từ **231.676** xuống **179.990** (**−22,31%**), trong khi **SBGL → SCEL** dẫn đầu năm 2025 với **217.530 ghế**. Điều này cho thấy thay đổi vị trí các tuyến dẫn đầu, không chỉ thay đổi quy mô tổng thị trường. [Q09]
- Trong danh sách các tuyến có mức tăng mạnh được lọc ở Q10: **SBGL → SABE** (**19.288 → 92.159**, **+377,80%**) và **SBJP → SBSP** (**15.701 → 41.643**, **+165,23%**). Hai giá trị này cần diễn giải kèm mức gốc và điều kiện lọc tối thiểu 10.000 ghế/năm ở cả hai năm. [Q10]

### C. Insight

**Ghế bán quốc tế tập trung rõ hơn theo tuyến, nhưng tuyến dẫn đầu vẫn có thể thay đổi.** Vì thế, Dashboard cần hiển thị cả **tỷ trọng Top 10** (mức tập trung) và **Top tuyến thay đổi theo năm** (cấu trúc mạng lưới), thay vì chỉ một bảng xếp hạng tĩnh.

Q11 là **tập trung theo tuyến có hướng**, không phải thị phần hãng hàng không. Dữ liệu Fact hiện tại không có chiều hãng nên không thể phân tích cạnh tranh giữa các hãng từ bảng này.

## Câu hỏi 5 — Vì sao có tháng giá thay đổi đột ngột? Kết luận đến đâu?

### A. Trường hợp cần ưu tiên kiểm tra: nội địa tháng 12/2025

| Tháng | Giá BRL | Số ghế bán | So với tháng trước |
|---|---:|---:|---|
| 11/2025 | 607,92 | 3.648.451 | — |
| **12/2025** | **739,17** | **2.148.302** | **Giá +21,59%; ghế −41,12%** |

Trong năm trước, tháng 12/2024 cũng có **giá +4,20% và ghế −24,50%** so với tháng 11/2024. Vậy chiều biến động lặp lại nhưng **biên độ 12/2025 mạnh hơn**, nhất là lượng ghế bán. [Q02, Q14]

Q14 dùng ngưỡng *do dự án định nghĩa* (giá MoM thay đổi từ 20% hoặc ghế MoM từ 30%). Theo ngưỡng này chỉ có **3 kỳ bị gắn cờ**, đều nội địa: **01/2025**, **12/2025**, **01/2026**. [Q14]

### B. Insight

**12/2025 là tín hiệu cần điều tra, không phải bằng chứng giá vé bị sai hoặc nguyên nhân là cung/cầu.** Hiện tượng chuyển từ tháng 11 sang tháng 12 xuất hiện cả hai năm, song độ lớn khác nhau; cần đối chiếu biến động **trong từng tuyến** và thay đổi **trọng số tuyến** để xác định giá bình quân tăng do giá trong tuyến tăng hay do cơ cấu bán vé thay đổi.

### C. Các giả thuyết cần kiểm chứng (chưa phải kết luận)

1. **Cơ cấu tuyến:** Những tuyến có giá cao chiếm tỷ trọng ghế lớn hơn vào tháng 12?
2. **Giá ngay trong cùng tuyến:** Trên nhóm tuyến có dữ liệu cả 11 và 12/2025, giá bình quân theo tuyến có tăng đáng kể?
3. **Cơ cấu hãng / loại vé / thời gian đặt trước:** Chưa có sẵn trong Fact hiện tại; cần thêm dữ liệu chi tiết phù hợp để trả lời.
4. **Độ phủ và thay đổi công bố:** Kiểm tra có cập nhật lại nguồn, đổi tiêu chí thu thập hoặc thay đổi chất lượng dữ liệu giữa hai tháng không.

**Kết luận có thể công bố:** “Dữ liệu ANAC cho thấy giá bình quân nội địa tháng 12/2025 tăng mạnh cùng với mức giảm số ghế bán, cần điều tra nguyên nhân ở cấp tuyến/hãng”. **Không công bố:** “Vì thiếu ghế nên giá chắc chắn tăng” hoặc “hành khách giảm vì giá tăng” khi chưa kiểm chứng nhân quả.

## 6. Độ tin cậy dữ liệu và những kết luận cần tránh

- **Tháng 05/2026 nội địa không có trong Warehouse**; đây là trạng thái thiếu dữ liệu nguồn chưa xác minh lý do cuối cùng, **không phải số ghế = 0**. Không tính MoM của 06/2026 so với 04/2026. Chỉ đối chiếu 8 tháng chung 2025–2026: số ghế **−3,42%**, giá bình quân **+7,12%**. [Q05, Q16]
- **Không có dữ liệu quốc tế 2026** trong Warehouse hiện tại; không được kết luận về xu hướng quốc tế năm 2026. [Q01, Q04]
- **Bản đồ:** 6.724/221.288 dòng Fact thiếu tọa độ ở ít nhất một đầu tuyến; liên quan **709.682/90.350.323 ghế** (**0,79%**). Chỉ lọc cho bản đồ, không bỏ khỏi thống kê tổng. [Q15]
- **Độ phủ giá 100%** là của dữ liệu **đã vào Warehouse**, không chứng minh bản dữ liệu thô ANAC không thiếu giá. [Q01]
- **Năm 2025 tăng trưởng** không có nghĩa mọi tuyến tăng hoặc tất cả người Brazil đi du lịch nhiều hơn; đây là số ghế bán theo phạm vi dữ liệu.
- Các ngưỡng gắn cờ bất thường và cách tính tương quan là **quy tắc phân tích do dự án chọn**; không mặc định là tiêu chuẩn nghiệp vụ bên ngoài.

## 7. Đề xuất trình bày trên Dashboard (gắn với câu hỏi thực tế)

| Câu hỏi quản lý | Thành phần đề xuất | Dữ liệu/SQL hiện có | Ghi chú bắt buộc |
|---|---|---|---|
| Giá khi nào tăng mạnh, có mùa vụ? | Biểu đồ giá theo tháng, đường 2024/2025 và đánh dấu cực trị | Q01, Q02, Q06 | Tránh khẳng định mùa vụ dài hạn |
| Thị trường nào tăng trưởng? | KPI YoY ghế/giá riêng mỗi thị trường | Q03, Q04, Q05 | BRL và USD riêng; cảnh báo năm không đủ tháng |
| Tăng trưởng có đồng đều giữa các tuyến? | Bảng so sánh tuyến + lọc tăng/giảm | Q09, Q10; cần truy vấn toàn Fact để bao phủ mọi tuyến | Không lấy Top 20 làm đại diện cho tất cả |
| Giá và lượng ghế liên hệ thế nào? | Scatter giá vs ghế theo tháng; r theo năm | Q07, Q08 | Hiển thị n và chú thích không suy ra nhân quả |
| Mức tập trung vào tuyến lớn? | Top 10 share và xếp hạng tuyến động | Q09, Q11 | Tuyến có hướng, không phải hãng |
| Tháng nào biến động khác thường? | Bảng cờ cảnh báo và drill-down theo tuyến | Q02, Q14 | Ngưỡng cảnh báo do dự án chọn |

## 8. Kết luận tổng hợp dành cho Portfolio

> Phân tích 2024–2025 cho thấy số ghế bán tăng ở cả thị trường nội địa và quốc tế, nhưng diễn biến giá và sự phân bổ theo tuyến khác nhau. Thị trường quốc tế tăng số ghế mạnh hơn trong khi giá bình quân giảm; mạng lưới quốc tế có tỷ trọng tập trung vào Top 10 tuyến cao hơn. Ở nội địa, tháng 05 có mức giá thấp nhất và tháng 12 cao nhất trong cả hai năm quan sát, gợi ý tính mùa vụ cần theo dõi. Dù thị trường tăng trưởng chung, một số tuyến lớn vẫn suy giảm số ghế. Biến động mạnh của tháng 12/2025 cần được điều tra ở cấp tuyến thay vì gán ngay cho một nguyên nhân duy nhất. Mọi kết luận đều được giới hạn trong số ghế bán và tháng bán vé của bộ dữ liệu ANAC, không đồng nhất với số hành khách thực bay hay quan hệ nhân quả.

## 9. Dẫn chứng và truy xuất

Tất cả số liệu và khẳng định định lượng trong báo cáo đều truy xuất về bộ dữ liệu do người thực hiện xuất từ DuckDB (`data_warehouse/analysis_results/Q01.csv` đến `Q17.csv`). `Q09` chỉ xuất 20 tuyến đứng đầu theo năm và thị trường; Q10 chỉ xuất 20 tuyến biến động mạnh theo điều kiện lọc, do đó phần trả lời “mọi tuyến?” chỉ là **bằng chứng phản ví dụ** từ các tuyến lặp lại trong Top 20, chưa phải một phép đo toàn bộ tuyến.

**Khả năng tái lập:** Chạy `python data_warehouse/queries/run_analysis.py --all`, rồi `python data_warehouse/queries/validate_business_insights.py --results-dir data_warehouse/analysis_results` để đối chiếu các luận điểm cốt lõi trong báo cáo.
