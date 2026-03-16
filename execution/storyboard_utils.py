import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def generate_storyboard_prompts(scenario_name, context, model="gemini", camera_settings="", reference_context=""):
    """
    Generates 4 sequential prompts for a storyboard.
    Returns: List of 4 strings.
    """
    
    system_instruction = f"""
    ROLE: You are an ACADEMY AWARD-WINNING HOLLYWOOD DIRECTOR. You are creating a 4-shot storyboard for a visual masterpiece.
    
    SCENARIO: {scenario_name}
    AUTHORITATIVE SCRIPT: {context}
    
    GOAL: Generate 4 sequential, high-end image prompts that tell a story.
    
    DIRECTOR'S RULES:
    1. **CINEMATIC FIDELITY**: Use terms like "Chiaroscuro", "Volumetric Fog", "Arriflex 35mm", "Golden Hour Glow".
    2. **MANDATORY CAMERA & STYLE SETTINGS**: {camera_settings or "Director's Choice"}. You must strictly adhere to these requested camera placements, lighting, angles, and styles for EVERY shot.
    3. **CHARACTER & PROP CONTEXT**: Ensure the following visual assets are present in the scene: {reference_context or 'None specifically requested'}.
    4. **CHARACTER CHEMISTRY**: If "Friends" or "Cast" are mentioned, they are NOT extras. They are co-leads. They should be looking at each other, interacting, and sharing emotions.
    5. **VISUAL CONTINUITY**: Keep the setting and outfits consistent across all 4 shots.
    4. **EVOCATIVE PROMPTS**: Write descriptions that flow like high-end screenplays. Massive detail.
    
    REQUIREMENTS:
    - Return ONLY a JSON list of 4 strings.
    - Example: ["Prompt 1", "Prompt 2", "Prompt 3", "Prompt 4"]
    """
    
    if model == "gemini":
        return _generate_gemini(system_instruction)
    else:
        # Fallback or future expansion
        return _generate_gemini(system_instruction)

def _generate_gemini(prompt):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return ["Error: Missing GOOGLE_API_KEY", "", "", ""]
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = { "Content-Type": "application/json" }
    
    payload = {
        "contents": [{
            "parts": [{ "text": prompt }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        res_json = response.json()
        
        # Extract text
        if 'candidates' not in res_json:
            print(f"❌ Storyboard Gen Error: {res_json.get('promptFeedback', res_json)}")
            return []
            
        text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        # Clean markdown
        text = text.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        try:
            params = json.loads(text)
        except json.JSONDecodeError:
             return ["Error parsing JSON", text, "", ""]

        # Handle Dict wrapper case (e.g. {"prompts": [...]})
        if isinstance(params, dict):
            for key, val in params.items():
                if isinstance(val, list):
                    params = val
                    break
        if isinstance(params, list) and len(params) >= 4:
            return params[:4]
        else:
            return ["Error parsing response", str(text), "", ""]
            
    except Exception as e:
        return [f"API Error: {e}", "", "", ""]
