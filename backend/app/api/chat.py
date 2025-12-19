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

# --- HELPER: BUDGET PARSER ---
def parse_budget_logic(text: str) -> Dict[str, Any]:
    """Analyzes budget text for amount AND intent (Over vs Under vs Approx)."""
    if not text:
        return {'amount': 0, 'type': 'none'}
    
    clean_text = text.lower().replace(",", "")
    numbers = re.findall(r'\d+', clean_text)
    if not numbers:
        return {'amount': 0, 'type': 'none'}
    
    amount = float(max(numbers, key=lambda x: float(x)))
    
    # Detect intent
    if any(w in clean_text for w in ["over", "above", "more than", "start", "min"]):
        return {'amount': amount, 'type': 'min'}
    if any(w in clean_text for w in ["under", "below", "less than"]):
        return {'amount': amount, 'type': 'max'}
    
    # Default to approx if number exists but no keywords
    return {'amount': amount, 'type': 'approx'}

# --- HELPER: SIMPLE JSON CLEANER ---
def clean_json_text(text: str) -> str:
    """Simple function that just strips markdown backticks."""
    text = text.strip()
    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return text.strip()

# --- HELPER: GET GEMINI MODEL ---
def _get_gemini_chat_model():
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY must be set in the environment.")
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
    generation_config = genai.types.GenerationConfig(
        max_output_tokens=1000,  # Increased to prevent "Unterminated string" errors
        temperature=0.7,
        response_mime_type="application/json"
    )
    
    return genai.GenerativeModel(
        "models/gemini-2.5-flash",
        generation_config=generation_config
    )

# --- HELPER: GET OR CREATE SESSION ---
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

# --- HELPER: RESET SESSION ---
def reset_session(session_id: str) -> Dict[str, Any]:
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    return get_session(session_id)

# --- EXTRACTION FUNCTION ---
async def extract_slots_and_reply(session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    """Extracts slots from user message using Gemini. Returns safe fallback on error."""
    info = session["info"]
    
    system_prompt = (
        "You are an AI Jewelry Concierge. Extract slots based on user answers.\n"
        "Current Info: " + json.dumps(info) + "\n\n"
        "User Message: '" + user_message + "'\n\n"
        
        "QUESTION STRATEGY (Strict Order - Only ask if slot is missing):\n"
        "1. Recipient: If 'recipient' is missing, ask 'Who are you shopping for?'\n"
        "2. Occasion: If 'event_occasion' is missing, ask 'What is the occasion? (Birthday, Anniversary, Holiday, or Just Because?)'\n"
        "3. Metal: If 'metal_preference' is missing, ask 'Does she usually wear Gold or Silver? (It's okay to say you don't know!)'\n"
        "4. Vibe: If 'volume_vibe' is missing, ask 'How would you describe her style?\n"
        "   (A) Simple & Clean\n"
        "   (B) Bold & Glamorous\n"
        "   (C) Artistic & Nature-loving\n"
        "   (D) Classic & Elegant\n"
        "   (Or say 'I don't know' and we'll play it safe!)'\n"
        "5. Budget: If 'budget' is missing, ask 'I think I have an idea of what she likes. Do you have a certain budget in mind?'\n"
        "6. If ALL slots are filled -> Set 'reply' to 'SEARCH_READY'.\n\n"
        
        "MAPPING LOGIC:\n"
        "- 'Anniversary', 'Wedding' -> event_occasion: 'Anniversary'\n"
        "- 'Birthday', 'Bday' -> event_occasion: 'Birthday'\n"
        "- 'Holiday', 'Eid', 'Christmas' -> event_occasion: 'Holiday'\n"
        "- 'Just because', 'Gift' -> event_occasion: 'Just Because'\n"
        "- 'Gold' -> metal_preference: 'Gold'\n"
        "- 'Silver', 'White', 'Platinum' -> metal_preference: 'Silver'\n"
        "- 'Not sure', 'Idk', 'Mix', 'Both', 'I don't know' -> metal_preference: 'Any'\n"
        "- 'Simple', 'Clean', 'Modern', 'Minimalist' -> volume_vibe: 'Simple'\n"
        "- 'Bold', 'Glamorous', 'Sparkly', 'Statement' -> volume_vibe: 'Glamorous'\n"
        "- 'Artistic', 'Nature', 'Boho', 'Flowers', 'Vintage' -> volume_vibe: 'Artistic'\n"
        "- 'Classic', 'Elegant', 'Traditional' -> volume_vibe: 'Classic'\n"
        "- 'Not sure', 'Idk', 'Safe', 'Play it safe', 'I don't know' -> volume_vibe: 'Safe_Fallback'\n\n"
        
        "OUTPUT FORMAT (JSON ONLY):\n"
        "{\n"
        '  "recipient": "...",\n'
        '  "event_occasion": "...",\n'
        '  "metal_preference": "...",\n'
        '  "volume_vibe": "...",\n'
        '  "budget": "...",\n'
        '  "reply": "..."\n'
        "}"
    )
    
    model = _get_gemini_chat_model()
    
    try:
        response = await model.generate_content_async(system_prompt)
        raw_text = response.text or ""
        cleaned_text = clean_json_text(raw_text)
        
        # Try to parse JSON
        parsed = json.loads(cleaned_text)
        
        # Validate that we got a dictionary
        if not isinstance(parsed, dict):
            raise ValueError("Response is not a dictionary")
        
        return parsed
        
    except Exception as e:
        print(f"ERROR GEMINI JSON PARSING: {str(e)}")
        print(f"RAW TEXT: {raw_text[:500] if 'raw_text' in locals() else 'N/A'}")
        
        # Safe Fallback: Return existing slot values and ask user to rephrase
        return {
            "recipient": info.get("recipient"),
            "event_occasion": info.get("event_occasion"),
            "metal_preference": info.get("metal_preference"),
            "volume_vibe": info.get("volume_vibe"),
            "budget": info.get("budget"),
            "reply": "Could you please rephrase that?"
        }

# --- CHAT ENDPOINT ---
@router.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    user_text = chat_message.message.strip()
    session_id = chat_message.session_id or "default-session"
    session = get_session(session_id)
    
    # Greeting / Reset
    if user_text.lower() in {"hi", "hello", "hey", "start", "restart"}:
        session = reset_session(session_id)
        return {
            "session_id": session_id,
            "message": "Welcome! I can help you find the perfect gift. Who are you shopping for today?",
            "slots": session["info"],
            "products": []
        }
    
    # Extract slots
    slot_result = await extract_slots_and_reply(session, user_text)
    
    # Update session memory (only update if new value provided)
    info = session["info"]
    if slot_result.get("recipient"):
        info["recipient"] = slot_result["recipient"]
    if slot_result.get("event_occasion"):
        info["event_occasion"] = slot_result["event_occasion"]
    if slot_result.get("metal_preference"):
        info["metal_preference"] = slot_result["metal_preference"]
    if slot_result.get("volume_vibe"):
        info["volume_vibe"] = slot_result["volume_vibe"]
    if slot_result.get("budget"):
        info["budget"] = slot_result["budget"]
    
    reply_text = slot_result.get("reply", "")
    
    # Check if all slots are ready
    is_ready = (reply_text == "SEARCH_READY") or (
        info["recipient"] and
        info["event_occasion"] and
        info["metal_preference"] and
        info["volume_vibe"] and
        info["budget"]
    )
    
    # If not ready, return the reply and current slots
    if not is_ready:
        return {
            "session_id": session_id,
            "message": reply_text,
            "slots": session["info"],
            "products": []
        }
    
    # --- SEARCH LOGIC (All slots filled) ---
    # Parse budget
    budget_info = parse_budget_logic(str(info["budget"]))
    budget_amount = budget_info['amount']
    budget_type = budget_info['type']
    
    # Build query
    query_parts = [f"Recipient: {info['recipient']}"]
    
    # Metal mapping
    metal_pref = info['metal_preference']
    if metal_pref == 'Any':
        query_parts.append("Material: Gold, Silver, Rose Gold, Mixed. Skin Tone: Neutral")
    elif metal_pref == 'Gold':
        query_parts.append("Material: Gold, Gold Plated. Skin Tone: Warm Tones")
    elif metal_pref == 'Silver':
        query_parts.append("Material: Silver, Sterling Silver, White Gold. Skin Tone: Cool Tones")
    
    # Occasion mapping
    occ = info['event_occasion']
    if occ == 'Anniversary':
        query_parts.append("Occasion: Party, Anniversary. Attributes: Romantic, Love, Eternity")
    elif occ == 'Holiday':
        query_parts.append("Occasion: Party, Holiday. Attributes: Festive, Sparkly, Gift")
    elif occ == 'Birthday':
        query_parts.append("Occasion: Party, Birthday. Attributes: Celebration, Stylish")
    elif occ == 'Just Because':
        query_parts.append("Occasion: Daily, Gift. Attributes: Affordable, Casual")
    
    # Vibe mapping
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
    
    # Search products
    products = search_products(final_query, match_count=20)
    
    # Filter by budget
    valid_products = []
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
                max_price = budget_amount * 1.4
                if price <= max_price:
                    valid_products.append(p)
            else:  # 'none'
                valid_products.append(p)
        except:
            continue
    
    # Fallback logic
    final_message = ""
    min_store_price = 300.0
    
    if not valid_products and budget_type == 'max' and budget_amount < min_store_price:
        final_message = f"I'd love to help, but our high-quality pieces start around {min_store_price} EGP. Here are our most affordable options:"
        valid_products = sorted(products, key=lambda x: float(x.get('price', 0)))[:3]
    elif not valid_products:
        final_message = "I couldn't find an exact match within that budget, but here are the closest options to that style:"
        valid_products = products[:3]
    else:
        valid_products = valid_products[:3]
        if valid_products:
            p = valid_products[0]
            final_message = f"I found this {p['title']}! It matches the {info['volume_vibe'].lower()} style and is perfect for {info['event_occasion']}."
        else:
            final_message = "I couldn't find any matching products. Please try adjusting your preferences."
    
    return {
        "session_id": session_id,
        "message": final_message,
        "products": valid_products
    }
