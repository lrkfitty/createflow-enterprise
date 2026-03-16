
import sys

print("\n--- 🧹 FINAL BUG SWEEP: LOGIC VERIFICATION ---")

# 1. SETUP: Mock Data
char_list = ["Shay", "Shays_boyfriend_full_view"]
cast_lookup_map = {
    "Shay": "/assets/Shay.png",
    "Shays": "/assets/Boyfriend.png" 
}
wardrobe_snapshot = {
    "Shay": "Yellow Top",
    "Shays": "Rick Owens"
}
outfits_db = {
    "Yellow Top": "/assets/YellowTop.png",
    "Rick Owens": "/assets/RickOwens.png"
}

print(f"INPUT: Characters: {char_list}")
print(f"MAP: {cast_lookup_map}")

# 2. RUN LOGIC (Mirrored from app.py V3.6)
final_assets = []
logs = []

for raw_name in char_list:
    logs.append(f"Processing '{raw_name}'...")
    
    # A. Face Resolution
    naive_key = raw_name.split(' ')[0]
    c_path = cast_lookup_map.get(naive_key)
    
    if not c_path:
        if '_' in raw_name:
            norm_key = raw_name.replace('_', ' ').split(' ')[0]
            c_path = cast_lookup_map.get(norm_key)
            if c_path: 
                logs.append(f"  -> Normalized '{raw_name}' to '{norm_key}' found path!")
                naive_key = norm_key
    
    if c_path:
        final_assets.append(f"FACE: {c_path}")
        
        # B. Outfit Resolution
        o_name = wardrobe_snapshot.get(raw_name) # Full Name Check
        if not o_name:
            o_name = wardrobe_snapshot.get(naive_key) # Naive/Norm Key Check
            
        if o_name:
            o_path = outfits_db.get(o_name)
            final_assets.append(f"OUTFIT: {o_name}")
        else:
            logs.append(f"  -> ⚠️ Values to resolve outfit for {raw_name}")

# 3. ASSERTIONS
print("\n--- RESULTS ---")
for l in logs: print(l)
print(f"\nGenerative Assets Payload: {final_assets}")

required = [
    "FACE: /assets/Shay.png",
    "OUTFIT: Yellow Top",
    "FACE: /assets/Boyfriend.png",
    "OUTFIT: Rick Owens"
]

missing = [req for req in required if req not in final_assets]

if not missing:
    print("\n✅ SWEEP PASSED: All logic paths valid. Multi-char + Normalization works.")
else:
    print(f"\n❌ SWEEP FAILED: Missing items: {missing}")
    sys.exit(1)
