import json
import csv
import re
import os
import time
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from io import BytesIO

# Load API Key
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configuration
INPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "koay.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "products_enriched.csv")

# ⚠️ SET TO None TO RUN ALL PRODUCTS. 
LIMIT = 18

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    return " ".join(re.sub(cleanr, '', raw_html).split())

def analyze_image(image_url):
    """Downloads image and asks Gemini for attributes."""
    if not image_url or not GOOGLE_API_KEY: return None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            
            # 🏆 USING GEMINI 2.0 FLASH
            # Smart, Multimodal, and High Rate Limits (1500/day)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200: return None
            
            img_data = Image.open(BytesIO(response.content))

            # --- UPDATED PROMPT WITH EXPANDED MATERIALS & STYLES ---
            prompt = """
            Analyze this jewelry image carefully. Return valid JSON with these keys:
            {
                "material": "Gold, Silver, Rose Gold, White Gold, Gold Plated, Sterling Silver, Platinum, Enamel, Leather, Cord, Pearl, Beaded, Mixed",
                "style": "Minimalist, Boho, Vintage, Bold, Statement, Art Deco, Modern, Classic, Romantic, Geometric, Nature, Dainty, Industrial, Traditional, Trendy",
                "gemstone": "Diamond, Zircon, Pearl, Turquoise, Onyx, Crystal, Emerald, Ruby, Sapphire, None",
                "skin_tone": "Cool Tones, Warm Tones, Neutral",
                "occasion": "Daily, Party, Valentine, Anniversary, Mother's Day, Holiday, Gift"
            }
            """
            
            res = model.generate_content([prompt, img_data])
            text = res.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)

        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                print(f"      ⏳ Quota hit. Sleeping 60s before retry...")
                time.sleep(60) 
            else:
                print(f"      ⚠️ Vision Error: {e}")
                return None
    return None

def infer_category(title):
    t_lower = title.lower()
    
    # Priority Order Matters!
    if "set" in t_lower: return "Set"
    if "anklet" in t_lower: return "Anklet"
    if "bangle" in t_lower: return "Bangle"
    
    # Catch "Bracelet" and common typo "Braclete"
    if "brace" in t_lower or "braclete" in t_lower: return "Bracelet"
    
    if "hoop" in t_lower: return "Hoop"
    
    # Check Earring BEFORE Ring
    if "earring" in t_lower or "earing" in t_lower: return "Earring"
    
    if "ring" in t_lower: return "Ring"
    
    if "chain" in t_lower: return "Chain"
    if "necklace" in t_lower: return "Necklace"
    if "handchain" in t_lower: return "Handchain"
    
    return "Jewelry"

def get_processed_ids():
    """Reads the existing CSV to find which IDs are already done."""
    if not os.path.exists(OUTPUT_FILE):
        return set()
    
    processed = set()
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader) # Skip header
            for row in reader:
                if row: processed.add(str(row[0])) # ID is first column
        except StopIteration:
            pass
    return processed

def main():
    print(f"🚀 Starting Smart Conversion (Resumable Mode)...")
    
    # 1. Load Source Data
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    all_products = data.get('products', [])

    # 2. Check what is already done
    processed_ids = get_processed_ids()
    print(f"📊 Total Products: {len(all_products)}")
    print(f"✅ Already Processed: {len(processed_ids)}")
    
    # 3. Filter list to only show pending items
    pending_products = [p for p in all_products if str(p['id']) not in processed_ids]
    
    if LIMIT:
        pending_products = pending_products[:LIMIT]
        print(f"🧪 LIMIT applied: Processing next {LIMIT} items only.")

    if not pending_products:
        print("🎉 All products are already processed! Run ingest.py now.")
        return

    print(f"⚡ Processing {len(pending_products)} remaining items...")

    # 4. Prepare CSV Writer (Append Mode)
    file_exists = os.path.exists(OUTPUT_FILE)
    mode = 'a' if file_exists else 'w'
    
    headers = ['id', 'title', 'price', 'description', 'style', 'material', 'skin_tone', 'occasion', 'gemstone', 'image_url', 'category']

    with open(OUTPUT_FILE, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers) # Write header only if new file

        # 5. Loop and Save Instantly
        for i, p in enumerate(pending_products):
            try:
                p_id = str(p.get('id'))
                title = p.get('title')
                desc = clean_html(p.get('body_html', '')) or title
                
                variants = p.get('variants', [])
                price = variants[0].get('price') if variants else "0"
                images = p.get('images', [])
                image_url = images[0].get('src') if images else ""

                # Category Logic
                cat = p.get('product_type', '')
                if not cat or cat.lower() == "jewelry":
                    cat = infer_category(title)
                else:
                    if cat.endswith('s') and cat.lower() != "glass": 
                        cat = cat[:-1]
                
                # Double check typos
                if cat.lower() in ["earing", "braclete"]:
                    cat = infer_category(title)

                print(f"[{i+1}/{len(pending_products)}] Analyzing: {title[:20]}... ({cat})")

                # Vision Analysis
                ai_data = None
                if image_url:
                    ai_data = analyze_image(image_url)
                    # SLEEP is crucial for Free Tier
                    time.sleep(4) 
                
                material = ai_data.get('material', 'Unknown') if ai_data else "Unknown"
                style = ai_data.get('style', 'Classic') if ai_data else "Classic"
                skin_tone = ai_data.get('skin_tone', 'All') if ai_data else "All"
                occasion = ai_data.get('occasion', 'General') if ai_data else "General"
                gemstone = ai_data.get('gemstone', 'None') if ai_data else "None"

                # Save Row IMMEDIATELY
                writer.writerow([p_id, title, price, desc, style, material, skin_tone, occasion, gemstone, image_url, cat])
                f.flush() # Force write to disk

            except Exception as e:
                print(f"❌ Error on item {i}: {e}")

    print(f"\n✅ Batch Complete. Total products in CSV: {len(get_processed_ids())}")

if __name__ == "__main__":
    main()