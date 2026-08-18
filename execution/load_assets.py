import os
import json
import re
import shutil
import datetime
from execution.s3_uploader import upload_file_obj

# --- MULTI-IMAGE PROFILE SUPPORT ---
# A "Profile" is an asset folder holding several reference images of the SAME
# subject (a character from 4 angles, a location from 3 camera angles) plus an
# optional voice sample. Files are named by convention so that BOTH the local
# scanner and the S3 scanner can recognise a profile without opening
# details.json (which S3 would charge an extra GET for, per asset):
#
#   {Category}/{Asset Name}/ref_1.png ... ref_N.png   <- the reference set
#   {Category}/{Asset Name}/default.png               <- copy of ref_1 (back-compat)
#   {Category}/{Asset Name}/voice_sample.mp3          <- optional (Characters)
#
# Without this grouping every ref_N.png would surface as its own library entry,
# which is the exact fragmentation this feature exists to remove.

PROFILE_IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.webp')
PROFILE_AUDIO_EXTS = ('.mp3', '.wav', '.m4a', '.aac', '.ogg')
_REF_RE = re.compile(r'^ref_(\d+)$', re.IGNORECASE)


def _ref_index(filename):
    """Returns the N from 'ref_N.ext', or None if the file isn't a profile ref."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    m = _REF_RE.match(stem)
    return int(m.group(1)) if m else None


def _is_profile_extra(filename):
    """True for files a profile owns but that must NOT become their own entry."""
    stem = os.path.splitext(os.path.basename(filename))[0].lower()
    return _ref_index(filename) is not None or stem in ("default", "voice_sample")


def _s3_public_url(bucket, key):
    """Builds the direct (non-expiring) S3 object URL for a key."""
    import urllib.parse
    encoded_key = '/'.join(urllib.parse.quote(part) for part in key.split('/'))
    region = os.getenv('AWS_REGION', 'ap-southeast-2')
    return f"https://{bucket}.s3.{region}.amazonaws.com/{encoded_key}"


class AssetRef(str):
    """
    An asset value that IS the primary image path/URL (a real str), while also
    carrying the rest of its Profile.

    This is deliberately a str subclass rather than a dict. The app has many
    consumers that pass an asset value straight into st.image(), os.path.exists(),
    .startswith("http"), etc. Handing those a dict crashes them (it did — the
    Asset Library grid blew up on st.image). As a str subclass every existing
    consumer keeps working untouched, and profile-aware code reads the extras
    via profile_refs()/profile_voice().
    """
    __slots__ = ("reference_images", "voice_sample", "profile_name")

    def __new__(cls, primary, reference_images=None, voice_sample=None, name=None):
        obj = super().__new__(cls, primary)
        obj.reference_images = list(reference_images) if reference_images else [str(primary)]
        obj.voice_sample = voice_sample
        obj.profile_name = name
        return obj

    def __reduce__(self):
        # REQUIRED. st.cache_data serializes what it stores, and a str subclass's
        # default reduce only round-trips the string value — the attached profile
        # silently collapsed to a single reference. Spelling out __reduce__ makes
        # the full profile survive caching, deepcopy and disk persistence.
        return (
            _rebuild_asset_ref,
            (str(self), list(self.reference_images), self.voice_sample, self.profile_name),
        )


def _rebuild_asset_ref(primary, reference_images, voice_sample, name):
    """Module-level rebuilder so AssetRef is picklable (see AssetRef.__reduce__)."""
    return AssetRef(primary, reference_images=reference_images,
                    voice_sample=voice_sample, name=name)


def profile_refs(value):
    """
    Every reference image for an asset value, whatever shape it is.
    Returns a plain list of str. Legacy single-image assets return one entry.

    Deliberately duck-typed rather than isinstance(value, AssetRef): app.py puts
    execution/ on sys.path, so this file gets imported under BOTH `load_assets`
    and `execution.load_assets` — two module objects, two distinct AssetRef
    classes. isinstance() silently fails across that boundary and the profile
    collapses to a single reference. getattr works regardless of which copy
    built the value.
    """
    refs = getattr(value, "reference_images", None)
    if refs:
        return [r for r in refs if r]
    if isinstance(value, dict):
        d_refs = [r for r in (value.get("reference_images") or []) if r]
        if d_refs:
            return list(d_refs)
        primary = value.get("default_img") or value.get("path")
        return [primary] if primary else []
    return [value] if value else []


def profile_voice(value):
    """The voice sample for an asset value, or None. Safe for every shape."""
    voice = getattr(value, "voice_sample", None)
    if voice:
        return voice
    if isinstance(value, dict):
        return value.get("voice_sample")
    return None


def build_profile_entry(asset_name, ref_map, voice=None):
    """
    Assembles the canonical profile value from {index: location} where location
    is an absolute path (local mode) or an https URL (cloud mode).

    Returns an AssetRef: a string equal to the primary image, so every legacy
    consumer keeps working, with the full reference set attached.
    """
    ordered = [ref_map[i] for i in sorted(ref_map.keys())]
    if not ordered:
        return None
    return AssetRef(ordered[0], reference_images=ordered, voice_sample=voice, name=asset_name)


def scan_directory(directory):
    """Recursively finds all image files in a directory. Returns {RelativePath / Name: absolute_path}."""
    items = {}
    if not os.path.exists(directory):
        return items
    
    base_dir_abs = os.path.abspath(directory)
        
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and not file.startswith('._'):
                full_path = os.path.abspath(os.path.join(root, file))
                
                # Calculate relative path
                rel_dir = os.path.relpath(root, base_dir_abs)
                
                # Base filename
                name = os.path.splitext(file)[0].replace('_', ' ').title()
                
                if rel_dir == ".":
                    final_name = name
                else:
                    # Make relative path readable
                    # e.g. "Summer/Beach" -> "Summer / Beach / Name"
                    rel_parts = [p.replace('_', ' ').title() for p in rel_dir.split(os.sep)]
                    prefix = " / ".join(rel_parts)
                    final_name = f"{prefix} / {name}"
                
                items[final_name] = full_path

    # Sort by name
    return dict(sorted(items.items()))


def scan_directory_with_profiles(directory):
    """
    Like scan_directory(), but collapses multi-image Profile folders into a
    SINGLE dict entry instead of one entry per ref_N image file.

    Returns {DisplayName: absolute_path} for ordinary loose images, and
    {DisplayName: {name, default_img, path, reference_images, voice_sample}}
    for profile folders. Both shapes are already understood by the consumers in
    app.py, which read `default_img`/`path` when the value is a dict.
    """
    if not os.path.exists(directory):
        return {}

    base_dir_abs = os.path.abspath(directory)
    profiles = {}
    profile_dirs = set()

    # Pass 1 — find folders that follow the ref_N profile convention.
    for root, dirs, files in os.walk(directory):
        ref_map = {}
        voice = None
        for file in files:
            if file.startswith('._'):
                continue
            low = file.lower()
            idx = _ref_index(file)
            if idx is not None and low.endswith(PROFILE_IMAGE_EXTS):
                ref_map[idx] = os.path.abspath(os.path.join(root, file))
            elif os.path.splitext(low)[0] == "voice_sample" and low.endswith(PROFILE_AUDIO_EXTS):
                voice = os.path.abspath(os.path.join(root, file))

        if not ref_map:
            continue

        rel_dir = os.path.relpath(root, base_dir_abs)
        asset_name = os.path.basename(root) if rel_dir != "." else os.path.basename(base_dir_abs)
        if rel_dir == ".":
            display = asset_name.replace('_', ' ').title()
        else:
            display = " / ".join(p.replace('_', ' ').title() for p in rel_dir.split(os.sep))

        entry = build_profile_entry(asset_name.replace('_', ' ').title(), ref_map, voice)
        if entry:
            profiles[display] = entry
            profile_dirs.add(os.path.abspath(root))

    # Pass 2 — ordinary images, skipping files already owned by a profile.
    items = {}
    for root, dirs, files in os.walk(directory):
        root_abs = os.path.abspath(root)
        is_profile_dir = root_abs in profile_dirs
        for file in files:
            if not file.lower().endswith(PROFILE_IMAGE_EXTS) or file.startswith('._'):
                continue
            # Inside a profile folder, ref_N/default/voice_sample belong to the
            # profile entry — surfacing them separately is the fragmentation bug.
            if is_profile_dir and _is_profile_extra(file):
                continue

            full_path = os.path.abspath(os.path.join(root, file))
            rel_dir = os.path.relpath(root, base_dir_abs)
            name = os.path.splitext(file)[0].replace('_', ' ').title()
            if rel_dir == ".":
                final_name = name
            else:
                rel_parts = [p.replace('_', ' ').title() for p in rel_dir.split(os.sep)]
                final_name = f"{' / '.join(rel_parts)} / {name}"
            items[final_name] = full_path

    merged = {**items, **profiles}
    return dict(sorted(merged.items()))


# --- CLOUD MANIFEST LOGIC ---
# (scan_manifest function removed - logic moved to Single Pass loop below)

def load_assets(base_path="assets", user_assets_dir=None, skip_base=False, target_username=None):
    """
    Dynamically loads assets.
    If 'assets_manifest.json' exists, uses S3 URLs (Cloud Mode).
    Otherwise scans local 'assets/' folder (Local Mode).
    """
    
    data = {
        "vibes": {},
        "outfits": {},
        "characters": {},
        "locations": {},
        "relations": {},
        "pets": {},
        "props": {},
        "vehicles": {},
        "foods": {}
    }
    
    if not skip_base:
        # 1. CHECK FOR CLOUD MANIFEST
        manifest_path = "assets_manifest.json"
        use_cloud = False
        
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                
                bucket = os.getenv("S3_BUCKET_NAME")
                if bucket:
                    region = os.getenv("AWS_REGION", "ap-southeast-2")
                    s3_base = f"https://{bucket}.s3.{region}.amazonaws.com/assets"
                    print(f"☁️ Cloud Mode Activated: Using {s3_base}")
                    use_cloud = True
                else:
                    print("⚠️ Manifest found but S3_BUCKET_NAME missing. Falling back to local.")
            except Exception as e:
                print(f"⚠️ Error reading manifest: {e}")
                
        if use_cloud:
            # --- CLOUD LOADING (Single Pass) ---
            print(f"☁️ Cloud Mode: Scanning {len(manifest) if manifest else 'S3 Direct'} items...")
            
            # If manifest is empty/failed, we MUST scan S3 directly for base assets too
            if not manifest or len(manifest) < 5:
                print("⚠️ Manifest empty/missing. Scanning S3 'assets/' prefix directly...")
                try:
                    import boto3
                    bucket = os.getenv("S3_BUCKET_NAME")
                    from botocore.config import Config
                    s3 = boto3.client(
                        's3', 
                        region_name=os.getenv("AWS_REGION", "ap-southeast-2"),
                        config=Config(s3={'addressing_style': 'virtual', 'signature_version': 's3v4'})
                    )
                    
                    # Scan root assets folder
                    paginator = s3.get_paginator('list_objects_v2')
                    pages = paginator.paginate(Bucket=bucket, Prefix="assets/")
                    
                    manifest = []
                    for page in pages:
                        for obj in page.get('Contents', []):
                             key = obj['Key']
                             # Filter valid images
                             if key.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and "users/" not in key:
                                 # Convert key to "relative path" style expected by loader
                                 # Remove 'assets/' prefix if present for cleaner matching logic?
                                 # Actually logic below expects full path?
                                 # Line 101: parts = rel_path.split("/")
                                 # Line 105: check for "AI Content Creators"
                                 # Just use key as rel_path
                                 manifest.append(key)
                    print(f"✅ Discovered {len(manifest)} base assets from S3.")
                except Exception as e:
                    print(f"❌ Failed to scan S3 base assets: {e}")
    
            # explicit mapping of Folder Name (in manifest) -> Data Category Key
            folder_map = {
                "environments": "locations",
                "vibes": "vibes",
                "outfits": "outfits",
                "influencer clothing": "outfits",
                "influencer clothing ": "outfits", # Handle trailing space
                "characters": "characters",
                "shay.so.fine": "characters", # Legacy Mapping
                "friends": "relations",
                "pets": "pets",
                "props": "props",
                "vehicles": "vehicles",
                "foods": "foods"
            }
    
            for rel_path in manifest:
                # manifest path: "AI Content Creators/Category/Sub/File.png"
                # Skip ui_icons files — never load them as assets
                if "ui_icons" in rel_path.lower() or "/icons/" in rel_path.lower():
                    continue
                
                parts = rel_path.split("/")
                
                # Skip root if present
                start_idx = 0
                if len(parts) > 0 and parts[0] == "AI Content Creators":
                    start_idx = 1
                
                if len(parts) <= start_idx + 1: continue # Need at least Category + File
                
                # Identify Category Folder
                cat_folder = parts[start_idx].lower().strip()
                
                # Map to App Category
                target_key = folder_map.get(cat_folder)
                
                if target_key:
                    # Generate Name
                    # Everything after Category Folder and before Filename is "SubPath"
                    sub_parts = parts[start_idx+1 : -1]
                    filename = os.path.splitext(parts[-1])[0].replace('_', ' ').title()
                    
                    if not sub_parts:
                        final_name = filename
                    else:
                        prefix_str = " / ".join([p.replace('_', ' ').title() for p in sub_parts])
                        final_name = f"{prefix_str} / {filename}"
                    
                    # Generate URL
                    url = f"{s3_base}/{rel_path.replace(' ', '%20')}"
                    
                    # Add to Data
                    data[target_key][final_name] = url
            
            # Fallback: If Vibes empty, use Locations
            if not data["vibes"]:
                data["vibes"] = data["locations"]

    # --- 2. USER ASSETS (Cloud or Local Cache) ---
    if user_assets_dir:
        # Check if this is a path like "output/users/{user}/Assets"
        # We need the username to build the S3 key: users/{user}/Assets
        try:
            username = target_username
            if not username:
                # Use heuristic: check if "users" is in path
                parts = user_assets_dir.split(os.sep)
                if "users" in parts:
                    u_idx = parts.index("users")
                    username = parts[u_idx + 1]
            
            if username:
                
                user_manifest_path = os.path.join(user_assets_dir, "user_manifest.json")
                bucket = os.getenv("S3_BUCKET_NAME")
                
                # A. Try Loading from Cached Manifest (FAST)
                loaded_from_cache = False
                if os.path.exists(user_manifest_path):
                     try:
                         # Check age (optional validity check could go here)
                         with open(user_manifest_path, "r") as f:
                             cached_items = json.load(f)
                             
                         # Initialize S3 for re-signing
                         import boto3
                         from botocore.config import Config
                         s3 = boto3.client(
                             's3', 
                             region_name=os.getenv("AWS_REGION", "ap-southeast-2"),
                             config=Config(s3={'addressing_style': 'virtual', 'signature_version': 's3v4'})
                         )

                         # Reconstruct Data Structure
                         for item in cached_items:
                             cat_key = item.get("category")
                             name = item.get("name")
                             url = item.get("url")
                             key = item.get("key")

                             # RE-SIGN URL IF KEY EXISTS (Fix Expiry)
                             if key and bucket:
                                 try:
                                     url = _s3_public_url(bucket, key)
                                 except Exception:
                                     pass # Fallback to cached URL if signing fails

                             # MULTI-IMAGE PROFILE: rebuild the full ref set from
                             # cached keys so URLs stay fresh like the single case.
                             prof = item.get("profile")
                             if prof and cat_key in data and name and bucket:
                                 try:
                                     ref_keys = prof.get("ref_keys") or []
                                     ref_map = {i: _s3_public_url(bucket, k) for i, k in enumerate(ref_keys)}
                                     voice_key = prof.get("voice_key")
                                     entry = build_profile_entry(
                                         prof.get("name") or name,
                                         ref_map,
                                         _s3_public_url(bucket, voice_key) if voice_key else None,
                                     )
                                     if entry:
                                         data[cat_key][name] = entry
                                         continue
                                 except Exception as pe:
                                     print(f"⚠️ Profile cache rebuild failed for {name}: {pe}")

                             if cat_key in data and name and url:
                                  data[cat_key][name] = url

                         loaded_from_cache = True
                     except Exception as e:
                         print(f"⚠️ Corrupt User Manifest: {e}")
                         
                # B. Fallback to S3 Scan (SLOW) -> Then Cache It
                if not loaded_from_cache and bucket and username:
                    import boto3
                    from botocore.config import Config
                    s3 = boto3.client(
                        's3', 
                        region_name=os.getenv("AWS_REGION", "ap-southeast-2"),
                        config=Config(s3={'addressing_style': 'virtual', 'signature_version': 's3v4'})
                    )
                    prefix = f"users/{username}/Assets/"
                    
                    # List all objects in user folder
                    paginator = s3.get_paginator('list_objects_v2')
                    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
                    
                    user_cats = {
                        "characters": "characters",
                        "environments": "locations", "locations": "locations",
                        "outfits": "outfits", "wardrobe": "outfits", "clothing": "outfits", "influencer clothing": "outfits",
                        "vibes": "vibes",
                        "friends": "relations", "relations": "relations",
                        "pets": "pets",
                        "props": "props",
                        "vehicles": "vehicles",
                        "foods": "foods"
                    }
                    
                    new_cache_list = []
                    # Multi-image profiles: {(target_key, display): {"name":.., "refs": {idx: key}, "voice": key}}
                    profile_groups = {}

                    for page in pages:
                        for obj in page.get('Contents', []):
                            key = obj['Key']
                            # key format: users/{user}/Assets/{Category}/{Asset Name...}
                            k_parts = key.split("/")
                            if len(k_parts) < 5: continue # Need Category + Name

                            # k_parts[0]=users, [1]=user, [2]=Assets, [3]=Category, [4:]=Rest
                            cat_folder_raw = k_parts[3]
                            cat_folder = cat_folder_raw.lower().strip() # Normalize
                            target_key = user_cats.get(cat_folder)
                            if not target_key:
                                continue

                            key_low = key.lower()
                            is_image = key_low.endswith(PROFILE_IMAGE_EXTS)
                            is_audio = key_low.endswith(PROFILE_AUDIO_EXTS)
                            if not (is_image or is_audio):
                                continue

                            # Name
                            sub_parts = k_parts[4:-1]
                            filename = k_parts[-1]

                            # --- HEURISTIC FIX: Re-classify based on sub-folders ---
                            # If user put "Clothing" folder inside "Characters", move it to Outfits
                            sub_str = " ".join(sub_parts).lower()
                            if "clothing" in sub_str or "outfit" in sub_str or "wardrobe" in sub_str:
                                target_key = "outfits"
                            elif "environment" in sub_str or "location" in sub_str:
                                target_key = "locations"
                            # --------------------------------------------------------

                            stem_low = os.path.splitext(filename)[0].lower()
                            ref_idx = _ref_index(filename)

                            # --- PROFILE GROUPING ---
                            # ref_N / default / voice_sample belong to their folder's
                            # profile entry; emitting them individually is the
                            # fragmentation this feature removes.
                            if sub_parts and (ref_idx is not None or stem_low in ("default", "voice_sample")):
                                p_str = " / ".join([p.replace('_', ' ').title() for p in sub_parts])
                                p_display = f"(My) {p_str}"
                                grp = profile_groups.setdefault(
                                    (target_key, p_display),
                                    {"name": sub_parts[-1].replace('_', ' ').title(), "refs": {}, "voice": None,
                                     "default_key": None, "default_name": None},
                                )
                                if ref_idx is not None and is_image:
                                    grp["refs"][ref_idx] = key
                                elif stem_low == "voice_sample" and is_audio:
                                    grp["voice"] = key
                                elif stem_low == "default" and is_image:
                                    # In a profile this duplicates ref_1, but a
                                    # LEGACY asset (pre-profile) is only a
                                    # default.* — keep it so it can still be
                                    # emitted flat if no ref_N files show up.
                                    grp["default_key"] = key
                                    p_str_legacy = " / ".join([p.replace('_', ' ').title() for p in sub_parts])
                                    grp["default_name"] = f"(My) {p_str_legacy} / {os.path.splitext(filename)[0].replace('_', ' ').title()}"
                                continue

                            # Loose audio that isn't a voice sample isn't a library asset.
                            if not is_image:
                                continue

                            name_base = os.path.splitext(filename)[0].replace('_', ' ').title()

                            if not sub_parts:
                                final_name = f"(My) {name_base}"
                            else:
                                p_str = " / ".join([p.replace('_', ' ').title() for p in sub_parts])
                                final_name = f"(My) {p_str} / {name_base}"

                            url = _s3_public_url(bucket, key)
                            data[target_key][final_name] = url

                            # Add to List for Cache
                            new_cache_list.append({
                                "category": target_key,
                                "name": final_name,
                                "url": url,
                                "key": key # Store key for future checks if needed
                            })

                    # --- EMIT GROUPED PROFILES ---
                    for (target_key, p_display), grp in profile_groups.items():
                        if not grp["refs"]:
                            # LEGACY asset: a lone default.* with no ref_N set.
                            # Emit it exactly as before so pre-profile characters
                            # and locations don't vanish from the library.
                            if grp.get("default_key"):
                                l_url = _s3_public_url(bucket, grp["default_key"])
                                l_name = grp.get("default_name") or p_display
                                data[target_key][l_name] = l_url
                                new_cache_list.append({
                                    "category": target_key,
                                    "name": l_name,
                                    "url": l_url,
                                    "key": grp["default_key"],
                                })
                            continue
                        ref_urls = {i: _s3_public_url(bucket, k) for i, k in grp["refs"].items()}
                        voice_url = _s3_public_url(bucket, grp["voice"]) if grp["voice"] else None
                        entry = build_profile_entry(grp["name"], ref_urls, voice_url)
                        if not entry:
                            continue
                        data[target_key][p_display] = entry
                        # Cache the KEYS so URLs can be rebuilt fresh on next load.
                        new_cache_list.append({
                            "category": target_key,
                            "name": p_display,
                            "url": str(entry),
                            "key": grp["refs"][sorted(grp["refs"].keys())[0]],
                            "profile": {
                                "name": grp["name"],
                                "ref_keys": [grp["refs"][i] for i in sorted(grp["refs"].keys())],
                                "voice_key": grp["voice"],
                            },
                        })

                    # WRITE CACHE
                    if new_cache_list:
                         try:
                             os.makedirs(user_assets_dir, exist_ok=True)
                             with open(user_manifest_path, "w") as f:
                                 json.dump(new_cache_list, f)
                             print(f"✅ Generated & Saved User Manifest for {username}")
                         except Exception as e:
                             print(f"⚠️ Failed to save user manifest: {e}")
                             
                    print(f"✅ Loaded User Assets from S3 for {username} (Live Scan)")
        except Exception as e:
             print(f"S3 User Asset Scan Error: {e}")
             import traceback
             traceback.print_exc()

    
    # --- LOCAL FALLBACK (Existing Logic) ---
    if not skip_base:
        # --- ROBUST PATH DETECTION ---
        # Find "AI Content Creators" regardless of casing or operating system
        if not os.path.exists(base_path):
            # 1. Search in current directory
            candidates = ["assets", "Assets"]
            found_base = None
            
            for c in candidates:
                if os.path.exists(c):
                    found_base = c
                    break
            
            if found_base:
                # Look for subfolder
                sub_candidates = ["AI Content Creators", "ai content creators", "Ai Content Creators"]
                
                # Check immediate children of assets/
                try:
                    children = os.listdir(found_base)
                    for child in children:
                        if child.lower() == "ai content creators":
                            base_path = os.path.join(found_base, child)
                            print(f"✅ Found Asset Path: {base_path}")
                            break
                except Exception as e:
                    print(f"Error scanning assets dir: {e}")
                    
                if base_path == "assets": # Didn't find subfolder, default to root
                     base_path = found_base
                     print(f"⚠️ 'AI Content Creators' subfolder not found. Using root '{found_base}'.")


        # --- 1. Vibes / Locations ---
        env_path = os.path.join(base_path, "Environments")
        if os.path.exists(env_path):
            data["locations"] = scan_directory_with_profiles(env_path)
        
        vibes_path = os.path.join(base_path, "Vibes")
        if os.path.exists(vibes_path):
            data["vibes"] = scan_directory(vibes_path)
        else:
            data["vibes"] = data["locations"]
        
        # --- 2. Outfits ---
        outfits_path = os.path.join(base_path, "Outfits")
        if not os.path.exists(outfits_path):
            # Handle typo folders
            for typo in ["Influencer CLothing ", "Influencer CLothing"]:
                 p = os.path.join(base_path, typo)
                 if os.path.exists(p): outfits_path = p; break
                 
        data["outfits"] = scan_directory(outfits_path)
        
        # --- 3. Characters ---
        # A. New Standard Structure
        chars_path_strict = os.path.join(base_path, "Characters")
        if os.path.exists(chars_path_strict):
            data["characters"].update(scan_directory_with_profiles(chars_path_strict))
        
        # B. Legacy Fallback (Root Folders)
        exclude = [
            "Environments", "Influencer CLothing ", "Influencer CLothing", 
            "Random Influencer Models", "Vibes", "Outfits", "Characters",
            "Friends", "Pets", "Props", "Vehicles", "Foods", ".DS_Store",
            "AI Content Creators", "ai content creators", "Ai Content Creators", "Assets",
            "ui_icons", "UI_Icons", "Ui_icons", "icons", "Icons",  # Never load UI icon folders
        ]
        
        if os.path.exists(base_path):
            root_folders = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
            for folder in root_folders:
                if folder not in exclude:
                    c_path = os.path.join(base_path, folder)
                    c_images = scan_directory(c_path)
                    for relative_key, full_path in c_images.items():
                        full_key = f"{folder} / {relative_key}"
                        if full_key not in data["characters"]:
                             data["characters"][full_key] = full_path
            
        # --- 4. Others (Standard) ---
        data["relations"] = scan_directory(os.path.join(base_path, "Friends"))
        data["pets"] = scan_directory(os.path.join(base_path, "Pets"))
        data["props"] = scan_directory(os.path.join(base_path, "Props"))
        data["vehicles"] = scan_directory(os.path.join(base_path, "Vehicles"))
        data["foods"] = scan_directory(os.path.join(base_path, "Foods"))

        # --- 5. AI Content Creators (Nested Base) ---
        ai_cc_path = os.path.join(base_path, "AI Content Creators")
        if os.path.exists(ai_cc_path):
            print(f"📂 Scanning Nested Base: {ai_cc_path}")
            # Map specific folders to categories
            nested_map = {
                "Environments": "locations",
                "Foods": "foods",
                "Friends": "relations",
                "Influencer CLothing ": "outfits",
                "Influencer CLothing": "outfits",
                "Pets": "pets",
                "Props": "props",
                "Shay.So.Fine": "characters", # Critical Mapping
                "Vehicles": "vehicles",
                "2026 jan clothing": "outfits",
                "2026 jan clothing ": "outfits"
            }
            
            for folder_name, cat_key in nested_map.items():
                start_p = os.path.join(ai_cc_path, folder_name)
                if os.path.exists(start_p):
                    found_items = scan_directory(start_p)
                    # Merge
                    # We want keys to likely look like "AI Content Creators / Shay / Image"?
                    # Or just "Shay / Image"
                    # scan_directory returns RELATIVE to start_p.
                    # so key is "Image".
                    # We might want to prefix unless it's unique.
                    
                    for k, v in found_items.items():
                        # If character, maybe use folder name as prefix?
                        # e.g. Shay.So.Fine / Image.png
                        if cat_key == "characters":
                             # Use the folder name or just "Shay"
                             prefix = folder_name.replace('.', ' ')
                             final_k = f"{prefix} / {k}"
                        elif cat_key == "outfits":
                             final_k = f"AI / {k}"
                        else:
                             final_k = k
                        
                        data[cat_key][final_k] = v


    # --- 5. User Assets (If Logged In) ---
    if user_assets_dir and os.path.exists(user_assets_dir):
        # Scan standard folders in user directory
        user_cats = {
            "Characters": "characters",
            "Environments": "locations",
            "Outfits": "outfits",
            "Vibes": "vibes",
            "Friends": "relations",
            "Pets": "pets",
            "Props": "props",
            "Vehicles": "vehicles",
            "Foods": "foods"
        }
        
        for folder_name, data_key in user_cats.items():
            u_path = os.path.join(user_assets_dir, folder_name)
            if os.path.exists(u_path):
                user_items = scan_directory_with_profiles(u_path)
                # Merge with prefix to identify them easily
                for name, path in user_items.items():
                    # Prefix with (User) or similar if desired, or just list them.
                    # Using a subtle prefix helps grouping in dropdowns
                    final_key = f"(My) {name}"
                    
                    # --- HEURISTIC FIX (Local) ---
                    target_key_local = data_key
                    n_low = name.lower()
                    if "clothing" in n_low or "outfit" in n_low or "wardrobe" in n_low:
                        target_key_local = "outfits" 
                        print(f"DEBUG(Local): Moved {name} to Outfits")
                    elif "environment" in n_low or "location" in n_low:
                        target_key_local = "locations"
                    # -----------------------------

                    data[target_key_local][final_key] = path
                    print(f"✅ Loaded User Asset: {final_key} -> {path}")
            else:
                print(f"⚠️ User Asset Folder Missing: {u_path}")

    return data


def get_assets_by_category(category, user_assets_dir=None):
    """
    Helper to get specific category assets directly.
    """
    data = load_assets(user_assets_dir=user_assets_dir)
    return data.get(category, {})

def promote_image_to_asset(image_path, user, category, asset_name, prompt=""):
    """
    Moves a generated image from a temporary/user folder to the permanent Assets library.
    Invalidates the manifest cache.
    """
    if not os.path.exists(image_path):
        return {"status": "failed", "error": f"Source image for '{asset_name}' not found at {image_path}"}
        
    # Standardize category path
    cat_folder = category.title() # e.g. "Characters", "Outfits"
    asset_dir = os.path.join("output", "users", user, "Assets", cat_folder, asset_name)
    os.makedirs(asset_dir, exist_ok=True)
    
    # Target Image Path
    # We use default.png for Character Identity, but maybe just filename for others?
    # For now, let's use the original filename or a clean standard.
    ext = os.path.splitext(image_path)[1] or ".png"
    target_filename = "default.png" if cat_folder == "Characters" else f"{asset_name.replace(' ', '_')}{ext}"
    target_path = os.path.join(asset_dir, target_filename)
    
    try:
        # 1. Copy local
        shutil.copy(image_path, target_path)
        
        # 2. Save metadata
        details = {
            "name": asset_name,
            "prompt": prompt,
            "category": category,
            "created": str(datetime.datetime.now())
        }
        json_path = os.path.join(asset_dir, "details.json")
        with open(json_path, "w") as f:
            json.dump(details, f)
            
        logs = [f"✅ Saved locally to {target_path}"]
            
        # 3. S3 Sync
        bucket = os.getenv("S3_BUCKET_NAME")
        if bucket:
            try:
                # Key format: users/{user}/Assets/{Category}/{Asset Name}/{filename}
                key_img = f"users/{user}/Assets/{cat_folder}/{asset_name}/{target_filename}"
                with open(target_path, "rb") as f:
                    upload_file_obj(f, key_img)
                
                key_json = f"users/{user}/Assets/{cat_folder}/{asset_name}/details.json"
                with open(json_path, "rb") as f:
                    upload_file_obj(f, key_json)
                logs.append("☁️ Synced to Cloud")
            except Exception as se:
                logs.append(f"⚠️ Cloud sync failed: {se}")
                
        # 4. CRITICAL: Invalidate Cache
        manifest_cache = os.path.join("output", "users", user, "Assets", "user_manifest.json")
        if os.path.exists(manifest_cache):
            os.remove(manifest_cache)
            logs.append("♻️ Manifest Cache Invalidated")
            
        return {"status": "success", "logs": "\n".join(logs), "asset_path": target_path}

    except Exception as e:
        return {"status": "failed", "error": str(e)}


def promote_multi_image_profile(image_paths, user, category, asset_name, prompt="",
                                voice_path=None, max_images=4):
    """
    Saves several reference images of the SAME subject as ONE grouped Profile
    asset (plus an optional voice sample), instead of N disconnected library
    entries.

    Used for Character Profiles (up to 4 reference photos + a ~15s voice sample)
    and Environment Profiles (up to 3 camera angles of one location). The saved
    layout is the ref_N convention documented at the top of this module, which
    both scan_directory_with_profiles() and the S3 scanner recognise.

    Falls back to promote_image_to_asset() when given a single/empty image list
    so callers don't need to branch.
    """
    paths = [p for p in (image_paths or []) if p and os.path.exists(p)][:max_images]

    if not paths:
        return {"status": "failed", "error": f"No valid reference images provided for '{asset_name}'."}

    cat_folder = category.title()  # e.g. "Characters", "Locations"
    asset_dir = os.path.join("output", "users", user, "Assets", cat_folder, asset_name)
    os.makedirs(asset_dir, exist_ok=True)

    try:
        logs = []
        written = []          # (local_path, filename) for S3 sync
        ref_locations = {}    # {index: local path} for details.json

        # 1. Copy each reference image as ref_N.<ext>
        for i, src in enumerate(paths, start=1):
            ext = os.path.splitext(src)[1] or ".png"
            fname = f"ref_{i}{ext}"
            dest = os.path.join(asset_dir, fname)
            shutil.copy(src, dest)
            written.append((dest, fname))
            ref_locations[i] = dest

        # 2. default.<ext> mirrors ref_1 so every legacy single-image consumer
        #    (which reads default_img/path as one string) keeps working.
        first_ext = os.path.splitext(paths[0])[1] or ".png"
        default_path = os.path.join(asset_dir, f"default{first_ext}")
        shutil.copy(paths[0], default_path)
        written.append((default_path, f"default{first_ext}"))

        # 3. Optional voice sample (Characters only)
        voice_dest = None
        if voice_path and os.path.exists(voice_path):
            v_ext = os.path.splitext(voice_path)[1] or ".mp3"
            voice_dest = os.path.join(asset_dir, f"voice_sample{v_ext}")
            shutil.copy(voice_path, voice_dest)
            written.append((voice_dest, f"voice_sample{v_ext}"))

        logs.append(f"✅ Saved {len(paths)} reference image(s) to {asset_dir}")
        if voice_dest:
            logs.append("🎙️ Voice sample attached")

        # 4. Metadata (superset of promote_image_to_asset's details.json)
        details = {
            "name": asset_name,
            "prompt": prompt,
            "category": category,
            "created": str(datetime.datetime.now()),
            "default_img": ref_locations[1],
            "reference_images": [ref_locations[i] for i in sorted(ref_locations)],
            "voice_sample": voice_dest,
        }
        json_path = os.path.join(asset_dir, "details.json")
        with open(json_path, "w") as f:
            json.dump(details, f, indent=2)

        # 5. S3 Sync — same key layout as promote_image_to_asset
        bucket = os.getenv("S3_BUCKET_NAME")
        if bucket:
            try:
                for local_p, fname in written:
                    key = f"users/{user}/Assets/{cat_folder}/{asset_name}/{fname}"
                    with open(local_p, "rb") as f:
                        upload_file_obj(f, key)
                key_json = f"users/{user}/Assets/{cat_folder}/{asset_name}/details.json"
                with open(json_path, "rb") as f:
                    upload_file_obj(f, key_json)
                logs.append("☁️ Synced to Cloud")
            except Exception as se:
                logs.append(f"⚠️ Cloud sync failed: {se}")

        # 6. CRITICAL: Invalidate the manifest cache or the new profile stays hidden.
        manifest_cache = os.path.join("output", "users", user, "Assets", "user_manifest.json")
        if os.path.exists(manifest_cache):
            os.remove(manifest_cache)
            logs.append("♻️ Manifest Cache Invalidated")

        return {
            "status": "success",
            "logs": "\n".join(logs),
            "asset_path": ref_locations[1],
            "reference_images": details["reference_images"],
            "voice_sample": voice_dest,
        }

    except Exception as e:
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    assets = load_assets()
    print(json.dumps(assets, indent=2))
