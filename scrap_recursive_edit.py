from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
import time
import os
import csv

SESSION_FILE = "watsons_session.json"
INPUT_JSON = "product_data_recursivefilter.json"
OUTPUT_JSON = "product_data_recursivefilter_copy.json"

def save_to_json(obj):
    """Save the object to JSON file."""
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)
    print(f"✅ Saved data to {OUTPUT_JSON}")

def load_json():
    """Load the existing JSON file."""
    if not os.path.exists(INPUT_JSON):
        print(f"❌ Input JSON file {INPUT_JSON} not found.")
        return None
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)
    print(f"✅ Loaded data from {INPUT_JSON}")

def extract_bp_number(url):
    """Extract BP_xxxxxx number from URL."""
    match = re.search(r'/p/BP_(\d+)', url)
    return match.group(1) if match else None

def extract_product_images(page, url, product_code):
    """Extract image URLs from a product page."""
    print(f"📄 Navigating to: {url}")
    try:
        page.goto(url, timeout=30000)
        print("⏳ Waiting for page content to load...")
        page.wait_for_load_state('domcontentloaded', timeout=15000)
        time.sleep(2)  # Brief delay for JavaScript rendering
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Extract images from the specified class
        images = []
        for div in soup.find_all('div', class_=re.compile(r'ng-tns-c2042697079-0.ng-star-inserted.is-initialized')):
            img = div.find('img')
            if img:
                src = img.get('src', '')
                if product_code in src:
                    images.append(src)

        unique_images = list(set(images))
        num_images = len(unique_images)
        if num_images >= 3:  # Keep if 3 or more
            image_value = unique_images
        else:
            image_value = unique_images[0] if unique_images else ''  # Fallback to single or empty

        return image_value
    except Exception as e:
        print(f"❌ Error scraping images from {url}: {e}")
        return ''

def main():
    # Load existing JSON
    obj = load_json()
    if not obj:
        print("❌ Exiting due to missing input JSON.")
        return

    # Read CSV
    products = []
    with open('final_test.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({'URL': row['URL'].strip(), 'Types': row['Types'].strip()})

    # Track BP numbers to handle duplicates
    bp_numbers_seen = {}
    duplicates = []

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

            # Process each product for image updates
            for product in products:
                url = product['URL']
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
                # Scrape images
                image_value = extract_product_images(page, url, product_code)

                # Update image field in JSON
                for prod in obj['product']:
                    if prod['link'] == url:
                        prod['image'] = image_value
                        print(f"✅ Updated image for product: {prod['name']}")
                        break
                else:
                    print(f"⚠️ No matching product found in JSON for URL: {url}")

            # Save updated JSON
            save_to_json(obj)
            print("🎉 Processed all product pages for image updates!")

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