import os
import json

ASSET_DIR = "assets"
MANIFEST_FILE = "assets_manifest.json"

def generate_manifest():
    """
    Scans local assets/ folder and creates a flatten JSON map.
    {
       "Characters/Shay.png": "s3-url-stub",
       ...
    }
    Actually, we just need the list of relative paths.
    """
    if not os.path.exists(ASSET_DIR):
        print(f"❌ '{ASSET_DIR}' not found. Cannot generate manifest.")
        return

    print(f"📂 Scanning '{ASSET_DIR}'...")
    
    # We want to mimic the structure load_assets expects.
    # But load_assets logic is complex (it builds categories).
    # So we should just dump the file tree, and let load_assets logic rebuild categories from the tree.
    
    file_tree = []
    
    for root, dirs, files in os.walk(ASSET_DIR):
        for file in files:
            if file.startswith("."): continue
            if not file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')): continue
            
            # relative path from assets root
            # e.g. "Characters/Shay/IMG_001.png"
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, "assets") # relative to assets folder
            
            file_tree.append(rel_path)
            
    with open(MANIFEST_FILE, "w") as f:
        json.dump(file_tree, f, indent=2)
        
    print(f"✅ Manifest saved to {MANIFEST_FILE} ({len(file_tree)} items).")
    print("👉 Commit this file to Git so the Cloud App can see the assets!")

if __name__ == "__main__":
    generate_manifest()
