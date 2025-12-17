import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# CRITICAL: This must match the index name used in ingest.py
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "gift-concierge-v1")

# Initialize Clients
if not GOOGLE_API_KEY or not PINECONE_API_KEY:
    print("❌ ERROR: Missing API Keys in rag.py")

genai.configure(api_key=GOOGLE_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

def search_products(query: str, match_count: int = 1) -> List[Dict[str, Any]]:
    """
    1. Converts the user's natural language query into a Vector.
    2. Sends that Vector to Pinecone to find similar products.
    3. Returns the product metadata.
    """
    print(f"🔍 RAG: Searching for -> '{query}'")
    
    try:
        # 1. Generate Embedding for the query
        # CRITICAL: task_type="retrieval_query" optimizes the vector for searching
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        query_vector = result['embedding']

        # 2. Search Pinecone
        # We fetch top 3 to ensure quality, then slice to match_count
        search_results = index.query(
            vector=query_vector,
            top_k=3, 
            include_metadata=True
        )

        # 3. Format Results
        products = []
        for match in search_results['matches']:
            meta = match['metadata']
            
            # Clean up the object to make it easy for the frontend
            product = {
                "id": meta.get("id"),
                "title": meta.get("title"),
                "price": meta.get("price"),
                "description": meta.get("description", ""),
                "style": meta.get("style", ""),
                "image_url": meta.get("image_url", ""),
                "score": match['score'] # How confident the AI is (0.0 to 1.0)
            }
            products.append(product)

        print(f"✅ RAG: Found {len(products)} matches.")
        
        # Return only the requested amount (1 product as per new logic)
        return products[:match_count]

    except Exception as e:
        print(f"❌ RAG ERROR: {str(e)}")
        return []