import requests
import json
import os
import time

# CONFIGURATION
BASE_URL = "https://koaysilver.com/products.json"
# Saves to backend/data/koay.json
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "koay.json")

def scrape_koay_silver_to_json():
    all_products = []
    page = 1
    limit = 250  # Max allowed by Shopify per request
    
    print(f"🚀 Starting Full Catalog Scraper for: {BASE_URL}")
    print(f"📂 Output File: {OUTPUT_FILE}")
    print("------------------------------------------------")

    while True:
        print(f"🔄 Scraping Page {page}...", end=" ")
        
        try:
            # Fetch the raw JSON from Shopify
            url = f"{BASE_URL}?page={page}&limit={limit}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Failed (Status: {response.status_code})")
                print("   Retrying in 3 seconds...")
                time.sleep(3)
                continue

            data = response.json()
            products = data.get("products", [])

            # STOP CONDITION: If no products returned, we are done
            if not products:
                print("✅ Done (No more products).")
                break

            # Add to master list
            all_products.extend(products)
            count = len(products)
            total_so_far = len(all_products)
            
            print(f"Found {count} items. (Total: {total_so_far})")
            
            # Prepare for next page
            page += 1
            time.sleep(1) # Be polite to the server

        except Exception as e:
            print(f"\n❌ Error on page {page}: {e}")
            break

    # SAVE TO JSON
    print("------------------------------------------------")
    print(f"💾 Saving {len(all_products)} products to JSON...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Wrap in "products" key to match standard Shopify structure
    final_data = {"products": all_products}

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    print(f"🎉 Success! Full catalog saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_koay_silver_to_json()