import os
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def extract_last_frame_as_base64(video_path):
    """
    Extracts the last frame of a local video MP4 file as a compressed Base64 JPEG data URI.
    Ensures 100% visual scene continuity without requiring S3 configuration.
    """
    if not video_path or not os.path.exists(video_path):
        return None
    try:
        import cv2
        from PIL import Image
        from io import BytesIO
        
        cap = cv2.VideoCapture(video_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
            ret, frame = cap.read()
            cap.release()
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                max_dim = 1280
                if max(img.width, img.height) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=80)
                encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return f"data:image/jpeg;base64,{encoded}"
        cap.release()
    except Exception as err:
        print(f"Video last frame extraction warning: {err}")
    return None

def image_to_base64_data_uri(img_path_or_url):
    """
    Converts a local file path or HTTP URL to an optimized lightweight base64 data URI.
    Resizes images to max 960px at JPEG quality 75 to keep total request payload lightweight (<2MB)
    and prevent Cloudflare HTTP 502 payload size limit errors.
    """
    if not img_path_or_url:
        return None
        
    # If HTTP URL, try fetching locally to convert to lightweight base64
    if img_path_or_url.startswith(("http://", "https://")):
        try:
            resp = requests.get(img_path_or_url, timeout=8)
            if resp.status_code == 200:
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(resp.content))
                max_dim = 960
                if max(img.width, img.height) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=75)
                encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return f"data:image/jpeg;base64,{encoded}"
        except Exception:
            pass
        return img_path_or_url
        
    if os.path.exists(img_path_or_url):
        try:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(img_path_or_url)
            max_dim = 960
            if max(img.width, img.height) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=75)
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
        except Exception as e:
            print(f"Base64 compression fallback warning for {img_path_or_url}: {e}")
            return None
            
    return None

def generate_wan_image(prompt, image_path, size="2K", output_folder="output", extra_images=None):
    """
    Edits an image using Alibaba Wan 2.7 Image Edit model via Atlas Cloud API.
    Supports up to 9 reference photos for multi-subject control.
    """
    logs = ["--- Starting Wan 2.7 Image Edit (Atlas Cloud API) ---"]
    api_key = os.getenv("ATLASCLOUD_API_KEY")
    
    if not api_key:
        return {"status": "failed", "error": "Missing ATLASCLOUD_API_KEY in environment.", "logs": logs}
        
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    try:
        # Convert image to Base64 URI or keep URL
        logs.append("Processing input image...")
        img_uri = image_to_base64_data_uri(image_path)
        logs.append(f"Source image converted to URI (length: {len(img_uri) if img_uri else 0})")
        
        images_payload = [img_uri] if img_uri else []
        if extra_images:
             for idx, img_p in enumerate(extra_images):
                  if not img_p: continue
                  try:
                       extra_uri = image_to_base64_data_uri(img_p)
                       if extra_uri:
                            images_payload.append(extra_uri)
                            logs.append(f"Encoded extra image reference {idx+2}")
                  except Exception as img_err:
                       logs.append(f"⚠️ Image encoding warning for reference {idx+2}: {img_err}")
        
        generate_url = "https://api.atlascloud.ai/api/v1/model/generateImage"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Build API payload
        payload = {
            "model": "alibaba/wan-2.7-pro/image-edit",
            "prompt": prompt,
            "images": images_payload,
            "size": size,
            "n": 1,
            "thinking_mode": False,
            "seed": -1,
            "enable_sync_mode": False,
            "enable_base64_output": False
        }
        
        logs.append(f"Submitting job to Atlas API for alibaba/wan-2.7-pro/image-edit...")
        response = requests.post(generate_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            return {"status": "failed", "error": f"API Request Failed: HTTP {response.status_code} - {response.text}", "logs": logs}
            
        result_json = response.json()
        if "data" not in result_json or "id" not in result_json["data"]:
            return {"status": "failed", "error": f"Invalid API response structure: {result_json}", "logs": logs}
            
        prediction_id = result_json["data"]["id"]
        logs.append(f"Prediction task created. Task ID: {prediction_id}")
        
        # Poll for result
        poll_url = f"https://api.atlascloud.ai/api/v1/model/prediction/{prediction_id}"
        logs.append("Polling for completion...")
        
        max_retries = 150  # 5 minutes
        for i in range(max_retries):
            time.sleep(2)
            poll_resp = requests.get(poll_url, headers={"Authorization": f"Bearer {api_key}"})
            if poll_resp.status_code != 200:
                logs.append(f"⚠️ Polling warning: HTTP {poll_resp.status_code}")
                continue
                
            poll_data = poll_resp.json()
            task_status = poll_data.get("data", {}).get("status")
            
            if i % 10 == 0:
                logs.append(f"   ... [{i+1}/{max_retries}] Status: {task_status}")
                
            if task_status in ["completed", "succeeded"]:
                outputs = poll_data.get("data", {}).get("outputs", [])
                if not outputs:
                    return {"status": "failed", "error": "API returned success but no outputs found.", "logs": logs}
                output_url = outputs[0]
                logs.append(f"Task completed successfully! Output URL: {output_url}")
                break
            elif task_status == "failed":
                err_msg = poll_data.get("data", {}).get("error") or "Unknown error"
                return {"status": "failed", "error": f"Generation failed: {err_msg}", "logs": logs}
        else:
            return {"status": "failed", "error": "Polling timed out after 5 minutes.", "logs": logs}
            
        # Download the output image
        timestamp = int(time.time())
        filename = f"wan27_edit_{timestamp}.jpg"
        filepath = os.path.join(output_folder, filename)
        
        logs.append(f"Downloading edited image from {output_url}...")
        dl_resp = requests.get(output_url)
        if dl_resp.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(dl_resp.content)
            logs.append(f"✅ Edited image saved to: {filepath}")
            
            # --- Generate Thumbnail for Performance ---
            thumb_filename = None
            try:
                from PIL import Image
                from io import BytesIO
                thumb_filename = f"wan27_edit_{timestamp}_thumb.jpg"
                thumb_filepath = os.path.join(output_folder, thumb_filename)
                
                img_for_thumb = Image.open(BytesIO(dl_resp.content))
                if img_for_thumb.mode in ('RGBA', 'P'): 
                    img_for_thumb = img_for_thumb.convert('RGB')
                img_for_thumb.thumbnail((512, 512), Image.Resampling.LANCZOS)
                img_for_thumb.save(thumb_filepath, format="JPEG", quality=80)
                logs.append(f"✅ Created gallery thumbnail: {thumb_filepath}")
            except Exception as thumb_err:
                logs.append(f"⚠️ Thumbnail Creation Warning: {thumb_err}")
        else:
            return {"status": "failed", "error": f"Failed to download image: HTTP {dl_resp.status_code}", "logs": logs}
            
        # Upload to S3 if bucket is configured
        s3_url = None
        if os.getenv("S3_BUCKET_NAME"):
            try:
                from execution.s3_uploader import upload_file_obj
                if "users" in output_folder:
                    relative_path = output_folder.replace("output/", "").replace("output\\", "")
                    s3_key = f"{relative_path}/{filename}"
                    thumb_s3_key = f"{relative_path}/{thumb_filename}" if thumb_filename else None
                else:
                    s3_key = f"generated/{filename}"
                    thumb_s3_key = f"generated/{thumb_filename}" if thumb_filename else None
                
                with open(filepath, "rb") as f_up:
                    s3_url = upload_file_obj(f_up, object_name=s3_key)
                logs.append(f"☁️ Uploaded to S3: {s3_key}")
                
                if thumb_s3_key and thumb_filename:
                     thumb_full_path = os.path.join(output_folder, thumb_filename)
                     if os.path.exists(thumb_full_path):
                          with open(thumb_full_path, "rb") as f_up_thumb:
                               upload_file_obj(f_up_thumb, object_name=thumb_s3_key)
                          logs.append(f"☁️ Uploaded thumbnail to S3: {thumb_s3_key}")
            except Exception as s3_err:
                logs.append(f"⚠️ S3 Upload Warning: {s3_err}")
                
        return {
            "status": "success",
            "image_path": filepath,
            "s3_url": s3_url,
            "logs": logs
        }
        
    except Exception as e:
        return {"status": "failed", "error": str(e), "logs": logs}

def generate_wan_video(prompt, image_path, resolution="1080P", duration=5, ref_video_path=None, ref_audio_path=None, extra_images=None, extra_videos=None, model="alibaba/wan-2.7/image-to-video", output_folder="output"):
    """
    Animates an image using Seedance 2.0 or Wan 2.7 models via Atlas Cloud API.
    Supports multi-subject image references (up to 9), video references, and audio/voiceover references for Seedance 2.0 Reference-to-Video.
    """
    brand_name = "Seedance 2.0" if "seedance" in model.lower() else "Wan 2.7"
    file_prefix = "seedance20_video" if "seedance" in model.lower() else "wan27_video"
    
    logs = [f"--- Starting {brand_name} Video ({model}) ---"]
    api_key = os.getenv("ATLASCLOUD_API_KEY")
    
    if not api_key:
        return {"status": "failed", "error": "Missing ATLASCLOUD_API_KEY in environment.", "logs": logs}
        
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    try:
        logs.append("Processing input image...")
        img_uri = image_to_base64_data_uri(image_path) if image_path else None
        logs.append(f"Source image processed (length: {len(img_uri) if img_uri else 0})")
        
        generate_url = "https://api.atlascloud.ai/api/v1/model/generateVideo"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        norm_res = "720P" if str(resolution).upper().strip() in ["720", "720P"] else "1080P"
        payload = {
            "model": model,
            "prompt": prompt,
            "resolution": norm_res,
            "duration": duration,
            "seed": -1
        }
        
        if "seedance" in model.lower() and "reference-to-video" in model.lower():
             # Seedance 2.0 Reference-to-Video (Up to 6 Images + Videos + Audios)
             images_payload = []
             seen_paths = set()
             
             if image_path:
                 seen_paths.add(image_path)
                 if img_uri:
                     images_payload.append(img_uri)
                     
             if extra_images:
                 for idx, img_p in enumerate(extra_images):
                     if not img_p or img_p in seen_paths:
                         continue
                     seen_paths.add(img_p)
                     if len(images_payload) >= 6:
                         logs.append("⚠️ Capped at 6 reference images for Seedance 2.0 to maintain lightweight payload.")
                         break
                     try:
                         extra_uri = image_to_base64_data_uri(img_p)
                         if extra_uri:
                             images_payload.append(extra_uri)
                             logs.append(f"Encoded reference image {len(images_payload)}")
                     except Exception as img_err:
                         logs.append(f"⚠️ Image encoding warning {idx+1}: {img_err}")
             
             # Reference Videos & Cascading Video Frame Extraction
             videos_payload = []
             
             def process_vid_ref(vid_path):
                  if not vid_path: return None
                  if vid_path.startswith(("http://", "https://")):
                      return vid_path
                  if os.path.exists(vid_path):
                      try:
                          from execution.s3_uploader import upload_file_obj
                          with open(vid_path, "rb") as f_ref:
                              s3_url = upload_file_obj(f_ref, object_name=f"ref_videos/{os.path.basename(vid_path)}")
                          if s3_url and s3_url.startswith(("http://", "https://")):
                              return s3_url
                      except Exception as s3_e:
                          logs.append(f"⚠️ Video S3 Upload warning: {s3_e}")
                          
                      # Fallback: Extract last frame of local MP4 video as image reference
                      frame_b64 = extract_last_frame_as_base64(vid_path)
                      if frame_b64 and len(images_payload) < 9:
                          images_payload.append(frame_b64)
                          logs.append("🎥 Extracted Shot N-1 last frame as Base64 image reference for visual continuity!")
                  return None

             if ref_video_path:
                  v_res = process_vid_ref(ref_video_path)
                  if v_res: videos_payload.append(v_res)
                  
             if extra_videos:
                  for v_item in extra_videos:
                      v_res = process_vid_ref(v_item)
                      if v_res and v_res not in videos_payload: videos_payload.append(v_res)
                      
             payload["reference_images"] = images_payload
             if videos_payload:
                 payload["reference_videos"] = videos_payload
                 
             # Reference Audios / Voiceover
             if ref_audio_path:
                 a_url = ref_audio_path
                 if not a_url.startswith(("http://", "https://")) and os.path.exists(a_url):
                     try:
                         from execution.s3_uploader import upload_file_obj
                         with open(a_url, "rb") as f_ref:
                             s3_url = upload_file_obj(f_ref, object_name=f"ref_audios/{os.path.basename(a_url)}")
                         if s3_url: a_url = s3_url
                     except Exception as s3_e:
                         logs.append(f"⚠️ Audio S3 Upload warning: {s3_e}")
                 payload["reference_audios"] = [a_url]
                 
        elif "reference-to-video" in model:
             if not ref_video_path:
                  return {"status": "failed", "error": "Missing reference video for Wan Reference-to-Video model.", "logs": logs}
             
             # Primary reference video
             ref_video_url = ref_video_path
             if not ref_video_path.startswith(("http://", "https://")) and os.path.exists(ref_video_path):
                 logs.append("Uploading primary reference video to S3...")
                 try:
                     from execution.s3_uploader import upload_file_obj
                     filename = os.path.basename(ref_video_path)
                     s3_key = f"ref_videos/{filename}"
                     with open(ref_video_path, "rb") as f_ref:
                         s3_url = upload_file_obj(f_ref, object_name=s3_key)
                     if s3_url:
                         ref_video_url = s3_url
                         logs.append(f"Primary reference video uploaded to S3: {s3_url}")
                     else:
                         raise ValueError("S3 upload returned empty URL")
                 except Exception as s3_err:
                     return {"status": "failed", "error": f"Failed to upload primary reference video to S3: {s3_err}", "logs": logs}
             
             videos_payload = [ref_video_url]
             
             # Extra reference videos
             if extra_videos:
                  for idx, v_path in enumerate(extra_videos):
                       if not v_path: continue
                       v_url = v_path
                       if not v_path.startswith(("http://", "https://")) and os.path.exists(v_path):
                            logs.append(f"Uploading extra reference video {idx+2} to S3...")
                            try:
                                from execution.s3_uploader import upload_file_obj
                                filename = os.path.basename(v_path)
                                s3_key = f"ref_videos/extra_{idx}_{filename}"
                                with open(v_path, "rb") as f_ref:
                                    s3_url = upload_file_obj(f_ref, object_name=s3_key)
                                if s3_url:
                                    v_url = s3_url
                                    logs.append(f"Extra reference video {idx+2} uploaded to S3: {s3_url}")
                                else:
                                    raise ValueError("S3 upload returned empty URL")
                            except Exception as s3_err:
                                logs.append(f"⚠️ S3 Upload Warning for video {idx+2}: {s3_err}")
                                continue
                       videos_payload.append(v_url)
             
             # Primary reference image
             images_payload = [img_uri]
             
             # Extra reference images
             if extra_images:
                  for idx, img_p in enumerate(extra_images):
                       if not img_p: continue
                       try:
                            extra_uri = image_to_base64_data_uri(img_p)
                            images_payload.append(extra_uri)
                            logs.append(f"Encoded extra image reference {idx+2}")
                       except Exception as img_err:
                            logs.append(f"⚠️ Image encoding warning for image {idx+2}: {img_err}")
                            
             payload["images"] = images_payload
             payload["videos"] = videos_payload
        elif "text-to-video" in model:
             payload["prompt_extend"] = True
        else:
             payload["image"] = img_uri
             payload["prompt_extend"] = True
        
        logs.append(f"Submitting job to Atlas API for {model}...")
        
        response = None
        for attempt in range(1, 4):
            try:
                logs.append(f"Sending request to Atlas Cloud (Attempt {attempt}/3)...")
                response = requests.post(generate_url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    break
                elif response.status_code in [500, 502, 503, 504, 429]:
                    logs.append(f"⚠️ Atlas Cloud returned transient HTTP {response.status_code}. Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    break
            except Exception as req_err:
                logs.append(f"⚠️ Connection attempt {attempt} failed: {req_err}")
                time.sleep(3)
                
        if not response or response.status_code != 200:
            raw_err = response.text if response else "No response from server"
            if "<html" in raw_err.lower() or (response and response.status_code in [502, 503, 504]):
                clean_err = "Atlas Cloud API temporary Gateway Timeout (HTTP 502). The backend server experienced a brief spike. Please click 'Animate Shot with Seedance' again to retry."
            else:
                clean_err = f"API Request Failed: HTTP {response.status_code if response else 'ERR'} - {raw_err[:250]}"
            return {"status": "failed", "error": clean_err, "logs": logs}
            
        result_json = response.json()
        if "data" not in result_json or "id" not in result_json["data"]:
            return {"status": "failed", "error": f"Invalid API response structure: {result_json}", "logs": logs}
            
        prediction_id = result_json["data"]["id"]
        logs.append(f"Prediction task created. Task ID: {prediction_id}")
        
        # Poll for result
        poll_url = f"https://api.atlascloud.ai/api/v1/model/prediction/{prediction_id}"
        logs.append("Polling for completion...")
        
        max_retries = 450  # 15 minutes
        for i in range(max_retries):
            time.sleep(2)
            poll_resp = requests.get(poll_url, headers={"Authorization": f"Bearer {api_key}"})
            if poll_resp.status_code != 200:
                logs.append(f"⚠️ Polling warning: HTTP {poll_resp.status_code}")
                continue
                
            poll_data = poll_resp.json()
            task_status = poll_data.get("data", {}).get("status")
            
            if i % 10 == 0:
                logs.append(f"   ... [{i+1}/{max_retries}] Status: {task_status}")
                
            if task_status in ["completed", "succeeded"]:
                outputs = poll_data.get("data", {}).get("outputs", [])
                if not outputs:
                    return {"status": "failed", "error": "API returned success but no outputs found.", "logs": logs}
                output_url = outputs[0]
                logs.append(f"Task completed successfully! Output URL: {output_url}")
                break
            elif task_status == "failed":
                err_msg = poll_data.get("data", {}).get("error") or "Unknown error"
                return {"status": "failed", "error": f"Generation failed: {err_msg}", "logs": logs}
        else:
            return {"status": "failed", "error": "Polling timed out after 15 minutes.", "logs": logs}
            
        # Download the output video
        timestamp = int(time.time())
        filename = f"{file_prefix}_{timestamp}.mp4"
        filepath = os.path.join(output_folder, filename)
        
        logs.append(f"Downloading video from {output_url}...")
        dl_resp = requests.get(output_url, stream=True)
        if dl_resp.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in dl_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logs.append(f"✅ Video saved to: {filepath}")
        else:
            return {"status": "failed", "error": f"Failed to download video: HTTP {dl_resp.status_code}", "logs": logs}
            
        # Upload to S3 if bucket is configured
        s3_url = None
        if os.getenv("S3_BUCKET_NAME"):
            try:
                from execution.s3_uploader import upload_file_obj
                if "users" in output_folder:
                    relative_path = output_folder.replace("output/", "").replace("output\\", "")
                    s3_key = f"{relative_path}/{filename}"
                else:
                    s3_key = f"generated/{filename}"
                
                with open(filepath, "rb") as f_up:
                    s3_url = upload_file_obj(f_up, object_name=s3_key)
                logs.append(f"☁️ Uploaded to S3: {s3_key}")
            except Exception as s3_err:
                logs.append(f"⚠️ S3 Upload Warning: {s3_err}")
                
        return {
            "status": "success",
            "video_path": filepath,
            "video_url": s3_url if s3_url else output_url,
            "logs": logs
        }
        
    except Exception as e:
        return {"status": "failed", "error": str(e), "logs": logs}
