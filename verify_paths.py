from execution.load_assets import load_assets
import os

print("--- Verifying Asset Paths ---")
assets = load_assets()

# Check Vibes
print(f"\n[Vibes]: Found {len(assets['vibes'])} items.")
first_vibe = list(assets['vibes'].keys())[0] if assets['vibes'] else "None"
print(f"Sample Vibe: {first_vibe} -> {assets['vibes'].get(first_vibe)}")

# Check Outfits
print(f"\n[Outfits]: Found {len(assets['outfits'])} items.")
# Try to find a specific one if possible, or just print first
first_outfit = list(assets['outfits'].keys())[0] if assets['outfits'] else "None"
print(f"Sample Outfit: {first_outfit} -> {assets['outfits'].get(first_outfit)}")

# Check Characters
print(f"\n[Characters]: Found {len(assets['characters'])} items.")
first_char = list(assets['characters'].keys())[0] if assets['characters'] else "None"
print(f"Sample Character: {first_char} -> {assets['characters'].get(first_char)}")

print("\n--- Integrity Check ---")
if os.path.isabs(assets['outfits'].get(first_outfit, "relative")):
    print("✅ Paths are ABSOLUTE. Multimodal Vision will work.")
else:
    print("❌ Paths are RELATIVE. Multimodal Vision will FAIL.")
