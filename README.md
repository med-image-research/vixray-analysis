# ViX-Ray Annotation Workspace

Hệ thống trực quan hóa dữ liệu và gán nhãn bounding box cho bộ dữ liệu 5.400 ảnh X-quang ngực **ViX-Ray**, phục vụ nghiên cứu VLM trong y tế.

---

## Ứng dụng dùng để làm gì?

- **Khoanh vùng tổn thương**: Dùng chuột vẽ khung trực tiếp trên ảnh X-quang để đánh dấu các vùng bệnh lý.
- **Tra cứu ca bệnh**: Xem chi tiết 5.400 ca chụp, tìm kiếm nhanh và lọc theo độ tuổi, giới tính, hướng chụp.
- **Thống kê bệnh lý**: Xem biểu đồ các bệnh thường gặp, các cặp bệnh hay đi chung với nhau và xu hướng theo từng độ tuổi.
- **Lưu trữ trực tuyến**: Tự động lưu kết quả gán nhãn lên Google Sheets ngay tức thì, giúp nhiều người cùng làm việc và không lo mất dữ liệu.

---

## Hướng dẫn cài đặt & Khởi chạy (Bash)

Mở terminal Bash (Git Bash trên Windows hoặc Terminal trên Linux/macOS) tại thư mục dự án:

### 1. Tạo và kích hoạt môi trường ảo

```bash
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường:
# Trên Windows (Git Bash):
source .venv/Scripts/activate

# Trên Linux / macOS:
# source .venv/bin/activate
```

### 2. Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### 3. Cấu hình kết nối Google Sheets (Tùy chọn)

Nếu muốn lưu dữ liệu gán nhãn lên Google Sheets, tạo file `.streamlit/secrets.toml`:

```toml
[google_sheets]
master_sheet_id = "YOUR_MASTER_SPREADSHEET_ID"
annotation_sheet_id = "YOUR_ANNOTATION_SPREADSHEET_ID"

[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "YOUR_SERVICE_ACCOUNT_EMAIL"
client_id = "YOUR_CLIENT_ID"
token_uri = "https://oauth2.googleapis.com/token"
```

*(Nếu chưa cấu hình secrets, ứng dụng vẫn xem được dữ liệu bình thường bằng file có sẵn).*

### 4. Chạy ứng dụng

```bash
streamlit run app.py
```

Mở trình duyệt truy cập: `http://localhost:8501`
