from playwright.sync_api import sync_playwright
import time, os, csv
import requests  # Added for optional link validation

TARGET_URL = "https://www.watsons.co.th/th/search?text=%E0%B8%A2%E0%B8%B2%E0%B8%AA%E0%B8%A3%E0%B8%B0%E0%B8%9C%E0%B8%A1&useDefaultSearch=false&brandRedirect=true"
SESSION_FILE = "watsons_session.json"
OUTPUT_CSV = "final_test.csv"

def save_to_csv(links):
    """Append product links to a CSV file."""
    file_exists = os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header only if file doesn't exist
        if not file_exists:
            writer.writerow(['URL', 'Types'])
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        types = "Shampoo"  # Change here
        for url in links:
            writer.writerow([url, types])
    print(f"✅ Appended {len(links)} unique links to {OUTPUT_CSV}")

def validate_url(url):
    """Check if a URL is likely a valid product link and optionally verify HTTP status."""
    # Filter URLs that look like product pages (e.g., contain '/p/BP_')
    if '/p/BP_' not in url:
        return False
    # Optional: Check HTTP status (uncomment to enable)
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False
    """
    return True

def scrape_product_links(page):
    """Scrape product links from the page."""
    print("🔍 Scraping product links...")
    links = []
    base_url = "https://www.watsons.co.th"
    
    # Selector for product links
    link_selector = 'a.ClickSearchResultEvent_Class.gtmAlink'
    
    try:
        page.wait_for_selector(link_selector, timeout=10000)
        elements = page.query_selector_all(link_selector)
        print(f"✅ Found {len(elements)} potential product links")
        
        for elem in elements:
            try:
                href = elem.get_attribute('href')
                if href:
                    # Make full URL if relative
                    if href.startswith('/'):
                        full_url = base_url + href
                    else:
                        full_url = href
                    if validate_url(full_url):
                        links.append(full_url)
                    else:
                        print(f"⚠️ Skipped invalid URL: {full_url}")
            except Exception as e:
                print(f"❌ Error processing link: {str(e)[:50]}")
                continue
    except Exception as e:
        print(f"❌ Error finding links: {str(e)[:50]}")
    
    # Remove duplicates
    unique_links = list(set(links))
    
    if not unique_links:
        print("⚠️ No valid product links found. The page might be dynamic or selectors may need adjustment.")
    return unique_links

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
        
        print(f"📄 Navigating to: {TARGET_URL}")
        page.goto(TARGET_URL)
        print("⏳ Waiting for page content to load...")
        page.wait_for_load_state('domcontentloaded', timeout=15000)
        time.sleep(2)  # Brief delay for JavaScript rendering
        
        # Scroll to load all promotions (handle lazy loading)
        print("📜 Scrolling to load all content...")
        last_height = page.evaluate("document.body.scrollHeight")
        max_scroll_attempts = 10  # Limit to prevent infinite loop
        attempts = 0
        while attempts < max_scroll_attempts:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)  # Delay for loading
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            attempts += 1
        
        # Scrape links
        product_links = scrape_product_links(page)
        
        # Save to CSV
        if product_links:
            save_to_csv(product_links)
            print(f"🎉 Scraped {len(product_links)} unique product links!")
            print("Example links:")
            for link in product_links[:5]:  # Show first 5
                print(link)
        else:
            print("❌ No links scraped. Inspect the page manually to verify selectors.")
        
        print(f"🛒 View results in: {OUTPUT_CSV}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("⏳ Waiting 5 seconds before closing...")
        time.sleep(5)
        try:
            browser.close()
        except:
            pass

print("👋 Program finished.")