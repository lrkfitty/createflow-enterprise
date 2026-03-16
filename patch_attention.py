import os

def patch_attention():
    print("🚑 PATCHING 'BasicTransformerBlock' Compatibility...")
    
    home = os.path.expanduser("~")
    repo_file = os.path.join(home, "stable-diffusion-webui", "repositories", "stable-diffusion-stability-ai", "ldm", "modules", "attention.py")
    
    if not os.path.exists(repo_file):
        print(f"❌ File not found: {repo_file}")
        return

    with open(repo_file, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    patched = False
    
    classes_to_patch = {
        "class BasicTransformerBlock(nn.Module):": [
            "    ATTENTION_MODES = {}\n",
            "    use_linear_dependency_scheduler = False\n"
        ],
        "class SpatialTransformer(nn.Module):": [
            "    use_linear = False\n"
        ]
    }

    for line in lines:
        new_lines.append(line)
        
        for cls_sig, injections in classes_to_patch.items():
            if cls_sig in line:
                print(f"🔧 Patching {cls_sig.split('(')[0]}...")
                for injection in injections:
                    new_lines.append(injection)
                patched = True
                
    if patched:
        with open(repo_file, "w") as f:
            f.writelines(new_lines)
        print("✨ PATCH SUCCESSFUL. The app should now start.")
    else:
        print("⚠️ Could not find BasicTransformerBlock class. Already patched?")

if __name__ == "__main__":
    patch_attention()
