import os
import time
import argparse
import pandas as pd
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

def get_existing_ids(index, namespace):
    """Fetches all vector IDs currently in the namespace to avoid re-embedding."""
    existing_ids = set()
    try:
        # Pinecone list method is paginated. We fetch all pages.
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

    # 1. LOAD CSV
    script_dir = os.path.dirname(os.path.abspath(__file__)) 
    backend_dir = os.path.dirname(script_dir)
    root_dir = os.path.dirname(backend_dir)
    
    csv_path = os.path.join(root_dir, 'data', f'{client_id}_enriched.csv')
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ No enriched data found for {client_id}")

    print(f"📂 Reading: {csv_path}")
    df = pd.read_csv(csv_path, dtype={'id': str})
    df = df.fillna('')
    print(f"📄 CSV contains {len(df)} products.")

    # 2. FILTER ALREADY INGESTED
    existing_ids = get_existing_ids(index, client_id)
    
    df_new = df[~df['id'].isin(existing_ids)]
    
    if df_new.empty:
        print("✅ All products are already ingested! Nothing to do.")
        return

    print(f"⚡ New products to ingest: {len(df_new)}")
    
    # 3. PROCESS NEW ONLY
    vectors_batch = []
    
    for i, row in df_new.iterrows():
        text_to_embed = f"Title: {row.get('title', '')}. Description: {row.get('description', '')}. Style: {row.get('style', '')}. Category: {row.get('category', '')}. Material: {row.get('material')}. Occasion: {row.get('occasion')}. Skin Tone: {row.get('skin_tone')}."

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
            # --- UPDATED METADATA: INCLUDED handle ---
            metadata = {
                "id": str(row.get('id')),
                "title": str(row.get('title', '')),
                "price": clean_price(row.get('price')),
                "style": str(row.get('style', '')),
                "category": str(row.get('category', '')),
                "image_url": str(row.get('image_url', '')),
                "material": str(row.get('material', '')),
                "occasion": str(row.get('occasion', '')),
                "skin_tone": str(row.get('skin_tone', '')),
                "handle": str(row.get('handle', '')) # <--- ADDED HANDLE HERE
            }

            vectors_batch.append({
                "id": str(row['id']),
                "values": embedding,
                "metadata": metadata
            })
            
            print(f"[{len(vectors_batch)}/{len(df_new)}] Prepared: {row.get('title', '')[:20]}...")

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