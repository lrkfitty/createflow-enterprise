"""
Generate photorealistic UI icons for the visual grid selectors.
Uses Gemini 2.0 Flash Image Generation via REST API.
Run: .venv/bin/python3 execution/generate_ui_icons.py
"""
import os
import sys
import time
import json
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# -- Config --
ICONS_ROOT = Path(__file__).parent.parent / "assets" / "ui_icons"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp-image-generation:generateContent"

CATEGORIES = {
    "camera_angles": {
        "Eye Level (Neutral)":        "eye-level camera angle, woman in neutral standing pose, camera at eye height",
        "Low Angle (Heroic/Power)":   "dramatic low angle shot looking up at confident woman, heroic powerful perspective",
        "High Angle (Vulnerable/CDM)":"high angle shot looking down at woman from above, vulnerable perspective",
        "Bird's Eye View (Overhead)": "bird's eye view looking straight down at woman on dark floor, overhead perspective",
        "Worm's Eye View (Ground Level)": "extreme low ground-level shot looking up at woman towering above",
        "Dutch Angle (Dynamic/Uneven)": "tilted dutch angle shot of woman, dynamic diagonal framing",
        "Profile / Side View":        "perfect side profile view of woman, clean silhouette",
        "Over the Shoulder":          "over-the-shoulder shot, camera behind one person looking at subject",
        "Point of View (POV)":        "first person POV perspective, hands visible reaching forward, immersive viewpoint",
        "Selfie Angle (High)":        "selfie angle from slightly above, woman arm extended, warm casual lighting",
        "Mirror Selfie":              "mirror selfie shot, woman photographing reflection, phone visible in mirror",
        "Straight On (Talking Head)": "straight-on centered talking head framing, woman facing camera directly",
        "Slightly Off-Center (Interview)": "slightly off-center interview framing, subject offset to one side",
        "3/4 View (Flattering Angle)":"classic three-quarter view angle, woman turned 45 degrees, flattering portrait",
    },
    "shot_types": {
        "Close Up":         "close-up shot of woman's face filling frame, sharp facial detail",
        "Medium Shot":      "medium shot of woman from waist up, balanced composition",
        "Full Body":        "full body shot of woman head to toe, fashion photography",
        "Wide Shot":        "wide shot showing woman small in large environment, establishing shot",
        "Extreme Close Up": "extreme close-up of woman's eyes and partial face, intense detail",
        "Cowboy Shot":      "cowboy shot of woman from mid-thigh up, western film style framing",
        "Overhead":         "overhead shot looking straight down, dramatic top-down view",
    },
    "lighting": {
        "Golden Hour (Warm/Soft)":       "golden hour warm sunset lighting, soft orange glow on face, backlit, dreamy",
        "Blue Hour (Moody/Cold)":        "blue hour twilight, cool blue moody tones, ethereal atmosphere",
        "Noon (Harsh/High Contrast)":    "harsh noon sunlight, strong shadows under eyes and nose, high contrast",
        "Midnight (Dark/Mystery)":       "midnight darkness, minimal dramatic lighting, mysterious shadows, noir",
        "Studio Lighting (Perfect/Softbox)": "perfect studio softbox lighting, even illumination, beauty lighting",
        "Ring Light (Influencer/Flat)":   "ring light, circular catchlight in eyes, flat even influencer style",
        "Neon (Cyberpunk/Colorful)":      "vibrant neon lighting, pink and blue cyberpunk glow, colorful light on face",
        "Cinematic (Rembrandt/Dramatic)": "Rembrandt lighting, dramatic triangle light on cheek, chiaroscuro, cinematic",
        "Overcast (Diffused/Flat)":       "overcast diffused natural light, soft flat lighting, no harsh shadows",
        "Flash Photography (Direct/Harsh)":"direct flash photography, harsh flat frontal light, paparazzi style",
    },
}


def generate_single_icon(api_key, prompt_detail, filepath, retries=2):
    """Generate a single icon via Gemini REST API."""
    full_prompt = (
        f"Generate a photorealistic cinematic thumbnail photo for a camera settings UI icon. "
        f"The image should show: {prompt_detail}. "
        f"Professional studio quality, dark moody background, square format, clean composition."
    )
    
    url = f"{API_BASE}?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
    }
    
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, timeout=90)
            data = resp.json()
            
            if "candidates" in data:
                for part in data["candidates"][0]["content"]["parts"]:
                    if "inlineData" in part:
                        img_bytes = base64.b64decode(part["inlineData"]["data"])
                        with open(filepath, "wb") as f:
                            f.write(img_bytes)
                        return True, len(img_bytes)
                return False, "No image in response"
            
            error_msg = data.get("error", {}).get("message", str(data)[:200])
            if "RESOURCE_EXHAUSTED" in str(data) or resp.status_code == 429:
                if attempt < retries - 1:
                    print(f"⏳ Rate limited, waiting 30s...", end=" ", flush=True)
                    time.sleep(30)
                    continue
            return False, error_msg
            
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(10)
                continue
            return False, "Timeout"
        except Exception as e:
            return False, str(e)

    return False, "Max retries exceeded"


def generate_icons():
    """Generate all icons."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY not set in .env")
        return

    total = sum(len(v) for v in CATEGORIES.values())
    count = 0
    generated = 0
    skipped = 0
    failed = []

    for category, options in CATEGORIES.items():
        cat_dir = ICONS_ROOT / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📂 {category} ({len(options)} icons)")

        for option_name, prompt_detail in options.items():
            count += 1
            # Safe filename
            safe_name = option_name.lower()
            for char in "()/ &'":
                safe_name = safe_name.replace(char, "_")
            safe_name = safe_name.strip("_")
            while "__" in safe_name:
                safe_name = safe_name.replace("__", "_")
            filepath = cat_dir / f"{safe_name}.png"

            if filepath.exists():
                print(f"  ⏭️  [{count}/{total}] {safe_name} (exists)")
                skipped += 1
                continue

            print(f"  🎨 [{count}/{total}] {safe_name}...", end=" ", flush=True)
            
            success, result = generate_single_icon(api_key, prompt_detail, filepath)
            
            if success:
                size_kb = result // 1024
                print(f"✅ ({size_kb}KB)")
                generated += 1
            else:
                print(f"❌ {result}")
                failed.append(option_name)
            
            time.sleep(4)  # Rate limit spacing

    print(f"\n{'='*50}")
    print(f"✅ Generated: {generated}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"📊 Total: {generated + skipped}/{total}")
    if failed:
        print(f"❌ Failed ({len(failed)}):")
        for f_name in failed:
            print(f"   - {f_name}")
    print(f"📁 Icons at: {ICONS_ROOT}")


if __name__ == "__main__":
    generate_icons()
