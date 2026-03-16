
def simulate_mini_series_logic(cast_selection):
    print(f"Input Cast Selection: {cast_selection}")
    
    clean_cast_map = {} 
    
    for full_key in cast_selection:
        # Mocking the path based on key (logic says real_path comes from assets)
        real_path = f"/path/to/{full_key}"
            
        base = full_key.split('/')[-1].replace('.png','').replace('.jpg','').strip()
        clean_name = base #.split(' ')[0] -- MATCHING FIX
        
        print(f"Processing '{full_key}' -> Base: '{base}' -> Clean Name: '{clean_name}'")
        
        if clean_name in clean_cast_map:
            print(f"⚠️ COLLISION DETECTED! Overwriting '{clean_name}' (was {clean_cast_map[clean_name]}) with {real_path}")

        clean_cast_map[clean_name] = real_path

    print("-" * 20)
    print(f"Final Cast Map Keys (Options available in dropdown): {list(clean_cast_map.keys())}")
    print("-" * 20)
    return clean_cast_map

# Test Case 1: Distinct First Names (Should work)
simulate_mini_series_logic([
    "Alice Wonderland",
    "Bob Builder",
    "Charlie Chaplin"
])

# Test Case 2: Shared First Names (Collision)
simulate_mini_series_logic([
    "John Doe",
    "John Smith",
    "John Wick"
])

# Test Case 3: Character with Titles/Prefixes (Collision)
simulate_mini_series_logic([
    "Detective Pikachu",
    "Detective Conan",
    "Detective Gadget"
])

# Test Case 4: Project/Era Prefixes (Collision)
simulate_mini_series_logic([
    "Cyberpunk_Alice",
    "Cyberpunk_Bob",
    "Cyberpunk_Charlie"
])
