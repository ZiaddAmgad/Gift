import requests
import json
import os
import time
import argparse

# HOW TO RUN:
# python scripts/scrape_all.py --client_id "koay" --url "https://koaysilver.com/products.json"

def scrape_shopify(client_id, base_url):
    # Dynamic Output Path: data/koay.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir)) # Up 2 levels to Gift/
    
    output_file = os.path.join(root_dir, "data", f"{client_id}.json")
    
    all_products = []
    page = 1
    limit = 250
    
    print(f"🚀 Starting Scraper for Client: {client_id}")
    print(f"🌐 URL: {base_url}")
    print("------------------------------------------------")

    while True:
        print(f"🔄 Scraping Page {page}...", end=" ")
        
        try:
            url = f"{base_url}?page={page}&limit={limit}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Failed (Status: {response.status_code})")
                time.sleep(3)
                continue

            data = response.json()
            products = data.get("products", [])

            if not products:
                print("✅ Done.")
                break

            all_products.extend(products)
            print(f"Found {len(products)} items. (Total: {len(all_products)})")
            
            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"\n❌ Error on page {page}: {e}")
            break

    # SAVE TO JSON
    print("------------------------------------------------")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    final_data = {"products": all_products}

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    print(f"🎉 Success! Saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--client_id", required=True, help="Unique ID for the client (e.g., 'fortuna', 'koay')")
    parser.add_argument("--url", required=True, help="Full link to products.json")
    args = parser.parse_args()
    
    scrape_shopify(args.client_id, args.url)