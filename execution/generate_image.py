import os
import json
import time
import requests
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv(override=True)

def generate_image_from_prompt(prompt_data, output_folder="output", reference_image_path=None, outfit_path=None, vibe_path=None):
    """
    Main Entry Point. Dispatches to the correct model engine.
    Returns: dict {"status": "success"|"failed", "image_path": str|None, "logs": str}
    """
    # Dispatch to Atlas Cloud API model
    return generate_image_nano(prompt_data, output_folder, reference_image_path, outfit_path, vibe_path)

def generate_image_nano(prompt_data, output_folder, reference_image_path, outfit_path, vibe_path):
    """
    Generates using Google Nano Banana 2 via the Atlas Cloud API.
    """
    load_dotenv(override=True)
    api_key = os.getenv("ATLASCLOUD_API_KEY")
    logs = ["--- Attempting Generation with Nano Banana 2 via Atlas Cloud API ---"]
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    positive_prompt = prompt_data.get("positive_prompt", "")
    
    # Check if this is an environment still (Empty Set Mandate)
    is_empty_env = prompt_data.get("is_environment_still", False) or "PURE EMPTY SET" in positive_prompt or "NO PEOPLE" in positive_prompt or "ENVIRONMENT" in prompt_data.get("model_type", "").upper()
    has_explicit_people = any(w in positive_prompt.lower() for w in ["extras", "crowd", "person", "character", "actor", "standing", "sitting", "portrait", "woman", "man"])
    
    if is_empty_env and not has_explicit_people:
        system_instruction = (
            "PURE EMPTY ARCHITECTURAL SET MANDATE: You are a master film production location designer. "
            "Your task is to generate a PURE EMPTY cinematic film location set still. "
            "STRICTLY DO NOT INCLUDE ANY PEOPLE, CHARACTERS, HUMAN FIGURES, ACTORS, OR SILHOUETTES IN THIS IMAGE. "
            "Focus 100% purely on empty architectural space, set design, furniture, lighting, and raw surface textures. \n\n"
        )
        if "PURE EMPTY ARCHITECTURAL SET MANDATE" not in positive_prompt:
            positive_prompt = system_instruction + positive_prompt
        
    multi_ref_instruction = (
        "MULTI-REFERENCE FUSION MODE: Multiple reference images of the SAME person have been provided. "
        "You MUST fuse all provided facial references into ONE single composite identity. "
        "Analyze all reference images together and extract the definitive facial structure, skin tone, "
        "eye shape, nose, lips, and distinctive features. The output must portray ONE person whose face "
        "is consistent across all provided references with natural unretouched skin texture. \n\n"
    )
    aspect_ratio = prompt_data.get("aspect_ratio")
    image_size = prompt_data.get("image_size", "1K")  # "512px", "1K", "2K", "4K"
    if aspect_ratio and aspect_ratio.lower() != "auto":
        positive_prompt = f"IMAGE ASPECT RATIO: {aspect_ratio}. " + positive_prompt

    all_cast_members = []  # List of {path, label}
    all_outfits = []  # List of {path, label}
    all_env_refs = []  # List of {path, label}
    location_ref = None
    
    if "assets" in prompt_data:
        for a in prompt_data["assets"]:
            l = a.get("label", "")
            p = a.get("path")
            
            if "Main Character" in l or "Reference Character" in l or "Cast:" in l:
                all_cast_members.append({"path": p, "label": l})
            elif "Outfit" in l:
                all_outfits.append({"path": p, "label": l})
            elif "Vibe" in l or "Location" in l or "Style" in l or "Environment" in l or "Anchor" in l or "Master" in l:
                all_env_refs.append({"path": p, "label": l})
                location_ref = p
    
    if reference_image_path and not all_cast_members:
        all_cast_members.append({"path": reference_image_path, "label": "Main Character"})
    if outfit_path and not all_outfits:
        all_outfits.append({"path": outfit_path, "label": "Outfit: Primary"})
    if vibe_path and not location_ref:
        location_ref = vibe_path
        all_env_refs.append({"path": vibe_path, "label": "Scene Location/Vibe Anchor"})

    if len(all_cast_members) >= 2:
        import re as _re
        base_names = set()
        for cm in all_cast_members:
            lbl = cm.get("label", "")
            base = _re.sub(r'\s*\(Ref \d+\)', '', lbl).strip()
            base_names.add(base)
        if len(base_names) == 1:
            positive_prompt = multi_ref_instruction + positive_prompt

    try:
        requested_model = prompt_data.get("model_type") or prompt_data.get("model") or ""
        if "gpt" in str(requested_model).lower() or "openai" in str(requested_model).lower() or "dalle" in str(requested_model).lower():
            model_type = "gpt"
        elif "wan" in str(requested_model).lower() or "alibaba" in str(requested_model).lower():
            model_type = "wan"
        elif "seedream" in str(requested_model).lower() or "bytedance" in str(requested_model).lower():
            model_type = "seedream"
        else:
            model_type = "nano"
            
        logs.append(f"Selected Atlas Cloud Model Engine: {model_type}")
        url = "https://api.atlascloud.ai/api/v1/model/generateImage"
        headers = { 
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        # Helper to process local or remote images and get Base64 URI
        def process_single_asset(asset_item):
            t_start = time.time()
            local_logs = []
            b64_uri = None
            label_text = None
            
            img_path = asset_item.get("path")
            label = asset_item.get("label", "Context")
            
            import base64
            b64_data = None
            mime_type = "image/jpeg"

            def process_and_encode(img_bytes, mime_type):
                try:
                    from PIL import Image
                    from io import BytesIO
                    img = Image.open(BytesIO(img_bytes))
                    
                    max_dim = 1280
                    if max(img.width, img.height) > max_dim:
                        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                        local_logs.append(f"multimodal: Resized {label} to {img.width}x{img.height}")
                        
                    if img.mode in ('RGBA', 'P'): img = img.convert('RGB')
                    
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=85)
                    return base64.b64encode(buffer.getvalue()).decode('utf-8'), "image/jpeg"
                except Exception as e:
                    local_logs.append(f"⚠️ Resize Warning for {label}: {e}. Using raw bytes.")
                    return base64.b64encode(img_bytes).decode('utf-8'), mime_type

            # Try local recovery first if it is an S3 URL representing a local file
            if img_path and img_path.startswith(('http://', 'https://')) and "users/" in img_path:
                 try:
                      local_rel = img_path.split(".amazonaws.com/")[1].split("?")[0]
                      local_abs = os.path.join(os.getcwd(), "output", local_rel)
                      if os.path.exists(local_abs):
                           img_path = local_abs
                 except Exception:
                      pass

            # Case A: URL
            if img_path and img_path.startswith(('http://', 'https://')):
                try:
                    t_dl_start = time.time()
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    resp = requests.get(img_path, headers=headers, timeout=(5, 30)) 
                    resp.raise_for_status()
                    dl_time = time.time() - t_dl_start
                    
                    b64_data, mime_type = process_and_encode(resp.content, "image/jpeg") 
                    local_logs.append(f"multimodal: Downloaded {label} from URL ({dl_time:.2f}s)")
                except Exception as e:
                    local_logs.append(f"⚠️ Failed to download {label}: {e}")
                    
                    # Clean path fallback
                    clean_path = img_path.split("?")[0]
                    if clean_path.startswith("output/") and os.path.exists(clean_path):
                         try:
                             with open(clean_path, "rb") as image_file:
                                 b64_data, mime_type = process_and_encode(image_file.read(), "image/jpeg")
                             local_logs.append(f"multimodal: Recovered {label} from local output path")
                         except Exception:
                             pass
            
            # Case B: Local File
            elif img_path and os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as image_file:
                        raw_bytes = image_file.read()
                        b64_data, mime_type = process_and_encode(raw_bytes, "image/jpeg")
                    local_logs.append(f"multimodal: Included {label} reference (Local)")
                except Exception as e:
                    local_logs.append(f"⚠️ Failed to read local file {label}: {e}")

            # Case C: Check relative in current directory
            elif img_path:
                local_alt = os.path.join(os.getcwd(), img_path)
                if os.path.exists(local_alt):
                     try:
                         with open(local_alt, "rb") as image_file:
                             raw_bytes = image_file.read()
                             b64_data, mime_type = process_and_encode(raw_bytes, "image/jpeg")
                         local_logs.append(f"multimodal: Included {label} reference (Local Alt)")
                     except Exception:
                         pass

            if b64_data:
                b64_uri = f"data:{mime_type};base64,{b64_data}"
                role_instruction = ""
                if "Cast:" in label or "Main Character" in label or "Reference Character" in label:
                    role_instruction = " (FACE & IDENTITY SOURCE - MATCH EXACTLY)"
                elif "Outfit" in label:
                    role_instruction = " (CLOTHING REFERENCE ONLY - IGNORE FACE/IDENTITY)"
                label_text = f"\n[VISUAL ID: {label}{role_instruction}]\n"
            
            # Case C: Text-only Context
            elif not b64_data and label and "Outfit for" in label:
                 label_text = f"IMPORTANT VISUAL CONTEXT: {label}"
                 local_logs.append(f"multimodal: Included text context: {label}")

            # Case E: Celebrity
            elif not b64_data and asset_item.get("celebrity_desc"):
                celeb_desc = asset_item["celebrity_desc"]
                label_text = (
                    f"\n[VISUAL IDENTITY: {label} — TEXT-BASED REFERENCE]\n"
                    f"Recreate this person's appearance with high fidelity based on the following description:\n"
                    f"{celeb_desc}\n"
                    f"Match their face, skin tone, hair color and style, eye shape, and all distinctive features exactly. "
                    f"Treat this description as if you had received a photograph of them.\n"
                )
                local_logs.append(f"multimodal: Celebrity text reference injected for {label}")

            elif not b64_data:
                 local_logs.append(f"⚠️ SKIPPED ASSET: {label}. Path/URL invalid or inaccessible: '{img_path}'")
                 
            total_asset_time = time.time() - t_start
            return b64_uri, label_text, local_logs

        if not api_key:
            raise Exception("Missing ATLASCLOUD_API_KEY in .env")

        # Collect assets for batch processing
        assets_to_process = []
        for c in all_cast_members: assets_to_process.append(c)
        for o in all_outfits: assets_to_process.append(o)
        for e in all_env_refs:
            if e not in assets_to_process: assets_to_process.append(e)
        if location_ref and not any(e.get("path") == location_ref for e in all_env_refs):
            assets_to_process.append({"path": location_ref, "label": "Scene Location/Vibe"})
        
        import concurrent.futures
        processed_assets_map = {}
        all_asset_logs = []
        
        if assets_to_process:
            logs.append(f"⚡ Parallel processing {len(assets_to_process)} assets...")
            t_batch_start = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_asset = {executor.submit(process_single_asset, asset): asset for asset in assets_to_process}
                for future in concurrent.futures.as_completed(future_to_asset):
                     original_asset = future_to_asset[future]
                     try:
                         res_uri, res_label, res_logs = future.result()
                         processed_assets_map[original_asset.get("path")] = (res_uri, res_label, res_logs)
                     except Exception as e:
                         logs.append(f"⚠️ Worker Error: {e}")

            logs.append(f"⚡ Assets ready in {time.time() - t_batch_start:.2f}s")

        # Interleave assets and create positional label prompts
        input_images = []
        prompt_injections = []
        image_index = 0
        
        for idx, cast_member in enumerate(all_cast_members):
            char_label = cast_member.get("label", "")
            char_name = None
            if "Cast:" in char_label:
                char_name = char_label.split("Cast:")[-1].strip()
            elif "Main Character" in char_label:
                char_name = "Main Character"
                
            cast_uri, cast_label, cast_logs = processed_assets_map.get(cast_member.get("path"), (None, None, []))
            all_asset_logs.extend(cast_logs)
            
            if cast_uri:
                input_images.append(cast_uri)
                prompt_injections.append(f"Image {image_index}: {cast_label.strip()}")
                image_index += 1
            elif cast_label:
                prompt_injections.append(cast_label.strip())
                
            matched_outfit = None
            for outfit in all_outfits:
                outfit_label = outfit.get("label", "")
                normalized_label = ' '.join(outfit_label.split())
                if char_name and f"Outfit for {char_name}" in normalized_label:
                    matched_outfit = outfit
                    break
                elif idx == 0 and normalized_label.startswith("Outfit:") and "for" not in normalized_label.lower():
                    matched_outfit = outfit
                    break
                    
            if matched_outfit:
                outfit_uri, outfit_label, outfit_logs = processed_assets_map.get(matched_outfit.get("path"), (None, None, []))
                all_asset_logs.extend(outfit_logs)
                
                if outfit_uri:
                    input_images.append(outfit_uri)
                    prompt_injections.append(f"Image {image_index}: {outfit_label.strip()}")
                    prompt_injections.append(f"⚠️ CRITICAL: The character in Image {image_index-1} ({char_name}) MUST wear the exact outfit shown in Image {image_index}.")
                    image_index += 1
                    logs.append(f"✅ Paired {char_name} with {matched_outfit.get('label', 'outfit')}")
                elif outfit_label:
                    prompt_injections.append(f"⚠️ CRITICAL: The character ({char_name}) MUST wear this outfit: {outfit_label.strip()}")
                    
        if all_env_refs:
            for e_item in all_env_refs:
                e_path = e_item.get("path")
                e_lbl = e_item.get("label", "Environment Reference")
                e_uri, _, e_logs = processed_assets_map.get(e_path, (None, None, []))
                all_asset_logs.extend(e_logs)
                if e_uri and e_uri not in input_images:
                    input_images.append(e_uri)
                    prompt_injections.append(f"Image {image_index}: Base Environment Master Reference ({e_lbl}). Match architectural layout, walls, materials, and lighting.")
                    image_index += 1
        elif location_ref:
            loc_uri, loc_label, loc_logs = processed_assets_map.get(location_ref, (None, None, []))
            all_asset_logs.extend(loc_logs)
            if loc_uri and loc_uri not in input_images:
                input_images.append(loc_uri)
                prompt_injections.append(f"Image {image_index}: Vibe/Location reference image. Use this scene environment/background.")
                image_index += 1
                
        if prompt_injections:
            binding_text = "\n".join(prompt_injections)
            positive_prompt = f"IMAGE REFERENCE BINDINGS:\n{binding_text}\n\n" + positive_prompt
            
        logs.extend(all_asset_logs)

        # Build payload for Atlas Cloud API
        ar_val = "9:16"
        if aspect_ratio and aspect_ratio.lower() != "auto":
            ar_val = aspect_ratio
            
        res_val = "4k"
        if image_size:
            res_val = image_size.lower()

        has_images = len(input_images) > 0
        
        if model_type == "wan":
            if has_images:
                model_name = "alibaba/wan-2.7-pro/image-edit"
                payload = {
                    "model": model_name,
                    "prompt": positive_prompt,
                    "images": input_images,
                    "size": "2K" if res_val in ["2k", "4k"] else "1K",
                    "thinking_mode": False,
                    "seed": -1,
                    "enable_sync_mode": False,
                    "enable_base64_output": False
                }
            else:
                model_name = "alibaba/wan-2.7-pro/text-to-image"
                payload = {
                    "model": model_name,
                    "prompt": positive_prompt,
                    "aspect_ratio": ar_val,
                    "resolution": res_val,
                    "enable_sync_mode": False,
                    "enable_base64_output": False
                }
        elif model_type == "gpt":
            if has_images:
                model_name = "openai/gpt-image-2-developer/edit"
                payload = {
                    "model": model_name,
                    "prompt": positive_prompt,
                    "images": input_images,
                    "resolution": res_val,
                    "enable_sync_mode": False,
                    "enable_base64_output": False
                }
            else:
                model_name = "openai/gpt-image-2-developer/text-to-image"
                payload = {
                    "model": model_name,
                    "prompt": positive_prompt,
                    "aspect_ratio": ar_val,
                    "resolution": res_val,
                    "enable_sync_mode": False,
                    "enable_base64_output": False
                }
        elif model_type == "seedream":
            if has_images:
                model_name = "bytedance/seedream-v5.0-pro/edit"
                payload = {
                    "model": model_name,
                    "prompt": positive_prompt,
                    "images": input_images,
                    "size": "2048*2048" if res_val in ["2k", "4k"] else "1024*1024",
                    "enable_sync_mode": False,
                    "enable_base64_output": False
                }
            else:
                model_name = "bytedance/seedream-v5.0-pro/text-to-image"
                payload = {
                    "model": model_name,
                    "prompt": positive_prompt,
                    "aspect_ratio": ar_val,
                    "size": "2048*2048" if res_val in ["2k", "4k"] else "1024*1024",
                    "enable_sync_mode": False,
                    "enable_base64_output": False
                }
        else: # nano (google/nano-banana-2)
            if has_images:
                model_name = "google/nano-banana-2/reference-to-image-developer"
                payload = {
                    "model": model_name,
                    "prompt": positive_prompt,
                    "images": input_images,
                    "aspect_ratio": ar_val,
                    "resolution": res_val,
                    "thinking_level": "default",
                    "enable_sync_mode": False,
                    "enable_base64_output": False,
                    "enable_web_search": False
                }
            else:
                model_name = "google/nano-banana-2/text-to-image"
                payload = {
                    "model": model_name,
                    "prompt": positive_prompt,
                    "aspect_ratio": ar_val,
                    "resolution": res_val,
                    "enable_sync_mode": False,
                    "enable_base64_output": False
                }
        
        logs.append(f"Submitting job to Atlas Cloud API for model {model_name}...")
        
        response = None
        for attempt in range(1, 4):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    break
                elif response.status_code in [500, 502, 503, 504, 429]:
                    logs.append(f"⚠️ Atlas Cloud transient HTTP {response.status_code}. Retrying in 3s...")
                    time.sleep(3)
                else:
                    break
            except Exception as req_err:
                logs.append(f"⚠️ Network error on attempt {attempt}: {req_err}")
                time.sleep(3)
                
        if not response or response.status_code != 200:
            raw_err = response.text if response else "No response from server"
            if "<html" in raw_err.lower() or (response and response.status_code in [502, 503, 504]):
                clean_err = "Atlas Cloud API temporary Gateway Timeout (HTTP 502). The server experienced a brief spike. Please click generate again to retry."
            else:
                clean_err = f"Atlas API request failed with status code {response.status_code if response else 'ERR'}: {raw_err[:250]}"
            raise Exception(clean_err)
            
        result_json = response.json()
        prediction_id = result_json["data"]["id"]
        logs.append(f"Task created. Prediction ID: {prediction_id}")
        
        # Poll prediction result
        poll_url = f"https://api.atlascloud.ai/api/v1/model/prediction/{prediction_id}"
        logs.append("Polling for completion...")
        
        max_retries = 150
        output_url = None
        for i in range(max_retries):
            time.sleep(2)
            poll_resp = requests.get(poll_url, headers={"Authorization": f"Bearer {api_key}"})
            if poll_resp.status_code != 200:
                logs.append(f"⚠️ Polling error: HTTP {poll_resp.status_code}")
                continue
                
            poll_data = poll_resp.json()
            task_status = poll_data.get("data", {}).get("status")
            
            if i % 10 == 0:
                logs.append(f"   ... [{i+1}/150] Status: {task_status}")
                
            if task_status in ["completed", "succeeded"]:
                outputs = poll_data.get("data", {}).get("outputs", [])
                if not outputs:
                    raise Exception("Atlas API returned success but no outputs found.")
                output_url = outputs[0]
                logs.append(f"✅ Generation Successful! URL: {output_url}")
                break
            elif task_status == "failed":
                err_msg = poll_data.get("data", {}).get("error") or "Unknown error"
                raise Exception(f"Generation failed: {err_msg}")
        else:
            raise Exception("Polling timed out after 5 minutes.")

        # Download result
        import uuid
        prefix = "gen_nano2"
        if model_type == "wan":
            prefix = "wan27"
        elif model_type == "gpt":
            prefix = "gptimg2"
        filename = f"{prefix}_{int(time.time())}_{str(uuid.uuid4())[:8]}.jpg"
        filepath = os.path.join(output_folder, filename)
        
        logs.append(f"Downloading output image from: {output_url}")
        dl_resp = requests.get(output_url)
        if dl_resp.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(dl_resp.content)
            logs.append(f"✅ Image saved locally: {filename}")
        else:
            raise Exception(f"Failed to download output image: HTTP {dl_resp.status_code}")
            
        thumb_filepath = None
        thumb_filename = None
        try:
            from PIL import Image
            from io import BytesIO
            thumb_filename = filename.rsplit('.', 1)[0] + "_thumb.jpg"
            thumb_filepath = os.path.join(output_folder, thumb_filename)
            img_for_thumb = Image.open(BytesIO(dl_resp.content))
            if img_for_thumb.mode in ('RGBA', 'P'): img_for_thumb = img_for_thumb.convert('RGB')
            img_for_thumb.thumbnail((512, 512), Image.Resampling.LANCZOS)
            img_for_thumb.save(thumb_filepath, format="JPEG", quality=80)
            logs.append(f"✅ Created thumbnail: {thumb_filename}")
        except Exception as e:
            logs.append(f"⚠️ Failed to create thumbnail: {e}")

        s3_url = None
        if os.getenv("S3_BUCKET_NAME"):
            try:
                from execution.s3_uploader import upload_file_obj
                if "users" in output_folder:
                    relative_path = output_folder.replace("output/", "").replace("output\\", "")
                    s3_key = f"{relative_path}/{filename}"
                    if thumb_filename:
                        thumb_s3_key = f"{relative_path}/{thumb_filename}"
                else:
                    s3_key = f"generated/{filename}"
                    if thumb_filename:
                        thumb_s3_key = f"generated/{thumb_filename}"
                        
                with open(filepath, "rb") as f_up:
                    s3_url = upload_file_obj(f_up, object_name=s3_key)
                if thumb_filepath:
                    with open(thumb_filepath, "rb") as f_up_thumb:
                        upload_file_obj(f_up_thumb, object_name=thumb_s3_key)
                logs.append(f"☁️ Uploaded to S3: {s3_key}")
            except Exception as e:
                logs.append(f"⚠️ S3 Upload Warning: {e}")
                
        return {
            "status": "success",
            "image_path": filepath,
            "s3_url": s3_url,
            "model_used": model_name,
            "logs": "\n".join(logs)
        }
    except Exception as e:
        logs.append(f"❌ General Error: {e}")
        return {
            "status": "failed",
            "image_path": None,
            "error": str(e),
            "model_used": requested_model or "google/nano-banana-2",
            "logs": "\n".join(logs)
        }
