"""
Character Pack Generator — 20 Diverse Characters
Generates a front-facing portrait for each character for the free Skool pack.
"""

import os
import sys
import json
import time

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from execution.generate_prompt import generate_prompt_content
from execution.generate_image import generate_image_from_prompt

OUTPUT_DIR = "output/character_pack"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# 20 DIVERSE CHARACTERS
# ─────────────────────────────────────────────
CHARACTERS = [
    {
        "id": 1,
        "name": "Marcus",
        "description": "Black male, late 30s, clean fade haircut, warm brown skin, confident dark eyes, strong jawline, athletic build",
        "outfit": "Tailored charcoal suit, white dress shirt, no tie — sharp entrepreneur energy",
        "vibe": "Modern glass-and-steel office lobby, afternoon light",
        "use_case": "Business / Entrepreneur",
        "shot": "Medium shot, eye-level, confident smile"
    },
    {
        "id": 2,
        "name": "Sofia",
        "description": "Latina female, mid 20s, long wavy dark brown hair, olive skin, bright hazel eyes, petite but toned",
        "outfit": "White fitted blazer, gold hoop earrings, minimalist style",
        "vibe": "Bright airy café with exposed brick and natural light",
        "use_case": "Lifestyle / Coach",
        "shot": "Portrait, warm golden-hour lighting, genuine smile"
    },
    {
        "id": 3,
        "name": "Yuki",
        "description": "East Asian female, early 30s, sleek straight black hair in a low bun, fair porcelain skin, sharp almond eyes, elegant posture",
        "outfit": "Structured cream turtleneck, minimal silver jewelry",
        "vibe": "Minimalist Tokyo-style studio, soft diffused light",
        "use_case": "Fashion / Creator",
        "shot": "Close-up portrait, editorial style"
    },
    {
        "id": 4,
        "name": "Darius",
        "description": "Black male, early 20s, tall athletic build, locs pulled back, deep brown skin, expressive eyes, easy confident smile",
        "outfit": "Oversized graphic hoodie, joggers, fresh sneakers — streetwear",
        "vibe": "Urban basketball court at golden hour",
        "use_case": "Fitness / Sports / Youth",
        "shot": "Wide medium shot, dynamic casual pose"
    },
    {
        "id": 5,
        "name": "Camille",
        "description": "Mixed-race (Black and French) female, late 20s, natural curly auburn hair, medium brown skin, freckles, warm amber eyes",
        "outfit": "Chic Parisian trench coat, beret, simple gold necklace",
        "vibe": "Paris street corner, cobblestone, soft overcast light",
        "use_case": "Travel / Lifestyle",
        "shot": "Medium shot, candid feel, light bokeh background"
    },
    {
        "id": 6,
        "name": "Raj",
        "description": "South Asian male, mid 30s, neat short dark hair, warm golden-brown skin, sharp intelligent eyes, medium build, clean-shaven",
        "outfit": "Smart casual — fitted navy polo, dark chinos, simple watch",
        "vibe": "Tech startup open workspace with exposed ceilings and monitors",
        "use_case": "Tech / SaaS / Professional",
        "shot": "Medium portrait, natural lighting, approachable expression"
    },
    {
        "id": 7,
        "name": "Elena",
        "description": "Eastern European female, 40s, shoulder-length platinum blonde hair, cool pale skin, striking blue-grey eyes, refined features",
        "outfit": "Elegant all-black ensemble — blazer and slim trousers, pearl earrings",
        "vibe": "Upscale hotel lobby, marble floors, warm chandelier light",
        "use_case": "Luxury / Executive",
        "shot": "Full-body medium shot, poised and authoritative"
    },
    {
        "id": 8,
        "name": "Kofi",
        "description": "West African male, late 20s, tall lean build, very dark rich skin, close-cropped hair, broad smile, high cheekbones",
        "outfit": "Vibrant kente-print shirt, tailored fit, modern interpretation",
        "vibe": "Bright outdoor market with colorful fabrics and natural sunlight",
        "use_case": "Culture / Community / Content",
        "shot": "Portrait, vibrant colors, joyful expression"
    },
    {
        "id": 9,
        "name": "Priya",
        "description": "South Asian female, early 30s, long silky black hair worn loose, warm caramel skin, dark expressive eyes, graceful build",
        "outfit": "Contemporary silk blouse in deep jewel tones, tailored pants",
        "vibe": "Modern rooftop at dusk, city skyline behind",
        "use_case": "Wellness / Mindfulness / Brand",
        "shot": "Medium portrait, soft warm lighting, serene expression"
    },
    {
        "id": 10,
        "name": "Jake",
        "description": "White male, mid 30s, tousled sandy brown hair, light skin, hazel eyes, athletic-lean build, rugged outdoorsy look",
        "outfit": "Fitted grey henley, dark jeans, hiking boots",
        "vibe": "Pacific Northwest forest trail, dappled sunlight",
        "use_case": "Outdoor / Adventure / Fitness",
        "shot": "Medium shot, natural candid, wind-swept feel"
    },
    {
        "id": 11,
        "name": "Amara",
        "description": "Nigerian female, mid 20s, shaved head, deep ebony skin, strong bone structure, bold dark eyes, striking and confident",
        "outfit": "Fashion-forward — sculptural white structured top, wide-leg trousers",
        "vibe": "High-fashion studio with stark white walls and dramatic shadows",
        "use_case": "Fashion / Editorial / Bold Brand",
        "shot": "Editorial portrait, high contrast lighting, powerful gaze"
    },
    {
        "id": 12,
        "name": "Carlos",
        "description": "Latino male, 50s, salt-and-pepper short hair, warm tan skin, laugh lines, kind brown eyes, stocky distinguished build",
        "outfit": "Smart casual — open collar linen shirt, blazer, comfortable confidence",
        "vibe": "Warm rustic restaurant terrace, southern European feel",
        "use_case": "Hospitality / Family / Community Leader",
        "shot": "Medium portrait, warm light, welcoming smile"
    },
    {
        "id": 13,
        "name": "Mei Lin",
        "description": "Chinese-American female, late 40s, short stylish bob, silver-streaked black hair, fair skin, sophisticated dark eyes",
        "outfit": "Refined business attire — structured burgundy blazer, silk blouse",
        "vibe": "Corner office, floor-to-ceiling windows, NYC skyline",
        "use_case": "Executive / Finance / Leadership",
        "shot": "Power portrait, confident, arms crossed lightly"
    },
    {
        "id": 14,
        "name": "Tobias",
        "description": "German male, early 20s, tall slim build, disheveled dirty blonde hair, fair skin, round wire-frame glasses, creative intellectual look",
        "outfit": "Indie creative — vintage band tee, corduroy jacket, slim jeans",
        "vibe": "Berlin underground art gallery with neon and graffiti walls",
        "use_case": "Creative / Arts / Gen Z",
        "shot": "Casual medium shot, quirky candid energy"
    },
    {
        "id": 15,
        "name": "Aaliyah",
        "description": "Black female, early 30s, long box braids adorned with gold cuffs, rich dark brown skin, full lips, glowing warm eyes, curves",
        "outfit": "Bodycon earth-tone dress, statement gold jewelry, heels",
        "vibe": "Luxury hotel rooftop pool at sunset, Miami energy",
        "use_case": "Lifestyle / Influencer / Beauty",
        "shot": "Glamour portrait, golden light, radiant expression"
    },
    {
        "id": 16,
        "name": "Hiroshi",
        "description": "Japanese male, 60s, silver cropped hair, distinguished weathered tan skin, calm wise dark eyes, lean composed build",
        "outfit": "Understated luxury — simple linen kimono-style jacket, monochrome",
        "vibe": "Zen garden with raked gravel and cherry blossom trees",
        "use_case": "Wisdom / Wellness / Spiritual / Premium",
        "shot": "Contemplative portrait, serene natural light"
    },
    {
        "id": 17,
        "name": "Zara",
        "description": "Middle Eastern female, mid 20s, thick dark wavy hair, olive-toned skin, large expressive dark eyes, full brows, model features",
        "outfit": "Chic athleisure — matching luxury set in dusty rose, clean sneakers",
        "vibe": "Modern gym studio with natural light and clean white aesthetic",
        "use_case": "Fitness / Health / Wellness Brand",
        "shot": "Dynamic medium shot, energetic confident pose"
    },
    {
        "id": 18,
        "name": "Jerome",
        "description": "Black male, 50s, bald head, full grey beard, deep rich brown skin, strong broad build, commanding calm presence",
        "outfit": "Distinguished casual — dark turtleneck, statement watch, simple but powerful",
        "vibe": "Private library with warm leather and dark wood shelving",
        "use_case": "Mentor / Executive / Wealth / Authority",
        "shot": "Strong portrait, Rembrandt lighting, gravitas"
    },
    {
        "id": 19,
        "name": "Luna",
        "description": "Latina female, early 20s, long ombre hair (dark to caramel), medium tan skin, bright playful green eyes, petite and energetic",
        "outfit": "Colorful boho — floral sundress, layered jewelry, sandals",
        "vibe": "Tropical beach with turquoise water and golden sand",
        "use_case": "Travel / Social Media / Fun Lifestyle",
        "shot": "Bright airy portrait, joy and movement, natural smiling"
    },
    {
        "id": 20,
        "name": "Aiden",
        "description": "Mixed-race (Asian and White) male, mid 20s, medium build, wavy dark hair, light skin with warm undertones, bright grey-blue eyes, clean modern look",
        "outfit": "Tech casual — premium crewneck sweatshirt, slim chinos, clean minimalist",
        "vibe": "Home studio setup with ring light, podcasting / content creator space",
        "use_case": "Content Creator / Podcast / Digital Entrepreneur",
        "shot": "Friendly medium portrait, direct eye contact, approachable"
    }
]


def run():
    results = []
    total = len(CHARACTERS)

    print(f"\n🎨 CreateFlow Character Pack — Generating {total} characters...\n")
    print("=" * 60)

    for char in CHARACTERS:
        idx = char["id"]
        name = char["name"]
        print(f"\n[{idx}/{total}] Generating: {name} — {char['use_case']}")
        print(f"  Vibe: {char['vibe']}")

        try:
            # Step 1: Generate prompt
            prompt_data = generate_prompt_content(
                vibe=char["vibe"],
                outfit=char["outfit"],
                character=char["description"],
                action=char["shot"],
                aspect_ratio="4:5"      # Good for social/pack portraits
            )

            if "Error" in prompt_data.get("positive_prompt", ""):
                raise Exception(f"Prompt error: {prompt_data['positive_prompt']}")

            # Inject character name into prompt for file naming
            prompt_data["character_name"] = name
            prompt_data["image_size"] = "1K"

            # Step 2: Generate image
            char_output_dir = os.path.join(OUTPUT_DIR, f"{idx:02d}_{name}")
            os.makedirs(char_output_dir, exist_ok=True)

            result = generate_image_from_prompt(
                prompt_data=prompt_data,
                output_folder=char_output_dir
            )

            if result["status"] == "success":
                print(f"  ✅ Saved: {result['image_path']}")
                results.append({
                    "id": idx,
                    "name": name,
                    "use_case": char["use_case"],
                    "status": "success",
                    "path": result["image_path"]
                })
            else:
                raise Exception(result.get("logs", "Unknown failure"))

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            results.append({
                "id": idx,
                "name": name,
                "use_case": char["use_case"],
                "status": "failed",
                "error": str(e)
            })

        # Small delay to avoid rate-limiting
        if idx < total:
            time.sleep(1)

    # ─── Summary ───
    print("\n" + "=" * 60)
    success = [r for r in results if r["status"] == "success"]
    failed  = [r for r in results if r["status"] == "failed"]
    print(f"\n✅ Generated: {len(success)}/{total}")
    if failed:
        print(f"❌ Failed:    {len(failed)}/{total}")
        for f in failed:
            print(f"   - {f['name']}: {f.get('error','?')[:80]}")

    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📋 Manifest saved: {manifest_path}")
    print(f"📁 All characters in: {OUTPUT_DIR}/\n")

    return results


if __name__ == "__main__":
    run()
