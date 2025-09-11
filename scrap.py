from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
import time
import os

SESSION_FILE = "watsons_session.json"
URL = "https://www.watsons.co.th/th/spectraban-%E0%B8%AA%E0%B9%80%E0%B8%9B%E0%B8%84%E0%B8%95%E0%B8%A3%E0%B9%89%E0%B8%B2%E0%B9%81%E0%B8%9A%E0%B8%99-%E0%B9%80%E0%B8%AD%E0%B8%AA%E0%B8%9E%E0%B8%B5%E0%B9%80%E0%B8%AD%E0%B8%9F-50-100-%E0%B8%81%E0%B8%A3%E0%B8%B1%E0%B8%A1/p/BP_139729"
OUTPUT_JSON = "product_data.json"
PRODUCT_CODE = "WTCTH-139729"

def save_to_json(obj):
    """Save the object to JSON file."""
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)
    print(f"✅ Saved data to {OUTPUT_JSON}")

def extract_product_details(page, url, obj):
    """Extract details from a product page and add to obj."""
    print(f"📄 Navigating to: {url}")
    page.goto(url)
    print("⏳ Waiting for page content to load...")
    page.wait_for_load_state('domcontentloaded', timeout=15000)
    time.sleep(2)  # Brief delay for JavaScript rendering
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # Extract images and name (filter for product code)
    images = []
    name = ''
    for media in soup.find_all('e2-media'):
        img = media.find('img')
        if img:
            src = img.get('src', '')
            if PRODUCT_CODE in src:
                images.append(src)
                if not name:
                    name = img.get('alt', '')

    unique_images = list(set(images))
    num_images = len(unique_images)
    if num_images >= 3:  # Keep if 3 or more; adjust threshold as needed
        image_value = unique_images
    else:
        image_value = unique_images[0] if unique_images else ''  # Fallback to single or empty

    # Extract description text
    description = ''
    for div in soup.find_all('div', class_=re.compile(r'content ng-tns-c\d+-\d+')):
        description += div.text.strip() + '\n'
    for div in soup.find_all('div', class_=re.compile(r'ng-tns-c\d+-\d+ ng-star-inserted')):
        description += div.text.strip() + '\n'

    description = re.sub(r'\s+', ' ', description).strip()

    # Split into sections using regex for keywords
    # Split on 'วิธีการใช้งาน' and 'ส่วนประกอบ'
    parts = re.split(r'(วิธีการใช้งาน|ส่วนประกอบ)', description, flags=re.IGNORECASE)

    # Reassemble sections
    desc_parts = []
    using = ''
    ingredient_text = ''
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if part.lower() == 'วิธีการใช้งาน':
            if i + 1 < len(parts):
                using = parts[i + 1].strip()
                i += 2
                continue
        elif part.lower() == 'ส่วนประกอบ':
            if i + 1 < len(parts):
                ingredient_text = parts[i + 1].strip()
                i += 2
                continue
        else:
            desc_parts.append(part)
            i += 1

    full_description = ' '.join(desc_parts).strip()

    # Parse ingredients: split by comma, filter non-ingredient text (e.g., start with English capital or contain chemical terms)
    ingredients = []
    if ingredient_text:
        raw_ings = [i.strip() for i in re.split(r',|\n|;', ingredient_text) if i.strip()]
        for ing in raw_ings:
            # Filter: starts with capital letter (English chemical names), ignore Thai or other text
            if re.match(r'^[A-Z0-9]', ing):
                # Remove trailing Thai text if present
                ing = re.sub(r' [ป-ฮ].*$', '', ing).strip()
                ingredients.append(ing)

    # Map ingredients
    ingredient_map = {ing['name'].lower(): ing['id'] for ing in obj['ingredient']}
    next_ing_id = max(ing['id'] for ing in obj['ingredient']) + 1 if obj['ingredient'] else 1
    ingredient_ids = []

    for ing in ingredients:
        ing_lower = ing.lower()
        if ing_lower in ingredient_map:
            ingredient_ids.append(ingredient_map[ing_lower])
        else:
            new_ing = {'id': next_ing_id, 'name': ing, 'allergic': False, 'allergic-relation': None}
            obj['ingredient'].append(new_ing)
            ingredient_map[ing_lower] = next_ing_id
            ingredient_ids.append(next_ing_id)
            next_ing_id += 1

    # Add new product (no price)
    next_prod_id = max(prod['id'] for prod in obj['product']) + 1 if obj['product'] else 1
    new_product = {
        'id': next_prod_id,
        'name': name,
        'description': full_description,
        'using': using,
        'image': image_value,
        'ingredient': ingredient_ids,
        'category': 1,  # Hardcoded to sunscreen category
        'link': url
    }

    obj['product'].append(new_product)
    print(f"✅ Added product: {name}")

with sync_playwright() as p:
    try:
        print("🌐 Opening Microsoft Edge...")
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,  # Set to True for background running
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )

        # Load or create session
        if os.path.exists(SESSION_FILE):
            print("🔐 Loading saved session...")
            context = browser.new_context(storage_state=SESSION_FILE)
        else:
            print("🔑 No session found. Creating new session with manual login...")
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.watsons.co.th/th/login")
            print("⏳ Please log in manually in the browser window...")
            print("👉 After successful login, press Enter here to continue and save the session...")
            input()  # Wait for user input after manual login
            try:
                # Verify we're on the main site after login
                page.wait_for_url("**/watsons.co.th/**", timeout=10000)
                context.storage_state(path=SESSION_FILE)
                print(f"✅ Session saved to {SESSION_FILE}")
            except Exception as e:
                print(f"❌ Login verification failed: {e}. Please try again.")
                browser.close()
                exit()

        # Set up new page and headers
        page = context.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        })

        # Initialize obj
        obj = {
            'user': [{'id': 1, 'allergic': [3]}],
            'ingredient': [
                {'id': 1, 'name': 'water', 'allergic': False, 'allergic-relation': None},
                {'id': 2, 'name': 'acid', 'allergic': True, 'allergic-relation': [3]},
                {'id': 3, 'name': 'perfume', 'allergic': True, 'allergic-relation': [2, 4]},
                {'id': 4, 'name': 'niacinamind', 'allergic': False, 'allergic-relation': None}
            ],
            'category': [
                {'id': 1, 'name': 'ครีมกันแดด'},
                {'id': 2, 'name': 'โฟมล้างหน้า'},
                {'id': 3, 'name': 'สบู่'}
            ],
            'product': [
                {'id': 1, 'name': 'Cerave Moisturizing 15 ml', 'description': 'xxxxxxx', 'using': 'xxxxxx', 'image': 'link', 'ingredient': [1, 3], 'price': 340, 'category': 1, 'link': 'www.....'},
                {'id': 2, 'name': 'Hongthai 15 ml', 'description': 'xxxxxxx', 'using': 'xxxxxx', 'image': 'link', 'ingredient': [4, 6], 'price': 200, 'category': 2, 'link': 'www.....'}
            ]
        }

        # Scrape the single product page
        extract_product_details(page, URL, obj)

        # Save to JSON
        save_to_json(obj)
        print("🎉 Processed product page!")

    except Exception as e:
        print(f"❌ Error: {e}")
        if "Executable doesn't exist" in str(e):
            print("Please run 'playwright install' to install required browser binaries.")
    finally:
        print("⏳ Waiting 5 seconds before closing...")
        time.sleep(5)
        try:
            browser.close()
        except:
            pass

print("👋 Program finished.")