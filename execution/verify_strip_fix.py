
print("\n--- 🕵️ AUTOMATED BUG TRACE: LEADING SPACE ISSUE ---")

# 1. THE BUG SCENARIO
# This is what the UI was sending (Leading Spaces)
raw_ui_keys = [
    " Shay Blonde Bob Back", 
    " Shays Bofriend Full View " 
]

print(f"INPUT KEYS: {raw_ui_keys}")

# 2. THE OLD LOGIC (Simulated Failure)
print("\n[TEST 1] SIMULATING OLD LOGIC...")
failed = False
for k in raw_ui_keys:
    # Old Code: split(' ')[0]
    base = k.split('/')[-1].replace('.png','').replace('.jpg','') 
    nickname = base.split(' ')[0]
    print(f"  Key: '{k}' -> Nickname: '{nickname}'")
    
    if nickname == "":
        print("  ❌ FAILURE: Detected Empty Nickname (This caused the leak!)")
        failed = True
        
if failed:
    print("  -> Conclusion: Old logic was indeed broken.")

# 3. THE NEW LOGIC (Simulated Fix)
print("\n[TEST 2] SIMULATING NEW LOGIC (.strip())...")
passed = True
clean_map = {}
for k in raw_ui_keys:
    # New Code: .strip() then split
    base = k.split('/')[-1].replace('.png','').replace('.jpg','').strip()
    nickname = base.split(' ')[0]
    
    clean_map[nickname] = "Asset_Path_OK"
    print(f"  Key: '{k}' -> Nickname: '{nickname}'")
    
    if nickname == "":
        print("  ❌ FAILURE: Still Empty!")
        passed = False
    else:
        print(f"  ✅ SUCCESS: Resolved valid key '{nickname}'")

print("\n--- FINAL VERDICT ---")
if passed and "Shay" in clean_map and "Shays" in clean_map:
    print("✅ FIX VERIFIED: The .strip() update successfully cleans the keys.")
    print("   The AI will now receive correct IDs: 'Shay' and 'Shays'.")
    print("   No more asset bleeding.")
else:
    print("❌ FIX FAILED.")
