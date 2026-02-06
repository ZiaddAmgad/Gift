import os
import json
import base64
import io
import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from PIL import Image

# NEW SDK IMPORTS (google.genai)
from google import genai
from google.genai import types

from app.core.rag import search_products

router = APIRouter()

# --- 🛡️ SECURITY CONSTANTS ---
MAX_TEXT_LENGTH = 150 
MAX_IMAGE_SIZE_B64 = 1_500_000 

# --- DATA MODELS ---
class Message(BaseModel):
    role: str
    content: str
    image: Optional[str] = None 

    @validator('content')
    def validate_content_length(cls, v):
        if len(v) > MAX_TEXT_LENGTH:
            return v[:MAX_TEXT_LENGTH] + "..."
        return v

    @validator('image')
    def validate_image_size(cls, v):
        if v and len(v) > MAX_IMAGE_SIZE_B64:
            raise ValueError("Image too large. Please use the official interface.")
        return v

class ChatRequest(BaseModel):
    messages: List[Message]
    client_id: Optional[str] = "artsy" 

# --- NEW MODEL FOR TRY-ON ---
class TryOnRequest(BaseModel):
    user_image: str          # Base64 string
    product_image_url: str
    product_title: Optional[str] = "Jewelry" # <--- ADD THIS
    client_id: Optional[str] = "artsy"

class ChatResponse(BaseModel):
    text_bubbles: List[str]
    products: Optional[List[dict]] = []
    allow_image: Optional[bool] = False
    chat_ended: Optional[bool] = False

# --- 1. VISION SYSTEM PROMPT ---
VISION_PROMPT = """
You are an expert Jewelry Stylist.

**INPUTS:**
1. **Chat History:** Use this to understand WHO (Recipient) and WHY (Occasion).
2. **Image:** Use this to understand the VISUAL STYLE and SKIN TONE.

**TASK:**
1. Check if the image contains a woman/girl or clear jewelry style reference. 
   - If NO person/style: Set "valid_image": false. STOP there.
2. **Visual Analysis:** Analyze the image for Skin Tone, Style, Material.
3. **Context Analysis:** Analyze the Chat History. Apply the **TAG MAPPING LOGIC** below to extract "context_tags".
4. GENERATE a 'friendly_reply' (2 sentences max).

**TAG MAPPING LOGIC (Strictly apply this to Chat History):**
- **Recipient:**
  - Mom / Grandma / Aunt -> "Traditional, Classic, Vintage"
  - Wife / Partner / Fiancee -> "Romantic, Classic, Statement"
  - Girlfriend -> "Romantic, Trendy, Dainty"
  - Sister / Friend -> "Trendy, Boho, Modern"
- **Occasion:**
  - Valentine -> "Valentine Romantic"
  - Anniversary -> "Anniversary Romantic Classic"
  - Mother's Day -> "Mother's Day Traditional"
  - Party / Wedding -> "Party Statement Bold"
  - Holiday -> "Holiday Statement"

**STRICT VISUAL TAG OPTIONS (Apply this to Image):**
- Material: "Gold, Silver, Rose Gold, White Gold, Gold Plated, Sterling Silver, Platinum, Enamel, Leather, Cord, Pearl, Beaded, Mixed"
- Style: "Minimalist, Boho, Vintage, Bold, Statement, Art Deco, Modern, Classic, Romantic, Geometric, Nature, Dainty, Industrial, Traditional, Trendy"
- Gemstone: "Diamond, Zircon, Pearl, Turquoise, Onyx, Crystal, Emerald, Ruby, Sapphire, None"
- Skin Tone: "Cool Tones, Warm Tones, Neutral"

**OUTPUT FORMAT (JSON):**
{
    "valid_image": boolean,
    "context_tags": "String containing mapped tags from History (e.g., 'Romantic Classic' if Fiancee found)",
    "material": "...",
    "style": "...",
    "gemstone": "...",
    "skin_tone": "...",
    "friendly_reply": "..." 
}
"""

# --- 2. TEXT SYSTEM PROMPT (UPDATED FOR 3 PRODUCTS) ---
SYSTEM_PROMPT = """
You are a warm, expert Jewelry Concierge.
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
   - Return **3 products** immediately.
   - **TEXT REPLY RULE:**
     - Write exactly 2 sentences.
     - Sentence 1: Briefly summarize the chosen style/vibe (e.g. "Since she loves [Style] looks...").
     - Sentence 2: "Based on that, I recommend these 3 pieces." (Or a similar variation).
   - **CRITICAL:** Set "chat_ended": true.

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
    "chat_ended": boolean,
    "search_params": {
        "ready_to_search": boolean,
        "recipient_tags": "...",
        "occasion_tags": "...",
        "material_tags": "...",
        "style_tags": "...",
        "gemstone_tags": "...",
        "product_count": 3 
    }
}
"""


def build_try_on_prompt(product_title: str):
    """
    Constructs a highly specific prompt based on the jewelry type.
    """
    p_lower = product_title.lower()
    
    # 1. DEFAULT SETTINGS
    framing = "Close-up portrait focusing on the relevant body part."
    placement = "Worn naturally."
    removal = "Ensure the skin area is clean before applying the jewelry."
    
    # 2. DYNAMIC LOGIC
    if any(x in p_lower for x in ['earring', 'hoop', 'ear', 'stud']) and 'set' not in p_lower:
        j_type = "EARRINGS"
        framing = "Extreme close-up 'Side Profile' portrait focusing strictly on the ear, jawline, and neck. Crop tight to the head."
        placement = "The earrings must hang naturally from the earlobe, obeying gravity."
        removal = "REMOVE any existing earrings the user is wearing. Replace them entirely with the Product. The earlobe must look clean."

    elif any(x in p_lower for x in ['necklace', 'chain', 'choker', 'pendant']) and 'set' not in p_lower:
        j_type = "NECKLACE"
        framing = "Elegant 'Bust Portrait' from the chest up to the nose. Focus on the clavicle and neck area."
        placement = "Draped realistically over the neck/clavicle. If wearing a high collar, place it over the fabric. If bare skin, place it on skin."
        removal = "REMOVE any existing necklaces. The neck area should feature ONLY this specific Product."

    elif any(x in p_lower for x in ['ring', 'band']) and 'set' not in p_lower:
        j_type = "RING"
        framing = "Macro 'Hand Detail' shot. Focus strictly on the fingers and hand. Blur the background/body."
        
        # Check for specific fingers
        if 'thumb' in p_lower:
            finger_target = "Thumb"
        elif 'pinky' in p_lower:
            finger_target = "Pinky finger"
        elif 'index' in p_lower:
            finger_target = "Index finger"
        else:
            finger_target = "Ring finger or Middle finger"
            
        placement = f"Fitted perfectly on the {finger_target}."
        removal = "REMOVE any existing rings on that hand. The fingers should be bare except for this Product."

    elif any(x in p_lower for x in ['bracelet', 'bangle', 'wrist']) and 'set' not in p_lower:
        j_type = "BRACELET/BANGLE"
        framing = "Macro 'Wrist and Forearm' shot. The hand can be resting on a lap, holding a bag, or near the face."
        placement = "Circling the wrist naturally with correct perspective and shadow."
        removal = "REMOVE any existing wristwatches or bracelets. The wrist must be clear."

    elif any(x in p_lower for x in ['anklet', 'ankle']):
        j_type = "ANKLET"
        framing = "Macro 'Ankle and Foot' detail shot. Focus strictly on the lower leg, ankle bone, and foot. Crop out the upper body."
        placement = "Wrapped naturally around the ankle bone. It should sit comfortably on the skin above the foot."
        removal = "REMOVE any existing anklets, socks, or ankle chains. The skin around the ankle must be bare."

    elif 'handchain' in p_lower or 'hand chain' in p_lower:
        j_type = "HANDCHAIN"
        framing = "Top-down 'Back of Hand' detail shot."
        placement = "Draped elegantly across the back of the hand, connecting the wrist to the middle finger."
        removal = "Remove existing rings or bracelets to highlight the handchain structure."

    elif 'set' in p_lower:
        j_type = "JEWELRY SET"
        framing = (
            "Multi-Point MACRO SHOT. Crop strictly to the Head, Neck, and Hands. "
            "IGNORE the waist, legs, and background. "
            "If the set includes rings/bracelets, bring the hand into the frame near the face/neck. "
            "Fill 80% of the image frame with the User's skin/clothing where the jewelry sits."
        )
        placement = (
            "Identify components (Necklace, Ring, etc.) and place them on their respective body parts. "
            "Ensure ALL pieces are visible in this single zoomed-in frame."
        )
        removal = "Remove existing jewelry from the neck, ears, and hands."
    
    else:
        j_type = "JEWELRY" # Fallback

    # 3. CONSTRUCT THE MASTER PROMPT
    # Added Instruction #7 specifically for scaling
    return f"""
    You are a high-end jewelry retoucher and photographer.
    
    YOUR TASK:
    Composite the Product ({j_type}) onto the User's photo to create a photorealistic catalog image.

    CRITICAL INSTRUCTIONS:
    1. FRAMING: {framing}
    2. REMOVAL: {removal}
    3. PLACEMENT: {placement}
    4. PRESERVE IDENTITY: Keep the User's exact skin tone, clothing texture, hair color, and lighting environment.
    5. LIGHTING: Match the reflection on the {j_type} to the light source in the User's photo.
    6. STYLE: Shallow depth of field (Bokeh). The jewelry must be the sharpest part of the image.
    7. REALISTIC SCALING: The Input Product Image is a "Macro/Zoomed-In" reference. You MUST shrink/scale it down to fit the User's anatomy realistically. It should look like fine jewelry, not oversized costume jewelry.
    
    Output a high-resolution, photorealistic image.
    """

# --- NEW TRY-ON ENDPOINT WITH CORRECT SDK ---
@router.post("/try-on")
async def try_on_endpoint(request: TryOnRequest):
    try:
        client_id = request.client_id or "artsy"
        env_key_name = f"GOOGLE_API_KEY_{client_id.upper()}"
        client_api_key = os.getenv(env_key_name) or os.getenv("GOOGLE_API_KEY")

        # Create new SDK client
        client = genai.Client(api_key=client_api_key)

        # 1. Download product image
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as http_client:
            product_response = await http_client.get(request.product_image_url)
            product_response.raise_for_status()
            product_image_data = product_response.content

        # 2. Decode user image from base64
        user_image_b64 = request.user_image
        if "base64," in user_image_b64:
            user_image_b64 = user_image_b64.split("base64,")[1]
        user_image_data = base64.b64decode(user_image_b64)

        # 3. Convert to PIL Images
        user_image = Image.open(io.BytesIO(user_image_data))
        product_image = Image.open(io.BytesIO(product_image_data))

        # 4. Create prompt
        prompt = build_try_on_prompt(request.product_title)

        # 5. Generate image using NEW SDK
        def _generate():
            return client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt, user_image, product_image],
            )

        response = await asyncio.to_thread(_generate)

        # 6. Extract generated image
        for part in response.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                b64 = base64.b64encode(image_data).decode("utf-8")
                mime = getattr(part.inline_data, "mime_type", "image/png")
                return {"image_url": f"data:{mime};base64,{b64}"}

        raise HTTPException(status_code=500, detail="No image was generated")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Try-On Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    client_id = request.client_id or "artsy"
    
    # --- DYNAMIC API KEY ---
    env_key_name = f"GOOGLE_API_KEY_{client_id.upper()}"
    client_api_key = os.getenv(env_key_name) or os.getenv("GOOGLE_API_KEY")
    
    # New google.genai client + configs (text + vision)
    client = genai.Client(api_key=client_api_key)
    text_config = types.GenerateContentConfig(response_mime_type="application/json")
    vision_config = types.GenerateContentConfig(response_mime_type="application/json")

    try:
        last_msg = request.messages[-1]
        
        # --- PATH A: VISION LOGIC ---
        if last_msg.image:
            print(f"📸 Image detected. Namespace: {client_id}")
            
            image_data = last_msg.image
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            image_bytes = base64.b64decode(image_data)

            # 1. Prepare Text History for Context
            history_text = "--- CHAT HISTORY ---\n"
            for m in request.messages:
                if m.role == 'user' and not m.image:
                    history_text += f"User: {m.content}\n"
            
            # 2. Multimodal Call: Prompt + History + Image (new SDK)
            vision_contents = [
                VISION_PROMPT,
                history_text,
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            ]

            def _call_vision():
                return client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=vision_contents,
                    config=vision_config,
                )

            response = await asyncio.to_thread(_call_vision)
            
            try:
                vision_data = json.loads(response.text)
                
                if not vision_data.get("valid_image", True):
                    failed_attempts = sum(1 for m in request.messages if m.content in ["Image uploaded", "[User sent an image]"])
                    if failed_attempts < 2:
                        return ChatResponse(
                            text_bubbles=["I couldn't quite see her style clearly in that photo. Do you have a clearer one, or should we just chat?"],
                            allow_image=True 
                        )
                    else:
                        return ChatResponse(
                            text_bubbles=["No worries! Let's stick to text to be safe. Does she usually prefer Gold or Silver?"],
                            allow_image=False 
                        )

                friendly_reply = vision_data.get("friendly_reply", "That's a beautiful photo! I see exactly what might suit her.")
                
                # 3. Combine Tags (Context from History + Visual from Image)
                context_tags = vision_data.get('context_tags', '')
                visual_tags = f"{vision_data.get('style','')} {vision_data.get('material','')} {vision_data.get('gemstone','')} {vision_data.get('occasion','')} {vision_data.get('skin_tone','')}"
                
                # Context comes first for RAG priority
                search_query_tags = f"{context_tags} {visual_tags}".strip()
                
                print(f"🔎 Hybrid Search Query: {search_query_tags}")
                
                # 4. Search
                raw_results = search_products(query_text=search_query_tags, top_k=3, namespace=client_id)
                # --- CHANGE: Limit to 3 products ---
                final_products = raw_results[:3] if raw_results else []
                
                if not final_products:
                    friendly_reply += " I looked through our collection and these popular pieces seem closest to that style."
                    # --- MULTI-TENANT SEARCH (Fallback) ---
                    # --- CHANGE: Limit to 3 products ---
                    final_products = search_products("Best seller", top_k=3, namespace=client_id)
                
                return ChatResponse(
                    text_bubbles=[friendly_reply],
                    products=final_products,
                    allow_image=False,
                    chat_ended=True
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
            # Text-only call (new SDK)
            def _call_text():
                return client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt],
                    config=text_config,
                )

            response = await asyncio.to_thread(_call_text)
            
            try:
                ai_data = json.loads(response.text)
            except json.JSONDecodeError:
                return ChatResponse(text_bubbles=["I'm listening! Could you tell me a bit more?"])

            bubbles = ai_data.get("reply_bubbles", [])
            if not bubbles: bubbles = ["Let me check on that for you."]
            
            allow_img = ai_data.get("allow_image", False)
            chat_ended = ai_data.get("chat_ended", False)

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
                count = params.get("product_count", 3) # Default to 3
                print(f"🔎 Text Search Query: {query} (Requesting: {count})")
                
                # --- MULTI-TENANT SEARCH (Text) ---
                raw_results = search_products(query_text=query, top_k=3, namespace=client_id)
                
                if raw_results:
                    # --- CHANGE: Limit to 3 products ---
                    products = raw_results[:3]
                else:
                    bubbles.append("I couldn't find an exact match, but here are our most popular pieces.")
                    # --- MULTI-TENANT SEARCH (Fallback) ---
                    # --- CHANGE: Limit to 3 products ---
                    products = search_products(query_text="Best seller", top_k=3, namespace=client_id)

            return ChatResponse(
                text_bubbles=bubbles, 
                products=products,
                allow_image=allow_img,
                chat_ended=chat_ended
            )

    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        return ChatResponse(text_bubbles=["I'm having a brief connection issue. Please say that again?"])