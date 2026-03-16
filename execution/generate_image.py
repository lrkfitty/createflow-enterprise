import os
import json
import time
import requests
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

def generate_image_from_prompt(prompt_data, output_folder="output", reference_image_path=None, outfit_path=None, vibe_path=None):
    """
    Main Entry Point. Dispatches to the correct model engine.
    Returns: dict {"status": "success"|"failed", "image_path": str|None, "logs": str}
    """
    
    # 1. Dispatch (Strictly Cloud)
    # Default to Nano Banana 2
    return generate_image_nano(prompt_data, output_folder, reference_image_path, outfit_path, vibe_path)

def generate_image_nano(prompt_data, output_folder, reference_image_path, outfit_path, vibe_path):
    """
    Generates using Google Nano Banana 2 (Gemini 3.1 Flash Image).
    """
    # Try specific Image Key first (for Paid tier), else fallback to standard key
    load_dotenv(override=True)
    api_key = os.getenv("GOOGLE_IMAGE_KEY") or os.getenv("GOOGLE_API_KEY")
    logs = ["--- Attempting Generation with Nano Banana 2 (Character-Outfit Pairing Enabled) ---"]
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    positive_prompt = prompt_data.get("positive_prompt", "")
    
    # SYSTEM PREAMBLE (Force Continuity)
    system_instruction = (
        "SYSTEM INSTRUCTION: You are a continuity engine. Your primary goal is to generate the scene described below "
        "while EXPERTLY matching the visual identities of the provided character reference images. "
        "You must match their face, hair, and outfit details exactly. Do not hallucinate new features. Pay close attention to character-outfit pairings indicated by binding text. \n\n"
    )
    multi_ref_instruction = (
        "MULTI-REFERENCE FUSION MODE: Multiple reference images of the SAME person have been provided. "
        "You MUST fuse all provided facial references into ONE single composite identity. "
        "Analyze all reference images together and extract the definitive facial structure, skin tone, "
        "eye shape, nose, lips, and distinctive features. The output must portray ONE person whose face "
        "is consistent across all provided references. Do NOT treat these as different people. \n\n"
    )
    if "SYSTEM INSTRUCTION" not in positive_prompt:
        positive_prompt = system_instruction + positive_prompt
    aspect_ratio = prompt_data.get("aspect_ratio")
    image_size = prompt_data.get("image_size", "1K")  # "512px", "1K", "2K", "4K" (uppercase K required)
    if aspect_ratio and aspect_ratio.lower() != "auto":
        # Keep AR in prompt text as backup hint, but also pass via imageConfig
        positive_prompt = f"IMAGE ASPECT RATIO: {aspect_ratio}. " + positive_prompt

    # --- UNPACK ASSETS (Enhanced Multi-Character Support with Pairing) ---
    # Collect ALL cast members and outfits
    all_cast_members = []  # List of {path, label}
    all_outfits = []  # List of {path, label}
    location_ref = None
    
    if "assets" in prompt_data:
        for a in prompt_data["assets"]:
            l = a.get("label", "")
            p = a.get("path")
            
            # Collect ALL characters (Main + Friends)
            if "Main Character" in l or "Reference Character" in l or "Cast:" in l:
                all_cast_members.append({"path": p, "label": l})
            
            # Collect ALL outfits
            elif "Outfit" in l:
                all_outfits.append({"path": p, "label": l})
                    
            # Collect location/vibe
            elif "Vibe" in l or "Location" in l or "Style" in l:
                location_ref = p
    
    # Legacy compatibility: use old parameters if provided and lists are empty
    if reference_image_path and not all_cast_members:
        all_cast_members.append({"path": reference_image_path, "label": "Main Character"})
    if outfit_path and not all_outfits:
        all_outfits.append({"path": outfit_path, "label": "Outfit: Primary"})
    if vibe_path and not location_ref:
        location_ref = vibe_path

    # MULTI-REFERENCE FUSION: detect when same character has 2+ images (same base name)
    # e.g. "Cast: Alex (Ref 1)", "Cast: Alex (Ref 2)" → activate composite fusion mode
    if len(all_cast_members) >= 2:
        import re as _re
        base_names = set()
        for cm in all_cast_members:
            lbl = cm.get("label", "")
            base = _re.sub(r'\s*\(Ref \d+\)', '', lbl).strip()
            base_names.add(base)
        # If all refs share one base name → multi-angle of same person; prepend fusion instruction
        if len(base_names) == 1:
            positive_prompt = multi_ref_instruction + positive_prompt

    try:
        # Switching to explicit Image Generation model from list (Nano/1.5 aliases are unstable)
        # Use known stable version
        model_name = 'gemini-3.1-flash-image-preview' # Nano Banana 2 (Fast + High Fidelity)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = { "Content-Type": "application/json" }

        # Helper to attach image or text context to payload
        def process_single_asset(asset_item):
            """
            Worker function for parallel processing.
            Returns a list of parts (or empty list) to append to the main payload.
            """
            t_start = time.time()
            local_logs = []
            asset_parts = []
            
            img_path = asset_item.get("path")
            label = asset_item.get("label", "Context")
            
            import base64 # Import locally to ensure availability in thread
            b64_data = None
            mime_type = "image/jpeg"

            # Helper to resize and encode
            def process_and_encode(img_bytes, mime_type):
                
                try:
                    from PIL import Image
                    from io import BytesIO
                    img = Image.open(BytesIO(img_bytes))
                    
                    # Resize if too large (Max 1280px long edge - Balanced Quality/Speed)
                    max_dim = 1280
                    if max(img.width, img.height) > max_dim:
                        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                        local_logs.append(f"multimodal: Resized {label} to {img.width}x{img.height}")
                        
                    # Convert to RGB (Strip Alpha) for JPEG optimization
                    if img.mode in ('RGBA', 'P'): img = img.convert('RGB')
                    
                    # Save to Buffer as JPEG 85%
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=85)
                    return base64.b64encode(buffer.getvalue()).decode('utf-8'), "image/jpeg"
                    
                except Exception as e:
                    local_logs.append(f"⚠️ Resize Warning for {label}: {e}. Using raw bytes.")
                    return base64.b64encode(img_bytes).decode('utf-8'), mime_type

            # Case A: URL
            if img_path and img_path.startswith(('http://', 'https://')):
                try:
                    t_dl_start = time.time()
                    # Strict timeout: 5s connect, 30s read. Accommodates 5MB+ files on slow links.
                    resp = requests.get(img_path, timeout=(5, 30)) 
                    resp.raise_for_status()
                    dl_time = time.time() - t_dl_start
                    
                    b64_data, mime_type = process_and_encode(resp.content, "image/jpeg") 
                    local_logs.append(f"multimodal: Downloaded {label} from URL ({dl_time:.2f}s)")
                except Exception as e:
                    local_logs.append(f"⚠️ Failed to download {label}: {e}")
            
            # Case B: Local File
            elif img_path and os.path.exists(img_path) and img_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                with open(img_path, "rb") as image_file:
                    raw_bytes = image_file.read()
                    b64_data, mime_type = process_and_encode(raw_bytes, "image/jpeg")
                local_logs.append(f"multimodal: Included {label} reference (Local)")

            # Add to Payload if we have data
            if b64_data:
                # FIX: STRONG BINDING - Explicitly tag the image for the model
                role_instruction = ""
                if "Cast:" in label or "Main Character" in label or "Reference Character" in label:
                    role_instruction = " (FACE & IDENTITY SOURCE - MATCH EXACTLY)"
                elif "Outfit" in label:
                    role_instruction = " (CLOTHING REFERENCE ONLY - IGNORE FACE/IDENTITY)"

                asset_parts.append({
                    "text": f"\n[VISUAL ID: {label}{role_instruction}]\n"
                })
                    
                asset_parts.append({
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64_data
                    }
                })
            
            # Case C: Text-only Context (e.g. Outfit description without image)
            elif not b64_data and label and "Outfit for" in label:
                 asset_parts.append({
                     "text": f"IMPORTANT VISUAL CONTEXT: {label}"
                 })
                 local_logs.append(f"multimodal: Included text context: {label}")

            # Case E: Celebrity / Named person — text description reference (no image needed)
            elif not b64_data and asset_item.get("celebrity_desc"):
                celeb_desc = asset_item["celebrity_desc"]
                asset_parts.append({
                    "text": (
                        f"\n[VISUAL IDENTITY: {label} — TEXT-BASED REFERENCE]\n"
                        f"Recreate this person's appearance with high fidelity based on the following description:\n"
                        f"{celeb_desc}\n"
                        f"Match their face, skin tone, hair color and style, eye shape, and all distinctive features exactly. "
                        f"Treat this description as if you had received a photograph of them.\n"
                    )
                })
                local_logs.append(f"multimodal: Celebrity text reference injected for {label}")

            # Case D: Failure / Skip
            elif not b64_data:
                 local_logs.append(f"⚠️ SKIPPED ASSET: {label}. Path/URL invalid or inaccessible: '{img_path}'")
                 
            total_asset_time = time.time() - t_start
            if total_asset_time > 2.0:
                local_logs.append(f"⚠️ Slow Asset Processing for {label}: {total_asset_time:.2f}s")
            
            return asset_parts, local_logs

        # --- Main Logic for Google API (WITH CHARACTER-OUTFIT PAIRING) ---
        logs.append(f"Prompt sent to Google: '{positive_prompt[:100]}...'")
        if aspect_ratio:
            logs.append(f"Aspect Ratio: {aspect_ratio}")
        
        if not api_key:
            raise Exception("Missing GOOGLE_API_KEY or GOOGLE_IMAGE_KEY in .env")

        # Prepare multimodal input with PAIRED character+outfit
        contents = []
        all_asset_logs = []

        # PARALLEL PROCESSING: FETCH ALL ASSETS FIRST
        # We need to map assets to their results efficiently
        # Strategy: 
        # 1. Create a list of all unique assets we need to process (Characters + Outfits + Location)
        # 2. Process them in parallel
        # 3. Re-assemble the ordered payload based on the logic below
        
        assets_to_process = []
        # Add cast members
        for c in all_cast_members: assets_to_process.append(c)
        # Add outfits
        for o in all_outfits: assets_to_process.append(o)
        # Add location
        if location_ref: assets_to_process.append({"path": location_ref, "label": "Scene Location/Vibe"})
        
        import concurrent.futures
        processed_assets_map = {} # path -> (parts, logs)
        
        logs.append(f"⚡ Parallel processing {len(assets_to_process)} assets...")
        t_batch_start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # We map the function to the items
            # Note: We need to key by path or object ref. 
            # process_single_asset takes dict.
            future_to_asset = {executor.submit(process_single_asset, asset): asset for asset in assets_to_process}
            
            for future in concurrent.futures.as_completed(future_to_asset):
                 original_asset = future_to_asset[future]
                 try:
                     res_parts, res_logs = future.result()
                     # Store result keyed by path (assuming unique paths, or we accept redundant processing if dupes)
                     processed_assets_map[original_asset.get("path")] = (res_parts, res_logs)
                 except Exception as e:
                     logs.append(f"⚠️ Worker Error: {e}")

        logs.append(f"⚡ Assets ready in {time.time() - t_batch_start:.2f}s")

        # 1. Process Characters + Outfits as INTERLEAVED PAIRS
        logs.append(f"🎭 Assembling {len(all_cast_members)} character(s) with outfit pairing...")
        
        for idx, cast_member in enumerate(all_cast_members):
            char_label = cast_member.get("label", "")
            
            # Extract character name for outfit matching
            char_name = None
            if "Cast:" in char_label:
                char_name = char_label.split("Cast:")[-1].strip()
            elif "Main Character" in char_label:
                char_name = "Main Character"
            
            # Add character reference FIRST (retrieve from map)
            cast_parts, cast_logs = processed_assets_map.get(cast_member.get("path"), ([], []))
            contents.extend(cast_parts)
            all_asset_logs.extend(cast_logs)
            
            # DEBUG: Show what we're trying to match
            logs.append(f"🔍 Trying to find outfit for {char_name} (label: {char_label})")
            
            # IMMEDIATELY pair with their outfit (if found)
            matched_outfit = None
            for outfit in all_outfits:
                outfit_label = outfit.get("label", "")
                # Normalize whitespace (handles "Outfit for  Chels" with extra spaces)
                normalized_label = ' '.join(outfit_label.split())
                
                if char_name and f"Outfit for {char_name}" in normalized_label:
                    matched_outfit = outfit
                    break
                # Case 2: Main character outfit - "Outfit: Name" (no "for")
                elif idx == 0 and normalized_label.startswith("Outfit:") and "for" not in normalized_label.lower():
                    matched_outfit = outfit
                    break
            
            if matched_outfit:
                # Add explicit binding instruction
                contents.append({
                    "text": f"⚠️ CRITICAL: THE CHARACTER SHOWN ABOVE ({char_name}) MUST WEAR THIS EXACT OUTFIT:"
                })
                outfit_parts, outfit_logs = processed_assets_map.get(matched_outfit.get("path"), ([], []))
                contents.extend(outfit_parts)
                all_asset_logs.extend(outfit_logs)
                logs.append(f"✅ Paired {char_name} with {matched_outfit.get('label', 'outfit')}")
            else:
                logs.append(f"⚠️ No outfit found for {char_name}")

        # 2. Location/Vibe (if provided)
        if location_ref:
            vibe_parts, vibe_logs = processed_assets_map.get(location_ref, ([], []))
            contents.extend(vibe_parts)
            all_asset_logs.extend(vibe_logs)

        # 3. Add the main text prompt LAST (after all visual refs)
        contents.append({"text": positive_prompt})
        
        # Add all asset processing logs to main logs
        logs.extend(all_asset_logs)

        # Build imageConfig for native API control
        image_config = {}
        if aspect_ratio and aspect_ratio.lower() != "auto":
            image_config["aspectRatio"] = aspect_ratio
        if image_size:
            image_config["imageSize"] = image_size  # "512px", "1K", "2K", "4K"
        
        gen_config = {
            "temperature": 0.4
        }
        if image_config:
            gen_config["imageConfig"] = image_config
        
        payload = {
            "contents": [
                {
                    "parts": contents
                }
            ],
            "generationConfig": gen_config
        }
        
        logs.append(f"Sending request to Google API for model: {model_name}")
        
        # Extended Retry Logic for High Load (Optimized for UX)
        max_retries = 3  # Reduced from 10 to avoid excessive wait times
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "candidates" in result and len(result["candidates"]) > 0:
                        candidate = result["candidates"][0]
                        # Check for image content
                        if "content" in candidate and "parts" in candidate["content"]:
                             for part in candidate["content"]["parts"]:
                                 if "inlineData" in part:
                                    image_data_b64 = part["inlineData"]["data"]
                                    # Decode and save
                                    image_bytes = base64.b64decode(image_data_b64)
                                    timestamp = int(time.time())
                                    filename = f"gen_nano2_{timestamp}_{str(os.urandom(4).hex())}.jpg"
                                    filepath = os.path.join(output_folder, filename)
                                    with open(filepath, "wb") as f:
                                        f.write(image_bytes)
                                    logs.append(f"✅ Generation Successful. Saved: {filename}")
                                    
                                    # Create thumbnail
                                    thumb_filepath = None
                                    thumb_filename = None
                                    try:
                                        from PIL import Image
                                        from io import BytesIO
                                        thumb_filename = filename.rsplit('.', 1)[0] + "_thumb.jpg"
                                        thumb_filepath = os.path.join(output_folder, thumb_filename)
                                        img_for_thumb = Image.open(BytesIO(image_bytes))
                                        if img_for_thumb.mode in ('RGBA', 'P'): img_for_thumb = img_for_thumb.convert('RGB')
                                        img_for_thumb.thumbnail((512, 512), Image.Resampling.LANCZOS)
                                        img_for_thumb.save(thumb_filepath, format="JPEG", quality=80)
                                        logs.append(f"✅ Created thumbnail: {thumb_filename}")
                                    except Exception as e:
                                        logs.append(f"⚠️ Failed to create thumbnail: {e}")
                                        thumb_filepath = None
                                        thumb_filename = None

                                    # S3 Upload (Preserved)
                                    s3_url = None
                                    if os.getenv("S3_BUCKET_NAME"):
                                        try:
                                            from execution.s3_uploader import upload_file_obj
                                            
                                            # Extract user-specific path from output_folder for S3
                                            # e.g., "output/users/Tytheguyttg/World" -> "users/Tytheguyttg/World/{filename}"
                                            if "users" in output_folder:
                                                relative_path = output_folder.replace("output/", "").replace("output\\", "")
                                                s3_key = f"{relative_path}/{filename}"
                                                if thumb_filename:
                                                    thumb_s3_key = f"{relative_path}/{thumb_filename}"
                                            else:
                                                # Fallback for non-user paths
                                                s3_key = f"generated/{filename}"
                                                if thumb_filename:
                                                    thumb_s3_key = f"generated/{thumb_filename}"
                                                    
                                            with open(filepath, "rb") as f_up:
                                                s3_url = upload_file_obj(f_up, object_name=s3_key)
                                                
                                            if thumb_filepath:
                                                with open(thumb_filepath, "rb") as f_up_thumb:
                                                    upload_file_obj(f_up_thumb, object_name=thumb_s3_key)
                                                    
                                            logs.append(f"☁️ Uploaded to S3: {s3_key} (and thumbnail)")
                                        except Exception as e:
                                            logs.append(f"⚠️ S3 Upload Warning: {e}")
                                            
                                    return {
                                        "status": "success",
                                        "image_path": filepath,
                                        "s3_url": s3_url,
                                        "model_used": model_name,
                                        "logs": "\n".join(logs)
                                    }
                    
                    # If we get here, no image was found in a 200 OK response
                    logs.append(f"⚠️ Response OK but no image found. Raw: {str(result)[:200]}...")
                    # Even 200s can be empty if filtered completely, treated as fail here to trigger potential fallback or feedback
                    raise Exception("Response received but no image parts found. (Likely safety filtered).")
                elif response.status_code in (500, 503):
                    if attempt < max_retries:
                        err_label = "Internal Error (500)" if response.status_code == 500 else "Server Overloaded (503)"
                        logs.append(f"⚠️ {err_label}. Retrying in {retry_delay}s... ({attempt+1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 10)  # Cap delay at 10s
                        continue
                    else:
                        raise Exception(f"Server Error ({response.status_code}) after {max_retries} retries. Try again later.")
                
                else:
                     logs.append(f"❌ Error {response.status_code}: {response.text}")
                     raise Exception(f"API Error {response.status_code}")
                     
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                     logs.append(f"⚠️ Network Error: {e}. Retrying in {retry_delay}s...")
                     time.sleep(retry_delay)
                     retry_delay = min(retry_delay * 2, 10)  # Cap at 10s
                     continue
                else:
                     raise Exception(f"Network Error after retries: {e}")
    except Exception as e:
        logs.append(f"❌ General Error: {e}")
        return {
            "status": "failed",
            "image_path": None,
            "model_used": model_name,
            "logs": "\n".join(logs)
        }

# DALL-E Fallback (Unused but preserved if needed later)
def generate_image_dalle(prompt_data, output_folder):
    pass
