from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
import time
import os
import csv

SESSION_FILE = "watsons_session.json"
OUTPUT_JSON = "product_data_recursive.json"

def save_to_json(obj):
    """Save the object to JSON file."""
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)
    print(f"✅ Saved data to {OUTPUT_JSON}")

def extract_bp_number(url):
    """Extract BP_xxxxxx number from URL."""
    match = re.search(r'/p/BP_(\d+)', url)
    return match.group(1) if match else None

def map_category(type_name):
    """Map CSV Types to category ID."""
    category_map = {
        "Sunscreen": 1,  # ครีมกันแดด
        "facial cleansing foam": 2,  # โฟมล้างหน้า
        "Soap": 3,  # สบู่
        "Shampoo": 4,  # แชมพู
        "Body cream": 5  # ครีมบำรุงผิวกาย
    }
    return category_map.get(type_name, 1)  # Default to Sunscreen if unknown

def extract_product_details(page, url, product_code, category_id, obj):
    """Extract details from a product page and add to obj."""
    print(f"📄 Navigating to: {url}")
    try:
        page.goto(url, timeout=30000)
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
                if product_code in src:
                    images.append(src)
                    if not name:
                        name = img.get('alt', '')

        unique_images = list(set(images))
        num_images = len(unique_images)
        if num_images >= 3:  # Keep if 3 or more
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

        # Parse ingredients
        ingredients = []
        if ingredient_text:
            raw_ings = [i.strip() for i in re.split(r',|\n|;', ingredient_text) if i.strip()]
            for ing in raw_ings:
                if re.match(r'^[A-Z0-9]', ing):
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

        # Add new product
        next_prod_id = max(prod['id'] for prod in obj['product']) + 1 if obj['product'] else 1
        new_product = {
            'id': next_prod_id,
            'name': name,
            'description': full_description,
            'using': using,
            'image': image_value,
            'ingredient': ingredient_ids,
            'category': category_id,
            'link': url
        }

        obj['product'].append(new_product)
        print(f"✅ Added product: {name}")
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")

def main():
    # Read CSV
    products = []
    with open('final_test.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({'URL': row['URL'].strip(), 'Types': row['Types'].strip()})

    # Track BP numbers to handle duplicates
    bp_numbers_seen = {}
    duplicates = []

    # Initialize JSON object
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
            {'id': 3, 'name': 'สบู่'},
            {'id': 4, 'name': 'แชมพู'},
            {'id': 5, 'name': 'ครีมบำรุงผิวกาย'}
        ],
        'product': []
    }

    with sync_playwright() as p:
        try:
            print("🌐 Opening Microsoft Edge...")
            browser = p.chromium.launch(
                channel="msedge",
                headless=False,
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
                input()
                try:
                    page.wait_for_url("**/watsons.co.th/**", timeout=10000)
                    context.storage_state(path=SESSION_FILE)
                    print(f"✅ Session saved to {SESSION_FILE}")
                except Exception as e:
                    print(f"❌ Login verification failed: {e}. Please try again.")
                    browser.close()
                    exit()

            # Set up new page
            page = context.new_page()
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            })

            # Process each product
            for product in products:
                url = product['URL']
                type_name = product['Types']
                bp_number = extract_bp_number(url)
                if not bp_number:
                    print(f"❌ No BP number found in URL: {url}")
                    continue

                product_code = f"WTCTH-{bp_number}"
                if bp_number in bp_numbers_seen:
                    duplicates.append({'bp_number': bp_number, 'url': url, 'existing_url': bp_numbers_seen[bp_number]})
                    print(f"⚠️ Duplicate BP number {bp_number} found for URL: {url}")
                    continue

                bp_numbers_seen[bp_number] = url
                category_id = map_category(type_name)
                extract_product_details(page, url, product_code, category_id, obj)

            # Save to JSON
            save_to_json(obj)
            print("🎉 Processed all product pages!")

            # Log duplicates
            if duplicates:
                print("⚠️ Duplicates found:")
                for dup in duplicates:
                    print(f"BP_{dup['bp_number']}: {dup['url']} (already processed as {dup['existing_url']})")

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

if __name__ == "__main__":
    main()