import os

def patch_encoders():
    print("🚑 PATCHING 'encoders/modules.py' (Missing OpenCLIP)...")
    
    home = os.path.expanduser("~")
    repo_file = os.path.join(home, "stable-diffusion-webui", "repositories", "stable-diffusion-stability-ai", "ldm", "modules", "encoders", "modules.py")
    
    if not os.path.exists(repo_file):
        print(f"❌ File not found: {repo_file}")
        return

    with open(repo_file, "r") as f:
        content = f.read()
        
    if "class FrozenOpenCLIPEmbedder" in content:
        print("✅ Class FrozenOpenCLIPEmbedder already exists.")
        return

    # Append the missing class
    # It inherits from AbstractEncoder or nn.Module. Let's use nn.Module to be safe and independent.
    patch_code = """
import torch.nn as nn

class FrozenOpenCLIPEmbedder(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
        print("⚠️  Dummy FrozenOpenCLIPEmbedder initialized")
        
    def forward(self, text):
        return None
        
    def encode(self, text):
        return None
"""

    with open(repo_file, "a") as f:
        f.write(patch_code)
        
    print("✅ Encoders Patch Applied. 'FrozenOpenCLIPEmbedder' added.")

if __name__ == "__main__":
    patch_encoders()
