import os
import json
import google.generativeai as genai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.core.rag import search_products

router = APIRouter()

# --- CONFIGURATION ---
if not os.getenv("GOOGLE_API_KEY"):
    raise RuntimeError("GOOGLE_API_KEY is not set.")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel(
    'models/gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

# --- DATA MODELS ---
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    text_bubbles: List[str]
    products: Optional[List[dict]] = []

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are "Fortuna", a warm, expert Jewelry Concierge.
Your Goal: Help the user find a gift using a specific conversation flow.
LANGUAGE: Strictly English. No Franco-Arabic. No Emojis.

--- CONVERSATION FLOW ---
1. **Recipient:** First, find out who it is for.
2. **Occasion check:**
   - If user says generic "Gift", ask: "Is there a special occasion you are celebrating, or just a nice surprise?"
   - DO NOT move to Material until you know if there is a specific Event (Birthday, Anniversary) or if it is definitely "Just Because".
3. **Occasion & Material:** 
   - Once Occasion is specific (or confirmed "Just Because"), REACT with empathy.
   - Then, in a separate bubble, ask: "To help me narrow it down, does she usually prefer **Gold or Silver**? (It's completely okay to say you're not sure!)"
4. **The Style Menu (Vibe Check):**
   - Once Material is known, ask for her **Style** using these EXACT options:
     (A) Simple & Clean
     (B) Bold & Beautiful
     (C) Artistic & Nature-Loving
     (D) Classic & Elegant
     (E) Cozy & Comfortable
     (F) Trendy & Fashionable
   - *If user asks for explanation:* You MUST return exactly 3 separate strings in 'reply_bubbles'. 
     - String 1: Explain A & B.
     - String 2: Explain C & D.
     - String 3: Explain E & F.
5. **The "Hero" Search:**
   - If you have Recipient + Occasion + Material + Style -> SEARCH.
   - Return ONLY the #1 best matching product initially.
6. **Iteration:**
   - If the user asks for "more", "different", or says "I don't like it", return 3 products.

--- STYLE EXPLANATIONS (Strictly split into 3 bubbles) ---
Bubble 1 Content:
(A) Simple & Clean: She likes things neat and calm. Not too many colors or stuff.
(B) Bold & Beautiful: She loves shiny things and being noticed.

Bubble 2 Content:
(C) Artistic & Nature-Loving: She likes creative things and nature. Nothing boring or plain.
(D) Classic & Elegant: She likes things that always look nice like old-fashion and classy looks.

Bubble 3 Content:
(E) Cozy & Comfortable: She loves soft, warm, comfy things. Feeling relaxed is important.
(F) Trendy & Fashionable: She likes what everyone is wearing right now and is always up to date.

--- TAG MAPPING LOGIC ---
**A. Recipient Mapping:**
- Mom / Grandma -> "Traditional, Classic, Vintage"
- Wife / Partner -> "Romantic, Classic, Statement"
- Girlfriend -> "Romantic, Trendy, Dainty"
- Sister / Friend -> "Trendy, Boho, Modern"
- Daughter / Niece -> "Dainty, Modern, Minimalist"

**B. Occasion Mapping:**
- Daily / Just Because -> Occasion: "Daily" | Style: "Minimalist, Dainty"
- Party / Wedding -> Occasion: "Party" | Style: "Statement, Bold"
- Valentine -> Occasion: "Valentine" | Style: "Romantic"
- Anniversary -> Occasion: "Anniversary" | Style: "Romantic, Classic"
- Mother's Day -> Occasion: "Mother's Day" | Style: "Traditional"
- Holiday -> Occasion: "Holiday" | Style: "Statement"
- Gift -> Occasion: "Gift" | Style: ""

**C. Material Mapping:**
- Gold -> "Gold, Gold Plated, Rose Gold"
- Silver -> "Silver, Sterling Silver, White Gold, Platinum"
- Both / Mix -> "Gold, Silver, Mixed"
- Unsure -> "Gold, Silver, Rose Gold, White Gold, Gold Plated, Sterling Silver, Platinum, Enamel, Leather, Cord, Pearl, Beaded, Mixed"

**D. Style Options:**
- A -> Style: "Minimalist, Modern, Geometric, Dainty" | Gemstone: "None"
- B -> Style: "Bold, Statement, Art Deco" | Gemstone: "Zircon, Crystal, Diamond"
- C -> Style: "Boho, Nature, Vintage, Romantic" | Material: "Enamel, Mixed, Beaded" | Gemstone: "Turquoise, Emerald"
- D -> Style: "Classic, Traditional, Romantic" | Gemstone: "Pearl, Sapphire"
- E -> Style: "Boho, Minimalist" | Material: "Leather, Cord, Beaded" | Gemstone: "Onyx, Turquoise"
- F -> Style: "Trendy, Modern, Industrial" | Gemstone: "Zircon"

--- OUTPUT FORMAT (JSON) ---
{
    "reply_bubbles": ["String 1", "String 2"],
    "search_params": {
        "ready_to_search": boolean,
        "recipient_tags": "...",
        "occasion_tags": "...",
        "material_tags": "...",
        "style_tags": "...",
        "gemstone_tags": "...",
        "product_count": 1 
    }
}
"""

@router.post("/message", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        recent_messages = request.messages[-15:]
        conversation_text = ""
        for msg in recent_messages:
            role_label = "User" if msg.role == "user" else "Assistant"
            conversation_text += f"{role_label}: {msg.content}\n"

        prompt = f"{SYSTEM_PROMPT}\n\n--- CONVERSATION HISTORY ---\n{conversation_text}\n\n--- JSON RESPONSE ---"
        response = await model.generate_content_async(prompt)
        
        try:
            ai_data = json.loads(response.text)
        except json.JSONDecodeError:
            return ChatResponse(text_bubbles=["I'm listening! Could you tell me a bit more?"])

        bubbles = ai_data.get("reply_bubbles", [])
        if not bubbles: bubbles = ["Let me check on that for you."]
        
        params = ai_data.get("search_params", {})
        products = []

        if params.get("ready_to_search", False):
            query_parts = [
                params.get('style_tags', ''),
                params.get('material_tags', ''),
                params.get('gemstone_tags', ''),
                params.get('occasion_tags', ''),
                params.get('recipient_tags', '')
            ]
            
            query = " ".join([p for p in query_parts if p]).strip()
            count = params.get("product_count", 1)
            print(f"🔎 Generated Query: {query} (Requesting: {count})")
            
            # Fetch 5 candidates
            raw_results = search_products(query_text=query, top_k=5)
            
            if raw_results:
                if count == 1:
                    # Hero Search: Top 1
                    products = raw_results[:1]
                elif count == 3:
                    # Iteration Search: Skip the first one, return next 3
                    products = raw_results[1:4]
            else:
                bubbles.append("I couldn't find an exact match, but here are our most popular pieces.")
                products = search_products(query_text="Best seller", top_k=3)

        return ChatResponse(text_bubbles=bubbles, products=products)

    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        return ChatResponse(text_bubbles=["I'm having a brief connection issue. Please say that again?"])