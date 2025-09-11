import json

# Load JSON from file
with open("product_data_recursivefilterimage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def fix_image_field(item):
    if "image" in item:
        if isinstance(item["image"], str):  # if single string
            if item["image"].strip():
                item["image"] = [item["image"]]  # wrap in list
            else:
                item["image"] = []  # empty string → empty list
        elif item["image"] is None:  # null → empty list
            item["image"] = []
        # if already list → keep as is

# Case 1: JSON is a list of objects
if isinstance(data, list):
    for item in data:
        fix_image_field(item)

# Case 2: JSON is a single object with products inside
elif isinstance(data, dict):
    for key, value in data.items():
        if isinstance(value, list):  # e.g., "products": [ {...}, {...} ]
            for item in value:
                fix_image_field(item)
        elif isinstance(value, dict):  # single object
            fix_image_field(value)

# Save fixed JSON
with open("data_fixed.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("✅ All 'image' fields fixed to be arrays!")
