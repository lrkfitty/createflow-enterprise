import os
import shutil

# Config
SOURCE_DIR = "output"
# The folder structure revealed 'TyTheGuyTTG' exists.
# We will use the username from users.json casing which was 'Tytheguyttg'
# But let's check what directory actually exists to be safe.
TARGET_USER = "Tytheguyttg" 
TARGET_DIR = os.path.join(SOURCE_DIR, "users", TARGET_USER, "Gallery")

# Create Target
os.makedirs(TARGET_DIR, exist_ok=True)

moved_count = 0
extensions = ('.jpg', '.jpeg', '.png', '.mp4', '.json')

print(f"Migrating assets from {SOURCE_DIR} -> {TARGET_DIR}...")

for filename in os.listdir(SOURCE_DIR):
    src_path = os.path.join(SOURCE_DIR, filename)
    
    # Skip directories
    if os.path.isdir(src_path):
        continue
        
    # Check extension
    if filename.lower().endswith(extensions):
        # Don't move config files if any (users.json is in config/ usually but check)
        if filename == "users.json": continue
        
        dst_path = os.path.join(TARGET_DIR, filename)
        shutil.move(src_path, dst_path)
        moved_count += 1
        
print(f"Successfully moved {moved_count} files.")
