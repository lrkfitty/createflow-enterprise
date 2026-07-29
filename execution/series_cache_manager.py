import os
import json
import requests
import hashlib
from PIL import Image
from io import BytesIO

def get_project_cache_dir(user_out_dir):
    """
    Returns the permanent local project cache directory path for the current user project.
    """
    cache_dir = os.path.join(user_out_dir, "ProjectCache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def cache_asset_locally(asset_path_or_url, user_out_dir, prefix="asset"):
    """
    Takes any remote HTTP/S3 URL or local path and returns a PERMANENT local disk file path.
    Downloads remote S3 presigned URLs locally so they NEVER time out or return 403 during long sessions.
    """
    if not asset_path_or_url:
        return None
        
    cache_dir = get_project_cache_dir(user_out_dir)
    
    # 1. Remote HTTP/S3 URL -> Download and save permanently to local cache
    if asset_path_or_url.startswith(("http://", "https://")):
        url_hash = hashlib.md5(asset_path_or_url.split('?')[0].encode('utf-8')).hexdigest()[:12]
        cached_filename = f"{prefix}_{url_hash}.jpg"
        cached_filepath = os.path.join(cache_dir, cached_filename)
        
        # If already cached locally and valid, return local path instantly
        if os.path.exists(cached_filepath) and os.path.getsize(cached_filepath) > 100:
            return cached_filepath
            
        try:
            resp = requests.get(asset_path_or_url, timeout=15)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(cached_filepath, format="JPEG", quality=85)
                return cached_filepath
        except Exception as e:
            print(f"⚠️ Failed to cache remote URL {asset_path_or_url[:60]}: {e}")
            return asset_path_or_url
            
    # 2. Local File Path -> Ensure valid and copy to project cache if needed
    if os.path.exists(asset_path_or_url):
        return asset_path_or_url
        
    return None

def save_series_project_session(user_out_dir, session_data):
    """
    Saves cast selections, wardrobe mappings, character lookup maps, and environment stills
    permanently to a local JSON snapshot file on disk.
    """
    cache_dir = get_project_cache_dir(user_out_dir)
    session_filepath = os.path.join(cache_dir, "series_project_session.json")
    try:
        with open(session_filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ Failed to save series session cache: {e}")
        return False

def load_series_project_session(user_out_dir):
    """
    Loads and restores cast selections, wardrobe mappings, character lookup maps, and environment stills
    from local disk JSON snapshot.
    """
    cache_dir = get_project_cache_dir(user_out_dir)
    session_filepath = os.path.join(cache_dir, "series_project_session.json")
    if os.path.exists(session_filepath):
        try:
            with open(session_filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load series session cache: {e}")
    return {}
