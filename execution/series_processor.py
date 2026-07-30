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
    Your mandate is to paint the entire picture as well as the scene. Every shot MUST read like a real Hollywood Studio Screenplay Shot Header with complete visual setup, atmospheric lighting, crowd composition, camera movement choreography, character blocking, parenthetical dialogue, and 35mm optical specifications.
    
    STRICT HOLLYWOOD SCREENPLAY & DIRECTORIAL SHOT HEADER FORMATTING MANDATE:
    Every shot's 'visual_prompt' MUST follow this exact, multi-layered Hollywood Screenplay Shot Header structure:

    1. SCENE SLUGLINE HEADER:
       - Format: INT. / EXT. [LOCATION] AT [TIME OF DAY] - [LIGHTING MOOD]

    2. LOCATION SETUP & ATMOSPHERE (PAINT THE PICTURE):
       - Paint the complete environmental picture: location architecture, atmospheric lighting temperature in Kelvin, sun angle, weather, dust motes, shadow falloff.
       - Describe background crowd / patron composition (e.g., "The area is filled with a minimum crowd of quiet patrons reading, but [Character Name] sticks out under the bright 3200K overhead light").

    3. CAMERA & MOVEMENT CHOREOGRAPHY:
       - Describe the exact camera movement: "The camera slowly pans in on [Character Name], moving from an observational 84° wide establishing shot into an intimate 29° medium close-up, tracking her deliberate steps toward the counter."

    4. CHARACTER BLOCKING & PERFORMANCE:
       - Describe posture, physical movement, eye contact, and muscle-movement micro-expressions (jaw tightens, breath shortens, eyes narrow, knuckles whiten on glass).

    5. HOLLYWOOD DIALOGUE & PARENTHETICAL DIRECTION:
       - Format:
         [CHARACTER NAME]
         ([parenthetical vocal delivery tone & emotional subtext])
         "[Dialogue line]"

    6. CINEMATOGRAPHY & 35mm OPTICS:
       - ARRI Alexa 35, Cooke Anamorphic/i Full Frame 65mm T2.3 lens, exact FOV degrees (FOV 107°, FOV 84°, FOV 47°, FOV 29°, FOV 18°), 3:1 key-to-fill exposure ratio, natural ISO 400 35mm film grain, organic shallow depth of field with buttery anamorphic background bokeh, unretouched physical skin texture, zero CGI, zero 3D render.

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
               "action_description": "Anisa enters the sun-drenched coffee shop at dusk. The area is filled with minimum background patrons, but Anisa sticks out under the bright 3200K overhead pendant beam. The camera slowly pans in on her as she pauses at the counter, her breath catching as her eyes lock onto Jason across the room.",
               "dialogue": "ANISA:\n(cold, unyielding precision; zero vocal fluctuation)\n\"I didn't expect to see you standing here today, Jason. We said everything we needed to say last night.\"",
               "director_notes": "Deliver line with cold, unyielding precision. Zero vocal fluctuation, eyes locked onto Jason's eyes without blinking. Micro-expression acting: jaw tightens on the word 'standing', fingers gripping handbag strap with whitening knuckles.",
               "characters": ["Anisa"],
               "visual_prompt": "INT. COFFEE SHOP AT DUSK - GOLDEN HOUR\n\nLOCATION SETUP & ATMOSPHERE:\nA sun-drenched coastal coffee shop at dusk with the sun barely setting over the ocean horizon. Deep amber rays bleed through floor-to-ceiling glass windows, casting long dramatic shadows across worn leather booths. The area is filled with a minimum crowd of quiet patrons reading, but Anisa sticks out under the bright 3200K overhead pendant beam, her yellow structured leather jacket glowing against the moody shadows.\n\nCAMERA & MOVEMENT CHOREOGRAPHY:\nThe camera slowly pans in on Anisa, moving from an observational 84° wide establishing shot into an intimate 29° medium close-up, tracking her deliberate steps toward the mahogany counter.\n\nCHARACTER BLOCKING & PERFORMANCE:\nAnisa pauses at the counter, her breath catching as her gaze locks onto Jason standing across the booth. Her jaw tightens on the word 'standing', fingers gripping the strap of her handbag with whitening knuckles.\n\nDIALOGUE & DIRECTION:\nANISA\n(cold, unyielding precision; zero vocal fluctuation)\n\"I didn't expect to see you standing here today, Jason. We said everything we needed to say last night.\"\n\nCINEMATOGRAPHY & 35mm OPTICS:\nCinematic 35mm motion picture film still. ARRI Alexa 35, Cooke Anamorphic/i Full Frame 65mm T2.3 lens, ISO 400 35mm film grain, 3:1 key-to-fill exposure ratio, 3200K warm tungsten key light from camera right, cool 5600K blue daylight fill, organic shallow depth of field with buttery background bokeh, unretouched physical skin texture, zero CGI.",
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
    # 3. DIRECT PRODUCTION NARRATIVE ENGINE (Guarantees Full 3-Scene, 6-Shot Narrative Arc with Hollywood Screenplay Shot Header Formatting)
    st.toast("⚡ Assembling Full 3-Scene Episode Script via Production Engine...")
    chars = cast_list if cast_list else ["Lead Character"]
    c1_name = chars[0]
    c2_name = chars[1] if len(chars) > 1 else c1_name
    
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
            "action_description": f"{c1_name} enters {valid_env} at dusk. The area is filled with a minimum crowd of quiet patrons, but {c1_name} sticks out under the bright 3200K overhead light. The camera slowly pans in on her as she pauses near the entrance, her breath catching as her eyes lock onto {c2_name} across the room.",
            "dialogue": f'{c1_name}:\n(cold, unyielding precision; zero vocal fluctuation)\n"I didn\'t expect to see you standing here today, {c2_name}. We said everything we needed to say last night."',
            "director_notes": f"Deliver line with cold, unyielding precision. Zero vocal fluctuation, gaze locked onto {c2_name} without blinking. Micro-expression acting: jaw tightens on the word \'standing\', fingers gripping the strap of her bag with whitening knuckles.",
            "characters": [c1_name],
            "visual_prompt": f"INT. {valid_env.upper()} AT DUSK - GOLDEN HOUR\n\nLOCATION SETUP & ATMOSPHERE:\nA sun-drenched coastal {valid_env.lower()} at dusk with the sun barely setting over the ocean horizon. Deep amber rays bleed through floor-to-ceiling glass windows, casting long dramatic shadows across worn leather booths. The area is filled with a minimum crowd of quiet patrons reading, but {c1_name} sticks out under the bright 3200K overhead pendant beam, her structured jacket glowing against the moody shadows.\n\nCAMERA & MOVEMENT CHOREOGRAPHY:\nThe camera slowly pans in on {c1_name}, moving from an observational 84° wide establishing shot into an intimate 29° medium close-up, tracking her deliberate steps toward the mahogany counter.\n\nCHARACTER BLOCKING & PERFORMANCE:\n{c1_name} pauses at the counter, her breath catching as her gaze locks onto {c2_name} standing across the room. Her jaw tightens on the word 'standing', fingers gripping the strap of her handbag with whitening knuckles.\n\nDIALOGUE & DIRECTION:\n{c1_name.upper()}\n(cold, unyielding precision; zero vocal fluctuation)\n\"I didn't expect to see you standing here today, {c2_name}. We said everything we needed to say last night.\"\n\nCINEMATOGRAPHY & 35mm OPTICS:\nCinematic 35mm motion picture film still. ARRI Alexa 35, Cooke Anamorphic/i Full Frame 65mm T2.3 lens, ISO 400 35mm film grain, 3:1 key-to-fill exposure ratio, 3200K warm tungsten key light from camera right, cool 5600K blue daylight fill, organic shallow depth of field with buttery background bokeh, unretouched physical skin texture, zero CGI.",
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
            "action_description": f"{c2_name} turns around slowly in {valid_env}, resting one hand on the mahogany surface under warm tungsten spill. The camera slowly pushes in as their eyes lock onto {c1_name} with an unflinching gaze.",
            "dialogue": f'{c2_name}:\n(low, resonant voice; chin tilted slightly upward)\n"Well, plans change, {c1_name}. We have unresolved business, and you knew I wasn\'t going to walk away."',
            "director_notes": f"Deliver cold and direct. No hesitation, voice low and resonant. Actor performance notes: chin tilted slightly upward, eyes narrowing as breath shortens, maintaining intense eye contact.",
            "characters": [c2_name],
            "visual_prompt": f"INT. {valid_env.upper()} - NIGHT / INTERIOR\n\nLOCATION SETUP & ATMOSPHERE:\nInside {valid_env.lower()} under warm 3200K tungsten key lighting casting dramatic shadow falloff across the mahogany surfaces. The ambient background is blurred into soft glowing golden motes, isolating {c2_name} in sharp, dramatic focus.\n\nCAMERA & MOVEMENT CHOREOGRAPHY:\nThe camera slowly pushes in on {c2_name} from a 47° medium perspective into a tight 29° medium close-up at eye level, capturing every subtle facial muscle movement.\n\nCHARACTER BLOCKING & PERFORMANCE:\n{c2_name} turns around slowly, resting one hand on the edge of the surface as their eyes lock onto {c1_name} with an unflinching gaze. A heavy silence settles over the space before {c2_name} speaks.\n\nDIALOGUE & DIRECTION:\n{c2_name.upper()}\n(low, resonant voice; chin tilted slightly upward)\n\"Well, plans change, {c1_name}. We have unresolved business, and you knew I wasn't going to walk away.\"\n\nCINEMATOGRAPHY & 35mm OPTICS:\nCinematic 35mm motion picture film still. ARRI Alexa 35, Cooke Anamorphic/i Full Frame 65mm T2.3 lens, ISO 400 35mm film grain, 1:1 key-to-shadow contrast ratio, 3200K warm tungsten key light from camera right, buttery anamorphic background bokeh, unretouched physical skin texture, zero CGI.",
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
            "action_description": f"{c1_name} takes a decisive step closer to {c2_name} in {valid_sec_env}, closing the physical distance to 1 meter. The camera tracks sideways in a low over-the-shoulder arc as friction escalates.",
            "dialogue": f'{c1_name}:\n(vocal volume rises with controlled intensity; desperation masked as anger)\n"{clean_premise} — and you know exactly how this story ends if we don\'t stop now!"',
            "director_notes": f"Vocal volume rises with controlled intensity. Subtext: desperation masked as anger. Actor posture: shoulders squared, leaning into {c2_name}\'s personal space.",
            "characters": [c1_name, c2_name],
            "visual_prompt": f"INT. {valid_sec_env.upper()} - DRAMATIC HIGH-CONTRAST\n\nLOCATION SETUP & ATMOSPHERE:\nA high-stakes scene inside {valid_sec_env.lower()}. Dramatic chiaroscuro lighting cuts across the midground, leaving deep shadow falloff in the corners while the central interaction is intensely lit.\n\nCAMERA & MOVEMENT CHOREOGRAPHY:\nThe camera slowly arcs sideways in an over-the-shoulder tracking movement (FOV 47°), maintaining tight composition on the 1-meter physical gap separating the two leads.\n\nCHARACTER BLOCKING & PERFORMANCE:\n{c1_name} takes a decisive step closer to {c2_name}, closing the physical distance. The air between them vibrates with unresolved history as {c1_name} leans forward, fingers clenching into a fist.\n\nDIALOGUE & DIRECTION:\n{c1_name.upper()}\n(vocal volume rises with controlled intensity; desperation masked as anger)\n\"{clean_premise} — and you know exactly how this story ends if we don't stop now!\"\n\nCINEMATOGRAPHY & 35mm OPTICS:\nCinematic 35mm motion picture film still. Two-shot over-the-shoulder perspective. ARRI Alexa 35, Panavision C-Series 50mm T2.0 lens, ISO 400 35mm film grain, high-contrast chiaroscuro lighting, razor-sharp focal plane on leading subject, unretouched physical skin texture, zero CGI.",
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
            "action_description": f"Extreme close-up of {c2_name}'s face as the truth hits. The camera holds steady in a tight 18° compression macro frame as a subtle muscle twitch runs along their jawline.",
            "dialogue": f'{c2_name}:\n(dangerous calm; breath shortens, lips part slightly)\n"Then don\'t push me any further, {c1_name}. Because once this line is crossed, there\'s no turning back."',
            "director_notes": f"Micro-expression masterclass: breath shortens, lips part slightly before speaking. Deliver with dangerous calm.",
            "characters": [c2_name],
            "visual_prompt": f"INT. {valid_sec_env.upper()} - EXTREME TIGHT CLOSE-UP\n\nLOCATION SETUP & ATMOSPHERE:\nTight macro atmosphere focusing on performance. Razor rim lighting cuts across cheekbones and jawline against a pitch-dark background.\n\nCAMERA & MOVEMENT CHOREOGRAPHY:\nThe camera holds static in an extreme 18° portrait compression macro shot, anchored 1.5 meters from the actor's eyes.\n\nCHARACTER BLOCKING & PERFORMANCE:\nExtreme close-up of {c2_name}'s face as the truth hits. Their pupils contract slightly, a subtle muscle twitch running along their jawline while shadow cuts across one side of their face.\n\nDIALOGUE & DIRECTION:\n{c2_name.upper()}\n(dangerous calm; breath shortens, lips part slightly)\n\"Then don't push me any further, {c1_name}. Because once this line is crossed, there's no turning back.\"\n\nCINEMATOGRAPHY & 35mm OPTICS:\nCinematic 35mm motion picture film still. ARRI Alexa 35, Leica Summilux-C 85mm T1.4 lens, ISO 400 35mm film grain, razor-edge lighting highlighting facial features, razor-thin depth of field where only the eyes are in sharp focus, unretouched skin detail, zero CGI.",
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
            "action_description": f"{c1_name} stands firm against the fading dusk light in {valid_env}. The camera slowly tilts upward from a low angle as warm golden hour sun bleeds through the glass, illuminating her face.",
            "dialogue": f'{c1_name}:\n(undeniable emotional weight; chin high, unblinking gaze)\n"This is our last chance to get this right, {c2_name}. Neither of us gets a second take."',
            "director_notes": f"Deliver with undeniable emotional weight and gravitas. Actor posture: chin high, unblinking gaze.",
            "characters": [c1_name],
            "visual_prompt": f"INT. {valid_env.upper()} AT DUSK - HERO CLOSE-UP\n\nLOCATION SETUP & ATMOSPHERE:\nSweeping architectural interior at dusk. Warm 2800K golden hour sunlight bleeds through high windows, casting an angelic amber glow across {c1_name} while cool blue shadow fills the background.\n\nCAMERA & MOVEMENT CHOREOGRAPHY:\nThe camera slowly tilts upward from a low-angle 29° hero perspective, elevating {c1_name}'s presence against the dramatic sky.\n\nCHARACTER BLOCKING & PERFORMANCE:\n{c1_name} stands firm against the fading dusk light, holding her ground as the final revelation settles between them. Her face is partially illuminated by the warm golden hour sun.\n\nDIALOGUE & DIRECTION:\n{c1_name.upper()}\n(undeniable emotional weight; chin high, unblinking gaze)\n\"This is our last chance to get this right, {c2_name}. Neither of us gets a second take.\"\n\nCINEMATOGRAPHY & 35mm OPTICS:\nCinematic 35mm motion picture film still. Low angle hero close-up framing. ARRI Alexa 35, Cooke Anamorphic 65mm T2.3 lens, ISO 400 35mm film grain, 2800K golden hour sunlight key, buttery anamorphic lens flare, unretouched tactile skin texture, zero CGI.",
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
            "action_description": f"Both {c1_name} and {c2_name} remain motionless in {valid_env}, framed against the sweeping architectural backdrop as sunset shadows stretch across the space. The camera slowly pulls back into a 107° master wide shot as the scene freezes in high tension.",
            "dialogue": f'{c2_name}:\n(final resonant beat; hold frame 3 seconds after delivery)\n"We\'ll see about that."',
            "director_notes": f"Hold final master frame for 3 full seconds after line delivery before slow fade to black.",
            "characters": [c1_name, c2_name],
            "visual_prompt": f"INT. {valid_env.upper()} - SUNSET MASTER OUTRO\n\nLOCATION SETUP & ATMOSPHERE:\nSweeping master wide view of {valid_env.lower()} at sunset. Long dramatic sunset silhouettes stretch across the polished architectural floor as ambient golden spill illuminates the entire space.\n\nCAMERA & MOVEMENT CHOREOGRAPHY:\nThe camera slowly pulls back into a sweeping 107° ultra-wide master perspective, framing both characters against the vast location backdrop.\n\nCHARACTER BLOCKING & PERFORMANCE:\nBoth {c1_name} and {c2_name} remain motionless in the space, framed against the sweeping architectural backdrop as sunset shadows stretch across the space, freezing the final moment in high dramatic tension.\n\nDIALOGUE & DIRECTION:\n{c2_name.upper()}\n(final resonant beat; hold frame 3 seconds after delivery)\n\"We'll see about that.\"\n\nCINEMATOGRAPHY & 35mm OPTICS:\nCinematic 35mm motion picture film master establishing shot. ARRI Alexa 35, ARRI Master Anamorphic 28mm T1.9 lens, ISO 400 35mm film grain, golden hour ambient sunset spill, organic deep architectural focus, zero CGI, zero 3D render.",
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
