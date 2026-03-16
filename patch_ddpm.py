import os

def patch_ddpm():
    print("🚑 PATCHING 'ddpm.py' (Missing Class)...")
    
    home = os.path.expanduser("~")
    repo_file = os.path.join(home, "stable-diffusion-webui", "repositories", "stable-diffusion-stability-ai", "ldm", "models", "diffusion", "ddpm.py")
    
    if not os.path.exists(repo_file):
        print(f"❌ File not found: {repo_file}")
        return

    with open(repo_file, "r") as f:
        content = f.read()
        
    classes_to_patch = [
        "LatentDepth2ImageDiffusion",
        "LatentUpscaleDiffusion",
        "LatentInpaintDiffusion",
        "ImageEmbeddingConditionedLatentDiffusion"
    ]
    
    new_classes_code = ""
    for cls in classes_to_patch:
        if f"class {cls}" not in content:
            print(f"➕ Patching missing class: {cls}")
            new_classes_code += f"""

class {cls}(LatentDiffusion):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("⚠️  Dummy {cls} initialized")
"""
        else:
            print(f"✅ Class {cls} already exists.")

    if new_classes_code:
        with open(repo_file, "a") as f:
            f.write(new_classes_code)
        print("✅ DDPM Patch Applied (All classes).")
    else:
        print("✨ DDPM already fully patched.")


if __name__ == "__main__":
    patch_ddpm()
