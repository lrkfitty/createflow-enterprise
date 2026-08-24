# Character Creator Utility
# Handles logic to map UI sliders/inputs to valid Prompt Keywords with WEIGHTS

def get_weighted_body_desc(value):
    """0-100 Slider for General Physique"""
    if value < 15: return "extremely slender lean frame, thin delicate silhouette"
    elif value < 35: return "slim slender petite physique"
    elif value < 55: return "athletic, fit, toned physique"
    elif value < 75: return "curvy, shapely, hourglass figure"
    elif value < 90: return "voluptuous, thick curvy full figure"
    else: return "heavyset, very voluptuous, deeply curved full figure"

def get_weighted_muscle_desc(value):
    """0-100 Slider for Muscle Mass"""
    if value < 20: return "soft smooth skin"
    elif value < 40: return "lightly toned muscles"
    elif value < 60: return "athletic muscle definition, visible toned abs"
    elif value < 80: return "ripped muscular physique, six pack abs, sculpted arms"
    else: return "heavily muscular bodybuilder physique, vascular muscle definition"

def get_weighted_bust_desc(value, b_type):
    """0-100 Slider + Type for Bust"""
    if value < 20: size_str = "flat petite chest, small bust"
    elif value < 40: size_str = "moderate bust"
    elif value < 60: size_str = "full cleavage, large bust"
    elif value < 80: size_str = "voluptuous heavy cleavage, very large breasts"
    else: size_str = "extremely large voluptuous bust, prominent cleavage"
    
    type_str = ""
    if b_type == "Augmented / Implants":
        type_str = ", rounded augmented implants"
    elif b_type == "Natural / Drop":
        type_str = ", natural teardrop shape"
    elif b_type == "Perky / Athletic":
        type_str = ", perky lifted athletic shape"
    
    return f"{size_str}{type_str}"

def get_weighted_waist_desc(value):
    """0-100 Slider for Waist"""
    if value < 20: return "extremely narrow tiny cinched corset wasp waist"
    elif value < 40: return "slim narrow waist, hourglass proportions"
    elif value < 60: return "natural proportioned waist"
    elif value < 80: return "wider midsection waist"
    else: return "broad thick midsection"

def get_weighted_hip_desc(value):
    """0-100 Slider for Hips"""
    if value < 20: return "narrow slender hips"
    elif value < 40: return "moderate proportioned hips"
    elif value < 60: return "curvy wide hips, shapely"
    elif value < 80: return "wide pear-shaped voluptuous hips"
    else: return "extremely wide exaggerated shelf hips, dramatic hourglass curves"

def get_weighted_glute_desc(value, g_type):
    """0-100 Slider + Type for Glutes"""
    if value < 20: size_str = "slim flat glutes"
    elif value < 40: size_str = "moderate glutes"
    elif value < 60: size_str = "curvy shapely round glutes"
    elif value < 80: size_str = "large bubble butt, voluptuous glutes and thick thighs"
    else: size_str = "massively curved prominent bubble butt, exaggerated curves"

    type_str = ""
    if g_type == "BBL / Surgical":
        type_str = ", sculpted shelf aesthetic"
    elif g_type == "Athletic / Hard":
        type_str = ", firm toned athletic glutes"
    elif g_type == "Soft / Natural":
        type_str = ", natural soft curve"

    return f"{size_str}{type_str}"

def get_age_description(value):
    """Maps age number to descriptive text."""
    if value < 25: return f"{value} years old, young adult, fresh youthful face"
    elif value < 35: return f"{value} years old, adult, mature defined features"
    elif value < 50: return f"{value} years old, middle aged, distinguished"
    elif value < 70: return f"{value} years old, senior, mature aged"
    else: return f"{value} years old, elderly"

def get_character_sheet_prompt(base_prompt):
    """Wraps the prompt to generate a character reference sheet."""
    suffix = "character reference sheet, split into 5 panels, top half 2 images: close up of facial details looking straight at camera and close up of 3/4 view, bottom half 3 images: side profile right, side profile left, full body standing shot, white studio background, consistent character, detailed anatomy, 35mm film photography, raw photo"
    return f"{base_prompt}, {suffix}"

def get_product_sheet_prompt(base_prompt):
    """Wraps the prompt to generate a product reference sheet."""
    suffix = "product reference sheet, split into 4 panels, four different angles: front view, side profile, back view, angled top-down view, clean studio background, consistent product design, detailed materials, commercial product photography"
    return f"{base_prompt}, {suffix}"

def build_character_prompt(attributes):
    """
    Constructs a full character prompt with natural descriptive attributes.
    """
    
    # Extract Basic
    gender = attributes.get("gender", "Female")
    ethnicity = attributes.get("ethnicity", "Any")
    age_val = attributes.get("age", 25)
    
    # Extract Face
    hair_color = attributes.get("hair_color", "Any")
    hair_style = attributes.get("hair_style", "Any")
    eye_color = attributes.get("eye_color", "Any")
    
    # Granular Makeup
    lashes = attributes.get("lashes", "None")
    eyebrows = attributes.get("eyebrows", "Natural")
    foundation = attributes.get("foundation", "None")
    lipgloss = attributes.get("lipgloss", "None")
    eyeshadow = attributes.get("eyeshadow", "None")
    blush = attributes.get("blush", "None")
    
    # Facial Hair (Enhanced)
    facial_hair = attributes.get("facial_hair", "None")
    facial_hair_color = attributes.get("facial_hair_color", "Same as Hair")
    facial_hair_length = attributes.get("facial_hair_length", "None")
    
    skin_details = attributes.get("skin_details", [])
    
    # Extract Body
    body_val = attributes.get("body_type", 50)
    muscle_val = attributes.get("muscle", 20)
    bust_val = attributes.get("bust", 40)
    bust_type = attributes.get("bust_type", "Natural")
    waist_val = attributes.get("waist", 50)
    hip_val = attributes.get("hips", 50)
    glute_val = attributes.get("glutes", 50)
    glute_type = attributes.get("glute_type", "Natural")
    
    # Extract Tattoos (List)
    tattoo_style = attributes.get("tattoo_style", "None")
    tattoo_places = attributes.get("tattoo_places", []) # List now
    
    # Character Description
    description = attributes.get("description", "")

    # Map Sliders to Natural Language Strings
    age_desc = get_age_description(age_val)
    body_desc = get_weighted_body_desc(body_val)
    muscle_desc = get_weighted_muscle_desc(muscle_val)
    waist_desc = get_weighted_waist_desc(waist_val)
    hip_desc = get_weighted_hip_desc(hip_val)
    glute_desc = get_weighted_glute_desc(glute_val, glute_type)
    
    # Contextual Bust
    bust_desc = ""
    # Add female anatomy if gender is female/nb/femme
    is_femme = "Female" in gender or gender == "Non-Binary"
    if is_femme:
        bust_desc = get_weighted_bust_desc(bust_val, bust_type)
        
    # Base Subject
    if ethnicity != "Any":
        subject = f"portrait photograph of a {ethnicity} {gender}"
    else:
        subject = f"portrait photograph of a {gender}"
        
    # Construct Physical Traits List
    traits = [age_desc, body_desc, muscle_desc, waist_desc, hip_desc, glute_desc]
    if bust_desc: traits.append(bust_desc)
    
    # Hair
    h_str = ""
    if hair_color != "Any": h_str += hair_color + " "
    if hair_style != "Any": h_str += hair_style
    if h_str: traits.append(f"{h_str} hair")

    # Eyes & Face
    if eye_color != "Any": traits.append(f"{eye_color} eyes")
    
    # Facial Hair (Enhanced)
    if facial_hair not in ["None", "Clean Shaven"]:
        fh_str = facial_hair
        if facial_hair_length != "None":
            fh_str = f"{facial_hair_length} {facial_hair}"
        if facial_hair_color != "Same as Hair":
            fh_str = f"{facial_hair_color} {fh_str}"
        traits.append(fh_str)
    
    # Makeup (Granular)
    makeup_parts = []
    if lashes != "None": makeup_parts.append(lashes)
    if eyebrows != "Natural": makeup_parts.append(f"{eyebrows} eyebrows")
    if foundation != "None": makeup_parts.append(f"{foundation} foundation")
    if lipgloss != "None": makeup_parts.append(f"{lipgloss} lips")
    if eyeshadow != "None": makeup_parts.append(eyeshadow)
    if blush != "None": makeup_parts.append(blush)
    
    if makeup_parts:
        traits.append(", ".join(makeup_parts))
    
    # Tattoos
    tattoo_style = attributes.get("tattoo_style", "None")
    tattoo_places = attributes.get("tattoo_places", [])
    tattoo_coverage = attributes.get("tattoo_coverage", "None")
    tattoo_sleeve = attributes.get("tattoo_sleeve", "None")

    if tattoo_style != "None":
        tat_parts = [f"{tattoo_style} tattoos"]
        if tattoo_coverage != "None":
            tat_parts.append(tattoo_coverage.lower())
        if tattoo_sleeve and tattoo_sleeve != "None":
            tat_parts.append(tattoo_sleeve.lower())
        if tattoo_places:
            tat_parts.append(f"on {', '.join(tattoo_places)}")
        traits.append(" — ".join(tat_parts))
    
    # Skin
    if skin_details:
        traits.append(", ".join(skin_details))

    # Accessories & Jewelry
    earrings = attributes.get("earrings", "None")
    necklace = attributes.get("necklace", "None")
    watch = attributes.get("watch", "None")
    rings = attributes.get("rings", [])
    bracelets = attributes.get("bracelets", [])
    piercings = attributes.get("piercings", [])

    acc_parts = []
    if earrings and earrings not in ["None", "No Earrings"]:
        acc_parts.append(f"wearing {earrings}")
    if necklace and necklace not in ["None", "No Necklace"]:
        acc_parts.append(f"wearing {necklace}")
    if watch and watch not in ["None", "No Watch"]:
        acc_parts.append(f"wearing {watch}")
    if rings:
        acc_parts.append(f"wearing {', '.join(rings)}")
    if bracelets:
        acc_parts.append(f"wearing {', '.join(bracelets)}")
    if piercings:
        acc_parts.append(f"with {', '.join(piercings)}")

    if acc_parts:
        traits.append(", ".join(acc_parts))
        
    traits_str = ", ".join(traits)
    
    # Environment & Style (Studio)
    env = "professional studio photography, solid neutral background, seamless backdrop"
    lighting = "soft studio lighting, rembrandt lighting, photography, highly detailed, sharp focus, natural skin texture"
    
    # Outfit (Smart Default)
    outfit = attributes.get("outfit", "")
    if not outfit:
        if is_femme:
            outfit = "tight black leggings, black sports bra, tight athletic fit"
        else:
            outfit = "athletic shorts, shirtless, bare chest, athletic fit, no shirt"
    
    # Combine
    full_prompt = f"{subject}, {traits_str}, wearing {outfit}, {env}, {lighting}, full body shot"
    
    # Append Character Description if provided
    if description:
        full_prompt += f", {description}"
    
    # Identity Likeness (ONLY if reference image is provided)
    has_ref = attributes.get("has_reference", False)
    likeness = attributes.get("likeness", 80)
    if has_ref:
        if likeness >= 90:
            full_prompt += ", ultra-high fidelity face match to reference photo, identical facial features and bone structure"
        elif likeness >= 80:
            full_prompt += ", high-fidelity resemblance to reference photo, matching facial features, bone structure, and eye shape"
        elif likeness >= 60:
            full_prompt += ", strong resemblance to reference photo, matching overall look and facial features"
        elif likeness >= 40:
            full_prompt += ", inspired by reference photo"
    
    return full_prompt
