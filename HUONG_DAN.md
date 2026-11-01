# ANAC Aviation Analytics – cập nhật dữ liệu nhiều năm

## Phạm vi

- Giữ nguyên 4 CSV **2024** đang có trong GitHub. **Không xoá** thư mục `DuLieu_DaXuLy`.
- Mỗi ngày, GitHub Actions kiểm tra danh sách file được công bố trong thư mục ANAC:
  - Nội địa: `https://sas.anac.gov.br/sas/tarifadomestica/YYYY/YYYYMM.csv`
  - Quốc tế: `https://sas.anac.gov.br/sas/tarifainternacional/YYYY/Internacional_YYYY-MM.csv`
- Bắt đầu quét năm 2025, tự mở rộng theo năm hiện tại. Khi nguồn mới có thể tải và phân tích hợp lệ, lưu bảng ETL gọn trong `DuLieu_DaXuLy/_tu_dong/parts/` rồi cập nhật 4 CSV tổng hợp. Bốn tệp CSV vẫn giữ tên `*_2024.csv` để **tương thích ngược** với dashboard cũ, nhưng sau lần ETL mới chúng chứa **nhiều năm**.
- Cập nhật các tháng mới không làm xoá kết quả 2024. Trước cập nhật đầu tiên, chương trình lưu ảnh chụp dữ liệu gốc 2024 vào `_tu_dong/baseline_2024/`.

## Bước triển khai lên repository cũ

1. Trước khi thay bất kỳ file nào, giữ bản sao của `dashboard.py` đang chạy để có thể phục hồi.
2. Ở thư mục gốc repository trên GitHub, cập nhật các tệp này bằng nội dung phiên bản mới:
   - `dashboard.py`
   - `cap_nhat_anac.py`
   - `nguon_anac.json`
   - `requirements.txt`
   - `.gitignore`
   - `tests/test_etl.py`
   - `.github/workflows/cap-nhat-du-lieu.yml`
3. **Đừng xoá** các thư mục `DuLieu_DaXuLy/`, `assets/`, hoặc bốn CSV 2024 hiện có. File ZIP không chứa CSV 2024 và không chứa logo của bạn.
4. Mở tab **Actions** trên GitHub, chọn **ANAC - ETL tu dong hang ngay** > **Run workflow** > chọn **check**. Xem kết quả và tệp CSV được phát hiện.
5. Nếu bước check xanh (thành công), chọn **Run workflow** > **update**. Theo dõi log. Nếu xuất hiện dữ liệu mới, chương trình tạo các bảng tổng hợp và tự commit.
6. Trang Streamlit Cloud sẽ đọc các tệp mới sau khi GitHub cập nhật. Dashboard có thêm bộ lọc **Năm phân tích** và phần "Lần ETL thành công". Một số lần cần chờ ứng dụng tự triển khai lại.

## Thử trực tiếp trên Windows trong VS Code

```powershell
pip install -r requirements.txt
python -m unittest discover -s tests -v
python cap_nhat_anac.py --check
python cap_nhat_anac.py
python -m streamlit run dashboard.py
```

**Quan trọng**: Các URL xây dựng theo mã nguồn flightsbr 1.2.0 (Ipea, Brazil). Trong môi trường tạo gói này, máy chủ ANAC không thể truy cập trực tiếp nên **chưa xác nhận tải trực tiếp với file ANAC thực tế**. Không coi trạng thái "đã có mã" là "đã cập nhật thành công". Cần chạy bước **check** trên GitHub hoặc máy bạn rồi đọc log.

ANAC có thay đổi quy định ghi nhận giá vé nội địa từ 01/02/2026, nên các bản ghi thiếu cấu trúc dự kiến bị từ chối, không âm thầm điền số giả. Phạm vi hai nhóm thị trường có thể khác nhau và tổng ghế không tương đương toàn bộ khách du lịch.

Các file Top 100 của năm 2024 không chứa tất cả tuyến 2024. Các năm mới được tổng hợp từ các tháng tải thành công; khi xem tất cả các năm, Top tuyến chỉ dựa vào các tuyến hiện có trong các bảng tóm tắt theo năm.

Nguồn:
- https://github.com/ipea/flightsbr/blob/main/R/utils_airfares.R
- https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/tarifas-aereas-domesticas/46-tarifas-aereas-domesticas
- https://www.anac.gov.br/assuntos/legislacao/legislacao-1/portarias/2025/portaria-18340
