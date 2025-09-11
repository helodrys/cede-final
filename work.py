import requests
from bs4 import BeautifulSoup

URL = "https://www.watsons.co.th/th/spectraban-%E0%B8%AA%E0%B9%80%E0%B8%9B%E0%B8%84%E0%B8%95%E0%B8%A3%E0%B9%89%E0%B8%B2%E0%B9%81%E0%B8%9A%E0%B8%99-%E0%B9%80%E0%B8%AD%E0%B8%AA%E0%B8%9E%E0%B8%B5%E0%B9%80%E0%B8%AD%E0%B8%9F-50-100-%E0%B8%81%E0%B8%A3%E0%B8%B1%E0%B8%A1/p/BP_139729"

# สร้าง session เก็บ cookies
session = requests.Session()

# header ให้เหมือน browser จริง
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
})

# ถ้าคุณรู้ session_id หรือ token จาก DevTools, ใส่ cookie ตรงนี้
session.cookies.set("session_id", "YOUR_SESSION_ID_HERE")

# โหลดหน้า
resp = session.get(URL, timeout=20)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "lxml")

# เลือก element ด้วย class
els = soup.select(".ng-tns-c2652604631-1.ng-star-inserted")

print(f"Found {len(els)} elements")
for i, el in enumerate(els, 1):
    print(f"--- Element {i} ---")
    print(el.get_text(strip=True))
