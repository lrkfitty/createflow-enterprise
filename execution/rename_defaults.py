import os

# Target Directory
TARGET_DIR = "/Users/tylarkin/Desktop/AI Cnntent Creator workflow/output/users/Tytheguyttg/Assets"

print(f"Scanning {TARGET_DIR} for 'default.png'...")

count = 0
for root, dirs, files in os.walk(TARGET_DIR):
    for file in files:
        if file.lower() == "default.png":
            parent_dir_name = os.path.basename(root)
            old_path = os.path.join(root, file)
            
            # New Name = Parent Dir Name . png
            new_name = f"{parent_dir_name}.png"
            new_path = os.path.join(root, new_name)
            
            if old_path != new_path:
                print(f"Renaming: {old_path} -> {new_path}")
                os.rename(old_path, new_path)
                count += 1

print(f"Finished. Renamed {count} files.")
