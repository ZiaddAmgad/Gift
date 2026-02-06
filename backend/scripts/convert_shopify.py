import json
import csv
import re
import os
import time
import requests
import argparse
from dotenv import load_dotenv
from google import genai  # new SDK
from PIL import Image
from io import BytesIO

# Load API Key
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# LIMIT = 18 # Set to None for full run
LIMIT = None 

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    return " ".join(re.sub(cleanr, '', raw_html).split())

def analyze_product_multimodal(image_url, title, description):
    """
    Multimodal Analysis: Uses Image + Title + Description to extract attributes.
    """
    if not image_url or not GOOGLE_API_KEY:
        return None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=GOOGLE_API_KEY)
            
            # 1. Download Image
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200: return None
            img_data = Image.open(BytesIO(response.content))

            # 2. Construct Multimodal Prompt
            # We inject the text context alongside the image
            prompt = f"""
            You are an expert Jewelry Data Analyst. Analyze this product using both the Image and the Text provided.

            **PRODUCT CONTEXT:**
            Title: {title}
            Description: {description}

            **ANALYSIS LOGIC:**
            1. **Material & Gemstone (Text Dominant):** 
               - Read the description carefully. If it specifies "18k Gold Plated" or "Sterling Silver", TRUST THE TEXT. 
               - If the text says "Silver plated with Rose Gold", choose the VISIBLE FINISH (Rose Gold) as the material.
               - If the text is vague, fall back to visual analysis.
            2. **Style & Skin Tone (Vision Dominant):** 
               - Rely primarily on the image to determine the aesthetic style (e.g. Boho vs Minimalist) and the best-suited skin tone.
            3. **Occasion:** 
               - Use both text context and visual vibe to decide.

            **RETURN VALID JSON WITH THESE EXACT KEYS & OPTIONS:**
            {{
                "material": "Gold, Silver, Rose Gold, White Gold, Gold Plated, Sterling Silver, Platinum, Enamel, Leather, Cord, Pearl, Beaded, Mixed",
                "style": "Minimalist, Boho, Vintage, Bold, Statement, Art Deco, Modern, Classic, Romantic, Geometric, Nature, Dainty, Industrial, Traditional, Trendy",
                "gemstone": "Diamond, Zircon, Pearl, Turquoise, Onyx, Crystal, Emerald, Ruby, Sapphire, None",
                "skin_tone": "Cool Tones, Warm Tones, Neutral",
                "occasion": "Daily, Party, Valentine, Anniversary, Mother's Day, Holiday, Gift"
            }}
            """
            
            # 3. Send Both to Gemini (new SDK)
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, img_data],
            )
            text = res.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)

        except Exception as e:
            if "429" in str(e):
                print(f"      ⏳ Quota hit. Sleeping 60s...")
                time.sleep(60) 
            else:
                print(f"      ⚠️ AI Analysis Error: {e}")
                return None
    return None

def infer_category(title):
    t_lower = title.lower()
    if "set" in t_lower: return "Set"
    if "anklet" in t_lower: return "Anklet"
    if "bangle" in t_lower: return "Bangle"
    if "brace" in t_lower or "braclete" in t_lower: return "Bracelet"
    if "hoop" in t_lower: return "Hoop"
    if "earring" in t_lower or "earing" in t_lower: return "Earring"
    if "ring" in t_lower: return "Ring"
    if "chain" in t_lower: return "Chain"
    if "necklace" in t_lower: return "Necklace"
    if "handchain" in t_lower: return "Handchain"
    return "Jewelry"

def get_processed_ids(output_file):
    if not os.path.exists(output_file): return set()
    processed = set()
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            next(reader) 
            for row in reader:
                if row: processed.add(str(row[0]))
        except StopIteration: pass
    return processed

def process_client_data(client_id):
    # Fix paths to point to root /Gift/data
    script_dir = os.path.dirname(os.path.abspath(__file__)) 
    backend_dir = os.path.dirname(script_dir)
    root_dir = os.path.dirname(backend_dir)
    
    input_file = os.path.join(root_dir, "data", f"{client_id}.json")
    output_file = os.path.join(root_dir, "data", f"{client_id}_enriched.csv")

    print(f"🚀 Enriching Data for: {client_id}")
    print(f"📂 Input: {input_file}")
    
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found. Run scraper first.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    all_products = data.get('products', [])

    processed_ids = get_processed_ids(output_file)
    pending_products = [p for p in all_products if str(p['id']) not in processed_ids]
    
    if LIMIT:
        pending_products = pending_products[:LIMIT]

    print(f"⚡ Processing {len(pending_products)} items...")

    file_exists = os.path.exists(output_file)
    mode = 'a' if file_exists else 'w'
    
    # --- UPDATED HEADER: ADDED 'handle' ---
    headers = ['id', 'title', 'price', 'description', 'style', 'material', 'skin_tone', 'occasion', 'gemstone', 'image_url', 'category', 'handle']

    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(headers)

        for i, p in enumerate(pending_products):
            try:
                p_id = str(p.get('id'))
                title = p.get('title')
                handle = p.get('handle', '') # <--- EXTRACT HANDLE
                desc = clean_html(p.get('body_html', '')) or title
                variants = p.get('variants', [])
                price = variants[0].get('price') if variants else "0"
                images = p.get('images', [])
                image_url = images[0].get('src') if images else ""
                
                cat = p.get('product_type', '')
                if not cat or cat.lower() == "jewelry": cat = infer_category(title)
                
                print(f"[{i+1}/{len(pending_products)}] Analyzing: {title[:20]}...")

                # --- NEW MULTIMODAL CALL ---
                ai_data = None
                if image_url:
                    # Pass Title and Description along with Image URL
                    ai_data = analyze_product_multimodal(image_url, title, desc)
                    time.sleep(3) # Short sleep to respect rate limits
                
                material = ai_data.get('material', 'Unknown') if ai_data else "Unknown"
                style = ai_data.get('style', 'Classic') if ai_data else "Classic"
                skin_tone = ai_data.get('skin_tone', 'All') if ai_data else "All"
                occasion = ai_data.get('occasion', 'General') if ai_data else "General"
                gemstone = ai_data.get('gemstone', 'None') if ai_data else "None"

                # --- UPDATED ROW: INCLUDED handle ---
                writer.writerow([p_id, title, price, desc, style, material, skin_tone, occasion, gemstone, image_url, cat, handle])
                f.flush()

            except Exception as e:
                print(f"❌ Error on item {i}: {e}")

    print(f"\n✅ Enrichment Complete: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--client_id", required=True, help="Client ID to process")
    args = parser.parse_args()
    process_client_data(args.client_id)