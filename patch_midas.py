import os

def patch_midas():
    print("🚑 INJECTING DUMMY 'midas' MODULE...")
    
    home = os.path.expanduser("~")
    # Path to where the module SHOULD be
    midas_dir = os.path.join(home, "stable-diffusion-webui", "repositories", "stable-diffusion-stability-ai", "ldm", "modules", "midas")
    
    # 1. Create Directory
    os.makedirs(midas_dir, exist_ok=True)
    
    # 2. Create __init__.py
    init_file = os.path.join(midas_dir, "__init__.py")
    with open(init_file, "w") as f:
        f.write("# Dummy midas module injected by repair script\n")
        f.write("from . import api\n")
        
    # 3. Create api.py (The part sd_models.py imports)
    api_file = os.path.join(midas_dir, "api.py")
    
    # Needs ISL_PATHS dict and load_model function to satisfy lines 55-60 of sd_models.py
    api_content = """
# Dummy API implementation
ISL_PATHS = {}

def load_model(*args, **kwargs):
    print("⚠️  Dummy midas.load_model called (No Depth Model available)")
    return None
"""
    with open(api_file, "w") as f:
        f.write(api_content)
        
    print("✅ Midas Patch Applied. The app should now start.")

if __name__ == "__main__":
    patch_midas()
