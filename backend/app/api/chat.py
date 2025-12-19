import json
import re
from typing import Dict, Any, Optional

import google.generativeai as genai
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import GOOGLE_API_KEY
from app.core.rag import search_products

router = APIRouter()

# --- DATA MODELS ---
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

# --- IN-MEMORY SESSION STORE ---
SESSIONS: Dict[str, Dict[str, Any]] = {}

# --- HELPER: SMART BUDGET PARSER ---
def parse_budget_logic(text: str) -> Dict[str, Any]:
    """
    Analyzes budget text for amount AND intent (Over vs Under vs Approx).
    Returns: {'amount': float, 'type': 'min'|'max'|'approx'|'none'}
    """
    if not text: return {'amount': 0, 'type': 'none'}
    
    clean_text = text.lower().replace(",", "")
    numbers = re.findall(r'\d+', clean_text)
    if not numbers: return {'amount': 0, 'type': 'none'}
    
    # Get the primary number
    amount = float(max(numbers, key=lambda x: float(x)))
    
    # Detect intent
    if any(w in clean_text for w in ["over", "above", "more than", "start", "min"]):
        return {'amount': amount, 'type': 'min'}
    
    if any(w in clean_text for w in ["under", "below", "less than"]):
        return {'amount': amount, 'type': 'max'}
    
    # Default to approx
    return {'amount': amount, 'type': 'approx'}

# --- HELPER: ROBUST JSON CLEANER ---
def clean_json_text(text: str) -> str:
    """
    Uses Regex to find the JSON object {...} inside the text,
    ignoring any conversational garbage before or after.
    """
    text = text.strip()
    # Find the first '{' and the last '}'
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text

def _get_gemini_chat_model():
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY must be set in the environment.")
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # CRITICAL FIX: Force JSON response type
    generation_config = genai.types.GenerationConfig(
        max_output_tokens=300,
        temperature=0.7,
        response_mime_type="application/json"
    )
    
    return genai.GenerativeModel(
        "models/gemini-2.5-flash", 
        generation_config=generation_config
    )

def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "step": "start",
            "info": {
                "recipient": None,
                "event_occasion": None,
                "metal_preference": None,
                "volume_vibe": None,
                "budget": None
            },
        }
    return SESSIONS[session_id]

def reset_session(session_id: str) -> Dict[str, Any]:
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    return get_session(session_id)

async def extract_slots_and_reply(session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    info = session["info"]
    
    system_prompt = (
        "You are an AI Jewelry Concierge. Extract 5 slots based on the user's answers.\n"
        "Current Info: " + json.dumps(info) + "\n\n"
        "User Message: '" + user_message + "'\n\n"
        
        "QUESTION STRATEGY (Strict Order):\n"
        "1. Recipient: If missing, ask 'Who are you shopping for?'\n"
        "2. Occasion: If 'event_occasion' is missing, ask 'What is the occasion? (Birthday, Anniversary, Holiday, or Just Because?)'\n"
        "3. Metal: If 'metal_preference' is missing, ask 'Does she usually wear Gold or Silver? (It's okay to say you don't know!)'\n"
        "4. Style: If 'volume_vibe' is missing, ask: 'How would you describe her style?\n"
        "   (A) Simple & Clean\n"
        "   (B) Bold & Glamorous\n"
        "   (C) Artistic & Nature-loving\n"
        "   (D) Classic & Elegant\n"
        "   (If you dont know we can play it safe?)'\n"
        "5. Budget: If 'budget' is missing, ask 'I think I have an idea of what she likes to wear now. Do you have a certain budget in mind?'\n"
        "6. If all filled -> Set 'reply' to 'SEARCH_READY'.\n\n"
        
        "MAPPING LOGIC:\n"
        "- 'Anniversary', 'Wedding' -> event_occasion: 'Anniversary'\n"
        "- 'Birthday', 'Bday' -> event_occasion: 'Birthday'\n"
        "- 'Holiday', 'Eid', 'Christmas', 'Easter' -> event_occasion: 'Holiday'\n"
        "- 'Just because', 'Gift' -> event_occasion: 'Just Because'\n"
        "- 'Gold' -> metal_preference: 'Gold'\n"
        "- 'Silver', 'White', 'Platinum' -> metal_preference: 'Silver'\n"
        "- 'Not sure', 'Idk', 'Mix', 'Both', 'No idea' -> metal_preference: 'Any'\n"
        "- 'Simple', 'Clean', 'Modern', 'Minimalist' -> volume_vibe: 'Simple'\n"
        "- 'Bold', 'Glamorous', 'Sparkly', 'Statement', 'Party' -> volume_vibe: 'Glamorous'\n"
        "- 'Artistic', 'Nature', 'Boho', 'Flowers', 'Vintage' -> volume_vibe: 'Artistic'\n"
        "- 'Classic', 'Elegant', 'Traditional' -> volume_vibe: 'Classic'\n"
        "- 'Not sure', 'Idk', 'Safe', 'Play it safe', 'I dont know' -> volume_vibe: 'Safe_Fallback'\n\n"

        "OUTPUT FORMAT (JSON ONLY):\n"
        "{\n"
        '  "recipient": "string or null",\n'
        '  "event_occasion": "string or null",\n'
        '  "metal_preference": "string or null",\n'
        '  "volume_vibe": "string or null",\n'
        '  "budget": "string or null",\n'
        '  "reply": "string"\n'
        "}"
    )

    model = _get_gemini_chat_model()
    
    try:
        # We use async to avoid blocking
        response = await model.generate_content_async(system_prompt)
        raw_text = response.text or ""
        
        # Clean the text before parsing
        cleaned_text = clean_json_text(raw_text)
        return json.loads(cleaned_text)
        
    except Exception as e:
        print(f"ERROR GEMINI: {str(e)}")
        # If parsing fails, just ask for recipient as fallback
        return {
            "reply": "I'm having a little trouble connecting. Could you tell me who the gift is for?",
            **info
        }

@router.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    user_text = chat_message.message.strip()
    session_id = chat_message.session_id or "default-session"
    session = get_session(session_id)

    # Greeting
    if user_text.lower() in {"hi", "hello", "hey", "start", "restart"}:
        session = reset_session(session_id)
        return {
            "session_id": session_id,
            "message": "Welcome! I can help you find the perfect gift. Who are you shopping for today?",
            "slots": session["info"],
            "products": []
        }

    # Extraction
    slot_result = await extract_slots_and_reply(session, user_text)

    # Update Memory
    info = session["info"]
    info["recipient"] = slot_result.get("recipient") or info["recipient"]
    info["event_occasion"] = slot_result.get("event_occasion") or info["event_occasion"]
    info["metal_preference"] = slot_result.get("metal_preference") or info["metal_preference"]
    info["volume_vibe"] = slot_result.get("volume_vibe") or info["volume_vibe"]
    info["budget"] = slot_result.get("budget") or info["budget"]
    
    reply_text = slot_result.get("reply", "")

    # Check Ready
    is_ready = (reply_text == "SEARCH_READY") or (
        info["recipient"] and 
        info["event_occasion"] and 
        info["metal_preference"] and 
        info["volume_vibe"] and
        info["budget"]
    )

    if is_ready:
        # --- 1. PARSE BUDGET ---
        budget_str = str(info["budget"]).lower()
        budget_info = parse_budget_logic(budget_str)
        budget_amount = budget_info['amount']
        budget_type = budget_info['type']
        
        # --- 2. BUILD QUERY ---
        query_parts = [f"Recipient: {info['recipient']}"]

        # Metal
        metal_pref = info['metal_preference']
        if metal_pref == 'Any':
            query_parts.append("Material: Gold, Silver, Rose Gold, Mixed. Skin Tone: Neutral")
        elif metal_pref == 'Gold':
            query_parts.append("Material: Gold, Gold Plated. Skin Tone: Warm Tones")
        elif metal_pref == 'Silver':
            query_parts.append("Material: Silver, Sterling Silver, White Gold. Skin Tone: Cool Tones")
        
        # Occasion
        occ = info['event_occasion']
        if occ == 'Anniversary':
            query_parts.append("Occasion: Party, Anniversary. Attributes: Romantic, Love, Eternity")
        elif occ == 'Holiday':
            query_parts.append("Occasion: Party, Holiday. Attributes: Festive, Sparkly, Gift")
        elif occ == 'Birthday':
             query_parts.append("Occasion: Party, Birthday. Attributes: Celebration, Stylish")
        elif occ == 'Just Because':
            query_parts.append("Occasion: Daily, Gift. Attributes: Affordable, Casual")
            
        # Vibe
        vibe = info['volume_vibe']
        if vibe == 'Simple':
            query_parts.append("Style: Minimalist, Modern, Geometric, Dainty. Gemstone: None")
        elif vibe == 'Glamorous':
            query_parts.append("Style: Bold, Statement, Art Deco, Trendy. Gemstone: Diamond, Zircon")
        elif vibe == 'Artistic':
            query_parts.append("Style: Boho, Nature, Vintage, Romantic. Material: Mixed")
        elif vibe == 'Classic':
            query_parts.append("Style: Classic, Traditional, Romantic. Gemstone: Pearl")
        elif vibe == 'Safe_Fallback': 
            query_parts.append("Style: Classic, Minimalist, Dainty. Occasion: Daily")

        final_query = ". ".join(query_parts)
        print(f"🔎 QUERY: {final_query} | Budget: {budget_info}")

        # --- 3. SEARCH & FILTER ---
        products = search_products(final_query, match_count=20)
        
        valid_products = []
        min_store_price = 300.0 
        
        for p in products:
            try:
                price = float(p.get('price', 0))
                if budget_type == 'min':
                    if price >= budget_amount:
                        valid_products.append(p)
                elif budget_type == 'max':
                    if price <= (budget_amount * 1.10):
                        valid_products.append(p)
                elif budget_type == 'approx':
                    min_price = budget_amount * 0.6
                    max_price = budget_amount * 1.4
                    if price >= min_price and price <= max_price:
                        valid_products.append(p)
                else:
                    valid_products.append(p)
            except:
                continue

        # --- 4. FALLBACK LOGIC ---
        final_message = ""
        
        if not valid_products and budget_type == 'max' and budget_amount < min_store_price:
            final_message = f"I'd love to help, but our high-quality pieces start around {min_store_price} EGP. Here are our most affordable options:"
            valid_products = sorted(products, key=lambda x: float(x.get('price', 0)))[:3]
        
        elif not valid_products:
             final_message = "I couldn't find an exact match within that budget, but here are the closest options to that style:"
             valid_products = products[:3]
        
        else:
            valid_products = valid_products[:3]
            p = valid_products[0]
            final_message = (
                f"I found this {p['title']}! It matches the {info['volume_vibe'].lower()} style and is perfect for {info['event_occasion']}."
            )

        return {
            "session_id": session_id,
            "message": final_message,
            "products": valid_products
        }

    return {
        "session_id": session_id,
        "message": reply_text,
        "slots": session["info"],
        "products": []
    }