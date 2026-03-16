import os

def patch_launch_utils():
    print("🛠️ PATCHING LAUNCHER TO IGNORE GIT...")
    
    home = os.path.expanduser("~")
    file_path = os.path.join(home, "stable-diffusion-webui", "modules", "launch_utils.py")
    
    if not os.path.exists(file_path):
        print(f"❌ Could not find file: {file_path}")
        return

    with open(file_path, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    patched = False
    
    new_lines = []
    patched_count = 0
    
    for line in lines:
        new_lines.append(line)
        # We look for the run_git function definition
        if "def run_git(" in line:
            # We inject a return statement immediately to disable it
            new_lines.append("    print(f'🚫 GIT DISABLED: Skipping {command} {desc}')\n")
            new_lines.append("    return ''\n") 
            patched_count += 1
            
    if patched_count > 0:
        with open(file_path, "w") as f:
            f.writelines(new_lines)
        print(f"✨ PATCH SUCCESSFUL! Modified {patched_count} occurrences.")
        
        # Verify
        with open(file_path, "r") as f:
            content = f.read()
            if "GIT DISABLED" in content:
                print("✅ Verification Passed.")
            else:
                print("❌ Verification Failed.")
    else:
        print("⚠️ Could not find run_git function. Is the file already patched?")

if __name__ == "__main__":
    patch_launch_utils()
