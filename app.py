import streamlit as st
import sys
import os
import json
import time
from dotenv import load_dotenv
load_dotenv(override=True)

# Add execution directory to path to import scripts
sys.path.append(os.path.join(os.path.dirname(__file__), 'execution'))

try:
    import importlib
    import load_assets as la_module
    importlib.reload(la_module)
    import load_assets as la_module
    importlib.reload(la_module)
    from load_assets import (load_assets, promote_image_to_asset,
                             profile_refs as _profile_refs,
                             profile_voice as _profile_voice)
    import execution.magic_ui as magic_ui_module
    importlib.reload(magic_ui_module)
    from execution.magic_ui import inject_magic_css, magic_text, card_begin, card_end, circular_progress, hover_button, icon_grid_selector, thumbnail_carousel, fidelity_mode_selector
    import generate_image as gi_module
    importlib.reload(gi_module)
    from generate_image import generate_image_from_prompt
    
    import generate_prompt as gp_module
    importlib.reload(gp_module)
    from generate_prompt import generate_prompt_content
    from campaign_runner import CampaignManager
    from execution.generate_video import generate_video_kling, generate_video_humo
    from execution.generate_wan import generate_wan_image, generate_wan_video
    from execution.s3_uploader import upload_file_obj, delete_file
    from generate_video_prompt import generate_motion_prompt
    from world_manager import load_world_db, get_assets_by_category, get_scenarios
    from execution.kling_client import KlingClient
    from execution.sora_client import SoraClient
    from execution.series_processor import parse_script_to_scenes
    from execution.auth import auth_mgr
    from execution.character_utils import build_character_prompt, get_character_sheet_prompt
except ImportError as e:
    st.error(f"Error importing scripts: {e}")
    st.stop()

# --- REMOTE CONFIG INJECTION (Secrets -> Env) ---
# Ensure helper scripts can see secrets as env vars, handling nested tables (e.g. [env])
def recursive_secrets_load(secrets_obj, prefix=""):
    for key, val in secrets_obj.items():
        if isinstance(val, dict):
             # Recursively dive in. Prefix optional? 
             # Usually Streamlit users might group like [aws] bucket_name. 
             # We want to eventually find simple keys if they exist deep down.
             recursive_secrets_load(val, prefix)
        else:
            # Flatten: If key is not in env, add it.
            # We trust the deepest key (or outer?) - First come first serve or overwrite?
            # Let's overwrite to ensure secrets take precedence.
            # Note: We don't prefix because scripts expect "S3_BUCKET_NAME", not "aws_S3_BUCKET_NAME"
            if key not in os.environ:
                 os.environ[key] = str(val)

try:
    if hasattr(st, "secrets"):
         # Convert StreamlitSecrets to dict for recursion
         recursive_secrets_load(dict(st.secrets))
except Exception as e:
    # Safe to ignore locally
    pass

st.set_page_config(page_title="CreateFlow | Viral Lense Media", layout="wide", page_icon=None)

# DEBUG: Inject Diagnostics if requested or if path missing
if os.getenv("S3_BUCKET_NAME") is None and hasattr(st, "secrets"):
     # Auto-show diagnostics if we have secrets but S3 is missing (Misconfiguration)
     with st.sidebar.expander("🛠️ System Diagnosis (Auto)", expanded=True):
          st.error("S3 Bucket Not Found in Env")
          st.write("Secrets Keys Found:")
          def elem_keys(obj, d=0):
               if d > 2: return
               for k, v in obj.items():
                    st.write(f"{'-'*d} {k}")
                    if isinstance(v, dict): elem_keys(v, d+1)
          if hasattr(st, "secrets"):
               elem_keys(dict(st.secrets))
          else:
               st.write("No 'st.secrets' object.")

# --- AUTHENTICATION GATE MOVED AFTER THEME LOADING ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- THEME INJECTION ---
# --- THEME INJECTION ---
def apply_custom_theme():
    # Inject Magic UI styles
    inject_magic_css()

apply_custom_theme()

# --- NEW AUTHENTICATION UI (MULTI-USER) ---
# from execution.auth import auth_mgr (Moved to top)
import extra_streamlit_components as stx
import datetime

# Cookie Manager Init
cookie_manager = stx.CookieManager()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Check Cookie
if not st.session_state.get("authenticated", False):
    try:
        # Check if user is trying to manually login (typing in form)
        # If so, SKIP auto-login to prevent overwriting their action
        manual_attempt = st.session_state.get("auth_user") or st.session_state.get("auth_pass") or st.session_state.get("reg_user")
        
        if not manual_attempt:
            auth_token = cookie_manager.get(cookie="auth_token")
            if auth_token:
                 user_payload = auth_mgr.verify_token(auth_token)
                 if user_payload:
                     st.session_state.authenticated = True
                     st.session_state.current_user = user_payload
    except Exception:
        pass

def handle_login():
    user = st.session_state.get("auth_user", "")
    pwd = st.session_state.get("auth_pass", "")
    
    token, msg = auth_mgr.login(user, pwd)
    
    if token:
        st.session_state.authenticated = True
        st.session_state.current_user = auth_mgr.verify_token(token)
        # Set Cookie (Expires in 7 days)
        cookie_manager.set("auth_token", token, expires_at=datetime.datetime.now() + datetime.timedelta(days=7))
    else:
        st.error(f"⛔ {msg}")

def handle_signup():
    new_user = st.session_state.get("reg_user", "")
    new_pass = st.session_state.get("reg_pass", "")
    
    if not new_user or not new_pass:
        st.error("Please fill in all fields.")
        return

    success, msg = auth_mgr.create_user(new_user, new_pass, role="viewer")
    
    if success:
        st.success("Account Created! Logging in...")
        # Auto Login
        token, _ = auth_mgr.login(new_user, new_pass)
        st.session_state.authenticated = True
        st.session_state.current_user = auth_mgr.verify_token(token)
        # Set Cookie
        cookie_manager.set("auth_token", token, expires_at=datetime.datetime.now() + datetime.timedelta(days=7))
    else:
        st.error(f"Error: {msg}")

if not st.session_state.authenticated:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<div style='text-align: center; color: #94A3B8; font-size: 1rem; font-weight: 500; margin-bottom: 0.5rem;'>Welcome to an all new tool brought to you by</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; color: #FFFFFF; font-size: 1.8rem; font-weight: 900; letter-spacing: 0.1em; margin-bottom: 0px;'>VIRAL LENSE MEDIA</div>", unsafe_allow_html=True)
        # Magic Text H1
        magic_text("CreateFlow", type="h1")
        
        # Auth Tabs
        tab_login, tab_signup = st.tabs(["Login", "Create Account"])
        
        with tab_login:
            st.text_input("Username", key="auth_user", placeholder="admin")
            st.text_input("Password", type="password", key="auth_pass", on_change=handle_login, placeholder="Password")
            # Remember Me removed (Default behavior now)
            st.button("LOGIN", on_click=handle_login, use_container_width=True, type="primary")

        with tab_signup:
            st.text_input("New Username", key="reg_user")
            st.text_input("New Password", type="password", key="reg_pass")
            st.button("SIGN UP", on_click=handle_signup, use_container_width=True)
        
    st.stop()

# --- LOGOUT & SIDEBAR INFO ---
with st.sidebar:
    st.caption("v4.0.0 | Build: Aurora UI") 
    if st.session_state.get("authenticated"):
        u_info = st.session_state.get("current_user", {"username": "Ghost"})
        credits = auth_mgr.get_credits(u_info.get("username"))
        st.markdown(f"**{u_info.get('username')}** ({u_info.get('role', 'Viewer')})")
        c1, c2 = st.columns([3, 1])
        with c1:
             st.markdown(f"<span style='font-size: 1.5rem; font-weight: 700; color: #fff;'>Credits: {credits}</span>", unsafe_allow_html=True)
        with c2:
             if st.button("🔄", key="refresh_creds", help="Hard Refresh (Clear Cache)"):
                 st.cache_data.clear()
                 st.cache_resource.clear()
                 st.rerun()
        
        # Explicit Reset for Troubleshooting
        if st.button("⚠️ RESET SYSTEM CACHE", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Cache Cleared!")
            time.sleep(1)
            st.rerun()

        if st.button("Logout"):
            # Clear cookie by setting it with past expiration
            cookie_manager.set("auth_token", "", expires_at=datetime.datetime.now() - datetime.timedelta(days=1))
            # Fully clear session state to preventing lingering variables
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Allow time for cookie to clear on frontend
            with st.spinner("Logging out..."):
                time.sleep(1)
            st.rerun()
    st.divider()

# HEADER
# HEADER
st.markdown("<div class='brand-overline'>CreateFlow</div>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center; font-size: 6rem; font-weight: 800; letter-spacing: -0.05em; margin-bottom: 0.5rem; text-shadow: 0 0 30px rgba(21,101,192,0.25);'>Enterprise Asset Studio</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 1.2rem; margin-bottom: 3rem; letter-spacing: 0.2em; text-transform: uppercase;'>Your Brand. Your Assets. Total Control.</p>", unsafe_allow_html=True)

# Load Assets
user_asset_path = None
if st.session_state.get("authenticated"):
    username = st.session_state.current_user.get("username", "guest")
    user_asset_path = os.path.join("output", "users", username, "Assets")
    
    # Debug
    # Debug Info Removed for Cleanliness
    # if os.getenv("S3_BUCKET_NAME"):
    #     st.toast(f"Cloud Mode: {os.getenv('S3_BUCKET_NAME')}")

try:
    # V4.1: Cached Loading (Performance Fix)
    # V4.2: Split Caching (Ultra Performance)
    # 1. Base Assets (Persisted to Disk, Updates Hourly or Manual)
    # V4.3: Renamed to get_global_assets to force hard cache bust of old stale ui_icons
    @st.cache_data(ttl=3600, persist="disk", show_spinner="Loading Asset Library...")
    def get_global_assets():
        # Enterprise: skip shared preset library — clients upload their own assets only
        return load_assets(user_assets_dir=None, skip_base=True)

    # 2. User Assets (Session Cache, Fast, Updates often)
    @st.cache_data(ttl=300, show_spinner=False)
    def get_user_assets(user_path, username):
        if not user_path: return {}
        return load_assets(user_assets_dir=user_path, skip_base=True, target_username=username)

    # Load & Merge
    base_assets = get_global_assets()
    user_assets_raw = get_user_assets(user_asset_path, username) if user_asset_path else {} # Return empty dict structure

    # Deep Merge (Naive update overwrites dicts, we need to merge keys within categories)
    # Actually load_assets returns {'characters': {...}, ...}
    # So we need to merge the inner dicts
    assets_raw = base_assets.copy() # Shallow copy of structure
    
    # Helper to merge deep
    # If user_assets_raw is just the dict structure
    # Wait, load_assets returns { 'characters': {}, ... }
    # So we iterate and update
    
    # Correction: If get_user_assets returns a full struct, we iterate keys
    # But wait, did I verify load_assets returns empty dicts for categories? Yes.
    
    # Safe Merging
    # We must deep copy the inner dicts first?
    # Actually, st.cache_data returns mutable refs? We should copy.
    import copy
    assets_raw = copy.deepcopy(base_assets) # Protect the disk cache
    
    if isinstance(user_assets_raw, dict):
        for cat, items in user_assets_raw.items():
            if cat in assets_raw and isinstance(items, dict):
                assets_raw[cat].update(items)
            elif cat not in assets_raw:
                 assets_raw[cat] = items
    
    # Proceed

    if "global_assets" not in st.session_state:
        st.session_state.global_assets = assets_raw

    # Alias for local scope simple access (Read Only)
    assets = st.session_state.global_assets
    
    # Debug
    # st.sidebar.write(f"User Assets Found: {len(assets.get('characters', {}))}")
    vibes_data = assets.get('vibes', {})
    outfits_data = assets.get('outfits', {})

    # Read from world_db
    from execution.world_manager import load_world_db
    db = load_world_db()

    characters_data = assets.get('characters', {}).copy()
    characters_data.update(db.get('characters', {}))
    
    # Merge Friends/Relations into Characters options
    relations_data = assets.get('relations', {})
    characters_data.update(relations_data)
    
    vibes_list = list(vibes_data.keys())
    outfits_list = list(outfits_data.keys())
    characters_list = list(characters_data.keys())
    
except Exception as e:
    st.error(f"Failed to load assets: {e}")
    st.stop()

# --- UI Inputs ---
# Load Knowledge Base
knowledge_base = {}
try:
    with open("knowledge_base.json", "r") as f:
        knowledge_base = json.load(f)
except FileNotFoundError:
    pass

# Initialize Campaign Manager
campaign_mgr = CampaignManager()

# --- HELPER: Resolve character to asset dict ---
def resolve_char_asset(char_key, char_val):
    """Returns an asset dict for generate_image from an uploaded brand ambassador."""
    path = char_val.get("default_img") if isinstance(char_val, dict) else char_val
    name = char_val.get("name", char_key) if isinstance(char_val, dict) else os.path.splitext(os.path.basename(str(char_key)))[0]
    return {"path": path, "label": f"Cast: {name}"}

# Helper: Scan Models - DEPRECATED for Cloud

# --- TABS LAYOUT# TABS
# --- HELPER: FILE ISOLATION ---
def get_user_out_dir(category="General"):
    """Returns a user-isolated output path."""
    if st.session_state.get("authenticated"):
        username = st.session_state.current_user.get("username", "guest")
    else:
        username = "guest"
    
    # Path: output/users/{username}/{category}
    path = os.path.join("output", "users", username, category)
    os.makedirs(path, exist_ok=True)
    return path

# --- HELPER: WAN & SEEDANCE ASSET MAPPING RIG ---
def render_wan_asset_mapping_rig(prefix_key, prompt_target_key=None):
    """
    Renders the visual Environment, Character & Outfit Mapping Rig for Wan & Seedance Studio.
    Returns dict:
      {
        "primary_image_path": str or None,
        "extra_ref_paths": list of str,
        "char_name": str or None,
        "outfit_name": str or None,
        "env_name": str or None,
        "mapping_tags": list of str,
        "ref_audio_paths": list of str   # character voice samples (Seedance 2.5)
      }
    """
    rig_results = {
        "primary_image_path": None,
        "extra_ref_paths": [],
        "char_name": None,
        "outfit_name": None,
        "env_name": None,
        "mapping_tags": [],
        "ref_audio_paths": []
    }
    
    with st.expander("🎭 Environment, Character & Outfit Mapping Rig", expanded=True):
        st.markdown("Build your scene environment first (or choose from existing locations), then select your character and their pre-mapped outfit. The rig automatically maps thumbnails and injects reference tags (`Image1`, `Image2`, `Image3`, `Image4`) into Wan 2.7 & Seedance 2.0.")
        
        c_tab_env, c_tab_char = st.tabs(["🏞️ 1. Environment & Location", "👤 2. Character & Outfit"])
        
        selected_env_paths = []
        selected_env_name = None
        env_names_list = []
        env_slot_labels = []   # one label PER PATH (a profile contributes several)
        selected_char_path = None
        selected_char_name = None
        selected_fit_path = None
        selected_fit_name = None
        
        session_assets = st.session_state.get("global_assets", {})
        username = st.session_state.current_user.get("username", "guest") if st.session_state.get("authenticated") else "guest"
        user_asset_path = os.path.join("output", "users", username, "Assets")
        
        # -------------------------------------------------------------
        # TAB 1: ENVIRONMENT & LOCATION (LIBRARY OR 35MM GENERATOR)
        # -------------------------------------------------------------
        with c_tab_env:
            env_mode = st.radio(
                "Environment Source", 
                ["Select from Library / Existing Master Stills", "✨ Generate New Cascading 35mm Environment Stills"], 
                horizontal=True, 
                key=f"{prefix_key}_env_mode_radio")
            
            if env_mode == "Select from Library / Existing Master Stills":
                raw_locs = session_assets.get('locations', {}).copy()
                cat_locs = get_assets_by_category("locations", user_assets_dir=user_asset_path)
                if cat_locs:
                    raw_locs.update(cat_locs)
                
                # Build unique location display dictionary (ensuring NO key collision)
                loc_opts = {}
                loc_profile_refs = {}  # display key -> full Environment Profile ref list
                for r_k, r_v in raw_locs.items():
                    raw_str_k = str(r_k).replace('{My}', '').strip()
                    l_path = None
                    l_refs = []
                    if isinstance(r_v, dict):
                        disp_name = r_v.get('name') or raw_str_k
                        l_path = r_v.get('default_img') or r_v.get('path')
                        l_refs = _profile_refs(r_v)
                    elif r_v:
                        disp_name = raw_str_k
                        l_path = str(r_v)
                        l_refs = _profile_refs(r_v)
                        
                    if l_path:
                        if os.path.sep in disp_name and not disp_name.startswith("http"):
                            parts = [p.replace('_', ' ').title() for p in disp_name.split(os.path.sep) if p and p != '.']
                            if len(parts) >= 2:
                                if parts[-1].lower() in ['default', 'image', 'primary', 'still', 'thumb', 'png', 'jpg', 'jpeg', 'webp']:
                                    clean_k = parts[-2]
                                else:
                                    clean_k = f"{parts[-2]} - {parts[-1]}"
                            else:
                                clean_k = parts[-1]
                            clean_k = os.path.splitext(clean_k)[0]
                        else:
                            clean_k = os.path.splitext(disp_name)[0].replace('_', ' ').title()
                            
                        # Ensure absolute uniqueness so keys never overwrite each other
                        orig_clean = clean_k
                        dup_counter = 1
                        while clean_k in loc_opts:
                            dup_counter += 1
                            clean_k = f"{orig_clean} ({dup_counter})"
                            
                        loc_opts[clean_k] = l_path
                        if len(l_refs) > 1:
                            loc_profile_refs[clean_k] = l_refs

                # Check for existing generated master stills in session
                existing_stills = st.session_state.get("selected_env_stills", []) or (
                    [st.session_state["primary_env_img"]] if "primary_env_img" in st.session_state and os.path.exists(st.session_state["primary_env_img"]) else []
                )
                
                st.markdown("##### 🏞️ Environment & Location Rig")
                st.caption("Select one or multiple environment locations for your scene using the visual photo carousel below or the search multiselect.")
                
                carousel_selected = thumbnail_carousel(
                    "Select Location Assets",
                    loc_opts,
                    state_key=f"{prefix_key}_rig_loc_multi",
                    thumb_cols=4,
                    show_label=True,
                    multi_select=True
                )
                
                # Also allow multiselect dropdown search
                state_ms_key = f"{prefix_key}_env_multiselect_v2"
                car_key = f"{prefix_key}_rig_loc_multi"
                prev_car_key = f"_prev_car_{car_key}"

                cur_car = list(carousel_selected) if isinstance(carousel_selected, list) else []
                prev_car = st.session_state.get(prev_car_key)

                # Only let the carousel drive the multiselect when the carousel
                # itself changed this run. Unconditionally copying it (the old
                # behaviour) meant a de-selection in the multiselect was
                # overwritten on the very next rerun and appeared to re-add itself.
                if state_ms_key not in st.session_state:
                    st.session_state[state_ms_key] = list(cur_car)
                elif prev_car is not None and cur_car != prev_car:
                    st.session_state[state_ms_key] = list(cur_car)
                st.session_state[prev_car_key] = list(cur_car)

                env_selection = st.multiselect(
                    "🔍 Search & Select Environment Locations",
                    options=list(loc_opts.keys()),
                    key=state_ms_key
                )

                # Push the multiselect back onto the carousel so removing an item
                # clears its highlight too (keeps the two controls in agreement).
                if list(env_selection) != cur_car:
                    st.session_state[car_key] = list(env_selection)
                    st.session_state[prev_car_key] = list(env_selection)

                env_names_list = []
                active_env_list = list(env_selection)
                
                if active_env_list:
                    st.markdown("---")
                    st.markdown("##### 📍 Active Selected Environments")
                    env_cols = st.columns(min(len(active_env_list), 4))
                    
                    for e_idx, member_name in enumerate(active_env_list):
                        l_path = loc_opts.get(member_name)
                        
                        if l_path:
                            prof_refs = loc_profile_refs.get(member_name) or []
                            env_names_list.append(member_name)

                            with env_cols[e_idx % 4]:
                                st.caption(f"**Image Slot #{e_idx+1}**")

                                # A Profile can supply every angle it holds, but
                                # that is a CHOICE — never force extra images in.
                                use_all_angles = False
                                if prof_refs and len(prof_refs) > 1:
                                    use_all_angles = st.checkbox(
                                        f"🎞️ Use all {len(prof_refs)} angles",
                                        value=True,
                                        key=f"{prefix_key}_env_allangles_{member_name}_{e_idx}",
                                        help="Uncheck to attach only the primary image for this location."
                                    )

                                is_u_env = isinstance(l_path, str) and (l_path.startswith("http://") or l_path.startswith("https://"))
                                if is_u_env or os.path.exists(str(l_path)):
                                    st.image(l_path, caption=f"Location: {member_name}", use_container_width=True)
                                else:
                                    st.caption(f"Location: `{member_name}`")

                            if prof_refs and use_all_angles:
                                for a_i, pr in enumerate(prof_refs):
                                    if pr not in selected_env_paths:
                                        selected_env_paths.append(pr)
                                        env_slot_labels.append(f"{member_name} (Angle {a_i+1})")
                            elif l_path not in selected_env_paths:
                                selected_env_paths.append(l_path)
                                env_slot_labels.append(member_name)
                                    
                    selected_env_name = ", ".join(env_names_list)
                elif existing_stills:
                    # Opt-in: this used to attach automatically whenever the
                    # selection was empty, which made de-selecting everything
                    # look like stills were re-adding themselves.
                    use_session_stills = st.checkbox(
                        f"📸 Use {len(existing_stills)} generated Environment Master Still(s) from this session",
                        value=True,
                        key=f"{prefix_key}_use_session_stills",
                        help="Uncheck to ignore stills generated earlier in this session."
                    )
                    if use_session_stills:
                        selected_env_paths.extend(existing_stills)
                        env_slot_labels.extend([f"Master Still #{i+1}" for i in range(len(existing_stills))])
                        selected_env_name = "Generated Environment Master Stills"
                    else:
                        st.caption("No environment attached.")
                    
            else:
                # ENVIRONMENT GENERATOR RIG (Cascading Stills -> one Environment Profile)
                st.markdown("##### 🎨 35mm Cinematic Environment Generator")
                st.caption("Generate up to 3 cascading stills to build an Environment Profile — full scene coverage and continuity from a single location.")

                env_name_input = st.text_input(
                    "Location / Environment Name",
                    placeholder="e.g. Modern Penthouse Lounge, Rainy Tokyo Alleyway, Tropical Resort Poolside",
                    key=f"{prefix_key}_gen_env_name"
                )

                # Optional real photo to anchor the profile. When present it becomes
                # still #1 and every generated angle is continuity-locked to it,
                # instead of the location being invented from text alone.
                env_seed_image = st.file_uploader(
                    "📸 Anchor Photo (Optional) — generate additional angles OF THIS location",
                    type=['png', 'jpg', 'jpeg'],
                    accept_multiple_files=False,
                    key=f"{prefix_key}_env_seed_img",
                    help="Upload a real photo of the location. It becomes reference #1 and the generated angles match its architecture, materials and lighting."
                )

                g_col1, g_col2, g_col3 = st.columns(3)
                with g_col1:
                    env_model_choice = st.selectbox(
                        "Image Engine Model",
                        [
                            "Google Nano Banana 2 (Recommended / Multi-Ref)",
                            "ByteDance Seedream 5.0 (Extreme Photorealism)"
                        ],
                        index=0,
                        key=f"{prefix_key}_gen_env_model"
                    )
                with g_col2:
                    env_still_count = st.slider(
                        "Total Stills in Profile (1 to 3)", 1, 3, 3,
                        key=f"{prefix_key}_gen_env_count",
                        help="Total reference images in this Environment Profile, including the anchor photo if you uploaded one."
                    )
                with g_col3:
                    env_notes = st.text_input(
                        "Textures & Lighting Cues",
                        placeholder="Volumetric fog, 5600K daylight, marble floors",
                        key=f"{prefix_key}_gen_env_notes"
                    )
                    
                if st.button("✨ Generate Cascading Environment Stills", type="primary", key=f"{prefix_key}_run_gen_env", use_container_width=True):
                    if not env_name_input.strip():
                        st.error("Please enter a location name.")
                    else:
                        with st.spinner(f"⚡ Generating {env_still_count} cascading environment stills for '{env_name_input}' using {env_model_choice.split(' ')[0]}..."):
                            from execution.series_processor import generate_environment_master_prompt
                            
                            angles = [
                                "Master Establishing Wide View (107° FOV)",
                                "Reverse Angle Depth View (84° FOV)",
                                "Medium Focal Action Space (63° FOV)",
                                "Macro Architectural Texture Detail (29° FOV)"
                            ]
                            
                            gen_stills = []

                            # An uploaded anchor photo becomes still #1. The
                            # continuity-lock block below already treats
                            # gen_stills[0] as the spatial source of truth for
                            # every later angle, so seeding it here makes the
                            # generated angles match a REAL location.
                            if env_seed_image is not None:
                                seed_path = os.path.join(
                                    "output", f"temp_env_seed_{prefix_key}{os.path.splitext(env_seed_image.name)[1] or '.png'}"
                                )
                                os.makedirs("output", exist_ok=True)
                                with open(seed_path, "wb") as f_seed:
                                    f_seed.write(env_seed_image.getbuffer())
                                gen_stills.append(seed_path)
                                st.caption(f"📸 Anchored to uploaded photo — generating {max(env_still_count - 1, 0)} matching angle(s).")

                            for idx in range(len(gen_stills), env_still_count):
                                angle_lbl = angles[idx] if idx < len(angles) else f"Alternate Perspective #{idx+1}"
                                env_prompt_data = generate_environment_master_prompt(
                                    location_name=f"{env_name_input}. {env_notes}" if env_notes else env_name_input,
                                    genre="Cinematic",
                                    tone="35mm Film Still",
                                    shot_angle_type=angle_lbl,
                                    prior_still_index=idx
                                )
                                env_p = env_prompt_data.get("environment_prompt")
                                
                                payload_assets = []
                                for p_idx, prev_s in enumerate(gen_stills):
                                    if os.path.exists(prev_s):
                                        payload_assets.append({
                                            "path": prev_s,
                                            "label": f"Master Environment Reference Still #{p_idx+1} (Base Location Anchor)"
                                        })
                                        
                                primary_master_still = gen_stills[0] if gen_stills else None
                                
                                if idx > 0 and gen_stills:
                                    continuity_preamble = (
                                        f"SYSTEM INSTRUCTION: SPATIAL ENVIRONMENT CONTINUITY LOCK. "
                                        f"Inspect attached Master Reference Still #1. "
                                        f"Render camera angle '{angle_lbl}' INSIDE the EXACT SAME architectural location ({env_name_input}). "
                                        f"Match wall textures, ceiling structures, window layout, flooring, and lighting setup from Reference Still #1. \n\n"
                                    )
                                    if "SYSTEM INSTRUCTION" not in env_p:
                                        env_p = continuity_preamble + env_p
                                        
                                p_data = {
                                    "positive_prompt": env_p,
                                    "model_type": env_model_choice,
                                    "is_environment_still": True,
                                    "assets": payload_assets,
                                    "aspect_ratio": "16:9",
                                    "image_size": "2K"
                                }
                                res_env = generate_image_from_prompt(
                                    p_data, 
                                    output_folder=get_user_out_dir("World/Environments"),
                                    vibe_path=primary_master_still
                                )
                                if res_env.get("status") == "success":
                                    gen_stills.append(res_env["image_path"])
                                else:
                                    break
                                    
                            if gen_stills:
                                st.session_state["selected_env_stills"] = list(gen_stills)
                                st.session_state["primary_env_img"] = gen_stills[0]
                                st.toast(f"✅ Generated {len(gen_stills)} Environment Stills!")
                                st.rerun()
                                
                # Show generated stills if present with selection checkboxes and Save to Asset Library button
                active_gen_stills = st.session_state.get("selected_env_stills", [])
                if active_gen_stills:
                    st.markdown("##### 🖼️ Active Environment Stills (Select One or Multiple)")
                    
                    e_cols = st.columns(len(active_gen_stills))
                    chosen_stills = []
                    for i, s_p in enumerate(active_gen_stills):
                        with e_cols[i]:
                            if os.path.exists(s_p):
                                st.image(s_p, caption=f"Still #{i+1}", use_container_width=True)
                                is_chk = st.checkbox(f"Use Still #{i+1}", value=True, key=f"{prefix_key}_chk_env_still_{i}")
                                if is_chk:
                                    chosen_stills.append(s_p)
                                    
                    _env_chosen = chosen_stills if chosen_stills else active_gen_stills
                    selected_env_paths.extend(_env_chosen)
                    _env_lbl = env_name_input if env_name_input else "Generated Environment Stills"
                    env_slot_labels.extend([f"{_env_lbl} (Angle {i+1})" for i in range(len(_env_chosen))])
                    selected_env_name = _env_lbl
                    
                    # 💾 SAVE TO LOCATIONS ASSET LIBRARY WITH INSTANT REFRESH
                    s_col1, s_col2 = st.columns([2, 1])
                    with s_col1:
                        save_loc_name = st.text_input("Asset Library Location Name", value=selected_env_name, key=f"{prefix_key}_save_loc_name")
                    with s_col2:
                        st.write("") # spacing
                        st.write("") 
                        if st.button("💾 Save as Environment Profile", key=f"{prefix_key}_btn_save_loc", use_container_width=True):
                            if selected_env_paths:
                                # Save all chosen angles as ONE grouped profile.
                                # Previously each still became its own disconnected
                                # library entry, which lost the continuity link
                                # between angles of the same location.
                                from load_assets import promote_multi_image_profile
                                res_env_save = promote_multi_image_profile(
                                    [p for p in selected_env_paths if os.path.exists(p)],
                                    username,
                                    "Locations",
                                    save_loc_name,
                                    prompt=f"Environment profile for {save_loc_name}",
                                    voice_path=None,
                                    max_images=3,
                                )
                                if res_env_save.get("status") == "success":
                                    from execution.load_assets import load_assets
                                    st.session_state["global_assets"] = load_assets(user_assets_dir=user_asset_path)
                                    st.cache_data.clear()
                                    n_saved = len(res_env_save.get("reference_images", []))
                                    st.toast(f"✅ Saved '{save_loc_name}' Environment Profile ({n_saved} angle(s))!")
                                    st.rerun()
                                else:
                                    st.error(f"Save failed: {res_env_save.get('error')}")
                                
            if selected_env_paths:
                st.caption(f"✅ **Environment Ready ({len(selected_env_paths)} still(s) attached)**")

        # -------------------------------------------------------------
        # TAB 2: MULTI-CHARACTER CAST & WARDROBE RIG
        # -------------------------------------------------------------
        with c_tab_char:
            from execution.world_manager import load_world_db
            db = load_world_db()
            characters_data = session_assets.get('characters', {}).copy()
            characters_data.update(db.get('characters', {}))
            characters_data.update(session_assets.get('relations', {}))
            all_outfits = session_assets.get('outfits', {})
            
            st.markdown("##### 👥 Cast & Wardrobe Rig")
            st.caption("Type or select cast members below. Once added, their character photo thumbnail pops up with their pre-mapped outfit carousel.")
            
            # Type / Search Multiselect for Cast Members
            cast_selection = st.multiselect(
                "🔍 Search & Select Cast Members for Scene",
                options=list(characters_data.keys()),
                key=f"{prefix_key}_cast_multiselect"
            )
            
            selected_characters = [] # list of dicts: {"name": str, "char_path": str, "fit_name": str, "fit_path": str}
            
            if cast_selection:
                st.markdown("---")
                st.markdown("##### 🎭 Active Cast & Wardrobe Setup")
                
                for c_idx, member_key in enumerate(cast_selection):
                    p_val = characters_data.get(member_key)
                    if not p_val:
                        # Fallback case-insensitive key search
                        m_clean = str(member_key).replace('{My}', '').strip().lower()
                        for k, v in characters_data.items():
                            if m_clean in str(k).replace('{My}', '').strip().lower():
                                p_val = v
                                break
                                
                    c_name = str(member_key).replace('{My}', '').replace('(My)', '').strip()
                    c_path = None
                    c_extra_imgs = []   # Character Profile refs beyond the primary
                    c_voice = None      # Character Profile voice sample

                    if isinstance(p_val, dict):
                        c_name = p_val.get('name', c_name)
                        c_path = p_val.get('default_img') or p_val.get('path')
                        c_extra_imgs = _profile_refs(p_val)[1:]
                        c_voice = _profile_voice(p_val)
                    elif isinstance(p_val, str):
                        c_path = p_val
                        # AssetRef is a str subclass carrying its Profile.
                        c_extra_imgs = _profile_refs(p_val)[1:]
                        c_voice = _profile_voice(p_val)
                        # Prefer the Profile's real name — otherwise the library
                        # key leaks into the prompt as "character (My) Name".
                        _pname = getattr(p_val, "profile_name", None)
                        if _pname:
                            c_name = _pname
                    elif not p_val and isinstance(member_key, str) and os.path.exists(member_key):
                        c_path = member_key
                        
                    # Extract clean name if filename
                    if c_path and (not c_name or '/' in c_name or '\\' in c_name):
                        base_n = os.path.basename(str(c_path))
                        c_name = os.path.splitext(base_n)[0].replace('_', ' ').title()
                        
                    st.markdown(f"###### 👤 Cast Member #{c_idx+1}: `{c_name}`")
                    c_col1, c_col2 = st.columns([1.3, 3])
                    
                    with c_col1:
                        # Character Photo Thumbnail Popup under Character Name (Supports Local Files & S3 URLs)
                        is_url = isinstance(c_path, str) and (c_path.startswith("http://") or c_path.startswith("https://"))
                        if c_path and (is_url or os.path.exists(str(c_path))):
                            st.image(c_path, caption=f"Character: {c_name}", use_container_width=True)
                            if not is_url:
                                char_dir = os.path.dirname(str(c_path))
                                valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
                                if os.path.exists(char_dir):
                                    siblings = [f for f in os.listdir(char_dir) if f.lower().endswith(valid_exts) and not f.startswith('.')]
                                    if siblings and len(siblings) > 1:
                                        current_file = os.path.basename(str(c_path))
                                        def_idx = siblings.index(current_file) if current_file in siblings else 0
                                        selected_var = st.selectbox(f"Look Variant for {c_name}", siblings, index=def_idx, key=f"{prefix_key}_char_var_{member_key}_{c_idx}")
                                        c_path = os.path.join(char_dir, selected_var)
                        else:
                            st.image("https://via.placeholder.com/300x300.png?text=Character+Image", caption=f"Character: {c_name}", use_container_width=True)

                        # Identity refs sharpen likeness, but each one is a photo
                        # of the person in SOME outfit. Too many can outvote the
                        # mapped wardrobe, so keep this dialable per shot.
                        if c_extra_imgs:
                            # Is an outfit already mapped to this character? The
                            # outfit carousel stores its pick in session state, so
                            # this is readable before the picker re-renders below.
                            _fit_state = st.session_state.get(f"{prefix_key}_rig_fit_{member_key}_{c_idx}")
                            _has_outfit = bool(_fit_state) and _fit_state != "None"

                            # st.checkbox's `value` is only an INITIAL value — once
                            # the widget has state it is ignored. Drop that state
                            # when outfit-presence flips so the correct default
                            # applies (wardrobe priority once an outfit is mapped).
                            _cb_key = f"{prefix_key}_char_allrefs_{member_key}_{c_idx}"
                            _seen_key = f"_prev_hasfit_{_cb_key}"
                            if st.session_state.get(_seen_key) != _has_outfit:
                                st.session_state.pop(_cb_key, None)
                                st.session_state[_seen_key] = _has_outfit

                            _use_refs = st.checkbox(
                                f"🎭 Use all {len(c_extra_imgs) + 1} identity refs",
                                value=not _has_outfit,
                                key=_cb_key,
                                help=("Extra identity photos sharpen likeness, but each one shows the "
                                      "person in some outfit and competes with the mapped wardrobe. "
                                      "Off by default when an outfit is attached.")
                            )
                            if not _use_refs:
                                c_extra_imgs = []
                                if _has_outfit:
                                    st.caption("🧥 Wardrobe priority: sending 1 identity photo so the outfit locks.")

                    with c_col2:
                        st.markdown(f"**Attach Outfit to {c_name}**")
                        c_clean = c_name.lower().strip() if c_name else ""
                        
                        # Priority sort: matching character outfits first, followed by all remaining outfits in catalog
                        priority_outfits = {}
                        other_outfits = {}
                        for o_k, o_v in all_outfits.items():
                            o_k_low = str(o_k).lower()
                            if c_clean and (c_clean in o_k_low or "angeil" in c_clean and "angeil" in o_k_low or "shay" in c_clean and "shay" in o_k_low or "anisa" in c_clean and "anisa" in o_k_low or "ty" in c_clean and "ty" in o_k_low or "danni" in c_clean and "danni" in o_k_low):
                                priority_outfits[o_k] = o_v
                            else:
                                other_outfits[o_k] = o_v
                                
                        combined_outfits = {**priority_outfits, **other_outfits}
                        
                        f_search = st.text_input(f"🔍 Search Outfit for {c_name}...", key=f"{prefix_key}_fit_search_{member_key}_{c_idx}", placeholder="e.g. Morning, Bikini, Dress, Suit, Robe")
                        if f_search.strip():
                            q_f = f_search.strip().lower()
                            filtered_f = {
                                k: v for k, v in combined_outfits.items()
                                if q_f in k.lower() or (isinstance(v, dict) and q_f in v.get('name', '').lower())
                            }
                            if filtered_f:
                                combined_outfits = filtered_f
                                
                        fit_key = thumbnail_carousel(
                            f"Select Outfit for {c_name}",
                            {"None": None, **combined_outfits},
                            state_key=f"{prefix_key}_rig_fit_{member_key}_{c_idx}",
                            thumb_cols=4,
                            show_label=True
                        )
                        
                        f_name = None
                        f_path = None
                        if fit_key and fit_key != "None":
                            f_val = combined_outfits.get(fit_key)
                            if isinstance(f_val, dict):
                                f_name = f_val.get('name', fit_key)
                                f_path = f_val.get('default_img')
                            elif f_val:
                                f_name = str(fit_key).split('/')[-1]
                                if os.path.sep in f_name:
                                    f_name = os.path.splitext(f_name)[0]
                                f_path = f_val
                                
                    if c_name and c_path:
                        selected_characters.append({
                            "name": c_name,
                            "char_path": c_path,
                            "fit_name": f_name,
                            "fit_path": f_path,
                            "extra_imgs": [p for p in c_extra_imgs if p and p != c_path],
                            "voice_path": c_voice
                        })
                        profile_bits = []
                        if c_extra_imgs:
                            profile_bits.append(f"{len(c_extra_imgs) + 1} refs")
                        if c_voice:
                            profile_bits.append("voice")
                        prof_note = f" · Profile ({', '.join(profile_bits)})" if profile_bits else ""
                        st.caption(f"✅ Mapped Slot #{len(selected_characters)}: `{c_name}`" + (f" wearing `{f_name}`" if f_name else "") + prof_note)
                    st.markdown("---")

        # -------------------------------------------------------------
        # THUMBNAIL PREVIEW STRIP & RIG SUMMARY
        # -------------------------------------------------------------
        rig_imgs = []
        
        # 1. Environment Stills First (Image1, Image2, etc.)
        for e_idx, e_p in enumerate(selected_env_paths[:10]):
            if e_idx < len(env_slot_labels):
                e_label = env_slot_labels[e_idx]
            elif e_idx < len(env_names_list):
                e_label = env_names_list[e_idx]
            else:
                e_label = selected_env_name or 'Location Master'
            rig_imgs.append((f"Image{len(rig_imgs)+1}", e_p, f"Location #{e_idx+1}: {e_label}"))
            
        # 2. Characters and their mapped Outfits Next
        for c_entry in selected_characters:
            c_n = c_entry["name"]
            c_p = c_entry["char_path"]
            f_n = c_entry["fit_name"]
            f_p = c_entry["fit_path"]
            
            c_tag_name = f"Image{len(rig_imgs)+1}"
            c_entry["char_tag"] = c_tag_name
            rig_imgs.append((c_tag_name, c_p, f"Character: {c_n}"))

            # Outfit sits directly after its character, ahead of any identity
            # refs, so the wardrobe reference is adjacent to the subject rather
            # than trailing several photos of them in other clothes.
            if f_p:
                f_tag_name = f"Image{len(rig_imgs)+1}"
                c_entry["fit_tag"] = f_tag_name
                rig_imgs.append((f_tag_name, f_p, f"Outfit for {c_n}: {f_n} (WARDROBE — this garment only)"))

            # Extra Character Profile references (angles 2..N) sharpen identity.
            c_entry["extra_tags"] = []
            for x_i, x_p in enumerate(c_entry.get("extra_imgs") or []):
                x_tag = f"Image{len(rig_imgs)+1}"
                c_entry["extra_tags"].append(x_tag)
                rig_imgs.append((x_tag, x_p, f"Character: {c_n} (Ref {x_i+2} — FACE ONLY, ignore clothing)"))

            # Voice sample rides along as a Seedance audio reference.
            if c_entry.get("voice_path"):
                rig_results["ref_audio_paths"].append(c_entry["voice_path"])
            
        if rig_imgs:
            st.markdown("---")
            st.markdown("##### 📌 Active Rig Mapping Slots")
            if rig_results["ref_audio_paths"]:
                st.caption(f"🎙️ {len(rig_results['ref_audio_paths'])} character voice sample(s) attached as audio references.")
            # Wrap into rows — Profiles can push this well past a single row.
            PER_ROW = 6
            for row_start in range(0, len(rig_imgs), PER_ROW):
                row_items = rig_imgs[row_start:row_start + PER_ROW]
                cols = st.columns(len(row_items))
                for i, (slot_tag, img_p, item_n) in enumerate(row_items):
                    with cols[i]:
                        st.caption(f"**{slot_tag}**")
                        is_u = isinstance(img_p, str) and (img_p.startswith("http://") or img_p.startswith("https://"))
                        if img_p and (is_u or os.path.exists(str(img_p))):
                            st.image(img_p, use_container_width=True)
                        st.caption(f"`{item_n}`")
                    
            # Build API Outputs
            rig_results["primary_image_path"] = rig_imgs[0][1]
            for _, img_p, _ in rig_imgs[1:]:
                rig_results["extra_ref_paths"].append(img_p)
                
            if selected_characters:
                rig_results["char_name"] = ", ".join([c["name"] for c in selected_characters])
                rig_results["outfit_name"] = ", ".join([c["fit_name"] for c in selected_characters if c["fit_name"]])
            rig_results["env_name"] = selected_env_name
            
            for tag, _, item_n in rig_imgs:
                rig_results["mapping_tags"].append(f"{tag}: {item_n}")
                
            # INJECTION BUTTON
            if prompt_target_key:
                if st.button("⚡ Auto-Inject Mapping Rig to Prompt", key=f"{prefix_key}_inject_btn", use_container_width=True):
                    tag_header = "\n".join([f"{t}: {item_n}" for t, _, item_n in rig_imgs])
                    
                    char_pair_sentences = []
                    identity_lock_sentences = []
                    for c in selected_characters:
                        c_n = c["name"]
                        c_tag = c.get("char_tag", "")
                        f_tag = c.get("fit_tag", "")
                        f_n = c.get("fit_name", "")
                        
                        clean_c_n = c_n.replace('{My}', '').replace('(My)', '').strip()
                        # Multi-reference identity lock: tell the model these
                        # separate images are ONE person, or it can read them
                        # as different characters.
                        x_tags = c.get("extra_tags") or []
                        if x_tags:
                            all_id_tags = ", ".join([c_tag] + list(x_tags))
                            id_sentence = (
                                f"{all_id_tags} are the SAME PERSON ({clean_c_n}) shown from different angles. "
                                f"Use them ONLY for facial identity, bone structure, skin tone, hair and tattoos"
                            )
                            if f_tag:
                                # Without this the identity photos act as wardrobe
                                # references and outvote the outfit 3-to-1.
                                id_sentence += (
                                    f". They are identity references, NOT wardrobe references — "
                                    f"completely IGNORE the clothing worn in {all_id_tags}; "
                                    f"it must not appear in the shot"
                                )
                            identity_lock_sentences.append(id_sentence)
                        if c_tag and f_tag and f_n:
                            clean_fit_name = f_n.replace('{My}', '').replace('(My)', '').strip()
                            char_pair_sentences.append(f"character {clean_c_n} ({c_tag}) strictly wearing the complete wardrobe from outfit {f_tag} ({clean_fit_name})")
                        elif c_tag and f_tag:
                            char_pair_sentences.append(f"character {clean_c_n} ({c_tag}) wearing mapped outfit ({f_tag})")
                        elif c_tag:
                            char_pair_sentences.append(f"character {clean_c_n} ({c_tag})")
                            
                    combined_char_str = ", ".join(char_pair_sentences) if char_pair_sentences else "characters"
                    
                    # 3D Spatial Environment Placement & Multi-Angle Camera Directive
                    if selected_env_name:
                        env_directive = (
                            f"placed INSIDE the 3D environment space of Image1 ({selected_env_name}). "
                            f"Use Image1 as the master 3D spatial and architectural set anchor for time, place, and location design. "
                            f"The camera moves dynamically through different angles, reverse perspectives, spatial depth, "
                            f"and room angles inside this environment (do NOT restrict camera to static angle of Image1)."
                        )
                    else:
                        env_directive = (
                            "placed INSIDE the 3D scene location of Image1. "
                            "Use Image1 as the 3D set anchor, exploring dynamic camera angles, depth, and spatial perspectives inside the space."
                        )
                    
                    wardrobe_pairs = [
                        (c.get("fit_tag"), c["name"].replace('{My}', '').replace('(My)', '').strip(), c.get("fit_name"))
                        for c in selected_characters if c.get("fit_tag")
                    ]
                    if wardrobe_pairs:
                        wardrobe_bits = [
                            f"{nm} wears ONLY the garment shown in {tag}"
                            + (f" ({str(fn).replace('{My}', '').replace('(My)', '').strip()})" if fn else "")
                            for tag, nm, fn in wardrobe_pairs
                        ]
                        wardrobe_lock_str = (
                            "Strict Wardrobe Lock: " + "; ".join(wardrobe_bits) + ". "
                            "Reproduce that garment's exact cut, straps, coverage, colour, fabric and detailing "
                            "as the single source of truth for wardrobe — it overrides any clothing visible in the "
                            "character identity references. Do not substitute, restyle, or omit any part of it."
                        )
                    else:
                        wardrobe_lock_str = "Strict Wardrobe Lock: Ensure every character wears the full complete clothing items shown in their mapped outfit reference image without altering or omitting jackets, tops, or pants."

                    # Environment Profile: several slots are the SAME location from
                    # different angles — spell that out so the model treats them as
                    # one continuous space (360° spatial lock).
                    env_slot_count = min(len(selected_env_paths), 10)
                    env_profile_lock = ""
                    if env_slot_count > 1:
                        env_tags = ", ".join(f"Image{i+1}" for i in range(env_slot_count))
                        env_profile_lock = (
                            f" Environment Profile: {env_tags} are the SAME single location shown from "
                            f"different camera angles — match wall textures, ceiling structure, window layout, "
                            f"flooring materials and lighting setup across every shot, never invent a new room."
                        )

                    identity_lock_str = ""
                    if identity_lock_sentences:
                        identity_lock_str = " Identity Lock: " + ". ".join(identity_lock_sentences) + "."

                    injected_text = f"{tag_header}\n\nCinematic 35mm film shot of {combined_char_str} {env_directive}{env_profile_lock}{identity_lock_str} {wardrobe_lock_str} 16:9 widescreen, organic camera movement, realistic 35mm film lighting, zero CGI."
                    st.session_state[prompt_target_key] = injected_text
                    st.toast("✅ Dynamic 3D Spatial & Strict Wardrobe Rig tags injected into Prompt!")
                    st.rerun()
                    
    return rig_results

# --- TABS LAYOUT ---
# --- TABS LAYOUT (Persistent) ---
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Workflow Wizard"

if "wan_edit_image" not in st.session_state:
    st.session_state.wan_edit_image = None
if "wan_animate_image" not in st.session_state:
    st.session_state.wan_animate_image = None
if "wan_active_subtab" not in st.session_state:
    st.session_state.wan_active_subtab = 0

# Custom CSS for Pill-like Tabs
st.markdown("""
<style>
    div[data-testid="stRadio"] > label > div {
        display: none;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        flex-direction: row;
        justify-content: center;
        overflow-x: auto;
        padding-bottom: 10px;
        gap: 6px;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        background-color: rgba(255, 255, 255, 0.06);
        padding: 0.5rem 1.1rem;
        border-radius: 20px;
        margin-right: 0px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        transition: all 0.3s ease;
        cursor: pointer;
        backdrop-filter: blur(8px);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label p {
        color: #CBD5E1 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        background-color: rgba(21, 101, 192, 0.15);
        border-color: rgba(21, 101, 192, 0.5);
        box-shadow: 0 0 12px rgba(21, 101, 192, 0.2);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {
        background: linear-gradient(135deg, #0D2137 0%, #1565C0 100%);
        color: white;
        border-color: transparent;
        font-weight: bold;
        box-shadow: 0 0 20px rgba(21, 101, 192, 0.45);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

nav_options = [
    "Workflow Wizard", 
    "My Gallery",
    "Video Vault",
    "Asset Library",
    "Mini Series",
    "World Builder",
    "Campaign Queue",
    "Art Director",
    "Video Studio",
    "Wan & Seedance Studio",
    "Character Studio",
    "Multi-Shot Generator"
]

# Admin Panel visibility
if st.session_state.get("authenticated") and st.session_state.current_user.get("role") == "admin":
    nav_options.append("Admin Panel")

# Use a callback to update state immediately or just bind to key
selection = st.radio(
    "Navigation", 
    nav_options, 
    index=nav_options.index(st.session_state.active_tab) if st.session_state.active_tab in nav_options else 0,
    horizontal=True, 
    label_visibility="collapsed",
    key="nav_radio"
)

# Update session state if it drifted (redundant with callback but safe)
st.session_state.active_tab = selection

# ==========================================
# TAB: MY GALLERY (v5 — Performance Optimized)
# ==========================================

# --- Cached S3 Scanner (survives reruns, 5-min TTL) ---
@st.cache_data(ttl=300, show_spinner="☁️ Scanning cloud gallery...")
def _scan_s3_gallery(bucket_name, prefix, region):
    """Cached S3 scan — returns sorted list of image metadata dicts."""
    import boto3
    s3 = boto3.client('s3', region_name=region)
    all_images_meta = []
    paginator = s3.get_paginator('list_objects_v2')
    
    all_objects = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            all_objects.append(obj)
            
    thumb_keys_set = set([obj['Key'] for obj in all_objects if obj['Key'].endswith('_thumb.jpg')])
    
    for obj in all_objects:
        key = obj['Key']
        if key.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and '/Assets/' not in key and not key.endswith('_thumb.jpg'):
            thumb_key_pred = key.rsplit('.', 1)[0] + "_thumb.jpg"
            has_thumb = thumb_key_pred in thumb_keys_set
            all_images_meta.append({
                "key": key,
                "thumb_key": thumb_key_pred if has_thumb else key,
                "name": os.path.basename(key),
                "time": obj.get('LastModified').timestamp()
            })
    all_images_meta.sort(key=lambda x: x["time"], reverse=True)
    return all_images_meta[:300]

# --- Cached Presigned URL batch (avoids re-signing on rerun) ---
@st.cache_data(ttl=3500, show_spinner=False)
def _sign_urls(bucket_name, region, keys_tuple):
    """Generate direct public S3 URLs for a batch of keys. keys_tuple for hashability."""
    urls = {}
    import urllib.parse
    for key in keys_tuple:
        encoded_parts = [urllib.parse.quote(part) for part in key.split('/')]
        encoded_key = '/'.join(encoded_parts)
        urls[key] = f"https://{bucket_name}.s3.{region}.amazonaws.com/{encoded_key}"
    return urls

# --- Cached Local Scanner (survives reruns, 2-min TTL) ---
@st.cache_data(ttl=120, show_spinner="📂 Scanning local gallery...")
def _scan_local_gallery(user_root):
    """Cached local file scan — returns sorted list of image metadata dicts."""
    local_imgs = []
    if not os.path.exists(user_root):
        return local_imgs
        
    all_files = []
    for root, dirs, files in os.walk(user_root):
        for file in files:
            all_files.append((root, file))
            
    thumb_paths = set([os.path.join(root, file) for root, file in all_files if file.endswith('_thumb.jpg')])
    
    for root, file in all_files:
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and "Assets" not in root and not file.endswith('_thumb.jpg'):
            full_path = os.path.join(root, file)
            thumb_path_pred = full_path.rsplit('.', 1)[0] + "_thumb.jpg"
            has_thumb = thumb_path_pred in thumb_paths
            
            try:
                mtime = os.path.getmtime(full_path)
            except OSError:
                mtime = 0
            local_imgs.append({
                "src": full_path,
                "thumb_src": thumb_path_pred if has_thumb else full_path,
                "name": file,
                "time": mtime,
                "is_local": True
            })
    local_imgs.sort(key=lambda x: x["time"], reverse=True)
    return local_imgs[:300]

# --- Cached Presigned S3 Video Stream URL ---
@st.cache_data(ttl=3500, show_spinner=False)
def _sign_stream_video_url(bucket_name, key, region):
    """Generates an S3 presigned URL with explicit video/mp4 MIME headers for instant HTML5 streaming."""
    import boto3
    try:
        s3 = boto3.client('s3', region_name=region)
        return s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': key,
                'ResponseContentType': 'video/mp4'
            },
            ExpiresIn=3600
        )
    except Exception as e:
        import urllib.parse
        encoded_parts = [urllib.parse.quote(part) for part in key.split('/')]
        encoded_key = '/'.join(encoded_parts)
        return f"https://{bucket_name}.s3.{region}.amazonaws.com/{encoded_key}"

# --- Cached S3 Video Vault Scanner ---
@st.cache_data(ttl=120, show_spinner="☁️ Scanning Cloud Video Vault...")
def _scan_s3_video_vault(bucket_name, prefix, region):
    """Scans S3 bucket recursively for all user generated videos."""
    import boto3
    s3 = boto3.client('s3', region_name=region)
    all_vids_meta = []
    paginator = s3.get_paginator('list_objects_v2')
    
    try:
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if key.lower().endswith(('.mp4', '.mov', '.webm', '.m4v')) and '/Assets/' not in key and '/Temp' not in key:
                    url = _sign_stream_video_url(bucket_name, key, region)
                    
                    filename = os.path.basename(key)
                    size_mb = obj.get('Size', 0) / (1024 * 1024)
                    mtime = obj.get('LastModified').timestamp() if obj.get('LastModified') else 0
                    
                    folder_tag = "🎬 Mini-Series" if "Series" in key else ("📹 Studio" if "Videos" in key else "🎥 Render")
                    
                    all_vids_meta.append({
                        "key": key,
                        "url": url,
                        "name": filename,
                        "size_mb": round(size_mb, 2),
                        "time": mtime,
                        "folder": folder_tag,
                        "is_local": False
                    })
    except Exception as e:
        print(f"S3 Video Vault scan warning: {e}")
        
    all_vids_meta.sort(key=lambda x: x["time"], reverse=True)
    return all_vids_meta[:300]

# --- Cached Local Video Vault Scanner ---
@st.cache_data(ttl=60, show_spinner="📂 Scanning Local Video Vault...")
def _scan_local_video_vault(user_root):
    """Scans local user directory recursively for all generated videos."""
    local_vids = []
    if not os.path.exists(user_root):
        return local_vids
        
    for root, dirs, files in os.walk(user_root):
        for file in files:
            if file.lower().endswith(('.mp4', '.mov', '.webm', '.m4v')) and "Assets" not in root and "Temp" not in root:
                full_path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(full_path)
                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                except OSError:
                    mtime = 0
                    size_mb = 0
                    
                folder_tag = "🎬 Mini-Series" if "Series" in root else ("📹 Studio" if "Videos" in root else "🎥 Render")
                
                local_vids.append({
                    "src": full_path,
                    "name": file,
                    "size_mb": round(size_mb, 2),
                    "time": mtime,
                    "folder": folder_tag,
                    "is_local": True
                })
                
    local_vids.sort(key=lambda x: x["time"], reverse=True)
    return local_vids[:300]

# --- Zoom Dialog ---
@st.dialog("🔍 Image Viewer", width="large")
def _gallery_zoom_dialog(src, name, is_local=False):
    """Full-size image viewer in a dialog overlay."""
    st.markdown(f"**{name}**")
    if is_local:
        st.image(src, use_container_width=True)
    else:
        st.markdown(
            f"<img src='{src}' style='width:100%; border-radius:8px;' />",
            unsafe_allow_html=True
        )
    # Download inside dialog
    if is_local and os.path.exists(os.path.abspath(src)):
        with open(src, "rb") as f:
            st.download_button("⬇️ Download", data=f, file_name=name, key="dlg_dl", use_container_width=True)
    elif not is_local:
        # Use HTML link styled as a button to force download without opening a new tab
        st.markdown(
            f'''
            <a href="{src}" download="{name}" style="display: block; width: 100%; border-radius: 8px; padding: 0.5rem 1rem; color: inherit; background-color: transparent; border: 1px solid rgba(250, 250, 250, 0.2); text-decoration: none; text-align: center; font-size: 16px; font-weight: 500; font-family: 'Source Sans Pro', sans-serif; box-sizing: border-box; transition: border-color 0.2s, color 0.2s;" onmouseover="this.style.borderColor='#FF4B4B'; this.style.color='#FF4B4B';" onmouseout="this.style.borderColor='rgba(250, 250, 250, 0.2)'; this.style.color='inherit';">
                ⬇️ Download
            </a>
            ''',
            unsafe_allow_html=True
        )

if selection == "Video Vault":
    with st.container():
        st.markdown("### 🎬 Enterprise Video Vault & History")
        
        if not st.session_state.get("authenticated"):
            st.warning("Please login to access your Video Vault.")
        else:
            username = st.session_state.current_user.get("username")
            user_root = os.path.join("output", "users", username)
            
            # Header stats & controls
            c_vhead, c_vsearch, c_vref = st.columns([2, 2, 1])
            with c_vhead:
                if os.getenv("S3_BUCKET_NAME"):
                    st.caption(f"☁️ Cloud Vault: `s3://{os.getenv('S3_BUCKET_NAME')}/users/{username}`")
                else:
                    st.caption(f"📂 Local Vault: `{os.path.abspath(user_root)}`")
            with c_vsearch:
                search_query = st.text_input("🔍 Search Videos", placeholder="Filter by name, shot, or series...", key="vv_search", label_visibility="collapsed")
            with c_vref:
                if st.button("🔄 Sync Vault", use_container_width=True, key="vv_sync_btn"):
                    _scan_s3_video_vault.clear()
                    _scan_local_video_vault.clear()
                    st.rerun()

            # Gather Cloud + Local Videos
            vids = []
            if os.getenv("S3_BUCKET_NAME"):
                bucket = os.getenv("S3_BUCKET_NAME")
                region = os.getenv("AWS_REGION", "ap-southeast-2")
                prefix = f"users/{username}/"
                vids = _scan_s3_video_vault(bucket, prefix, region)
            else:
                vids = _scan_local_video_vault(user_root)
                
            # Filter search query
            if search_query:
                vids = [v for v in vids if search_query.lower() in v["name"].lower()]
                
            if not vids:
                st.info("ℹ️ No videos found in your Video Vault history yet. Generate a video in **Mini Series** or **Wan & Seedance Studio** to automatically save it here!")
            else:
                if "vv_page" not in st.session_state:
                    st.session_state.vv_page = 0
                    
                VIDEOS_PER_PAGE = 8
                total_videos = len(vids)
                total_pages = max(1, (total_videos + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                
                current_page = st.session_state.vv_page
                if current_page >= total_pages:
                    current_page = total_pages - 1
                    st.session_state.vv_page = current_page
                if current_page < 0:
                    current_page = 0
                    st.session_state.vv_page = 0
                    
                start_idx = current_page * VIDEOS_PER_PAGE
                end_idx = min(start_idx + VIDEOS_PER_PAGE, total_videos)
                page_vids = vids[start_idx:end_idx]
                
                # Header stats & Page controls
                v_head_col, v_page_col = st.columns([2, 2])
                with v_head_col:
                    st.success(f"🎥 Found **{total_videos} videos** in Vault (Page {current_page + 1}/{total_pages})")
                with v_page_col:
                    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
                    with col_p1:
                        if st.button("⬅️ Prev", disabled=(current_page == 0), key="vv_prev_top"):
                            st.session_state.vv_page -= 1
                            st.rerun()
                    with col_p2:
                        st.caption(f"Showing {start_idx+1}–{end_idx}")
                    with col_p3:
                        if st.button("Next ➡️", disabled=(current_page >= total_pages - 1), key="vv_next_top"):
                            st.session_state.vv_page += 1
                            st.rerun()
                
                # Grid of video cards (2 columns per row, paginated)
                for i in range(0, len(page_vids), 2):
                    v_cols = st.columns(2)
                    for c_idx, vid in enumerate(page_vids[i:i+2]):
                        with v_cols[c_idx]:
                            with st.container(border=True):
                                st.markdown(f"**{vid['name']}**")
                                st.caption(f"🏷️ {vid['folder']} | 💾 {vid['size_mb']} MB")
                                
                                vid_src = vid["src"] if vid.get("is_local") else vid["url"]
                                if vid.get("is_local"):
                                    st.video(vid_src)
                                else:
                                    st.markdown(f"""
                                    <video width="100%" controls preload="none" playsinline style="border-radius: 8px; max-height: 320px; background-color: #000; outline: none;">
                                        <source src="{vid_src}" type="video/mp4">
                                        Your browser does not support HTML5 video streaming.
                                    </video>
                                    """, unsafe_allow_html=True)
                                
                                c_act1, c_act2 = st.columns(2)
                                with c_act1:
                                    if vid.get("is_local") and os.path.exists(vid["src"]):
                                        with open(vid["src"], "rb") as f_v:
                                            st.download_button(
                                                "⬇️ Download MP4",
                                                data=f_v,
                                                file_name=vid["name"],
                                                mime="video/mp4",
                                                use_container_width=True,
                                                key=f"vv_dl_{vid['name']}_{current_page}_{i}_{c_idx}"
                                            )
                                    else:
                                        st.markdown(f"[⬇️ Download MP4]({vid_src})")
                                with c_act2:
                                    if st.button("🎬 Edit in Studio", key=f"vv_edit_{vid['name']}_{current_page}_{i}_{c_idx}", use_container_width=True):
                                        st.session_state.wan_edit_image = vid_src
                                        st.session_state.active_tab = "Wan & Seedance Studio"
                                        st.rerun()

                if total_pages > 1:
                    st.markdown("---")
                    b_p1, b_p2, b_p3 = st.columns([1, 2, 1])
                    with b_p1:
                        if st.button("⬅️ Previous Page", disabled=(current_page == 0), key="vv_prev_bot"):
                            st.session_state.vv_page -= 1
                            st.rerun()
                    with b_p2:
                        st.markdown(f"<div style='text-align: center'>Page {current_page + 1} of {total_pages}</div>", unsafe_allow_html=True)
                    with b_p3:
                        if st.button("Next Page ➡️", disabled=(current_page >= total_pages - 1), key="vv_next_bot"):
                            st.session_state.vv_page += 1
                            st.rerun()

if selection == "My Gallery":
    with st.container():
        st.markdown("### Personal Gallery")
    
        if not st.session_state.get("authenticated"):
            st.warning("Please login to see your gallery.")
        else:
            username = st.session_state.current_user.get("username")
            user_root = os.path.join("output", "users", username)
            abs_root = os.path.abspath(user_root)
            
            # --- Header Row: path info + page size + refresh ---
            col_gal_head, col_gal_size, col_gal_ref = st.columns([3, 1, 1])
            with col_gal_head:
                 if os.getenv("S3_BUCKET_NAME"):
                     st.caption(f"☁️ Cloud Gallery: `s3://{os.getenv('S3_BUCKET_NAME')}/users/{username}`")
                 else:
                     st.caption(f"📂 Gallery Path: `{abs_root}`")
            with col_gal_size:
                 page_size_options = [12, 20, 50]
                 if "gallery_page_size" not in st.session_state:
                     st.session_state.gallery_page_size = 12
                 selected_size = st.selectbox(
                     "Per page", page_size_options, 
                     index=page_size_options.index(st.session_state.gallery_page_size),
                     key="gal_page_size_sel", label_visibility="collapsed"
                 )
                 if selected_size != st.session_state.gallery_page_size:
                     st.session_state.gallery_page_size = selected_size
                     st.session_state.gallery_page = 0
                     st.rerun()
            with col_gal_ref:
                 if st.button("🔄 Refresh", use_container_width=True):
                      # Clear all gallery scan caches
                      _scan_s3_gallery.clear()
                      _sign_urls.clear()
                      _scan_local_gallery.clear()
                      st.session_state.gallery_page = 0
                      st.rerun()
        
            my_images = []
            IMAGES_PER_PAGE = st.session_state.get("gallery_page_size", 12)
        
            # --- S3 CLOUD SCAN (Cached) ---
            if os.getenv("S3_BUCKET_NAME"):
                try:
                    bucket = os.getenv("S3_BUCKET_NAME")
                    region = os.getenv("AWS_REGION", "ap-southeast-2")
                    prefix = f"users/{username}/"
                    
                    if "gallery_page" not in st.session_state:
                        st.session_state.gallery_page = 0
                    
                    # 1. Fetch metadata (cached across reruns)
                    all_images_meta = _scan_s3_gallery(bucket, prefix, region)
                    
                    # 2. Paginate
                    total_images = len(all_images_meta)
                    total_pages = max(1, (total_images + IMAGES_PER_PAGE - 1) // IMAGES_PER_PAGE)
                    
                    current_page = st.session_state.gallery_page
                    if current_page >= total_pages:
                        current_page = total_pages - 1
                        st.session_state.gallery_page = current_page
                    if current_page < 0:
                        current_page = 0
                        st.session_state.gallery_page = 0
                        
                    start_idx = current_page * IMAGES_PER_PAGE
                    end_idx = start_idx + IMAGES_PER_PAGE
                    page_meta = all_images_meta[start_idx:end_idx]
                    
                    # 3. Batch-sign URLs (cached separately so page changes are instant)
                    keys_to_sign = set()
                    for item in page_meta:
                        keys_to_sign.add(item["key"])
                        if "thumb_key" in item:
                            keys_to_sign.add(item["thumb_key"])
                        
                    signed_urls = _sign_urls(bucket, region, tuple(sorted(list(keys_to_sign))))
                    
                    for item in page_meta:
                        my_images.append({
                            "src": signed_urls.get(item["key"], ""),
                            "thumb_src": signed_urls.get(item.get("thumb_key", item["key"]), ""),
                            "name": item['name'],
                            "time": item['time']
                        })
                    
                    # Pagination Controls
                    st.caption(f"Showing {start_idx+1}–{min(end_idx, total_images)} of {total_images} images")
                    
                    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
                    with col_p1:
                        if st.button("⬅️ Previous", disabled=(current_page == 0)):
                            st.session_state.gallery_page -= 1
                            st.rerun()
                    with col_p2:
                        st.markdown(f"<div style='text-align: center'>Page {current_page + 1} of {total_pages}</div>", unsafe_allow_html=True)
                    with col_p3:
                        if st.button("Next ➡️", disabled=(current_page >= total_pages - 1)):
                            st.session_state.gallery_page += 1
                            st.rerun()

                except Exception as e:
                    st.error(f"Gallery S3 Scan Error: {e}")
                
            # --- LOCAL SCAN (Fallback or Hybrid) — CACHED ---
            elif os.path.exists(user_root):
                local_imgs = _scan_local_gallery(user_root)
                
                # Apply pagination to local images
                total_local = len(local_imgs)
                if "gallery_page" not in st.session_state:
                    st.session_state.gallery_page = 0
                total_pages_local = max(1, (total_local + IMAGES_PER_PAGE - 1) // IMAGES_PER_PAGE)
                current_page = min(st.session_state.gallery_page, total_pages_local - 1)
                start_idx = current_page * IMAGES_PER_PAGE
                end_idx = start_idx + IMAGES_PER_PAGE
                my_images.extend(local_imgs[start_idx:end_idx])
                
                if total_local > 0:
                    st.caption(f"Showing {start_idx+1}–{min(end_idx, total_local)} of {total_local} images")
                    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
                    with col_p1:
                        if st.button("⬅️ Previous", disabled=(current_page == 0), key="local_prev"):
                            st.session_state.gallery_page -= 1
                            st.rerun()
                    with col_p2:
                        st.markdown(f"<div style='text-align: center'>Page {current_page + 1} of {total_pages_local}</div>", unsafe_allow_html=True)
                    with col_p3:
                        if st.button("Next ➡️", disabled=(current_page >= total_pages_local - 1), key="local_next"):
                            st.session_state.gallery_page += 1
                            st.rerun()

            
            if not my_images:
                st.info(f"No images found for `{username}` yet. Generate something in the Wizard or Series tab!")
            else:
                st.write(f"Found {len(my_images)} images on this page.")
                
                # --- Gallery Grid CSS ---
                st.markdown("""
                <style>
                    .gallery-card img {
                        border-radius: 8px;
                        aspect-ratio: 1 / 1;
                        object-fit: cover;
                        width: 100%;
                        transition: transform 0.2s ease, box-shadow 0.2s ease;
                    }
                    .gallery-card img:hover {
                        transform: scale(1.03);
                        box-shadow: 0 4px 20px rgba(21, 101, 192, 0.3);
                    }
                    .gallery-card {
                        margin-bottom: 1rem;
                    }
                    .gal-name {
                        font-size: 0.75rem;
                        color: #94A3B8;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        margin-top: 4px;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                # Display Grid with lazy-loaded images
                cols = st.columns(4)
                for idx, item in enumerate(my_images):
                    is_local = item.get("is_local", False)
                    with cols[idx % 4]:
                        # Render image
                        if is_local:
                            st.image(item.get("thumb_src", item["src"]), use_container_width=True)
                            st.markdown(f"<div class='gal-name'>{item['name']}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(
                                f"""<div class="gallery-card">
                                    <img src="{item.get('thumb_src', item['src'])}" loading="lazy" alt="{item['name']}" />
                                    <div class="gal-name">{item['name']}</div>
                                </div>""",
                                unsafe_allow_html=True
                            )
                        
                        # Single row: zoom + download (reduced from 2 columns to 1 button row)
                        c_view, c_dl = st.columns(2)
                        with c_view:
                            if st.button("🔍 View", key=f"view_{idx}", use_container_width=True):
                                _gallery_zoom_dialog(item["src"], item["name"], is_local=is_local)
                        with c_dl:
                            if is_local and os.path.exists(os.path.abspath(item["src"])):
                                with open(item["src"], "rb") as f:
                                    st.download_button("⬇️ Save", data=f, file_name=item["name"], key=f"gal_dl_{idx}", use_container_width=True)
                            elif not is_local:
                                # Use an HTML download link styled as a button for S3 presigned URLs
                                st.markdown(
                                    f'''
                                    <a href="{item['src']}" download="{item['name']}" style="display: block; width: 100%; border-radius: 8px; padding: 0.25rem 0.75rem; color: inherit; background-color: transparent; border: 1px solid rgba(250, 250, 250, 0.2); text-decoration: none; text-align: center; font-size: 14px; box-sizing: border-box; transition: border-color 0.2s, color 0.2s;" onmouseover="this.style.borderColor='#FF4B4B'; this.style.color='#FF4B4B';" onmouseout="this.style.borderColor='rgba(250, 250, 250, 0.2)'; this.style.color='inherit';">
                                        ⬇️ Save
                                    </a>
                                    ''',
                                    unsafe_allow_html=True
                                )
                        
                        # Row 2: Wan 2.7 Studio Shortcuts
                        c_wan_edit, c_wan_anim = st.columns(2)
                        # Identify the best local path if available
                        target_shortcut_path = item.get("local_path", item["src"]) if is_local else item["src"]
                        with c_wan_edit:
                            if st.button("✏️ Edit", key=f"wan_edit_btn_{idx}", use_container_width=True, help="Edit this image using Wan 2.7 Image-to-Image"):
                                st.session_state.wan_edit_image = target_shortcut_path
                                st.session_state.wan_studio_subtab_radio = "Image-to-Image (Scene Editor)"
                                st.session_state.active_tab = "Wan & Seedance Studio"
                                st.rerun()
                        with c_wan_anim:
                            if st.button("🎬 Animate", key=f"wan_anim_btn_{idx}", use_container_width=True, help="Animate this image using Wan 2.7 Image-to-Video"):
                                st.session_state.wan_animate_image = target_shortcut_path
                                st.session_state.wan_studio_subtab_radio = "Image-to-Video (Motion)"
                                st.session_state.active_tab = "Wan & Seedance Studio"
                                st.rerun()

# ==========================================
# TAB: ASSET LIBRARY
# ==========================================
if selection == "Asset Library":
    with st.container():
        username = st.session_state.current_user.get("username")
        user_asset_root = os.path.join("output", "users", username, "Assets")
        
        col_up_1, col_up_2 = st.columns([1, 2])
        
        with col_up_1:
            st.info("How it works:\n\n1. Select a category (e.g. Characters).\n2. Upload an image.\n3. Give it a name.\n4. It's now usable in Wizard & World Builder!")
            
        with col_up_2:
            st.markdown("##### Upload New Asset")
            
            # Category Map
            cat_map = {
                "Characters": "Characters",
                "Outfits": "Outfits",
                "Environments": "Environments",
                "Vibes": "Vibes",
                "Props": "Props",
                "Pets": "Pets",
                "Friends": "Friends",
                "Vehicles": "Vehicles"
            }
            
            target_cat = st.selectbox("Category", list(cat_map.keys()))
            uploaded_files = st.file_uploader("Choose Images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
            
            # Optional Name Override (Only applies if single file, or strictly prefixes?)
            # User request: "Original file name should be saved... shouldn't have to rename"
            # So custom_name is truly optional or for prefixing.
            custom_name_prefix = st.text_input("Name Prefix (Optional)", placeholder="Leave empty to use filenames")
            
            if st.button("Save to Library", type="primary"):
                if not uploaded_files:
                    st.error("Please upload files.")
                else:
                    save_dir = os.path.join(user_asset_root, cat_map[target_cat])
                    os.makedirs(save_dir, exist_ok=True)
                    
                    count = 0
                    for up_file in uploaded_files:
                        # 1. Determine Name
                        if custom_name_prefix:
                             # Use prefix + index if multiple? Or just prefix if one?
                             # Let's clean filename
                             f_clean = os.path.splitext(up_file.name)[0]
                             final_name = f"{custom_name_prefix} {f_clean}"
                        else:
                             final_name = os.path.splitext(up_file.name)[0]
                             
                        # Sanitize
                        final_name = "".join([c for c in final_name if c.isalnum() or c in (' ', '-', '_')]).strip()
                        ext = os.path.splitext(up_file.name)[1]
                        
                        # 2. Save File
                        target_path = os.path.join(save_dir, f"{final_name}{ext}")
                        with open(target_path, "wb") as f:
                            f.write(up_file.getbuffer())
                            
                        # 3. SMART INJECT (Instant UI Update)
                        # Add to Session State so it appears in dropdowns immediately
                        # Key format: "(My) Name"
                        mem_key = f"(My) {final_name}"
                        # Map back to internal Keys
                        # cat_map keys are UI keys (Characters), we need internal usage keys (characters)
                        internal_cat_map = {
                            "Characters": "characters", "Outfits": "outfits", "Environments": "locations",
                            "Vibes": "vibes", "Props": "props", "Pets": "pets", "Friends": "relations", "Vehicles": "vehicles"
                        }
                        int_key = internal_cat_map.get(target_cat)
                        
                        if int_key and "global_assets" in st.session_state:
                             st.session_state.global_assets[int_key][mem_key] = target_path
                        
                        # --- S3 SYNC (Restored per-file) ---
                        if os.getenv("S3_BUCKET_NAME"):
                             try:
                                 from execution.s3_uploader import upload_file_obj 
                                 # Key: users/{user}/Assets/{Category}/{Filename}
                                 s3_key = f"users/{username}/Assets/{cat_map[target_cat]}/{final_name}{ext}"
                                 
                                 # Upload
                                 # We can upload the buffer directly or the file
                                 with open(target_path, "rb") as f_up:
                                     upload_file_obj(f_up, object_name=s3_key)
                                     
                                 count += 1
                             except Exception as e:
                                 st.error(f"S3 Upload Error for {final_name}: {e}")
                        else:
                             count += 1
                             
                    st.success(f"Saved {count} assets! Check dropdowns instantly.")
                    # NO RERUN needed because we updated State.
                            
                    st.success(f"Saved **{final_name}** to {target_cat}!")
                    
                    # Update Manifest Logic
                    # We just added a file. We should update the manifest if it exists, or delete it to force a rescan.
                    # Deleting is safer and forces a sync on next load (which will recreate it).
                    # Actually, since load_assets creates it if missing, deleting is a perfect detailed invalidation strategy.
                    
                    user_manifest_path = os.path.join(user_asset_root, "user_manifest.json")
                    if os.path.exists(user_manifest_path):
                        try:
                            # Option A: Delete to force refresh
                            os.remove(user_manifest_path)
                            # Option B: Append to it (Complex, risky if schema changes)
                        except Exception:
                            pass
                    
                    # Clear Cache to allow new asset to show
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    
                    time.sleep(1)
                    st.rerun()

        st.divider()
        st.markdown("#### 📂 Your Library")
        
        # Display directly from Loaded Assets (which includes S3 URLs if in Cloud Mode)
        # We filter for items starting with "(My)" which load_assets.py applies to user content
        
        user_cats = {
            "Characters": "characters",
            "Outfits": "outfits",
            "Environments": "locations", # Mapped
            "Vibes": "vibes",
            "Props": "props", 
            "Pets": "pets",
            "Friends": "relations",
            "Vehicles": "vehicles"
        }
        
        found_any = False
        
        for ui_cat, data_key in user_cats.items():
            # Get all assets for this category
            # all_dict is {Name: Path/URL}
            all_dict = assets.get(data_key, {})
            
            # Filter for User Assets (marked with (My) prefix or checking if it's an S3 URL with 'users/'?)
            # The cleanest way is relying on the keys from load_assets
            my_items = {k: v for k, v in all_dict.items() if "(My)" in k}
            
            if my_items:
                found_any = True
                with st.expander(f"{ui_cat} ({len(my_items)})", expanded=False):
                    c_grid = st.columns(6)
                    for i, (name, url) in enumerate(my_items.items()):
                        # Clean name for display: "(My) Name" -> "Name"
                        clean_name = name.replace("(My) ", "")
                        
                        with c_grid[i % 6]:
                            st.image(url, caption=clean_name, use_container_width=True)
                            
                            # DELETE BUTTON
                            # Use ui_cat to ensure uniqueness across categories (e.g. Vibes vs Locations acting as fallback)
                            if st.button("🗑️", key=f"del_{ui_cat}_{i}_{name}", help=f"Delete {clean_name}"):
                                try:
                                    # 1. Determine Folder Name from Internal Key
                                    # data_key is 'characters', 'outfits', etc.
                                    # We need 'Characters', 'Outfits' for disk/S3
                                    folder_map = {
                                        "characters": "Characters", "outfits": "Outfits", 
                                        "locations": "Environments", "vibes": "Vibes", 
                                        "props": "Props", "pets": "Pets", 
                                        "relations": "Friends", "vehicles": "Vehicles"
                                    }
                                    folder_name = folder_map.get(data_key, data_key.capitalize())
                                    
                                    # Handle URL parameters for S3 Presigned URLs
                                    clean_url = url.split('?')[0]
                                    fname = os.path.basename(clean_url)
                                    
                                    # 2. Local Delete (Construct path explicitly)
                                    # user_asset_root is available in scope
                                    local_path = os.path.join(user_asset_root, folder_name, fname)
                                    if os.path.exists(local_path):
                                        os.remove(local_path)
                                        # Also try to remove json metadata if it exists
                                        meta = local_path.replace(os.path.splitext(local_path)[1], ".json")
                                        if os.path.exists(meta): os.remove(meta)
                                        st.toast(f"Deleted local file: {clean_name}")
                                    elif os.path.exists(url) and url != local_path:
                                        # Fallback if url was actually a different local path
                                        os.remove(url)
                                    
                                    # 3. S3 Delete
                                    if os.getenv("S3_BUCKET_NAME"):
                                        # Construct Key: users/{user}/Assets/{Folder}/{Filename}
                                        s3_key = f"users/{username}/Assets/{folder_name}/{fname}"
                                        delete_file(s3_key)
                                        st.toast(f"Deleted from Cloud: {clean_name}")
                                        
                                    # 4. State Update
                                    if data_key in st.session_state.global_assets:
                                        if name in st.session_state.global_assets[data_key]:
                                            del st.session_state.global_assets[data_key][name]
                                            
                                    # 5. Clear Cache & Rerun
                                    st.cache_data.clear()
                                    time.sleep(0.5)
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Delete Failed: {e}")
                            
        if not found_any:
            st.info("No custom assets found yet. Upload one above!")
            
        # Debug Info for User Peace of Mind
        if os.getenv("S3_BUCKET_NAME"):
            st.success(f"☁️ Cloud Mode Active: Syncing with S3 ({os.getenv('S3_BUCKET_NAME')})")
        else:
            if os.path.exists(user_asset_root):
                st.caption(f"📂 Local Storage: {user_asset_root}")
            else:
                st.warning("⚠️ Local Storage Missing (Expected on Cloud if S3 not fully synced)")


# ==========================================
# TAB 1: WORKFLOW WIZARD (Existing Logic)
# ==========================================
if selection == "Workflow Wizard":
    with st.container():
        st.markdown("### Step-by-Step Content Creator")
        
        # --- UI Inputs ---
        # --- UI Inputs ---
        # --- UI Inputs (Fragmented for Performance) ---
        @st.fragment
        def wizard_selectors(vibes, outfits, characters, v_data, o_data, c_data):
            st.markdown("#### 1. Choose Character")
            # Build character carousel data — strip path strings for display
            char_carousel_data = {}
            for k, v in c_data.items():
                char_carousel_data[k] = v

            thumbnail_carousel(
                "Characters",
                char_carousel_data,
                state_key="wiz_char",
                thumb_cols=3,
                show_label=False
            )

            # Outfit carousel — only show after character is selected
            if st.session_state.get("wiz_char"):
                st.markdown("#### 2. Choose Outfit")
                outfit_carousel_data = {k: v for k, v in o_data.items()}
                thumbnail_carousel(
                    "Outfits",
                    outfit_carousel_data,
                    state_key="wiz_outfit",
                    thumb_cols=3,
                    show_label=False
                )

            st.markdown("#### 3. Vibe / Atmosphere")
            vibe_carousel_data = {k: v for k, v in v_data.items()}
            thumbnail_carousel(
                "Vibes",
                vibe_carousel_data,
                state_key="wiz_vibe",
                thumb_cols=3,
                show_label=False
            )
    
        # Call Fragment
        wizard_selectors(vibes_list, outfits_list, characters_list, vibes_data, outfits_data, characters_data)
    
        # --- FIDELITY MODE ROW ---
        fidelity_label, fidelity_modifier = fidelity_mode_selector(state_key="wiz_fidelity")
        st.session_state['wiz_fidelity_modifier'] = fidelity_modifier

        st.divider()

        # V3.9: Wrapped in Form to Prevent Reload Loop
        with st.form(key="wizard_form"):
            # Expandable Camera Controls
            with st.expander("🎥 Camera & Scene Settings", expanded=False):
                col_cam, col_light, col_action = st.columns(3)
                
                with col_cam:
                    st.markdown("**Camera**")
                    sel_camera = st.selectbox("Camera Type", ["Auto"] + knowledge_base.get("cameras", []))
                    sel_lens = st.selectbox("Lens", ["Auto"] + knowledge_base.get("lenses", []))
                    sel_shot = st.selectbox("Shot Type", ["Auto"] + knowledge_base.get("shot_types", []))
                    sel_angle = st.selectbox("Camera Angle", ["Auto"] + knowledge_base.get("camera_angles", []))
                    sel_ar = st.selectbox("Aspect Ratio", ["Auto", "4:5 (Standard)", "16:9 (Cinematic)", "9:16 (Social)"], index=0)
                    sel_res = st.selectbox("Resolution", ["1K", "2K", "4K"], index=0, help="Higher = sharper but slower")
                    sel_style = st.selectbox("Photo Style", ["Auto"] + knowledge_base.get("styles", []))
                    
                with col_light:
                    st.markdown("**Atmosphere**")
                    sel_lighting = st.selectbox("Lighting", ["Auto"] + knowledge_base.get("lighting", []))
                    sel_weather = st.selectbox("Weather", ["Auto"] + knowledge_base.get("weather", []))
                    sel_film = st.selectbox("Film Stock (Grain)", ["Auto"] + knowledge_base.get("film_stocks", []), key="wiz_film_stock")
                    
                with col_action:
                    st.markdown("**Action & Tone**")
                    sel_action = st.selectbox("Subject Action", ["Auto"] + knowledge_base.get("actions", []), key="wiz_action")
                    sel_emotion = st.selectbox("Emotion", ["Auto"] + knowledge_base.get("emotions", []), key="wiz_emotion")
                    sel_filter = st.selectbox("Filter / Look", ["Auto"] + knowledge_base.get("filters", []), key="wiz_filter")
    
            # Custom Direction
            st.subheader("4. Creative Direction")
            custom_scenario = st.text_input("Scenario / Context", placeholder="e.g. At a luxury coffee shop in Paris...")
            custom_notes = st.text_area("Specific Details", placeholder="Enter any extra details here...")
            
            # Advanced Settings & Variants
            col_adv, col_count = st.columns([3, 1])
            
            with col_adv:
                with st.expander("⚙️ Advanced Brain Settings"):
                     st.caption("Brain: Gemini 2.0 Flash (Optimized for Cost)")
                     prompt_engine = "gemini-2.0-flash" 
                     render_engine = "nano" 
                     likeness = 0.5
                     st.sidebar.success("✅ Running in Low-Cost Mode (Flash 2.0)")
                     # selected_checkpoint removed
                     
            with col_count:
                num_images = st.slider("Generate Count", 1, 4, 1, key="wiz_test_count")
    
            # CRITICAL: Store all form values in session state for Director AI button (outside form)
            st.session_state['wiz_sel_camera'] = sel_camera
            st.session_state['wiz_sel_lens'] = sel_lens
            st.session_state['wiz_sel_shot'] = sel_shot
            st.session_state['wiz_sel_angle'] = sel_angle
            st.session_state['wiz_sel_ar'] = sel_ar
            st.session_state['wiz_sel_style'] = sel_style
            st.session_state['wiz_sel_lighting'] = sel_lighting
            st.session_state['wiz_sel_weather'] = sel_weather
            st.session_state['wiz_sel_film'] = sel_film
            st.session_state['wiz_sel_action'] = sel_action
            st.session_state['wiz_sel_emotion'] = sel_emotion
            st.session_state['wiz_sel_filter'] = sel_filter
            st.session_state['wiz_custom_scenario'] = custom_scenario
            st.session_state['wiz_custom_notes'] = custom_notes
    
            # --- CAMPAIGN BUTTON ---
            col_c_btn, col_c_batch = st.columns([3, 1])
            with col_c_batch:
                campaign_batch = st.number_input("Queue Copies", min_value=1, max_value=10, value=1, help="How many variations to queue?")
    
            submit_wiz = st.form_submit_button("Add to Campaign Queue", type="primary")
    
        if submit_wiz:
            # CHECK CREDITS
            user = st.session_state.current_user.get("username")
            if not auth_mgr.deduct_credits(user, 1):
                st.error("❌ Insufficient Credits! Please top up.")
            else:
                # Retrieve values from Session State (set by Fragment)
                s_char = st.session_state.get("wiz_char")
                s_outfit = st.session_state.get("wiz_outfit")
                s_vibe = st.session_state.get("wiz_vibe")

                # Get path for Vision
                char_val = characters_data.get(s_char)
                char_asset = resolve_char_asset(s_char, char_val) if char_val else None
                char_path = char_asset.get("path") if char_asset else None
                outfit_path = outfits_data.get(s_outfit)
                vibe_path = vibes_data.get(s_vibe)
                
                def clean_val(val): return None if val == "Auto" else val
                
                fidelity_mod = st.session_state.get('wiz_fidelity_modifier', '')
                prompt_data = generate_prompt_content(
                    vibe=clean_val(s_vibe), 
                    outfit=s_outfit, 
                    character=char_path,
                    outfit_path=outfit_path,
                    vibe_path=vibe_path,
                    additional_notes=f"{custom_notes} . Context: {custom_scenario} . Emotion: {clean_val(sel_emotion)} . Style: {clean_val(sel_style) or ''} . Look: {fidelity_mod}", 
                    camera=clean_val(sel_camera),
                    lens=clean_val(sel_lens),
                    shot_type=clean_val(sel_shot),
                    angle=clean_val(sel_angle),
                    lighting=clean_val(sel_lighting),
                    weather=clean_val(sel_weather),
                    action=clean_val(sel_action),
                    film_stock=clean_val(sel_film),
                    filter_look=clean_val(sel_filter),
                    aspect_ratio=sel_ar.split(" ")[0], 
                    model_engine=prompt_engine 
                )
                
                prompt_data["likeness_strength"] = likeness # Pass to generator
                
                prompt_data["model_type"] = render_engine 
                prompt_data["image_size"] = sel_res
                job_name = f"{s_outfit} - {clean_val(s_vibe)}"
                campaign_mgr.add_job(
                    name=job_name,
                    description=f"Engine: {render_engine}",
                    prompt_data=prompt_data,
                    settings={ "batch_count": campaign_batch },
                    output_folder=get_user_out_dir("Campaign"),
                    char_path=char_path,
                    outfit_path=outfit_path,
                    vibe_path=vibe_path
                )
                msg = f"Added '{job_name}'! (Engine: {render_engine}, Batch: {campaign_batch})"
                st.success(msg)

    st.divider()

    # --- TWO STEP GENERATION ---
    col_wiz_btn1, col_wiz_btn2 = st.columns(2)
    
    # Session State for Wizard Prompt
    if "wiz_generated_prompt" not in st.session_state:
        st.session_state.wiz_generated_prompt = None

    with col_wiz_btn1:
        if st.button("✨ Director Vision AI (Generate Prompt)", type="primary", use_container_width=True):
             with st.spinner("Director is writing master prompt..."):
                # Retrieve values from Session State
                s_char = st.session_state.get("wiz_char")
                s_outfit = st.session_state.get("wiz_outfit")
                s_vibe = st.session_state.get("wiz_vibe")
                
                # Get camera/scene settings from session state (stored in form)
                sel_camera = st.session_state.get('wiz_sel_camera', 'Auto')
                sel_lens = st.session_state.get('wiz_sel_lens', 'Auto')
                sel_shot = st.session_state.get('wiz_sel_shot', 'Auto')
                sel_angle = st.session_state.get('wiz_sel_angle', 'Auto')
                sel_ar = st.session_state.get('wiz_sel_ar', 'Auto')
                sel_style = st.session_state.get('wiz_sel_style', 'Auto')
                sel_lighting = st.session_state.get('wiz_sel_lighting', 'Auto')
                sel_weather = st.session_state.get('wiz_sel_weather', 'Auto')
                sel_film = st.session_state.get('wiz_sel_film', 'Auto')
                sel_action = st.session_state.get('wiz_sel_action', 'Auto')
                sel_emotion = st.session_state.get('wiz_sel_emotion', 'Auto')
                sel_filter = st.session_state.get('wiz_sel_filter', 'Auto')
                custom_scenario = st.session_state.get('wiz_custom_scenario', '')
                custom_notes = st.session_state.get('wiz_custom_notes', '')

                # Get path for Vision
                char_val = characters_data.get(s_char)
                char_asset = resolve_char_asset(s_char, char_val) if char_val else None
                char_path = char_asset.get("path") if char_asset else None
                outfit_path = outfits_data.get(s_outfit)
                vibe_path = vibes_data.get(s_vibe)
                
                # Filter "Auto" values (pass None if Auto)
                def clean_val(val): return None if val == "Auto" else val
                
                fidelity_mod = st.session_state.get('wiz_fidelity_modifier', '')
                prompt_data = generate_prompt_content(
                    vibe=s_vibe, 
                    outfit=s_outfit, 
                    character=char_path,
                    outfit_path=outfit_path,
                    vibe_path=vibe_path,
                    additional_notes=f"{custom_notes} . Context: {custom_scenario} . Emotion: {clean_val(sel_emotion)} . Style: {clean_val(sel_style) or ''} . Look: {fidelity_mod}", 
                    camera=clean_val(sel_camera),
                    lens=clean_val(sel_lens),
                    shot_type=clean_val(sel_shot),
                    angle=clean_val(sel_angle),
                    lighting=clean_val(sel_lighting),
                    weather=clean_val(sel_weather),
                    action=clean_val(sel_action),
                    emotion=clean_val(sel_emotion), # Added Emotion
                    film_stock=clean_val(sel_film),
                    filter_look=clean_val(sel_filter),
                    aspect_ratio=sel_ar.split(" ")[0], 
                    model_engine=prompt_engine 
                )
                
                st.session_state.wiz_generated_prompt = prompt_data
                st.toast("Prompt Generated! Review below.")

    # Show Editable Prompt if generated
    if st.session_state.wiz_generated_prompt:
        st.markdown("##### 📝 Review & Edit Prompt")
        
        # We bind this to a separate key to allow editing
        # If the generated prompt changes or is new, we might want to reset? 
        # For simple flow, we default value to what's in session state
        
        wiz_prompt_text = st.text_area(
            "Master Prompt", 
            value=st.session_state.wiz_generated_prompt.get("positive_prompt", ""),
            height=200,
            key="wiz_manual_edit"
        )
        
        with col_wiz_btn2:
             c_q, c_g = st.columns([1, 2])
             with c_q:
                 add_queue = st.button("Add to Queue", use_container_width=True, key="wiz_add_q")
             with c_g:
                 run_now = st.button("🎨 Generate Images", type="primary", use_container_width=True, key="wiz_run")
             
             if add_queue:
                 # Update prompt data
                 final_prompt_data = st.session_state.wiz_generated_prompt.copy()
                 final_prompt_data["positive_prompt"] = wiz_prompt_text
                 final_prompt_data["likeness_strength"] = likeness
                 final_prompt_data["model_type"] = render_engine 
                 # Re-resolve paths for execution
                 s_char = st.session_state.get("wiz_char")
                 s_outfit = st.session_state.get("wiz_outfit")
                 s_vibe = st.session_state.get("wiz_vibe")
                 char_val = characters_data.get(s_char)
                 char_asset = resolve_char_asset(s_char, char_val) if char_val else None
                 char_path = char_asset.get("path") if char_asset else None
                 outfit_path = outfits_data.get(s_outfit)
                 vibe_path = vibes_data.get(s_vibe)
                 
                 campaign_mgr.add_job(
                    name=f"Wiz_{s_char}_{int(time.time())}",
                    description=f"Wizard: {s_char} in {s_outfit}",
                    prompt_data=final_prompt_data,
                    settings={"batch_count": num_images},
                    output_folder=get_user_out_dir("Wizard"),
                    char_path=char_path,
                    outfit_path=outfit_path,
                    vibe_path=vibe_path
                 )
                 st.success("✅ Added to Campaign Queue!")

             if run_now:
                 with st.status(f"Running workflow ({prompt_engine} + {render_engine})...", expanded=True) as status:
                    st.write(f"Generating {num_images} Image(s)...")
                    
                    # Update prompt data with edited text
                    # We need a deep copy or just modify the dict
                    final_prompt_data = st.session_state.wiz_generated_prompt.copy()
                    final_prompt_data["positive_prompt"] = wiz_prompt_text
                    final_prompt_data["likeness_strength"] = likeness
                    final_prompt_data["model_type"] = render_engine 
                    # Re-resolve paths for execution
                    s_char = st.session_state.get("wiz_char")
                    s_outfit = st.session_state.get("wiz_outfit")
                    s_vibe = st.session_state.get("wiz_vibe")

                    char_val = characters_data.get(s_char)
                    char_asset = resolve_char_asset(s_char, char_val) if char_val else None
                    char_path = char_asset.get("path") if char_asset else None
                    outfit_path = outfits_data.get(s_outfit)
                    vibe_path = vibes_data.get(s_vibe)
                    
                    # OUTPUT SETUP - User Isolated
                    wiz_out_dir = get_user_out_dir("Wizard")
                    
                    st.write(f"DEBUG: Saving to {os.path.abspath(wiz_out_dir)}")

                    # Parallel Execution
                    from concurrent.futures import ThreadPoolExecutor
                    results = []
                    
                    with ThreadPoolExecutor() as executor:
                        # CRITICAL: Pass the image paths so Generation Logic can see them
                        futures = [executor.submit(generate_image_from_prompt, final_prompt_data, wiz_out_dir, char_path, outfit_path, vibe_path) for i in range(num_images)]
                        for future in futures:
                            results.append(future.result())
                    
                    # Display Results
                    # Create a container for results
                    st.divider()
                    st.markdown("#### 📸 Results")
                    cols = st.columns(num_images)
                    for i, result in enumerate(results):
                        with cols[i]:
                            if result and result.get("status") == "success":
                                img_path = result["image_path"]
                                st.image(img_path, caption=f"Variant {i+1}", use_container_width=True)
                                
                                # Show explicit path
                                abs_path = os.path.abspath(img_path)
                                st.success(f"Saved: {os.path.basename(img_path)}")
                                st.caption(f"📁 {abs_path}")
                                
                                # Add download button
                                c_d, c_s = st.columns(2)
                                with c_d:
                                    with open(img_path, "rb") as f:
                                        st.download_button("⬇️ Download", f, file_name=os.path.basename(img_path), mime="image/png", key=f"dw_{i}")
                                with c_s:
                                    if st.button("📁 Quick Save", key=f"qs_{i}", help="Saves to 'Wizard' category in Assets"):
                                        if st.session_state.get("authenticated"):
                                            user = st.session_state.current_user.get("username")
                                            # Default name to timestamp/index if not providing a form
                                            a_name = f"Wiz_{int(time.time())}_{i}"
                                            res = promote_image_to_asset(img_path, user, "Vibes", a_name, wiz_prompt_text)
                                            if res["status"] == "success":
                                                st.toast(f"Saved to Vibes!")
                                                st.cache_data.clear()
                                            else:
                                                st.error(f"Save Failed: {res.get('error')}")
                            else:
                                st.error("Failed")
                                if result: st.write(result)
                    
                    status.update(label="Workflow Complete!", state="complete", expanded=True)






# ==========================================
# TAB: MINI SERIES STUDIO
# ==========================================
if selection == "Mini Series":
    with st.container():
        from execution.mini_series_ui import mini_series_ui
        mini_series_ui(user_asset_path, outfits_data, vibes_data, assets, knowledge_base, auth_mgr, get_user_out_dir, campaign_mgr)
# ==========================================
# ==========================================
# TAB: ADMIN PANEL
# ==========================================
if selection == "Admin Panel":
    with st.container():
        st.markdown("### 🛡️ School Community Admin")
        st.info("Manage the Allowlist for student access. Only emails in this list can sign up.")

        # Tabs
        tab_list, tab_users, tab_upload, tab_stats = st.tabs(["Active Allowlist", "User Management", "Upload CSV", "System Config"])
        
        with tab_list:
            c_tog, c_add = st.columns([2, 1])
            with c_tog:
                is_enforced = os.getenv("ENFORCE_ALLOWLIST", "True").lower() == "true"
                if st.checkbox("Enforce Allowlist (Reject unknown emails)", value=is_enforced):
                    auth_mgr.toggle_allowlist_enforcement(True)
                    st.toast("Allowlist Enforced")
                else:
                    auth_mgr.toggle_allowlist_enforcement(False)
                    st.warning("Allowlist Disabled: Open Signup Active")
            
            with c_add:
                with st.form("quick_add"):
                    new_email = st.text_input("Quick Add Email")
                    if st.form_submit_button("Add Member"):
                        if "@" in new_email:
                            auth_mgr.add_to_allowlist(new_email.strip())
                            st.success(f"Added {new_email}")
                            st.rerun()
                        else:
                            st.error("Invalid Email")
            
            st.divider()
            rows = auth_mgr.list_allowlist()
            if rows:
                st.dataframe(rows, use_container_width=True, column_config={
                    "0": "Email", "1": "Name", "2": "Active"
                })
            else:
                st.warning("Allowlist is empty.")
        
        with tab_users:
            st.markdown("#### Registered Users")
            all_users = auth_mgr.get_all_users()
            st.dataframe(all_users, use_container_width=True)
            
            st.divider()
            st.markdown("#### User Actions")
            c_u, c_act, c_val = st.columns([2, 2, 2])
            with c_u:
                tgt_user = st.selectbox("Select User", [u['username'] for u in all_users])
            with c_act:
                action = st.selectbox("Action", ["Add Credits", "Reset Password", "Ban User"])
            with c_val:
                val_input = st.text_input("Value (Credits or New Pass)", key="admin_act_val")
                
            if st.button("Execute Action", type="primary"):
                if action == "Add Credits":
                    if val_input.isdigit():
                        auth_mgr.add_credits(tgt_user, int(val_input))
                        st.success(f"Added {val_input} credits to {tgt_user}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Enter a number for credits")
                elif action == "Reset Password":
                    if len(val_input) > 3:
                        auth_mgr.reset_user_password(tgt_user, val_input)
                        st.success(f"Password reset for {tgt_user}")
                    else:
                        st.error("Password too short")
                elif action == "Ban User":
                    if st.checkbox(f"Confirm Delete {tgt_user}?"):
                        if auth_mgr.ban_user(tgt_user):
                            st.success(f"Banned {tgt_user}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Cannot ban admin")

        with tab_upload:
            st.markdown("#### Bulk Add Students")
            uploaded_file = st.file_uploader("Upload CSV (Header: email, name)", type=["csv"])
            if uploaded_file:
                import pandas as pd
                try:
                    df = pd.read_csv(uploaded_file)
                    # Normalize headers
                    df.columns = [c.lower().strip() for c in df.columns]
                    
                    if "email" not in df.columns:
                        st.error("CSV must have an 'email' column.")
                    else:
                        if st.button(f"Import {len(df)} Students"):
                            count = 0
                            for index, row in df.iterrows():
                                email = str(row['email']).strip()
                                name = str(row.get('name', '')).strip()
                                if "@" in email:
                                    if auth_mgr.add_to_allowlist(email, name):
                                        count += 1
                            st.success(f"Successfully added {count} students to Allowlist!")
                except Exception as e:
                    st.error(f"Error parsing CSV: {e}")

        with tab_stats:
            st.write("Coming soon: Usage stats per student.")
# Global defaults for form submit buttons — must be set before any tab block
gen_world = False
wb_queue = False

if selection == "World Builder":
    with st.container():
        st.markdown("### World Builder")
        st.info("Construct complex scenes with multiple characters, props, and specific assets.")
    
    # Load Real Data
    world_db = load_world_db()
    scenarios = get_scenarios()
    
    # Layout
    # Layout: Full Width for Builder
    # Removed "Asset Database" Column as requested
    
    st.markdown("#### Scenario Director")
    
    # 0. Import Helper
    # Ideally should be at top, but placing here for context
    try:
        from execution.storyboard_utils import generate_storyboard_prompts
    except ImportError as e:
        st.error(f"Failed to import storyboard utils: {e}")
        def generate_storyboard_prompts(s, c, m): return [f"Error: {e}"]

    # 1. Scenario Mode Selection
    with st.container():
        card_begin()
        st.markdown("#### Scenario Director")
        
        # Mode Toggle - CRITICAL: Use key to persist across form submissions
        scenario_mode = st.radio(
            "Scenario Mode",
            ["📚 Pre-built Templates", "✏️ Custom Scenario"],
            horizontal=True,
            key="wb_scenario_mode",  # PERSIST SELECTION
            help="Choose a pre-built scenario template or create your own custom scene"
        )
        
        if scenario_mode == "📚 Pre-built Templates":
            # Existing pre-built scenario logic
            # Sort by Category then Name
            scenario_keys = sorted(
                list(scenarios.keys()),
                key=lambda k: (scenarios[k].get('category', 'Uncategorized'), scenarios[k].get('name', ''))
            )
            
            selected_scenario_key = st.selectbox(
                "Select Scenario Template", 
                scenario_keys, 
                format_func=lambda x: f"[{scenarios[x].get('category', 'General').upper()}] {scenarios[x]['name']}"
            )
            
            if selected_scenario_key:
                scenario = dict(scenarios[selected_scenario_key])
                scenario['is_custom'] = False
                st.session_state['wb_current_scenario'] = scenario
                st.session_state['wb_selected_scenario_key'] = selected_scenario_key
                st.caption(f"💡 Template: {scenario['template_prompt']}")
        else:
            # NEW: Custom Scenario Builder
            st.markdown("##### Create Your Own Scene")
            
            custom_scenario_name = st.text_input(
                "Scenario Name (Optional)", 
                placeholder="e.g., Girls' Night Out, Birthday Celebration, Beach Day..."
            )
            
            custom_scenario_desc = st.text_area(
                "Describe Your Scene",
                placeholder="Describe the scene you want to create. The Director AI will automatically incorporate all your selected assets (characters, outfits, locations, props, etc.) into this scene description.\n\nExample: 'A fun photoshoot at the beach during golden hour' or 'Celebrating a friend's birthday at a rooftop restaurant'",
                height=120,
                help="The Director AI will contextualize all your selected assets into this scenario"
            )
            
            save_as_template = st.checkbox(
                "💾 Save as template for future use",
                help="This will add your custom scenario to the pre-built templates"
            )
            
            
            # Create a mock scenario object for downstream logic
            scenario = {
                "name": custom_scenario_name or "Custom Scene",
                "category": "custom",
                "template_prompt": custom_scenario_desc or "Custom scene with selected assets",
                "is_custom": True  # Flag to trigger Director AI
            }
            selected_scenario_key = "custom_scenario"
            
            # CRITICAL: Store these IMMEDIATELY so form can access them
            st.session_state['wb_current_scenario'] = scenario
            st.session_state['wb_selected_scenario_key'] = selected_scenario_key
            
            # Save as template if requested
            if save_as_template and custom_scenario_name and custom_scenario_desc:
                try:
                    from world_manager import add_asset
                    scenario_key = custom_scenario_name.lower().replace(" ", "_")
                    add_asset("scenarios", scenario_key, {
                        "name": custom_scenario_name,
                        "category": "custom",
                        "template_prompt": custom_scenario_desc
                    })
                    st.success(f"✅ Saved '{custom_scenario_name}' as a template! It will appear in pre-built templates after refresh.")
                except Exception as e:
                    st.error(f"Failed to save template: {e}")
            
            if custom_scenario_desc:
                st.caption(f"✨ Your scene: {custom_scenario_desc[:100]}{'...' if len(custom_scenario_desc) > 100 else ''}")
        
        card_end()
    
    if selected_scenario_key:
        # --- SCENE COMPOSITION UI (Synced with Filesystem) ---
        # Fragment to prevent full reload
        @st.fragment
        def wb_composition_fragment(scenarios, selected_scenario_key):
            assets = st.session_state.global_assets
            temp_selections = {}
            temp_assets = []
            prompt_engine = "gemini-2.0-flash" # Default for World Builder
            
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                with st.container():
                    card_begin()
                    st.markdown("##### Cast & Characters")
                    st.markdown("###### 1. Protagonist")
                    
                    
                    characters_data = assets.get('characters', {})
                    wb_char_opts = {**characters_data}

                    # --- CHARACTER CAROUSEL ---
                    protag_key = thumbnail_carousel(
                        "Select Protagonist",
                        wb_char_opts,
                        state_key="wb_protag",
                        thumb_cols=3,
                        show_label=True
                    )

                    protag_opts = wb_char_opts  
                    p_final_path = None
                    p_final_name = "Character"
    
                    if protag_key:
                        p_val = protag_opts.get(protag_key)
                        if isinstance(p_val, dict):
                            p_final_name = p_val['name']
                            p_final_path = p_val.get('default_img')
                        elif p_val:
                            # Filesystem Asset
                            filename = protag_key.split('/')[-1]
                            if "default" in filename.lower():
                                 p_final_name = protag_key.split('/')[-2]
                            else:
                                 p_final_name = os.path.splitext(filename)[0]
                            p_final_path = p_val
                    
                        temp_selections["PROTAGONIST"] = p_final_name
    
                        if p_final_path and os.path.exists(str(p_final_path)):
                            siblings = []
                            char_dir = os.path.dirname(p_final_path)
                            valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
                            siblings = [f for f in os.listdir(char_dir) if f.lower().endswith(valid_exts) and not f.startswith('.')]
                        
                            if siblings:
                                current_file = os.path.basename(p_final_path)
                                try:
                                    def_idx = siblings.index(current_file)
                                except ValueError:
                                    def_idx = 0
                                selected_var = st.selectbox("Select Specific Look", siblings, index=def_idx, key="protag_var")
                                p_final_path = os.path.join(char_dir, selected_var)
                    
                        if p_final_path:
                            temp_assets.append({"path": p_final_path, "label": "Main Character"})

                    st.markdown("###### 1b. Main Character Outfit")
                    fit_opts = assets.get('outfits', {})

                    # --- OUTFIT CAROUSEL ---
                    fit_key = thumbnail_carousel(
                        "Select Outfit",
                        {"None": None, **fit_opts},
                        state_key="wb_outfit_main",
                        thumb_cols=3,
                        show_label=False
                    )
                    
                    if fit_key and fit_key != "None":
                        path = fit_opts.get(fit_key)
                        if isinstance(path, dict): path = path.get('default_img')
                        
                        fit_name = fit_key.split('/')[-1] 
                        if os.path.sep in fit_name: fit_name = os.path.splitext(fit_name)[0]
                        if "default" in fit_name.lower(): fit_name = "Stylish Outfit"
                        
                        temp_selections["OUTFIT"] = fit_name
                        temp_assets.append({"path": path, "label": f"Outfit: {fit_name}"})
    
                    st.markdown("###### 2. Friends & Cast")
                    rel_opts = assets.get('relations', {})
                    cast_pool = {**wb_char_opts, **rel_opts}
                    rel_keys = sorted(list(cast_pool.keys()))
                    
                    selected_rels = st.multiselect(
                        "Include People", 
                        rel_keys,
                        format_func=lambda x: cast_pool[x].get('name', x) if isinstance(cast_pool[x], dict) else x
                    )
                
                    rel_names = []
                    if selected_rels:
                        st.caption("Selected Cast:")
                        r_cols = st.columns(len(selected_rels))
                        for idx, k in enumerate(selected_rels):
                            path = cast_pool[k] 
                            name = k 
                            if isinstance(path, dict):
                                 name = path.get('name', k)
                                 path = path.get('default_img', '')
                            else:
                                 clean_name = os.path.splitext(k.split('/')[-1])[0]
                                 if k in wb_char_opts: name = clean_name
                                 else: name = clean_name
                        
                            rel_names.append(name)
                            temp_assets.append({"path": path, "label": f"Cast: {name}"})
                            with r_cols[idx]:
                                if path: st.image(path, caption=name)
    
                    if rel_names:
                        temp_selections["RELATIONS"] = " and ".join(rel_names)
                        st.caption("Selected Cast Outfits:")
                        friend_outfit_details = []
                        f_cols = st.columns(len(selected_rels))
                        for idx, k in enumerate(selected_rels):
                            with f_cols[idx]:
                                 f_name = cast_pool[k]['name'] if isinstance(cast_pool[k], dict) else k.split('/')[-1]
                                 
                                 # Standardize outfit options, starting with "Default Outfit"
                                 f_fit_opts = {"Default Outfit": None}
                                 raw_opts = assets.get('outfits', {})
                                 if raw_opts:
                                     f_fit_opts.update(raw_opts)
                                 else:
                                     f_fit_opts.update({"Casual": "", "Chic": ""})
                                     
                                 f_outfit_key = st.selectbox(f"Outfit for {f_name.split()[0]}", list(f_fit_opts.keys()), index=0, key=f"fit_{idx}")
                                 
                                 f_outfit_path = None
                                 if f_outfit_key == "Default Outfit":
                                     f_outfit_name = "default outfit"
                                 elif isinstance(f_fit_opts[f_outfit_key], dict):
                                     f_outfit_name = f_fit_opts[f_outfit_key]['name']
                                     f_outfit_path = f_fit_opts[f_outfit_key].get('default_img')
                                 else:
                                     f_outfit_name = os.path.splitext(f_outfit_key.split('/')[-1])[0]
                                     f_outfit_path = f_fit_opts[f_outfit_key]
                                 
                                 if f_outfit_path:
                                     temp_assets.append({"path": f_outfit_path, "label": f"Outfit for {f_name}: {f_outfit_name}"}) 
                                     st.image(f_outfit_path, width=150, caption=f_outfit_name)
                                 else:
                                     st.caption("Using default appearance.")
                                     
                                 friend_outfit_details.append(f"{f_name} in {f_outfit_name}") 
                        if friend_outfit_details:
                            temp_selections["FRIEND_OUTFITS"] = ", ".join(friend_outfit_details)
                    else:
                        temp_selections["RELATIONS"] = "nobody"
                    card_end()

            with col_c2:
                with st.container():
                    card_begin()
                    st.markdown("##### Setting & Props")
                    st.markdown("###### 3. Pets")
                    pet_opts = assets.get('pets', {})
                    selected_pets = st.multiselect("Include Pets", list(pet_opts.keys()))
                    pet_names = []
                    if selected_pets:
                        p_cols = st.columns(len(selected_pets))
                        for idx, k in enumerate(selected_pets):
                            path = pet_opts[k]
                            name = k.split('/')[-1]
                            pet_names.append(name)
                            temp_assets.append({"path": path, "label": f"Pet: {name}"})
                            with p_cols[idx]:
                                 if path: st.image(path, caption=name)
                    st.divider()
                    st.markdown("###### 4. Props & Vehicles")
                    prop_opts = assets.get('props', {})
                    veh_opts = assets.get('vehicles', {})
                    all_props = {**prop_opts, **veh_opts}
                    selected_props = st.multiselect("Include Items", list(all_props.keys()))
                    prop_names = []
                    if selected_props:
                         pr_cols = st.columns(min(len(selected_props), 4))
                         for idx, k in enumerate(selected_props):
                             path = all_props[k]
                             name = k.split('/')[-1]
                             prop_names.append(name)
                             temp_assets.append({"path": path, "label": f"Prop: {name}"})
                             col_idx = idx % 4
                             with pr_cols[col_idx]:
                                 if path: st.image(path, caption=name)
                    if prop_names:
                        temp_selections["PROPS"] = ", ".join(prop_names)
                        temp_selections["VEHICLE"] = prop_names[0]
                    else:
                        temp_selections["PROPS"] = "props"
                        temp_selections["VEHICLE"] = "vehicle"
                    st.divider()
                    st.markdown("###### 5. Location")
                    loc_opts = get_assets_by_category("locations")
                    
                    loc_key = thumbnail_carousel(
                        "Select Location",
                        {"None": None, **loc_opts},
                        state_key="wb_location",
                        thumb_cols=3,
                        show_label=False
                    )
                    
                    if loc_key and loc_key != "None":
                          val = loc_opts.get(loc_key)
                          path = val['default_img'] if isinstance(val, dict) else val
                          loc_name = loc_key.split('/')[-1]
                          if os.path.sep in loc_name: loc_name = os.path.splitext(loc_name)[0]
                          
                          if "default" in loc_name.lower(): loc_name = "Luxury Location"

                          temp_selections["LOCATION"] = loc_name
                          temp_assets.append({"path": path, "label": "Location"})
                    else:
                          temp_selections["LOCATION"] = "generic location"
                    
                    st.divider()
                    st.markdown("###### 6. Vibe / Atmosphere")
                    vibe_opts = ["Luxury", "Cinematic", "Dark", "Bright", "Cozy", "High Energy", "Chill", "Romantic", "Cyberpunk", "Vintage"]
                    sel_vibe = st.selectbox("Select Vibe", vibe_opts, index=0)
                    temp_selections["VIBE"] = sel_vibe

                    card_end()
            
            # Persist to Session State (Critical for Generator outside fragment)
            st.session_state['wb_selections'] = temp_selections
            st.session_state['wb_assets_to_inject'] = temp_assets
            # Store auxiliary lists (props, pets etc) if needed by prompt logic
            st.session_state['wb_rel_names'] = rel_names
            st.session_state['wb_pet_names'] = pet_names
            st.session_state['wb_prop_names'] = prop_names

        # Call the Fragment
        wb_composition_fragment(scenarios, selected_scenario_key)
        
        # Hydrate Local Vars from storage (for downstream legacy logic)
        current_selections = st.session_state.get('wb_selections', {})
        assets_to_inject = st.session_state.get('wb_assets_to_inject', [])
        rel_names = st.session_state.get('wb_rel_names', [])
        pet_names = st.session_state.get('wb_pet_names', [])
        prop_names = st.session_state.get('wb_prop_names', [])
        
        # Camera/Shot/Lighting are now dropdowns inside the form below (see Additional Settings)

        # --- FIDELITY MODE ---
        wb_fidelity_label, wb_fidelity_modifier = fidelity_mode_selector(state_key="wb_fidelity")
        st.session_state['wb_fidelity_modifier'] = wb_fidelity_modifier

        st.divider()

        # V3.9: Wrapped in Form to prevent Camera Settings Reload Loop
        with st.form(key="wb_camera_form"):
            # --- ALL CAMERA CONTROLS (Including angle/shot/lighting moved from card pickers) ---
            with st.expander("📸 Camera & Scene Settings", expanded=False):
                col_cam, col_mood, col_look = st.columns(3)
                with col_cam:
                    st.markdown("**📷 Hardware**")
                    sel_camera = st.selectbox("Camera Type", ["Auto"] + knowledge_base.get("cameras", []), key="wb_cam")
                    sel_lens = st.selectbox("Lens", ["Auto"] + knowledge_base.get("lenses", []), key="wb_lens")
                    sel_shot = st.selectbox("Shot Type", ["Auto"] + knowledge_base.get("shot_types", []), key="wb_shot")
                    sel_angle = st.selectbox("Camera Angle", ["Auto"] + knowledge_base.get("camera_angles", []), key="wb_angle")
                    sel_ar = st.selectbox("Aspect Ratio", ["Auto", "4:5", "16:9", "9:16", "1:1", "3:2"], index=0, key="wb_ar")
                    sel_res = st.selectbox("Resolution", ["1K", "2K", "4K"], index=0, key="wb_res", help="Higher = sharper but slower")
                    sel_lighting = st.selectbox("Lighting", ["Auto"] + knowledge_base.get("lighting", []), key="wb_lighting")
    
                with col_mood:
                    st.markdown("**Direction & Mood**")
                    sel_film = st.selectbox("Style", ["Auto"] + knowledge_base.get("styles", []), key="wb_film")
                    sel_filter_look = st.selectbox("Filter / Look", ["Auto"] + knowledge_base.get("filters", []), key="wb_look")
                    sel_weather = st.selectbox("Weather", ["Auto"] + knowledge_base.get("weather", []), key="wb_weath")
                    sel_film_stock = st.selectbox("Film Stock", ["Auto"] + knowledge_base.get("film_stocks", []), key="wb_stock")
                    # Emotions
                    emotions = [
                        "Auto", "Confident", "Carefree", "Playful", "Relaxed", "Flirty", "Happy", "Calm", "Curious", 
                        "Focused", "Content", "Empowered", "Soft", "Radiant", "Unbothered", "Dreamy", 
                        "Joyful", "Peaceful", "Excited", "Serene", "Bold", "Mischievous", "Warm", 
                        "Self-assured", "Chill", "Lighthearted", "Magnetic", "Present", "Satisfied", 
                        "Quietly happy", "Seductive", "Boss Bitch", "Hysterical", "Zen"
                    ]
                    sel_emotion = st.selectbox("Emotion", emotions, key="wb_emo")
                    
                    # Actions
                    actions = [
                         "Auto",
                         "Adjusting outfit strap", "Adjusting sunglasses", "Applying lip gloss", "Biting lip playfully", 
                         "Celebrating big play courtside", "Celebrating together", "Checking phone notifications", "Clinking drink glasses",
                         "Crossing arms confidently", "Crossing legs slowly", "Dancing subtly", "Fixing hair casually", "Fixing jacket collar",
                         "Flipping hair back", "Group selfie moment", "Holding drink cup", "Holding sunglasses", 
                         "Hyping each other up", "Journaling quietly", "Laughing lightly", "Laughing mid-conversation", "Laughing with friends",
                         "Leaning against wall", "Leaning casually", "Leaning on railing", "Looking around calmly", 
                         "Looking over shoulder", "Pausing mid-step", "Podcast Host (Speaking into Mic)", "Pointing something out", 
                         "Posing effortlessly", "Resting hands on hips", "Scrolling phone casually", 
                         "Sharing inside joke", "Sipping iced coffee", "Sitting close together", "Sitting poolside relaxed", 
                         "Sitting thoughtfully", "Smiling softly", "Stepping into sunlight", "Stretching arms overhead", 
                         "Stretching neck gently", "Taking a deep breath", "Taking mirror selfie", "Talking mid-conversation",
                         "Tilting head slightly", "Walking confidently forward", "Walking side by side", "Walking with friends"
                     ]
                    sel_action = st.selectbox("Action", actions, key="wb_act")

                with col_look:
                    st.markdown("**Appearance**")
                    sel_hairstyle = st.selectbox("Hairstyle", ["Auto"] + knowledge_base.get("hairstyles", []), key="wb_hair")
                    sel_makeup = st.selectbox("Makeup", ["Auto"] + knowledge_base.get("makeup", []), key="wb_makeup")
                    sel_hair_cond = st.selectbox("Hair Condition", ["Auto"] + knowledge_base.get("hair_condition", []), key="wb_hair_cond")
                    sel_temperature = st.slider("Temperature (AI Creativity)", 0.0, 2.0, 1.0, 0.1, key="wb_temp", help="Lower = more predictable. Higher = more creative/wild.")
            
            # --- CUSTOM DETAILS ---
            st.markdown("#### Creative Direction")
            custom_details = st.text_area("Specific Details / Custom Context", placeholder="e.g. Holding a red cup, Laughing uniquely, Cyberpunk neon colors...", help="These details will be added to the prompt.")
    
            # --- PROMPT GENERATION LOGIC UPDATE ---
            # CRITICAL: Get scenario from session state (widgets outside form don't persist)
            scenario = st.session_state.get('wb_current_scenario', scenario)
            
            # Check if this is a custom scenario (requires Director AI)
            is_custom_scenario = scenario.get("is_custom", False)
            
            # CRITICAL: Store flag in session state so it persists on button click
            st.session_state['is_custom_scenario'] = is_custom_scenario
            
            # Prepare prompt based on scenario type
            if is_custom_scenario:
                # NEW: Prepare data for custom scenario Director AI (will execute on button click)
                # Store scenario and settings for Director AI button
                st.session_state['custom_scenario_data'] = {
                    'scenario_concept': scenario['template_prompt'],
                    'current_selections': current_selections,
                    'rel_names': rel_names,
                    'pet_names': pet_names,
                    'prop_names': prop_names,
                    'camera_settings': {
                        'shot': sel_shot,
                        'angle': sel_angle,
                        'lighting': sel_lighting,
                        'emotion': sel_emotion,
                        'action': sel_action,
                        'film': sel_film,
                        'filter_look': sel_filter_look,
                        'hairstyle': sel_hairstyle,
                        'makeup': sel_makeup,
                        'hair_condition': sel_hair_cond
                    },
                    'custom_details': custom_details
                }
                
                # Build a basic template prompt as fallback
                final_prompt = f"{scenario['template_prompt']} featuring {current_selections.get('PROTAGONIST', 'character')}"
                if current_selections.get('LOCATION'):
                    final_prompt += f" at {current_selections.get('LOCATION')}"
                if current_selections.get('OUTFIT'):
                    final_prompt += f" wearing {current_selections.get('OUTFIT')}"
                if custom_details:
                    final_prompt += f", {custom_details}"
                    
                st.info("ℹ️ Click 'Director Vision AI' below to generate a detailed, immersive prompt for your custom scenario")
                
            else:
                # EXISTING: Pre-built template logic
                # Instead of generic replacement, we prepare the context for the AI
                base_template = scenario['template_prompt']
                for k, v in current_selections.items():
                    base_template = base_template.replace(f"[{k}]", v)
                    
                extras = rel_names + pet_names + prop_names
                extras_str = ", ".join(extras) if extras else "background details"
                base_template = base_template.replace("[PROPS_AND_CAST]", extras_str)
                
                # We pass this 'base_template' as the "Scenario Context" to the generator
                custom_scenario = base_template # Renaming for clarity in next step pass
                
                # st.info(f"**Base Context:** {custom_scenario[:100]}...") # Hidden inside form to reduce clutter
                
                final_prompt = custom_scenario # Start with the base scenario
                final_prompt = final_prompt.replace("[RELATION]", current_selections.get("RELATIONS", "friend"))
                final_prompt = final_prompt.replace("[OUTFIT]", current_selections.get("OUTFIT", "casual outfit"))
        
                # Append Custom Details
                if custom_details:
                    final_prompt += f", {custom_details}"
        
                # Append Friend Outfits
                if "FRIEND_OUTFITS" in current_selections:
                     final_prompt += f", {current_selections['FRIEND_OUTFITS']}"
        
                # Append Camera Settings
                cam_details = []
                if sel_camera != "Auto": cam_details.append(f"shot on {sel_camera}")
                if sel_lens != "Auto": cam_details.append(f"{sel_lens} lens")
                if sel_shot != "Auto": cam_details.append(sel_shot) # Restored Logic
                # sel_shot removed in favor of AR + Angle <-- REMOVING THIS COMMENT
                if sel_lighting != "Auto": cam_details.append(f"{sel_lighting} lighting")
                if sel_angle != "Auto": cam_details.append(f"{sel_angle} angle")
                if sel_film != "Auto": cam_details.append(f"{sel_film} style")
                if sel_film_stock != "Auto": cam_details.append(f"Film Stock: {sel_film_stock}")
                if sel_filter_look != "Auto": cam_details.append(f"Look: {sel_filter_look}")
                
                # New Logic
                if sel_emotion != "Auto": cam_details.append(f"Expression: {sel_emotion}")
                if sel_action != "Auto": cam_details.append(f"Action: {sel_action}")
                if sel_hairstyle != "Auto": cam_details.append(f"Hairstyle: {sel_hairstyle}")
                if sel_makeup != "Auto": cam_details.append(f"Makeup: {sel_makeup}")
                if sel_hair_cond != "Auto": cam_details.append(f"Hair: {sel_hair_cond}")
                
                if cam_details:
                    final_prompt += ", " + ", ".join(cam_details)
                    
                # Fallback for Protagonist if replacement failed (e.g. key mismatch)
                if "[PROTAGONIST]" in final_prompt:
                     # Try to find it again or default
                     p_name = current_selections.get("PROTAGONIST", "The Influencer")
                     final_prompt = final_prompt.replace("[PROTAGONIST]", p_name)
    
            # --- DEBUG: INSPECT STATE BEFORE RUNNING AI ---
            # Collapsed by default to avoid confusion
            with st.expander("🛠️ Advanced Debug Info (Inputs)", expanded=False):
                st.write("**Scenario Type:**", "Custom" if is_custom_scenario else "Pre-built Template")
                st.write("**Current Selections:**", current_selections)
                st.write("**Assets (Visual Refs):**", assets_to_inject)
                st.write("**Final Prompt:**", final_prompt)
                st.write("**Session State Keys:**", list(st.session_state.keys()))

            # --- AI DIRECTOR BUTTON ---
            col_ai_btn, col_blank = st.columns([1, 1])
            with col_ai_btn:
                # FORM SUBMIT BUTTON 1
                run_director = st.form_submit_button("Director Vision AI (Generate Prompt)", help="Uses the World-Class Brain to rewrite this into a masterpiece.")
            
            if run_director:
                with st.spinner("Director is rewriting scene..."):
                    
                   # CHECK: Is this a custom scenario? (Use session state flag)
                    use_custom_flow = st.session_state.get('is_custom_scenario', False) and 'custom_scenario_data' in st.session_state

                    if use_custom_flow:
                        # CUSTOM SCENARIO FLOW - Use new detailed Director AI
                        custom_data = st.session_state['custom_scenario_data']
                        
                        # Build comprehensive asset summary
                        assets_summary = f"""Main Character: {custom_data['current_selections'].get('PROTAGONIST', 'character')}
Outfit: {custom_data['current_selections'].get('OUTFIT', 'casual outfit')}
Location: {custom_data['current_selections'].get('LOCATION', 'generic location')}
Cast/Friends: {custom_data['current_selections'].get('RELATIONS', 'nobody')}
Props: {custom_data['current_selections'].get('PROPS', 'none')}
Vibe: {custom_data['current_selections'].get('VIBE', 'neutral')}"""
                        
                        if custom_data['rel_names']:
                            assets_summary += f"\nFriend Outfits: {custom_data['current_selections'].get('FRIEND_OUTFITS', 'casual')}"
                        if custom_data['pet_names']:
                            assets_summary += f"\nPets: {', '.join(custom_data['pet_names'])}"
                        
                        # Build camera settings summary
                        cam_settings = custom_data['camera_settings']
                        camera_summary = []
                        if cam_settings['shot'] != "Auto": camera_summary.append(f"Shot: {cam_settings['shot']}")
                        if cam_settings['angle'] != "Auto": camera_summary.append(f"Angle: {cam_settings['angle']}")
                        if cam_settings['lighting'] != "Auto": camera_summary.append(f"Lighting: {cam_settings['lighting']}")
                        if cam_settings['emotion'] != "Auto": camera_summary.append(f"Emotion: {cam_settings['emotion']}")
                        if cam_settings['action'] != "Auto": camera_summary.append(f"Action: {cam_settings['action']}")
                        if cam_settings['film'] != "Auto": camera_summary.append(f"Style: {cam_settings['film']}")
                        if cam_settings['filter_look'] != "Auto": camera_summary.append(f"Look: {cam_settings['filter_look']}")
                        if cam_settings.get('hairstyle', 'Auto') != "Auto": camera_summary.append(f"Hairstyle: {cam_settings['hairstyle']}")
                        if cam_settings.get('makeup', 'Auto') != "Auto": camera_summary.append(f"Makeup: {cam_settings['makeup']}")
                        if cam_settings.get('hair_condition', 'Auto') != "Auto": camera_summary.append(f"Hair: {cam_settings['hair_condition']}")
                        
                        camera_str = ", ".join(camera_summary) if camera_summary else "natural"
                        
                        # Build Director AI prompt for custom scenario
                        director_prompt = f"""You are a master cinematic prompt writer for photorealistic image generation. Create a rich, immersive, DETAILED scene description.

SCENARIO CONCEPT: {custom_data['scenario_concept']}

CHARACTERS & ASSETS:
{assets_summary}

CAMERA & STYLE: {camera_str}

ADDITIONAL DETAILS: {custom_data['custom_details'] or 'none'}

CRITICAL REQUIREMENTS:
1. Output as a SINGLE flowing paragraph (NO markdown, NO sections, NO code blocks, NO bullet points)
2. Start with "Cinematic 35mm film shot, organic film grain, natural skin pores"
3. Create a VIVID, IMMERSIVE scene - paint the picture with rich visual details
4. Incorporate EVERY asset listed above naturally into the scene
5. Pay special attention to the "ADDITIONAL DETAILS" - these are user-specified and must be included
6. Include specific details about:
   - Character appearances, expressions, and poses
   - Environment atmosphere, lighting quality, and textures
   - Spatial relationships between characters and props
   - Color palette and mood
   - Camera framing and composition
7. Make it feel like a professional film scene - atmospheric, dimensional, alive
8. Length: 4-6 detailed sentences that build a cohesive visual narrative
9. NO explanations, NO justifications - ONLY the direct image prompt

Write an immersive, detailed prompt now:"""
                        
                        try:
                            generated_prompt = None
                            _atlas_key = os.getenv("ATLASCLOUD_API_KEY")
                            if _atlas_key:
                                try:
                                    _headers = {
                                        "Content-Type": "application/json",
                                        "Authorization": f"Bearer {_atlas_key}"
                                    }
                                    _payload = {
                                        "model": "google/gemini-2.5-flash",
                                        "messages": [{"role": "user", "content": director_prompt}],
                                        "temperature": sel_temperature
                                    }
                                    _resp = requests.post("https://api.atlascloud.ai/v1/chat/completions", headers=_headers, json=_payload, timeout=30)
                                    if _resp.status_code == 200:
                                        _res_json = _resp.json()
                                        generated_prompt = _res_json['choices'][0]['message']['content'].strip()
                                except Exception as _atlas_err:
                                    print(f"Atlas Director AI Warning: {_atlas_err}")

                            if not generated_prompt:
                                import google.generativeai as genai
                                _google_key = os.getenv("GOOGLE_API_KEY")
                                if not _google_key:
                                    raise ValueError("ATLASCLOUD_API_KEY or GOOGLE_API_KEY not configured")
                                genai.configure(api_key=_google_key)
                                models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-flash-latest', 'gemini-pro-latest', 'gemini-2.0-flash-001', 'gemini-2.5-pro']
                                response = None
                                last_err = "No models succeeded."
                                for m_name in models_to_try:
                                    try:
                                        model = genai.GenerativeModel(m_name)
                                        response = model.generate_content(director_prompt, generation_config={"temperature": sel_temperature})
                                        break
                                    except Exception as e:
                                        last_err = str(e)
                                        continue
                                if not response:
                                    raise ValueError(f"Generative AI execution failed: {last_err}")
                                generated_prompt = response.text.strip()
                            
                            # Remove any markdown artifacts if present
                            if "```" in generated_prompt:
                                generated_prompt = generated_prompt.replace("```", "").strip()
                            
                            st.session_state['wb_manual_prompt'] = generated_prompt
                            st.success("✨ Custom Scenario Director AI Complete!")
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Director AI error: {e}")
                            # Fallback to simple concatenation
                            fallback = f"{custom_data['scenario_concept']}, {assets_summary.replace(chr(10), ', ')}, {camera_str}"
                            if custom_data['custom_details']:
                                fallback += f", {custom_data['custom_details']}"
                            st.session_state['wb_manual_prompt'] = fallback
                            st.warning("Used fallback prompt generation")
                            st.rerun()
                            
                    else:
                        # PRE-BUILT TEMPLATE FLOW - Use existing visual reference Director AI
                        # 1. Identify Main Assets & Extras

                        main_char_path = None
                        main_outfit_path = None
                        vibe_p = None
                        extras_payload = []
                        
                        for asset in assets_to_inject:
                            lbl = asset.get('label', '')
                            path = asset.get('path')
                            
                            if "Main Character" in lbl:
                                 main_char_path = path
                            elif lbl.startswith("Outfit: "): # Exact main outfit label format
                                 main_outfit_path = path
                            elif lbl == "Location":
                                 vibe_p = path
                            else:
                                 # Friends, Friend Outfits, Pets, Props
                                 extras_payload.append(asset)
                        
                        st.toast(f"Director AI Analyzing: {current_selections.get('PROTAGONIST', 'Character')} + {current_selections.get('OUTFIT', 'Outfit')}... [Cam: {sel_camera}, Act: {sel_action}]")
                    
                        prompt_engine = "gemini-2.0-flash" # User requested specifically (Free Tier)
                        
                        # Extract Active Scenario Details
                        scenario_obj = st.session_state.get('wb_current_scenario', scenario)
                        scen_title = scenario_obj.get('name', 'General Scene') if isinstance(scenario_obj, dict) else 'General Scene'
                        scen_concept = scenario_obj.get('template_prompt', '') if isinstance(scenario_obj, dict) else ''

                        additional_notes_str = (
                            f"SCENARIO TITLE & THEME: '{scen_title}'. "
                            f"SCENARIO CONCEPT: {scen_concept}. "
                            f"ATMOSPHERE/VIBE: {current_selections.get('VIBE', 'General')}. FILM STYLE: {sel_film}. "
                            f"CURRENT DRAFT CONTEXT: {base_template}. "
                            f"INSTRUCTION: Create a fresh, vivid, Hollywood-level scene description specifically for the scenario '{scen_title}'. "
                            f"Integrate all visual references, character identities, outfits, and camera specs smoothly."
                        )

                        # 2. Call Generator with full context
                        enhanced_res = generate_prompt_content(
                            vibe=current_selections.get("VIBE", "luxury"),
                            outfit=current_selections.get("OUTFIT", "fashion"),
                            character=main_char_path, # Pass the PATH
                            outfit_path=main_outfit_path, # Pass the PATH
                            vibe_path=vibe_p, # Pass Location as Image 3 (Vibe Ref)
                            extra_images=extras_payload, # Pass Friends & Extras
                            
                            # Pass Technical Specs Explicitly
                            camera=(sel_camera if sel_camera != "Auto" else None),
                            lens=(sel_lens if sel_lens != "Auto" else None),
                            shot_type=(sel_shot if sel_shot != "Auto" else None),
                            angle=(sel_angle if sel_angle != "Auto" else None),
                            lighting=(sel_lighting if sel_lighting != "Auto" else None),
                            action=(sel_action if sel_action != "Auto" else None),
                            emotion=(sel_emotion if sel_emotion != "Auto" else None),
                            film_stock=(sel_film_stock if sel_film_stock != "Auto" else None),
                            filter_look=(sel_filter_look if sel_filter_look != "Auto" else None),
                            
                            additional_notes=additional_notes_str,
                            model_engine=prompt_engine # Use currently selected brain (Gemini 2.0)
                        )
                        
                        if enhanced_res and "positive_prompt" in enhanced_res:
                            # final_prompt = enhanced_res["positive_prompt"] <--- REMOVED to prevent conflict with change detector
                            st.session_state['wb_manual_prompt'] = enhanced_res["positive_prompt"]
                            # Draft state remains unchanged, so the box won't auto-revert
                            st.success("🎬 Director Cut Generated! (See Box Below)")
                            time.sleep(1) # Pause to let user see
                            st.rerun()
    
            # --- STATE MANAGEMENT FOR PROMPT BOX ---
            # We need the box to update when:
            # 1. Dropdowns change (Calculated prompt changes)
            # 2. AI Button is clicked (AI rewrites prompt)
            # 3. User types (Manual edit)
            
            # --- STATE MANAGEMENT FOR PROMPT BOX (FIXED) ---
            # We must track the "Draft" state separately to avoid overwriting AI output
            
            if 'last_draft_state' not in st.session_state:
                st.session_state['last_draft_state'] = final_prompt
            
            # 1. Did the Dropdowns change? (Compare current calculated draft vs last known draft)
            if final_prompt != st.session_state['last_draft_state']:
                 # Dropdowns changed -> Reset box to new draft
                 st.session_state['wb_manual_prompt'] = final_prompt
                 st.session_state['last_draft_state'] = final_prompt
            
            # Initialize key if needed
            if 'wb_manual_prompt' not in st.session_state:
                 st.session_state['wb_manual_prompt'] = final_prompt
    
            # Make Prompt Editable
            final_prompt_val = st.text_area("Final Prompt (Editable)", key="wb_manual_prompt", height=200)
            final_prompt = final_prompt_val
            
            st.markdown("<br>", unsafe_allow_html=True)
            wb_queue = st.checkbox("Add to Campaign Queue", key="wb_queue_check")
            # FORM SUBMIT BUTTON (Generate)
            gen_world = st.form_submit_button("Generate Single Scene", type="primary", use_container_width=True)

    # --- ACTION AREA (Outside Form) ---
    st.divider()
    col_act1, col_act2 = st.columns(2)
    
    with col_act1:
        st.markdown("#### 📸 Quick Shot")
        
        # Generation Logic triggered by Form Submit
        if gen_world:
             # Re-resolve main character path from assets just in case
             main_char_path = None
             for a in assets_to_inject:
                 if "Main Character" in a.get('label', ''):
                     main_char_path = a.get('path')
                     break

             # Check Queue Mode
             if st.session_state.get("wb_queue_check"):
                 campaign_mgr.add_job(
                    name=f"WB_Scene_{int(time.time())}",
                    description="World Builder Scene",
                    prompt_data={
                        "positive_prompt": final_prompt,
                        "aspect_ratio": sel_ar,
                        "image_size": sel_res,
                        "model_type": "nano",
                        "assets": assets_to_inject
                    },
                    settings={"batch_count": 1},
                    output_folder=get_user_out_dir("World"),
                    char_path=main_char_path
                 )
                 st.success("✅ Added Scene to Campaign Queue!")
                 
             else:
                 can_proceed = True
                 if st.session_state.get("authenticated"):
                     username = st.session_state.current_user.get("username")
                     if not auth_mgr.deduct_credits(username, 1):
                         st.error("❌ Not enough credits!")
                         can_proceed = False
                     else:
                         st.toast("🪙 1 Credit Deducted")
                 
                 if can_proceed:

                     # Magic UI Progress
                     prog_ph = st.empty()
                     # from execution.magic_ui import circular_progress
                     with prog_ph.container():
                          circular_progress()
                          st.caption("Generating...")
                     
                     wb_payload = {
                         "positive_prompt": final_prompt,
                         "aspect_ratio": sel_ar, 
                         "image_size": sel_res,
                         "model_type": "nano", 
                         "assets": assets_to_inject
                     }
                     res = generate_image_from_prompt(wb_payload, get_user_out_dir("World"))
                     
                     prog_ph.empty() # Clear Progress
                     
                     with st.expander("Generation Logs", expanded=False):
                         st.code(res.get("logs", "No logs"))
                         
                     if res["status"] == "success":
                         st.session_state['wb_last_img'] = res["image_path"]
                         if st.session_state.get("authenticated"):
                             time.sleep(0.5)
                             st.rerun()
                     else:
                         # Refund Logic
                         username = st.session_state.current_user.get("username")
                         auth_mgr.add_credits(username, 1)
                         st.error(f"Generation Failed: {res.get('logs')}")
                         st.toast("Credit Refunded")

        # Display Result (Persistent)
        if 'wb_last_img' in st.session_state and os.path.exists(st.session_state['wb_last_img']):
            last_img = st.session_state['wb_last_img']
            st.image(last_img, caption="World Build Result", use_container_width=True)
            
            with open(last_img, "rb") as f:
                st.download_button("⬇️ Download Image", f, file_name=os.path.basename(last_img), mime="image/png")
            
            # Save to Assets Button
            st.divider()
            with st.form("wb_save_asset"):
                c_n, c_s = st.columns([2, 1])
                with c_n:
                    asset_name = st.text_input("Name this Asset", placeholder="e.g. My Beach House")
                with c_s:
                    save_asset = st.form_submit_button("📁 Save to Assets", use_container_width=True)
                
                if save_asset:
                    if asset_name and st.session_state.get("authenticated"):
                        user = st.session_state.current_user.get("username")
                        res = promote_image_to_asset(last_img, user, "Locations", asset_name, final_prompt)
                        if res["status"] == "success":
                            st.success(f"Added to Locations!")
                            st.info(res.get("logs", ""))
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Save Failed: {res.get('error')}")
                    else:
                        st.error("Please provide a name.")
    
    with col_act2:
            st.markdown("#### 🎞️ Storyboard Generator")
            if st.button("Draft Storyboard (4 Shots)"):
                with st.spinner("AI Director is writing script..."):
                    # Extract Camera Settings for Context
                    camera_settings_summary = []
                    if sel_camera != "Auto": camera_settings_summary.append(f"Shot: {sel_camera}")
                    if sel_lens != "Auto": camera_settings_summary.append(f"Lens: {sel_lens}")
                    if sel_shot != "Auto": camera_settings_summary.append(f"Shot Type: {sel_shot}")
                    if sel_angle != "Auto": camera_settings_summary.append(f"Angle: {sel_angle}")
                    if sel_lighting != "Auto": camera_settings_summary.append(f"Lighting: {sel_lighting}")
                    if sel_film_stock != "Auto": camera_settings_summary.append(f"Film Stock: {sel_film_stock}")
                    if sel_filter_look != "Auto": camera_settings_summary.append(f"Look: {sel_filter_look}")
                    camera_str = ", ".join(camera_settings_summary) if camera_settings_summary else ""

                    # Extract Asset Labels for Context
                    asset_labels = [a.get('label', 'Unknown Asset') for a in assets_to_inject]
                    reference_context_str = ", ".join(asset_labels) if asset_labels else ""

                    # Pass the FULL prompt + specs as context
                    scen_name = scenario.get('name', 'Custom Scenario') if isinstance(scenario, dict) else str(scenario)
                    sb_prompts = generate_storyboard_prompts(
                        scen_name, 
                        final_prompt,
                        camera_settings=camera_str,
                        reference_context=reference_context_str
                    )
                    st.session_state['sb_prompts'] = sb_prompts
                    if sb_prompts and isinstance(sb_prompts, list) and len(sb_prompts) > 0 and not str(sb_prompts[0]).startswith("Error"):
                        st.success("Storyboard Drafted! See below.")
                    else:
                        st.error(f"Generation failed: {sb_prompts[0] if sb_prompts else 'Unknown error'}")
            
            if 'sb_prompts' in st.session_state:
                prompts = st.session_state['sb_prompts']
                edited_prompts = []
                
                # --- BATCH CONTROL ---
                c_sb_q, c_sb_run = st.columns([1, 1])
                
                # Re-resolve main char for logic usage
                main_char_path_sb = None
                for a in assets_to_inject:
                     if "Main Character" in a.get('label', ''):
                         main_char_path_sb = a.get('path')
                         break

                with c_sb_q:
                    if st.button("Add All to Queue"):
                         curr_idx = len(campaign_mgr.queue)
                         for i, p in enumerate(prompts):
                             active_p = st.session_state.get(f"sb_{i}", p)
                             campaign_mgr.add_job(
                                name=f"SB_Shot_{i+1}_{int(time.time())}",
                                description=f"Storyboard Shot {i+1}",
                                prompt_data={
                                    "positive_prompt": active_p, 
                                    "aspect_ratio": sel_ar,
                                    "image_size": sel_res,
                                    "model_type": "nano",
                                    "assets": assets_to_inject
                                },
                                settings={"batch_count": 1},
                                output_folder=get_user_out_dir("Storyboard"),
                                char_path=main_char_path_sb
                             )
                         st.success(f"Added {len(prompts)} shots to Queue!")
                         
                with c_sb_run:
                    if st.button("🎬 Generate All"):
                         for i, p in enumerate(prompts):
                             active_p = st.session_state.get(f"sb_{i}", p)
                             # Credit Check Loop
                             can_proceed = True
                             if st.session_state.get("authenticated"):
                                 username = st.session_state.current_user.get("username")
                                 if not auth_mgr.deduct_credits(username, 1):
                                     st.error(f"❌ Not enough credits to generate Shot {i+1}!")
                                     can_proceed = False
                                     break # Stop generation
                             
                             if can_proceed:
                                 with st.spinner(f"Generating Shot {i+1}..."):
                                     wb_payload = {
                                         "positive_prompt": active_p, # Use active text
                                         "aspect_ratio": sel_ar, 
                                         "image_size": sel_res,
                                         "model_type": "nano", 
                                         "assets": assets_to_inject
                                     }
                                 res = generate_image_from_prompt(wb_payload, get_user_out_dir("Storyboard"))
                                 if res["status"] == "success":
                                     st.toast(f"Shot {i+1} Generated! (-1 Credit)")
                                     st.session_state[f"sb_img_{i}"] = res["image_path"] # Saved!
                                 else:
                                     st.error(f"Shot {i+1} Failed")
                                     # Refund 
                                     username = st.session_state.current_user.get("username")
                                     auth_mgr.add_credits(username, 1)
                                     st.toast(f"Shot {i+1} Refunded")
                         
                         if st.session_state.get("authenticated"):
                             st.rerun() # Verify update

                for i, p in enumerate(prompts):
                    col_sb_text, col_sb_img = st.columns([2, 1])
                    
                    with col_sb_text:
                        val = st.text_area(f"Shot {i+1}", value=p, height=100, key=f"sb_{i}")
                        edited_prompts.append(val)
                        
                        if st.button(f"Generate Shot {i+1}", key=f"btn_sb_{i}"):
                            # Credit Check
                            can_proceed = True
                            if st.session_state.get("authenticated"):
                                username = st.session_state.current_user.get("username")
                                if not auth_mgr.deduct_credits(username, 1):
                                    st.error("❌ Not enough credits!")
                                    can_proceed = False
                                else:
                                    st.toast("🪙 1 Credit Deducted")
                            
                            if can_proceed:
                                with st.spinner("Rolling camera..."):
                                    wb_payload = {
                                         "positive_prompt": val, # Use edited text
                                         "aspect_ratio": sel_ar, 
                                         "image_size": sel_res,
                                         "model_type": "nano", 
                                         "assets": assets_to_inject
                                     }
                                    res = generate_image_from_prompt(wb_payload, get_user_out_dir("Storyboard"))
                                    with st.expander(f"Logs Shot {i+1}", expanded=False):
                                         st.code(res.get("logs", "No logs"))
                                         
                                    if res["status"] == "success":
                                        st.session_state[f"sb_img_{i}"] = res["image_path"]
                                        if st.session_state.get("authenticated"):
                                            time.sleep(1)
                                            st.rerun()
                                    else:
                                        st.error(res["logs"])
                    
                    with col_sb_img:
                        if f"sb_img_{i}" in st.session_state:
                             img_path = st.session_state[f"sb_img_{i}"]
                             st.image(img_path, use_container_width=True)
                             if os.path.exists(img_path):
                                 with open(img_path, "rb") as f:
                                     st.download_button(
                                         "⬇️ Save", 
                                         f, 
                                         file_name=os.path.basename(img_path),
                                         mime="image/png",
                                         key=f"dl_sb_{i}"
                                     )
                
                st.divider()
                if st.button("Add Storyboard to Campaign Queue", type="primary"):
                    # Capture current assets state
                    import copy
                    current_assets = copy.deepcopy(assets_to_inject)
                    
                    count = 0
                    for i, p in enumerate(edited_prompts):
                        # Construct Prompt Data (New Schema)
                        p_data = {
                            "positive_prompt": p + f", {final_prompt}",
                            "aspect_ratio": sel_ar,
                            "image_size": sel_res,
                            "model_type": "nano",
                            "assets": current_assets
                        }
                        
                        campaign_mgr.add_job(
                            name=f"Storyboard Shot {i+1}",
                            description=f"Scene: {scenario.get('name', 'Custom')}",
                            prompt_data=p_data,
                            settings={"batch_count": 1},
                            output_folder=get_user_out_dir("Campaign")
                        )
                        count += 1
                    
                    st.success(f"Added {count} shots to Campaign Queue! Go to 'Campaign Queue' tab to run them.")



# ==========================================
# ==========================================
if selection == "Campaign Queue":
    with st.container():
        st.markdown("### Campaign Manager")
        
        # Sync with Backend
        st.session_state.campaign_queue = campaign_mgr.queue
        
        pending_count = len([x for x in st.session_state.campaign_queue if x['status'] == 'pending'])
        
        st.metric("Pending Jobs", pending_count)

        # ── AUTO-PLAN CAMPAIGN (New Agentic Feature) ────────────────────────
        with st.expander("🤖 Auto-Plan Campaign", expanded=(pending_count == 0)):
            st.markdown(
                "**Describe your content goal in plain English.** "
                "The AI Director will generate a full content calendar and queue all jobs automatically."
            )
            ac_brief = st.text_area(
                "Campaign Brief",
                placeholder="e.g. 30 days of luxury lifestyle content for Shay — rooftop moments, travel vibes, and editorial fashion",
                height=80,
                key="ac_brief"
            )
            ac_col1, ac_col2, ac_col3 = st.columns([2, 1, 1])
            with ac_col1:
                ac_num_posts = st.slider("Number of Posts", min_value=5, max_value=30, value=10, step=1, key="ac_num_posts")
            with ac_col2:
                ac_character = st.text_input("Lock Character (optional)", placeholder="Shay", key="ac_character")
            with ac_col3:
                ac_plan_btn = st.button("✨ Generate Plan", type="primary", key="ac_plan_btn", use_container_width=True)

            if ac_plan_btn:
                if not ac_brief.strip():
                    st.warning("Please enter a campaign brief.")
                else:
                    with st.spinner(f"Planning {ac_num_posts} posts..."):
                        try:
                            from execution.plan_campaign import plan_campaign, build_campaign_job
                            planned_posts = plan_campaign(
                                ac_brief.strip(),
                                num_posts=ac_num_posts,
                                character=ac_character.strip() if ac_character.strip() else None
                            )
                            st.session_state.ac_planned_posts = planned_posts
                        except Exception as plan_err:
                            st.error(f"Planning failed: {plan_err}")
                            st.session_state.ac_planned_posts = []

            # Preview Table + Queue All
            if "ac_planned_posts" in st.session_state and st.session_state.ac_planned_posts:
                posts = st.session_state.ac_planned_posts
                st.success(f"✅ {len(posts)} posts planned. Review below then queue them all.")

                import pandas as pd
                preview_df = pd.DataFrame([{
                    "#": p["post_number"],
                    "Name": p["name"],
                    "Character": p["character"],
                    "Vibe / Scenario": p["vibe"],
                    "Outfit": p["outfit"][:40] + "..." if len(p.get("outfit", "")) > 40 else p.get("outfit", ""),
                    "Ratio": p["aspect_ratio"],
                    "Day": p["day_of_week"]
                } for p in posts])
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

                if st.button("⚡ Queue All", type="primary", key="ac_queue_all"):
                    from execution.plan_campaign import build_campaign_job
                    queued_count = 0
                    username_ac = st.session_state.current_user.get("username", "guest")
                    out_dir_ac = get_user_out_dir("Campaign")
                    for post_plan in posts:
                        job_kwargs = build_campaign_job(post_plan, out_dir_ac, username_ac)
                        campaign_mgr.add_job(**job_kwargs)
                        queued_count += 1
                    st.session_state.ac_planned_posts = []
                    st.success(f"✅ {queued_count} jobs added to the queue!")
                    st.rerun()
        # ────────────────────────────────────────────────────────────────────
    
        # 2. Controls - Auto-Advancing with Stop Capability
        if "campaign_running" not in st.session_state:
            st.session_state.campaign_running = False
    
        col_run, col_stop, col_clear = st.columns([1, 1, 4])
        
        with col_run:
            # Run Button
            if st.button("RUN", type="primary", disabled=st.session_state.campaign_running or pending_count == 0):
                st.session_state.campaign_running = True
                st.rerun()
    
        with col_stop:
            # Stop Button
            if st.button("STOP", disabled=not st.session_state.campaign_running):
                st.session_state.campaign_running = False
                st.warning("Stopping after current task...")
                st.rerun()
                
        with col_clear:
            if st.button("Clear All"):
                campaign_mgr.clear_queue()
                st.rerun()
    
        # --- PROCESSOR LOGIC ---
        if st.session_state.campaign_running:
            status_box = st.empty()
            
            # Check for next job
            job = campaign_mgr.get_next_pending_job()
            
            if job:
                status_box.info(f"Processing: {job['name']}...")
                
                # Execute (Blocking for 1 job)
                try:
                    campaign_mgr.process_job(job)
                    st.toast(f"Finished: {job['name']}")
                    st.rerun() # Loop for next
                except Exception as e:
                    st.error(f"Job Failed: {e}")
                    st.session_state.campaign_running = False
            else:
                status_box.success("All Jobs Completed.")
                st.session_state.campaign_running = False
    

# ==========================================
# TAB: ART DIRECTOR (NL Brief + Voice Dictation)
# ==========================================
if selection == "Art Director":
    with st.container():
        st.markdown("### 🎨 Art Director")
        st.markdown(
            "Describe the shot you want in plain language — or record your brief with your voice. "
            "The AI maps your words to your assets and generates the image."
        )

        # ── Voice Dictation ─────────────────────────────────────────────────
        st.markdown("#### 🎙️ Speak Your Brief (Optional)")
        try:
            ad_audio = st.audio_input("Hold to record, release to transcribe", key="ad_audio_input_widget")
            if ad_audio is not None:
                # Hash-guard: only transcribe when audio content is new
                # Without this, every widget interaction rerenders → re-transcribes → loop
                audio_bytes = ad_audio.read()
                audio_hash = hash(audio_bytes)
                if st.session_state.get("ad_last_audio_hash") != audio_hash:
                    st.session_state["ad_last_audio_hash"] = audio_hash
                    with st.spinner("Transcribing..."):
                        try:
                            from execution.transcribe_voice import transcribe_voice
                            transcription = transcribe_voice(audio_bytes)
                            if transcription:
                                st.session_state["ad_brief_input"] = transcription
                                st.success(f'🎙️ I heard: *"{transcription}"*')
                            else:
                                st.warning("No audio detected — please try again or type your brief below.")
                        except Exception as voice_err:
                            st.warning(f"Transcription unavailable: {voice_err}")

        except Exception:
            st.caption("🎙️ Mic not available in this browser — type your brief below.")

        # ── Text Brief ──────────────────────────────────────────────────────
        st.markdown("#### ✏️ Your Brief")
        ad_brief = st.text_area(
            "Describe the shot",
            placeholder="e.g. moody rooftop bar at night, Shay in a sleek black dress, editorial and cinematic",
            height=100,
            key="ad_brief_input"   # voice dictation writes directly to this key
        )

        ad_parse_btn = st.button("🧠 Parse Brief", type="primary", key="ad_parse_btn")

        if ad_parse_btn:
            with st.spinner("Mapping brief to your assets..."):
                try:
                    from execution.parse_intent import parse_intent
                    parsed = parse_intent(ad_brief.strip())
                    st.session_state.ad_parsed = parsed

                    # ── Force-write ALL widget state keys BEFORE next render ──────────
                    # Streamlit ignores `index=` / `value=` params once a key exists
                    # in session_state, so we must set them here, immediately after parse.

                    def _resolve_char_key_seed(name: str):
                        name_lower = name.lower().strip()
                        # 1. Exact name-field match
                        for k, v in characters_data.items():
                            cname = v.get("name", k) if isinstance(v, dict) else k
                            if cname.lower() == name_lower:
                                return k
                        # 2. Exact key match
                        for k in characters_data:
                            if k.lower() == name_lower:
                                return k
                        # 3. Partial name-field match (handles "(My) Dudlow" → "Dudlow")
                        for k, v in characters_data.items():
                            cname = v.get("name", k) if isinstance(v, dict) else k
                            if name_lower in cname.lower() or cname.lower().startswith(name_lower):
                                return k
                        # 4. Partial key match (handles path-style keys like
                        #    "Shay Stock Photo / Shay High Bun Front" → matches "shay")
                        for k in characters_data:
                            if name_lower in k.lower():
                                return k
                        return None

                    parsed_names = parsed.get("characters", [])

                    # Primary character selectbox
                    primary_key_seed = _resolve_char_key_seed(parsed_names[0]) if parsed_names else None
                    if primary_key_seed and primary_key_seed in characters_list:
                        st.session_state["ad_primary_char"] = primary_key_seed
                    elif characters_list:
                        st.session_state["ad_primary_char"] = characters_list[0]

                    # Additional cast multiselect
                    secondary_names_seed = parsed_names[1:]
                    auto_keys = [_resolve_char_key_seed(n) for n in secondary_names_seed]
                    auto_keys = [k for k in auto_keys if k and k in characters_data]
                    st.session_state["ad_additional_cast"] = auto_keys

                    # Vibe / scenario
                    if parsed.get("vibe"):
                        st.session_state["ad_vibe_edit"] = parsed["vibe"]

                    # Aspect ratio
                    ratio = parsed.get("aspect_ratio", "9:16")
                    if ratio in ["9:16", "1:1", "16:9"]:
                        st.session_state["ad_ratio"] = ratio

                    # Primary outfit — fuzzy-match against outfit_opts
                    outfit_opts_seed = list(outfits_data.keys())
                    parsed_outfit_lower = parsed.get("outfit", "").lower()
                    if parsed_outfit_lower and outfit_opts_seed:
                        outfit_match = next(
                            (ok for ok in outfit_opts_seed
                             if any(word in ok.lower() for word in parsed_outfit_lower.split()[:3])),
                            None
                        )
                        if outfit_match:
                            st.session_state["ad_primary_outfit"] = outfit_match

                    # Additional notes
                    if parsed.get("additional_notes"):
                        st.session_state["ad_notes"] = parsed["additional_notes"]

                except Exception as parse_err:
                    st.error(f"Parsing failed: {parse_err}")
                    st.session_state.ad_parsed = None


        # ── Parsed Result + Scene Builder ────────────────────────────────────
        if "ad_parsed" in st.session_state and st.session_state.ad_parsed:
            parsed = st.session_state.ad_parsed
            confidence = parsed.get("confidence", "low")
            conf_icon = {"high": "✅", "medium": "⚠️", "low": "❓"}.get(confidence, "❓")

            st.markdown(f"#### {conf_icon} Scene Setup — Confidence: `{confidence.upper()}`")
            st.info("Review and edit fields before generating. Add multiple characters — each gets its own outfit.")



            # ── Primary Character + Outfit ──────────────────────────────────
            st.markdown("##### 🌟 Primary Character")

            # Resolve primary character from parsed characters list
            parsed_char_names = parsed.get("characters", [parsed.get("character", "Shay")])
            primary_name = parsed_char_names[0] if parsed_char_names else "Shay"

            def _resolve_char_key(name: str):
                """Find the characters_data key that best matches a character name string."""
                name_lower = name.lower().strip()
                for k, v in characters_data.items():
                    cname = v.get("name", k) if isinstance(v, dict) else k
                    if cname.lower() == name_lower:
                        return k
                for k, v in characters_data.items():
                    cname = v.get("name", k) if isinstance(v, dict) else k
                    if name_lower in cname.lower() or cname.lower() in name_lower:
                        return k
                return None

            primary_key = _resolve_char_key(primary_name)

            pc_col1, pc_col2, pc_col3 = st.columns([2, 2, 1])
            with pc_col1:
                char_idx = characters_list.index(primary_key) if primary_key and primary_key in characters_list else 0
                ad_primary_char = st.selectbox("Character", characters_list, index=char_idx, key="ad_primary_char")

            with pc_col2:
                # Primary outfit — dropdown from asset library
                outfit_opts = list(outfits_data.keys())
                parsed_outfit_text = parsed.get("outfit", "").lower()
                outfit_match_idx = 0
                if parsed_outfit_text:
                    for i, ok in enumerate(outfit_opts):
                        if any(word in ok.lower() for word in parsed_outfit_text.split()[:3]):
                            outfit_match_idx = i
                            break
                if outfit_opts:
                    ad_primary_outfit_key = st.selectbox(
                        "Outfit", outfit_opts, index=outfit_match_idx, key="ad_primary_outfit"
                    )
                else:
                    ad_primary_outfit_key = None
                    st.text_input("Outfit Description", value=parsed_outfit_text, key="ad_primary_outfit_text")

            with pc_col3:
                pchar_val = characters_data.get(ad_primary_char, {})
                pchar_path = pchar_val.get("default_img") if isinstance(pchar_val, dict) else None
                if pchar_path and os.path.exists(str(pchar_path)):
                    st.image(pchar_path, use_container_width=True)

            # ── Additional Cast ─────────────────────────────────────────────
            st.markdown("##### 👥 Additional Cast (Optional)")
            cast_pool_ad = {k: v for k, v in characters_data.items() if k != ad_primary_char}

            # ad_additional_cast was pre-seeded in the parse button handler above
            additional_cast_keys = st.multiselect(
                "Add more characters to the scene",
                options=sorted(cast_pool_ad.keys()),
                format_func=lambda x: cast_pool_ad[x].get("name", x) if isinstance(cast_pool_ad[x], dict) else x,
                key="ad_additional_cast"
            )


            # Per-character outfit selectors (one column per extra cast member)
            extra_cast_outfits = {}   # {char_key: outfit_key}
            if additional_cast_keys:
                st.caption("Select an outfit for each cast member:")
                cast_outfit_cols = st.columns(len(additional_cast_keys))
                for idx, char_key in enumerate(additional_cast_keys):
                    char_val_ex = cast_pool_ad.get(char_key, {})
                    char_name_ex = char_val_ex.get("name", char_key) if isinstance(char_val_ex, dict) else char_key
                    char_path_ex = char_val_ex.get("default_img") if isinstance(char_val_ex, dict) else None
                    with cast_outfit_cols[idx]:
                        st.markdown(f"**{char_name_ex}**")
                        if char_path_ex and os.path.exists(str(char_path_ex)):
                            st.image(char_path_ex, use_container_width=True)
                        if outfit_opts:
                            ex_outfit_key = st.selectbox(
                                f"Outfit", outfit_opts, key=f"ad_extra_outfit_{idx}"
                            )
                        else:
                            ex_outfit_key = st.text_input(f"Outfit", key=f"ad_extra_outfit_text_{idx}")
                        extra_cast_outfits[char_key] = ex_outfit_key

            # ── Vibe, Ratio, Resolution, Notes ──────────────────────────────
            st.markdown("##### 🌆 Scene Details")
            sd_col1, sd_col2, sd_col3 = st.columns([3, 2, 2])
            with sd_col1:
                ad_vibe_edit = st.text_input("Vibe / Scenario", value=parsed.get("vibe", ""), key="ad_vibe_edit")
            with sd_col2:
                ad_ratio = st.selectbox(
                    "Aspect Ratio",
                    ["9:16", "1:1", "16:9"],
                    index=["9:16", "1:1", "16:9"].index(parsed.get("aspect_ratio", "9:16")),
                    key="ad_ratio"
                )
            with sd_col3:
                ad_resolution = st.selectbox(
                    "Resolution",
                    ["1K", "2K", "4K", "512px"],
                    index=0,
                    key="ad_resolution",
                    help="512px = fast draft • 1K = standard • 2K/4K = high quality (slower)"
                )

            ad_notes = st.text_input(
                "Additional Notes",
                value=parsed.get("additional_notes", ""),
                placeholder="Extra mood, lighting, or style direction",
                key="ad_notes"
            )

            st.divider()
            ad_gen_btn = st.button("🎬 Generate Image", type="primary", key="ad_gen_btn", use_container_width=True)

            if ad_gen_btn:
                # Resolve primary character
                pchar_val = characters_data.get(ad_primary_char, {})
                pchar_path = pchar_val.get("default_img") if isinstance(pchar_val, dict) else None

                # Resolve primary outfit
                primary_outfit_path = None
                primary_outfit_name = ""
                if ad_primary_outfit_key and outfit_opts:
                    pfit_val = outfits_data.get(ad_primary_outfit_key, {})
                    primary_outfit_name = pfit_val.get("name", ad_primary_outfit_key) if isinstance(pfit_val, dict) else ad_primary_outfit_key
                    primary_outfit_path = pfit_val.get("default_img") if isinstance(pfit_val, dict) else pfit_val

                # Build extra_images list for multi-cast
                ad_extra_images = []
                for char_key in additional_cast_keys:
                    char_val_ex = cast_pool_ad.get(char_key, {})
                    char_name_ex = char_val_ex.get("name", char_key) if isinstance(char_val_ex, dict) else char_key
                    char_path_ex = char_val_ex.get("default_img") if isinstance(char_val_ex, dict) else None
                    if char_path_ex:
                        ad_extra_images.append({"path": char_path_ex, "label": f"Cast: {char_name_ex}"})
                    # Attach their outfit
                    ex_outfit_key = extra_cast_outfits.get(char_key)
                    if ex_outfit_key and outfit_opts:
                        ex_fit_val = outfits_data.get(ex_outfit_key, {})
                        ex_fit_name = ex_fit_val.get("name", ex_outfit_key) if isinstance(ex_fit_val, dict) else ex_outfit_key
                        ex_fit_path = ex_fit_val.get("default_img") if isinstance(ex_fit_val, dict) else ex_fit_val
                        if ex_fit_path:
                            ad_extra_images.append({"path": ex_fit_path, "label": f"Outfit for {char_name_ex}: {ex_fit_name}"})

                with st.spinner("Crafting prompt and generating image..."):
                    try:
                        prompt_data = generate_prompt_content(
                            vibe=ad_vibe_edit or ad_notes,
                            outfit=primary_outfit_name,
                            character=pchar_path or ad_primary_char,
                            outfit_path=primary_outfit_path,
                            additional_notes=ad_notes,
                            aspect_ratio=ad_ratio,
                            extra_images=ad_extra_images if ad_extra_images else None
                        )
                        # Inject resolution into prompt_data so generate_image picks it up
                        prompt_data["image_size"] = ad_resolution

                        out_dir_ad = get_user_out_dir("ArtDirector")
                        result = generate_image_from_prompt(
                            prompt_data,
                            output_folder=out_dir_ad,
                            reference_image_path=pchar_path
                        )

                        if result.get("status") == "success":
                            st.image(result["image_path"], use_container_width=True)
                            st.success("Image generated successfully!")
                            # Reset parsed state after success
                            st.session_state.ad_parsed = None
                            st.session_state.ad_brief = ""
                        else:
                            st.error(f"Generation failed: {result.get('logs', 'Unknown error')}")
                    except Exception as gen_err:
                        st.error(f"Error during generation: {gen_err}")

# ==========================================
# ==========================================
# TAB: VIDEO STUDIO
# ==========================================
if selection == "Video Studio":
    with st.container():
        st.markdown("### AI Video Generator (Kling 2.6 / Veo 2.0)")
        st.info("Transform your generated images into high-motion video clips using the latest 2026 models.")
    
    # Sub-tabs for Creation vs Gallery
    v_tab_create, v_tab_gallery = st.tabs(["Generate Video", "Video Gallery (Recover)"])
    
    with v_tab_gallery:
        # Use User Isolated Directory
        vid_dir = get_user_out_dir("Videos")
        
        st.markdown(f"#### Generated Videos (Folder: `{os.path.basename(vid_dir)}`)")
        
        if not os.path.exists(vid_dir):
             st.warning(f"No video folder found at {vid_dir}")
        else:
             # Find MP4s
             videos = [f for f in os.listdir(vid_dir) if f.endswith(".mp4")]
             videos.sort(key=lambda x: os.path.getmtime(os.path.join(vid_dir, x)), reverse=True)
             
             if not videos:
                 st.info("No videos found yet.")
             else:
                 for vid in videos:
                     vid_path = os.path.join(vid_dir, vid)
                     
                     with st.expander(f"- {vid}", expanded=True):
                         c1, c2 = st.columns([3, 1])
                         with c1:
                             st.video(vid_path)
                         with c2:
                             st.markdown("**Actions**")
                             with open(vid_path, "rb") as vf:
                                 st.download_button(
                                     f"Download MP4",
                                     data=vf,
                                     file_name=vid,
                                     mime="video/mp4",
                                     key=f"dl_{vid}"
                                 )
                             st.caption(f"Size: {os.path.getsize(vid_path)/1024/1024:.1f}MB")

    with v_tab_create:
        with st.form(key="video_form"):
            # Model Selection
            video_model = st.selectbox(
                "Engine", 
                [
                    "Kling AI 2.6 (Professional)", 
                    "HuMo AI (Human Motion Premium)",
                    "Seedance 2.0 (Reference-to-Video)",
                    "Seedance 2.0 Mini (Reference-to-Video)",
                    "Seedance 2.0 (Image-to-Video)",
                    "Seedance 2.0 (Text-to-Video)",
                    "Wan 2.7 (Image-to-Video)",
                    "Wan 2.7 Spicy (Image-to-Video)",
                    "Wan 2.7 (Reference-to-Video)",
                    "Wan 2.7 Spicy (Reference-to-Video)"
                ], 
                key="vid_model_select"
            )
            
            col_v_in, col_v_set = st.columns([1, 1])
        
            with col_v_in:
                st.markdown("**1. Select Input Image**")
                # Allow uploading OR selecting from recent outputs (mockup for now)
                video_source_img = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="vid_in_img")
                
                if video_source_img:
                    st.image(video_source_img, caption="Input Preview", use_container_width=True)
                
                st.markdown("**2. Motion Settings**")
                col_mv, col_phy = st.columns(2)
                with col_mv:
                    vid_movement = st.selectbox("Camera Move", ["Auto", "Pan Left", "Pan Right", "Zoom In", "Zoom Out", "Handheld", "Drone Orbit"], key="vid_move")
                with col_phy:
                    vid_physics = st.selectbox("Physics Focus", ["Standard", "High Physics", "Jiggle Physics", "Water/Liquids"], help="Enforce specific physics simulations.")
                    
                motion_prompt = st.text_area("Motion Prompt", height=100, placeholder="Describe the movement...", key="vid_prompt_text")
                
                # NOTE: Auto-Generate Vision AI button inside Form acts as Submit. 
                # This is tricky. We'll disable it or move it out if problematic.
                # Actually, submit buttons can distinguish themselves.
                auto_vis = st.form_submit_button("Auto-Generate with Vision AI")
                
                if auto_vis:
                     # ... (Vision logic)
                     # Since this is a submit, it will rerun. We need to handle logic conditionally.
                     # However, generating video is also a submit.
                     # We can't have both run.
                     pass # We will handle logic below outside form? No, inside form but check bools.

            # Settings Column (Dynamic)
            with col_v_set:
                ref_video_url = None
                ref_orientation = "image"
                if "Kling" in video_model:
                    st.info("⚡ Engine: **Kling AI 2.6** (Professional)")
                    
                    col_dur, col_qual = st.columns(2)
                    with col_dur:
                        duration = st.selectbox("Duration", ["5s", "10s"])
                    with col_qual:
                        quality = st.selectbox("Quality Mode", ["Professional (High Quality, Slower)", "Standard (Fast, Efficient)"])
                        
                    # Advanced Model Override
                    with st.expander("Advanced Model Settings (Override)", expanded=False):
                         model_version_input = st.text_input("Kling Model Version", value="2.6", help="Code auto-converts '2.6' to 'kling-v2-6'.")
                         st.caption("Available: `2.6` (Latest), `1.6` (Stable), `1.5`.")
                         
                         st.divider()
                         st.markdown("**Cinematic Overrides (Prompt Injection)**")
                         v_stock = st.selectbox("Film Stock", ["None"] + knowledge_base.get("film_stocks", []), key="vid_stock")
                         v_filter = st.selectbox("Filter / Look", ["None"] + knowledge_base.get("filters", []), key="vid_filter")
                         v_movie_style = st.selectbox("Movie Reference", ["None"] + knowledge_base.get("movie_styles", []), key="vid_style")
                         
                         st.markdown("**Action & Transition**")
                         c_act, c_trans = st.columns(2)
                         with c_act:
                             # Actions relevant for video
                             vid_actions = ["None", "Slow Motion Walk", "Turning Head", "Running", "Dancing", "Talking", "Laughing", "Fighting", "Driving", "Flying", "Explosion", "Wind blowing hair"]
                             v_action = st.selectbox("Subject Action", vid_actions, key="vid_action_override")
                         with c_trans:
                             v_trans = st.selectbox("Transition In", ["None"] + knowledge_base.get("transitions", []), key="vid_trans")
    
                    mode_val = "pro" if "Professional" in quality else "std"
                    
                    # Camera Controls
                    camera_data = None
                    with st.expander("Camera & Motion Control", expanded=False):
                         enable_camera = st.checkbox("Enable Camera Control", value=False)
                         if enable_camera:
                             st.caption("Values range from -10 to 10.")
                             c1, c2 = st.columns(2)
                             with c1:
                                  h_val = st.slider("Horizontal (X)", -10.0, 10.0, 0.0, step=0.5, help="Neg: Left, Pos: Right")
                                  v_val = st.slider("Vertical (Y)", -10.0, 10.0, 0.0, step=0.5, help="Neg: Down, Pos: Up")
                                  z_val = st.slider("Zoom", -10.0, 10.0, 0.0, step=0.5, help="Neg: In, Pos: Out")
                             with c2:
                                  pan_val = st.slider("Pan (Rotate V)", -10.0, 10.0, 0.0, step=0.5, help="Neg: Down, Pos: Up")
                                  tilt_val = st.slider("Tilt (Rotate H)", -10.0, 10.0, 0.0, step=0.5, help="Neg: Left, Pos: Right")
                                  roll_val = st.slider("Roll", -10.0, 10.0, 0.0, step=0.5, help="Neg: CCW, Pos: CW")
                             
                             camera_data = {
                                 "type": "simple",
                                 "config": {
                                     "horizontal": h_val,
                                     "vertical": v_val,
                                     "pan": pan_val,
                                     "tilt": tilt_val,
                                     "roll": roll_val,
                                     "zoom": z_val
                                 }
                             }
    
                    # Motion Transfer (Video Reference)
                    st.divider()
                    st.markdown("**Video Driven Motion**")
                    
                    m_tab1, m_tab2 = st.tabs(["URL Input", "Upload Video"])
                    
                    with m_tab1:
                        url_input = st.text_input("Reference Video URL (S3/Public)", help="Paste an `http` URL to a video. Overrides Camera Control.")
                        if url_input: ref_video_url = url_input
                        
                    with m_tab2:
                        st.info("⚠️ **Constraint:** Video must be **≤ 30 seconds** and **< 100MB**.")
                        uploaded_vid = st.file_uploader("Upload Reference Video", type=['mp4', 'mov'])
                        if uploaded_vid:
                             # Size Check (100MB)
                             if uploaded_vid.size > 100 * 1024 * 1024:
                                  st.error(f"File too large ({uploaded_vid.size / 1024 / 1024:.1f}MB). Max 100MB.")
                             else:
                                  with st.spinner("Uploading to S3..."):
                                       # Check if already uploaded in session to avoid re-upload
                                       if 'last_uploaded_vid_name' not in st.session_state or st.session_state['last_uploaded_vid_name'] != uploaded_vid.name:
                                            s3_url = upload_file_obj(uploaded_vid, f"user_uploads/{uploaded_vid.name}")
                                            if s3_url:
                                                 st.session_state['last_uploaded_vid_url'] = s3_url
                                                 st.session_state['last_uploaded_vid_name'] = uploaded_vid.name
                                                 st.success("✅ Uploaded!")
                                            else:
                                                 st.error("Upload failed.")
                                       
                                       if 'last_uploaded_vid_url' in st.session_state:
                                            ref_video_url = st.session_state['last_uploaded_vid_url']
                                            st.caption(f"Using: `{ref_video_url}`")
                    
                    if ref_video_url:
                         st.warning("⚠️ Motion Control Mode Active: Camera settings will be ignored.")
                         # Orientation Logic
                         st.markdown("##### 📐 Match Orientation To:")
                         orient_choice = st.radio(
                             "Orientation Source",
                             ["Image (Best for Style, Max 10s)", "Video (Best for Action, Max 30s)"],
                             help="If your video is >10s, you MUST select 'Video'.",
                             label_visibility="collapsed"
                         )
                         ref_orientation = "video" if "Video" in orient_choice else "image"
    
                elif "HuMo" in video_model:
                    st.info("⚡ Engine: **HuMo AI** (Human Motion)")
                    st.warning("Requires REPLICATE_API_TOKEN. High cost per second (~$0.01/s).")
                    
                    st.markdown("**3. Audio Control (Lip Sync)**")
                    humo_audio = st.file_uploader("Upload Audio (Optional)", type=["mp3", "wav"], help="Add audio to sync motion or lips.")
                    
                    st.markdown("**4. Advanced Settings**")
                    h_steps = st.slider("Inference Steps", 10, 100, 50, help="More steps = higher quality (and cost).")
                    h_guidance = st.slider("Text Guidance", 2.0, 15.0, 5.0)
                    h_audio_guidance = st.slider("Audio Guidance", 2.0, 15.0, 5.5)
                    
                elif "Wan" in video_model:
                    st.info("⚡ Engine: **Wan 2.7 (Atlas Cloud API)**")
                    if "Spicy" in video_model:
                         if "Reference-to-Video" in video_model:
                              st.warning("🔥 spicy mode enabled: Model alibaba/wan-2.7/reference-to-video will be called with no guardrails.")
                         else:
                              st.warning("🔥 spicy mode enabled: Model alibaba/wan-2.7/image-to-video will be called with no guardrails.")
                    
                    col_wan_res, col_wan_ar, col_wan_dur = st.columns(3)
                    with col_wan_res:
                        wan_studio_res = st.selectbox("Resolution", ["1080P", "720P"], index=0, key="studio_wan_res")
                    with col_wan_ar:
                        wan_studio_ar = st.selectbox("Aspect Ratio", ["16:9 (Widescreen)", "9:16 (Vertical / Reels)", "1:1 (Square)"], index=0, key="studio_wan_ar")
                    with col_wan_dur:
                        wan_studio_dur = st.slider("Duration (seconds)", 2, 15, 5, key="studio_wan_dur")
                        
                    if "Reference-to-Video" in video_model:
                        st.markdown("**Video Driven Motion (Reference)**")
                        
                        # Character Swap / Motion Keep Toggle for Video Studio
                        wan_studio_char_swap = st.checkbox(
                            "🔄 Keep Video Motion (Character Swap)", 
                            value=False, 
                            key="wan_video_studio_char_swap",
                            help="If enabled, this will strictly preserve the motion, background, and physics from the reference video, and swap the character identity with the input image. (Requires reference video to be named Video1 and input image to be named Image1 in your prompt)."
                        )
                        
                        m_tab1, m_tab2 = st.tabs(["URL Input", "Upload Video"])
                        
                        with m_tab1:
                            url_input = st.text_input("Reference Video URL (S3/Public)", key="wan_ref_url_input", help="Paste an `http` URL to a video.")
                            if url_input: ref_video_url = url_input
                            
                        with m_tab2:
                            st.info("⚠️ **Constraint:** Video must be **≤ 30 seconds** and **< 100MB**.")
                            uploaded_vid = st.file_uploader("Upload Reference Video", type=['mp4', 'mov'], key="wan_ref_uploader")
                            if uploaded_vid:
                                 if uploaded_vid.size > 100 * 1024 * 1024:
                                      st.error(f"File too large ({uploaded_vid.size / 1024 / 1024:.1f}MB). Max 100MB.")
                                 else:
                                      with st.spinner("Uploading to S3..."):
                                           if 'last_uploaded_vid_name' not in st.session_state or st.session_state['last_uploaded_vid_name'] != uploaded_vid.name:
                                                s3_url = upload_file_obj(uploaded_vid, f"user_uploads/{uploaded_vid.name}")
                                                if s3_url:
                                                     st.session_state['last_uploaded_vid_url'] = s3_url
                                                     st.session_state['last_uploaded_vid_name'] = uploaded_vid.name
                                                     st.success("✅ Uploaded!")
                                                else:
                                                     st.error("Upload failed.")
                                           
                                           if 'last_uploaded_vid_url' in st.session_state:
                                                ref_video_url = st.session_state['last_uploaded_vid_url']
                                                st.caption(f"Using: `{ref_video_url}`")
                                                
                        with st.expander("📸 Seedance 2.0 Multi-Subject Reference Lock (Up to 9 Reference Images & 4 Videos)", expanded=True):
                             st.markdown(
                                 "Reference these subjects in your prompt as `Image1`, `Image2`, `Image3` ... `Image9`, and `Video1`, `Video2`, `Video3`, `Video4`.\n"
                                 "*(Image1 is your main input image above; Video1 is your main reference video above)*"
                             )
                             
                             # Option A: Quick Multi-File Bulk Upload
                             st.file_uploader(
                                 "📁 Quick Bulk Upload (Select up to 8 additional reference images at once)",
                                 type=["png", "jpg", "jpeg", "webp"],
                                 accept_multiple_files=True,
                                 key="v_wan_extra_imgs_bulk",
                                 help="Select multiple images from your computer at once. They will automatically populate slots Image2 through Image9."
                             )
                             
                             st.markdown("--- **or Upload / Assign Slots Individually (Image 2 through Image 9)** ---")
                             
                             c_img_a, c_img_b = st.columns(2)
                             with c_img_a:
                                 st.file_uploader("Upload Image 2 (Image2)", type=["png", "jpg", "jpeg", "webp"], key="v_wan_extra_img2")
                                 st.file_uploader("Upload Image 3 (Image3)", type=["png", "jpg", "jpeg", "webp"], key="v_wan_extra_img3")
                                 st.file_uploader("Upload Image 4 (Image4)", type=["png", "jpg", "jpeg", "webp"], key="v_wan_extra_img4")
                                 st.file_uploader("Upload Image 5 (Image5)", type=["png", "jpg", "jpeg", "webp"], key="v_wan_extra_img5")
                             with c_img_b:
                                 st.file_uploader("Upload Image 6 (Image6)", type=["png", "jpg", "jpeg", "webp"], key="v_wan_extra_img6")
                                 st.file_uploader("Upload Image 7 (Image7)", type=["png", "jpg", "jpeg", "webp"], key="v_wan_extra_img7")
                                 st.file_uploader("Upload Image 8 (Image8)", type=["png", "jpg", "jpeg", "webp"], key="v_wan_extra_img8")
                                 st.file_uploader("Upload Image 9 (Image9)", type=["png", "jpg", "jpeg", "webp"], key="v_wan_extra_img9")
                                 
                             st.markdown("--- **Video Motion / Camera Choreography References (Video 2 through Video 4)** ---")
                             c_vid_a, c_vid_b = st.columns(2)
                             with c_vid_a:
                                 st.file_uploader("Upload Video 2 (Video2)", type=["mp4", "mov"], key="v_wan_extra_vid2")
                                 st.file_uploader("Upload Video 3 (Video3)", type=["mp4", "mov"], key="v_wan_extra_vid3")
                             with c_vid_b:
                                 st.file_uploader("Upload Video 4 (Video4)", type=["mp4", "mov"], key="v_wan_extra_vid4")
    
            st.divider()
            
            gen_video_btn = st.form_submit_button("Generate Video", type="primary")

        # LOGIC HANDLERS (Outside Form, triggered by vars)
        if auto_vis:
            if not video_source_img:
                st.error("Upload an image to analyze.")
            elif not os.getenv("GOOGLE_API_KEY"):
                st.error("Missing GOOGLE_API_KEY for Vision Analysis.")
            else:
                prog_ph = st.empty()
                # from execution.magic_ui import circular_progress
                with prog_ph.container():
                     circular_progress()
                     st.caption("Analyzing Context...")
                
                # Save temp
                temp_path = os.path.join("output", "temp_vision_input.png")
                with open(temp_path, "wb") as f:
                    f.write(video_source_img.getbuffer())
                    
                current_typed_prompt = st.session_state.get("vid_prompt_text", "")
                suggestion = generate_motion_prompt(
                    temp_path, 
                    movement_type=vid_movement, 
                    physics_focus=vid_physics,
                    additional_context=f"User's Scene Idea / Actions: {current_typed_prompt}" if current_typed_prompt else ""
                )
                st.session_state["motion_suggestion"] = suggestion
                st.rerun()

        if "motion_suggestion" in st.session_state:
             # This part is tricky. 'Apply Suggestion' button cannot be outside form targeting inside form.
             # We just show text.
             st.info(f"💡 Suggestion: {st.session_state['motion_suggestion']}")

        if gen_video_btn:
            user = st.session_state.current_user.get("username")
            if not auth_mgr.deduct_credits(user, 5):
                st.error("❌ Need 5 Credits for Video!")
            elif not video_source_img:
                st.error("Please upload an image first.")
            else:
                with st.status("Generating Video...", expanded=True) as status:
                    # Save uploaded file momentarily
                    temp_path = os.path.join("output", "temp_video_input.png")
                    with open(temp_path, "wb") as f:
                        f.write(video_source_img.getbuffer())
                    
                    # INJECT STYLE PROMPT
                    final_motion_prompt = motion_prompt
                    
                    # Only check these keys if they exist (which they do if Kling selected, but safe to check)
                    v_stock_val = None
                    v_filter_val = None
                    
                    # Hacky access to scoped variables? No, need to use st.session_state or re-read
                    if "vid_stock" in st.session_state and st.session_state["vid_stock"] != "None":
                        final_motion_prompt += f", Shot on {st.session_state['vid_stock']}"
                    if "vid_filter" in st.session_state and st.session_state["vid_filter"] != "None":
                        final_motion_prompt += f", {st.session_state['vid_filter']} look"
                    if "vid_style" in st.session_state and st.session_state["vid_style"] != "None":
                        final_motion_prompt += f", {st.session_state['vid_style']}"
                    if "vid_action_override" in st.session_state and st.session_state["vid_action_override"] != "None":
                        final_motion_prompt += f", Action: {st.session_state['vid_action_override']}"
                    if "vid_trans" in st.session_state and st.session_state["vid_trans"] != "None":
                         # Transitions often work best as camera instructions
                        final_motion_prompt += f", {st.session_state['vid_trans']} transition"
                    
                    st.caption(f"Final Prompt: {final_motion_prompt}")

                    result = None
                    
                    if "Kling" in video_model:
                        if not (os.getenv("KLING_ACCESS_KEY") and os.getenv("KLING_SECRET_KEY")):
                             st.error("Missing KLING_ACCESS_KEY/SECRET.")
                             status.update(label="Failed", state="error")
                        else:
                             st.write(f"Sending to Kling AI 2.6 API ({mode_val.upper()} Mode)...")
                             st.write("Processing... (Standard: ~2-5m, Pro: ~5-10m)")
                             
                             result = generate_video_kling(
                                 temp_path, 
                                 final_motion_prompt, 
                                 duration=5, 
                                 model_version=model_version_input, 
                                 quality_mode=mode_val, 
                                 camera_control=camera_data,
                                 ref_video_path=ref_video_url,
                                 ref_orientation=ref_orientation,
                                 output_folder=get_user_out_dir("Videos")
                             )
                    
                    elif "HuMo" in video_model:
                         if not os.getenv("REPLICATE_API_TOKEN"):
                              st.error("Missing REPLICATE_API_TOKEN.")
                              status.update(label="Failed", state="error")
                         else:
                              st.write("Sending to Replicate (HuMo)...")
                              st.write("Processing on 8x H100 GPU (Est ~1-2 mins)...")

                              # Use local temp path - generate_video_humo will upload it securely via Replicate client
                              humo_img_input = temp_path
                              
                              # Handle Audio
                              humo_audio_input = None
                              if humo_audio:
                                  # Save audio locally
                                  audio_path = os.path.join("output", "temp_audio_input.mp3")
                                  with open(audio_path, "wb") as fa:
                                      fa.write(humo_audio.getbuffer())
                                  humo_audio_input = audio_path
                              
                              result = generate_video_humo(
                                  humo_img_input,
                                  final_motion_prompt,
                                  audio_path=humo_audio_input,
                                  num_inference_steps=h_steps,
                                  guidance_scale=h_guidance,
                                  audio_guidance_scale=h_audio_guidance,
                                  output_folder=get_user_out_dir("Videos")
                              )
                              
                    elif "Wan" in video_model or "Seedance" in video_model:
                        target_engine = "alibaba/wan-2.7/image-to-video"
                        if "Mini" in video_model:
                            target_engine = "bytedance/seedance-2.0-mini/reference-to-video"
                        elif "Seedance" in video_model and "Reference" in video_model:
                            target_engine = "bytedance/seedance-2.0/reference-to-video"
                        elif "Seedance" in video_model and "Image" in video_model:
                            target_engine = "bytedance/seedance-2.0/image-to-video"
                        elif "Seedance" in video_model and "Text" in video_model:
                            target_engine = "bytedance/seedance-2.0/text-to-video"
                        elif "Reference-to-Video" in video_model:
                            target_engine = "alibaba/wan-2.7/reference-to-video"
                        
                        engine_name_display = "Seedance 2.0" if "Seedance" in video_model else "Wan 2.7"
                        st.write(f"Sending to {engine_name_display} Video API via Atlas Cloud...")
                        st.write("Animate-to-Video in progress... (Est ~2-3 mins)")
                        
                        # Fetch values from session state safely
                        w_res = st.session_state.get("studio_wan_res", "1080P")
                        w_dur = st.session_state.get("studio_wan_dur", 5)
                        
                        extra_imgs = []
                        extra_vids = []
                        
                        if "Reference-to-Video" in video_model or "Seedance" in video_model:
                             # 1. Process Quick Bulk Uploaded Reference Images
                             bulk_uploads = st.session_state.get("v_wan_extra_imgs_bulk", [])
                             if bulk_uploads:
                                 for idx, b_file in enumerate(bulk_uploads[:8]):
                                     b_path = os.path.join("output", f"temp_wan_bulk_ex_img_{idx+2}.png")
                                     with open(b_path, "wb") as f:
                                         f.write(b_file.getbuffer())
                                     if b_path not in extra_imgs and len(extra_imgs) < 8:
                                         extra_imgs.append(b_path)

                             # 2. Process Slot-by-Slot Reference Images (Image 2 through Image 9)
                             for slot_idx in range(2, 10):
                                 w_slot_file = st.session_state.get(f"v_wan_extra_img{slot_idx}")
                                 if w_slot_file:
                                     slot_path = os.path.join("output", f"temp_wan_ex_img{slot_idx}.png")
                                     with open(slot_path, "wb") as f:
                                         f.write(w_slot_file.getbuffer())
                                     if slot_path not in extra_imgs and len(extra_imgs) < 8:
                                         extra_imgs.append(slot_path)
                                         
                             # 3. Process Reference Videos (Video 2 through Video 4)
                             for slot_v_idx in range(2, 5):
                                 w_vid_file = st.session_state.get(f"v_wan_extra_vid{slot_v_idx}")
                                 if w_vid_file:
                                     v_slot_path = os.path.join("output", f"temp_wan_ex_vid{slot_v_idx}.mp4")
                                     with open(v_slot_path, "wb") as f:
                                         f.write(w_vid_file.getbuffer())
                                     if v_slot_path not in extra_vids and len(extra_vids) < 3:
                                         extra_vids.append(v_slot_path)
                                  
                        final_motion_payload_prompt = final_motion_prompt
                        if "Reference-to-Video" in video_model and st.session_state.get("wan_video_studio_char_swap"):
                             # Append instructions to enforce motion transfer swap and identity locking
                             final_motion_payload_prompt = (
                                  "Strict Character Swap: Lock character identity to Image1. "
                                  "Transfer all environment details, lighting, physics, frame timing, and motion strictly from Video1. "
                                  "Keep the actions identical to Video1, but swap the character with Image1. "
                                  f"Context: {final_motion_prompt}"
                             )
                             
                        result = generate_wan_video(
                            prompt=final_motion_payload_prompt,
                            image_path=temp_path,
                            resolution=w_res,
                            duration=w_dur,
                            aspect_ratio=st.session_state.get("studio_wan_ar", "16:9").split(" ")[0],
                            ref_video_path=ref_video_url,
                            extra_images=extra_imgs if extra_imgs else None,
                            extra_videos=extra_vids if extra_vids else None,
                            model=target_engine,
                            output_folder=get_user_out_dir("Videos")
                        )

                    # Common Result Handling
                    if result:
                        if result["status"] == "success":
                            status.update(label="Complete!", state="complete")
                            
                            if result.get("warning"):
                                 st.warning(result["warning"])
                            else:
                                 st.success(f"Video Generated! (Task ID: {result.get('task_id', 'N/A')})")
                            
                            if result.get('video_path'):
                                 st.success(f"💾 Saved to: {result['video_path']}")
                                 
                            if result.get('video_url'):
                                st.write(f"**Direct Link:** [Click to Open]({result.get('video_url')})")
                                st.video(result.get('video_url'))
                                
                                if result.get('video_path') and os.path.exists(result['video_path']):
                                    with open(result['video_path'], "rb") as v_file:
                                        st.download_button(
                                            label="⬇️ Download MP4",
                                            data=v_file,
                                            file_name=os.path.basename(result['video_path']),
                                            mime="video/mp4"
                                        )
                            else:
                                if "video_path" in result and result["video_path"]:
                                     # Local file existed but no URL?
                                     st.video(result["video_path"])
                                else:
                                     st.warning("Video URL/Path not found.")
                                
                            with st.expander("Process Logs", expanded=False):
                                st.write(result.get("logs", []))
                        else:
                            status.update(label="Failed", state="error")
                            st.error(f"Error: {result.get('error')}")
                            with st.expander("Error Logs", expanded=True):
                                 st.write(result.get("logs", []))


# ==========================================
# TAB: WAN & SEEDANCE STUDIO (Atlas Cloud API)
# ==========================================
if selection == "Wan & Seedance Studio":
    with st.container():
        st.markdown("### Wan & Seedance Studio (Atlas Cloud API)")
        st.info("Edit your scene images and animate them using the latest Wan 2.7 & Seedance 2.0 models on Atlas Cloud.")

    # Check for authentication
    username = st.session_state.current_user.get("username") if st.session_state.get("authenticated") else "guest"
    
    # Initialize session state for subtab radio if not present
    if "wan_studio_subtab_radio" not in st.session_state:
        st.session_state.wan_studio_subtab_radio = "Image-to-Image (Scene Editor)"

    w_mode = st.radio(
        "Select Studio Tool",
        ["Image-to-Image (Scene Editor)", "Image-to-Video (Motion)"],
        horizontal=True,
        key="wan_studio_subtab_radio"
    )
    
    if w_mode == "Image-to-Image (Scene Editor)":
        st.markdown("#### Wan 2.7 Image-to-Image Editor")
        st.write("Modify the wardrobe, location, lighting, or style of your generated images.")
        
        # 🎭 CHARACTER, OUTFIT & ENVIRONMENT MAPPING RIG
        rig_edit_res = render_wan_asset_mapping_rig(prefix_key="wan_edit", prompt_target_key="wan_edit_prompt")
        
        # Select image source
        src_option = st.radio("Image Source", ["Shortcut (from Mapping Rig)", "Shortcut (from Gallery)", "Upload custom image"], horizontal=True, key="wan_edit_source_option")
        
        edit_image_path = None
        if src_option == "Shortcut (from Mapping Rig)":
            if rig_edit_res["primary_image_path"]:
                target_rig_img = rig_edit_res["primary_image_path"]
                st.info(f"Using primary image from Mapping Rig: `{os.path.basename(str(target_rig_img))}`")
                if os.path.exists(str(target_rig_img)):
                    st.image(target_rig_img, width=300)
                edit_image_path = target_rig_img
            else:
                st.warning("No image selected in Mapping Rig above. Pick a character, outfit, or location in the rig above.")
        elif src_option == "Shortcut (from Gallery)":
            if st.session_state.wan_edit_image:
                st.info(f"Using image from gallery shortcut: `{os.path.basename(st.session_state.wan_edit_image)}`")
                st.image(st.session_state.wan_edit_image, width=300)
                edit_image_path = st.session_state.wan_edit_image
            else:
                st.warning("No shortcut image selected. Go to 'My Gallery' and click '✏️ Edit' on an image, or upload a custom image.")
        else:
            uploaded_edit_img = st.file_uploader("Upload Image to Edit", type=["png", "jpg", "jpeg"], key="wan_edit_uploader")
            if uploaded_edit_img:
                temp_edit_path = os.path.join("output", "temp_wan_edit_input.png")
                with open(temp_edit_path, "wb") as f:
                    f.write(uploaded_edit_img.getbuffer())
                st.image(uploaded_edit_img, width=300)
                edit_image_path = temp_edit_path
                
        # Extra Reference Images (for clothing, locations, multi-subject)
        extra_ref_paths = list(rig_edit_res["extra_ref_paths"])
        with st.expander("🎨 Multi-Subject / Clothing & Location References (Optional Uploads / URLs)", expanded=False):
            st.markdown("Add up to 8 additional reference images (e.g. clothing reference, face reference, background style reference) to guide the Wan edit.")
            
            ref_input_mode = st.radio("Reference Source Mode", ["Upload Files", "URLs (S3/Web)"], horizontal=True, key="wan_edit_ref_mode")
            if ref_input_mode == "Upload Files":
                uploaded_refs = st.file_uploader(
                    "Upload Reference Images (Max 8)",
                    type=["png", "jpg", "jpeg", "webp"],
                    accept_multiple_files=True,
                    key="wan_edit_uploaded_refs"
                )
                if uploaded_refs:
                    for i, file_obj in enumerate(uploaded_refs[:8]):
                        temp_ref_path = os.path.join("output", f"temp_wan_ref_{i}.png")
                        with open(temp_ref_path, "wb") as f:
                            f.write(file_obj.getbuffer())
                        if temp_ref_path not in extra_ref_paths:
                            extra_ref_paths.append(temp_ref_path)
                    st.success(f"Loaded {len(uploaded_refs[:8])} local upload reference images.")
            else:
                url_text = st.text_area(
                    "Reference URLs (One per line)",
                    placeholder="https://example.com/outfit.jpg\nhttps://example.com/location.jpg",
                    key="wan_edit_ref_urls"
                )
                if url_text.strip():
                    lines = [line.strip() for line in url_text.split("\n") if line.strip()]
                    for u_line in lines[:8]:
                        if u_line not in extra_ref_paths:
                            extra_ref_paths.append(u_line)
                    st.success(f"Registered {len(lines[:8])} reference URLs.")

        edit_prompt = st.text_area("Edit Prompt (SOP instructions)", placeholder="e.g. Change the background to a sunny Malibu beach. Change her outfit to a red leather jacket and black jeans. Keep character identity identical.", key="wan_edit_prompt")
        edit_size = st.selectbox("Resolution", ["2K", "1K"], index=0, key="wan_edit_size")
        
        run_edit_btn = st.button("Generate Edited Image", type="primary", key="wan_run_edit")
        
        if run_edit_btn:
            if not edit_image_path:
                st.error("Please provide a source image.")
            elif not edit_prompt:
                st.error("Please describe what changes you want to make.")
            else:
                user = st.session_state.current_user.get("username")
                if not auth_mgr.deduct_credits(user, 3):
                    st.error("❌ Need 3 Credits for Wan 2.7 Editing!")
                else:
                    with st.status("Submitting job to Atlas API...", expanded=True) as status:
                        st.write("Uploading and running alibaba/wan-2.7-pro/image-edit...")
                        
                        out_dir = get_user_out_dir("World")
                        res = generate_wan_image(
                            prompt=edit_prompt,
                            image_path=edit_image_path,
                            size=edit_size,
                            output_folder=out_dir,
                            extra_images=extra_ref_paths
                        )
                        
                        if res and res["status"] == "success":
                            status.update(label="Complete!", state="complete")
                            st.success("✅ Image generated and saved to your Gallery!")
                            st.image(res["image_path"], caption="Edited Scene Output", use_container_width=True)
                            
                            # Option to send immediately to motion generator
                            if st.button("🎬 Send to Animate", key="send_to_animate_from_edit"):
                                st.session_state.wan_animate_image = res["image_path"]
                                st.session_state.wan_studio_subtab_radio = "Image-to-Video (Motion)"
                                st.rerun()
                        else:
                            status.update(label="Failed", state="error")
                            st.error(f"Error: {res.get('error', 'Unknown error')}")
                            with st.expander("Logs", expanded=True):
                                st.write(res.get("logs", []))

    else:
        st.markdown("#### Wan & Seedance Video Motion Generator")
        st.write("Animate your edited scene image or generate cinematic video clips from scratch.")
        
        # 🎭 CHARACTER, OUTFIT & ENVIRONMENT MAPPING RIG
        rig_anim_res = render_wan_asset_mapping_rig(prefix_key="wan_anim", prompt_target_key="wan_anim_prompt")
        
        # Read selected model flavor to check if Text-to-Video
        model_flavor_val = st.session_state.get("wan_studio_flavor_select", "Wan 2.7 Standard (Image-to-Video)")
        is_txt_to_vid = "Text-to-Video" in model_flavor_val
        
        anim_image_path = None
        if is_txt_to_vid:
            st.info("ℹ️ **Text-to-Video Mode Selected**: No input image is required. Video will be generated purely from your Motion Prompt.")
        else:
            # Select image source
            anim_src_option = st.radio("Image Source", ["Shortcut (from Mapping Rig)", "Shortcut (from Gallery or Editor)", "Upload custom image"], horizontal=True, key="wan_anim_source_option")
            
            if anim_src_option == "Shortcut (from Mapping Rig)":
                if rig_anim_res["primary_image_path"]:
                    target_p = rig_anim_res["primary_image_path"]
                    st.info(f"Using image from Mapping Rig: `{os.path.basename(str(target_p))}`")
                    if os.path.exists(str(target_p)):
                        st.image(target_p, width=300)
                    anim_image_path = target_p
                else:
                    st.warning("No image selected in Mapping Rig above. Pick a character, outfit, or location in the rig above.")
            elif anim_src_option == "Shortcut (from Gallery or Editor)":
                if st.session_state.wan_animate_image:
                    target_p = st.session_state.wan_animate_image
                    # If it's a signed S3 URL but we have a matching local file under output/ or user/ directories:
                    if target_p.startswith(("http://", "https://")) and "users/" in target_p:
                         try:
                              # Extract local path from S3 layout structure: users/admin/World/filename.jpg
                              local_rel = target_p.split(".amazonaws.com/")[1].split("?")[0]
                              local_abs = os.path.join("output", local_rel)
                              if os.path.exists(local_abs):
                                   target_p = local_abs
                         except Exception:
                              pass
                    st.info(f"Using image from shortcut: `{os.path.basename(target_p)}`")
                    st.image(target_p, width=300)
                    anim_image_path = target_p
                else:
                    st.warning("No shortcut image selected. Go to 'My Gallery' and click '🎬 Animate' on an image, or run the editor above.")
            else:
                uploaded_anim_img = st.file_uploader("Upload Image to Animate", type=["png", "jpg", "jpeg"], key="wan_anim_uploader")
                if uploaded_anim_img:
                    temp_anim_path = os.path.join("output", "temp_wan_anim_input.png")
                    with open(temp_anim_path, "wb") as f:
                        f.write(uploaded_anim_img.getbuffer())
                    st.image(uploaded_anim_img, width=300)
                    anim_image_path = temp_anim_path
                
        # Director Vision AI Generator for Wan
        if anim_image_path:
            st.markdown("---")
            st.markdown("#### 🪄 Director Vision AI Prompt Generator")
            st.caption("Let Gemini analyze your scene composition and generate a custom cinematography prompt.")
            
            vis_col1, vis_col2, vis_col3 = st.columns(3)
            with vis_col1:
                wan_vis_move = st.selectbox(
                    "Desired Movement", 
                    ["Auto", "Pan Left/Right", "Zoom In/Out", "Dolly Shot", "Handheld Close-up", "Slow Drone Orbit"], 
                    key="wan_vis_move"
                )
            with vis_col2:
                wan_vis_physics = st.selectbox(
                    "Dynamics Focus", 
                    ["Standard", "Wind Dynamics (hair/fabric)", "High Motion (action/dance)", "Fluid Dynamics (liquids)"], 
                    key="wan_vis_physics"
                )
            with vis_col3:
                wan_vis_style = st.selectbox(
                    "Cinematic Style", 
                    ["Film Scene (Moody)", "High Action (Kinetic)", "Portrait Study (Emotions)", "Surreal (Dreamlike)"], 
                    key="wan_vis_style"
                )
                
            if st.button("🪄 Analyze & Suggest Prompt", key="wan_run_vision_ai", use_container_width=True):
                if not os.getenv("GOOGLE_API_KEY"):
                    st.error("Missing GOOGLE_API_KEY for Vision Analysis.")
                else:
                    with st.spinner("🎬 Director AI is analyzing your image composition..."):
                        from execution.generate_video_prompt import generate_motion_prompt
                        
                        current_typed_prompt = st.session_state.get("wan_anim_prompt", "")
                        additional_context_str = f"Render style guideline: {wan_vis_style}."
                        if current_typed_prompt:
                            additional_context_str += f" User's scene idea/action: {current_typed_prompt}"
                            
                        suggestion = generate_motion_prompt(
                            anim_image_path,
                            movement_type=wan_vis_move,
                            physics_focus=wan_vis_physics,
                            emotion="Dynamic",
                            additional_context=additional_context_str
                        )
                        st.session_state["wan_vision_ai_suggestion"] = suggestion
                        
            if "wan_vision_ai_suggestion" in st.session_state:
                st.info(f"💡 **Director AI Prompt Suggestion:**\n\n{st.session_state['wan_vision_ai_suggestion']}")
                
                c_apply, c_clear = st.columns(2)
                with c_apply:
                    if st.button("✅ Apply to Motion Prompt Box", key="wan_apply_vis_suggestion", use_container_width=True):
                        st.session_state.wan_anim_prompt = st.session_state["wan_vision_ai_suggestion"]
                        del st.session_state["wan_vision_ai_suggestion"]
                        st.rerun()
                with c_clear:
                    if st.button("❌ Dismiss", key="wan_clear_vis_suggestion", use_container_width=True):
                        del st.session_state["wan_vision_ai_suggestion"]
                        st.rerun()
            st.markdown("---")
            
        wan_model_flavor = st.selectbox(
            "Model Variant",
            [
                "Wan 2.7 Standard (Image-to-Video)", 
                "Wan 2.7 Spicy (Image-to-Video)",
                "Wan 2.7 Standard (Reference-to-Video)",
                "Wan 2.7 Spicy (Reference-to-Video)",
                "Seedance 2.5 (Reference-to-Video - Up to 50 Refs)",
                "Seedance 2.5 (Image-to-Video)",
                "Seedance 2.5 (Text-to-Video)",
                "Seedance 2.0 (Reference-to-Video)",
                "Seedance 2.0 Mini (Reference-to-Video)",
                "Seedance 2.0 (Image-to-Video)",
                "Seedance 2.0 (Text-to-Video)"
            ],
            index=0,
            key="wan_studio_flavor_select"
        )
        
        if "2.5" in wan_model_flavor:
            st.info("⚡ **Seedance 2.5 Active**: Supports up to **50 Multimodal References** (`Image1`..`Image50`), native 30s clips & 4K resolution. Atlas Cloud API rate: **$0.134/sec** (Cost Forecast: ~$0.67 for 5s | ~$1.34 for 10s | ~$4.02 for 30s). Uses **10 Credits**.")
        
        ref_video_url = None
        wan_char_swap = False
        if "Reference-to-Video" in wan_model_flavor:
            st.markdown("**Video Driven Motion (Reference)**")
            
            # Character Swap / Motion Keep Toggle
            wan_char_swap = st.checkbox(
                "🔄 Keep Video Motion (Character Swap)", 
                value=False, 
                help="If enabled, this will strictly preserve the motion, background, and physics from the reference video, and swap the character identity with the input image. (Requires reference video to be named Video1 and input image to be named Image1 in your prompt)."
            )
            
            m_tab1, m_tab2 = st.tabs(["URL Input", "Upload Video"])
            
            with m_tab1:
                url_input = st.text_input("Reference Video URL (S3/Public)", key="wan_studio_ref_url_input", help="Paste an `http` URL to a video.")
                if url_input: ref_video_url = url_input
                
            with m_tab2:
                st.info("⚠️ **Constraint:** Video must be **≤ 30 seconds** and **< 100MB**.")
                uploaded_vid = st.file_uploader("Upload Reference Video", type=['mp4', 'mov'], key="wan_studio_ref_uploader")
                if uploaded_vid:
                     if uploaded_vid.size > 100 * 1024 * 1024:
                          st.error(f"File too large ({uploaded_vid.size / 1024 / 1024:.1f}MB). Max 100MB.")
                     else:
                          with st.spinner("Uploading to S3..."):
                               if 'last_uploaded_vid_name' not in st.session_state or st.session_state['last_uploaded_vid_name'] != uploaded_vid.name:
                                    s3_url = upload_file_obj(uploaded_vid, f"user_uploads/{uploaded_vid.name}")
                                    if s3_url:
                                         st.session_state['last_uploaded_vid_url'] = s3_url
                                         st.session_state['last_uploaded_vid_name'] = uploaded_vid.name
                                         st.success("✅ Uploaded!")
                                    else:
                                         st.error("Upload failed.")
                               
                               if 'last_uploaded_vid_url' in st.session_state:
                                    ref_video_url = st.session_state['last_uploaded_vid_url']
                                    st.caption(f"Using: `{ref_video_url}`")
                                    
            ref_limit_label = "50 Reference Images & 10 Videos" if "2.5" in wan_model_flavor else "9 Reference Images & 4 Videos"
            with st.expander(f"📸 Seedance Multi-Subject Reference Lock (Up to {ref_limit_label})", expanded=True):
                 st.markdown("Reference these subjects in your prompt as `Image1`, `Image2`, `Image3` ... `Image50`, and `Video1`, `Video2`, `Video3` ... `Video10`.")
                 
                 # Option A: Quick Bulk Upload
                 st.file_uploader(
                     "📁 Quick Bulk Upload (Select multiple reference images at once)",
                     type=["png", "jpg", "jpeg", "webp"],
                     accept_multiple_files=True,
                     key="studio_wan_extra_imgs_bulk",
                     help="Select multiple images from your computer at once."
                 )
                 
                 st.markdown("--- **or Upload / Assign Slots Individually (Image 2 through Image 9)** ---")
                 c_img_a, c_img_b = st.columns(2)
                 with c_img_a:
                     st.file_uploader("Upload Image 2 (Image2)", type=["png", "jpg", "jpeg", "webp"], key="studio_wan_extra_img2")
                     st.file_uploader("Upload Image 3 (Image3)", type=["png", "jpg", "jpeg", "webp"], key="studio_wan_extra_img3")
                     st.file_uploader("Upload Image 4 (Image4)", type=["png", "jpg", "jpeg", "webp"], key="studio_wan_extra_img4")
                     st.file_uploader("Upload Image 5 (Image5)", type=["png", "jpg", "jpeg", "webp"], key="studio_wan_extra_img5")
                 with c_img_b:
                     st.file_uploader("Upload Image 6 (Image6)", type=["png", "jpg", "jpeg", "webp"], key="studio_wan_extra_img6")
                     st.file_uploader("Upload Image 7 (Image7)", type=["png", "jpg", "jpeg", "webp"], key="studio_wan_extra_img7")
                     st.file_uploader("Upload Image 8 (Image8)", type=["png", "jpg", "jpeg", "webp"], key="studio_wan_extra_img8")
                     st.file_uploader("Upload Image 9 (Image9)", type=["png", "jpg", "jpeg", "webp"], key="studio_wan_extra_img9")
                     
                 st.markdown("--- **Video Motion / Camera Choreography References (Video 2 through Video 4)** ---")
                 c_vid_a, c_vid_b = st.columns(2)
                 with c_vid_a:
                     st.file_uploader("Upload Video 2 (Video2)", type=["mp4", "mov"], key="studio_wan_extra_vid2")
                     st.file_uploader("Upload Video 3 (Video3)", type=["mp4", "mov"], key="studio_wan_extra_vid3")
                 with c_vid_b:
                     st.file_uploader("Upload Video 4 (Video4)", type=["mp4", "mov"], key="studio_wan_extra_vid4")
        
        anim_prompt = st.text_area("Motion Prompt", placeholder="e.g. The character turns her head to look at the camera and smiles, wind blowing hair, realistic physics and textures, 35mm lens.", key="wan_anim_prompt")
        
        c_res, c_ar, c_dur = st.columns(3)
        with c_res:
            anim_res = st.selectbox("Resolution", ["1080P", "720P", "4K Ultra HD"], index=0, key="wan_anim_res")
        with c_ar:
            anim_ar = st.selectbox("Aspect Ratio", ["16:9 (Widescreen)", "9:16 (Vertical / Reels)", "1:1 (Square)"], index=0, key="wan_anim_ar")
        with c_dur:
            anim_dur = st.slider("Duration (seconds)", 2, 30, 5, key="wan_anim_dur")
            
        run_anim_btn = st.button("Generate Video Motion", type="primary", key="wan_run_anim")
        
        if run_anim_btn:
            # 1. Gather all reference images and videos upfront FIRST!
            extra_imgs = list(rig_anim_res["extra_ref_paths"])
            extra_vids = []

            max_extra_allowed = 49 if "2.5" in wan_model_flavor else 8

            # Profiles can contribute many refs (env angles + per-character
            # angles). Older models accept far fewer, so trim before sending.
            if len(extra_imgs) > max_extra_allowed:
                st.warning(
                    f"⚠️ {len(extra_imgs)} reference images mapped but "
                    f"{wan_model_flavor} accepts {max_extra_allowed} — using the first {max_extra_allowed}. "
                    f"Switch to a Seedance 2.5 variant to use the full set."
                )
                extra_imgs = extra_imgs[:max_extra_allowed]
            if "Reference-to-Video" in wan_model_flavor or "Seedance" in wan_model_flavor:
                bulk_uploads_st = st.session_state.get("studio_wan_extra_imgs_bulk", [])
                if bulk_uploads_st:
                    for idx, b_file in enumerate(bulk_uploads_st[:max_extra_allowed]):
                        b_path = os.path.join("output", f"temp_wan_studio_bulk_ex_img_{idx+2}.png")
                        with open(b_path, "wb") as f:
                            f.write(b_file.getbuffer())
                        if b_path not in extra_imgs and len(extra_imgs) < max_extra_allowed:
                            extra_imgs.append(b_path)

                for slot_idx in range(2, 10):
                    w_slot_file = st.session_state.get(f"studio_wan_extra_img{slot_idx}")
                    if w_slot_file:
                        slot_path = os.path.join("output", f"temp_wan_studio_ex_img{slot_idx}.png")
                        with open(slot_path, "wb") as f:
                            f.write(w_slot_file.getbuffer())
                        if slot_path not in extra_imgs and len(extra_imgs) < max_extra_allowed:
                            extra_imgs.append(slot_path)
                            
                for slot_v_idx in range(2, 5):
                    w_vid_file = st.session_state.get(f"studio_wan_extra_vid{slot_v_idx}")
                    if w_vid_file:
                        v_slot_path = os.path.join("output", f"temp_wan_studio_ex_vid{slot_v_idx}.mp4")
                        with open(v_slot_path, "wb") as f:
                            f.write(w_vid_file.getbuffer())
                        if v_slot_path not in extra_vids and len(extra_vids) < 3:
                            extra_vids.append(v_slot_path)

            # If anim_image_path is missing but extra_imgs has images, use extra_imgs[0] as primary image!
            if not anim_image_path and extra_imgs:
                anim_image_path = extra_imgs[0]

            # 2. JSON Prompt Auto-Extraction if raw JSON was pasted
            clean_anim_prompt = anim_prompt.strip() if anim_prompt else ""
            if clean_anim_prompt.startswith("{") and ("visual_prompt" in clean_anim_prompt or "shots" in clean_anim_prompt or "title" in clean_anim_prompt):
                try:
                    import json
                    parsed_j = json.loads(clean_anim_prompt)
                    if isinstance(parsed_j, dict):
                        if "visual_prompt" in parsed_j:
                            clean_anim_prompt = parsed_j["visual_prompt"]
                        elif "shots" in parsed_j and isinstance(parsed_j["shots"], list) and len(parsed_j["shots"]) > 0:
                            vp_list = [sh.get("visual_prompt", "") for sh in parsed_j["shots"] if sh.get("visual_prompt")]
                            if vp_list:
                                clean_anim_prompt = "\n\n".join(vp_list)
                            else:
                                clean_anim_prompt = parsed_j["shots"][0].get("action_description", clean_anim_prompt)
                except Exception:
                    pass

            is_text_to_video_selected = "Text-to-Video" in wan_model_flavor
            
            if not is_text_to_video_selected and not anim_image_path and not extra_imgs:
                st.error("⚠️ **Source image missing!** For Reference-to-Video or Image-to-Video, please upload a source image or reference image above. Or select **`Seedance 2.5 (Text-to-Video)`** from Model Variant if generating purely from text!")
            elif not clean_anim_prompt:
                st.error("Please describe the motion you want in the Motion Prompt area.")
            else:
                user = st.session_state.current_user.get("username")
                req_credits = 10 if "2.5" in wan_model_flavor else 5
                if not auth_mgr.deduct_credits(user, req_credits):
                    st.error(f"❌ Need {req_credits} Credits for {wan_model_flavor}!")
                else:
                    with st.status("⚡ Submitting motion job to Atlas Cloud API...", expanded=True) as status:
                        target_engine = "alibaba/wan-2.7/image-to-video"
                        if "Seedance 2.5" in wan_model_flavor and "Reference" in wan_model_flavor:
                            target_engine = "bytedance/seedance-2.5/reference-to-video"
                        elif "Seedance 2.5" in wan_model_flavor and "Image" in wan_model_flavor:
                            target_engine = "bytedance/seedance-2.5/image-to-video"
                        elif "Seedance 2.5" in wan_model_flavor and "Text" in wan_model_flavor:
                            target_engine = "bytedance/seedance-2.5/text-to-video"
                        elif "Mini" in wan_model_flavor:
                            target_engine = "bytedance/seedance-2.0-mini/reference-to-video"
                        elif "Seedance" in wan_model_flavor and "Reference" in wan_model_flavor:
                            target_engine = "bytedance/seedance-2.0/reference-to-video"
                        elif "Seedance" in wan_model_flavor and "Image" in wan_model_flavor:
                            target_engine = "bytedance/seedance-2.0/image-to-video"
                        elif "Seedance" in wan_model_flavor and "Text" in wan_model_flavor:
                            target_engine = "bytedance/seedance-2.0/text-to-video"
                        elif "Reference-to-Video" in wan_model_flavor:
                            target_engine = "alibaba/wan-2.7/reference-to-video"
                            
                        st.write(f"🚀 Running **{target_engine}** model...")
                        if extra_imgs:
                            st.write(f"📸 Loaded **{len(extra_imgs)} reference images**.")
                        if extra_vids:
                            st.write(f"📹 Loaded **{len(extra_vids)} reference videos**.")

                        final_wan_prompt = clean_anim_prompt
                        if wan_char_swap:
                             final_wan_prompt = (
                                  "Strict Character Swap: Lock character identity to Image1. "
                                  "Transfer all environment details, lighting, physics, frame timing, and motion strictly from Video1. "
                                  "Keep the actions identical to Video1, but swap the character with Image1. "
                                  f"Context: {clean_anim_prompt}"
                             )
                        
                        out_dir = get_user_out_dir("Videos")
                        # Character Profile voice samples -> Seedance audio refs
                        rig_audios = list(rig_anim_res.get("ref_audio_paths") or [])
                        res = generate_wan_video(
                            prompt=final_wan_prompt,
                            image_path=anim_image_path,
                            resolution=anim_res,
                            duration=anim_dur,
                            aspect_ratio=anim_ar.split(" ")[0],
                            ref_video_path=ref_video_url,
                            ref_audio_path=rig_audios[0] if rig_audios else None,
                            extra_audio_paths=rig_audios[1:] if len(rig_audios) > 1 else None,
                            extra_images=extra_imgs if extra_imgs else None,
                            extra_videos=extra_vids if extra_vids else None,
                            model=target_engine,
                            output_folder=out_dir,
                            status_callback=status.write
                        )
                        
                        if res and res.get("status") == "success":
                            status.update(label="Complete!", state="complete")
                            st.success("✅ Video generated successfully!")
                            st.write(f"💾 Saved to: {res.get('video_path', 'N/A')}")
                            if res.get("video_url"):
                                st.video(res["video_url"])
                            if res.get("video_path") and os.path.exists(res["video_path"]):
                                with open(res["video_path"], "rb") as vf:
                                    st.download_button(
                                        "⬇️ Download MP4",
                                        data=vf,
                                        file_name=os.path.basename(res["video_path"]),
                                        mime="video/mp4"
                                    )
                        else:
                            status.update(label="Failed", state="error")
                            st.error(f"Error: {res.get('error', 'Unknown error') if res else 'Generation failed'}")
                            if res and res.get("logs"):
                                with st.expander("Logs", expanded=True):
                                    st.write(res.get("logs", []))

# ==========================================
# TAB 8: CHARACTER STUDIO
# ==========================================
if selection == "Character Studio":

    with st.container():
        st.markdown("### Character Studio")
    st.info("Design your cast with precision. Used consistently across the platform.")

    # Fragment to fix "Tab Jump" bug on generation
    @st.fragment
    def character_studio_fragment():
        import importlib
        import execution.character_studio_ui as _cs_mod
        importlib.reload(_cs_mod)
        _cs_mod.render_character_studio(characters_data, get_user_out_dir, campaign_mgr)
        
    character_studio_fragment()


# ==========================================
# TAB: MULTI-SHOT GENERATOR
# ==========================================
if selection == "Multi-Shot Generator":
    from execution.multishot_ui import render_multishot_ui
    render_multishot_ui(get_user_out_dir)

