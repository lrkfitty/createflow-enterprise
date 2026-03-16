
import os
import sys
import time
from PIL import Image

# Add execution dir
sys.path.append(os.path.join(os.getcwd(), 'execution'))

from generate_image import generate_image_from_prompt

def create_dummy_image(filename):
    print(f"Creating dummy 4k image: {filename}")
    img = Image.new('RGB', (4000, 3000), color = 'blue')
    img.save(filename)
    return filename

def test_generation_speed():
    # Setup dummy assets
    assets = []
    for i in range(3):
        fname = f"dummy_gen_test_{i}.jpg"
        create_dummy_image(fname)
        assets.append({"path": fname, "label": f"Reference Character {i}"})
    
    print("⚡ Starting Generation Speed Test...")
    start_time = time.time()
    
    # Mock payload
    payload = {
        "positive_prompt": "A test image",
        "aspect_ratio": "1:1",
        "assets": assets
    }
    
    # Run generation
    # Note: This might fail at the API call stage if no key, but we care about the logs before that.
    try:
        result = generate_image_from_prompt(payload, output_folder="output/test")
    except Exception as e:
        print(f"Generation failed (expected if no API key): {e}")
        result = {"logs": str(e), "status": "failed"}
        
    end_time = time.time()
    print(f"Total time (including potential API timeout/call): {end_time - start_time:.2f}s")
    
    # Analyze Logs
    logs = result.get("logs", "")
    print("\n--- LOG ANALYSIS ---")
    
    if "Parallel processing" in logs:
        print("✅ Parallel Processing Detected")
    else:
        print("❌ Parallel Processing NOT Detected")
        
    if "Resized" in logs and "to 1280" in logs: 
        print("✅ Resizing Detected (1280px or similar)")
    elif "Resized" in logs:
         # Fallback if the string formatting varies slightly
         print(f"✅ Resizing Log Found: {logs}")
    else:
        print("❌ Resizing NOT Detected in logs")

    # Clean up
    for a in assets:
        if os.path.exists(a["path"]):
            os.remove(a["path"])

if __name__ == "__main__":
    test_generation_speed()
