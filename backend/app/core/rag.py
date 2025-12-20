import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "gift-concierge-v1")

if not GOOGLE_API_KEY or not PINECONE_API_KEY:
    print("❌ ERROR: Missing API Keys in rag.py")

genai.configure(api_key=GOOGLE_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

def search_products(query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    1. Converts query to vector.
    2. Searches Pinecone.
    3. Returns 'top_k' results.
    """
    print(f"🔍 RAG: Searching for -> '{query_text}' (Limit: {top_k})")
    
    try:
        # 1. Generate Embedding
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query_text,
            task_type="retrieval_query"
        )
        query_vector = result['embedding']

        # 2. Search Pinecone
        # We allow chat.py to decide how many to fetch (top_k)
        search_results = index.query(
            vector=query_vector,
            top_k=top_k, 
            include_metadata=True
        )

        # 3. Format Results
        products = []
        for match in search_results['matches']:
            meta = match['metadata']
            
            product = {
                "id": meta.get("id"),
                "title": meta.get("title"),
                "price": meta.get("price"),
                "description": meta.get("description", ""),
                "style": meta.get("style", ""),
                "image_url": meta.get("image_url", ""),
                "score": match['score']
            }
            products.append(product)

        print(f"✅ RAG: Found {len(products)} matches.")
        return products

    except Exception as e:
        print(f"❌ RAG ERROR: {str(e)}")
        return []