import os
import json
import time
import textwrap
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def generate_prompt_content(vibe, outfit, character, 
                            outfit_path=None, vibe_path=None, # Multimodal Inputs
                            additional_notes=None, 
                            camera=None, lens=None, shot_type=None, angle=None,
                            lighting=None, weather=None, action=None, emotion=None,
                            film_stock=None, filter_look=None, # New Inputs
                            aspect_ratio="9:16", # Default
                            extra_images=None, # New: List of {path, label} types
                            model_engine="gemini-2.0-flash"): # Standard: Gemini 2.0 Flash (Free & Fast)
    """
    Generates a detailed image prompt using Google Gemini.
    CRITICAL: Visual references take ABSOLUTE priority over text descriptions.
    """
    
    # Common Helper to encode image
    def encode_image(image_path):
        import base64
        import requests
        
        # Case A: URL
        if image_path.startswith(('http://', 'https://')):
            try:
                resp = requests.get(image_path)
                resp.raise_for_status()
                return base64.b64encode(resp.content).decode('utf-8')
            except Exception as e:
                print(f"Failed to download reference image: {e}")
                return "" # Handle gracefully
                
        # Case B: Local File
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        
        return ""

    # 1. Analyze Inputs
    character_is_image = False
    character_bio = ""
    
    # Check if Character string is a path/url to an image
    if character:
        is_url = character.startswith(('http://', 'https://'))
        is_local_img = os.path.exists(character) and character.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        
        if is_url or is_local_img:
            character_is_image = True
            
            # Try to find bio.txt (Only for local files currently)
            if is_local_img:
                base_name = os.path.splitext(character)[0]
                txt_path = base_name + ".txt"
                parent_dir = os.path.dirname(character)
                bio_txt_in_folder = os.path.join(parent_dir, "bio.txt")
                if os.path.exists(txt_path):
                    with open(txt_path, 'r') as f: character_bio = f.read()
                elif os.path.exists(bio_txt_in_folder):
                    with open(bio_txt_in_folder, 'r') as f: character_bio = f.read()

    outfit_is_image = False
    if outfit_path:
        if outfit_path.startswith(('http', 'https')) or os.path.exists(outfit_path):
            outfit_is_image = True
            
    vibe_is_image = False
    if vibe_path:
         if vibe_path.startswith(('http', 'https')) or os.path.exists(vibe_path):
            vibe_is_image = True

    # Construct Director's Note
    director_context = []
    if camera: director_context.append(f"Camera: {camera}")
    if lens: director_context.append(f"Lens: {lens}")
    if shot_type: director_context.append(f"Shot Type: {shot_type}")
    if angle: director_context.append(f"Camera Angle: {angle}")
    if lighting: director_context.append(f"Lighting: {lighting}")
    if weather: director_context.append(f"Weather: {weather}")
    if action: director_context.append(f"Action/Pose: {action}")
    if emotion: director_context.append(f"Emotion/Expression: {emotion}")
    if film_stock: director_context.append(f"Film Stock: {film_stock}")
    if filter_look: director_context.append(f"Color Grading/Filter: {filter_look}")
    if aspect_ratio: director_context.append(f"Frame Aspect Ratio: {aspect_ratio}")
    
    tech_specs = "\n".join(director_context)

    # --- COMPLETELY REWRITTEN SYSTEM PROMPT (VISUAL PRIORITY) ---
    instructions = "You are an expert Visual Director."
    img_refs_text = ""
    if character_is_image: img_refs_text += "- IMAGE 1: THE CHARACTER (Identity Lock). Keep face/body EXACT.\n"
    if outfit_is_image:    img_refs_text += "- IMAGE 2: THE OUTFIT (Visual Reference). Copy this clothing detail-for-detail.\n"
    if vibe_is_image:      img_refs_text += "- IMAGE 3: THE VIBE (Visual Reference). Copy this environment/lighting.\n"
    
    system_prompt = textwrap.dedent(f"""
        {instructions}
        
        ROLE: You are an ACADEMY AWARD-WINNING CINEMATOGRAPHER and HOLLYWOOD DIRECTOR. You are famous for your visual storytelling, intense detail, and atmospheric lighting.
        
        GOAL: Your job is to take visual references and turn them into a **VISUAL MASTERPIECE PROMPT**.
        
        🚨 ABSOLUTE RULE #1: VISUAL REFERENCES = TRUTH 🚨
        The images provided are ABSOLUTE REALITY. Your job is to DESCRIBE WHAT YOU SEE, not what the text says.
        - If IMAGE 1 shows a blonde woman → You MUST write "blonde woman"
        - If IMAGE 2 shows a brown fur top → You MUST write "brown fur top"
        - If the text says "red dress" but IMAGE 2 shows black pants → DESCRIBE THE BLACK PANTS
        
        IMAGES OVERRIDE TEXT. ALWAYS. NO EXCEPTIONS.
        
        CRITICAL OUTPUT RULES:
        1.  **DESCRIBE EXACTLY WHAT YOU SEE IN THE IMAGES.** Do not invent features or clothing.
        2.  **RICH, DENSE, EVOCATIVE LANGUAGE:** 150+ words. Use cinematic terms like "Volumetric Lighting", "Subsurface Scattering", "Bokeh", "Film Grain", "Chiaroscuro".
        3.  **NEVER BE GENERIC:**
            -   BAD: "She is wearing a top."
            -   GOOD: "She is draped in a plush brown fur cropped top that catches the golden hour light with each movement, revealing hints of skin at her midriff."
        
        INSTRUCTION MANUAL:
        
        1.  **VISUAL IDENTITY LOCK (HIGHEST PRIORITY):**
            -   **STUDY IMAGE 1 (Character):** What does she ACTUALLY look like?
                - Hair: color, length, texture, style
                - Face: eye color, facial structure, skin tone
                - Body: proportions, build
            -   **DO NOT HALLUCINATE.** If you see blonde hair, write blonde. If you see green eyes, write green.
            
        2.  **WARDROBE FIDELITY (SECOND PRIORITY):**
            -   **STUDY IMAGE 2 (Outfit):** What is she ACTUALLY wearing?
                - Colors, textures, fit, accessories
                - Stitching, fabric weight, how it drapes
            -   **DO NOT INVENT CLOTHING.** Describe what exists in the image.
            
        3.  **ENVIRONMENT & ATMOSPHERE:**
            -   **STUDY IMAGE 3 (Location/Vibe):** What is the ACTUAL setting?
                - Indoor/outdoor? Architecture? Lighting quality?
                - Describe light sources, shadows, reflections, atmosphere
            
        4.  **TECHNICAL ENHANCEMENT:**
            -   Use the technical specs to enhance the existing composition:
                - "Shot on [Camera] with [Lens], [Lighting]..."
            
        5.  **ACTION & STORY (Expand the Mood):**
            -   Take the action/emotion and weave it into the scene
            -   "Striding confidently", "Eyes locked in an intense gaze"
            
        6.  **CO-STARS & SCENE COMPOSITION:**
            -   If ADDITIONAL REFERENCE images are provided, INTEGRATE each person
            -   **DESCRIBE EACH PERSON EXACTLY AS THEY APPEAR** in their reference image
            -   Create CHEMISTRY and BLOCKING:
                - "She stands between two companions: one in a leather jacket on her left, the other in sunglasses on her right"
            -   **MAKE THEM INTERACT.** No static lineups.
            -   For 3+ people, describe SPATIAL ARRANGEMENT (triangle, line, huddle)
            
        OUTPUT JSON FORMAT:
        {{
            "positive_prompt": "(MASTERPIECE): [What you SEE in the images] + [Technical specs] + [Action/Emotion expansion] + [Cinematic atmosphere]. High aesthetic, 8k, photorealistic.",
            "negative_prompt": "cartoon, illustration, anime, 3d render, painting, drawing, text, watermark, low quality, glitch, deformed, mutated, ugly, disfigured, smooth skin, plastic look, wrong hair color, wrong outfit, hallucinated features...",
            "aspect_ratio": "{aspect_ratio}"
        }}
    """)
    
    user_text_content = f"Generate a masterpiece prompt. The character is wearing '{outfit}' in a '{vibe}' setting."
    
    # Force Textual Acknowledgement of Extras WITH NAME EXTRACTION
    print(f"🔍 DEBUG [generate_prompt]: extra_images received = {extra_images}")  # CRITICAL DEBUG
    if extra_images:
        character_names = []
        extras_txt = []
        
        for img in extra_images:
            lbl = img.get('label', 'Ref')
            
            # Extract character name from "Cast: Name" or "Cast:  Name" labels
            if "Cast:" in lbl:
                # Parse: "Cast:  Chels" -> "Chels"
                name_part = lbl.split("Cast:")[-1].strip()
                if name_part:
                    character_names.append(name_part)
            
            extras_txt.append(f"- {lbl}")
        
        cast_count = 1  # Start with the main character
        if character_names:
            cast_count += len(character_names)
            
            # Build explicit name list
            names_list = ", ".join(character_names)
            
            user_text_content += f"\n\n🎬 CRITICAL: This is a {cast_count}-PERSON SCENE with the following characters: {names_list}."
            user_text_content += f"\n\n⚠️ YOU MUST USE THESE EXACT NAMES in your description. For example:"
            for name in character_names:
                user_text_content += f"\n- '{name}, a [description]...' NOT 'a [description]...'"
            
            user_text_content += "\n\nCAST LIST (with reference images):\n" + "\n".join(extras_txt)
            user_text_content += "\n\nDESCRIBE HOW EACH PERSON LOOKS (from their image), how they're positioned, and how they interact. Create a TABLEAU, not a lineup."

    if tech_specs: user_text_content += f"\n\nTECHNICAL SPECS:\n{tech_specs}"
    if character_bio: user_text_content += f"\n\nCHARACTER BIO (context only):\n{character_bio}"
    if additional_notes: user_text_content += f"\n\nADDITIONAL CONTEXT: {additional_notes}"


    # ================= GEMINI IMPLEMENTATION =================
    if "gemini" in model_engine:
        try:
            load_dotenv(override=True)
            google_key = os.getenv("GOOGLE_API_KEY")
            if not google_key: return {"positive_prompt": "Error: GOOGLE_API_KEY missing", "aspect_ratio": "9:16"}
            
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel(model_engine)
            
            # Prepare Content List
            gemini_content = [system_prompt, "\n\nUSER REQUEST:\n" + user_text_content]
            
            # Load Images using PIL for Gemini
            from PIL import Image
            import requests
            from io import BytesIO
            import concurrent.futures

            def resize_image(img, max_size=1024):
                """Resize image to max_size on longest side while maintaining aspect ratio."""
                width, height = img.size
                if width <= max_size and height <= max_size:
                    return img
                
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            def load_pil_image(path):
                img = None
                try:
                    if path.startswith(('http://', 'https://')):
                        resp = requests.get(path, timeout=10)
                        resp.raise_for_status()
                        img = Image.open(BytesIO(resp.content))
                    elif os.path.exists(path):
                        img = Image.open(path)
                except Exception as e:
                    print(f"PIL Load Error for {path}: {e}")
                    return None
                
                if img:
                    try:
                        return resize_image(img)
                    except Exception as e:
                        print(f"Resize Error for {path}: {e}")
                        return img # Return original if resize fails
                return None

            # Parallel Load Helper
            def fetch_image_map(img_data):
                """Helper for parallel fetch. Returns (label, PIL_Image) or None"""
                p = img_data.get("path")
                l = img_data.get("label", "Ref")
                if not p: return None
                
                image_obj = load_pil_image(p)
                if image_obj:
                    return (l, image_obj)
                return None

            # 1. Load Main Images (Sequential is fine for 3, but let's be consistent)
            # Actually, let's just load them.
            
            if character_is_image:
                img = load_pil_image(character)
                if img:
                    gemini_content.append("IMAGE 1 (CHARACTER - IDENTITY LOCK):")
                    gemini_content.append(img)
                
            if outfit_is_image:
                img = load_pil_image(outfit_path)
                if img:
                    gemini_content.append("IMAGE 2 (OUTFIT - EXACT WARDROBE):")
                    gemini_content.append(img)
                
            if vibe_is_image:
                img = load_pil_image(vibe_path)
                if img:
                    gemini_content.append("IMAGE 3 (LOCATION/VIBE):")
                    gemini_content.append(img)
                
            # 2. Parallel Load Extra Images
            if extra_images:
                print(f"⚡ Fetching {len(extra_images)} extra images in parallel...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    results = list(executor.map(fetch_image_map, extra_images))
                
                for res in results:
                    if res:
                        lbl, img_obj = res
                        gemini_content.append(f"ADDITIONAL REFERENCE ({lbl} - DESCRIBE EXACTLY AS SHOWN):")
                        gemini_content.append(img_obj)
                
            # RETRY LOGIC FOR 429 (RATE LIMIT)
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(gemini_content)
                    break 
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        raise e
            
            # Parse JSON
            raw_text = response.text
            if "```json" in raw_text:
                try: raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                except IndexError: pass
            elif "{" in raw_text:
                start = raw_text.find("{")
                end = raw_text.rfind("}") + 1
                raw_text = raw_text[start:end]
            
            result = json.loads(raw_text)
            return result
            
        except Exception as e:
            print(f"Gemini Error: {e}")
            return {"positive_prompt": f"Error generating prompt: {e}", "aspect_ratio": aspect_ratio}
    
    return {"positive_prompt": "Unknown model engine", "aspect_ratio": aspect_ratio}
