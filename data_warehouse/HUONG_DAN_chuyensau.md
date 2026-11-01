# Gắn Business Insights vào ANAC Portfolio

Bộ này được lập từ **17 file kết quả phân tích CSV của bạn**, không thay đổi Data Warehouse hay ETL.

## Vị trí file

```
project/
├─ docs/
│  ├─ BAO_CAO_BUSINESS_INSIGHTS_ANAC.md      # Mới; đọc và trích làm Portfolio
│  └─ BANG_DAN_CHUNG_INSIGHTS.csv            # Mới; dấu vết số liệu
└─ data_warehouse/
   └─ queries/
      ├─ analysis.sql                        # Cũ; giữ nguyên
      ├─ run_analysis.py                     # Cũ; giữ nguyên
      └─ validate_business_insights.py       # Mới; đối chiếu nội dung báo cáo
```

Giải nén ZIP và chép các file vào đúng thư mục trên. Không xóa các báo cáo Bước 4 đã có; báo cáo mới **bổ sung phần kết luận có ý nghĩa**, không thay thế các truy vấn SQL.

Tại Terminal PowerShell ở thư mục `project`, chạy:

```powershell
python data_warehouse/queries/validate_business_insights.py --results-dir data_warehouse/analysis_results
```

Nếu muốn tái tạo kết quả trước khi kiểm tra:

```powershell
python data_warehouse/queries/run_analysis.py --all
python data_warehouse/queries/validate_business_insights.py --results-dir data_warehouse/analysis_results
```

> Báo cáo phản ánh dữ liệu trong bản snapshot 17 CSV đã gửi, tới 09/2026. Khi ETL bổ sung tháng mới, hãy chạy lại các truy vấn và cập nhật insight; không mặc định các kết luận về năm sau vẫn đúng.

**Định nghĩa:** THANG là tháng tham chiếu bán vé, không phải tháng khởi hành; ASSENTOS là ghế bán; BRL và USD phân tích tách biệt. Phân tích tương quan hoặc bất thường không đủ chứng minh quan hệ nhân quả.
