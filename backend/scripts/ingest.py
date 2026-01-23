import os
import time
import argparse
import pandas as pd
import unicodedata
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "gift-concierge-v1")
BATCH_SIZE = 50 

def clean_price(price_val):
    if pd.isna(price_val): return 0.0
    try:
        clean_str = str(price_val).replace('$', '').replace(',', '').strip()
        return float(clean_str)
    except: return 0.0

# --- THE NUCLEAR OPTION (Strict ASCII) ---
def force_ascii(text):
    """
    Removes ANY character that isn't standard English/ASCII.
    This deletes Arabic/Chinese/Emojis to prevent Windows HTTP crashes.
    Ex: "Islamic “آية الكرسي"" -> "Islamic Necklace"
    """
    if text is None: return ""
    s = str(text)
    
    # 1. Normalize (Turn 'é' into 'e')
    s = unicodedata.normalize('NFKD', s)
    
    # 2. Encode to ASCII, ignoring errors (Drops Arabic/Emojis)
    s = s.encode('ascii', 'ignore').decode('ascii')
    
    # 3. Clean up double quotes/spaces left behind
    s = s.replace('"', '').replace("'", "")
    return s.strip()

def get_existing_ids(index, namespace):
    existing_ids = set()
    try:
        for ids in index.list(namespace=namespace):
            existing_ids.update(ids)
        print(f"🧐 Found {len(existing_ids)} existing vectors in namespace '{namespace}'")
    except Exception as e:
        print(f"⚠️ Could not fetch existing IDs (Namespace might be empty): {e}")
    return existing_ids

def ingest_client(client_id):
    print(f"🚀 Ingesting for Client: {client_id} -> Namespace: {client_id}")

    if not GOOGLE_API_KEY or not PINECONE_API_KEY:
        raise ValueError("❌ Missing API Keys.")
    
    genai.configure(api_key=GOOGLE_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing_indexes = [i.name for i in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing_indexes:
        print(f"⚙️ Creating Master Index '{PINECONE_INDEX_NAME}'...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=768, 
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        time.sleep(10)
    
    index = pc.Index(PINECONE_INDEX_NAME)

    script_dir = os.path.dirname(os.path.abspath(__file__)) 
    backend_dir = os.path.dirname(script_dir)
    root_dir = os.path.dirname(backend_dir)
    
    csv_path = os.path.join(root_dir, 'data', f'{client_id}_enriched.csv')
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ No enriched data found for {client_id}")

    print(f"📂 Reading: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path, dtype={'id': str}, encoding='utf-8')
    except UnicodeDecodeError:
        print("⚠️ UTF-8 read failed, trying latin-1 (Excel)...")
        df = pd.read_csv(csv_path, dtype={'id': str}, encoding='latin-1')

    df = df.fillna('')
    print(f"📄 CSV contains {len(df)} products.")

    existing_ids = get_existing_ids(index, client_id)
    
    df_new = df[~df['id'].isin(existing_ids)]
    
    if df_new.empty:
        print("✅ All products are already ingested! Nothing to do.")
        return

    print(f"⚡ New products to ingest: {len(df_new)}")
    
    vectors_batch = []
    
    for i, row in df_new.iterrows():
        # Get raw text for embedding (We WANT the AI to read the Arabic)
        raw_title = str(row.get('title', ''))
        raw_desc = str(row.get('description', ''))
        
        # Prepare text to embed (Use raw rich text)
        text_to_embed = f"Title: {raw_title}. Description: {raw_desc}. Style: {row.get('style')}. Material: {row.get('material')}."

        embedding = None
        for attempt in range(3):
            try:
                time.sleep(0.5)
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text_to_embed,
                    task_type="retrieval_document"
                )
                embedding = result['embedding']
                break 
            except: time.sleep(2)
        
        if embedding:
            # --- APPLY STRICT ASCII TO METADATA ---
            # This ensures the upload to Pinecone does NOT crash on Windows
            metadata = {
                "id": str(row.get('id')),
                "title": force_ascii(raw_title), # Stripped for safety
                "price": clean_price(row.get('price')),
                "style": force_ascii(row.get('style', '')),
                "category": force_ascii(row.get('category', '')),
                "image_url": str(row.get('image_url', '')),
                "material": force_ascii(row.get('material', '')),
                "occasion": force_ascii(row.get('occasion', '')),
                "skin_tone": force_ascii(row.get('skin_tone', '')),
                "handle": force_ascii(row.get('handle', ''))
            }

            vectors_batch.append({
                "id": str(row['id']),
                "values": embedding,
                "metadata": metadata
            })
            
            # Print safe title for console
            print(f"[{len(vectors_batch)}/{len(df_new)}] Prepared: {metadata['title'][:20]}...")

        if len(vectors_batch) >= BATCH_SIZE:
            index.upsert(vectors=vectors_batch, namespace=client_id)
            print(f"⬆️ Uploaded batch to namespace '{client_id}'")
            vectors_batch = []

    if len(vectors_batch) > 0:
        index.upsert(vectors=vectors_batch, namespace=client_id)
        print(f"⬆️ Uploaded final batch.")

    print(f"✅ Ingestion Complete for {client_id}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--client_id", required=True, help="Client ID (Namespace)")
    args = parser.parse_args()
    ingest_client(args.client_id)