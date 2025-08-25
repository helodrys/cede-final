from playwright.sync_api import sync_playwright
import time, os
from datetime import datetime

TARGET_URL = "https://shopee.co.th/POP-MART-CRYBABY-Wild-but-Cutie-Series-Vinyl-Plush-Pendant-Blind-Box(whole-set%EF%BC%89-i.569947420.41251000830"   # ✅ ลิงก์หน้าสินค้า (เปลี่ยนตามต้องการ)
TARGET_TIME = "09:39:00"
QUANTITY = 1                                    
SESSION_FILE = "shopee_session.json"             

def wait_until(target_time):
    """รอจนถึงเวลาที่กำหนด"""
    print(f"⏰ รอจนถึง {target_time}")
    while True:
        now = time.strftime("%H:%M:%S")
        if now >= target_time:
            print(f"\n🚀 ถึงเวลาแล้ว! เริ่มทำงาน...")
            break
        print(f"🕒 รอ {target_time} | ตอนนี้ {now}", end="\r")
        time.sleep(0.1)

def click_with_retry(page, selector, timeout=5000, description=""):
    """คลิกด้วยการลองซ้ำหลายครั้ง"""
    selectors = [
        selector,
        f"button:has-text('{selector}')",
        f"[data-testid*='{selector}']",
        f".{selector}",
        f"#{selector}"
    ]
    
    for sel in selectors:
        try:
            print(f"🔍 หา {description}: {sel}")
            page.wait_for_selector(sel, timeout=timeout)
            page.click(sel)
            print(f"✅ คลิก {description} สำเร็จ")
            return True
        except Exception as e:
            print(f"❌ ไม่พบ {sel}: {str(e)[:50]}")
            continue
    return False

with sync_playwright() as p:
    try:
        print("🌐 เปิด Microsoft Edge...")

        browser = p.chromium.launch(
            channel="msedge", 
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        if os.path.exists(SESSION_FILE):
            print("🔐 โหลด session ที่เคย login แล้ว...")
            context = browser.new_context(storage_state=SESSION_FILE)
        else:
            print("🔑 ยังไม่มี session กรุณา login ด้วยตนเอง...")
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://shopee.co.th/buyer/login")
            print("⏳ กรุณา login ด้วยตนเอง แล้วกด Enter ต่อ...")
            input("👉 กด Enter เมื่อ login เสร็จสมบูรณ์...")
            try:
                page.wait_for_url("**/shopee.co.th/**", timeout=10000)
                context.storage_state(path=SESSION_FILE)
                print("✅ บันทึก session เรียบร้อย")
            except:
                print("❌ Login ไม่สำเร็จ กรุณาลองใหม่")
                browser.close()
                exit()
        page = context.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        })
        
        print(f"📄 เข้าสู่หน้าสินค้า: {TARGET_URL}")
        page.goto(TARGET_URL)
        print("⏳ รอหน้าเว็บโหลด...")
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        wait_until(TARGET_TIME)
        print(f"🧮 กำหนดจำนวนสินค้า: {QUANTITY}")
        quantity_selectors = [
            'input[type="number"]',
            'input.shopee-input-quantity',
            'input[data-testid*="quantity"]',
            '.quantity-input input',
            '[class*="quantity"] input'
        ]
        quantity_set = False
        for selector in quantity_selectors:
            try:
                if page.is_visible(selector):
                    page.click(selector)
                    page.keyboard.press('Control+a')
                    page.type(selector, str(QUANTITY))
                    print(f"✅ ตั้งจำนวน {QUANTITY} สำเร็จ")
                    quantity_set = True
                    break
            except:
                continue

        if not quantity_set:
            print("⚠️ ไม่พบช่องจำนวนสินค้า ใช้จำนวนเริ่มต้น")
        time.sleep(0.5)
        print("🛒 คลิกปุ่ม 'เพิ่มไปยังรถเข็น'...")
        cart_selectors = [
            "button:has-text('เพิ่มไปยังรถเข็น')",
            "button:has-text('Add to Cart')",
            "[data-testid*='add-to-cart']",
            "button[class*='add-to-cart']",
            ".btn-solid-primary:has-text('เพิ่ม')",
            "button:has-text('เพิ่มลงตะกร้า')"
        ]     
        cart_clicked = False
        for selector in cart_selectors:
            try:
                if page.is_visible(selector):
                    page.click(selector)
                    print("✅ คลิกเพิ่มไปยังรถเข็นสำเร็จ")
                    
                    cart_clicked = True
                    break
            except Exception as e:
                print(f"❌ ไม่สำเร็จ {selector}: {str(e)[:50]}")
                continue

        if not cart_clicked:
            print("❌ ไม่พบปุ่มเพิ่มไปยังรถเข็น")
            
        time.sleep(2)
        print("🔍 ตรวจสอบ popup ยืนยัน...")
        confirm_selectors = [
            "button:has-text('ตกลง')",
            "button:has-text('OK')",
            "button:has-text('Confirm')",
            ".shopee-button--primary:has-text('ตกลง')",
            "[data-testid*='confirm']"
        ]     
        for selector in confirm_selectors:
            try:
                if page.is_visible(selector, timeout=3000):
                    page.click(selector)
                    print("👍 คลิกตกลงเรียบร้อย")
                    break
            except:
                continue
        else:
            print("ℹ️ ไม่มี popup ยืนยัน")
        time.sleep(2)
        try:
            if page.is_visible(".shopee-toast__text"):
                toast_text = page.text_content(".shopee-toast__text")
                print(f"📝 ข้อความแจ้งเตือน: {toast_text}")
        except:
            pass
        print("🎉 เสร็จสิ้นกระบวนการ!")
        print("🛒 ตรวจสอบรถเข็นของคุณได้ที่: https://shopee.co.th/cart")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
    finally:
        print("⏳ รอ 10 วินาที ก่อนปิดโปรแกรม...")
        time.sleep(10)
        try:
            browser.close()
        except:
            pass

print("👋 โปรแกรมจบการทำงาน")