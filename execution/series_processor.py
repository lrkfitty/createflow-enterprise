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
    You are a World-Class HOLLYWOOD SHOWRUNNER, MASTER DIRECTOR, and SCRIPTWRITER specializing in HIGGSFIELD SEEDANCE V2 WORKFLOW.
    Your job is to transform a premise/synopsis into a complete, masterfully written episode script with FULL CHARACTER DIALOGUE, physical performance cues, and precise 35mm visual prompts.
    
    CRITICAL MANDATE - CHARACTER DIALOGUE FOR EVERY SHOT:
    1. WRITE REAL DRAMATIC DIALOGUE:
       - Every shot featuring characters MUST have explicit, high-level dramatic dialogue lines (e.g. "JAZI: 'We shouldn't be here... look at those windows.'").
       - Include direct speech, subtext, vocal delivery tone, and micro-expression acting cues.
       - NEVER leave dialogue empty for character shots!
    2. VISUAL PROMPT COMPOSITION:
       - Structure 'visual_prompt' to include the Scene Action + Character Dialogue + Cinematography Specs.
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
    4. ACTING & PERFORMANCE THROUGH MUSCLE MOVEMENT:
       - Describe physical muscle movements: "jaw tightens, eyes drop to the table, breath shortens, knuckles whiten on glass".

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
               "action_description": "Jazi turns slowly, her jaw tightening as she looks across the room.",
               "dialogue": "JAZI: \"You thought I wouldn't find out? Take a look around.\"",
               "director_notes": "Deliver line cold with zero vocal fluctuation. Keep gaze locked on Lima's eyes.",
               "characters": ["Jazi"],
               "visual_prompt": "ACTION: Jazi turns slowly, her jaw tightening as she looks across the room.\nDIALOGUE:\nJAZI: \"You thought I wouldn't find out? Take a look around.\"\nDIRECTOR NOTES: Deliver line cold with zero vocal fluctuation.\nCINEMATOGRAPHY:\nCinematic 35mm film still. Jazi in medium close-up. CAMERA: FOV 29°, eye-level, operator anchored 2 meters. ISO 400 35mm film grain, 3200K tungsten key light, shallow depth of field. Unretouched physical skin texture, zero CGI.",
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

    # 3. DIRECT PRODUCTION NARRATIVE ENGINE (Guarantees Full 3-Scene, 6-Shot Narrative Arc)
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
            "action_description": f"{c1_name} enters {valid_env}, noticing {c2_name} across the room as tension fills the air.",
            "dialogue": f'{c1_name}: "I didn\'t expect to see you here today."',
            "director_notes": f"Deliver line with guarded curiosity. Keep physical posture tall.",
            "characters": [c1_name],
            "visual_prompt": f"ACTION: {c1_name} enters {valid_env}.\nDIALOGUE:\n{c1_name}: \"I didn't expect to see you here today.\"\nDIRECTOR NOTES: Deliver line with guarded curiosity.\nCINEMATOGRAPHY:\nCinematic 35mm film still of {c1_name} at {valid_env}. CAMERA: FOV 84°, Wide Shot, eye-level. ISO 400 35mm film grain, 5600K daylight key, deep focus. Unretouched physical skin texture, zero CGI.",
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
            "action_description": f"{c2_name} turns around slowly, eyes locking onto {c1_name} with an unflinching gaze.",
            "dialogue": f'{c2_name}: "Well, plans change. We have unresolved business."',
            "director_notes": f"Deliver cold and direct. No smiling.",
            "characters": [c2_name],
            "visual_prompt": f"ACTION: {c2_name} turns around slowly.\nDIALOGUE:\n{c2_name}: \"Well, plans change. We have unresolved business.\"\nDIRECTOR NOTES: Deliver cold and direct.\nCINEMATOGRAPHY:\nCinematic 35mm film still of {c2_name} at {valid_env}. CAMERA: FOV 29°, Medium Close-Up, eye-level. ISO 400 35mm film grain, 3200K tungsten key, shallow depth of field. Unretouched physical skin texture, zero CGI.",
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
            "action_description": f"{c1_name} takes a step closer to {c2_name}, resting a hand on the surface as friction escalates.",
            "dialogue": f'{c1_name}: "{clean_premise} — and you know exactly how this ends!"',
            "director_notes": f"Vocal volume rises slightly. Physical distance decreases to 1 meter.",
            "characters": [c1_name, c2_name],
            "visual_prompt": f"ACTION: {c1_name} steps closer to {c2_name}.\nDIALOGUE:\n{c1_name}: \"{clean_premise} — and you know exactly how this ends!\"\nDIRECTOR NOTES: Vocal volume rises slightly.\nCINEMATOGRAPHY:\nCinematic 35mm film still of {c1_name} and {c2_name} at {valid_sec_env}. CAMERA: FOV 47°, Medium Two-Shot, eye-level. ISO 400 35mm film grain, chiaroscuro lighting. Unretouched physical skin texture, zero CGI.",
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
            "action_description": f"Close-up of {c2_name}'s expression as jaw tightens and breathing quickens.",
            "dialogue": f'{c2_name}: "Then don\'t push me any further."',
            "director_notes": f"Micro-expression acting: eyes narrow, breathing heavy.",
            "characters": [c2_name],
            "visual_prompt": f"ACTION: Tight close-up of {c2_name}'s expression.\nDIALOGUE:\n{c2_name}: \"Then don't push me any further.\"\nDIRECTOR NOTES: Micro-expression acting.\nCINEMATOGRAPHY:\nCinematic 35mm film still of {c2_name}. CAMERA: FOV 18°, Tight Close-Up. ISO 400 35mm film grain, razor shallow depth of field. Unretouched physical skin texture, zero CGI.",
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
            "action_description": f"{c1_name} holds position, refusing to back down as the revelation lands.",
            "dialogue": f'{c1_name}: "This is our last chance to get this right."',
            "director_notes": f"Deliver line with emotional weight and certainty.",
            "characters": [c1_name],
            "visual_prompt": f"ACTION: {c1_name} holds position.\nDIALOGUE:\n{c1_name}: \"This is our last chance to get this right.\"\nDIRECTOR NOTES: Deliver with emotional weight.\nCINEMATOGRAPHY:\nCinematic 35mm film still of {c1_name} at {valid_env}. CAMERA: FOV 29°, Low Angle Hero Close-Up. ISO 400 35mm film grain, high contrast key, shallow depth of field. Unretouched physical skin texture, zero CGI.",
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
            "action_description": f"Both {c1_name} and {c2_name} stand locked in a tense standoff as the scene fades out.",
            "dialogue": f'{c2_name}: "We\'ll see about that."',
            "director_notes": f"Hold final frame for 3 seconds after line delivery.",
            "characters": [c1_name, c2_name],
            "visual_prompt": f"ACTION: Both {c1_name} and {c2_name} stand locked in a tense standoff.\nDIALOGUE:\n{c2_name}: \"We'll see about that.\"\nDIRECTOR NOTES: Hold final frame for 3 seconds.\nCINEMATOGRAPHY:\nCinematic 35mm film master establishing shot of {c1_name} and {c2_name} at {valid_env}. CAMERA: FOV 107°, Ultra-Wide Establishing, golden hour lighting.",
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
