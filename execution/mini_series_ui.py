
import streamlit as st
import os
import json
from execution.magic_ui import card_begin, card_end
from execution.character_utils import build_character_prompt
from execution.generate_image import generate_image_from_prompt
from execution.series_processor import parse_script_to_scenes
from execution.load_assets import get_assets_by_category
from execution.kling_client import KlingClient
from execution.sora_client import SoraClient
from execution.s3_uploader import upload_file_obj


def mini_series_ui(user_asset_path, outfits_data, vibes_data, assets, knowledge_base, auth_mgr, get_user_out_dir_func, campaign_mgr=None):
    # --- STEP 4: PRODUCTION ---
    st.markdown("---")
    st.markdown("---")
    # Queue Button
    if st.button("🚀 Add Episode to Campaign Queue", type="primary", help="Add all shots to the Campaign Manager for background processing."):
        if not st.session_state.series_storyboard:
            st.error("No storyboard defined.")
        elif not campaign_mgr:
            st.error("Campaign Manager not available.")
        else:
            sb = st.session_state.series_storyboard
            ep_title = sb.get('title', 'Untitled_Ep').replace(" ", "_")
            series_name = st.session_state.get('series_title', 'My_Series').replace(" ", "_") # Fallback? 
            # Actually series_title is local var in Step 1. We might need to fetch it or default.
            # Usually series_title is not in session state explicitly unless we put it there.
            # We'll rely on the folder structure or just use ep_title.
            
            base_out = get_user_out_dir_func("Series")
            # We'll let campaign runner handle subfolders or specify full path
            # Campaign runner treats 'output_folder' as the dest.
            # We want: output/Series/{SeriesName}/{EpTitle}/
            
            # Try to grab title from Form if possible, otherwise generic
            # st.session_state doesn't have series_title easily accessible if inside a form locally.
            # But the storyboard has it? No, storyboard has title.
            
            full_out_dir = os.path.join(base_out, series_name, ep_title)
            
            count = 0
            
            for scene_idx, scene in enumerate(sb.get('scenes', [])):
                s_id = scene.get('id', scene_idx+1)
                
                for shot_idx, shot in enumerate(scene.get('shots', [])):
                    sh_id = shot_idx + 1
                    
                    # 1. Resolve Assets
                    assets_payload = []
                    
                    # Location
                    start_env = scene.get('location', '') # Or get from shot?
                    # The shot might have specific env logic (B-Roll vs Main)
                    # We can reuse the logic: Main vs B-Roll
                    # But for now, let's trust the 'location' key or user selection if we had it.
                    # Simplified: Use the scene location name as key
                    
                    # Resolve Environment Path
                    # In main UI we allow overriding per shot? 
                    # The previous code logic:
                    # target_env = shot_data['environment']
                    # We need to resolve 'target_env'.
                    # Let's assume the scene location text matches a key in vibes/locations?
                    # Or use the lookup.
                    
                    env_name = scene.get('location', 'Unknown')
                    # Try to find path
                    env_path = vibes_data.get(env_name) or assets.get('locations', {}).get(env_name)
                    if isinstance(env_path, dict): env_path = env_path.get('default_img')
                    
                    if env_path:
                        assets_payload.append({"path": env_path, "label": f"Location: {env_name}"})
                        
                    # Characters
                    shot_chars = shot.get('characters', [])
                    for c_name in shot_chars:
                        # Lookup
                        c_key = c_name.strip() #.split(' ')[0] -- FIXED: Use full key for lookup
                        c_path = st.session_state.cast_lookup_map.get(c_key)
                        
                        # Fallback lookup
                        if not c_path:
                             # Try full name in map
                             for k, v in st.session_state.cast_lookup_map.items():
                                 if k in c_name: 
                                     c_path = v
                                     break
                        
                        if c_path:
                            assets_payload.append({"path": c_path, "label": f"Cast: {c_name}"})
                            
                            # Outfit (Check per-shot override first, then fallback to Series Bible)
                            shot_w = shot.get('wardrobe', {})
                            outfit_name = shot_w.get(c_key) or shot_w.get(c_name)
                            if not outfit_name:
                                w_snapshot = st.session_state.get('cast_wardrobe_map_snapshot', {})
                                outfit_name = w_snapshot.get(c_key) or w_snapshot.get(c_name, "Default Outfit")
                            
                            if outfit_name and outfit_name != "Default Outfit" and outfit_name != "Default":
                                o_path = outfits_data.get(outfit_name)
                                if isinstance(o_path, dict): o_path = o_path.get('default_img')
                                if o_path:
                                    assets_payload.append({"path": o_path, "label": f"Outfit for {c_name}"})

                    # Prompt Construction — Structured Camera Direction + Scene Still
                    p_text = shot.get('visual_prompt', '')
                    t_day = shot.get('time_of_day', 'Day')
                    
                    # Build camera direction block from shot metadata
                    cam_parts = []
                    if shot.get('shot_size'): cam_parts.append(f"Shot: {shot['shot_size']}")
                    if shot.get('camera_angle'): cam_parts.append(f"Angle: {shot['camera_angle']}")
                    if shot.get('composition'): cam_parts.append(f"Composition: {shot['composition']}")
                    if shot.get('depth_of_field'): cam_parts.append(f"DoF: {shot['depth_of_field']}")
                    if shot.get('lighting_type'): cam_parts.append(f"Lighting: {shot['lighting_type']}")
                    cam_direction = ". ".join(cam_parts) + "." if cam_parts else ""
                    
                    final_prompt = f"Photorealistic film still. Time of Day: {t_day}. {cam_direction}\n{p_text}"
                    
                    # Add Job
                    job_name = f"Ep{ep_title}_S{s_id}_Sh{sh_id}"
                    
                    campaign_mgr.add_job(
                        name=job_name,
                        description=f"Scene {s_id} Shot {sh_id}",
                        prompt_data={
                            "positive_prompt": final_prompt,
                            "negative_prompt": "blurry, low quality, distortion, ugly face",
                            "num_images": 1,
                            "guidance_scale": 7.5,
                            "model_type": "nano",
                            "aspect_ratio": st.session_state.get('series_ar', '16:9'),
                            "image_size": st.session_state.get('series_res', '1K'),
                            "assets": assets_payload
                        },
                        settings={"batch_count": 1},
                        output_folder=full_out_dir,
                        # Pass paths technically redundant if in 'assets' payload but good for reference
                        char_path=None, 
                        outfit_path=None, 
                        vibe_path=None
                    )
                    count += 1
            
            st.success(f"✅ Added {count} Shots to Campaign Queue!")
            st.caption("Go to 'Campaign Queue' tab to run them.")
    """
    Renders the Mini Series Studio UI.
    """
    st.markdown("### 🎬 Mini Series Studio")
    st.info("Create episodic content with consistent cast, wardrobe, and environments.")

    # --- Session State ---
    if "series_storyboard" not in st.session_state:
        st.session_state.series_storyboard = None

    # --- STEP 1: SERIES BIBLE ---
    with st.expander("📖 Step 1: Series Bible & Production Blueprint", expanded=True):
        col_sb1, col_sb2 = st.columns([1.1, 0.9])
        
        with col_sb1:
            series_title = st.text_input("🎬 Series Title", placeholder="The Influencer Life")
            series_logline = st.text_area("📝 Series Logline & High-Concept Premise", placeholder="A high-stakes drama following rival creators maneuvering through Miami's elite scene...", height=80)
            
            st.markdown("#### 🆔 Identity, Tone & Format")
            c_gen, c_tone = st.columns(2)
            with c_gen:
                s_genre = st.selectbox("Genre", [
                    "General / Drama", 
                    "A24 Psychological Drama", 
                    "Cyberpunk / Sci-Fi", 
                    "Neo-Noir Crime / Thriller", 
                    "High-Fashion / Luxury", 
                    "Rom-Com / Romance", 
                    "Horror / Supernatural", 
                    "Slice of Life / Realism"
                ])
            with c_tone:
                s_tone = st.selectbox("Tone & Mood", [
                    "A24 Moody & Atmospheric", 
                    "Hyper-Luxury Gloss", 
                    "Gritty Cinematic", 
                    "Dark & Suspenseful", 
                    "Warm Golden Nostalgia", 
                    "Documentary / Raw", 
                    "Comedic & Energetic"
                ])
            
            c_wb, c_len = st.columns(2)
            with c_wb:
                s_wb_lighting = st.selectbox("Lighting & White Balance Mood", [
                    "5600K Natural Daylight (Clean & Crisp)",
                    "3200K Tungsten Warmth (Golden Hour / Interior)",
                    "4000K Neutral Studio Flash",
                    "Neon Cyberpunk (Pink & Cyan Spill)",
                    "8500K Cold Blue Haze (Suspense & Rain)",
                    "High-Contrast Chiaroscuro (Deep Shadows)"
                ])
            with c_len:
                s_len = st.selectbox("Target Episode Format", [
                    "30 Seconds (Commercial / Short — 8-10 Shots)",
                    "15 Seconds (TikTok / Reel — 4-6 Shots)",
                    "45 Seconds (Dramatic Short — 12-14 Shots)",
                    "60 Seconds (Mini Episode — 16-18 Shots)"
                ])

            # CINEMATOGRAPHY SETTINGS (Selected FIRST so it influences Environment Generation!)
            st.markdown("#### 🎥 Cinematography & Lens Package")
            c_cam, c_lens = st.columns(2)
            with c_cam:
                 cam_opts = [
                     "Auto", 
                     "Arri Alexa 65 (Large Format)", "Arri Alexa Mini LF", "Sony Venice 2 (8K)", 
                     "RED V-Raptor [VV]", "Panavision Millennium DXL2", 
                     "IMAX 15/70mm Film", "Kodak Vision3 35mm Film", "16mm Bolex", "Super 8mm",
                     "iPhone 15 Pro Max (ProRes)", "VHS Camcorder (90s)", "CCTV Security Cam"
                 ]
                 s_camera = st.selectbox("Camera Body", cam_opts, key="s_camera")
                 
                 stock_opts = [
                     "Auto", 
                     "Kodak Portra 400", "Kodak Portra 800", "Fujifilm Velvia 100", 
                     "Cinestill 800T (Halation)", "Kodak Tri-X 400 (B&W)", "Ilford HP5 (Grainy B&W)",
                     "Technicolor (3-Strip)", "Bleach Bypass (Gritty)"
                 ]
                 s_film_stock = st.selectbox("Film Stock / LUT", stock_opts, key="s_film_stock")

            with c_lens:
                 lens_opts = [
                     "Auto", 
                     "Arri Signature Prime", "Cooke S4/i Prime", "Panavision Primo 70", "Canon K-35 Vintage",
                     "Atlas Orion Anamorphic", "Laowa Probe Lens",
                     "14mm Ultra Wide", "24mm Wide", "35mm Standard", "50mm Standard", 
                     "85mm Portrait", "105mm Macro", "200mm Telephoto", "600mm Sniper"
                 ]
                 s_lens = st.selectbox("Lens Glass", lens_opts, key="s_lens")

                 grade_opts = ["Auto", "Teal & Orange (Blockbuster)", "Vintage Warmth", "Cool Blue", "Noir B&W", "Matrix Green", "Euphoria Purple"]
                 s_filter_look = st.selectbox("Color Grade", grade_opts, key="s_filter_look")
            
            c_light, c_style = st.columns(2)
            with c_light:
                 light_opts = ["Auto", "Golden Hour", "Studio Softbox", "Rembrandt", "Neon Cyberpunk", "Natural Diffused", "Hard Flash", "Silhouette", "God Rays"]
                 s_lighting = st.selectbox("Lighting", light_opts, key="s_lighting")
            with c_style:
                 style_opts = [
                     "Auto", 
                     "Wes Anderson (Symmetrical/Pastel)", "Christopher Nolan (IMAX/Cold)", "Denis Villeneuve (Brutalist)",
                     "Wong Kar-wai (Step Printing)", "Quentin Tarantino (Low Angle)", 
                     "Euphoria (Glitter/A24)", "Cyberpunk (Neon)", "1950s Technicolor", "1990s Sitcom"
                 ]
                 s_movie_style = st.selectbox("Style Reference", style_opts, key="s_movie_style")
            
            c_ar_col, c_res_col = st.columns(2)
            with c_ar_col:
                 s_aspect_ratio = st.selectbox("Aspect Ratio", ["16:9", "9:16", "4:5", "1:1"], index=0, key="series_ar")
            with c_res_col:
                 s_resolution = st.selectbox("Resolution", ["1K", "2K", "4K"], index=0, key="series_res", help="Higher = sharper but slower + more expensive")

        with col_sb2:
            st.markdown("#### 🎭 Cast Engine & Character Chemistry")
            
            char_opts = get_assets_by_category("characters", user_asset_path)
            rel_opts = get_assets_by_category("relations", user_asset_path)
            all_cast_opts = {**char_opts, **rel_opts}
            
            cast_selection = st.multiselect("Select Cast Members for Episode", list(all_cast_opts.keys()))
            
            cast_wardrobe_map = {}
            cast_role_map = {}
            cast_acting_profile_map = {}
            
            if cast_selection:
                st.caption("Configure Roles, Wardrobe & Micro-Expression Acting Profiles:")
                for member in cast_selection:
                    st.divider()
                    c_img, c_info = st.columns([1, 3.5])
                    
                    c_data = all_cast_opts.get(member)
                    c_path = c_data.get('default_img') if isinstance(c_data, dict) else c_data
                    member_basename = member.split('/')[-1].replace('.png','').replace('.jpg','').strip()

                    with c_img:
                        if c_path:
                            try:
                                st.image(c_path, use_container_width=True)
                            except Exception as e:
                                st.warning("IMG Error")
                        else:
                            st.warning("No Image")

                    with c_info:
                        st.markdown(f"**{member_basename}**")
                        c1, c2 = st.columns(2)
                        with c1:
                            role = st.selectbox(f"Role", ["Protagonist / Lead", "Co-Lead / Love Interest", "Antagonist / Rival", "Confidant / Best Friend", "Supporting Lead"], key=f"role_{member}")
                            cast_role_map[member] = role

                        with c2:
                            outfit_opts = list(outfits_data.keys())
                            sel_fit = st.selectbox(f"Wardrobe", ["Default Outfit"] + outfit_opts, key=f"series_fit_{member}")
                            cast_wardrobe_map[member] = sel_fit
                            if sel_fit != "Default Outfit":
                                o_path = outfits_data.get(sel_fit)
                                if isinstance(o_path, dict): o_path = o_path.get('default_img')
                                if o_path and os.path.exists(o_path):
                                    st.image(o_path, width=70)
                                    
                        act_profile = st.text_input(
                            f"Micro-Expression Profile",
                            value="Eyes locked, jaw tightens, subtle breathing pattern",
                            key=f"act_{member}",
                            help="Higgsfield Seedance V2 muscle-movement performance description."
                        )
                        cast_acting_profile_map[member_basename] = act_profile

    # --- STEP 2: HIGGSFIELD ENVIRONMENT MASTER GENERATION ---
    st.markdown("---")
    with st.expander("🌄 Step 2: Higgsfield AI Environment Master Studio", expanded=True):
        st.markdown("Generate 8K Environment Master Stills with **Cascading Knowledge Continuity** & multi-model comparison before writing the script.")
        
        all_locs = list(vibes_data.keys()) + list(assets.get('locations', {}).keys())
        
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            st.write("**Primary Location** (Main Action Set)")
            series_env = st.selectbox("Choose Preset Location (Optional)", ["None"] + all_locs, key="series_env_sel")
            custom_env_title = st.text_input("Custom Location / Set Name", placeholder="e.g. Luxury Beverly Hills Penthouse", key="custom_env_title")
            
            target_env_name = custom_env_title if custom_env_title else (series_env if series_env != "None" else "Main Production Environment")

            if series_env and series_env != "None":
                path = vibes_data.get(series_env) or assets.get('locations', {}).get(series_env)
                if path:
                    if isinstance(path, dict): path = path.get('default_img')
                    st.image(path, caption="Preset Location Reference", width=220)

        with e_col2:
            st.write("**Secondary Location** (B-Roll / Cutaway Set)")
            sec_env = st.selectbox("Choose B-Roll Set", ["None"] + all_locs, key="sec_env")
            
            if sec_env and sec_env != "None":
                path_sec = vibes_data.get(sec_env) or assets.get('locations', {}).get(sec_env)
                if path_sec:
                    if isinstance(path_sec, dict): path_sec = path_sec.get('default_img')
                    st.image(path_sec, caption="Secondary B-Roll Environment", width=220)

        st.markdown("---")
        st.markdown("##### ⚙️ Environment Still Generator & Model Options")
        
        m_col1, m_col2, m_col3 = st.columns([2, 1, 2])
        with m_col1:
            env_model_choice = st.selectbox(
                "Image Model Engine",
                [
                    "Google Nano Banana 2 (Recommended / Multi-Ref)",
                    "SeaDream 5.0 (ByteDance / Ultra Photorealistic)",
                    "Flux 1.1 Pro (Black Forest Labs)",
                    "Ideogram 2.0 (High Contrast)",
                    "DALL-E 3 / GPT Image 2.0"
                ],
                key="env_model_choice"
            )
        with m_col2:
            env_still_count = st.slider("Stills to Generate", 1, 4, 3, key="env_still_count", help="Cascading stills: each generated still references the previous for 100% architectural continuity!")
        with m_col3:
            env_custom_notes = st.text_input(
                "Environmental Textures & Details",
                placeholder="Wet asphalt, rain reflections, volumetric fog 30%, neon sign flickering",
                key="env_notes"
            )

        if st.button("✨ Generate Cascading 8K Environment Stills", type="primary", key="gen_env_btn", use_container_width=True):
            with st.spinner(f"⚡ AI Generating {env_still_count} Cascading Environment Stills for '{target_env_name}'..."):
                from execution.series_processor import generate_environment_master_prompt
                
                angles = [
                    "Master Establishing Wide View (107° FOV)",
                    "Reverse Angle Depth View (84° FOV)",
                    "Medium Focal Action Space (63° FOV)",
                    "Macro Architectural Texture Detail (29° FOV)"
                ]
                
                generated_stills = []
                logs_all = []
                
                for idx in range(env_still_count):
                    angle_label = angles[idx if idx < len(angles) else 0]
                    st.toast(f"⚡ Rendering Still {idx+1}/{env_still_count}: {angle_label}")
                    
                    env_data = generate_environment_master_prompt(
                        location_name=f"{target_env_name}. {env_custom_notes}" if env_custom_notes else target_env_name,
                        genre=s_genre,
                        tone=f"{s_tone}. Lighting: {s_lighting}. Camera: {s_camera}, {s_lens}. LUT: {s_film_stock}, Grade: {s_filter_look}, Style: {s_movie_style}",
                        shot_angle_type=angle_label
                    )
                    env_p = env_data.get("environment_prompt")
                    
                    # Cascading Knowledge Continuity: Pass prior generated still as reference
                    payload_assets = []
                    if generated_stills and os.path.exists(generated_stills[-1]):
                        payload_assets.append({
                            "path": generated_stills[-1],
                            "label": f"Prior Environment Reference Still #{len(generated_stills)} (MATCH ARCHITECTURE, COLORS & LIGHTING)"
                        })
                    
                    p_data = {
                        "positive_prompt": env_p,
                        "model_type": env_model_choice,
                        "assets": payload_assets,
                        "aspect_ratio": st.session_state.get('series_ar', '16:9'),
                        "image_size": "2K"
                    }
                    
                    res_env = generate_image_from_prompt(p_data, get_user_out_dir_func("Series/Environments"))
                    if res_env.get("status") == "success":
                        generated_stills.append(res_env["image_path"])
                    else:
                        st.error(f"Still #{idx+1} Generation Failed: {res_env.get('logs')}")
                        break
                
                if generated_stills:
                    st.session_state["env_stills_list"] = generated_stills
                    st.session_state["primary_env_img"] = generated_stills[0]
                    st.toast(f"✅ Generated {len(generated_stills)} Cascading 8K Environment Stills!")
                    st.rerun()

        # Display Cascading Gallery & Active Anchor Selector
        if "env_stills_list" in st.session_state and st.session_state["env_stills_list"]:
            st.markdown("##### 🖼️ Cascading Environment Gallery & Active Master Anchor")
            st.caption("Each still builds upon the previous for seamless set continuity. Choose which still serves as the Primary Location Anchor for your episode:")
            
            stills = [s for s in st.session_state["env_stills_list"] if os.path.exists(s)]
            if stills:
                cols = st.columns(len(stills))
                for i, s_path in enumerate(stills):
                    with cols[i]:
                        st.image(s_path, caption=f"Still #{i+1} (Angle {i+1})", use_container_width=True)
                        is_active = (st.session_state.get("primary_env_img") == s_path)
                        if st.button(f"{'🎯 Active Master' if is_active else 'Select Still #' + str(i+1)}", key=f"sel_env_still_{i}", type="primary" if is_active else "secondary", use_container_width=True):
                            st.session_state["primary_env_img"] = s_path
                            st.toast(f"🎯 Set Still #{i+1} as Active Master Environment Anchor!")
                            st.rerun()
                        with open(s_path, "rb") as f_img:
                            st.download_button(f"⬇️ Download #{i+1}", f_img, file_name=os.path.basename(s_path), mime="image/png", key=f"dl_env_still_{i}")
        elif "primary_env_img" in st.session_state and os.path.exists(st.session_state["primary_env_img"]):
            st.image(st.session_state["primary_env_img"], caption=f"✨ Generated 8K Higgsfield Environment Master Still ({target_env_name})", use_container_width=True)

    # --- STEP 3: WRITER'S ROOM ---
    st.markdown("---")
    st.markdown("### ✍️ Step 3: Writer's Room & Director Vision AI")
    
    c_script, c_action = st.columns([3, 1])
    with c_script:
        with st.form(key="director_form"):
            series_script = st.text_area("Episode Synopsis & Dialogue Intent", height=200, placeholder="Synopsis: She finds out he's been lying, but he doesn't know she knows yet.\n\nIntent:\nALICE: Cold, distant.\nBOB: Trying too hard to be casual.")
            s_transition_style = st.selectbox("Transition Pacing", ["Standard", "Fast / TikTok", "Slow / Cinematic", "Match Cut"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_director = st.form_submit_button("✨ Director Vision AI", type="primary", use_container_width=True)

    if submit_director:
            if not series_script:
                st.error("Please enter a synopsis.")
            elif not cast_selection:
                st.error("Please select a cast.")
            else:
                with st.spinner("AI Director is breaking down the script..."):
                    # 1. Clean Cast Names & Map
                    char_opts = get_assets_by_category("characters", user_asset_path)
                    rel_opts = get_assets_by_category("relations", user_asset_path)
                    all_cast_opts = {**char_opts, **rel_opts}
                    
                    clean_cast_map = {} 
                    clean_names_list = []
                    
                    for full_key in cast_selection:
                        c_data = all_cast_opts.get(full_key)
                        real_path = None
                        if isinstance(c_data, dict):
                            real_path = c_data.get('default_img')
                        else:
                            real_path = c_data
                            
                        base = full_key.split('/')[-1].replace('.png','').replace('.jpg','').strip()
                        
                        if real_path:
                            clean_cast_map[base] = real_path
                            clean_names_list.append(base)
                            
                            # Add first word key
                            first_word = base.replace('_', ' ').split(' ')[0]
                            if first_word and first_word != base:
                                clean_cast_map[first_word] = real_path
                    
                    st.session_state.cast_lookup_map = clean_cast_map

                    # Clean Roles Map
                    clean_roles_map = {}
                    if cast_role_map:
                        for full_key, role in cast_role_map.items():
                            base = full_key.split('/')[-1].replace('.png','').replace('.jpg','').strip()
                            c_name = base #.split(' ')[0] -- FIXED
                            clean_roles_map[c_name] = role

                    # Clean Wardrobe Map
                    clean_wardrobe_map = {}
                    director_refs = [] 
                    
                    if cast_wardrobe_map:
                        for full_key, outfit in cast_wardrobe_map.items():
                            base = full_key.split('/')[-1].replace('.png','').replace('.jpg','').strip()
                            clean_wardrobe_map[base] = outfit 
                            # Add first word as key for robust LLM matching (e.g. "Shay_v1" -> "Shay")
                            first_word = base.replace('_', ' ').split(' ')[0]
                            if first_word and first_word != base:
                                clean_wardrobe_map[first_word] = outfit 
                            
                            if outfit != "Default":
                                o_path = outfits_data.get(outfit)
                                if isinstance(o_path, dict): o_path = o_path.get('default_img')
                                if o_path:
                                    director_refs.append({
                                        "path": o_path, 
                                        "label": f"{base}'s Wardrobe: {outfit}"
                                    })
                        
                        st.session_state.cast_wardrobe_map_snapshot = clean_wardrobe_map
                    
                    for c_name, c_path in clean_cast_map.items():
                         director_refs.append({
                             "path": c_path,
                             "label": f"Cast Member: {c_name}"
                         })

                    # V2 API Call
                    sb_data = parse_script_to_scenes(
                        script_text=series_script, 
                        cast_list=clean_names_list, 
                        environment_name=series_env,
                        genre=s_genre,
                        tone=s_tone,
                        roles_map=clean_roles_map,
                        wardrobe_map=clean_wardrobe_map,
                        ref_images=director_refs,
                        secondary_environment=sec_env,
                        camera=s_camera,
                        lens=s_lens,
                        lighting=s_lighting,
                        film_stock=s_film_stock,
                        filter_look=s_filter_look,
                        movie_style=s_movie_style,
                        transition_style=s_transition_style
                    )
                    
                    if "error" in sb_data:
                        st.error(sb_data['error'])
                    else:
                        st.session_state.series_storyboard = sb_data
                        # clear keys
                        keys_to_clear = [k for k in st.session_state.keys() if k.startswith(("p_s", "img_s", "m_s", "btn_s"))]
                        for k in keys_to_clear:
                            del st.session_state[k]
                        st.success("Director Vision Generated!")

    # --- STEP 3: DIRECTOR MODE ---
    if st.session_state.series_storyboard:
        st.markdown("---")
        st.markdown("### 🎬 Director Mode & Storyboard")
        
        sb = st.session_state.series_storyboard
        st.caption(f"Episode: {sb.get('title', 'Untitled')}")
        
        generated_shots_data = [] 
        
        # Ensure lookup map
        if "cast_lookup_map" not in st.session_state:
             char_opts = get_assets_by_category("characters", user_asset_path)
             rel_opts = get_assets_by_category("relations", user_asset_path)
             all_cast_opts = {**char_opts, **rel_opts}
             
             clean_cast_map = {}
             if cast_selection:
                 for full_key in cast_selection:
                    c_data = all_cast_opts.get(full_key)
                    real_path = c_data.get('default_img') if isinstance(c_data, dict) else c_data
                    
                    base = full_key.split('/')[-1].replace('.png','').replace('.jpg','')
                    clean_name = base #.split(' ')[0] -- FIXED
                    if real_path: clean_cast_map[clean_name] = real_path
                 st.session_state.cast_lookup_map = clean_cast_map
        
        cast_map = st.session_state.cast_lookup_map

        for scene_idx, scene in enumerate(sb.get('scenes', [])):
            with st.container():
                st.markdown(f"#### Scene {scene.get('id')}: {scene.get('location')}")
                
                shots = scene.get('shots', [])
                for shot_idx, shot in enumerate(shots):
                    key_base = f"s{scene_idx}_sh{shot_idx}"
                    
                    # Resolve Character
                    char_list = shot.get('characters', [])
                    char_ref_name = char_list[0] if char_list else None
                    char_full_key = None
                    
                    if char_ref_name:
                        char_full_key = cast_map.get(char_ref_name)
                        if not char_full_key:
                            for c_name, c_key in cast_map.items():
                                if c_name in char_ref_name or char_ref_name in c_name:
                                    char_full_key = c_key
                                    break
                    
                    if not char_full_key and cast_selection and not shot.get('is_broll', False):
                         char_full_key = cast_selection[0]

                    col_txt, col_img = st.columns([1.5, 1])
                    
                    # Fix NameError by initializing motion_type
                    motion_type = "Still" 
                    mocap_file = None

                    with col_txt:
                        st.markdown(f"**Shot {shot_idx+1}**")
                        
                        meta_cols = st.columns(4)
                        meta_cols[0].caption(f"📏 {shot.get('shot_size', 'Auto')}")
                        meta_cols[1].caption(f"🎥 {shot.get('camera_angle', 'Auto')}")
                        meta_cols[2].caption(f"💡 {shot.get('lighting_type', 'Auto')}")
                        meta_cols[3].caption(f"🎨 {shot.get('composition', 'Auto')}")
                        
                        all_cast_keys = list(st.session_state.cast_lookup_map.keys())
                        current_chars = shot.get('characters', [])
                        valid_defaults = []
                        for c in current_chars:
                            if c in all_cast_keys: valid_defaults.append(c)
                            elif c.replace('_', ' ').split(' ')[0] in all_cast_keys: 
                                valid_defaults.append(c.replace('_', ' ').split(' ')[0])
                                
                        selected_chars = st.multiselect(
                            "Cast in Shot", 
                            options=all_cast_keys,
                            default=valid_defaults,
                            key=f"cast_sel_{key_base}",
                            label_visibility="collapsed",
                            placeholder="Select Cast..."
                        )
                        shot['characters'] = selected_chars
                        
                        # Per-shot Wardrobe Selection (See, Select, & Reselect mapped outfits)
                        shot_wardrobe_map = {}
                        if selected_chars:
                            with st.expander("👕 Cast Wardrobe for Shot (Select / Change)", expanded=True):
                                for c_name in selected_chars:
                                    w_snapshot = st.session_state.get('cast_wardrobe_map_snapshot', {})
                                    orig_outfit = w_snapshot.get(c_name) or w_snapshot.get(c_name.replace('_', ' ').split(' ')[0], "Default Outfit")
                                    if orig_outfit == "Default":
                                        orig_outfit = "Default Outfit"
                                        
                                    outfit_options = ["Default Outfit"] + list(outfits_data.keys())
                                    def_fit_idx = 0
                                    if orig_outfit in outfit_options:
                                        def_fit_idx = outfit_options.index(orig_outfit)
                                        
                                    w_col1, w_col2 = st.columns([3, 1])
                                    with w_col1:
                                        sel_fit = st.selectbox(
                                            f"Outfit for {c_name}",
                                            outfit_options,
                                            index=def_fit_idx,
                                            key=f"shot_fit_{key_base}_{c_name}"
                                        )
                                        shot_wardrobe_map[c_name] = sel_fit
                                    with w_col2:
                                        if sel_fit and sel_fit != "Default Outfit" and sel_fit != "Default":
                                            o_path = outfits_data.get(sel_fit)
                                            if isinstance(o_path, dict): o_path = o_path.get('default_img')
                                            if o_path and os.path.exists(o_path):
                                                st.image(o_path, caption=sel_fit[:15], width=60)
                                        else:
                                            st.caption("Default Outfit")
                                            
                        shot['wardrobe'] = shot_wardrobe_map
                        
                        time_opts = ["Morning", "Noon", "Afternoon", "Golden Hour", "Blue Hour", "Night", "Midnight"]
                        ai_time = shot.get('time_of_day', 'Day')
                        ai_time_norm = ai_time.title() if ai_time else "Day"
                        def_idx = 0
                        for idx, opt in enumerate(time_opts):
                            if opt.lower() in ai_time_norm.lower():
                                def_idx = idx
                                break
                                
                        selected_time = st.selectbox(
                            "Time of Day", 
                            time_opts, 
                            index=def_idx,
                            key=f"time_{key_base}",
                            label_visibility="collapsed"
                        )
                        shot['time_of_day'] = selected_time

                        trans_opts = ["None"] + knowledge_base.get("transitions", [])
                        sel_trans = st.selectbox("Transition", trans_opts, key=f"trans_{key_base}", label_visibility="collapsed")
                        shot['transition'] = sel_trans
                        
                        shot_prompt = st.text_area("Visual Prompt", value=shot.get('visual_prompt'), height=250, key=f"p_{key_base}", label_visibility="collapsed")
                        st.caption(f"Length: {len(shot_prompt) if shot_prompt else 0} chars (Target: 800+)")
                        
                        c_gen, c_type = st.columns([1, 1.5])
                        with c_gen:
                            if st.button(f"Generate Shot {shot_idx+1}", key=f"btn_{key_base}"):
                                user = st.session_state.current_user.get("username")
                                if not auth_mgr.deduct_credits(user, 1):
                                    st.error("❌ No Credits!")
                                else:
                                    with st.spinner("Rolling camera..."):
                                        final_assets_payload = []
                                        
                                        # Resolve Cast Assets (Robust)
                                        target_chars = shot.get('characters', [])
                                        is_broll = shot.get('is_broll', False)
                                        if not target_chars and cast_selection and not is_broll:
                                             pass 

                                        for raw_name in target_chars:
                                            c_path = st.session_state.cast_lookup_map.get(raw_name)
                                            if not c_path:
                                                 first_w = raw_name.replace('_', ' ').split(' ')[0]
                                                 c_path = st.session_state.cast_lookup_map.get(first_w)
                                            
                                            if c_path:
                                                final_assets_payload.append({"path": c_path, "label": f"Cast: {raw_name}"})
                                                # Outfit from shot level override, fallback to snapshot
                                                o_key = shot_wardrobe_map.get(raw_name)
                                                if not o_key:
                                                    first_w = raw_name.replace('_', ' ').split(' ')[0]
                                                    o_key = shot_wardrobe_map.get(first_w)
                                                if not o_key:
                                                    w_snapshot = st.session_state.get('cast_wardrobe_map_snapshot', {})
                                                    o_key = w_snapshot.get(raw_name) or w_snapshot.get(raw_name.replace('_', ' ').split(' ')[0], "Default Outfit")
                                                
                                                if o_key and o_key != "Default Outfit" and o_key != "Default":
                                                    o_path = outfits_data.get(o_key)
                                                    if isinstance(o_path, dict): o_path = o_path.get('default_img')
                                                    if o_path: 
                                                        final_assets_payload.append({"path": o_path, "label": f"Outfit for {raw_name}"})

                                        # Location (Prefer Generated Higgsfield AI Environment Master Still)
                                        target_env = sec_env if is_broll and sec_env != "None" else series_env
                                        if "primary_env_img" in st.session_state and os.path.exists(st.session_state["primary_env_img"]) and not is_broll:
                                            final_assets_payload.append({"path": st.session_state["primary_env_img"], "label": f"Location Master (HIGGSFIELD SEEDANCE V2 ENVIRONMENT): {target_env}"})
                                        else:
                                            env_path = vibes_data.get(target_env) or assets.get('locations', {}).get(target_env)
                                            if isinstance(env_path, dict): env_path = env_path.get('default_img')
                                            if env_path: final_assets_payload.append({"path": env_path, "label": f"Location: {target_env}"})
                                        
                                        # Prompt — Structured Camera Direction + Scene Still
                                        time_setting = shot.get('time_of_day', 'Day')
                                        
                                        # Build camera direction block from shot metadata
                                        cam_parts = []
                                        if shot.get('shot_size'): cam_parts.append(f"Shot: {shot['shot_size']}")
                                        if shot.get('camera_angle'): cam_parts.append(f"Angle: {shot['camera_angle']}")
                                        if shot.get('composition'): cam_parts.append(f"Composition: {shot['composition']}")
                                        if shot.get('depth_of_field'): cam_parts.append(f"DoF: {shot['depth_of_field']}")
                                        if shot.get('lighting_type'): cam_parts.append(f"Lighting: {shot['lighting_type']}")
                                        cam_direction = ". ".join(cam_parts) + "." if cam_parts else ""
                                        
                                        final_shot_prompt = f"Photorealistic film still. Time of Day: {time_setting}. {cam_direction}\n{shot_prompt}"
                                        
                                        # Cascading context — attach prior shot for scene consistency
                                        prior_key = f"img_s{scene_idx}_sh{shot_idx - 1}" if shot_idx > 0 else None
                                        prior_path = st.session_state.get(prior_key) if prior_key else None
                                        
                                        if prior_path and os.path.exists(prior_path):
                                            final_shot_prompt += (
                                                "\n\nSCENE CONTINUITY: The attached 'Prior Shot' image shows the PREVIOUS moment "
                                                "from this same scene. Match the EXACT environment, lighting, color palette, "
                                                "set design, and character wardrobe from that image."
                                            )
                                            final_assets_payload.append({
                                                "path": prior_path,
                                                "label": "Prior Shot (SCENE CONTINUITY - MATCH ENVIRONMENT & LIGHTING)"
                                            })
                                        
                                        p_data = {
                                             "positive_prompt": final_shot_prompt,
                                             "model_type": "nano", 
                                             "assets": final_assets_payload,
                                             "aspect_ratio": st.session_state.get('series_ar', '16:9'),
                                             "image_size": st.session_state.get('series_res', '1K')
                                        }
                                        
                                        res = generate_image_from_prompt(p_data, get_user_out_dir_func("Series"))
                                        if res["status"] == "success":
                                            st.session_state[f"img_{key_base}"] = res["image_path"]
                                            st.success("Shot Captured!")
                                        else:
                                            st.error(f"Error: {res.get('logs')}")
                        
                        with c_type:
                            motion_type = st.radio("Media", ["Still", "Kling Video", "Sora 2 Video", "Mocap"], key=f"m_{key_base}", horizontal=True, label_visibility="collapsed")
                            if motion_type == "Mocap":
                                mocap_file = st.file_uploader("Ref", type=['mp4'], key=f"up_{key_base}", label_visibility="collapsed")

                    with col_img:
                        if f"img_{key_base}" in st.session_state:
                            img_p = st.session_state[f"img_{key_base}"]
                            st.image(img_p, caption=f"Shot {shot_idx+1}", use_container_width=True)
                            if os.path.exists(img_p):
                                with open(img_p, "rb") as file:
                                    st.download_button("⬇️ Download Still", file, file_name=os.path.basename(img_p), mime="image/png", key=f"dl_{key_base}")
                                    
                            # HIGGSFIELD MOTION RIG & SEEDANCE ANIMATION
                            with st.expander(f"🎬 Higgsfield Motion Rig & Seedance Video", expanded=False):
                                st.caption("Animate this shot using Seedance 2.0 Reference-to-Video (Atlas Cloud) with your characters, environment master, video motion, and voiceovers.")
                                
                                v_engine = st.selectbox(
                                    "Video Engine", 
                                    [
                                        "Seedance 2.0 Mini (Reference-to-Video)",
                                        "Seedance 2.0 (Image-to-Video)",
                                        "Wan 2.7 (Image-to-Video)",
                                        "Kling 1.6 Video"
                                    ],
                                    key=f"v_eng_{key_base}"
                                )
                                v_res = st.selectbox("Resolution", ["720P (Half Cost / Fast)", "1080P"], index=0, key=f"v_res_{key_base}")
                                v_dur = st.slider("Duration (Sec)", 2, 10, 5, key=f"v_dur_{key_base}")
                                
                                all_cast_keys = list(st.session_state.cast_lookup_map.keys())
                                sel_anim_cast = st.multiselect(
                                    "Character References (Likeness Lock)",
                                    options=all_cast_keys,
                                    default=[c for c in shot.get('characters', []) if c in all_cast_keys],
                                    key=f"v_cast_{key_base}",
                                    help="Select cast members to pass their CreateFlow account reference images to Seedance / Wan for 100% likeness lock."
                                )
                                
                                c_vref_col, c_aref_col = st.columns(2)
                                with c_vref_col:
                                    up_vref = st.file_uploader("Reference Motion / Video (MP4)", type=["mp4", "mov"], key=f"v_vref_{key_base}")
                                with c_aref_col:
                                    up_aref = st.file_uploader("Reference Voiceover / Audio (MP3/WAV)", type=["mp3", "wav", "m4a"], key=f"v_aref_{key_base}")

                                motion_prompt_input = st.text_area(
                                    "Motion Action Prompt",
                                    value=shot_prompt,
                                    height=100,
                                    key=f"v_p_{key_base}"
                                )

                                if st.button(f"🎥 Animate Shot {shot_idx+1} with Seedance", type="primary", key=f"v_btn_{key_base}", use_container_width=True):
                                    user = st.session_state.current_user.get("username") if "current_user" in st.session_state and st.session_state.current_user else "guest"
                                    if not auth_mgr.deduct_credits(user, 3):
                                        st.error("❌ Not enough credits! Video generation requires 3 credits.")
                                    else:
                                        with st.spinner("⚡ Animating shot with Seedance 2.0 / Wan 2.7 on Atlas Cloud..."):
                                            # Assemble Multi-Reference Array (Up to 9 images)
                                            ref_images = []
                                            
                                            # 1. Environment Master Still
                                            if "primary_env_img" in st.session_state and os.path.exists(st.session_state["primary_env_img"]):
                                                ref_images.append(st.session_state["primary_env_img"])
                                                
                                            # 2. Selected Cast Character References
                                            for c_ref_name in sel_anim_cast:
                                                c_path = st.session_state.cast_lookup_map.get(c_ref_name)
                                                if c_path and os.path.exists(c_path):
                                                    ref_images.append(c_path)
                                                    
                                            # 3. Wardrobe References
                                            w_snapshot = st.session_state.get('cast_wardrobe_map_snapshot', {})
                                            for c_ref_name in sel_anim_cast:
                                                o_key = w_snapshot.get(c_ref_name)
                                                if o_key and o_key != "Default Outfit" and o_key != "Default":
                                                    o_path = outfits_data.get(o_key)
                                                    if isinstance(o_path, dict): o_path = o_path.get('default_img')
                                                    if o_path and os.path.exists(o_path):
                                                        ref_images.append(o_path)

                                            # Save Uploaded Video Reference if provided
                                            temp_v_path = None
                                            if up_vref:
                                                temp_v_dir = get_user_out_dir_func("Series/TempUploads")
                                                temp_v_path = os.path.join(temp_v_dir, f"ref_v_{key_base}.mp4")
                                                with open(temp_v_path, "wb") as f_v:
                                                    f_v.write(up_vref.getbuffer())

                                            # Save Uploaded Audio / Voiceover Reference if provided
                                            temp_a_path = None
                                            if up_aref:
                                                temp_a_dir = get_user_out_dir_func("Series/TempUploads")
                                                temp_a_path = os.path.join(temp_a_dir, f"ref_a_{key_base}.mp3")
                                                with open(temp_a_path, "wb") as f_a:
                                                    f_a.write(up_aref.getbuffer())

                                            if "Seedance 2.0 Mini" in v_engine:
                                                target_model = "bytedance/seedance-2.0-mini/reference-to-video"
                                            elif "Seedance 2.0 (Image" in v_engine:
                                                target_model = "bytedance/seedance-2.0/image-to-video"
                                            elif "Wan" in v_engine:
                                                target_model = "alibaba/wan-2.7/image-to-video"
                                            else:
                                                target_model = "bytedance/seedance-2.0/image-to-video"
                                                
                                            from execution.generate_wan import generate_wan_video
                                            res_video = generate_wan_video(
                                                prompt=motion_prompt_input,
                                                image_path=img_p,
                                                resolution=v_res,
                                                duration=v_dur,
                                                ref_video_path=temp_v_path,
                                                ref_audio_path=temp_a_path,
                                                extra_images=ref_images if ref_images else None,
                                                model=target_model,
                                                output_folder=get_user_out_dir_func("Series/Videos")
                                            )
                                            
                                            if res_video.get("status") == "success":
                                                st.session_state[f"vid_{key_base}"] = res_video["video_path"]
                                                st.toast(f"✅ Shot {shot_idx+1} Animated Successfully with Seedance!")
                                                st.rerun()
                                            else:
                                                auth_mgr.add_credits(user, 3)
                                                st.error(f"Video Generation Failed: {res_video.get('error')}")
                                                with st.expander("View Logs"):
                                                    st.code("\n".join(res_video.get("logs", [])))

                            if f"vid_{key_base}" in st.session_state and os.path.exists(st.session_state[f"vid_{key_base}"]):
                                vid_p = st.session_state[f"vid_{key_base}"]
                                st.video(vid_p)
                                with open(vid_p, "rb") as v_file:
                                    st.download_button("⬇️ Download Motion Video", v_file, file_name=os.path.basename(vid_p), mime="video/mp4", key=f"dl_vid_{key_base}")
                        else:
                            st.info("Generate photo first to animate")
                    
                    st.divider()

                    generated_shots_data.append({
                        "scene_id": scene.get('id'),
                        "shot_id": shot_idx + 1,
                        "prompt": shot_prompt,
                        "type": motion_type,
                        "mocap": mocap_file,
                        "characters": shot.get('characters'),
                        "environment": series_env,
                        "transition": shot.get('transition'),
                        "generated_still": st.session_state.get(f"img_{key_base}"),
                        "generated_video": st.session_state.get(f"vid_{key_base}")
                    })
