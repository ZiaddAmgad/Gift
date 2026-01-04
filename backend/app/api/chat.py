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

# 1. Text Chat Model
text_model = genai.GenerativeModel(
    'models/gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

# 2. Vision Model
vision_model = genai.GenerativeModel(
    'models/gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

# --- DATA MODELS ---
class Message(BaseModel):
    role: str
    content: str
    image: Optional[str] = None 

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    text_bubbles: List[str]
    products: Optional[List[dict]] = []
    allow_image: Optional[bool] = False 

# --- 1. VISION SYSTEM PROMPT ---
VISION_PROMPT = """
You are an expert Jewelry Stylist. Analyze this image to find the perfect gift.

**TASK:**
1. Analyze the woman's Skin Tone, Style, and probable Material preferences.
2. EXTRACT tags strictly from the lists below.
3. GENERATE a 'friendly_reply' that is warm but CONCISE (Max 3 sentences).

**STRICT TAG OPTIONS:**
- Material: "Gold, Silver, Rose Gold, White Gold, Gold Plated, Sterling Silver, Platinum, Enamel, Leather, Cord, Pearl, Beaded, Mixed"
- Style: "Minimalist, Boho, Vintage, Bold, Statement, Art Deco, Modern, Classic, Romantic, Geometric, Nature, Dainty, Industrial, Traditional, Trendy"
- Gemstone: "Diamond, Zircon, Pearl, Turquoise, Onyx, Crystal, Emerald, Ruby, Sapphire, None"
- Skin Tone: "Cool Tones, Warm Tones, Neutral"
- Occasion: "Daily, Party, Valentine, Anniversary, Mother's Day, Holiday, Gift"

**OUTPUT FORMAT (JSON):**
{
    "material": "...",
    "style": "...",
    "gemstone": "...",
    "skin_tone": "...",
    "friendly_reply": "..." 
}
"""

# --- 2. TEXT SYSTEM PROMPT (UPDATED: 4 Products + Stop) ---
SYSTEM_PROMPT = """
You are "Fortuna", a warm, expert Jewelry Concierge.
Your Goal: Help the user find a gift using a specific conversation flow.
LANGUAGE: Strictly English. No Franco-Arabic. No Emojis.

--- CONVERSATION FLOW ---
1. **Recipient:** First, find out who it is for.
2. **Occasion check:**
   - If generic "Gift", ask: "Is there a special occasion...?"
   - Confirm event or "Just Because" before moving on.
3. **Occasion Reaction:** 
   - Once Occasion is specific, REACT with empathy.
4. **The Image Offer (New Step):**
   - After reacting, ask: "If you want, you can share a photo that shows her style or we can just keep chatting. Totally up to you"
   - **CRITICAL:** Set "allow_image": true in the JSON response for this step ONLY.
   - If they say yes/upload -> Vision Model takes over.
   - If they say no -> Continue to Material question below.
5. **Material Question (If no image):** 
   - Ask: "To help me narrow it down, does she usually prefer **Gold or Silver**? (It's completely okay to say you're not sure!)"
   - "allow_image": false
6. **The Style Menu (Vibe Check):**
   - Once Material is known, ask for Style.
   - **FORMATTING:** Return this as ONE bubble. Use '\\n' to separate lines.
   - Text must look like this:
     "Think about her favorite outfits or her daily look. Which of these categories best describes her fashion sense? (You can choose multiple letters!)"
     
     (A) Simple & Clean
     (B) Bold & Beautiful
     (C) Artistic & Nature-Loving
     (D) Classic & Elegant
     (E) Cozy & Comfortable
     (F) Trendy & Fashionable"
7. **Style Explanations (If asked):**
   - Return exactly 3 separate bubbles. Use '\\n\\n' to separate items within a bubble.
   - Bubble 1: "(A) Simple & Clean: ... \\n\\n(B) Bold & Beautiful: ..."
   - Bubble 2: "(C) Artistic & Nature-Loving: ... \\n\\n(D) Classic & Elegant: ..."
   - Bubble 3: "(E) Cozy & Comfortable: ... \\n\\n(F) Trendy & Fashionable: ..."
   - Use the definitions below.
8. **Final Recommendations (The End):**
   - If Recipient + Occasion + Material + Style are known -> SEARCH.
   - Return **4 products** immediately.
   - Text Reply: "Here are 4 beautiful options that match her style perfectly. I hope you find the perfect gift!"
   - Do NOT ask a follow-up question. The goal is to show products and finish.

--- STYLE DEFINITIONS ---
(A) Simple & Clean: She likes things neat and calm. Not too many colors or stuff.
(B) Bold & Beautiful: She loves shiny things and being noticed.
(C) Artistic & Nature-Loving: She likes creative things and nature. Nothing boring or plain.
(D) Classic & Elegant: She likes things that always look nice like old-fashion and classy looks.
(E) Cozy & Comfortable: She loves soft, warm, comfy things. Feeling relaxed is important.
(F) Trendy & Fashionable: She likes what everyone is wearing right now and is always up to date.

--- TAG MAPPING LOGIC ---
**A. Recipient Mapping:**
- Mom / Grandma / Aunt -> "Traditional, Classic, Vintage"
- Wife / Partner / Fiancee / Fiance -> "Romantic, Classic, Statement"
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
- Both / Mix -> "Gold, Silver, Rose Gold, White Gold, Gold Plated, Sterling Silver, Platinum, Mixed"
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
    "allow_image": boolean, 
    "search_params": {
        "ready_to_search": boolean,
        "recipient_tags": "...",
        "occasion_tags": "...",
        "material_tags": "...",
        "style_tags": "...",
        "gemstone_tags": "...",
        "product_count": 4 
    }
}
"""

@router.post("/message", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        last_msg = request.messages[-1]
        
        # --- PATH A: VISION LOGIC ---
        if last_msg.image:
            print("📸 Image detected. Switching to Vision Model.")
            
            image_data = last_msg.image
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            
            image_part = {
                "mime_type": "image/jpeg", 
                "data": image_data
            }

            response = await vision_model.generate_content_async([VISION_PROMPT, image_part])
            
            try:
                vision_data = json.loads(response.text)
                
                friendly_reply = vision_data.get("friendly_reply", "That's a beautiful photo! I see exactly what might suit her.")
                search_query_tags = f"{vision_data.get('style','')} {vision_data.get('material','')} {vision_data.get('gemstone','')} {vision_data.get('occasion','')} {vision_data.get('skin_tone','')}"
                
                print(f"🔎 Vision Search Query: {search_query_tags}")
                
                # Fetch 6, Return 4
                raw_results = search_products(query_text=search_query_tags, top_k=6)
                
                # Return 4 Products immediately
                final_products = raw_results[:4] if raw_results else []
                
                if not final_products:
                    friendly_reply += " I looked through our collection and these popular pieces seem closest to that style."
                    final_products = search_products("Best seller", top_k=4)
                else:
                    friendly_reply += " Based on that, here are 4 beautiful options."

                return ChatResponse(
                    text_bubbles=[friendly_reply],
                    products=final_products,
                    allow_image=False 
                )

            except Exception as e:
                print(f"❌ Vision Processing Error: {e}")
                return ChatResponse(text_bubbles=["I had a little trouble analyzing that specific photo. Could you tell me a bit about her style using text instead?"])

        # --- PATH B: TEXT LOGIC ---
        else:
            recent_messages = request.messages[-15:]
            conversation_text = ""
            for msg in recent_messages:
                role_label = "User" if msg.role == "user" else "Assistant"
                content = msg.content if msg.content else "[User sent an Image]"
                conversation_text += f"{role_label}: {content}\n"

            prompt = f"{SYSTEM_PROMPT}\n\n--- CONVERSATION HISTORY ---\n{conversation_text}\n\n--- JSON RESPONSE ---"
            response = await text_model.generate_content_async(prompt)
            
            try:
                ai_data = json.loads(response.text)
            except json.JSONDecodeError:
                return ChatResponse(text_bubbles=["I'm listening! Could you tell me a bit more?"])

            bubbles = ai_data.get("reply_bubbles", [])
            if not bubbles: bubbles = ["Let me check on that for you."]
            
            allow_img = ai_data.get("allow_image", False)

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
                count = params.get("product_count", 4) # Default to 4
                print(f"🔎 Text Search Query: {query} (Requesting: {count})")
                
                # Search for 6, return 4 to ensure quality
                raw_results = search_products(query_text=query, top_k=6)
                
                if raw_results:
                    products = raw_results[:4]
                else:
                    bubbles.append("I couldn't find an exact match, but here are our most popular pieces.")
                    products = search_products(query_text="Best seller", top_k=4)

            return ChatResponse(
                text_bubbles=bubbles, 
                products=products,
                allow_image=allow_img 
            )

    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        return ChatResponse(text_bubbles=["I'm having a brief connection issue. Please say that again?"])