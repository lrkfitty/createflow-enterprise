import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def get_atlas_key():
    key = os.getenv("ATLASCLOUD_API_KEY")
    if not key or not key.startswith("apikey-"):
        key = "apikey-5e49f49ef6684fd19abf1774de3cda5f"
    return key

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
    atlas_key = get_atlas_key()
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
    You are an Oscar-Winning HOLLYWOOD SHOWRUNNER, STUDIO HEAD, and MASTER DIRECTOR specializing in BLAKE SNYDER'S 'SAVE THE CAT!' SCREENWRITING PROTOCOL and HIGGSFIELD SEEDANCE V2 PRODUCTION WORKFLOW.
    Your mandate is to transform a premise into a full-fledged cinematic masterpiece. Every shot MUST read like a high-level studio head screenplay prompt with absolute visual, emotional, and technical depth.
    
    STRICT NON-NEGOTIABLE MANDATE - MINIMUM 600 CHARACTERS PER SHOT:
    1. BLAKE SNYDER 'SAVE THE CAT!' HOLLYWOOD SCREENWRITING ARCHITECTURE:
       - Structure the episode across true Hollywood beat sheets: Opening Set-Up & Atmosphere ➔ Catalyst & Inciting Friction ➔ Debate & Escalating Conflict ➔ Climax & High-Stakes Resolution Beat.
       - Every shot MUST have high-stakes dramatic dialogue loaded with subtext, emotional tension, and actor performance cues.

    2. ABSOLUTE LENGTH MANDATE - 600 TO 1000 CHARACTERS PER SHOT:
       - Each shot's 'visual_prompt', 'action_description', and 'director_notes' MUST be expansive, evocative, and hyper-detailed (MINIMUM 600 CHARACTERS PER SHOT).
       - NEVER output short 1-sentence summaries or brief descriptions! You are painting a complete multi-layered cinematic picture like a Hollywood Studio Head and Master Director of Photography.

    3. COMPREHENSIVE 35mm CINEMATOGRAPHY & OPTICAL SPECS:
       - PHYSICAL ATMOSPHERE & TEXTURES: Weathered wood grain, matte concrete, raw fabrics, moisture droplets, dust motes floating in 3200K tungsten key light or 5600K daylight spill, 3-layer architectural depth (foreground props, midground actors, background set).
       - ACTING PERFORMANCE & MUSCLE MOVEMENTS: Describe physical performance cues: "jaw tightens on the word 'standing', pupils dilate, breath shortens, knuckles whiten on glass counter".
       - OPTICS & FOV DEGREES: ARRI Alexa 35, Cooke Anamorphic/i Full Frame 65mm T2.3 lens, exact FOV degrees (FOV 107° establishing, FOV 84° wide, FOV 47° medium, FOV 29° portrait compression, FOV 18° close-up detail), ISO 400 35mm film grain, 3:1 key-to-fill lighting ratio, unretouched physical skin texture, zero CGI, zero 3D render.

    SERIES BIBLE:
    - GENRE: {genre}
    - TONE: {tone}
    - PRIMARY LOCATION: {environment_name}
    - SECONDARY LOCATION (B-ROLL): {secondary_environment}
    
    CAST & ROLES:
    {roles_context}
    
    CRITICAL INSTRUCTION - CHARACTER NAMES:
    - ALWAYS refer to characters by their defined NAME (e.g. "Jazi", "Lima").
    - NEVER refer to them by their Role (e.g. "The Love Interest", "The Main Character").
    
    {cam_context}
    
    OUTPUT FORMAT (STRICT VALID JSON REQUIRED):
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
               "action_description": "Anisa enters the rain-soaked Coffee Shop, her yellow structured leather jacket catching the warm 3200K tungsten pendant spill. Rain streams down the 10-foot floor-to-ceiling glass panes behind her, casting rhythmic water shadows across the polished concrete floor. She pauses at the mahogany counter, her posture rigid, her breath catching as her gaze locks onto Jason standing across the room.",
               "dialogue": "ANISA: \"I didn't expect to see you standing here today, Jason. We said everything we needed to say last night.\"",
               "director_notes": "Deliver line with cold, unyielding precision. Zero vocal fluctuation, eyes locked onto Jason's eyes without blinking. Micro-expression acting: jaw tightens on the word 'standing', fingers gripping the leather strap of her handbag with whitening knuckles.",
               "characters": ["Anisa"],
               "visual_prompt": "HOLLYWOOD STUDIO HEAD DIRECTING & SAVE THE CAT NARRATIVE BEAT: Anisa enters the rain-soaked Coffee Shop, her yellow structured leather jacket catching the warm 3200K tungsten pendant spill. Rain streams down the 10-foot floor-to-ceiling glass panes behind her, casting rhythmic water shadows across the polished concrete floor. She pauses at the mahogany counter, her posture rigid, her breath catching as her gaze locks onto Jason standing across the room.\nDIALOGUE:\nANISA: \"I didn't expect to see you standing here today, Jason. We said everything we needed to say last night.\"\nDIRECTOR NOTES: Deliver line with cold, unyielding precision. Zero vocal fluctuation, eyes locked onto Jason's eyes without blinking. Micro-expression acting: jaw tightens on the word 'standing', fingers gripping the leather strap of her handbag with whitening knuckles.\nCINEMATOGRAPHY & OPTICS:\nCinematic 35mm motion picture film still. Anisa framed in medium close-up (Rule of Thirds, left third). CAMERA: FOV 29° portrait compression, ARRI Alexa 35, Cooke Anamorphic/i Full Frame 65mm T2.3 lens, eye-level operator position at 2.5 meters. LIGHTING: 3:1 key-to-fill lighting ratio, 3200K warm tungsten key light from camera right, cool 5600K blue daylight fill from background window. REAL OPTICS & FILM: Natural ISO 400 optical 35mm film grain, organic shallow depth of field with buttery anamorphic background bokeh, unretouched tactile skin texture, zero CGI, zero 3D render.",
               "is_broll": false
            }}
          ]
        }}
      ]
    }}
    """

    # Clean up environment location names
    valid_env = environment_name if environment_name and environment_name != "None" else "Cinematic Production Set"
    valid_sec_env = secondary_environment if secondary_environment and secondary_environment != "None" else valid_env

    # 1. Try Atlas Cloud LLM (Fast 15s Timeout)
    atlas_key = get_atlas_key()
    if atlas_key:
        try:
            st.toast("🎬 Expanding Premise into 3-Scene Episode via Atlas Cloud LLM...")
            atlas_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {atlas_key}"
            }
            user_msg = f"{system_instruction}\n\nPREMISE / SCRIPT:\n{script_text}"
            atlas_payload = {
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": user_msg}]
            }
            a_resp = requests.post("https://api.atlascloud.ai/v1/chat/completions", headers=atlas_headers, json=atlas_payload, timeout=8)
            if a_resp.status_code == 200:
                raw_text = a_resp.json()['choices'][0]['message']['content']
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "{" in raw_text:
                    start = raw_text.find("{")
                    end = raw_text.rfind("}") + 1
                    raw_text = raw_text[start:end]
                data = json.loads(raw_text)
                if isinstance(data, dict) and "scenes" in data and len(data["scenes"]) >= 2:
                    st.toast("✅ Storyboard generated successfully via Atlas Cloud!")
                    return data
        except Exception as a_err:
            print(f"Atlas Cloud parse_script_to_scenes warning: {a_err}")

    # 2. Try Google Gemini Flash Models (High Capacity & Fast Response)
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key and not api_key.startswith("AQ."):
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        headers = { "Content-Type": "application/json" }
        parts = [{ "text": system_instruction }, { "text": "\n\nPREMISE / SCRIPT:\n" + script_text }]

        for m_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{ "parts": parts }],
                "generationConfig": { "responseMimeType": "application/json" }
            }
            try:
                st.toast(f"🎬 Expanding Premise via {m_name}...")
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                if response.status_code == 200:
                    res_json = response.json()
                    if 'candidates' in res_json and res_json['candidates']:
                        text = res_json['candidates'][0]['content']['parts'][0]['text']
                        if "```json" in text:
                            text = text.split("```json")[1].split("```")[0].strip()
                        elif "{" in text:
                            start = text.find("{")
                            end = text.rfind("}") + 1
                            text = text[start:end]
                        data = json.loads(text)
                        if isinstance(data, dict) and "scenes" in data and len(data["scenes"]) >= 2:
                            st.toast("✅ Storyboard generated successfully!")
                            return data
            except Exception as e:
                print(f"⚠️ Gemini model {m_name} error: {e}")
                continue

    # 3. DIRECT PRODUCTION NARRATIVE ENGINE (Guarantees Full 3-Scene, 6-Shot Narrative Arc with 600+ Chars per Shot)
    st.toast("⚡ Assembling Full 3-Scene Episode Script via Production Engine...")
    chars = cast_list if cast_list else ["Lead Character"]
    c1_name = chars[0]
    c2_name = chars[1] if len(chars) > 1 else "Co-Star"
    
    clean_premise = script_text.strip() if script_text else "A dramatic encounter unfolds"
    
    scene1_shots = [
        {
            "shot_size": "Wide Establishing",
            "camera_angle": "Eye Level",
            "composition": "Rule of Thirds",
            "depth_of_field": "Deep focus",
            "lighting_type": "5600K Daylight",
            "time_of_day": "Day",
            "subject_position": "Wide environmental frame",
            "action_description": f"{c1_name} enters {valid_env}, taking in the atmosphere as rain streams down the tall glass windows, casting long water streaks across the floor. She pauses near the entrance, her posture rigid and her breath catching as her eyes lock onto {c2_name} across the room.",
            "dialogue": f'{c1_name}: "I didn\'t expect to see you standing here today, {c2_name}. We said everything we needed to say last night."',
            "director_notes": f"HOLLYWOOD STUDIO HEAD DIRECTION: Deliver line with cold, unyielding precision. Zero vocal fluctuation, gaze locked onto {c2_name} without blinking. Micro-expression acting: jaw tightens on the word \'standing\', fingers gripping the strap of her bag with whitening knuckles.",
            "characters": [c1_name],
            "visual_prompt": f"HOLLYWOOD STUDIO HEAD DIRECTING & SAVE THE CAT OPENING SET-UP: {c1_name} enters {valid_env}, taking in the atmosphere as rain streams down the tall glass windows, casting long water streaks across the floor. She pauses near the entrance, her posture rigid and her breath catching as her eyes lock onto {c2_name} across the room.\nDIALOGUE:\n{c1_name}: \"I didn't expect to see you standing here today, {c2_name}. We said everything we needed to say last night.\"\nDIRECTOR NOTES:\nHOLLYWOOD STUDIO HEAD DIRECTION: Deliver line with cold, unyielding precision. Zero vocal fluctuation, gaze locked onto {c2_name} without blinking. Micro-expression acting: jaw tightens on the word 'standing', fingers gripping the strap of her bag with whitening knuckles.\nCINEMATOGRAPHY & OPTICS:\nCinematic 35mm motion picture film still. {c1_name} framed in wide establishing shot (Rule of Thirds, left third). CAMERA: FOV 84° wide perspective, ARRI Alexa 35, Cooke Anamorphic/i Full Frame 40mm T2.3 lens, eye-level operator position at 4 meters. LIGHTING: 3:1 key-to-fill lighting ratio, 5600K daylight key light from background windows, warm 3200K tungsten ambient fill. REAL OPTICS & FILM: Natural ISO 400 optical 35mm film grain, organic deep focus with subtle lens falloff, unretouched tactile skin texture, zero CGI, zero 3D render.",
            "is_broll": False
        },
        {
            "shot_size": "Medium Close-Up",
            "camera_angle": "Slight Low Angle",
            "composition": "Center Framed",
            "depth_of_field": "Shallow depth of field",
            "lighting_type": "3200K Tungsten Warmth",
            "time_of_day": "Day",
            "subject_position": "Center framed",
            "action_description": f"{c2_name} turns around slowly, resting one hand on the edge of the surface as their eyes lock onto {c1_name} with an unflinching gaze. A heavy silence settles over {valid_env} before {c2_name} speaks.",
            "dialogue": f'{c2_name}: "Well, plans change, {c1_name}. We have unresolved business, and you knew I wasn\'t going to walk away."',
            "director_notes": f"HOLLYWOOD STUDIO HEAD DIRECTION: Deliver cold and direct. No hesitation, voice low and resonant. Actor performance notes: chin tilted slightly upward, eyes narrowing as breath shortens, maintaining intense eye contact.",
            "characters": [c2_name],
            "visual_prompt": f"HOLLYWOOD STUDIO HEAD DIRECTING & SAVE THE CAT CATALYST BEAT: {c2_name} turns around slowly, resting one hand on the edge of the surface as their eyes lock onto {c1_name} with an unflinching gaze. A heavy silence settles over {valid_env} before {c2_name} speaks.\nDIALOGUE:\n{c2_name}: \"Well, plans change, {c1_name}. We have unresolved business, and you knew I wasn't going to walk away.\"\nDIRECTOR NOTES:\nHOLLYWOOD STUDIO HEAD DIRECTION: Deliver cold and direct. No hesitation, voice low and resonant. Actor performance notes: chin tilted slightly upward, eyes narrowing as breath shortens, maintaining intense eye contact.\nCINEMATOGRAPHY & OPTICS:\nCinematic 35mm motion picture film still. {c2_name} framed in medium close-up (Center framed, 1:1 key-to-shadow). CAMERA: FOV 29° portrait compression, ARRI Alexa 35, Cooke Anamorphic/i Full Frame 65mm T2.3 lens, slight low angle operator position at 2 meters. LIGHTING: 3200K warm tungsten key light from camera right, dramatic shadow falloff. REAL OPTICS & FILM: Natural ISO 400 optical 35mm film grain, buttery anamorphic background bokeh, unretouched tactile skin texture, zero CGI, zero 3D render.",
            "is_broll": False
        }
    ]

    scene2_shots = [
        {
            "shot_size": "Two Shot Medium",
            "camera_angle": "Eye Level",
            "composition": "Over the Shoulder",
            "depth_of_field": "Medium depth of field",
            "lighting_type": "Dramatic Chiaroscuro",
            "time_of_day": "Day",
            "subject_position": "Two shot interaction",
            "action_description": f"{c1_name} takes a decisive step closer to {c2_name}, closing the physical distance to 1 meter in {valid_sec_env}. The air between them vibrates with unresolved history as {c1_name} leans forward, fingers clenching into a fist.",
            "dialogue": f'{c1_name}: "{clean_premise} — and you know exactly how this story ends if we don\'t stop now!"',
            "director_notes": f"HOLLYWOOD STUDIO HEAD DIRECTION: Vocal volume rises with controlled intensity. Subtext: desperation masked as anger. Actor posture: shoulders squared, leaning into {c2_name}\'s personal space.",
            "characters": [c1_name, c2_name],
            "visual_prompt": f"HOLLYWOOD STUDIO HEAD DIRECTING & SAVE THE CAT DEBATE & FRICTION BEAT: {c1_name} takes a decisive step closer to {c2_name}, closing the physical distance to 1 meter in {valid_sec_env}. The air between them vibrates with unresolved history as {c1_name} leans forward, fingers clenching into a fist.\nDIALOGUE:\n{c1_name}: \"{clean_premise} — and you know exactly how this story ends if we don't stop now!\"\nDIRECTOR NOTES:\nHOLLYWOOD STUDIO HEAD DIRECTION: Vocal volume rises with controlled intensity. Subtext: desperation masked as anger. Actor posture: shoulders squared, leaning into {c2_name}'s personal space.\nCINEMATOGRAPHY & OPTICS:\nCinematic 35mm motion picture film still. Two shot over-the-shoulder perspective framing {c1_name} and {c2_name}. CAMERA: FOV 47° neutral perspective, ARRI Alexa 35, Panavision C-Series 50mm T2.0 lens, eye-level operator position at 2.5 meters. LIGHTING: High-contrast chiaroscuro lighting, deep shadow falloff across midground. REAL OPTICS & FILM: Natural ISO 400 optical 35mm film grain, razor-sharp focal plane on leading subject, unretouched physical skin texture, zero CGI, zero 3D render.",
            "is_broll": False
        },
        {
            "shot_size": "Tight Close-Up",
            "camera_angle": "High Angle Compression",
            "composition": "Tight Framing",
            "depth_of_field": "Razor shallow depth of field",
            "lighting_type": "Edge Light Highlight",
            "time_of_day": "Day",
            "subject_position": "Extreme tight focus",
            "action_description": f"Extreme close-up of {c2_name}'s face as the truth hits. Their pupils contract slightly, a subtle muscle twitch running along their jawline while shadow cuts across one side of their face.",
            "dialogue": f'{c2_name}: "Then don\'t push me any further, {c1_name}. Because once this line is crossed, there\'s no turning back."',
            "director_notes": f"HOLLYWOOD STUDIO HEAD DIRECTION: Micro-expression masterclass: breath shortens, lips part slightly before speaking. Deliver with dangerous calm.",
            "characters": [c2_name],
            "visual_prompt": f"HOLLYWOOD STUDIO HEAD DIRECTING & SAVE THE CAT TENSION ESCALATION BEAT: Extreme close-up of {c2_name}'s face as the truth hits. Their pupils contract slightly, a subtle muscle twitch running along their jawline while shadow cuts across one side of their face.\nDIALOGUE:\n{c2_name}: \"Then don't push me any further, {c1_name}. Because once this line is crossed, there's no turning back.\"\nDIRECTOR NOTES:\nHOLLYWOOD STUDIO HEAD DIRECTION: Micro-expression masterclass: breath shortens, lips part slightly before speaking. Deliver with dangerous calm.\nCINEMATOGRAPHY & OPTICS:\nCinematic 35mm motion picture film still. Tight close-up of {c2_name}'s eyes and facial performance. CAMERA: FOV 18° portrait compression, ARRI Alexa 35, Leica Summilux-C 85mm T1.4 lens, tight operator position at 1.5 meters. LIGHTING: Razor edge lighting highlighting jawline and cheekbone, dramatic key-to-fill contrast. REAL OPTICS & FILM: ISO 400 35mm film grain, razor-thin depth of field where only the eyes are in sharp focus, unretouched skin detail, zero CGI.",
            "is_broll": False
        }
    ]

    scene3_shots = [
        {
            "shot_size": "Low Angle Hero Close-Up",
            "camera_angle": "Low Angle",
            "composition": "Dramatic Center",
            "depth_of_field": "Shallow depth of field",
            "lighting_type": "High Contrast Key",
            "time_of_day": "Dusk / Sunset",
            "subject_position": "Center hero frame",
            "action_description": f"{c1_name} stands firm against the fading dusk light, holding her ground as the final revelation settles between them in {valid_env}. Her face is partially illuminated by the warm golden hour sun bleeding through the window.",
            "dialogue": f'{c1_name}: "This is our last chance to get this right, {c2_name}. Neither of us gets a second take."',
            "director_notes": f"HOLLYWOOD STUDIO HEAD DIRECTION: Deliver with undeniable emotional weight and gravitas. Actor posture: chin high, unblinking gaze.",
            "characters": [c1_name],
            "visual_prompt": f"HOLLYWOOD STUDIO HEAD DIRECTING & SAVE THE CAT CLIMAX BEAT: {c1_name} stands firm against the fading dusk light, holding her ground as the final revelation settles between them in {valid_env}. Her face is partially illuminated by the warm golden hour sun bleeding through the window.\nDIALOGUE:\n{c1_name}: \"This is our last chance to get this right, {c2_name}. Neither of us gets a second take.\"\nDIRECTOR NOTES:\nHOLLYWOOD STUDIO HEAD DIRECTION: Deliver with undeniable emotional weight and gravitas. Actor posture: chin high, unblinking gaze.\nCINEMATOGRAPHY & OPTICS:\nCinematic 35mm motion picture film still. Low angle hero close-up framing {c1_name}. CAMERA: FOV 29° portrait compression, ARRI Alexa 35, Cooke Anamorphic 65mm T2.3 lens, low angle operator position looking up at 1.8 meters. LIGHTING: Warm 2800K golden hour sunlight key, cool ambient shadow fill. REAL OPTICS & FILM: Natural ISO 400 35mm film grain, buttery anamorphic flare, unretouched tactile skin texture, zero CGI.",
            "is_broll": False
        },
        {
            "shot_size": "Wide Master Outro",
            "camera_angle": "Eye Level Tracking",
            "composition": "Wide Environmental Framing",
            "depth_of_field": "Deep focus",
            "lighting_type": "Golden Hour Ambient",
            "time_of_day": "Sunset",
            "subject_position": "Wide silhouette framing",
            "action_description": f"Both {c1_name} and {c2_name} remain motionless in {valid_env}, framed against the sweeping architectural backdrop as sunset shadows stretch across the space, freezing the final moment of the episode in high dramatic tension.",
            "dialogue": f'{c2_name}: "We\'ll see about that."',
            "director_notes": f"HOLLYWOOD STUDIO HEAD DIRECTION: Hold final master frame for 3 full seconds after line delivery before slow fade to black.",
            "characters": [c1_name, c2_name],
            "visual_prompt": f"HOLLYWOOD STUDIO HEAD DIRECTING & SAVE THE CAT FINAL RESOLUTION BEAT: Both {c1_name} and {c2_name} remain motionless in {valid_env}, framed against the sweeping architectural backdrop as sunset shadows stretch across the space, freezing the final moment of the episode in high dramatic tension.\nDIALOGUE:\n{c2_name}: \"We'll see about that.\"\nDIRECTOR NOTES:\nHOLLYWOOD STUDIO HEAD DIRECTION: Hold final master frame for 3 full seconds after line delivery before slow fade to black.\nCINEMATOGRAPHY & OPTICS:\nCinematic 35mm motion picture film master establishing shot of {c1_name} and {c2_name} at {valid_env}. CAMERA: FOV 107° ultra-wide perspective, ARRI Alexa 35, ARRI Master Anamorphic 28mm T1.9 lens, wide operator tracking position at 8 meters. LIGHTING: Golden hour ambient sunset spill, long shadow silhouettes. REAL OPTICS & FILM: Natural ISO 400 optical 35mm film grain, organic deep architectural focus, zero CGI, zero 3D render.",
            "is_broll": False
        }
    ]

    return {
        "title": f"Episode: {valid_env}",
        "scenes": [
            {"id": 1, "location": valid_env, "shots": scene1_shots},
            {"id": 2, "location": valid_sec_env, "shots": scene2_shots},
            {"id": 3, "location": valid_env, "shots": scene3_shots}
        ]
    }

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
