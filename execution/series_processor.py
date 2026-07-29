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

def generate_environment_master_prompt(location_name, genre="General", tone="Neutral", camera="Auto", lighting="Auto", style="Auto", shot_angle_type="Master Establishing View"):
    """
    Generates a Real-World Organic 35mm Film Texture Environment Master Prompt for a location.
    Enforces tactile physical textures, 3-layer depth, WB in Kelvin, optical lens falloff, and NO CGI/artificial sharpness.
    """
    atlas_key = os.getenv("ATLASCLOUD_API_KEY")
    prompt_req = f"""
    ROLE: You are an Oscar-Winning Master Director of Photography and Film Production Designer.
    TASK: Write a master real-world 35mm motion picture film camera location prompt for: '{location_name}'.
    SHOT PERSPECTIVE / ANGLE: {shot_angle_type}.
    GENRE: {genre}, TONE: {tone}, CAMERA/LIGHT: {camera}, {lighting}, STYLE: {style}.
    
    REAL-WORLD CINEMATIC FILM RULES:
    1. RAW TACTILE SURFACES: Describe authentic unpolished physical textures (weathered wood grain, peeling plaster, matte concrete, dust motes in air, moisture, rust, raw fabrics).
    2. ZERO CGI / ZERO PLASTIC: Do NOT use digital jargon or buzzwords like '8K', 'photorealistic', 'hyperrealistic', '3D render', 'volumetric light beams', 'masterpiece', 'unreal engine'.
    3. REAL OPTICS & FILM: Describe 35mm motion picture film stock, natural ISO 400 optical film grain, realistic optical depth of field, natural shadow falloff, anamorphic lens flare/aberration.
    4. OPTICS & FOV: Match perspective '{shot_angle_type}' (use FOV degrees: 107° for wide establishing, 84° for reverse angle, 63° for medium detail, 29° for texture macro).
    5. 3-LAYER DEPTH: Foreground physical props/occlusion, midground main space, deep background architecture.
    6. LIGHTING: Natural exposure, White Balance in Kelvin (5600K daylight or 3200K tungsten), unretouched specular reflections.
    7. STRICT EMPTY SET MANDATE: Absolutely NO PEOPLE, NO CHARACTERS, NO HUMAN FIGURES, NO SILHOUETTES, NO PERSONS. This is a pure empty architectural film set location still (unless 'extras' or 'people' is explicitly stated in the location prompt).
    8. Return ONLY valid JSON: {{"environment_prompt": "PURE EMPTY SET STILL (NO PEOPLE, NO CHARACTERS, NO HUMAN FIGURES). Cinematic 35mm film still of...", "location": "{location_name}"}}
    """
    if atlas_key:
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {atlas_key}"}
            payload = {
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": prompt_req}]
            }
            r = requests.post("https://api.atlascloud.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if r.status_code == 200:
                raw = r.json()['choices'][0]['message']['content']
                if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
                elif "{" in raw: raw = raw[raw.find("{"):raw.rfind("}")+1]
                return json.loads(raw)
        except Exception as e:
            print(f"Environment prompt generation error: {e}")
            
    default_prompt = f"PURE EMPTY SET STILL (NO PEOPLE, NO CHARACTERS, NO HUMAN FIGURES). Cinematic 35mm motion picture film still of {location_name}. 107° ultra-wide FOV, 3-layer depth composition with weathered foreground architectural details, midground main space, and deep background layers. Natural 35mm film grain, ISO 400, unpolished physical surfaces with realistic dust and patina, 5600K daylight balance, natural unretouched shadow falloff, optical lens depth of field, RAW photography, zero CGI, zero people."
    return {"environment_prompt": default_prompt, "location": location_name}


def parse_script_to_scenes(script_text, cast_list, environment_name, genre="General", tone="Neutral", roles_map=None, wardrobe_map=None, ref_images=None, secondary_environment="None", camera="Auto", lens="Auto", lighting="Auto", film_stock="Auto", filter_look="Auto", movie_style="Auto", transition_style="Auto"):
    """
    Uses Atlas Cloud LLM (or Gemini fallback) to break down a script into structured Scenes
    strictly following the Higgsfield Seedance V2 Prompting Protocol.
    """
    
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
    You are a World-Class HOLLYWOOD SHOWRUNNER, MASTER DIRECTOR, and CINEMATOGRAPHER specializing in HIGGSFIELD SEEDANCE V2 WORKFLOW.
    Your job is to transform a premise/synopsis into a complete, masterfully directed episode script with FULL CHARACTER DIALOGUE, physical performance cues, and precise 35mm visual prompts.
    
    HIGGSFIELD SEEDANCE V2 DIRECTING & PROMPTING PROTOCOL (STRICT ADHERENCE REQUIRED):
    1. MASTER DIRECTING & DIALOGUE GENERATION (MANDATORY FOR EVERY SHOT):
       - You MUST write REAL dramatic character dialogue lines for EVERY shot featuring characters (e.g. ALICE: "We shouldn't be here... look at those windows.").
       - For establishing shots or atmospheric beats, write internal monologue / voiceover cues or intense scene intent.
       - State direct character speech, subtext, vocal delivery tone, and micro-expression acting cues.
       - Embed the dialogue lines, physical actions, and 35mm camera directions directly into 'visual_prompt' so it functions as a complete Master Director Script!
    2. POSITIVE-ONLY PHRASING:
       - Describe exact physical actions, posture, lighting, and surface textures.
       - NEVER use negative prohibitions ("no blur", "does not fall", "not cartoon").
    3. FOV DEGREES ANCHOR TABLE (Use exact degree steps in visual_prompt):
       - 180° = Fisheye / POV
       - 107° = Architectural Ultra-Wide (Establishing Environment)
       - 84°  = Wide Shot (Group Blocking)
       - 63°  = Observational Wide
       - 47°  = Neutral Human Perspective (Medium Shot)
       - 29°  = Portrait Compression (Medium Close-Up)
       - 18°  = Natural Portrait (Close-Up, Identity Preserved)
       - 12°  = Tele-Detail (Hands, Props, Key Objects)
       - 8°   = Super-Tele Extreme Compression
    4. CAMERA BLOCK IN 3RD POSITION:
       - Structure: [Subject Context & Tags] -> [Space & Timing / Physical Action & Dialogue] -> [CAMERA: FOV° + Operator Axis + Height] -> [Atmosphere & Light in %/Kelvin] -> [Style & Output].
    5. ACTING & PERFORMANCE THROUGH MUSCLE MOVEMENT:
       - Never use raw emotion labels like "sad" or "angry".
       - Describe physical muscle movements: "jaw tightens, eyes drop to the table, breath shortens, knuckles whiten on glass".
    6. PHYSICAL INTERACTION & ATMOSPHERE:
       - State atmosphere in percent (%) or meters depth (e.g. "fog density 30%, haze visible at 20 meters depth").
       - Physical interaction: rain runs down fabric, dust motes catch light beams, skin shows natural texture.

    SERIES BIBLE:
    - GENRE: {genre}
    - TONE: {tone}
    - PRIMARY LOCATION: {environment_name}
    - SECONDARY LOCATION (B-ROLL): {secondary_environment}
    
    CAST & ROLES:
    {roles_context}
    
    CRITICAL INSTRUCTION - CHARACTER NAMES:
    - ALWAYS refer to characters by their defined NAME (e.g. "Shay", "Chels").
    - NEVER refer to them by their Role (e.g. "The Love Interest", "The Main Character").
    
    {cam_context}
    
    DYNAMIC SHOT BREAKDOWN:
    - Analyze the script and create AS MANY SHOTS AS THE SCRIPT NEEDS (MINIMUM 8).
    - Create dedicated dialogue shots, reaction shots, location establishing, and emotional beats.
    - Mark B-Roll shots with "is_broll": true.
    
    OUTPUT FORMAT:
    Return ONLY valid JSON:
    {{
      "title": "Episode Title",
      "scenes": [
        {{
          "id": 1,
          "location": "{environment_name}",
          "shots": [
            {{
               "shot_size": "Medium Close-Up",
               "camera_angle": "Eye Level",
               "composition": "Rule of Thirds",
               "depth_of_field": "Shallow depth of field",
               "lighting_type": "3200K Tungsten Warmth",
               "time_of_day": "Night / Interior",
               "subject_position": "Center-left framed",
               "action_description": "Alice turns slowly, her jaw tightening as she looks across the room.",
               "dialogue": "ALICE: 'You thought I wouldn't find out? Take a look around.'",
               "director_notes": "Deliver line cold with zero vocal fluctuation. Keep gaze locked on Bob's eyes.",
               "characters": ["Alice"],
               "visual_prompt": "ACTION: Alice turns slowly, her jaw tightening as she looks across the room.\nDIALOGUE: ALICE: \"You thought I wouldn't find out? Take a look around.\"\nDIRECTOR NOTES: Deliver line cold with zero vocal fluctuation.\nCINEMATOGRAPHY: Cinematic 35mm film still. Alice in medium close-up. CAMERA: FOV 29°, eye-level, operator anchored 2 meters. ISO 400 35mm film grain, 3200K tungsten key light, shallow depth of field. Unretouched physical skin texture, zero CGI.",
               "is_broll": false
            }}
          ]
        }}
      ]
    }}
    """

    # Try Atlas Cloud API First (Zero Quota Limits)
    atlas_key = os.getenv("ATLASCLOUD_API_KEY")
    if atlas_key:
        try:
            st.toast("🎬 Generating Higgsfield Seedance Storyboard via Atlas Cloud LLM...")
            atlas_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atlas_key}"
            }
            user_msg = f"{system_instruction}\n\nSCRIPT:\n{script_text}"
            atlas_payload = {
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": user_msg}]
            }
            a_resp = requests.post("https://api.atlascloud.ai/v1/chat/completions", headers=atlas_headers, json=atlas_payload, timeout=60)
            if a_resp.status_code == 200:
                raw_text = a_resp.json()['choices'][0]['message']['content']
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "{" in raw_text:
                    start = raw_text.find("{")
                    end = raw_text.rfind("}") + 1
                    raw_text = raw_text[start:end]
                data = json.loads(raw_text)
                st.toast("✅ Storyboard generated successfully via Atlas Cloud!")
                return data
        except Exception as a_err:
            print(f"Atlas Cloud parse_script_to_scenes warning: {a_err}")

    # Fallback to Google API if Atlas unavailable
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "Missing ATLASCLOUD_API_KEY and GOOGLE_API_KEY"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
    headers = { "Content-Type": "application/json" }
    
    parts = []
    parts.append({ "text": system_instruction })
    
    if ref_images:
        def load_single_ref(img_data):
            path = img_data.get('path')
            label = img_data.get('label', 'Image')
            result_parts = []
            try:
                raw_bytes = None
                if path and path.startswith("http"):
                    resp = requests.get(path, timeout=5)
                    if resp.status_code == 200: raw_bytes = resp.content
                elif path and os.path.exists(path):
                    with open(path, "rb") as f: raw_bytes = f.read()
                if raw_bytes:
                    optimized_bytes = resize_bytes_to_jpeg(raw_bytes)
                    b64 = base64.b64encode(optimized_bytes).decode('utf-8')
                    result_parts.append({ "text": f"VISUAL REFERENCE - {label}:" })
                    result_parts.append({ "inline_data": { "mime_type": "image/jpeg", "data": b64 } })
            except Exception as e:
                print(f"Error loading {label}: {e}")
            return result_parts

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(load_single_ref, ref_images))
        for res in results:
            parts.extend(res)

    parts.append({ "text": "\n\nSCRIPT:\n" + script_text })

    payload = {
        "contents": [{ "parts": parts }],
        "generationConfig": { "responseMimeType": "application/json" }
    }
    
    try:
        st.toast("🎬 Waiting for Gemini AI response...")
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        res_json = response.json()
        if 'candidates' not in res_json:
            return {"error": f"Gemini Refusal: {res_json.get('promptFeedback', res_json)}"}
        text = res_json['candidates'][0]['content']['parts'][0]['text']
        text = text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        st.toast("✅ Storyboard generated successfully!")
        return data
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    sample_script = "Tylarkin walks into the Neon Bar. He sees Shay sitting at a booth. He waves."
    cast = ["Tylarkin", "Shay"]
    env = "Neon Bar"
    print(json.dumps(parse_script_to_scenes(sample_script, cast, env), indent=2))

if __name__ == "__main__":
    # Local Test
    sample_script = "Tylarkin walks into the Neon Bar. He sees Shay sitting at a booth. He waves."
    cast = ["Tylarkin", "Shay"]
    env = "Neon Bar"
    print(json.dumps(parse_script_to_scenes(sample_script, cast, env), indent=2))
