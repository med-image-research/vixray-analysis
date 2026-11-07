import os
import time
from playwright.sync_api import sync_playwright

# Thay bằng URL ứng dụng Streamlit của bạn hoặc cấu hình qua GitHub Secret STREAMLIT_URL
STREAMLIT_URL = os.environ.get("STREAMLIT_URL") or "https://ten-ung-dung.streamlit.app"


def keep_alive():
    with sync_playwright() as p:
        print("Đang khởi động trình duyệt Chromium...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Đang truy cập {STREAMLIT_URL}...")
        # Chờ cho đến khi mạng rảnh rỗi (trang đã tải xong JS/WebSocket)
        page.goto(STREAMLIT_URL, wait_until="networkidle", timeout=60000)

        # Đợi thêm 5 giây để Streamlit hoàn tất render UI
        time.sleep(5)

        # Click một vị trí bất kỳ (body) để giả lập tương tác người dùng
        page.click("body", force=True)
        print("Ping thành công! Đã tải và tương tác với trang.")

        browser.close()


if __name__ == "__main__":
    keep_alive()
