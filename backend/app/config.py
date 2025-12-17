# Loads API keys and config from .env
import os
from dotenv import load_dotenv

load_dotenv()

# Google Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Database URL (optional, not used directly in Supabase client)
DATABASE_URL = os.getenv("DATABASE_URL")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
