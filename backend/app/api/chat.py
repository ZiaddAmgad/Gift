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
    
    # Detect intent - check for minimum keywords first
    if any(w in clean_text for w in ["over", "above", "more than", "start", "min"]):
        return {'amount': amount, 'type': 'min'}
    
    # Check for maximum keywords
    if any(w in clean_text for w in ["under", "below", "less than"]):
        return {'amount': amount, 'type': 'max'}
    
    # Check for approximate keywords
    if any(w in clean_text for w in ["about", "around", "approx", "close to"]):
        return {'amount': amount, 'type': 'approx'}
    
    # If a number exists but no keywords, default to 'approx' (safer than max)
    return {'amount': amount, 'type': 'approx'}

def _get_gemini_chat_model():
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY must be set in the environment.")
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # ADD CONFIGURATION
    generation_config = genai.types.GenerationConfig(
        max_output_tokens=300, # Increased to 300 (Safe for chatty replies)
        temperature=0.7
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
                "volume_vibe": None, # Now supports: Simple, Glamorous, Artistic, Classic
                "budget": None
            },
        }
    return SESSIONS[session_id]

def reset_session(session_id: str) -> Dict[str, Any]:
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    return get_session(session_id)

def clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return text

def extract_slots_and_reply(session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    info = session["info"]
    
    # --- PROMPT WITH EXPANDED VIBE CHECK ---
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
        
        # METAL MAPPING (With I dont know fallback)
        "- 'Gold' -> metal_preference: 'Gold'\n"
        "- 'Silver', 'White', 'Platinum' -> metal_preference: 'Silver'\n"
        "- 'Not sure', 'Idk', 'Mix', 'Both', 'No idea', 'I dont know', 'I don't know' -> metal_preference: 'Any'\n"
        
        # STYLE MAPPING (Expanded to cover Vision Attributes)
        "- 'Simple', 'Clean', 'Modern', 'Minimalist' -> volume_vibe: 'Simple'\n"
        "- 'Bold', 'Glamorous', 'Sparkly', 'Statement', 'Party' -> volume_vibe: 'Glamorous'\n"
        "- 'Artistic', 'Nature', 'Boho', 'Flowers', 'Vintage' -> volume_vibe: 'Artistic'\n"
        "- 'Classic', 'Elegant', 'Traditional' -> volume_vibe: 'Classic'\n"
        "- 'Not sure', 'Idk', 'Safe', 'Play it safe', 'I dont know', 'I don't know' -> volume_vibe: 'Safe_Fallback'\n\n"

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
        response = model.generate_content(system_prompt)
        raw_text = response.text or ""
        cleaned_text = clean_json_text(raw_text)
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"ERROR GEMINI: {str(e)}")
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
    slot_result = extract_slots_and_reply(session, user_text)

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
        
        # --- 2. BUILD QUERY (Mapping User input to Vision Tags) ---
        query_parts = []
        
        # Recipient
        query_parts.append(f"Recipient: {info['recipient']}")

        # Metal (Handle 'Any' -> Neutral Skin Tone / Mixed)
        metal_pref = info['metal_preference']
        if metal_pref == 'Any':
            query_parts.append("Material: Gold, Silver, Rose Gold, Mixed. Skin Tone: Neutral")
        elif metal_pref == 'Gold':
            query_parts.append("Material: Gold, Gold Plated. Skin Tone: Warm Tones")
        elif metal_pref == 'Silver':
            query_parts.append("Material: Silver, Sterling Silver, White Gold. Skin Tone: Cool Tones")
        
        # Occasion (Maps to Usage)
        occ = info['event_occasion']
        if occ == 'Anniversary':
            query_parts.append("Occasion: Party, Anniversary. Attributes: Romantic, Love, Eternity")
        elif occ == 'Holiday':
            query_parts.append("Occasion: Party, Holiday. Attributes: Festive, Sparkly, Gift")
        elif occ == 'Birthday':
             query_parts.append("Occasion: Party, Birthday. Attributes: Celebration, Stylish")
        elif occ == 'Just Because':
            query_parts.append("Occasion: Daily, Gift. Attributes: Affordable, Casual")
            
        # VIBE MAPPING (The Big Update to cover your Vision Attributes)
        vibe = info['volume_vibe']
        
        if vibe == 'Simple':
            # Covers: Minimalist, Modern, Geometric, Dainty, Industrial
            query_parts.append("Style: Minimalist, Modern, Geometric, Dainty, Industrial. Gemstone: None")
            
        elif vibe == 'Glamorous':
            # Covers: Bold, Statement, Art Deco, Trendy, Zircon
            query_parts.append("Style: Bold, Statement, Art Deco, Trendy. Gemstone: Diamond, Zircon, Crystal")
            
        elif vibe == 'Artistic':
            # Covers: Boho, Nature, Vintage, Mixed
            query_parts.append("Style: Boho, Nature, Vintage, Romantic. Material: Mixed, Beaded")
            
        elif vibe == 'Classic':
            # Covers: Classic, Traditional, Pearl
            query_parts.append("Style: Classic, Traditional, Romantic. Gemstone: Pearl")
            
        elif vibe == 'Safe_Fallback': 
            # Covers: Classic, Minimalist (The safest options)
            query_parts.append("Style: Classic, Minimalist, Dainty. Occasion: Daily, Gift")

        final_query = ". ".join(query_parts)
        print(f"🔎 QUERY: {final_query} | Budget: {budget_info}")

        # --- 3. SEARCH & FILTER ---
        # Perform Vector Search first to get candidates (increase match_count to 20)
        products = search_products(final_query, match_count=20)
        
        # Create a list valid_products by filtering the candidates
        valid_products = []
        for p in products:
            try:
                price = float(p.get('price', 0))
                # Apply budget filtering based on type
                if budget_type == 'min':
                    # Keep products where price >= amount
                    if price >= budget_amount:
                        valid_products.append(p)
                elif budget_type == 'max':
                    # Keep products where price <= amount
                    if price <= budget_amount:
                        valid_products.append(p)
                elif budget_type == 'approx':
                    # Keep products where price <= (amount * 1.4)
                    max_price = budget_amount * 1.4
                    if price <= max_price:
                        valid_products.append(p)
                elif budget_type == 'none':
                    # No budget filter
                    valid_products.append(p)
            except:
                continue

        # --- 4. SOFT FALLBACK LOGIC ---
        budget_ignored = False
        
        # If valid_products is empty AFTER filtering
        if not valid_products:
            # Set valid_products = products[:3] (Take the top 3 style matches, ignoring price)
            valid_products = products[:3]
            budget_ignored = True
        else:
            # Set valid_products = valid_products[:3]
            valid_products = valid_products[:3]
            budget_ignored = False

        # --- 5. UPDATE THE FINAL MESSAGE ---
        final_message = ""
        
        if budget_ignored:
            # If budget_ignored is True: Prepend text indicating budget was ignored
            final_message = "I couldn't find an exact match around that price, but here are the best options matching the style you described:"
        else:
            # Else: Use the standard "I found this [Title]..." message
            if valid_products:
                p = valid_products[0]
                metal_text = info['metal_preference']
                if metal_text == 'Any': metal_text = "jewelry"
                
                final_message = (
                    f"I found this {p['title']}! It matches the {info['volume_vibe'].lower()} style and is perfect for {info['event_occasion']}."
                )
            else:
                final_message = "I couldn't find any matching products. Please try adjusting your preferences."

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