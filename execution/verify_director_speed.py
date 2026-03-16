import sys
import os
import time
sys.path.append(os.getcwd())
from execution.series_processor import parse_script_to_scenes

print("--- TESTING DIRECTOR AI SPEED ---")

# Mock Data
script = "INT. ALIEN BAR - NIGHT. Shay and Chels are drinking neon cocktails."
cast = ["Shay", "Chels"]
# Use dummy URLs that would normally take time if sequential
# Note: Since we don't have real signed URLs without the app, we can just test the function call logic.
# Actual latency speedup happens when URLs are involved.
# For this test, we verify it runs without error and the threading logic works.

print("Starting Dry Run...")
start = time.time()
# Note: This will actually call Gemini, so we expect some latency from the model.
try:
    result = parse_script_to_scenes(script, cast, "Alien Bar")
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print("✅ Success!")
        print(f"Output Scenes: {len(result.get('scenes', []))}")
except Exception as e:
    print(f"❌ Exception: {e}")

print(f"--- Total Time: {time.time() - start:.2f}s ---")
