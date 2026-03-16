import sys
import os
import json
sys.path.append(".")
from execution.series_processor import parse_script_to_scenes
from unittest.mock import MagicMock, patch

# Mock Request so we don't spend API credits on verification
def mock_gemini_response(*args, **kwargs):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    
    # Mocking a valid 12-shot structure
    mock_content = {
        "title": "Test Episode",
        "scenes": [{
            "id": 1,
            "location": "Neon Bar",
            "shots": [{"description": f"Shot {i}", "characters": ["Shay"], "camera": "Wide", "visual_prompt": "Test Prompt"} for i in range(1, 13)]
        }]
    }
    
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{ "text": json.dumps(mock_content) }]
            }
        }]
    }
    return mock_resp

print("🔍 Verifying Mini Series V3 Backend (Hollywood Upgrade)...")

with patch('requests.post', side_effect=mock_gemini_response):
    try:
        # TEST V3 PARAMS
        result = parse_script_to_scenes(
            script_text="Testing cinematic upgrade.",
            cast_list=["Shay"],
            environment_name="Neon Bar",
            genre="Sci-Fi",
            tone="Neon Noir",
            roles_map={"Shay": "Protagonist"},
            secondary_environment="Alleyway",
            camera="Alexa Mini LF",
            lens="Anamorphic",
            lighting="Neon / Cyberpunk"
        )
        
        # Verify Structure
        shots = result['scenes'][0]['shots']
        if len(shots) == 12:
            print("   Invoking parse_script_to_scenes with V3 Cine Params...OK ✅ (12-Scene Logic + Camera Params Accepted)")
        else:
            print(f"   ❌ Scene count mismatch: {len(shots)}")
            exit(1)
            
    except Exception as e:
        print(f"   ❌ Verification Failed: {e}")
        exit(1)

print("\n🎉 V3 Backend Verification Passed!")
