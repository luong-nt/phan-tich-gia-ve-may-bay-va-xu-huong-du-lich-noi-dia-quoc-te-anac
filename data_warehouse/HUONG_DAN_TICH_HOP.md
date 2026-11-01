# TÍCH HỢP BÁO CÁO BƯỚC 4 VÀO ANAC PORTFOLIO

1. Sao chép thư mục `docs/` vào `project/docs/` (hoặc đặt riêng báo cáo Markdown vào `project/docs`).
2. Sao chép `data_warehouse/queries/verify_analysis_results.py` vào thư mục cùng tên trong `project`.
3. Giữ nguyên 17 file `data_warehouse/analysis_results/Q01.csv` ... `Q17.csv` đã tạo trên máy. **Không cần thay `analysis.sql` hoặc sửa DuckDB.**
4. Từ Terminal ở thư mục `project`, chạy:

```powershell
python data_warehouse/queries/verify_analysis_results.py --results-dir data_warehouse/analysis_results
```

Kết quả đã chạy trên bộ ZIP bạn gửi: **20 PASS, 0 FAIL**. Nếu kết quả khác, gửi lại các dòng `FAIL` để kiểm tra.

Bước 4 đã có SQL, kết quả CSV, bản báo cáo và kiểm tra đối chiếu. Trước khi chốt nghiệm thu, nên mở ngẫu nhiên 1–2 báo cáo tuyến Q09/Q10 để giải thích kết quả bằng ngôn ngữ nghiệp vụ và xác nhận định dạng tiếng Việt hiển thị chính xác.

Về sau, nếu dữ liệu ANAC thay đổi theo lịch, hãy chạy lại 17 SQL rồi mới cập nhật báo cáo hoặc dashboard; báo cáo Markdown là **ảnh chụp số liệu** chứ không tự đổi theo dữ liệu mới.
