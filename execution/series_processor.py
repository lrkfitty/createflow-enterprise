import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Imports for inner function needing global scope if moving out
from PIL import Image
from io import BytesIO
import base64
import concurrent.futures
import time
import streamlit as st

def resize_bytes_to_jpeg(image_bytes, max_size=1280):
    """Resize image bytes to max_size and return generic JPEG bytes."""
    try:
        img = Image.open(BytesIO(image_bytes))
        
        # Resize logic
        width, height = img.size
        if width <= max_size and height <= max_size:
            # If small enough, just convert to JPEG to ensure compatibility/compression
            pass 
        else:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB (in case of RGBA PNG) and save as JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        out_buffer = BytesIO()
        img.save(out_buffer, format="JPEG", quality=85)
        return out_buffer.getvalue()
        
    except Exception as e:
        print(f"Resize Error: {e}")
        return image_bytes # Fallback to original

def parse_script_to_scenes(script_text, cast_list, environment_name, genre="General", tone="Neutral", roles_map=None, wardrobe_map=None, ref_images=None, secondary_environment="None", camera="Auto", lens="Auto", lighting="Auto", film_stock="Auto", filter_look="Auto", movie_style="Auto", transition_style="Auto"):
    """
    Uses Gemini to break down a raw script into structured Scenes.
    Dynamic shot count based on script content (minimum 8, no maximum).
    V3 Update: Added Cinematic Parameters (Camera, Lens, Lighting).
    V3.5 Update: Multimodal Support (Deep Vision).
    V3.6 Update: Added Film Stock and Filter/Look.
    V4 Update: Reframed for photorealistic scene stills (not video).
    """
    

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "Missing GOOGLE_API_KEY"}

    # Format roles for context
    roles_context = ""
    if roles_map or wardrobe_map:
        roles_context = "\n    - Character Profiles:\n"
        all_names = set(list(roles_map.keys()) if roles_map else []) | set(list(wardrobe_map.keys()) if wardrobe_map else [])
        for name in all_names:
            role = roles_map.get(name, "Actor") if roles_map else "Actor"
            outfit = wardrobe_map.get(name, "Standard Outfit") if wardrobe_map else "Standard Outfit"
            roles_context += f"      * {name}: Role={role}, Wardrobe={outfit}\n"

    # CINEMATOGRAPHY CONTEXT
    cam_context = f"""
    CINEMATOGRAPHY SETTINGS (STRICTLY ENFORCE):
    - CAMERA BODY: {camera}
    - LENS PACKAGE: {lens}
    - LIGHTING STYLE: {lighting}
    - FILM STOCK: {film_stock}
    - FILTER/LOOK: {filter_look}
    - MOVIE STYLE REFERENCE: {movie_style}
    - VISUAL PACING / MOOD PROGRESSION: {transition_style}
    """

    system_instruction = f"""
    You are a World-Class HOLLYWOOD DIRECTOR and CINEMATOGRAPHER (Netflix/HBO/A24 Standard).
    Your job is to visualize a script into a precise, high-end storyboard of PHOTOREALISTIC SCENE STILLS (film stills).
    These are NOT for video — they are individual HIGH-FIDELITY PHOTOGRAPHS capturing key dramatic moments.
    You MUST prioritize VISUAL AESTHETICS above all else. No flat lighting. No generic angles.
    Refer to the 'CINEMATOGRAPHY SETTINGS' below for the specific camera and lens package.
    
    SERIES BIBLE:
    - GENRE: {genre}
    - TONE: {tone}
    - PRIMARY LOCATION: {environment_name}
    - SECONDARY LOCATION (B-ROLL): {secondary_environment}
    
    DYNAMIC ENVIRONMENT SCALING:
    - The PRIMARY LOCATION is the starting point or anchor.
    - HOWEVER, if the SCRIPT explicitly describes a scene moving to a new place (e.g. 'INT. CAR', 'EXT. PARK'), you MUST update the `location` field and the prompt description to match the NEW location.
    - Do NOT force the Primary Location if the story leaves it. Follow the narrative journey.
    
    CAST & ROLES:
    {roles_context}
    
    CRITICAL INSTRUCTION - CHARACTER NAMES:
    - ALWAYS refer to characters by their defined NAME (e.g. "Shay", "Chels").
    - NEVER refer to them by their Role (e.g. "The Love Interest", "The Main Character").
    - The Asset System only recognizes NAMES.
    
    {cam_context}
    
    INSTRUCTIONS:
    1. VISUAL STYLE: You must write prompts that produce HIGH-FIDELITY PHOTOREALISTIC STILLS.
       - Use keywords: "Photorealistic, Film Still, Color Graded, Volumetric Lighting, Depth of Field, 8k, Ultra-Detailed, RAW Photography".
       - Apply the specific Camera/Lens/Lighting settings provided above to EVERY description.
       - Think like a PHOTOGRAPHER capturing a single decisive moment, NOT a videographer.
       - Example: "Wide shot on Arri Alexa with Anamorphic Lens, cinematic moody lighting, frozen moment..."
    
    2. SCENE BREAKDOWN: Analyze the script and create AS MANY SHOTS AS THE SCRIPT NEEDS.
       - Each shot is a STANDALONE STILL IMAGE — a frozen moment in time.
       - MINIMUM 8 shots. NO MAXIMUM — let the script dictate the count.
       - **HOW TO DETERMINE SHOT COUNT:**
         * Count every KEY DIALOGUE LINE → each one needs a shot
         * Count every REACTION MOMENT → each one needs a shot  
         * Count every LOCATION CHANGE → each one needs an establishing shot
         * Count every EMOTIONAL BEAT → each one needs a shot
         * Add 1-2 opening establishing shots + 1 closing atmosphere shot
         * Example: Script with 10 dialogue lines + 3 reactions + 2 location changes = ~17 shots

       - **STRUCTURE GUIDE (Scale with script complexity):**
         * OPENING: 1-2 Establishing Stills (Character/Environment Introduction)
         * BODY: One shot per dialogue line, reaction, or emotional beat (the bulk of coverage)
         * B-ROLL: Sprinkle atmosphere/detail shots where they serve the mood (mark these with "is_broll": true)
         * CLOSING: 1 Final Hero Shot or Closing Atmosphere Still

       - **CRITICAL RULE ON B-ROLL:**
         * Do NOT force B-Roll at fixed positions — place them where they serve the scene.
         * Only use B-Roll (Environment/Details) if it enhances the atmosphere.
         * Mark B-Roll shots with "is_broll": true in the JSON output.
         * If the scene is dialogue-heavy, prioritize CHARACTER FOCUS over B-Roll.

       - **DIALOGUE-TO-SHOT MAPPING (CRITICAL — DO NOT SKIP LINES):**
         * If the script contains SPEAKING LINES or DIALOGUE, you MUST dedicate shots to the KEY dialogue moments.
         * Each important line of dialogue = ONE SHOT capturing the character IN THE ACT of delivering that line.
         * The 'visual_prompt' MUST quote the specific line being spoken (e.g. "Shay, mid-sentence, saying 'I told you this would happen'").
         * Show the CHARACTER'S FACE and BODY LANGUAGE at that exact moment — the emotion behind the words.
         * Include REACTION SHOTS: after a key line, show the OTHER character's face reacting to what was just said.
         * Do NOT summarize 5 lines of dialogue into one generic "two characters talking" shot.
         * Think of it like a SCRIPT SUPERVISOR: every beat in the script should have visual coverage.

    3. VISUAL FIDELITY (CRITICAL - DO NOT FAIL THIS):
       - You have been provided with VISUAL REFERENCE images labeled "Wardrobe".
       - You MUST Use these images as the ABSOLUTE SOURCE OF TRUTH.

       A. **WARDROBE (STRICT - DO NOT HALLUCINATE)**:
       - You DO NOT know what the outfit looks like. Use the LABEL only.
       - **CORRECT**: "Shay wearing the Red Dress"
       - **WRONG**: "Shay wearing a red silk gown with lace trim" (This will conflict with the image).
       - **REASON**: The image generator uses the REFERENCE IMAGE. Your text description of the outfit creates GHOSTING and ARTIFACTS.
       - **EXCEPTION**: You CAN describe how the outfit is being worn (e.g. "dirty", "wet", "torn", "flowing in wind").

       B. **FACES & IDENTITY (STRICT - DO NOT HALLUCINATE)**:
       - You DO NOT know what the character looks like.
       - **CORRECT**: "Shay smiles..."
       - **WRONG**: "Shay, a beautiful blonde woman with blue eyes, smiles..."
       - **REASON**: Describing the face creates a "Generic AI Face" that overrides the specific LoRA/Reference Identity.
       - **VERIFICATION**: Scan your prompt. Did you write "blonde", "brunette", "blue eyes", "pale skin"? DELETE IT immediately. Only describe EMOTIONS and LIGHTING on the face.

    4. TEXTURE & DETAIL (HOLLYWOOD STANDARD):
       - You MUST include 3-4 keywords per shot describing TEXTURE (e.g. "Gritty film grain", "Sweat on brow", "Dust motes in light", "Chrome reflection").
       - Avoid vague words like "Atmospheric" without defining WHAT makes it atmospheric.

    5. SHOT CONSISTENCY CHECK:
       - If the Request says "Medium Shot", you MUST generate a "Medium Shot".
       - Do NOT drift to "Wide Shot" unless the script action makes a Medium Shot physically impossible.
       - Self-Correct: Before outputting, ask "Does this match the requested camera angle?"

    6. B-ROLL RULES:
       - B-Roll shots must NOT focus on main characters. Focus on details, environment, lighting, or objects that set the mood (Tone).
       - Use the 'Secondary/B-Roll Environment'.
    
    5. SHOT LIST: For each Shot, you must define these SPECIFIC, GRANULAR parameters:
       - 'shot_size': E.g. "Extreme Close Up", "Medium Shot", "Wide Shot".
       - 'camera_angle': E.g. "Low Angle", "High Angle", "Dutch Angle", "Eye Level".
       - 'composition': E.g. "Center Framed", "Rule of Thirds", "Symmetrical".
       - 'depth_of_field': E.g. "Shallow depth of field", "Deep focus", "Bokeh".
       - 'lighting_type': E.g. "Rembrandt", "Soft Box", "Neon", "Golden Hour Hard Light".
       - 'time_of_day': E.g. "Morning", "Day", "Golden Hour", "Blue Hour", "Night".
       - 'subject_position': E.g. "Seated at bar", "Walking towards camera".
       - 'action_description': What is happening.
       - 'characters': List of characters present.
       - 'visual_prompt': THE FINAL MASTER PROMPT (Must be 1000+ characters).
         * This is where you earn your Oscar. Do NOT just copy the script action.
         * **SCENE EXPANSION**: If the script says "Shay sits", you write "Shay sits, slumped forward, exhaustion etched into her posture, the harsh neon light casting deep shadows under her eyes."
         * **ENVIRONMENTAL TEXTURE**: Describe the dust motes, the condensation on glass, the crack in the wall, the specific way light hits the fabric.
         * **MICRO-EXPRESSIONS**: Describe the subtle twitch of a lip, the glaze in the eyes, the tension in the jaw.
         * **LIGHTING SPECIFICITY**: Use terms like "Chiaroscuro", "Rim Light", "Volumetric God Rays", "Practical Source", "Specular Highlights".
         * Structure: "Photorealistic film still. [Shot Size], [Camera Angle]. [Subject Position], [Action Description + Micro-Expression]. [Time of Day], [Lighting Type + Specular Details], [Depth of Field]. [Camera/Lens Specs for Texture]. Ultra-detailed, 8k, RAW photography. [Detailed Background Texture]. [Detailed Outfit interaction with environment]. [Atmosphere/Vibe]."
    
    OUTPUT FORMAT:
    Return ONLY valid JSON.
    {{
      "title": "Episode Title",
      "scenes": [
        {{
          "id": 1,
          "location": "...",
          "shots": [
            {{
               "shot_size": "...",
               "camera_angle": "...",
               "composition": "...",
               "depth_of_field": "...",
               "lighting_type": "...",
               "time_of_day": "...",
               "subject_position": "...",
               "action_description": "...",
               "characters": ["Name1"],
               "visual_prompt": "...",
               "is_broll": false
            }}
          ]
        }}
      ]
    }}
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
    headers = { "Content-Type": "application/json" }
    
    # BUILD MULTIMODAL PAYLOAD
    parts = []
    
    # 1. System Instruction
    parts.append({ "text": system_instruction })
    
    # 2. Reference Images (PARALLELIZED)
    if ref_images:
        # Imports already handled above or at module level if moved
        # But we need to ensure load_single_ref can see resize_bytes_to_jpeg

        def load_single_ref(img_data):
            path = img_data.get('path')
            label = img_data.get('label', 'Image')
            t_start = time.time()
            
            result_parts = []
            
            try:
                raw_bytes = None
                
                # Case A: URL
                if path and path.startswith("http"):
                    resp = requests.get(path, timeout=5)  # Reduced from 10s to 5s
                    if resp.status_code == 200:
                        raw_bytes = resp.content
                        print(f"   ⚡ Downloaded {label} in {time.time() - t_start:.2f}s")
                    else:
                        print(f"   ⚠️ Failed to download {label}: Status {resp.status_code}")

                # Case B: Local File
                elif path and os.path.exists(path):
                    with open(path, "rb") as f:
                        raw_bytes = f.read()
                        print(f"   ⚡ Loaded {label} (Local) in {time.time() - t_start:.2f}s")
                
                # Optimize & Encode
                if raw_bytes:
                    # RESIZE STEP
                    optimized_bytes = resize_bytes_to_jpeg(raw_bytes)
                    
                    b64 = base64.b64encode(optimized_bytes).decode('utf-8')
                    result_parts.append({ "text": f"VISUAL REFERENCE - {label}:" })
                    result_parts.append({ "inline_data": { "mime_type": "image/jpeg", "data": b64 } })
                    
            except Exception as e:
                print(f"   ❌ Error loading {label}: {e}")
                
            return result_parts

        print(f"⚡ Director AI: fetching {len(ref_images)} assets in parallel...")
        st.toast(f"📥 Loading {len(ref_images)} reference images...")
        t_batch_start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # maintain order? Order matters less here as distinct prompt parts, but nice to keep.
            results = list(executor.map(load_single_ref, ref_images))
            
        for res in results:
            parts.extend(res)
            
        load_time = time.time() - t_batch_start
        print(f"⚡ Director AI assets ready in {load_time:.2f}s")
        st.toast(f"✅ References loaded ({load_time:.1f}s). Generating storyboard...")

    # 3. Script
    parts.append({ "text": "\n\nSCRIPT:\n" + script_text })

    payload = {
        "contents": [{
            "parts": parts
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        # Timeout increased to 120s for Director AI Stability
        st.toast("🎬 Waiting for Gemini AI response (may take 30-120s)...")
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        res_json = response.json()
        
        # Extract text
        if 'candidates' not in res_json:
            error_msg = f"Gemini Refusal: {res_json.get('promptFeedback', res_json)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
            
        text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        # Clean markdown
        text = text.replace('```json', '').replace('```', '').strip()
        
        # Parse
        data = json.loads(text)
        st.toast("✅ Storyboard generated successfully!")
        return data

    except requests.exceptions.Timeout:
        return {"error": "API Timeout (120s exceeded). Try reducing cast size or simplifying script."}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Local Test
    sample_script = "Tylarkin walks into the Neon Bar. He sees Shay sitting at a booth. He waves."
    cast = ["Tylarkin", "Shay"]
    env = "Neon Bar"
    print(json.dumps(parse_script_to_scenes(sample_script, cast, env), indent=2))
