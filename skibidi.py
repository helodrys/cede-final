import json

# Read the JSON file
with open('product_data_recursivefilterimagelist copy.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Empty the ingredient list at the root
data['ingredient'] = []

# Save the modified data back to file
with open('product_data_recursivefilterimagelist copy.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("✅ Successfully emptied all ingredient arrays")
