import csv
import os
import re
import time

INPUT_CSV = "watsons_product_links.csv"
OUTPUT_CSV = "cleaned_watsons_product_links.csv"

def clean_url(url):
    """Clean the URL by truncating anything after /p/BP_XXXX"""
    # Use regex to match up to /p/BP_ followed by digits
    match = re.match(r'(https?://.+?/p/BP_\d+)', url.strip())
    if match:
        return match.group(1)
    return url.strip()  # Return original if no match

def process_csv():
    """Process the input CSV, clean URLs, remove duplicates, and save to new CSV."""
    if not os.path.exists(INPUT_CSV):
        print(f"❌ Input file {INPUT_CSV} not found.")
        return

    urls = set()
    with open(INPUT_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            next(reader)  # Skip header if present
        except StopIteration:
            pass
        for row in reader:
            if row:
                raw_url = row[0]
                cleaned = clean_url(raw_url)
                if cleaned:
                    urls.add(cleaned)

    if not urls:
        print("⚠️ No URLs found in the CSV.")
        return

    # Save to output CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['URL'])
        for url in sorted(urls):
            writer.writerow([url])

    print(f"✅ Processed {len(urls)} unique cleaned URLs.")
    print(f"🛒 Saved to: {OUTPUT_CSV}")
    print("Example cleaned URLs:")
    for url in list(urls)[:5]:
        print(url)

if __name__ == "__main__":
    print("🔍 Starting CSV cleaning process...")
    start_time = time.time()
    process_csv()
    print(f"👋 Finished in {time.time() - start_time:.2f} seconds.")