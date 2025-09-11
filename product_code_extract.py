import json
import re

# Regex pattern for WTCTH-xxxxxx
pattern = re.compile(r"WTCTH-\d+")

# Read the JSON file
with open('product_data_recursivefilterimagelist copy.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Go through all products
for product in data.get("product", []):
    codes = []
    for url in product.get("image", []):
        matches = pattern.findall(url)
        if matches:
            codes.extend(matches)
    # Remove duplicates (if same code appears multiple times)
    product["product_codes"] = list(set(codes))

# Save back to file
with open('product_data_recursivefilterimagelist copy.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("✅ Successfully extracted WTCTH codes into product['product_codes']")
