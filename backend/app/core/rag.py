import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from google import genai  # new SDK
from pinecone import Pinecone

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "gift-concierge-v1")

if not GOOGLE_API_KEY or not PINECONE_API_KEY:
    print("❌ ERROR: Missing API Keys in rag.py")

# Initialize new google.genai client
genai_client = genai.Client(api_key=GOOGLE_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# UPDATED: Added 'namespace' argument (Default to empty string if not provided)
def search_products(query_text: str, top_k: int = 5, namespace: str = "") -> List[Dict[str, Any]]:
    """
    1. Converts query to vector.
    2. Searches Pinecone within a specific Client Namespace.
    3. Returns 'top_k' results.
    """
    print(f"🔍 RAG: Searching '{query_text}' in Namespace: '{namespace}'")
    
    try:
        # 1. Generate Embedding using new google.genai
        result = genai_client.models.embed_content(
            model="models/text-embedding-004",
            contents=query_text,
        )
        query_vector = result.embeddings[0].values

        # 2. Search Pinecone (With Namespace)
        # If namespace is "", Pinecone searches the default namespace.
        search_results = index.query(
            vector=query_vector,
            top_k=top_k, 
            include_metadata=True,
            namespace=namespace # <--- CRITICAL UPDATE
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
                "handle": meta.get("handle", ""),
                "score": match['score']
            }
            products.append(product)

        print(f"✅ RAG: Found {len(products)} matches.")
        return products

    except Exception as e:
        print(f"❌ RAG ERROR: {str(e)}")
        return []