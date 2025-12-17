import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# 1. Load the key from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
api_key = os.getenv("PINECONE_API_KEY")

if not api_key:
    print("❌ Error: PINECONE_API_KEY not found in .env file")
    exit(1)

# 2. Connect to Pinecone
print("🔌 Connecting to Pinecone...")
pc = Pinecone(api_key=api_key)

# 3. Define Index Config
INDEX_NAME = "gift-concierge-v1"
DIMENSIONS = 768 # Crucial: Must match Google's text-embedding-004

# 4. Create Index if it doesn't exist
existing_indexes = [i.name for i in pc.list_indexes()]

if INDEX_NAME not in existing_indexes:
    print(f"⚙️ Creating new index: '{INDEX_NAME}' (Dimension: {DIMENSIONS})...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSIONS,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1" # Free tier supports this region
        )
    )
    # Wait a moment for it to initialize
    while not pc.describe_index(INDEX_NAME).status['ready']:
        time.sleep(1)
    print("✅ Index created successfully!")
else:
    print(f"✅ Index '{INDEX_NAME}' already exists. You are good to go.")

# 5. Print Stats
index = pc.Index(INDEX_NAME)
stats = index.describe_index_stats()
print("\n📊 Current Database Stats:")
print(stats)