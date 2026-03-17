import streamlit as st
import sys
import os
import json
import time

# Add execution directory to path to import scripts
sys.path.append(os.path.join(os.path.dirname(__file__), 'execution'))

try:
    import importlib
    import load_assets as la_module
    importlib.reload(la_module)
    import load_assets as la_module
    importlib.reload(la_module)
    from load_assets import load_assets, promote_image_to_asset
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

# --- TABS LAYOUT ---
# --- TABS LAYOUT (Persistent) ---
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Workflow Wizard"

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
    "Asset Library",
    "Mini Series",
    "World Builder",
    "Campaign Queue",
    "Art Director",
    "Video Studio",
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
    return all_images_meta[:200]

# --- Cached Presigned URL batch (avoids re-signing on rerun) ---
@st.cache_data(ttl=3500, show_spinner=False)
def _sign_urls(bucket_name, region, keys_tuple):
    """Generate presigned URLs for a batch of S3 keys. keys_tuple for hashability."""
    import boto3
    s3 = boto3.client('s3', region_name=region)
    urls = {}
    for key in keys_tuple:
        urls[key] = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=3600
        )
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
    return local_imgs[:200]

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
                scenario = scenarios[selected_scenario_key]
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
                                 f_fit_opts = assets.get('outfits', {})
                                 if not f_fit_opts: f_fit_opts = {"Casual": "", "Chic": ""}
                                 f_outfit_key = st.selectbox(f"Outfit for {f_name.split()[0]}", list(f_fit_opts.keys()), key=f"fit_{idx}")
                                 f_outfit_path = None
                                 if isinstance(f_fit_opts[f_outfit_key], dict):
                                     f_outfit_name = f_fit_opts[f_outfit_key]['name']
                                     f_outfit_path = f_fit_opts[f_outfit_key].get('default_img')
                                 else:
                                     f_outfit_name = os.path.splitext(f_outfit_key.split('/')[-1])[0]
                                     f_outfit_path = f_fit_opts[f_outfit_key]
                                 temp_assets.append({"path": f_outfit_path, "label": f"Outfit for {f_name}: {f_outfit_name}"}) 
                                 friend_outfit_details.append(f"{f_name} in {f_outfit_name}") 
                                 if f_outfit_path: st.image(f_outfit_path, width=150, caption=f_outfit_name)
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
                    
                    # DEBUG OUTPUT
                    st.write(f"🔍 DEBUG: is_custom_scenario in session = {st.session_state.get('is_custom_scenario', 'NOT SET')}")
                    st.write(f"🔍 DEBUG: custom_scenario_data exists = {'custom_scenario_data' in st.session_state}")
                    st.write(f"🔍 DEBUG: use_custom_flow = {use_custom_flow}")
                    
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
2. Start with "Photorealistic, hyper-detailed, cinematic"
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
                            import google.generativeai as genai
                            model = genai.GenerativeModel("gemini-2.0-flash")
                            response = model.generate_content(director_prompt, generation_config={"temperature": sel_temperature})
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
                        # 2. Call Generator with full context
                        # We treat the current draft as 'additional_notes' context
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
                            
                            additional_notes=f"CREATIVE BRIEF: The atmosphere is {current_selections.get('VIBE', 'General')}. Overall style: {sel_film}. CREATE A FRESH, HOLLYWOOD-LEVEL SCENE DESCRIPTION from the visual references and cast list. Do not copy template text.",
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
                    sb_prompts = generate_storyboard_prompts(
                        scenario['name'], 
                        final_prompt,
                        camera_settings=camera_str,
                        reference_context=reference_context_str
                    )
                    st.session_state['sb_prompts'] = sb_prompts
                    if sb_prompts and not isinstance(sb_prompts[0], str) or (len(sb_prompts) > 0 and "Error" not in sb_prompts[0]):
                        st.success("Storyboard Drafted! See below.")
                    else:
                        st.error(f"Generation failed: {sb_prompts}")
            
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
                             campaign_mgr.add_job(
                                name=f"SB_Shot_{i+1}_{int(time.time())}",
                                description=f"Storyboard Shot {i+1}",
                                prompt_data={
                                    "positive_prompt": p + f", {final_prompt}", 
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
                                         "positive_prompt": p + f", {final_prompt}", # Append full context
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
            st.markdown("**Select Video Engine**")
            video_model = st.selectbox("Engine", ["Kling AI 2.6 (Professional)", "HuMo AI (Human Motion Premium)"], key="vid_model_select")
            
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
                    
                    ref_video_url = None
                    ref_orientation = "image"
                    
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
                    
                suggestion = generate_motion_prompt(temp_path, movement_type=vid_movement, physics_focus=vid_physics)
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

