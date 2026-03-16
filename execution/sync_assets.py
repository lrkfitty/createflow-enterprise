import os
import json
import boto3
import mimetypes
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")
MANIFEST_PATH = "assets_manifest.json"
ASSETS_ROOT = "assets"

def sync_assets():
    print(f"🔄 Starting Asset Sync to {BUCKET_NAME}...")
    
    # 1. Load Manifest
    existing_assets = set()
    manifest_list = []
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r") as f:
            manifest_list = json.load(f)
            existing_assets = set(manifest_list)
    
    print(f"📊 Current Manifest Count: {len(existing_assets)}")
    
    # 2. Setup S3
    s3 = boto3.client('s3', region_name=REGION)
    
    new_assets = []
    
    # 3. Walk Directory
    # We only care about "AI Content Creators" folder typically, but let's scan all valid assets
    # The manifest paths start with "AI Content Creators/..." usually.
    # So if we walk "assets", we need to be careful about the relative path.
    
    # Let's assume the user put everything in "assets/AI Content Creators"
    scan_root = os.path.join(ASSETS_ROOT, "AI Content Creators")
    if not os.path.exists(scan_root):
        print(f"❌ Error: {scan_root} does not exist.")
        return

    for root, dirs, files in os.walk(scan_root):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and not file.startswith('._'):
                full_path = os.path.join(root, file)
                
                # Calculate relative path from 'assets' folder
                # e.g. assets/AI Content Creators/File.jpg -> AI Content Creators/File.jpg
                rel_path = os.path.relpath(full_path, ASSETS_ROOT)
                
                # FORCE UPLOAD (Fix Permissions)
                if rel_path not in existing_assets:
                # if True:
                    print(f"🆕 Found New Asset: {rel_path}")
                    
                    # Upload to S3
                    try:
                        content_type, _ = mimetypes.guess_type(full_path)
                        if not content_type: content_type = 'application/octet-stream'
                        
                        s3.upload_file(
                            full_path, 
                            BUCKET_NAME, 
                            f"assets/{rel_path}", # S3 Key matches manifest path + assets prefix for cloud
                            ExtraArgs={'ContentType': content_type}
                        )
                        print(f"   ☁️ Uploaded to S3")
                        
                        new_assets.append(rel_path)
                        existing_assets.add(rel_path)
                        
                    except Exception as e:
                        print(f"   ❌ Upload Failed: {e}")

    # 4. Update Manifest
    if new_assets:
        print(f"📝 Adding {len(new_assets)} new items to manifest...")
        updated_list = sorted(list(existing_assets)) # Sort for cleanliness
        
        with open(MANIFEST_PATH, "w") as f:
            json.dump(updated_list, f, indent=2)
            
        print("✅ Manifest Updated.")
    else:
        print("✅ No new assets to sync.")

if __name__ == "__main__":
    sync_assets()
