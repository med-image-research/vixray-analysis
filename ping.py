import os
import time
from playwright.sync_api import sync_playwright  # pyright: ignore[reportMissingImports]

STREAMLIT_URL = os.environ.get("STREAMLIT_URL")

def keep_alive():
    with sync_playwright() as p:
        print("Đang khởi động trình duyệt Chromium...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Đang truy cập {STREAMLIT_URL}...")
        page.goto(STREAMLIT_URL, wait_until="networkidle", timeout=60000)

        time.sleep(5)

        page.click("body", force=True)
        print("Ping thành công! Đã tải và tương tác với trang.")

        browser.close()


if __name__ == "__main__":
    keep_alive()
