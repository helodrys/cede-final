from bs4 import BeautifulSoup
import json
import re
import os

# File paths
JSON_FILE = "product_data_recursivefilterimagelist copy.json"
OUTPUT_JSON = "product_data_recursivefilterimagelist copy_updated.json"
DEBUG_PREFIX = "debug_page_"

def extract_bp_number(link):
    """Extract BP_xxxxxx number from product link."""
    match = re.search(r'/p/BP_(\d+)', link)
    return match.group(1) if match else None

def extract_ingredients_from_html(html_file):
    """Extract ingredients from debug HTML after 'ส่วนประกอบ </h4><p class="ng-tns-c...'>'."""
    if not os.path.exists(html_file):
        print(f"Debug file not found: {html_file}")
        return ""
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the h4 with "ส่วนประกอบ"
    h4 = soup.find('h4', string=re.compile(r'ส่วนประกอบ'))
    if h4:
        # Find the next p with class matching ng-tns-c... ng-star-inserted
        next_p = h4.find_next_sibling('p', class_=re.compile(r'ng-tns-c\d+-\d+ ng-star-inserted'))
        if next_p:
            ingredient_text = next_p.get_text(strip=True)
            print(f"Extracted ingredient text: {ingredient_text[:200]}...")
            return ingredient_text
    
    print("No 'ส่วนประกอบ' section found.")
    return ""

def parse_ingredients(ingredient_text):
    """Parse ingredients from text using heuristics for comma-separated or space-separated lists."""
    ingredients = []
    if not ingredient_text:
        return ingredients
    
    # Uppercase for consistency
    ingredient_text = ingredient_text.upper()
    
    # First, try splitting by comma
    raw_parts = [part.strip() for part in ingredient_text.split(',') if part.strip()]
    
    if len(raw_parts) > 1:
        # Use comma split
        for part in raw_parts:
            # Filter English only (no Thai)
            if re.match(r'^[A-Z0-9\s\(\)\-\.\/,]+$', part) and not re.search(r'[ป-ฮ]', part):
                ingredients.append(part)
    else:
        # If no commas or long string, tokenize by space and group using heuristics
        tokens = re.split(r'\s+', ingredient_text)
        i = 0
        while i < len(tokens):
            current_ing = tokens[i]
            i += 1
            # Group next words if they look like chemical continuation (uppercase, short, with - / numbers)
            while i < len(tokens) and len(tokens[i]) <= 15 and re.match(r'^[A-Z0-9\-\./]+$', tokens[i]):
                current_ing += ' ' + tokens[i]
                i += 1
            # Filter English only
            if re.match(r'^[A-Z0-9\s\(\)\-\.\/]+$', current_ing) and not re.search(r'[ป-ฮ]', current_ing):
                ingredients.append(current_ing)
    
    # Ensure uniqueness (normalize to lowercase for checking)
    unique_ings = []
    seen = set()
    for ing in ingredients:
        ing_lower = ing.lower()
        if ing_lower not in seen:
            seen.add(ing_lower)
            unique_ings.append(ing)
    
    print(f"Parsed unique ingredients: {unique_ings}")
    return unique_ings

# Load JSON
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Clear ingredients
data['ingredient'] = []
for product in data['product']:
    product['ingredient'] = []

# Process each product
for product in data['product']:
    print(f"\n--- Processing product: {product['name']} ---")
    
    # Get product_code from product_codes or derive from link
    if 'product_codes' in product and product['product_codes']:
        product_code = product['product_codes'][0]
    else:
        bp_number = extract_bp_number(product['link'])
        if not bp_number:
            print(f"No BP number for {product['name']}")
            continue
        product_code = f"WTCTH-{bp_number}"
    
    # Load debug HTML
    html_file = f"debug_html/{DEBUG_PREFIX}{product_code}.html"
    ingredient_text = extract_ingredients_from_html(html_file)
    
    # Parse ingredients
    parsed_ings = parse_ingredients(ingredient_text)
    
    # Map to IDs
    ingredient_ids = []
    for ing in parsed_ings:
        ing_lower = ing.lower()
        existing_id = None
        for existing in data['ingredient']:
            if existing['name'].lower() == ing_lower:
                existing_id = existing['id']
                break
        
        if existing_id:
            ingredient_ids.append(existing_id)
        else:
            next_id = len(data['ingredient']) + 1
            new_ing = {
                'id': next_id,
                'name': ing,
                'allergic': False,
                'allergic-relation': None
            }
            data['ingredient'].append(new_ing)
            ingredient_ids.append(next_id)
    
    product['ingredient'] = ingredient_ids
    print(f"Updated {len(ingredient_ids)} ingredients for {product['name']}")

# Save updated JSON
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"\n✅ Updated JSON saved to {OUTPUT_JSON}")
print(f"Total unique ingredients added: {len(data['ingredient'])}")