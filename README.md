# ViX-Ray Annotation Workspace 🩻

Hệ thống trực quan hóa dữ liệu và gán nhãn không gian (Spatial Bounding Box Annotation) cho bộ dữ liệu ảnh X-quang ngực **ViX-Ray** (5.400 ảnh) phục vụ nghiên cứu mô hình thị giác - ngôn ngữ (VLM).

---

## 🌟 Tính năng chính

1. **Tổng quan (Overview & Clinical Analytics)**:
   - Thống kê toàn diện 5.400 ca bệnh ViX-Ray, số lượng Reference Finding, trạng thái gán nhãn.
   - Biểu đồ phân bố theo tập dữ liệu (`train`, `val`, `test`), hướng chụp, độ tuổi, giới tính và file nguồn.
   - **Phân tích bệnh lý lâm sàng chuẩn hóa từ cột Kết luận (`impressions`)**:
     - Bộ lọc phủ định và bình thường bao quát 100%, bảo toàn các tính từ hình thái dương tính (`không đều`, `không đồng nhất`, `mất cân đối`).
     - Hệ thống phân loại 2 tầng theo **4 Hệ cơ quan giải phẫu chuẩn** và **13 nhóm bệnh lý**.
     - Biểu đồ A: Số lượng ca & Xác suất hiện mắc $P(\text{Bệnh})$ theo 4 hệ cơ quan.
     - Biểu đồ B: Top 8 cặp bệnh lý đồng mắc phổ biến nhất — $P(A \cap B)$.
     - Biểu đồ C: Biến thiên xác suất 5 bệnh lý phổ biến theo 4 nhóm tuổi ($<50$, $50–64$, $65–74$, $\ge 75$).
     - Biểu đồ D: Phân phối số lượng bệnh lý đồng mắc trên mỗi phim X-quang.
     - Bảng thống kê chi tiết xác suất hiện mắc theo giới tính và độ tuổi trung bình.
2. **Danh sách gán nhãn (Reference Findings Table)**:
   - Bảng tổng hợp 5.400 ca bệnh với tính năng tìm kiếm đa trường và bộ lọc đa tầng.
   - Nhấp vào bất kỳ dòng nào để chuyển ngay sang chế độ gán nhãn chi tiết cho ca bệnh đó.
3. **Chi tiết ca bệnh & Không gian gán nhãn (Case Viewer & Studio)**:
   - Xem ảnh X-quang độ phân giải cao kết hợp ngữ cảnh lâm sàng (Mô tả hình ảnh & Kết luận chẩn đoán).
   - Mở ảnh toàn màn hình trên tab mới chỉ với một cú nhấp chuột.
   - Bảng màu viền phân biệt độ tương phản cao với nét vẽ chuẩn y khoa (độ dày 1px).
   - Thanh công cụ vẽ tương tác hỗ trợ hoàn tác, xóa và phím tắt `Ctrl + Z`.
   - Sinh mã định danh Reference Finding phân cấp tự động theo từng ca bệnh (`<Mã ảnh>-RF<Số thứ tự>`).
4. **Lưu trữ đồng bộ hai chiều (Dual Backend)**:
   - Tích hợp trực tiếp Google Sheets API với xác thực Service Account.
   - Tự động lưu bản sao dự phòng cục bộ (Parquet & CSV) để hoạt động ngoại tuyến khi cần thiết.

---

## 📁 Cấu trúc dự án

```
vixray-workspace/
├── app.py                      # Điểm khởi chạy ứng dụng Streamlit
├── requirements.txt            # Thư viện phụ thuộc
├── README.md                   # Tài liệu hướng dẫn
├── .gitignore
├── .streamlit/
│   └── secrets.toml            # Cấu hình Google Sheets & Service Account
├── src/
│   ├── __init__.py
│   ├── bbox.py                 # Xử lý tọa độ, chuyển đổi tỉ lệ và vẽ khung định vị
│   ├── charts.py               # Biểu đồ Plotly trực quan hóa dữ liệu và bệnh lý
│   ├── config.py               # Hằng số cấu hình, danh mục trạng thái và đường dẫn
│   ├── data.py                 # Nạp dữ liệu Master/Annotations và tải ảnh từ Google Drive
│   ├── filters.py              # Xử lý logic lọc dữ liệu toàn cục
│   ├── models.py               # Dataclass định nghĩa cấu trúc dữ liệu
│   ├── patch.py                # Tương thích ngược Streamlit cho thư viện vẽ canvas
│   ├── pathology.py            # Xử lý ngôn ngữ lâm sàng, trích xuất 13 bệnh lý & 4 hệ cơ quan
│   ├── storage.py              # Quản lý kết nối Google Sheets và lưu trữ cục bộ
│   ├── ui.py                   # Cấu hình theme, CSS và thanh bên bộ lọc
│   └── views/
│       ├── __init__.py
│       ├── overview.py         # Màn hình 1: Tổng quan, biểu đồ tiến độ & phân tích bệnh lý
│       ├── reference_findings.py # Màn hình 2: Bảng tra cứu và quản lý 5.400 ca bệnh
│       └── case_viewer.py      # Màn hình 3: Chi tiết ca bệnh và không gian gán nhãn
└── storage/
    ├── annotations.csv         # Bản lưu dữ liệu gán nhãn cục bộ
    └── master.parquet          # Bản lưu 5.400 ca bệnh gốc
```

---

## 🚀 Hướng dẫn cài đặt và khởi chạy

### 1. Cài đặt môi trường
```bash
pip install -r requirements.txt
```

### 2. Cấu hình Google Sheets
Thiết lập file `.streamlit/secrets.toml`:
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

### 3. Khởi chạy ứng dụng
```bash
streamlit run app.py
```
