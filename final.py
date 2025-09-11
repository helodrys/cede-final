import json
import re
import os
import time
from bs4 import BeautifulSoup
from datetime import datetime
from playwright.sync_api import sync_playwright

# Input and output files
INPUT_JSON = "updated_product_data.json"  # Previous output JSON
OUTPUT_JSON = "updated_product_data.json"
REPORT_FILE = "ingredient_report.txt"
DEBUG_DIR = "debug_html/"
SESSION_FILE = "watsons_session.json"

def split_ingredients(ingredient_text):
    """Split ingredient text by commas, preserving commas within parentheses."""
    ingredients = []
    current = []
    paren_count = 0
    for char in ingredient_text:
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        elif char == ',' and paren_count == 0:
            ingredients.append(''.join(current).strip())
            current = []
            continue
        current.append(char)
    if current:
        ingredients.append(''.join(current).strip())
    return [ing for ing in ingredients if ing]

def parse_ingredients_from_html(html_content, product_code, product_id, source="web"):
    """Parse ingredients from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialize ingredient text
    ingredient_text = ''
    
    # Try finding 'ส่วนประกอบ' or 'ส่วนผสม' in h4, h3, div, or span
    headers = soup.find_all(['h4', 'h3', 'div', 'span'], string=re.compile(r'ส่วนประกอบ|ส่วนผสม'))
    for header in headers:
        next_element = header.find_next(['p', 'div', 'span'], class_=re.compile(r'ng-tns-c\d+-\d+ ng-star-inserted|description|product-details'))
        if next_element:
            ingredient_text = next_element.get_text(strip=True)
            break
    
    # Fallback: Search for 'ส่วนประกอบ' or 'ส่วนผสม' in text and take the next element
    if not ingredient_text:
        sections = soup.find_all(string=re.compile(r'ส่วนประกอบ|ส่วนผสม'))
        for section in sections:
            parent = section.parent
            next_sibling = parent.find_next_sibling(['p', 'div', 'span'])
            if next_sibling:
                ingredient_text = next_sibling.get_text(strip=True)
                break
            if parent.get_text(strip=True) and re.match(r'^[A-Z0-9\s\(\)\-\.\/,]*$', parent.get_text(strip=True)):
                ingredient_text = parent.get_text(strip=True)
                break
    
    print(f"Raw ingredient text for {product_code} (ID: {product_id}) from {source}: {ingredient_text[:200]}...")
    
    if not ingredient_text:
        with open(REPORT_FILE, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            context = soup.find(string=re.compile(r'ส่วนประกอบ|ส่วนผสม'))
            context_html = str(context.parent)[:500] if context else "No ingredient section found"
            f.write(f"[{timestamp}] No ingredients found for product {product_code} (ID: {product_id}) from {source}. HTML context: {context_html}\n")
        print(f"❌ No ingredients found for {product_code} (ID: {product_id}) from {source}")
        return []
    
    # Normalize to uppercase and filter out Thai characters
    ingredient_text = ingredient_text.upper()
    if re.search(r'[ป-ฮ]', ingredient_text):
        ingredient_text = re.sub(r'[ป-ฮ]+', '', ingredient_text)
    
    # Split by commas first
    raw_ings = split_ingredients(ingredient_text)
    ingredients = []
    
    # For run-on text (no commas), split by space and group into chemical-like names
    for raw_ing in raw_ings:
        raw_ing = raw_ing.strip()
        if not raw_ing:
            continue
        if ',' in raw_ing:
            parts = [part.strip() for part in raw_ing.split(',') if part.strip()]
            for part in parts:
                word_count = len(re.split(r'\s+', part))
                if word_count <= 4:
                    ingredients.append(part)
                else:
                    words = re.split(r'\s+', part)
                    temp_group = []
                    for word in words:
                        temp_group.append(word)
                        if len(temp_group) >= 4 or re.search(r'(ACID|EXTRACT|ALCOHOL|POLYMER|BENZOATE|GLYCERIN|HYALURONATE|DIMETHYL|ETHYLHEXYL|TRIAZINE|PHENOL|DIMETHICONE|PEG|PPG|HYDROXY|CARBOMER|AMMONIUM|ACRYLATES|COPOLYMER|FRAGRANCE|PANTHENOL|ADENOSINE|EDTA|BUTYLENE|ALOE|CAMELLIA|SINENSIS|LEAF|HYDROLYZED|EXTENSIN|\d+,\d+-|BIS-|-OH|-YL|-IC|-ATE|-ONE|-INE|-ENE|-ANE|-OL|-ID|-IM|-AM|-UM|-ER)$', word.upper()):
                            ingredients.append(' '.join(temp_group))
                            temp_group = []
                    if temp_group:
                        ingredients.append(' '.join(temp_group))
        else:
            words = re.split(r'\s+', raw_ing)
            current_group = []
            for word in words:
                word = word.strip()
                if not word:
                    continue
                current_group.append(word)
                if len(current_group) >= 1 and len(current_group) <= 4:
                    if re.search(r'(ACID|EXTRACT|ALCOHOL|POLYMER|BENZOATE|GLYCERIN|HYALURONATE|DIMETHYL|ETHYLHEXYL|TRIAZINE|PHENOL|DIMETHICONE|PEG|PPG|HYDROXY|CARBOMER|AMMONIUM|ACRYLATES|COPOLYMER|FRAGRANCE|PANTHENOL|ADENOSINE|EDTA|BUTYLENE|ALOE|CAMELLIA|SINENSIS|LEAF|HYDROLYZED|EXTENSIN|\d+,\d+-|BIS-|-OH|-YL|-IC|-ATE|-ONE|-INE|-ENE|-ANE|-OL|-ID|-IM|-AM|-UM|-ER)$', word.upper()):
                        ingredients.append(' '.join(current_group))
                        current_group = []
                    elif re.match(r'^[A-Z0-9]+(?:-[A-Z0-9]+)?$', word):
                        continue
                    else:
                        ingredients.append(' '.join(current_group))
                        current_group = []
                else:
                    ingredients.append(' '.join(current_group))
                    current_group = []
            if current_group:
                ingredients.append(' '.join(current_group))
    
    # Filter English-only and ensure uniqueness
    unique_ingredients = []
    seen = set()
    for ing in ingredients:
        ing = ing.strip()
        if ing and re.match(r'^[A-Z0-9\s\(\)\-\.\/,]*$', ing) and not re.search(r'[ป-ฮ]', ing):
            word_count = len(re.split(r'\s+', ing))
            if word_count <= 4:
                ing_lower = ing.lower()
                if ing_lower not in seen:
                    seen.add(ing_lower)
                    unique_ingredients.append(ing)
    
    print(f"Parsed unique ingredients for {product_code} (ID: {product_id}) from {source}: {unique_ingredients}")
    return unique_ingredients

def scrape_ingredients_from_web(page, url, product_code, product_id):
    """Scrape ingredients from the Watsons website."""
    print(f"🌐 Navigating to {url} for product {product_code} (ID: {product_id})")
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state('domcontentloaded', timeout=15000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)  # Wait for dynamic content
        html = page.content()
        
        # Save HTML for debugging
        debug_file = os.path.join(DEBUG_DIR, f"debug_page_{product_code}_web.html")
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"📝 Saved web HTML to {debug_file}")
        
        return parse_ingredients_from_html(html, product_code, product_id, source="web")
    except Exception as e:
        with open(REPORT_FILE, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] Web scraping failed for product {product_code} (ID: {product_id}) at {url}: {str(e)}\n")
        print(f"❌ Web scraping failed for {product_code} (ID: {product_id}): {str(e)}")
        return []

def read_failed_products():
    """Read failed products from ingredient_report.txt."""
    failed_products = []
    if not os.path.exists(REPORT_FILE):
        print(f"❌ Report file {REPORT_FILE} not found.")
        return failed_products
    
    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        # Match lines like: "- https://.../p/BP_xxxxxx (ID: 2, Code: WTCTH-xxxxxx)"
        match = re.match(r'-\s*(https://[^\s]+)\s*\(ID:\s*(\d+),\s*Code:\s*(WTCTH-\d+)\)', line.strip())
        if match:
            url, product_id, product_code = match.groups()
            failed_products.append({
                'url': url,
                'id': int(product_id),
                'code': product_code
            })
    
    print(f"✅ Loaded {len(failed_products)} failed products from {REPORT_FILE}")
    return failed_products

def main():
    # Load the JSON file
    if not os.path.exists(INPUT_JSON):
        print(f"❌ Input JSON file {INPUT_JSON} not found.")
        return
    
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ Loaded data from {INPUT_JSON}")
    
    # Read failed products from ingredient_report.txt
    failed_products = read_failed_products()
    if not failed_products:
        print("✅ No failed products to process.")
        return
    
    # Initialize ingredient map and ID counter
    ingredient_map = {ing['name'].lower(): ing['id'] for ing in data['ingredient']}
    next_ing_id = max([ing['id'] for ing in data['ingredient']], default=0) + 1
    new_failed_products = []
    
    # Initialize Playwright
    with sync_playwright() as p:
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
            print("🔑 Creating new session with manual login...")
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.watsons.co.th/th/login")
            print("⏳ Please log in manually in the browser window...")
            print("👉 After successful login, press Enter to continue and save the session...")
            input()
            try:
                page.wait_for_url("**/watsons.co.th/**", timeout=10000)
                context.storage_state(path=SESSION_FILE)
                print(f"✅ Session saved to {SESSION_FILE}")
            except Exception as e:
                print(f"❌ Login verification failed: {e}. Please try again.")
                browser.close()
                return
        
        page = context.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        })
        
        # Process each failed product
        for failed in failed_products:
            product_id = failed['id']
            product_code = failed['code']
            url = failed['url']
            
            # Find the product in JSON
            product = next((p for p in data['product'] if p['id'] == product_id), None)
            if not product:
                print(f"❌ Product ID {product_id} not found in JSON.")
                new_failed_products.append(f"{url} (ID: {product_id}, Code: {product_code})")
                continue
            
            print(f"\n--- Re-scraping product ID {product_id}: {product['name']} ({product_code}) from web ---")
            
            # Clear existing ingredients
            product['ingredient'] = []
            
            # Scrape ingredients from web
            parsed_ings = scrape_ingredients_from_web(page, url, product_code, product_id)
            
            # If no ingredients found, use a default ingredient
            if not parsed_ings:
                parsed_ings = ["UNKNOWN"]
                with open(REPORT_FILE, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"[{timestamp}] Using default ingredient 'UNKNOWN' for product {product_code} (ID: {product_id}) due to no ingredients found.\n")
                print(f"⚠️ Using default ingredient 'UNKNOWN' for {product_code} (ID: {product_id})")
            
            # Map ingredients to IDs
            product_ing_ids = []
            for ing in parsed_ings:
                ing_lower = ing.lower()
                if ing_lower in ingredient_map:
                    product_ing_ids.append(ingredient_map[ing_lower])
                else:
                    new_ing = {
                        'id': next_ing_id,
                        'name': ing,
                        'allergic': False,
                        'allergic-relation': None
                    }
                    data['ingredient'].append(new_ing)
                    ingredient_map[ing_lower] = next_ing_id
                    product_ing_ids.append(next_ing_id)
                    next_ing_id += 1
            
            product['ingredient'] = product_ing_ids
            print(f"Updated product ID {product_id} with {len(product_ing_ids)} ingredient IDs from web")
            
            if not product_ing_ids:
                new_failed_products.append(f"{url} (ID: {product_id}, Code: {product_code})")
        
        browser.close()
    
    # Save the updated JSON
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    # Log new failed products to ingredient_report.txt
    with open(REPORT_FILE, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"\n[{timestamp}] Failed products after re-scraping (no ingredients):\n")
        if new_failed_products:
            for link in new_failed_products:
                f.write(f"- {link}\n")
        else:
            f.write("No failed products after re-scraping.\n")
    
    print(f"\n✅ Updated JSON saved to {OUTPUT_JSON}")
    print(f"Failed products logged to {REPORT_FILE}")
    print(f"Total unique ingredients: {len(data['ingredient'])}")

def extract_bp_number(link):
    """Extract BP_xxxxxx number from product link."""
    match = re.search(r'/p/BP_(\d+)', link)
    return match.group(1) if match else None

if __name__ == "__main__":
    main()