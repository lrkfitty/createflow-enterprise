import os
import sys

# Ensure we can import modules from execution/
sys.path.append(os.path.join(os.getcwd(), 'execution'))
from auth import AuthManager

def fix_account():
    print("Initializing AuthManager...")
    auth = AuthManager()
    
    username = "Tytheguyttg"
    
    # 1. Fix Credits & Sync to S3
    if username in auth.users:
        print(f"User {username} found. Current credits: {auth.users[username].get('credits')}")
        auth.users[username]['credits'] = 200
        print(f"Setting credits to 200...")
        auth.save_users() # This pushes to S3!
        print("✅ Credits updated and pushed to S3.")
    else:
        print(f"❌ User {username} not found in DB!")

    # 2. Fix Assets Directory
    # Note: Using the exact casing from the username in users.json
    assets_dir = f"output/users/{username}/Assets"
    if not os.path.exists(assets_dir):
        print(f"Creating missing directory: {assets_dir}")
        os.makedirs(assets_dir, exist_ok=True)
        print("✅ Directory created.")
    else:
        print(f"Directory already exists: {assets_dir}")

if __name__ == "__main__":
    fix_account()
