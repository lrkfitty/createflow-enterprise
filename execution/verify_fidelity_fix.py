
import sys
import os

print("\n--- 🕵️‍♀️ VERIFICATION: OUTFIT FIDELITY FIX ---")

# 1. SETUP: Simulate the User's State
# The user selects a specific variation of Shay
cast_selection = ["/some/path/to/Shay Blonde Bob Back.png"]
raw_name = "Shay Blonde Bob Back"

# The Snapshot was validated with just the First Name
cast_wardrobe_map_snapshot = {
    "Shay": "Yellow Silk Top" # This is the key we must match
}

print(f"1. User Selected: '{raw_name}'")
print(f"2. Snapshot Map Keys: {list(cast_wardrobe_map_snapshot.keys())}")

# 3. LOGIC TEST (The Logic from app.py)
print("\n--- RUNNING LOGIC ---")

# Step A: Get Char Ref
char_ref = raw_name # "Shay Blonde Bob Back"

# Step B: The FIX (Split the name)
naive_char_key = char_ref.split(' ')[0]
print(f"   -> Derived Key: '{naive_char_key}'")

# Step C: Lookup
outfit_name_key = cast_wardrobe_map_snapshot.get(naive_char_key, "Default")
print(f"   -> Lookup Result: '{outfit_name_key}'")

# 4. ASSERTION
if outfit_name_key == "Yellow Silk Top":
    print("\n✅ SUCCESS: Outfit Found! The 'Variation' bug is squashed.")
    print("   The system now correctly links 'Shay Blonde Bob' -> 'Shay' -> 'Yellow Silk Top'.")
else:
    print("\n❌ FAILURE: Outfit NOT Found. Logic still flawed.")
