import os
import time
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# Unified Index Name
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "gift-concierge-v1")
BATCH_SIZE = 50 

def clean_price(price_val):
    """Helper to convert '$1,200.00' or '1200' to float 1200.0"""
    if pd.isna(price_val):
        return 0.0
    try:
        clean_str = str(price_val).replace('$', '').replace(',', '').strip()
        return float(clean_str)
    except:
        return 0.0

def ingest_products():
    print(f"🚀 Starting Ingestion to Index: {PINECONE_INDEX_NAME}...")

    if not GOOGLE_API_KEY or not PINECONE_API_KEY:
        raise ValueError("❌ Missing API Keys. Please check your backend/.env file.")
    
    # 1. Configure APIs
    genai.configure(api_key=GOOGLE_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # 2. Check/Create Index (Self-Healing Logic)
    existing_indexes = [i.name for i in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing_indexes:
        print(f"⚙️ Creating new index '{PINECONE_INDEX_NAME}' (Dimension: 768)...")
        try:
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=768, # Google Gemini Output Dimension
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            print("⏳ Waiting for index to initialize...")
            time.sleep(10) # Give Pinecone a moment to wake up
        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")
    
    index = pc.Index(PINECONE_INDEX_NAME)

    # 3. Load Data
    # Path logic: backend/scripts/ingest.py -> backend -> root -> data
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    csv_path = os.path.join(base_dir, 'data', 'products_enriched.csv')
    
    # Fallback to mock if enriched doesn't exist
    if not os.path.exists(csv_path):
        print(f"⚠️ Enriched data not found at {csv_path}. Checking for mock data...")
        csv_path = os.path.join(base_dir, 'data', 'products_mock.csv')

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ Could not find any CSV file at: {csv_path}")

    print(f"📂 Reading data from: {csv_path}")
    df = pd.read_csv(csv_path, dtype={'id': str})
    df = df.fillna('')
    
    print(f"📄 Found {len(df)} products.")
    vectors_batch = []
    
    for i, row in df.iterrows():
        # --- SMART CONTEXT BUILDER ---
        parts = [f"Title: {row.get('title', '')}."]
        parts.append(f"Description: {row.get('description', '')}.")
        parts.append(f"Style: {row.get('style', '')}.")
        parts.append(f"Category: {row.get('category', '')}.")
        
        if row.get('material'): parts.append(f"Material: {row.get('material')}.")
        if row.get('occasion'): parts.append(f"Good for Occasion: {row.get('occasion')}.")
        if row.get('skin_tone'): parts.append(f"Fits Skin Tone: {row.get('skin_tone')}.")
        if row.get('gemstone'): parts.append(f"Gemstone: {row.get('gemstone')}.")

        text_to_embed = " ".join(parts)

        # --- RETRY LOGIC ---
        embedding = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                time.sleep(0.5) # Rate limit protection
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text_to_embed,
                    task_type="retrieval_document"
                )
                embedding = result['embedding']
                break 
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Failed row {row.get('id')} after 3 attempts")
                else:
                    time.sleep(2)
        
        if embedding:
            metadata = {
                "id": str(row.get('id')),
                "title": str(row.get('title', '')),
                "price": clean_price(row.get('price')),
                "style": str(row.get('style', '')),
                "category": str(row.get('category', '')),
                "image_url": str(row.get('image_url', '')),
                "material": str(row.get('material', '')),
                "occasion": str(row.get('occasion', '')),
                "skin_tone": str(row.get('skin_tone', ''))
            }

            vectors_batch.append({
                "id": str(row['id']),
                "values": embedding,
                "metadata": metadata
            })
            
            if i % 10 == 0:
                print(f"[{i+1}/{len(df)}] Processed: {row.get('title', 'Unknown')[:30]}...")

        # UPLOAD BATCH
        if len(vectors_batch) >= BATCH_SIZE:
            try:
                index.upsert(vectors=vectors_batch)
                print(f"⬆️ Uploaded batch of {len(vectors_batch)}")
                vectors_batch = []
            except Exception as e:
                print(f"❌ Batch Upload Failed: {e}")

    # UPLOAD LEFTOVERS
    if len(vectors_batch) > 0:
        index.upsert(vectors=vectors_batch)
        print(f"⬆️ Uploaded final batch of {len(vectors_batch)}")

    print("✅ Ingestion Complete!")

if __name__ == "__main__":
    ingest_products()