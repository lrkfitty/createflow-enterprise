import os

def patch_ldm_data():
    print("🚑 PATCHING 'ldm.data.util' (Missing file)...")
    
    home = os.path.expanduser("~")
    # Path to where the file SHOULD be
    data_dir = os.path.join(home, "stable-diffusion-webui", "repositories", "stable-diffusion-stability-ai", "ldm", "data")
    
    if not os.path.exists(data_dir):
        print(f"❌ Directory not found: {data_dir}")
        return

    util_file = os.path.join(data_dir, "util.py")
    
    # Needs AddMiDaS class to satisfy import
    file_content = """
# Dummy util.py injected by repair script
import numpy as np

class AddMiDaS(object):
    def __init__(self, model_type):
        self.model_type = model_type
        print("⚠️  Dummy AddMiDaS initialized")

    def __call__(self, examples):
        return examples
"""
    with open(util_file, "w") as f:
        f.write(file_content)
        
    print("✅ LDM Data Patch Applied. The app should now start.")

if __name__ == "__main__":
    patch_ldm_data()
