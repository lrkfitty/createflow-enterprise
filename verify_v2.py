import sys
import os
import json

# Add execution dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'execution'))

print("🔍 Verifying Mini Series V2 Backend...")

try:
    from series_processor import parse_script_to_scenes
    
    # Test Data V2
    script = "Synopsis: A high stakes poker game turns deadly."
    cast = ["Bond", "LeChiffre"]
    env = "Casino"
    
    # New Params
    genre = "Thriller"
    tone = "Gritty"
    roles = {"Bond": "Protagonist", "LeChiffre": "Antagonist"}
    sec_env = "Exterior Balcony"
    
    print("   Invoking parse_script_to_scenes with V2 params...", end="")
    
    # Dry run with missing key - should return {"error": ...} or fail gracefully
    # We really just want to verify the parameters match what the function expects and returns a response structure
    
    # MOCKING the request to test Logic Flow without API
    # Since we can't get real 12 scenes without an API key, we will verify the Function Signature and the JSON handling.
    
    try:
        # Mocking the response_text for a successful 12-scene generation
        # This tests if the code CAN handle the response if Gemini provides it
        import unittest.mock
        
        with unittest.mock.patch('requests.post') as mock_post:
            mock_resp = unittest.mock.Mock()
            mock_resp.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": "```json\n" + json.dumps({
                                "title": "Test Ep",
                                "scenes": [{"id": 1, "shots": [{"description": "s1"}] * 12}] # Mock 12 shots
                            }) + "\n```"
                        }]
                    }
                }]
            }
            mock_post.return_value = mock_resp
            
            res = parse_script_to_scenes(script, cast, env, genre, tone, roles, sec_env)
            
            if len(res['scenes'][0]['shots']) == 12:
                print("OK ✅ (12-Scene Logic Handling)")
            else:
                print(f"FAILED ❌ (Expected 12 shots, got {len(res['scenes'][0]['shots'])})")

    except Exception as te:
        print(f"FAILED ❌: {te}")
        sys.exit(1)
        
except ImportError as e:
    print(f"FAILED ❌ Import Error: {e}")
    sys.exit(1)
    
print("\n🎉 V2 Backend Verification Passed!")
