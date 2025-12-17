import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load the environment variables to get the key
# We assume .env is in backend/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ Error: No GOOGLE_API_KEY found in .env")
else:
    print(f"✅ Found API Key: {api_key[:5]}...")
    try:
        genai.configure(api_key=api_key)
        print("\n🔍 Scanning for available models...")
        found_any = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
                found_any = True
        
        if not found_any:
            print("\n⚠️ No chat models found. Your API key might be restricted or invalid.")
        else:
            print("\n✅ Success! Use one of the names above in your chat.py file.")
            
    except Exception as e:
        print(f"\n❌ API Error: {str(e)}")