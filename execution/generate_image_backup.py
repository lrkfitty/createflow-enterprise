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
    api_key = os.getenv("GOOGLE_IMAGE_KEY") or os.getenv("GOOGLE_API_KEY")
    logs = ["--- Attempting Generation with Nano Banana 2 (Restored) ---"]
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    positive_prompt = prompt_data.get("positive_prompt", "")
    
    # SYSTEM PREAMBLE (Force Continuity)
    system_instruction = (
        "SYSTEM INSTRUCTION: You are a continuity engine. Your primary goal is to generate the scene described below "
        "while EXPERTLY matching the visual identities of the provided character reference images. "
        "You must match their face, hair, and outfit details exactly. Do not hallucinate new features. \n\n"
    )
    if "SYSTEM INSTRUCTION" not in positive_prompt:
        positive_prompt = system_instruction + positive_prompt
    aspect_ratio = prompt_data.get("aspect_ratio")
    if aspect_ratio and aspect_ratio.lower() != "auto":
        # Inject AR into the prompt text as the API does not support the 'aspectRatio' field in generateContent
        positive_prompt = f"IMAGE ASPECT RATIO: {aspect_ratio}. " + positive_prompt

    # --- UNPACK ASSETS (Fix for World Builder / Char Studio) ---
    # If explicit args are missing, try to find them in the 'assets' list
    if not reference_image_path and "assets" in prompt_data:
        for a in prompt_data["assets"]:
            l = a.get("label", "")
            p = a.get("path")
            # Heuristics to map labels to roles
            if "Main Character" in l or "Reference Character" in l or "Cast:" in l:
                reference_image_path = p
    
    if not outfit_path and "assets" in prompt_data:
        for a in prompt_data["assets"]:
            l = a.get("label", "")
            p = a.get("path")
            if "Outfit" in l:
                outfit_path = p
                
    if not vibe_path and "assets" in prompt_data:
        for a in prompt_data["assets"]:
            l = a.get("label", "")
            p = a.get("path")
            if "Vibe" in l or "Location" in l or "Style" in l:
                vibe_path = p

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
                    
                    # Resize if too large (Max 1536px long edge)
                    max_dim = 1536
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
                asset_parts.append({
                    "text": f"\n[VISUAL ID: {label}]\n"
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

            # Case D: Failure / Skip
            elif not b64_data:
                 local_logs.append(f"⚠️ SKIPPED ASSET: {label}. Path/URL invalid or inaccessible: '{img_path}'")
                 
            total_asset_time = time.time() - t_start
            if total_asset_time > 2.0:
                local_logs.append(f"⚠️ Slow Asset Processing for {label}: {total_asset_time:.2f}s")
            
            return asset_parts, local_logs

        # --- Main Logic for Google API ---
        logs.append(f"Prompt sent to Google: '{positive_prompt[:100]}...'")
        logs.append(f"Aspect Ratio: {aspect_ratio}")
        
        if not api_key:
            raise Exception("Missing GOOGLE_API_KEY or GOOGLE_IMAGE_KEY in .env")

        # Prepare multimodal input
        contents = []
        all_asset_logs = []

        # 1. Reference Image (if provided)
        if reference_image_path:
            ref_parts, ref_logs = process_single_asset({"path": reference_image_path, "label": "Reference Character"})
            contents.extend(ref_parts)
            all_asset_logs.extend(ref_logs)

        # 2. Outfit Image (if provided)
        if outfit_path:
            outfit_parts, outfit_logs = process_single_asset({"path": outfit_path, "label": "Outfit for Character"})
            contents.extend(outfit_parts)
            all_asset_logs.extend(outfit_logs)

        # 3. Vibe Image (if provided)
        if vibe_path:
            vibe_parts, vibe_logs = process_single_asset({"path": vibe_path, "label": "Vibe/Style Reference"})
            contents.extend(vibe_parts)
            all_asset_logs.extend(vibe_logs)

        # Add the main text prompt
        contents.append({"text": positive_prompt})
        
        # Add all asset processing logs to main logs
        logs.extend(all_asset_logs)

        payload = {
            "contents": [
                {
                    "parts": contents
                }
            ],
            "generationConfig": {
                "temperature": 0.4
            }
        }
        
        logs.append(f"Sending request to Google API for model: {model_name}")
        
        # Extended Retry Logic for High Load (User requested)
        max_retries = 10
        retry_delay = 2 # Start with 2 seconds
        
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
                                    
                                    # S3 Upload (Preserved)
                                    s3_url = None
                                    if os.getenv("S3_BUCKET_NAME"):
                                        try:
                                            from execution.s3_uploader import upload_file_obj
                                            s3_key = f"generated/{filename}"
                                            with open(filepath, "rb") as f_up:
                                                s3_url = upload_file_obj(f_up, object_name=s3_key)
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
                    
                    # If we get here, no image was found in a 200 OK response
                    logs.append(f"⚠️ Response OK but no image found. Raw: {str(result)[:200]}...")
                    # Even 200s can be empty if filtered completely, treated as fail here to trigger potential fallback or feedback
                    raise Exception("Response received but no image parts found. (Likely safety filtered).")
                elif response.status_code == 503:
                    if attempt < max_retries:
                        logs.append(f"⚠️ Server Overloaded (503). Retrying in {retry_delay}s... ({attempt+1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 30) # Cap delay at 30s
                        continue
                    else:
                        raise Exception("Model Overloaded (503) after multiple retries. Try again later.")
                
                else:
                     logs.append(f"❌ Error {response.status_code}: {response.text}")
                     raise Exception(f"API Error {response.status_code}")
                     
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                     logs.append(f"⚠️ Network Error: {e}. Retrying in {retry_delay}s...")
                     time.sleep(retry_delay)
                     retry_delay = min(retry_delay * 2, 30)
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
