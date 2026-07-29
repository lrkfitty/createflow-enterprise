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
    # Try Atlas Cloud API first (Atlas Key - zero quota limits)
    atlas_key = os.getenv("ATLASCLOUD_API_KEY")
    if atlas_key:
        atlas_models = ["google/gemini-2.5-flash", "google/gemini-2.0-flash", "openai/gpt-4o-mini", "deepseek-ai/deepseek-v4-flash"]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {atlas_key}"
        }
        for m_name in atlas_models:
            payload = {
                "model": m_name,
                "messages": [{"role": "user", "content": prompt}]
            }
            try:
                resp = requests.post("https://api.atlascloud.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    res_json = resp.json()
                    text = res_json['choices'][0]['message']['content']
                    text = text.replace('```json', '').replace('```', '').strip()
                    
                    start_bracket = min([i for i in (text.find('['), text.find('{')) if i != -1], default=-1)
                    end_bracket = max([text.rfind(']'), text.rfind('}')])
                    if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
                        text = text[start_bracket:end_bracket+1]

                    params = json.loads(text)
                    if isinstance(params, dict):
                        for key, val in params.items():
                            if isinstance(val, list):
                                params = val
                                break

                    if isinstance(params, list) and len(params) >= 1:
                        clean_prompts = []
                        for item in params:
                            if isinstance(item, str):
                                clean_prompts.append(item.strip())
                            elif isinstance(item, dict):
                                str_val = item.get("prompt") or item.get("description") or item.get("text") or list(item.values())[0]
                                clean_prompts.append(str(str_val).strip())
                        
                        while len(clean_prompts) < 4:
                            clean_prompts.append(clean_prompts[-1] if clean_prompts else prompt)
                            
                        return clean_prompts[:4]
            except Exception as atlas_e:
                print(f"Atlas Cloud LLM Warning ({m_name}): {atlas_e}")
                continue

    # Fallback: Direct Google API Key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return ["Error: Missing ATLASCLOUD_API_KEY and GOOGLE_API_KEY", "", "", ""]
        
    models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-flash-latest', 'gemini-pro-latest', 'gemini-2.0-flash-001', 'gemini-2.5-pro']
    headers = { "Content-Type": "application/json" }
    payload = {
        "contents": [{
            "parts": [{ "text": prompt }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    last_error_msg = "Unknown error"
    for m_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code != 200:
                last_error_msg = f"HTTP {response.status_code}: {response.text}"
                continue
                
            res_json = response.json()
            if 'candidates' not in res_json or not res_json['candidates']:
                last_error_msg = f"No candidates: {res_json.get('promptFeedback', res_json)}"
                continue
                
            text = res_json['candidates'][0]['content']['parts'][0]['text']
            text = text.replace('```json', '').replace('```', '').strip()
            
            start_bracket = min([i for i in (text.find('['), text.find('{')) if i != -1], default=-1)
            end_bracket = max([text.rfind(']'), text.rfind('}')])
            if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
                text = text[start_bracket:end_bracket+1]

            try:
                params = json.loads(text)
            except json.JSONDecodeError:
                return ["Error parsing JSON", text, "", ""]

            if isinstance(params, dict):
                for key, val in params.items():
                    if isinstance(val, list):
                        params = val
                        break
            
            if isinstance(params, list) and len(params) >= 1:
                clean_prompts = []
                for item in params:
                    if isinstance(item, str):
                        clean_prompts.append(item.strip())
                    elif isinstance(item, dict):
                        str_val = item.get("prompt") or item.get("description") or item.get("text") or list(item.values())[0]
                        clean_prompts.append(str(str_val).strip())
                
                while len(clean_prompts) < 4:
                    clean_prompts.append(clean_prompts[-1] if clean_prompts else prompt)
                    
                return clean_prompts[:4]
            else:
                return ["Error parsing response", str(text), "", ""]
                
        except Exception as e:
            last_error_msg = str(e)
            continue
            
    return [f"API Error after trying all models. Last error: {last_error_msg}", "", "", ""]
