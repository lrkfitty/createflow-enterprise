
import streamlit as st
import os
import json
import time
import datetime
import shutil
from execution.magic_ui import card_begin, card_end, circular_progress
from execution.character_utils import build_character_prompt, get_character_sheet_prompt
from execution.generate_image import generate_image_from_prompt
from load_assets import promote_image_to_asset
from execution.auth import auth_mgr
from execution.s3_uploader import upload_file_obj
from execution.celebrities import CELEBRITIES, CELEB_CATEGORIES, get_celebrities_by_category, get_celebrity_by_name

def render_character_studio(characters_data, get_user_out_dir_func, campaign_mgr=None):
    """
    Renders the Character Studio UI.
    args:
        characters_data: Dictionary of character assets.
        get_user_out_dir_func: Function to get user output directory.
    """
    col_char_ctrl, col_char_view = st.columns([1, 1.5]) 
    
    with col_char_ctrl:
        card_begin()
        
        # Initialize user early to prevent UnboundLocalError in save block
        user = st.session_state.current_user.get("username") if st.session_state.get("current_user") else "guest"

        st.markdown("#### Design Specs")
        
        # 2. Output Mode (Outside Form for Instant Reactivity)
        st.markdown("**Output Format**")
        output_mode = st.selectbox("Generation Mode", [
            "Concept Portrait (Vertical)", 
            "Character Sheet (5 Angles - Vertical)",
            "Individual Shots (Batch)"
        ])
        
        selected_angles = []
        if output_mode == "Individual Shots (Batch)":
            angle_opts = [
                "Front View", "Side View (Left)", "Side View (Right)",
                "3/4 View (Left)", "3/4 View (Right)", "Back View",
                "Close Up (Face)", "Extreme Close Up",
                "Over Shoulder", "Low Angle", "High Angle"
            ]
            selected_angles = st.multiselect(
                "Select Angles to Generate",
                angle_opts,
                default=["Front View", "Side View (Left)", "3/4 View (Left)", "Back View"]
            )
            
        st.divider()
        
        
        with st.form("character_creator_form"):
            # 1. Reference Images (Multi-Upload)
            st.markdown("**1. References (Optional)**")
            ref_imgs = st.file_uploader(
                "Upload Face/Reference Images (multiple angles = better likeness)",
                type=['png', 'jpg', 'jpeg'],
                accept_multiple_files=True,
                help="Upload multiple photos of the same person from different angles to dramatically improve likeness accuracy"
            )
            
            # Thumbnail strip for uploaded references
            if ref_imgs:
                thumb_cols = st.columns(min(len(ref_imgs), 5))
                for i, img_f in enumerate(ref_imgs):
                    with thumb_cols[i % 5]:
                        st.image(img_f, caption=f"Ref {i+1}", use_container_width=True)
            
            # ── CELEBRITY INSPIRATION ────────────────────────────────────
            with st.expander("⭐ Celebrity Inspiration (Optional)", expanded=False):
                st.caption("Generate a look inspired by a famous person. Select a category then choose a celebrity.")
                
                celeb_cat = st.selectbox(
                    "Category",
                    ["All"] + CELEB_CATEGORIES,
                    key="celeb_cat_filter"
                )
                filtered_celebs = get_celebrities_by_category(celeb_cat)
                celeb_names = ["None"] + [c["name"] for c in filtered_celebs]
                
                selected_celeb_name = st.selectbox(
                    "Celebrity",
                    celeb_names,
                    key="selected_celeb"
                )
                selected_celeb = get_celebrity_by_name(selected_celeb_name) if selected_celeb_name != "None" else None
                if selected_celeb:
                    st.info(
                        f"**{selected_celeb['name']}** ({selected_celeb['category']})\n\n"
                        f"*Visual profile: {selected_celeb['prompt_description'][:120]}...*"
                    )
            
            # – UNIFIED: Add Reference Identity from Library ─────────────
            st.caption("Or choose existing Identity:")
            char_keys = sorted(list(characters_data.keys()))
            ref_identity = st.selectbox("Base on Character", ["None"] + char_keys, 
                                        format_func=lambda x: characters_data[x].get('name', x) if isinstance(characters_data.get(x), dict) else x)
            
            lock_identity_path = None
            if ref_identity != "None":
                 val = characters_data[ref_identity]
                 lock_identity_path = val.get('default_img') if isinstance(val, dict) else val
                 st.caption(f"Using Identity: {ref_identity.split('/')[-1]}")
            
            # Likeness Fidelity Slider (default raised to 80)
            st.markdown("**Likeness Fidelity**")
            likeness = st.slider(
                "How closely should the result match the reference?",
                0, 100, 80,
                help="0: Creative interpretation | 50: Inspired by reference | 100: Near-identical likeness",
                key="char_likeness"
            )
            likeness_labels = {
                0: "🎨 Fully Creative", 20: "🌀 Loosely Inspired",
                40: "👤 Similar Features", 60: "🔍 Strong Resemblance",
                80: "🎯 Near Identical", 100: "🔒 Exact Likeness"
            }
            # Find closest label
            closest = min(likeness_labels.keys(), key=lambda k: abs(k - likeness))
            st.caption(f"{likeness_labels[closest]}")
            
            # Pass this to session state for generation
            if lock_identity_path:
                st.session_state['lock_identity_path'] = lock_identity_path
            elif 'lock_identity_path' in st.session_state:
                del st.session_state['lock_identity_path']
            
            # Form content continues...
            
            # 3. Attributes
            st.markdown("**3. Attributes**")
            
            with st.expander("Core Identity", expanded=True):
                c_gender = st.selectbox("Gender", ["Female", "Male", "Non-Binary"])
                eth_opts = [
                    # ── General ──
                    "Any",
                    "Mixed Race",
                    # ── African Nations ──
                    "Nigerian (Yoruba / Igbo / Hausa)",
                    "Ghanaian",
                    "Kenyan / East African",
                    "Ethiopian / Eritrean",
                    "Somali",
                    "South African (Zulu / Xhosa)",
                    "Congolese / Central African",
                    "Senegalese / West African",
                    "Ugandan / Rwandan",
                    "Tanzanian",
                    "Cameroonian",
                    "Sudanese / Nubian",
                    "Zimbabwean",
                    "African American",
                    "Afro-Caribbean",
                    # ── Latino / Latin American ──
                    "Mexican",
                    "Puerto Rican",
                    "Dominican",
                    "Cuban",
                    "Colombian",
                    "Venezuelan",
                    "Brazilian",
                    "Argentinian",
                    "Peruvian",
                    "Chilean",
                    "Ecuadorian",
                    "Guatemalan / Central American",
                    "Afro-Latina",
                    "Indigenous Latin American",
                    # ── East / Southeast Asian ──
                    "Korean",
                    "Japanese",
                    "Chinese (Han)",
                    "Chinese (Cantonese)",
                    "Taiwanese",
                    "Vietnamese",
                    "Filipino",
                    "Thai",
                    "Indonesian / Javanese",
                    "Malay",
                    "Cambodian / Khmer",
                    "Burmese / Myanmar",
                    # ── South Asian ──
                    "Indian (North — Punjabi / Hindi)",
                    "Indian (South — Tamil / Telugu)",
                    "Pakistani",
                    "Bangladeshi",
                    "Sri Lankan",
                    "Nepali",
                    # ── Middle Eastern / North African ──
                    "Arab (Gulf — Saudi / Emirati / Kuwaiti)",
                    "Arab (Levant — Lebanese / Syrian / Palestinian)",
                    "Egyptian",
                    "Moroccan / Maghrebi",
                    "Turkish",
                    "Iranian / Persian",
                    "Israeli",
                    # ── European ──
                    "Nordic / Scandinavian (Swedish / Norwegian / Danish)",
                    "Northern European (British / Irish / Dutch)",
                    "Mediterranean (Italian / Greek / Spanish / Portuguese)",
                    "Eastern European (Russian / Polish / Ukrainian)",
                    "Slavic (Czech / Slovak / Serbian / Croatian)",
                    "Balkan",
                    "French",
                    "German / Austrian)",
                    # ── Other ──
                    "Indigenous / Native American",
                    "Pacific Islander (Hawaiian / Samoan / Tongan)",
                    "Central Asian (Kazakh / Uzbek)",
                ]
                c_ethnicity = st.selectbox("Ethnicity / Background", eth_opts)
                c_age = st.slider("Age", 18, 90, 25)
            

            with st.expander("Face & Details", expanded=False):
                # Hair
                st.markdown("**Hair**")
                c1, c2 = st.columns(2)
                with c1:
                    hair_color_opts = [
                        "Any", "Blonde", "Platinum Blonde", "Honey Blonde", "Dirty Blonde",
                        "Brunette", "Dark Brown", "Chestnut", "Auburn", 
                        "Black", "Jet Black", "Red", "Ginger", "Copper Red",
                        "Pastel Pink", "Lavender", "Blue", "Green",
                        "Grey", "Silver", "White", "Salt and Pepper"
                    ]
                    c_hair_col = st.selectbox("Hair Color", hair_color_opts)
                with c2:
                    hair_style_opts = [
                        "Any", "Long Straight", "Long Wavy", "Long Curly", 
                        "Medium Length", "Shoulder Length", "Wavy", "Curly", "Coily",
                        "Bob Cut", "Lob", "Pixie", "Undercut", "Fade",
                        "Braids", "Box Braids", "Cornrows", "French Braids",
                        "Messy Bun", "Top Knot", "Ponytail", "Pigtails",
                        "Buzz Cut", "Crew Cut", "Afro", "Dreads", "Locs",
                        "Mohawk", "Mullet", "Shag", "Layers"
                    ]
                    c_hair_style = st.selectbox("Hair Style", hair_style_opts)
                
                # Custom Hairstyle Override
                c_hair_custom = st.text_input("Custom Hairstyle (Optional)", placeholder="e.g. asymmetrical bob with bangs", help="Override the dropdown with your own description")
                
                st.divider()
                
                # Facial Hair (Enhanced)
                st.markdown("**Facial Hair**")
                cf1, cf2 = st.columns(2)
                with cf1:
                    facial_opts = [
                        "None", "Clean Shaven",
                        "Stubble", "Light Stubble", "Heavy Stubble",
                        "Goatee", "Van Dyke", "Soul Patch",
                        "Mustache", "Handlebar Mustache", "Pencil Mustache",
                        "Beard", "Short Beard", "Medium Beard", "Long Beard", "Full Beard",
                        "Mutton Chops", "Sideburns", "Chinstrap"
                    ]
                    c_facial = st.selectbox("Facial Hair Style", facial_opts)
                with cf2:
                    c_facial_color = st.selectbox("Facial Hair Color", ["Same as Hair"] + hair_color_opts[1:], help="Can differ from head hair")
                
                if c_facial not in ["None", "Clean Shaven"]:
                    c_facial_length = st.select_slider("Facial Hair Length", ["Stubble", "Short", "Medium", "Long"], value="Short")
                else:
                    c_facial_length = "None"
                
                st.divider()
                
                # Eyes
                st.markdown("**Eyes**")
                c_eye = st.selectbox("Eye Color", ["Any", "Blue", "Green", "Brown", "Hazel", "Grey", "Amber", "Heterochromia (Two Colors)"])
                

                
                st.divider()
                
                # Skin
                c_skin = st.multiselect("Skin Details", ["Freckles", "Beauty Marks", "Moles", "Vitiligo", "Scarring", "Acne", "Perfect Skin", "Textured Skin", "Wrinkles", "Dimples"])

            with st.expander("✒️ Tattoos & Body Art", expanded=False):
                st.caption("Apply contextual tattoos, ink styles, and define sleeve and placement mapping.")
                
                # Tattoos — Granular Controls
                st.markdown("**Tattoos**")
                
                tat_col1, tat_col2 = st.columns(2)
                with tat_col1:
                    c_tat_style = st.selectbox("Art Style", [
                        "None", "Minimalist / Fine Line", "Traditional American",
                        "Neo-Traditional", "Japanese / Irezumi", "Tribal",
                        "Geometric", "Blackwork / Dotwork", "Watercolor",
                        "Realism / Portrait", "Chicano / Black & Grey", "New School",
                        "Henna / Mehndi", "Script / Lettering", "Ignorant Style", "Biomechanical"
                    ])
                    
                    if c_tat_style != "None":
                        c_tat_coverage = st.selectbox("Coverage / Density", [
                            "Light (a few small pieces)", "Moderate (scattered pieces)",
                            "Heavy (large coverage)", "Very Heavy (nearly filled)"
                        ])
                    else:
                        c_tat_coverage = "None"

                with tat_col2:
                    if c_tat_style != "None":
                        c_sleeve_style = st.selectbox("Sleeve Style", [
                            "None", "Quarter Sleeve (shoulder cap)", "Half Sleeve (upper arm)",
                            "Half Sleeve (forearm)", "Three-Quarter Sleeve", "Full Sleeve (one arm)",
                            "Full Sleeve (both arms)", "Leg Sleeve (one leg)", "Leg Sleeve (both legs)",
                            "Body Suit (full torso + arms)"
                        ])
                        
                        tat_place_opts = [
                            "Full Sleeve — Left Arm", "Full Sleeve — Right Arm", "Forearm — Left", "Forearm — Right",
                            "Upper Arm — Left", "Upper Arm — Right", "Elbow (ditch) — Left", "Elbow (ditch) — Right",
                            "Wrist — Left", "Wrist — Right", "Hands", "Fingers / Knuckles",
                            "Chest — Left Pec", "Chest — Right Pec", "Full Chest Panel", "Sternum / Underboob",
                            "Stomach / Abs (upper)", "Lower Stomach / Below Navel", "Full Stomach", "Ribs / Side — Left", "Ribs / Side — Right",
                            "Upper Back", "Full Back", "Lower Back", "Spine / Backbone", "Traps", "Shoulders",
                            "Neck — Front", "Neck — Side Left", "Neck — Side Right", "Behind Ear — Left", "Behind Ear — Right",
                            "Face — Minimal (teardrop / small)", "Face — Heavy Coverage", "Scalp / Head",
                            "Full Leg — Left", "Full Leg — Right", "Thigh — Left", "Thigh — Right", "Knee (kneecap)",
                            "Shin / Calf — Left", "Shin / Calf — Right", "Ankles", "Feet / Top of Foot", "Sole / Bottom of Foot",
                            "Full Body Coverage"
                        ]
                        c_tat_place = st.multiselect("Placement", tat_place_opts)
                    else:
                        c_sleeve_style = "None"
                        c_tat_place = []

            with st.expander("💍 Accessories & Jewelry", expanded=False):
                st.caption("Add earrings, piercings, necklaces, watches, rings, and bracelets")
                
                acc1, acc2 = st.columns(2)
                with acc1:
                    c_earrings = st.selectbox("Earrings", [
                        "None", "Studs (small)", "Studs (diamond/gem)",
                        "Small Hoops", "Medium Hoops", "Large Statement Hoops",
                        "Huggie Hoops", "Dangling / Drop Earrings",
                        "Chandelier Earrings", "Ear Cuffs",
                        "Pearl Earrings", "Gold Studs", "Silver Studs",
                        "Mismatched / Asymmetrical", "No Earrings"
                    ])
                    c_necklace = st.selectbox("Necklace", [
                        "None", "Dainty Gold Chain", "Dainty Silver Chain",
                        "Layered Chains (2-3)", "Layered Chains (4+)",
                        "Pendant Necklace", "Cross Necklace",
                        "Diamond / Tennis Necklace", "Pearl Strand",
                        "Choker (Velvet)", "Choker (Chain)",
                        "Cuban Link Chain", "Rope Chain",
                        "Body Chain", "Locket Necklace",
                        "No Necklace"
                    ])
                    c_watch = st.selectbox("Watch", [
                        "None", "Rolex (Classic Jubilee)", "Rolex Daytona",
                        "AP Royal Oak (Audemars Piguet)", "Patek Philippe",
                        "Cartier Santos / Tank", "Richard Mille",
                        "Hublot Big Bang", "IWC Pilot",
                        "Apple Watch (Sport)", "Apple Watch Ultra",
                        "Samsung Galaxy Watch", "Casio G-Shock",
                        "Minimalist Dress Watch", "Gold Watch", "Silver Watch",
                        "No Watch"
                    ])
                with acc2:
                    c_rings = st.multiselect("Rings", [
                        "Gold Band (plain)", "Silver Band (plain)",
                        "Diamond Engagement Ring", "Diamond Tennis Ring",
                        "Pinky Ring (gold)", "Pinky Ring (silver)",
                        "Signet Ring", "Statement Ring (large gem)",
                        "Snake Ring", "Stackable Rings (multiple)",
                        "Knuckle Rings", "Full Finger Ring (armor)",
                    "Wedding Band", "Eternity Band"
                    ])
                    c_bracelets = st.multiselect("Bracelets / Bangles", [
                        "Gold Bangle", "Silver Bangle",
                        "Stacked Bangles", "Tennis Bracelet (diamonds)",
                        "Chain Bracelet", "Cuff Bracelet",
                        "Beaded Bracelet", "Evil Eye Bracelet",
                        "Cartier Love Bracelet", "Hermes Clic Clac",
                        "Thread / String Bracelet"
                    ])
                    c_piercings = st.multiselect("Body Piercings", [
                        "Nose Ring (hoop)", "Nose Stud",
                        "Septum Ring", "Eyebrow Piercing",
                        "Lip Ring", "Labret Stud",
                        "Tongue Piercing",
                        "Industrial / Helix Piercing",
                        "Tragus Piercing", "Conch Piercing",
                        "Belly Button Ring / Navel Piercing",
                        "Cheek Piercings (dimple piercings)",
                        "Multiple Ear Piercings (stacked)",
                        "Nipple Piercings"
                    ])


            with st.expander("Makeup (Granular)", expanded=False):
                st.caption("Fine-tune makeup details")
                
                cm1, cm2 = st.columns(2)
                with cm1:
                    c_lashes = st.selectbox("Lashes", ["None", "Natural", "Mascara", "False Lashes", "Dramatic Lashes", "Wispy Lashes"])
                    c_eyebrows = st.selectbox("Eyebrows", ["Natural", "Defined", "Arched", "Bold", "Thin", "Bushy", "Microbladed", "Laminated"])
                    c_foundation = st.selectbox("Foundation/Base", ["None", "Natural", "Light Coverage", "Full Coverage", "Matte", "Dewy", "Contoured"])
                with cm2:
                    c_lipgloss = st.selectbox("Lips", ["None", "Natural", "Subtle Gloss", "High Gloss", "Matte Lipstick", "Bold Lipstick", "Lip Liner", "Ombre Lips"])
                    c_eyeshadow = st.selectbox("Eye Shadow", ["None", "Neutral", "Smokey Eye", "Winged Liner", "Cat Eye", "Colorful", "Glitter", "Cut Crease"])
                    c_blush = st.selectbox("Blush/Bronzer", ["None", "Subtle", "Natural", "Bronzed", "Heavy Contour"])

            with st.expander("Body Composition", expanded=False):
                st.caption("Customize physique details (0-100)")
                c_body = st.slider("General Physique", 0, 100, 50, help="0: Skinny | 50: Athletic | 100: Heavy/Curvy")
                c_muscle = st.slider("Muscle Mass", 0, 100, 20, help="0: Soft | 100: Ripped Bodybuilder")
                
                # Bust Details
                c1, c2 = st.columns([2, 1]) 
                with c1:
                     c_bust = st.slider("Bust Size", 0, 100, 40, help="Applies to Femme characters")
                with c2:
                     c_bust_type = st.selectbox("Bust Type", ["Natural / Drop", "Perky / Athletic", "Augmented / Implants"])
                
                c_waist = st.slider("Waist Width", 0, 100, 50, help="0: Cinematic Hourglass | 100: Wide")
                c_hips = st.slider("Hips Width", 0, 100, 50, help="0: Narrow | 100: Exaggerated Shelf Hips")
                
                # Glute Details
                c3, c4 = st.columns([2, 1])
                with c3:
                    c_glutes = st.slider("Glute Size", 0, 100, 50, help="0: Flat | 100: Exaggerated Bubble Butt")
                with c4:
                    c_glute_type = st.selectbox("Glute Type", ["Soft / Natural", "Athletic / Hard", "BBL / Surgical"])

            # Character Description
            st.divider()
            st.markdown("**4. Character Description (Optional)**")
            c_description = st.text_area(
                "Nuanced Details",
                placeholder="Add subtle character details... e.g. 'slightly crooked smile', 'scar above left eyebrow', 'confident posture'",
                height=80,
                help="This text will be added to the prompt for fine-tuned customization"
            )
            
            # Name
            st.divider()
            st.markdown("**5. Finalize**")
            char_name = st.text_input("Character Name", placeholder="e.g. Sarah")
            
            # Safe defaults if Accessories expander was never opened in this session
            if 'c_earrings' not in dir():
                try: c_earrings
                except NameError: c_earrings = "None"
            if 'c_necklace' not in dir():
                try: c_necklace
                except NameError: c_necklace = "None"
            if 'c_watch' not in dir():
                try: c_watch
                except NameError: c_watch = "None"
            if 'c_rings' not in dir():
                try: c_rings
                except NameError: c_rings = []
            if 'c_bracelets' not in dir():
                try: c_bracelets
                except NameError: c_bracelets = []
            if 'c_piercings' not in dir():
                try: c_piercings
                except NameError: c_piercings = []

            # Submit
            st.markdown("<br>", unsafe_allow_html=True)
            col_q, col_sub = st.columns([1, 2])
            with col_q:
                add_to_queue = st.checkbox("Add to Queue", value=False)
            with col_sub:
                create_char = st.form_submit_button("✨ Generate Character", type="primary", use_container_width=True)
            
        card_end()

    with col_char_view:
        card_begin()
        st.markdown("#### Studio Preview")
        
        # State Handling
        if create_char:
            if not char_name:
                st.error("Please name your character first.")
            else:
                # Build Prompt
                # Inject celebrity visual description if one is selected
                celeb_obj = get_celebrity_by_name(st.session_state.get("selected_celeb", "None"))
                extra_description = c_description
                if celeb_obj:
                    celeb_suffix = f"Inspired by {celeb_obj['name']}: {celeb_obj['prompt_description']}"
                    extra_description = f"{c_description}, {celeb_suffix}" if c_description else celeb_suffix
                    # Respect the celebrity's recommended likeness hint if slider is at default
                    if likeness == 80:
                        likeness = celeb_obj.get("likeness_hint", 85)

                attrs = {
                   "gender": c_gender,
                   "ethnicity": c_ethnicity,
                   "age": c_age,
                   "body_type": c_body,
                   "muscle": c_muscle,
                   "bust": c_bust,
                   "bust_type": c_bust_type,
                   "waist": c_waist,
                   "hips": c_hips,
                   "glutes": c_glutes,
                   "glute_type": c_glute_type,
                   "hair_color": c_hair_col,
                   "hair_style": c_hair_custom if c_hair_custom else c_hair_style,
                   "eye_color": c_eye,
                   "facial_hair": c_facial,
                   "facial_hair_color": c_facial_color,
                   "facial_hair_length": c_facial_length,
                   "lashes": c_lashes,
                   "eyebrows": c_eyebrows,
                   "foundation": c_foundation,
                   "lipgloss": c_lipgloss,
                   "eyeshadow": c_eyeshadow,
                   "blush": c_blush,
                   "skin_details": c_skin,
                   "tattoo_style": c_tat_style,
                   "tattoo_places": c_tat_place,
                   "tattoo_coverage": c_tat_coverage,
                   "tattoo_sleeve": c_sleeve_style,
                   # Accessories
                   "earrings": c_earrings,
                   "necklace": c_necklace,
                   "watch": c_watch,
                   "rings": c_rings,
                   "bracelets": c_bracelets,
                   "piercings": c_piercings,
                   "description": extra_description,
                   "likeness": likeness
                }
                st.session_state['char_last_attrs'] = attrs 
                
                base_prompt = build_character_prompt(attrs)
                
                if output_mode == "Character Sheet (5 Angles - Vertical)":
                    full_prompt = get_character_sheet_prompt(base_prompt)
                    ar = "4:5" # User requested 4:5 for all Studio generations
                    target_w, target_h = 896, 1152
                else:
                    full_prompt = base_prompt
                    ar = "4:5" # Portrait
                    target_w, target_h = 896, 1152
                
                st.success("Prompt Built!")
                with st.expander("View Prompt"):
                    st.code(full_prompt)
                
                # Generate
                if add_to_queue and campaign_mgr:
                     # QUEUE MODE
                     job_name = f"Char_{char_name}"
                     
                     # Build multi-reference asset list
                     import tempfile
                     assets = []
                     for i, uploaded_ref in enumerate(ref_imgs or []):
                         tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                         tmp.write(uploaded_ref.getbuffer())
                         tmp.flush()
                         assets.append({"path": tmp.name, "label": f"Cast: {char_name or 'Main'} (Ref {i+1})"})
                     # Library identity lock (fallback if no uploads)
                     if not assets and st.session_state.get("lock_identity_path"):
                         assets.append({
                             "path": st.session_state["lock_identity_path"],
                             "label": f"Cast: {char_name or 'Main'}"
                         })
                         
                     campaign_mgr.add_job(
                        name=job_name,
                        description=f"Character Concept: {char_name}",
                        prompt_data={
                             "positive_prompt": full_prompt,
                             "width": target_w, "height": target_h,
                             "aspect_ratio": ar,
                             "image_size": "4K",
                             "model_type": "nano",
                             "assets": assets
                        },
                        settings={"batch_count": 1},
                        output_folder=get_user_out_dir_func("Characters/Concepts"),
                        char_path=st.session_state.get("lock_identity_path")
                     )
                     st.success(f"✅ Added '{char_name}' to Campaign Queue!")
                     
                else:
                    # SYNC MODE
                    user = st.session_state.current_user.get("username")
                    
                    if output_mode == "Individual Shots (Batch)":
                        if not selected_angles:
                            st.error("Please select at least one angle.")
                        else:
                            total_credits = len(selected_angles)
                            if auth_mgr.deduct_credits(user, total_credits):
                                st.session_state['char_batch_results'] = []
                                # Clear single preview
                                if 'char_preview' in st.session_state:
                                    del st.session_state['char_preview']
                                
                                import tempfile
                                assets = []
                                for i, uploaded_ref in enumerate(ref_imgs or []):
                                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                                    tmp.write(uploaded_ref.getbuffer())
                                    tmp.flush()
                                    assets.append({"path": tmp.name, "label": f"Cast: IdentityLock (Ref {i+1})"})
                                if not assets and st.session_state.get("lock_identity_path"):
                                    assets.append({"path": st.session_state["lock_identity_path"], "label": f"Cast: {char_name or 'Main'}"})
                                
                                for idx, angle in enumerate(selected_angles):
                                    with st.spinner(f"Generating angle: {angle}..."):
                                        angle_prompt = f"{base_prompt}, {angle.lower()}, professional photography"
                                        
                                        current_assets = list(assets)
                                        modified_prompt = angle_prompt
                                        
                                        # CASADE LOGIC: If this is not the first angle, use the first generated image as the anchor
                                        if idx > 0 and len(st.session_state['char_batch_results']) > 0:
                                            first_img_path = st.session_state['char_batch_results'][0]['path']
                                            current_assets.append({
                                                "path": first_img_path,
                                                "label": "Main Subject (SOURCE OF TRUTH — match face, identity, tattoos, and proportions exactly)"
                                            })
                                            modified_prompt += (
                                                ", (identical face to reference:1.5), (exact same person:1.5), "
                                                "(preserve facial features exactly:1.4), (same bone structure:1.3), "
                                                "(maintain exact tattoo placement and style:1.4), DO NOT alter facial features"
                                            )
                                        
                                        payload = {
                                            "positive_prompt": modified_prompt,
                                            "width": target_w, "height": target_h,
                                            "aspect_ratio": ar,
                                            "image_size": "4K",
                                            "model_type": "nano",
                                            "assets": current_assets
                                        }
                                        res = generate_image_from_prompt(payload, get_user_out_dir_func("Characters/Concepts"))
                                        if res["status"] == "success":
                                            st.session_state['char_batch_results'].append({
                                                "angle": angle,
                                                "path": res['image_path'],
                                                "payload": payload
                                            })
                                            st.toast(f"✅ {angle} complete!")
                                        else:
                                            auth_mgr.add_credits(user, 1)  # Refund
                                            st.error(f"{angle} failed: {res.get('logs')}")
                                
                                st.success("✅ Batch generation complete!")
                            else:
                                st.error(f"Need {total_credits} credits for this batch.")
                                
                    else:
                        if auth_mgr.deduct_credits(user, 1):
                            with st.spinner("Creating Character in Studio..."):
                                 # Clear batch results if standard creation
                                 if 'char_batch_results' in st.session_state:
                                     del st.session_state['char_batch_results']
                                     
                                 # Build multi-reference asset list
                                 import tempfile
                                 assets = []
                                 for i, uploaded_ref in enumerate(ref_imgs or []):
                                     tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                                     tmp.write(uploaded_ref.getbuffer())
                                     tmp.flush()
                                     assets.append({"path": tmp.name, "label": f"Cast: {char_name or 'Main'} (Ref {i+1})"})
                                 # Library identity lock (fallback)
                                 if not assets and st.session_state.get("lock_identity_path"):
                                     assets.append({
                                         "path": st.session_state["lock_identity_path"],
                                         "label": f"Cast: {char_name or 'Main'}"
                                     })
                                 
                                 # Payload
                                 payload = {
                                     "positive_prompt": full_prompt,
                                     "width": target_w, "height": target_h,
                                     "aspect_ratio": ar,
                                     "image_size": "4K",
                                     "model_type": "nano",
                                     "assets": assets
                                 }
                                 
                                 res = generate_image_from_prompt(payload, get_user_out_dir_func("Characters/Concepts"))
                                 
                                 if res["status"] == "success":
                                     st.session_state['char_preview'] = res['image_path']
                                     st.session_state['char_final_prompt'] = full_prompt
                                     st.toast("Character Generated!")
                                 else:
                                     auth_mgr.add_credits(user, 1) # Refund
                                     st.error(f"Failed: {res.get('logs')}")
                        else:
                            st.error("Not enough credits.")

        # Display Result
        if 'char_batch_results' in st.session_state and st.session_state['char_batch_results']:
            st.markdown("#### Batch Generation Complete")
            batch = st.session_state['char_batch_results']
            
            # Show prominent preview for the first image
            first = batch[0]
            st.image(first['path'], caption=f"{char_name} - {first['angle']}", use_container_width=True)
            
            c_dl_main, c_rerun_main = st.columns(2)
            with c_dl_main:
                with open(first['path'], "rb") as f:
                    st.download_button(
                        label="⬇️ Download",
                        data=f,
                        file_name=f"{char_name}_{first['angle'].replace(' ', '_').lower()}.jpg",
                        mime="image/jpeg",
                        key="dl_batch_main"
                    )
            with c_rerun_main:
                if st.button("🔄 Rerun", key="rerun_batch_main"):
                    stored_payload = first.get("payload")
                    if not stored_payload:
                        st.error("No stored payload found.")
                    else:
                        user = st.session_state.current_user.get("username") if 'current_user' in st.session_state and st.session_state.current_user else "guest"
                        if auth_mgr.deduct_credits(user, 1):
                            with st.spinner(f"🔄 Re-generating {first['angle']}..."):
                                res = generate_image_from_prompt(stored_payload, get_user_out_dir_func("Characters/Concepts"))
                                if res["status"] == "success":
                                    # Overwrite path in session state
                                    st.session_state['char_batch_results'][0]['path'] = res['image_path']
                                    st.success(f"✅ Recreated {first['angle']}!")
                                    st.rerun()
                                else:
                                    auth_mgr.add_credits(user, 1)
                                    st.error(f"Failed to rerun: {res.get('logs')}")
                        else:
                            st.warning("Not enough credits to rerun.")
            
            # Show the rest below in columns
            if len(batch) > 1:
                st.markdown("##### Additional Angles")
                cols = st.columns(min(len(batch)-1, 3))
                for i, item in enumerate(batch[1:]):
                    actual_idx = i + 1
                    with cols[i % len(cols)]:
                         st.image(item['path'], caption=item['angle'], use_container_width=True)
                         
                         c_dl_sub, c_rerun_sub = st.columns(2)
                         with c_dl_sub:
                             with open(item['path'], "rb") as f:
                                 st.download_button(
                                     label="⬇️ Download",
                                     data=f,
                                     file_name=f"{char_name}_{item['angle'].replace(' ', '_').lower()}.jpg",
                                     mime="image/jpeg",
                                     key=f"dl_batch_{actual_idx}"
                                 )
                         with c_rerun_sub:
                             if st.button("🔄 Rerun", key=f"rerun_batch_{actual_idx}"):
                                 stored_payload = item.get("payload")
                                 if not stored_payload:
                                     st.error("No payload found.")
                                 else:
                                     user = st.session_state.current_user.get("username") if 'current_user' in st.session_state and st.session_state.current_user else "guest"
                                     if auth_mgr.deduct_credits(user, 1):
                                         with st.spinner(f"🔄 Re-generating {item['angle']}..."):
                                             res = generate_image_from_prompt(stored_payload, get_user_out_dir_func("Characters/Concepts"))
                                             if res["status"] == "success":
                                                 # Overwrite path in session state
                                                 st.session_state['char_batch_results'][actual_idx]['path'] = res['image_path']
                                                 st.success(f"✅ Recreated {item['angle']}!")
                                                 st.rerun()
                                             else:
                                                 auth_mgr.add_credits(user, 1)
                                                 st.error(f"Failed: {res.get('logs')}")
                                     else:
                                         st.warning("Not enough credits.")
                         
        elif 'char_preview' in st.session_state:
            preview_path = st.session_state['char_preview']
            st.image(preview_path, caption="Concept Preview", use_container_width=True)
            
            with open(preview_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Image",
                    data=f,
                    file_name=f"{char_name}_concept.jpg",
                    mime="image/jpeg",
                    key="dl_single_preview"
                )
                
            # Save Actions
            c_save, c_sheet = st.columns(2)
            with c_save:
                if st.button("Save as New Asset", use_container_width=True):
                     if char_name:
                         # Use Unified Helper
                         res_save = promote_image_to_asset(
                             preview_path, 
                             user, 
                             "Characters", 
                             char_name, 
                             st.session_state.get('char_final_prompt', '')
                         )
                         
                         if res_save["status"] == "success":
                             st.success(f"Saved {char_name} to Assets!")
                             st.info(res_save.get("logs", ""))
                             # Clear Cache
                             st.cache_data.clear()
                             time.sleep(1)
                             st.rerun()
                         else:
                             st.error(f"Save Failed: {res_save.get('error')}")
                     else:
                         st.error("Enter a name in the form.")
            
            with c_sheet:
                if st.button("Lock & Create Sheet", use_container_width=True, type="secondary"):
                    st.session_state["lock_identity_path"] = preview_path
                    st.session_state["trigger_lock_sheet"] = True
                    st.rerun()

        # Handle Triggered Lock Sheet
        if st.session_state.get("trigger_lock_sheet"):
            st.session_state["trigger_lock_sheet"] = False # Reset
            
            attrs = st.session_state.get("char_last_attrs")
            lock_path = st.session_state.get("lock_identity_path")
            
            if attrs and lock_path:
                # Re-import not needed as we imported at top
                    base_prompt = build_character_prompt(attrs)
                    full_prompt = get_character_sheet_prompt(base_prompt)
                    target_w, target_h = 896, 1152  # 4:5 vertical
                    
                    user = st.session_state.current_user.get("username")
                    if auth_mgr.deduct_credits(user, 1):
                        prog_ph = st.empty()
                        # from execution.magic_ui import circular_progress
                        with prog_ph.container():
                             circular_progress()
                             st.caption("Creating in Studio...")
                             
                        assets = [{
                            "path": lock_path,
                            "label": f"Cast: {char_name or 'Main'}"
                        }]
                        payload = {
                            "positive_prompt": full_prompt,
                            "width": target_w, "height": target_h,
                            "aspect_ratio": "4:5",
                            "image_size": "4K",
                            "model_type": "nano",
                            "assets": assets
                        }
                    res = generate_image_from_prompt(payload, get_user_out_dir_func("Characters/Concepts"))
                    if res["status"] == "success":
                        st.session_state['char_preview'] = res['image_path']
                        st.session_state['char_final_prompt'] = full_prompt
                        st.toast("Identity Locked & Sheet Created!")
                        st.rerun()
                    else:
                        auth_mgr.add_credits(user, 1)
                        st.error("Failed to generate sheet.")
            elif not lock_path:
                st.error("No identity locked. Please generate a character first.")
        card_end()
