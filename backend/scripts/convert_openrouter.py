import json
import csv
import re
import os
import time
import base64
import requests
from dotenv import load_dotenv
from openai import OpenAI

# 1. Load Environment Variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Configuration
INPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "koay.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "products_enriched.csv")

# ⚠️ SET TO None TO RUN ALL PRODUCTS
LIMIT = 1

# 🏆 MODEL SELECTION — Google Gemini 2.5 Flash Vision Model
MODEL_NAME = "google/gemini-2.5-flash"

def clean_html(raw_html):
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    return " ".join(re.sub(cleanr, '', raw_html).split())

def encode_image_to_base64(image_url):
    """Downloads an image and converts it to Base64."""
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        print(f"⚠️ Image Download Error: {e}")
    return None


# -------------------------
# 🔥 GEMINI 2.5 FLASH VERSION
# -------------------------
def analyze_image(image_url):
    """Analyzes jewelry attributes using Gemini 2.5 Flash on OpenRouter."""

    if not image_url or not OPENROUTER_API_KEY:
        return None

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Jewelry AI Script"
        }
    )

    base64_image = encode_image_to_base64(image_url)
    if not base64_image:
        return None

    prompt = """
    Analyze this jewelry image and return VALID JSON ONLY with these keys:
    {
        "material": "...",
        "style": "...",
        "gemstone": "...",
        "skin_tone": "...",
        "occasion": "..."
    }
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        { "type": "text", "text": prompt },
                        { "type": "input_image", "image": f"data:image/jpeg;base64,{base64_image}" }
                    ]
                }
            ]
        )

        content = response.choices[0].message.content

        # Clean markdown
        content = content.replace("```json", "").replace("```", "").strip()

        # Convert to dictionary
        return json.loads(content)

    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return None


def infer_category(title):
    t = title.lower()
    if "set" in t: return "Set"
    if "anklet" in t: return "Anklet"
    if "bangle" in t: return "Bangle"
    if "brace" in t: return "Bracelet"
    if "hoop" in t: return "Hoop"
    if "earring" in t or "earing" in t: return "Earring"
    if "ring" in t: return "Ring"
    if "chain" in t: return "Chain"
    if "necklace" in t: return "Necklace"
    return "Jewelry"


def get_processed_ids():
    if not os.path.exists(OUTPUT_FILE): 
        return set()
    processed = set()
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            next(reader)
            for row in reader:
                if row:
                    processed.add(str(row[0]))
        except StopIteration:
            pass
    return processed


def main():
    print("🚀 Starting Smart Jewelry Enrichment (Gemini 2.5 Flash)...")

    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_products = data.get("products", [])
    processed_ids = get_processed_ids()

    print(f"📊 Total Products: {len(all_products)}")
    print(f"✅ Already Processed: {len(processed_ids)}")

    pending = [p for p in all_products if str(p["id"]) not in processed_ids]

    if LIMIT:
        pending = pending[:LIMIT]
        print(f"🧪 LIMIT applied: {LIMIT} items")

    if not pending:
        print("🎉 All products processed!")
        return

    print(f"⚡ Processing {len(pending)} items...")

    file_exists = os.path.exists(OUTPUT_FILE)
    mode = "a" if file_exists else "w"

    headers = [
        "id", "title", "price", "description",
        "style", "material", "skin_tone", "occasion",
        "gemstone", "image_url", "category"
    ]

    with open(OUTPUT_FILE, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)

        for i, p in enumerate(pending):
            try:
                p_id = str(p.get("id"))
                title = p.get("title")
                desc = clean_html(p.get("body_html", "")) or title
                variants = p.get("variants", [])
                price = variants[0].get("price") if variants else "0"
                images = p.get("images", [])
                image_url = images[0].get("src") if images else ""

                category = p.get("product_type", "")
                if not category or category.lower() == "jewelry":
                    category = infer_category(title)

                print(f"[{i+1}/{len(pending)}] Analyzing: {title[:30]}... ({category})")

                ai = analyze_image(image_url) if image_url else None

                material = ai.get("material", "Unknown") if ai else "Unknown"
                style = ai.get("style", "Classic") if ai else "Classic"
                skin_tone = ai.get("skin_tone", "All") if ai else "All"
                occasion = ai.get("occasion", "General") if ai else "General"
                gemstone = ai.get("gemstone", "None") if ai else "None"

                writer.writerow([
                    p_id, title, price, desc,
                    style, material, skin_tone, occasion,
                    gemstone, image_url, category
                ])
                f.flush()

                time.sleep(1)  # avoid rate limiting

            except Exception as e:
                print(f"❌ Error on item {i}: {e}")

    print("\n✅ Batch Complete.")


if __name__ == "__main__":
    main()
