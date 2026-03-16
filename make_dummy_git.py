import os
import subprocess

def make_dummy_git():
    print("🎭 CREATING DUMMY GIT REPOS TO TRICK LAUNCHER...")
    
    home = os.path.expanduser("~")
    repo_base = os.path.join(home, "stable-diffusion-webui", "repositories")
    
    # 1. Target Directories
    targets = [
        os.path.join(repo_base, "stable-diffusion-stability-ai"),
        os.path.join(repo_base, "taming-transformers")
    ]
    
    for target in targets:
        if not os.path.exists(target):
            print(f"⚠️  Missing folder: {target} (Skipping)")
            continue
            
        print(f"🔧 Fixing: {os.path.basename(target)}")
        
        # Initialize Git
        subprocess.run(["git", "init"], cwd=target, check=False)
        
        # Configure User (Local only) to allow commit
        subprocess.run(["git", "config", "user.email", "you@example.com"], cwd=target, check=False)
        subprocess.run(["git", "config", "user.name", "Your Name"], cwd=target, check=False)
        
        # Add all files
        subprocess.run(["git", "add", "."], cwd=target, check=False)
        
        # Commit (So it looks like a valid repo)
        subprocess.run(["git", "commit", "-m", "Dummy commit to satisfy launcher"], cwd=target, check=False)
        
        # REMOVE REMOTE explicitly so it can't try to pull interactively
        subprocess.run(["git", "remote", "remove", "origin"], cwd=target, check=False)
        
        print(f"✅ Converted {os.path.basename(target)} to a local-only git repo.")

    # ALSO: Unset the global config that might be causing issues
    print("🧹 Cleaning global git config...")
    subprocess.run(["git", "config", "--global", "--unset", "url.https://github.com/CompVis/stable-diffusion.git.insteadOf"], check=False)
    
    print("✨ DONE. Now launch the app.")

if __name__ == "__main__":
    make_dummy_git()
