"""
Multi-Shot Character Reference Generator

Generates multiple angles of a character from a single reference image.
"""

import streamlit as st
from execution.character_utils import get_character_sheet_prompt, get_product_sheet_prompt
from execution.generate_image import generate_image_from_prompt
from execution.auth import auth_mgr
import os
import google.generativeai as genai

def render_multishot_ui(get_user_out_dir_func):
    """
    Renders the Multi-Shot reference generator UI.
    
    Args:
        get_user_out_dir_func: Function to get user output directory
    """
    # ── Session state migration: clear stale dropdown keys from old names ──
    stale_mode = st.session_state.get("multishot_mode_select", "")
    if stale_mode not in [
        "Character Sheet (5 Angles - Vertical)",
        "Product Sheet (4 Angles)",
        "Individual Shots (Batch)",
        "Single Custom Angle",
        "End Frame Generator",
        "Cinematic Coverage (Scene)",
        ""
    ]:
        del st.session_state["multishot_mode_select"]

    st.markdown("### Multi-Shot Reference Generator")
    st.info("Upload a character or product reference and generate multiple angles for consistency across your content.")
    
    # --- Character & Outfit Reference Dropdowns ---
    assets_data = st.session_state.get("global_assets", {})
    characters_data = assets_data.get("characters", {}).copy()
    characters_data.update(assets_data.get("relations", {}))  # Include friends
    outfits_data = assets_data.get("outfits", {})
    
    char_list = ["None (use uploaded reference only)"] + sorted(characters_data.keys())
    outfit_list = ["None"] + sorted(outfits_data.keys())
    
    st.markdown("**🎭 Character/Product & Outfit Reference**")
    ref_col1, ref_col2 = st.columns(2)
    with ref_col1:
        selected_char = st.selectbox(
            "Character Reference",
            char_list,
            index=0,
            help="Select a character from your asset library for identity consistency",
            key="ms_char_select"
        )
    with ref_col2:
        selected_outfit = st.selectbox(
            "Outfit Reference",
            outfit_list,
            index=0,
            help="Select an outfit for wardrobe consistency",
            key="ms_outfit_select"
        )
    
    # Resolve paths
    char_ref_path = characters_data.get(selected_char) if selected_char != "None (use uploaded reference only)" else None
    outfit_ref_path = outfits_data.get(selected_outfit) if selected_outfit != "None" else None
    
    # Show thumbnails if selected
    if char_ref_path or outfit_ref_path:
        thumb_cols = st.columns(2)
        with thumb_cols[0]:
            if char_ref_path:
                st.image(char_ref_path, caption=selected_char, width=120)
        with thumb_cols[1]:
            if outfit_ref_path:
                st.image(outfit_ref_path, caption=selected_outfit, width=120)
    
    st.divider()
    
    # --- Mode Selection (OUTSIDE form so it reruns instantly) ---
    st.markdown("**1. Output Format**")
    ms_mode_col, ms_res_col = st.columns([2, 1])
    with ms_mode_col:
        multishot_mode = st.selectbox(
            "Generation Mode",
            [
                "Character Sheet (5 Angles - Vertical)", 
                "Product Sheet (4 Angles)",
                "Individual Shots (Batch)", 
                "Single Custom Angle",
                "End Frame Generator",
                "Cinematic Coverage (Scene)"
            ],
            key="multishot_mode_select"
        )
    with ms_res_col:
        ms_resolution = st.selectbox("Resolution", ["1K", "2K", "4K"], index=0, key="ms_res", help="Higher = sharper but slower")
    
    # Mode-specific options (also outside form for instant reactivity)
    selected_angles = []
    custom_angle = ""
    endframe_description = ""
    transition_style = "Moderate"
    endframe_ar = "16:9"
    # Cinematic Coverage state
    coverage_scene = ""
    coverage_angles = []
    coverage_cast = []
    coverage_outfits = {}
    
    if multishot_mode == "Individual Shots (Batch)":
        angle_opts = [
            "Front View",
            "Side View (Left)",
            "Side View (Right)",
            "3/4 View (Left)",
            "3/4 View (Right)",
            "Back View",
            "Over Shoulder",
            "Low Angle",
            "High Angle"
        ]
        selected_angles = st.multiselect(
            "Select Angles to Generate",
            angle_opts,
            default=["Front View", "Side View (Left)", "3/4 View (Left)", "Back View"]
        )
    elif multishot_mode == "Single Custom Angle":
        custom_angle = st.text_input(
            "Describe the Angle/Pose",
            placeholder="e.g. looking over shoulder, confident expression"
        )
    elif multishot_mode == "End Frame Generator":
        st.markdown("🎬 **Cinematic End Frame** — Describe how the scene should end")
        
        # Apply AI Director prefill BEFORE widget renders (sets the widget key)
        if "endframe_prefill" in st.session_state:
            st.session_state["endframe_desc_key"] = st.session_state.pop("endframe_prefill")
        
        endframe_description = st.text_area(
            "End Frame Description",
            placeholder="e.g. character turns away from camera, walking into a sunset, dramatic silhouette",
            height=100,
            help="Describe what changes between the start frame and end frame",
            key="endframe_desc_key"
        )
        
        # --- AI Director Vision Button ---
        dir_col1, dir_col2 = st.columns([1, 1])
        with dir_col1:
            if st.button("🎬 AI Director Vision", help="AI analyzes your start frame and suggests an end frame", key="ai_director_btn"):
                st.session_state["run_ai_director"] = True
        
        # Show AI Director suggestion if available
        if st.session_state.get("ai_director_suggestion"):
            st.success(f"🎬 **Director's Vision:** {st.session_state['ai_director_suggestion']}")
            col_use, col_retry = st.columns(2)
            with col_use:
                if st.button("✅ Use This Description", key="use_director_suggestion"):
                    st.session_state["endframe_prefill"] = st.session_state["ai_director_suggestion"]
                    del st.session_state["ai_director_suggestion"]
                    st.rerun()
            with col_retry:
                if st.button("🔄 Get Another Suggestion", key="retry_director"):
                    st.session_state["run_ai_director"] = True
                    if "ai_director_suggestion" in st.session_state:
                        del st.session_state["ai_director_suggestion"]
        
        # Execute AI Director if triggered
        if st.session_state.pop("run_ai_director", False):
            temp_path = os.path.join("output", "temp_multishot_ref.png")
            if os.path.exists(temp_path):
                with st.spinner("🎬 Director is analyzing your start frame..."):
                    try:
                        from dotenv import load_dotenv
                        load_dotenv(override=True)
                        google_key = os.getenv("GOOGLE_API_KEY")
                        if not google_key:
                            st.error("Missing GOOGLE_API_KEY for AI Director.")
                        else:
                            genai.configure(api_key=google_key)
                            model = genai.GenerativeModel("gemini-2.0-flash")
                            
                            from PIL import Image
                            start_img = Image.open(temp_path)
                            
                            # Build context from BOTH text fields
                            endframe_input = st.session_state.get("endframe_desc_key", "")
                            additional_input = st.session_state.get("multishot_additional", "")
                            extra_context = ""
                            if endframe_input:
                                extra_context += f"User's end frame idea: {endframe_input}"
                            if additional_input:
                                extra_context += f"\nAdditional details: {additional_input}"
                            
                            director_prompt = (
                                "You are an AWARD-WINNING CINEMATOGRAPHER analyzing a START FRAME from a shot.\n\n"
                                "TASK: Suggest what the END FRAME of this same shot should look like.\n\n"
                                "Analyze the image and describe:\n"
                                "1. What cinematic movement should happen (camera pan, dolly, zoom, etc.)\n"
                                "2. How the subject's pose/position should change\n"
                                "3. How the lighting/mood should evolve\n"
                                "4. What makes this transition feel cinematic and emotionally impactful\n\n"
                                "OUTPUT: Write ONLY the end frame description in 2-3 sentences. "
                                "Be specific and visual. No JSON, no labels — just the description.\n"
                            )
                            if extra_context:
                                director_prompt += f"\nCONTEXT FROM USER:\n{extra_context}\n\nIncorporate the user's intent into your suggestion."
                            
                            response = model.generate_content([director_prompt, start_img])
                            suggestion = response.text.strip()
                            
                            st.session_state["ai_director_suggestion"] = suggestion
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"AI Director Error: {e}")
            else:
                st.warning("⚠️ Upload a start frame image first, then try AI Director.")
        
        ef_col1, ef_col2 = st.columns(2)
        with ef_col1:
            transition_style = st.selectbox(
                "Transition Intensity",
                ["Subtle", "Moderate", "Dramatic"],
                index=1,
                help="How much the end frame can deviate from the start frame"
            )
        with ef_col2:
            endframe_ar = st.selectbox(
                "Aspect Ratio",
                ["16:9", "4:5", "1:1", "9:16"],
                index=0,
                help="Cinematic 16:9 recommended"
            )
            endframe_res = st.selectbox("Resolution", ["1K", "2K", "4K"], index=0, key="ms_ef_res", help="Higher = sharper but slower")
    elif multishot_mode == "Cinematic Coverage (Scene)":
        st.markdown("🎬 **Cinematic Scene Coverage** — Same moment, multiple camera angles")
        st.caption("Select your cast, describe the scene, and choose which angles to cover.")
        
        # --- Multi-Character Selection ---
        st.markdown("**🎭 Cast Selection**")
        char_options = sorted(characters_data.keys())
        coverage_cast = st.multiselect(
            "Select Characters in Scene",
            char_options,
            default=[],
            help="Choose 1-4 characters that appear in this scene",
            max_selections=4,
            key="coverage_cast_select"
        )
        
        # Per-character outfit assignment
        if coverage_cast:
            st.markdown("**👔 Outfit Assignment**")
            outfit_options = ["None"] + sorted(outfits_data.keys())
            outfit_cols = st.columns(min(len(coverage_cast), 4))
            for i, char_name in enumerate(coverage_cast):
                with outfit_cols[i % len(outfit_cols)]:
                    clean_name = char_name.replace("(My) ", "")
                    coverage_outfits[char_name] = st.selectbox(
                        f"{clean_name}",
                        outfit_options,
                        index=0,
                        key=f"coverage_outfit_{i}"
                    )
            
            # Show cast + outfit thumbnails
            thumb_cols = st.columns(min(len(coverage_cast), 4))
            for i, char_name in enumerate(coverage_cast):
                with thumb_cols[i % len(thumb_cols)]:
                    c_path = characters_data.get(char_name)
                    if c_path:
                        st.image(c_path, caption=char_name.replace("(My) ", ""), width=100)
                    # Show outfit thumbnail if selected
                    selected_outfit_name = coverage_outfits.get(char_name, "None")
                    if selected_outfit_name != "None":
                        o_path = outfits_data.get(selected_outfit_name)
                        if o_path:
                            st.image(o_path, caption=f"👔 {selected_outfit_name}", width=100)
        
        st.divider()
        
        # --- Scene Description ---
        # Apply AI Director prefill BEFORE widget renders
        if "coverage_scene_prefill" in st.session_state:
            st.session_state["coverage_scene_key"] = st.session_state.pop("coverage_scene_prefill")
        
        coverage_scene = st.text_area(
            "Scene Description",
            placeholder="e.g. Two characters face each other across a dimly lit bar, tension building. Rain streaks the window behind them.",
            height=120,
            help="Describe the moment happening — all angles will capture this same moment",
            key="coverage_scene_key"
        )
        
        # --- AI Director Vision for Coverage ---
        dir_col1, dir_col2 = st.columns([1, 1])
        with dir_col1:
            if st.button("🎬 AI Director Vision", help="AI analyzes your reference and suggests a scene", key="coverage_director_btn"):
                st.session_state["run_coverage_director"] = True
        
        # Show suggestion if available
        if st.session_state.get("coverage_director_suggestion"):
            st.success(f"🎬 **Director's Vision:** {st.session_state['coverage_director_suggestion']}")
            col_use, col_retry = st.columns(2)
            with col_use:
                if st.button("✅ Use This Scene", key="use_coverage_suggestion"):
                    st.session_state["coverage_scene_prefill"] = st.session_state["coverage_director_suggestion"]
                    del st.session_state["coverage_director_suggestion"]
                    st.rerun()
            with col_retry:
                if st.button("🔄 Get Another", key="retry_coverage_director"):
                    st.session_state["run_coverage_director"] = True
                    if "coverage_director_suggestion" in st.session_state:
                        del st.session_state["coverage_director_suggestion"]
        
        # Execute Coverage AI Director if triggered
        if st.session_state.pop("run_coverage_director", False):
            temp_path = os.path.join("output", "temp_multishot_ref.png")
            has_frame = os.path.exists(temp_path)
            with st.spinner("🎬 Director is analyzing your scene..."):
                try:
                    from dotenv import load_dotenv
                    load_dotenv(override=True)
                    google_key = os.getenv("GOOGLE_API_KEY")
                    if not google_key:
                        st.error("Missing GOOGLE_API_KEY for AI Director.")
                    else:
                        genai.configure(api_key=google_key)
                        model = genai.GenerativeModel("gemini-2.0-flash")
                        
                        # Build rich context from all inputs
                        context_parts = []
                        
                        # Cast info
                        if coverage_cast:
                            cast_names = [c.replace("(My) ", "") for c in coverage_cast]
                            context_parts.append(f"CHARACTERS IN SCENE: {', '.join(cast_names)}")
                            # Outfits
                            outfit_info = []
                            for c in coverage_cast:
                                o = coverage_outfits.get(c, "None")
                                if o != "None":
                                    outfit_info.append(f"{c.replace('(My) ', '')} wearing {o}")
                            if outfit_info:
                                context_parts.append(f"OUTFITS: {'; '.join(outfit_info)}")
                        
                        # Selected angles
                        sel_angles = st.session_state.get("coverage_angles_select", [])
                        if sel_angles:
                            context_parts.append(f"CAMERA ANGLES PLANNED: {', '.join(sel_angles)}")
                        
                        # User's scene description so far
                        scene_input = st.session_state.get("coverage_scene_key", "")
                        if scene_input:
                            context_parts.append(f"USER'S SCENE IDEA: {scene_input}")
                        
                        # Additional details
                        additional_input = st.session_state.get("multishot_additional", "")
                        if additional_input:
                            context_parts.append(f"ADDITIONAL DETAILS: {additional_input}")
                        
                        context_block = "\n".join(context_parts)
                        
                        director_prompt = (
                            "You are an AWARD-WINNING FILM DIRECTOR planning scene coverage.\n\n"
                            "TASK: Write a vivid, cinematic SCENE DESCRIPTION for a dramatic moment.\n\n"
                            f"CONTEXT:\n{context_block}\n\n"
                            "Write a rich scene description (3-4 sentences) that:\n"
                            "1. Sets the environment/location with vivid detail\n"
                            "2. Describes the characters' positions, body language, and emotional state\n"
                            "3. Establishes the mood, lighting, and atmosphere\n"
                            "4. Creates dramatic tension or emotional weight\n\n"
                            "OUTPUT: Write ONLY the scene description. No labels, no JSON.\n"
                            "Incorporate the user's ideas if provided. Be specific and visual.\n"
                        )
                        
                        # Include reference image if available
                        content_parts = [director_prompt]
                        if has_frame:
                            from PIL import Image
                            start_img = Image.open(temp_path)
                            content_parts.append(start_img)
                        
                        response = model.generate_content(content_parts)
                        suggestion = response.text.strip()
                        
                        st.session_state["coverage_director_suggestion"] = suggestion
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"AI Director Error: {e}")
        
        # --- Cinematic Angle Presets ---
        base_angles = [
            # === CORE COVERAGE ===
            "Wide Establishing Shot",
            "Two-Shot (Medium)",
            "Low Angle Power Shot",
            "High Angle Overview",
            "Dutch Angle (Tension)",
            "Extreme Close-Up (Detail)",
            # === CLASSIC CINEMATIC ===
            "Cowboy Shot (Mid-Thigh)",
            "Full Body Shot",
            "Profile Shot (Side View)",
            "Three-Quarter Shot",
            "Insert Shot (Object Detail)",
            "Reaction Shot",
            "Point-of-View (POV)",
            "Bird's Eye Top-Down",
            "Worm's Eye (Ground Level)",
            # === CINEMATOGRAPHER SIGNATURES ===
            "Kubrick One-Point Perspective",
            "Spielberg Oner (Long Take)",
            "Tarantino Trunk Shot",
            "Wes Anderson Symmetry",
            "Hitchcock Vertigo Zoom",
            "Deakins Natural Light",
            "Vilmos Zsigmond Flare Shot",
            "Gordon Willis Godfather Shadow",
            "Emmanuel Lubezki Golden Hour",
            "Bradford Young Silhouette",
            # === ADVANCED TECHNIQUES ===
            "Rack Focus Pull",
            "Split Diopter (Dual Focus)",
            "Mirror/Reflection Shot",
            "Foreground Framing",
            "Doorway / Threshold Shot",
            "Negative Space Composition",
            "Chiaroscuro (High Contrast)",
            "Shallow DOF Bokeh Portrait",
            "Lens Flare / Backlit",
            "Handheld Intimate"
        ]
        # Add per-character angles
        for char_name in coverage_cast:
            clean = char_name.replace("(My) ", "")
            base_angles.append(f"Over-the-Shoulder ({clean})")
            base_angles.append(f"Close-Up ({clean})")
            base_angles.append(f"Medium Shot ({clean})")
        
        # Smart defaults based on cast size
        if len(coverage_cast) >= 2:
            c1 = coverage_cast[0].replace("(My) ", "")
            c2 = coverage_cast[1].replace("(My) ", "")
            default_angles = [
                "Wide Establishing Shot",
                f"Over-the-Shoulder ({c1})",
                f"Over-the-Shoulder ({c2})",
                f"Close-Up ({c1})"
            ]
        elif len(coverage_cast) == 1:
            c1 = coverage_cast[0].replace("(My) ", "")
            default_angles = [
                "Wide Establishing Shot",
                f"Medium Shot ({c1})",
                f"Close-Up ({c1})",
                "Low Angle Power Shot"
            ]
        else:
            default_angles = ["Wide Establishing Shot", "Two-Shot (Medium)", "Low Angle Power Shot", "High Angle Overview"]
        
        # Filter defaults to only include available options
        default_angles = [a for a in default_angles if a in base_angles]
        
        coverage_angles = st.multiselect(
            "Camera Angles to Generate",
            base_angles,
            default=default_angles[:4],
            help="Select your angles. Each costs 1 credit.",
            max_selections=8,
            key="coverage_angles_select"
        )
    
    st.divider()
    
    # Additional prompts (outside form)
    additional_prompt = st.text_area(
        "Additional Details (Optional)",
        placeholder="e.g. wearing black jacket, cyberpunk aesthetic, neon lighting",
        height=80,
        help="Add specific details you want to maintain across all angles",
        key="multishot_additional"
    )
    
    st.divider()
    
    # --- Image Upload (OUTSIDE form so it persists across reruns) ---
    st.markdown("**📸 Main Target Image (Character or Product)**")
    st.caption("Upload your best single-view of the character or product — this becomes the source of truth for outfit, pose, or design.")
    ref_upload = st.file_uploader(
        "Main Reference Image (single view)", 
        type=['png', 'jpg', 'jpeg'],
        help="Your best generated image — the one you want to rotate into other angles",
        key="multishot_ref_uploader"
    )
    
    # Persist main ref to disk
    temp_ref_path = os.path.join("output", "temp_multishot_ref.png")
    if ref_upload:
        os.makedirs("output", exist_ok=True)
        with open(temp_ref_path, "wb") as f:
            f.write(ref_upload.getbuffer())
        st.session_state["multishot_ref_saved"] = True
        st.image(ref_upload, caption="✅ Main Reference", use_container_width=True)
    elif st.session_state.get("multishot_ref_saved") and os.path.exists(temp_ref_path):
        st.image(temp_ref_path, caption="Main Reference (saved)", use_container_width=True)
    
    st.divider()
    
    # --- Additional Reference Images ---
    st.markdown("**🔒 Additional Reference Images (Up to 13)**")
    st.caption(
        "Upload up to 13 additional photos — different angles, lighting, outfits, or close-ups. "
        "More references = stronger identity/design lock across all generated panels."
    )
    face_ref_uploads = st.file_uploader(
        "Additional Reference Images",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="Any photos that show the subject: face close-ups, product details, 3/4 views, etc.",
        key="multishot_face_refs"
    )
    
    # Save face refs to disk
    temp_face_ref_dir = os.path.join("output", "temp_face_refs")
    os.makedirs(temp_face_ref_dir, exist_ok=True)
    face_ref_paths = []
    MAX_REFS = 13
    
    if face_ref_uploads:
        # Cap to 13
        face_ref_uploads = face_ref_uploads[:MAX_REFS]
        if len(face_ref_uploads) > MAX_REFS:
            st.warning(f"Only the first {MAX_REFS} images will be used.")
        # Clear old refs
        import glob
        for old in glob.glob(os.path.join(temp_face_ref_dir, "face_ref_*.png")):
            try: os.remove(old)
            except: pass
        
        cols = st.columns(min(len(face_ref_uploads), 7))
        for idx, face_file in enumerate(face_ref_uploads):
            fpath = os.path.join(temp_face_ref_dir, f"face_ref_{idx}.png")
            with open(fpath, "wb") as f:
                f.write(face_file.getbuffer())
            face_ref_paths.append(fpath)
            with cols[idx % 7]:
                st.image(face_file, caption=f"Ref {idx+1}", use_container_width=True)
        st.session_state["multishot_face_ref_count"] = len(face_ref_paths)
        st.caption(f"✅ {len(face_ref_paths)} reference image(s) loaded")
    elif st.session_state.get("multishot_face_ref_count", 0) > 0:
        # Reload saved refs
        import glob
        saved = sorted(glob.glob(os.path.join(temp_face_ref_dir, "face_ref_*.png")))
        face_ref_paths = saved
        if saved:
            cols = st.columns(min(len(saved), 7))
            for idx, fp in enumerate(saved):
                with cols[idx % 7]:
                    st.image(fp, caption=f"Ref {idx+1}", use_container_width=True)
            st.caption(f"✅ {len(saved)} reference image(s) loaded")
    
    st.divider()
    
    # --- Fidelity / Likeness ---
    st.markdown("**🎯 Identity Fidelity**")
    likeness_val = st.slider(
        "Likeness Strength",
        min_value=0, max_value=100, value=80, step=5,
        key="ms_likeness",
        help="How strictly the model must match the reference face."
    )
    # Tier label
    if likeness_val >= 90:
        fidelity_label = "🔴 **Ultra** — Face clone, zero deviation allowed"
    elif likeness_val >= 80:
        fidelity_label = "🟠 **High** — Strong identity lock on facial structure"
    elif likeness_val >= 60:
        fidelity_label = "🟡 **Medium** — Strong resemblance, some creative latitude"
    elif likeness_val >= 40:
        fidelity_label = "🟢 **Low** — Inspired by the reference, loose match"
    else:
        fidelity_label = "⚪ **None** — No identity constraints, fully creative"
    st.caption(fidelity_label)

    st.divider()

    # --- Generate Button (minimal form) ---
    with st.form("multishot_form"):
        col_q, col_gen = st.columns([1, 2])
        with col_q:
            add_to_queue = st.checkbox("Add to Queue", value=False)
        with col_gen:
            generate_multishot = st.form_submit_button("✨ Generate Multi-Shot", type="primary", use_container_width=True)
    
    # Processing Logic
    has_ref_image = os.path.exists(temp_ref_path) if st.session_state.get("multishot_ref_saved") else False
    if generate_multishot:
        if not has_ref_image:
            st.error("Please upload a main character image first.")
        else:
            user = st.session_state.current_user.get("username") if st.session_state.get("current_user") else "guest"
            
            # Build base prompt with strong identity-lock instruction
            identity_lock_instruction = ""
            if face_ref_paths:
                if multishot_mode == "Product Sheet (4 Angles)":
                    identity_lock_instruction = (
                        " CRITICAL IDENTITY LOCK: Additional reference images of the product are provided. "
                        "You MUST match the product design EXACTLY — same materials, branding, shape, colors, "
                        "and texture. The physical product must remain IDENTICAL across all angle changes. "
                        "Only the camera perspective changes, NOT the product."
                    )
                else:
                    identity_lock_instruction = (
                        " CRITICAL FACE LOCK: Additional face reference images are provided. "
                        "You MUST match the face in those references EXACTLY — same bone structure, "
                        "skin tone, eye shape, nose, lips. The face must remain IDENTICAL "
                        "across all angle changes. Only the camera angle changes, NOT the face."
                    )
            
            subject_noun = "product" if multishot_mode == "Product Sheet (4 Angles)" else "character"
            base_prompt = (
                f"{subject_noun} maintaining EXACT identity, shape, colors, and features from the main reference image"
                + identity_lock_instruction
            )
            if additional_prompt:
                base_prompt += f", {additional_prompt}"

            # --- Inject fidelity tokens (same tiers as Character Creator) ---
            likeness = st.session_state.get("ms_likeness", 80)
            if likeness >= 90:
                base_prompt += (
                    ", (ultra-high fidelity face match:1.6), (DO NOT deviate from reference face:1.5), "
                    "(identical face to reference:1.5), (exact same person:1.5), "
                    "(preserve facial features exactly:1.4), (same bone structure:1.4), "
                    "(same nose shape:1.4), (same jawline:1.4), (same eye shape:1.4), "
                    "(same skin tone:1.3), (same brow shape:1.3), "
                    "(photographic identity match:1.5), DO NOT alter facial features, "
                    "(face clone:1.4)"
                )
            elif likeness >= 80:
                base_prompt += (
                    ", (identical face to reference:1.5), (exact same person:1.5), "
                    "(preserve facial features exactly:1.4), (same bone structure:1.3), "
                    "(same nose shape:1.3), (same jawline:1.3), (same eye shape:1.3), "
                    "(photographic identity match:1.4), DO NOT alter facial features"
                )
            elif likeness >= 60:
                base_prompt += (
                    ", (strong resemblance to reference:1.4), (same face:1.4), "
                    "(preserve key facial features:1.3), (similar bone structure:1.3), "
                    "(match skin tone:1.2), (match eye shape:1.2)"
                )
            elif likeness >= 40:
                base_prompt += ", (inspired by reference:1.2), similar features to reference, (match overall look:1.1)"
            # Below 40: no identity constraints
            
            # Build common asset list — main ref + face identity locks + char/outfit library refs
            def build_assets_list(start_frame_path, label="Main Subject (SOURCE OF TRUTH — match design, outfit, and environment)"):
                """Builds asset payload with main ref, identity locks, and library refs."""
                asset_list = [{"path": start_frame_path, "label": label}]
                
                # Identity likeness locks
                for idx, fp in enumerate(face_ref_paths):
                    if os.path.exists(fp):
                        asset_list.append({
                            "path": fp,
                            "label": f"Cast/Object: IdentityLock (Ref {idx+1}) — SPECIFIC DESIGN/IDENTITY ONLY — DO NOT use for pose or environment"
                        })
                
                # Library character reference
                char_name = None
                if char_ref_path:
                    char_name = selected_char.replace("(My) ", "")
                    asset_list.append({"path": char_ref_path, "label": f"Cast: {char_name}"})
                
                # Library outfit reference
                if outfit_ref_path:
                    outfit_label = f"Outfit for {char_name}" if char_name else f"Outfit: {selected_outfit}"
                    asset_list.append({"path": outfit_ref_path, "label": outfit_label})
                
                return asset_list

            
            # Handle different modes
            if multishot_mode == "Character Sheet (5 Angles - Vertical)":
                # Generate 5-angle vertical character sheet
                full_prompt = get_character_sheet_prompt(base_prompt)
                
                # Credit check
                if auth_mgr.deduct_credits(user, 1):
                    with st.spinner("Generating 5-angle vertical character sheet..."):
                        assets = build_assets_list(temp_ref_path)
                        payload = {
                            "positive_prompt": full_prompt,
                            "aspect_ratio": "4:5",
                            "image_size": st.session_state.get("ms_res", "1K"),
                            "model_type": "nano",
                            "assets": assets
                        }
                        
                        res = generate_image_from_prompt(payload, get_user_out_dir_func("MultiShot"))
                        
                        if res["status"] == "success":
                            st.session_state['multishot_result'] = res['image_path']
                            st.success("✅ Character sheet generated!")
                            st.rerun()
                        else:
                            auth_mgr.add_credits(user, 1)  # Refund
                            st.error(f"Generation failed: {res.get('logs')}")
                else:
                    st.error("Not enough credits.")
            
            elif multishot_mode == "Product Sheet (4 Angles)":
                # Generate 4-angle product sheet
                full_prompt = get_product_sheet_prompt(base_prompt)
                
                # Credit check
                if auth_mgr.deduct_credits(user, 1):
                    with st.spinner("Generating 4-angle product sheet..."):
                        assets = build_assets_list(temp_ref_path)
                        payload = {
                            "positive_prompt": full_prompt,
                            "aspect_ratio": "1:1",  # Square is best for 4-panel grids (2x2)
                            "image_size": st.session_state.get("ms_res", "1K"),
                            "model_type": "nano",
                            "assets": assets
                        }
                        
                        res = generate_image_from_prompt(payload, get_user_out_dir_func("MultiShot"))
                        
                        if res["status"] == "success":
                            st.session_state['multishot_result'] = res['image_path']
                            st.success("✅ Product sheet generated!")
                            st.rerun()
                        else:
                            auth_mgr.add_credits(user, 1)  # Refund
                            st.error(f"Generation failed: {res.get('logs')}")
                else:
                    st.error("Not enough credits.")
            
            elif multishot_mode == "Individual Shots (Batch)":
                # Generate each angle separately
                if not selected_angles:
                    st.error("Please select at least one angle.")
                else:
                    # Credit check for batch
                    total_credits_needed = len(selected_angles)
                    if auth_mgr.deduct_credits(user, total_credits_needed):
                        st.session_state['multishot_batch_results'] = []
                        
                        for angle in selected_angles:
                            with st.spinner(f"Generating {angle}..."):
                                angle_prompt = f"{base_prompt}, {angle.lower()}, professional photography"
                                
                                assets = build_assets_list(temp_ref_path)
                                payload = {
                                    "positive_prompt": angle_prompt,
                                    "aspect_ratio": "4:5",
                                    "image_size": st.session_state.get("ms_res", "1K"),
                                    "model_type": "nano",
                                    "assets": assets
                                }
                                
                                res = generate_image_from_prompt(payload, get_user_out_dir_func("MultiShot"))
                                
                                if res["status"] == "success":
                                    st.session_state['multishot_batch_results'].append({
                                        "angle": angle,
                                        "path": res['image_path']
                                    })
                                    st.toast(f"✅ {angle} complete!")
                                else:
                                    st.error(f"{angle} failed: {res.get('logs')}")
                                    auth_mgr.add_credits(user, 1)  # Refund this one
                        
                        st.success("Batch generation complete!")
                        st.rerun()
                    else:
                        st.error(f"Need {total_credits_needed} credits for this batch.")
            
            elif multishot_mode == "Single Custom Angle":
                if not custom_angle:
                    st.error("Please describe the angle/pose you want.")
                else:
                    # Generate single custom angle
                    if auth_mgr.deduct_credits(user, 1):
                        with st.spinner(f"Generating custom angle..."):
                            custom_prompt = f"{base_prompt}, {custom_angle}, professional photography"
                            
                            assets = build_assets_list(temp_ref_path)
                            payload = {
                                "positive_prompt": custom_prompt,
                                "aspect_ratio": "4:5",
                                "image_size": st.session_state.get("ms_res", "1K"),
                                "model_type": "nano",
                                "assets": assets
                            }
                            
                            res = generate_image_from_prompt(payload, get_user_out_dir_func("MultiShot"))
                            
                            if res["status"] == "success":
                                st.session_state['multishot_result'] = res['image_path']
                                st.success("✅ Custom angle generated!")
                                st.rerun()
                            else:
                                auth_mgr.add_credits(user, 1)  # Refund
                                st.error(f"Generation failed: {res.get('logs')}")
                    else:
                        st.error("Not enough credits.")
            
            elif multishot_mode == "End Frame Generator":
                if not endframe_description:
                    st.error("Please describe what the end frame should look like.")
                else:
                    if auth_mgr.deduct_credits(user, 1):
                        with st.spinner("🎬 Generating cinematic end frame..."):
                            # Build transition intensity instruction
                            intensity_map = {
                                "Subtle": (
                                    "Make MINIMAL changes from the start frame. "
                                    "Keep the same camera angle, lighting, and composition. "
                                    "Only adjust what the user described — small expression changes, slight movement, minor lighting shifts."
                                ),
                                "Moderate": (
                                    "Allow MODERATE changes from the start frame. "
                                    "The scene can shift noticeably — different pose, adjusted camera angle, evolved lighting — "
                                    "but the overall environment and character identity must remain consistent."
                                ),
                                "Dramatic": (
                                    "Allow DRAMATIC changes from the start frame. "
                                    "The scene can transform significantly — major camera movement, lighting overhaul, "
                                    "new positioning — while preserving character identity and scene continuity."
                                )
                            }
                            intensity_instruction = intensity_map.get(transition_style, intensity_map["Moderate"])
                            
                            # Build the cinematic end frame prompt
                            endframe_prompt = (
                                f"CINEMATIC END FRAME GENERATION\n\n"
                                f"You are a cinematic continuity engine. You are given a START FRAME from a shot. "
                                f"Generate the END FRAME of this same shot.\n\n"
                                f"RULES:\n"
                                f"- Maintain EXACT character identity (face, body, clothing) from the start frame\n"
                                f"- Maintain scene continuity (same location, same world, same time of day unless told otherwise)\n"
                                f"- The end frame should feel like a natural conclusion of the same camera shot\n"
                                f"- {intensity_instruction}\n\n"
                                f"WHAT CHANGES IN THE END FRAME:\n"
                                f"{endframe_description}\n"
                            )
                            if additional_prompt:
                                endframe_prompt += f"\nADDITIONAL CONTEXT: {additional_prompt}\n"
                            
                            endframe_prompt += (
                                f"\nSTYLE: Photorealistic, cinematic, professional cinematography, "
                                f"film grain, shallow depth of field"
                            )
                            
                            assets = build_assets_list(temp_ref_path, label="Reference Character (START FRAME - MAINTAIN CONTINUITY)")
                            selected_ar = endframe_ar
                            payload = {
                                "positive_prompt": endframe_prompt,
                                "aspect_ratio": selected_ar,
                                "image_size": st.session_state.get("ms_ef_res", "1K"),
                                "model_type": "nano",
                                "assets": assets
                            }
                            
                            res = generate_image_from_prompt(payload, get_user_out_dir_func("MultiShot"))
                            
                            if res["status"] == "success":
                                st.session_state['endframe_result'] = {
                                    "start_frame": temp_ref_path,
                                    "end_frame": res['image_path'],
                                    "description": endframe_description,
                                    "transition": transition_style
                                }
                                st.success("✅ End frame generated!")
                                st.rerun()
                            else:
                                auth_mgr.add_credits(user, 1)  # Refund
                                st.error(f"Generation failed: {res.get('logs')}")
                    else:
                        st.error("Not enough credits.")
            
            elif multishot_mode == "Cinematic Coverage (Scene)":
                if not coverage_scene:
                    st.error("Please describe the scene.")
                elif not coverage_angles:
                    st.error("Please select at least one camera angle.")
                else:
                    total_credits = len(coverage_angles)
                    if auth_mgr.deduct_credits(user, total_credits):
                        st.session_state['coverage_results'] = []
                        
                        # Build cast assets (same for every shot)
                        cast_assets = []
                        if has_ref_image:
                            cast_assets.append({"path": temp_ref_path, "label": "Reference Character"})
                        for c_name in coverage_cast:
                            c_path = characters_data.get(c_name)
                            if c_path:
                                clean = c_name.replace("(My) ", "")
                                cast_assets.append({"path": c_path, "label": f"Cast: {clean}"})
                                # Add outfit if assigned
                                outfit_choice = coverage_outfits.get(c_name, "None")
                                if outfit_choice != "None":
                                    o_path = outfits_data.get(outfit_choice)
                                    if o_path:
                                        cast_assets.append({"path": o_path, "label": f"Outfit for {clean}"})
                        
                        # Generate each angle with cascading reference
                        last_generated_path = None
                        for shot_idx, angle_name in enumerate(coverage_angles):
                            with st.spinner(f"🎬 Generating {angle_name} ({shot_idx + 1}/{len(coverage_angles)})..."):
                                # Build per-angle camera direction
                                camera_direction = ""
                                if "Wide" in angle_name or "Establishing" in angle_name:
                                    camera_direction = "Wide establishing shot. Full scene visible. All characters in frame. Environmental context emphasized. Deep depth of field."
                                elif "Over-the-Shoulder" in angle_name:
                                    focus_char = angle_name.split("(")[-1].rstrip(")")
                                    camera_direction = f"Over-the-shoulder shot. Camera behind {focus_char}, looking at the other character(s). {focus_char}'s shoulder/back visible in foreground, slightly blurred. Focus on the character they're facing. Shallow depth of field."
                                elif "Close-Up" in angle_name:
                                    if "Extreme" in angle_name:
                                        camera_direction = "Extreme close-up on a key detail — eyes, hands, or an important object. Macro-level detail. Very shallow depth of field."
                                    else:
                                        focus_char = angle_name.split("(")[-1].rstrip(")")
                                        camera_direction = f"Close-up on {focus_char}. Head and shoulders framing. Intimate, emotional. Shallow depth of field with background softly blurred."
                                elif "Medium Shot" in angle_name:
                                    focus_char = angle_name.split("(")[-1].rstrip(")")
                                    camera_direction = f"Medium shot of {focus_char}. Waist-up framing. Character clearly visible with some environmental context. Natural depth of field."
                                elif "Two-Shot" in angle_name:
                                    camera_direction = "Two-shot at medium distance. Both characters in frame, positioned naturally. Balanced composition showing their spatial relationship."
                                elif "Low Angle" in angle_name:
                                    camera_direction = "Low angle shot looking up. Emphasizes power and dominance. Characters appear larger than life. Dramatic perspective."
                                elif "High Angle" in angle_name:
                                    camera_direction = "High angle shot looking down. Creates vulnerability or reveals spatial layout. Bird's eye perspective on the scene."
                                elif "Dutch" in angle_name:
                                    camera_direction = "Dutch angle (tilted frame). Creates unease and tension. Diagonal composition. Disorienting and dramatic."
                                # --- CLASSIC CINEMATIC ---
                                elif "Cowboy" in angle_name:
                                    camera_direction = "Cowboy shot. Framed from mid-thigh up, showing hands and hips. Classic Western framing. Conveys readiness and confidence. Named for showing the gun holster in Westerns."
                                elif "Full Body" in angle_name:
                                    camera_direction = "Full body shot. Character framed head to toe with breathing room. Shows full posture, outfit, and body language. Medium depth of field."
                                elif "Profile" in angle_name:
                                    camera_direction = "Profile shot from the side. Clean 90-degree side view of the character. Strong silhouette emphasis. Shows jawline and profile features. Dramatic rim lighting."
                                elif "Three-Quarter" in angle_name:
                                    camera_direction = "Three-quarter angle shot. Camera at 45 degrees to the subject. Classic portrait angle showing depth and dimension. Flattering perspective with natural depth."
                                elif "Insert" in angle_name:
                                    camera_direction = "Insert shot on a crucial object or detail in the scene — a hand gesture, a prop, a letter, a weapon. Tight framing. Narrative emphasis. Shallow depth of field."
                                elif "Reaction" in angle_name:
                                    camera_direction = "Reaction shot. Focus on a character's emotional response to events. Medium close-up capturing subtle facial expressions. The story is told through their face."
                                elif "POV" in angle_name or "Point-of-View" in angle_name:
                                    camera_direction = "First-person point-of-view shot. Camera IS the character's eyes. What they see, we see. Immersive, subjective perspective. Slight handheld movement for authenticity."
                                elif "Bird" in angle_name and "Eye" in angle_name:
                                    camera_direction = "Bird's eye view. Camera directly overhead looking straight down. God-like perspective. Reveals spatial relationships and patterns. Disorienting, powerful."
                                elif "Worm" in angle_name:
                                    camera_direction = "Worm's eye view. Camera at ground level looking up. Extreme low angle. Characters tower overhead. Ground texture visible in foreground. Dramatic and imposing."
                                # --- CINEMATOGRAPHER SIGNATURES ---
                                elif "Kubrick" in angle_name:
                                    camera_direction = "Kubrick one-point perspective. Perfectly symmetrical composition. Single vanishing point dead center. Hallway or corridor framing. Unsettling precision. Deep depth of field. Every element mathematically balanced."
                                elif "Spielberg" in angle_name or "Oner" in angle_name:
                                    camera_direction = "Spielberg-style long take / oner. Camera moves fluidly through the scene, following action without cuts. Choreographed blocking. Characters move in and out of frame. Naturalistic, immersive. Medium depth of field."
                                elif "Tarantino" in angle_name or "Trunk" in angle_name:
                                    camera_direction = "Tarantino trunk shot. Camera placed inside a car trunk or container looking up at characters peering down. Extreme low angle. Characters dominate the frame from above. Wide-angle lens distortion. Iconic and voyeuristic."
                                elif "Wes Anderson" in angle_name or "Symmetry" in angle_name:
                                    camera_direction = "Wes Anderson symmetrical composition. Perfectly centered subject. Pastel or curated color palette. Flat, tableau-like staging. Deadpan framing. Characters face camera directly. Storybook aesthetic."
                                elif "Hitchcock" in angle_name or "Vertigo" in angle_name:
                                    camera_direction = "Hitchcock vertigo effect (dolly zoom). Background appears to stretch or compress while subject stays same size. Disorienting, psychologically intense. Creates a sense of dread or revelation."
                                elif "Deakins" in angle_name:
                                    camera_direction = "Roger Deakins natural light style. Soft, motivated lighting from practical sources (windows, lamps, fire). No harsh artificial light. Naturalistic color palette. Painterly composition. Atmospheric depth."
                                elif "Zsigmond" in angle_name or "Flare" in angle_name:
                                    camera_direction = "Vilmos Zsigmond lens flare shot. Shooting into a light source (sun, lamp, window). Intentional lens flares streak across the frame. Warm, golden tones. Dreamy, romantic 1970s cinematography aesthetic."
                                elif "Willis" in angle_name or "Godfather" in angle_name:
                                    camera_direction = "Gordon Willis 'Prince of Darkness' style. Deep shadows dominate. Character's eyes barely visible under heavy brow shadow. Top-lit, high contrast. Rich blacks, warm amber tones. The darkness tells the story."
                                elif "Lubezki" in angle_name or "Golden Hour" in angle_name:
                                    camera_direction = "Emmanuel Lubezki golden hour shot. Natural sunlight at magic hour. Long shadows, warm golden tones. Naturalistic, almost spiritual quality. Wide-angle with deep focus. Characters bathed in ethereal light."
                                elif "Bradford" in angle_name or "Silhouette" in angle_name:
                                    camera_direction = "Bradford Young silhouette shot. Character rendered as dark silhouette against a bright background. Minimal detail, maximum emotion. Backlit. The shape and posture tell everything. Moody, poetic, underexposed."
                                # --- ADVANCED TECHNIQUES ---
                                elif "Rack Focus" in angle_name:
                                    camera_direction = "Rack focus pull. Foreground element sharp, background blurred — or vice versa. Guides the viewer's attention. Dramatic shift in focus plane. Reveals hidden information."
                                elif "Split Diopter" in angle_name:
                                    camera_direction = "Split diopter shot. Both foreground and background in sharp focus simultaneously using split-focus lens. Unnatural but striking. Two planes of action visible at once. De Palma signature technique."
                                elif "Mirror" in angle_name or "Reflection" in angle_name:
                                    camera_direction = "Mirror or reflection shot. Character seen through a mirror, window, puddle, or reflective surface. Creates visual duality. Metaphor for inner conflict or hidden self."
                                elif "Foreground" in angle_name:
                                    camera_direction = "Foreground framing shot. An object or element in the near foreground creates a natural frame around the subject. Adds depth layers. Selective focus between planes."
                                elif "Doorway" in angle_name or "Threshold" in angle_name:
                                    camera_direction = "Doorway / threshold shot. Character framed within a door, window, or archway. Creates a frame-within-a-frame. Symbolizes transition, choices, or confinement. John Ford signature."
                                elif "Negative Space" in angle_name:
                                    camera_direction = "Negative space composition. Character occupies a small portion of the frame. Vast empty space dominates. Creates isolation, loneliness, or insignificance. Minimalist and powerful."
                                elif "Chiaroscuro" in angle_name:
                                    camera_direction = "Chiaroscuro lighting. Extreme contrast between light and dark. Renaissance painting influence. Single hard light source. Deep blacks and bright highlights. Dramatic, sculptural quality."
                                elif "Bokeh" in angle_name or "Shallow DOF" in angle_name:
                                    camera_direction = "Shallow depth of field portrait. Subject tack-sharp with creamy bokeh background. Wide aperture, f/1.2-1.4 aesthetic. Dreamy out-of-focus highlights. Intimate and cinematic."
                                elif "Lens Flare" in angle_name or "Backlit" in angle_name:
                                    camera_direction = "Backlit lens flare shot. Strong light source behind the subject. Rim light outlines the character. Intentional flares and haze. Ethereal, dramatic, J.J. Abrams-esque."
                                elif "Handheld" in angle_name:
                                    camera_direction = "Handheld intimate shot. Slightly unsteady, raw, documentary feel. Close to the subject. Creates urgency and authenticity. Paul Greengrass / Dardenne Brothers style."
                                else:
                                    camera_direction = f"{angle_name}. Professional cinematography."
                                
                                # Build the scene prompt for this angle
                                coverage_prompt = (
                                    f"CINEMATIC SCENE COVERAGE — {angle_name}\n\n"
                                    f"SCENE: {coverage_scene}\n\n"
                                    f"CAMERA: {camera_direction}\n\n"
                                    f"RULES:\n"
                                    f"- This is ONE MOMENT captured from this specific camera angle\n"
                                    f"- ALL characters must maintain their EXACT identity from reference images\n"
                                    f"- ALL characters must wear their assigned outfits EXACTLY\n"
                                    f"- The scene, lighting, and environment must be CONSISTENT across all angles\n"
                                    f"- Photorealistic, cinematic, professional cinematography, film grain\n"
                                )
                                if additional_prompt:
                                    coverage_prompt += f"\nADDITIONAL CONTEXT: {additional_prompt}\n"
                                
                                # Cascading reference: include prior shot for scene consistency
                                shot_assets = list(cast_assets)  # Copy base assets
                                if last_generated_path and os.path.exists(last_generated_path):
                                    coverage_prompt += (
                                        f"\nSCENE CONTINUITY: The attached 'Prior Angle' image shows this SAME scene "
                                        f"from a different camera angle. Match the EXACT environment, lighting, "
                                        f"color palette, set design, and character wardrobe from that image.\n"
                                    )
                                    shot_assets.append({
                                        "path": last_generated_path, 
                                        "label": "Prior Angle (SCENE CONTINUITY - MATCH ENVIRONMENT & LIGHTING)"
                                    })
                                
                                payload = {
                                    "positive_prompt": coverage_prompt,
                                    "aspect_ratio": "16:9",
                                    "image_size": st.session_state.get("ms_res", "1K"),
                                    "model_type": "nano",
                                    "assets": shot_assets
                                }
                                
                                res = generate_image_from_prompt(payload, get_user_out_dir_func("MultiShot"))
                                
                                if res["status"] == "success":
                                    last_generated_path = res['image_path']  # Chain for next shot
                                    st.session_state['coverage_results'].append({
                                        "angle": angle_name,
                                        "path": res['image_path'],
                                        "payload": payload  # Store for rerun
                                    })
                                    st.toast(f"✅ {angle_name} complete!")
                                else:
                                    st.error(f"{angle_name} failed: {res.get('logs')}")
                                    auth_mgr.add_credits(user, 1)  # Refund this one
                        
                        st.success(f"🎬 Cinematic coverage complete! {len(st.session_state.get('coverage_results', []))} shots generated.")
                        st.rerun()
                    else:
                        st.error(f"Need {total_credits} credits for this coverage.")
    
    # Display Results
    st.divider()
    st.markdown("#### Results")
    
    # End Frame side-by-side display
    if 'endframe_result' in st.session_state:
        ef_data = st.session_state['endframe_result']
        st.markdown(f"**🎬 End Frame** — *{ef_data.get('transition', '')}* transition")
        st.caption(f"Description: {ef_data.get('description', '')}")
        
        col_start, col_end = st.columns(2)
        with col_start:
            st.markdown("**START FRAME**")
            if os.path.exists(ef_data['start_frame']):
                st.image(ef_data['start_frame'], caption="Start Frame", use_container_width=True)
        with col_end:
            st.markdown("**END FRAME**")
            if os.path.exists(ef_data['end_frame']):
                st.image(ef_data['end_frame'], caption="End Frame", use_container_width=True)
                with open(ef_data['end_frame'], "rb") as f:
                    st.download_button(
                        "⬇️ Download End Frame",
                        f,
                        file_name=os.path.basename(ef_data['end_frame']),
                        mime="image/png",
                        key="dl_endframe"
                    )
        st.divider()
    
    # Single result display
    if 'multishot_result' in st.session_state:
        result_path = st.session_state['multishot_result']
        if os.path.exists(result_path):
            st.image(result_path, caption="Generated Multi-Shot", use_container_width=True)
            with open(result_path, "rb") as f:
                st.download_button(
                    "⬇️ Download Result",
                    f,
                    file_name=os.path.basename(result_path),
                    mime="image/png"
                )
    
    # Batch results display
    if 'multishot_batch_results' in st.session_state:
        batch_results = st.session_state['multishot_batch_results']
        if batch_results:
            cols = st.columns(min(3, len(batch_results)))
            for idx, result in enumerate(batch_results):
                with cols[idx % 3]:
                    if os.path.exists(result['path']):
                        st.image(result['path'], caption=result['angle'], use_container_width=True)
                        with open(result['path'], "rb") as f:
                            st.download_button(
                                f"⬇️ {result['angle']}",
                                f,
                                file_name=os.path.basename(result['path']),
                                mime="image/png",
                                key=f"dl_multishot_{idx}"
                            )
    
    # Cinematic Coverage results (2x2 grid)
    if 'coverage_results' in st.session_state:
        cov_results = st.session_state['coverage_results']
        if cov_results:
            st.markdown("**🎬 Cinematic Coverage**")
            
            # 2x2 grid
            for row_start in range(0, len(cov_results), 2):
                row_items = cov_results[row_start:row_start + 2]
                cols = st.columns(2)
                for i, result in enumerate(row_items):
                    actual_idx = row_start + i
                    with cols[i]:
                        if os.path.exists(result['path']):
                            st.image(result['path'], caption=result['angle'], use_container_width=True)
                            btn_dl, btn_rerun = st.columns(2)
                            with btn_dl:
                                with open(result['path'], "rb") as f:
                                    st.download_button(
                                        f"⬇️ Download",
                                        f,
                                        file_name=os.path.basename(result['path']),
                                        mime="image/png",
                                        key=f"dl_coverage_{actual_idx}"
                                    )
                            with btn_rerun:
                                if st.button(f"🔄 Rerun", key=f"rerun_coverage_{actual_idx}"):
                                    # Run regeneration INLINE — no intermediate rerun
                                    stored_payload = result.get("payload")
                                    if not stored_payload:
                                        st.error("No stored payload — regenerate all shots first.")
                                    else:
                                        user = st.session_state.current_user.get("username") if st.session_state.get("current_user") else "guest"
                                        if auth_mgr.deduct_credits(user, 1):
                                            with st.spinner(f"🔄 Re-generating {result['angle']}..."):
                                                # Build assets with cascading ref from adjacent shot
                                                rerun_assets = [a for a in stored_payload.get("assets", []) if "Prior Angle" not in a.get("label", "")]
                                                adj_idx = actual_idx - 1 if actual_idx > 0 else (actual_idx + 1 if actual_idx + 1 < len(cov_results) else None)
                                                if adj_idx is not None and os.path.exists(cov_results[adj_idx]['path']):
                                                    rerun_assets.append({
                                                        "path": cov_results[adj_idx]['path'],
                                                        "label": "Prior Angle (SCENE CONTINUITY - MATCH ENVIRONMENT & LIGHTING)"
                                                    })
                                                
                                                rerun_payload = dict(stored_payload)
                                                rerun_payload["assets"] = rerun_assets
                                                
                                                res = generate_image_from_prompt(rerun_payload, get_user_out_dir_func("MultiShot"))
                                                if res["status"] == "success":
                                                    cov_results[actual_idx]["path"] = res['image_path']
                                                    cov_results[actual_idx]["payload"] = rerun_payload
                                                    st.session_state['coverage_results'] = cov_results
                                                    st.toast(f"✅ {result['angle']} re-generated!")
                                                    st.rerun()
                                                else:
                                                    auth_mgr.add_credits(user, 1)
                                                    st.error(f"Rerun failed: {res.get('logs')}")
                                        else:
                                            st.error("Not enough credits to rerun.")

