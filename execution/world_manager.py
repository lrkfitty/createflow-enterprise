import json
import os
try:
    from execution.load_assets import load_assets
except ImportError:
    # Fallback for relative import if running from different context
    from load_assets import load_assets

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'world_db.json')

def load_world_db():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def save_world_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def add_asset(category, key, data):
    db = load_world_db()
    if category not in db:
        db[category] = {}
    
    db[category][key] = data
    save_world_db(db)
    return True

def get_scenarios():
    db = load_world_db()
    return db.get("scenarios", {})

def get_assets_by_category(category, user_assets_dir=None):
    # 1. Load from Database (Rich Metadata)
    db = load_world_db()
    db_assets = db.get(category, {})
    
    # 2. Load from Filesystem (Raw Paths)
    # PASS user_assets_dir here!
    fs_data = load_assets(user_assets_dir=user_assets_dir)
    fs_assets = fs_data.get(category, {})
    
    # 3. Merge: Database overrides Filesystem if keys conflict
    # This allows users to "Upgrade" a file asset to a DB asset by adding metadata
    merged = {**fs_assets, **db_assets}
    return merged
