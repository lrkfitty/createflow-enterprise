import os
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def image_to_base64_data_uri(img_path_or_url):
    """
    Converts a local file path to a base64 data URI, or returns the URL as-is if it starts with http.
    Optimizes/resizes local images to keep request payload size lightweight.
    """
    if not img_path_or_url:
        return None
        
    if img_path_or_url.startswith(("http://", "https://")):
        return img_path_or_url
        
    if os.path.exists(img_path_or_url):
        try:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(img_path_or_url)
            max_dim = 1920
            if max(img.width, img.height) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            data = buffer.getvalue()
            
            encoded = base64.b64encode(data).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
        except Exception as e:
            with open(img_path_or_url, "rb") as f:
                data = f.read()
                encoded = base64.b64encode(data).decode('utf-8')
                ext = os.path.splitext(img_path_or_url)[1].lower()
                mime = "image/jpeg"
                if ext in (".png", ".webp"):
                    mime = f"image/{ext[1:]}"
                return f"data:{mime};base64,{encoded}"
            
    raise FileNotFoundError(f"Image source not found: {img_path_or_url}")

def generate_wan_image(prompt, image_path, size="2K", output_folder="output"):
    """
    Edits an image using Alibaba Wan 2.7 Image Edit model via Atlas Cloud API.
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
        
        generate_url = "https://api.atlascloud.ai/api/v1/model/generateImage"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Build API payload
        payload = {
            "model": "alibaba/wan-2.7-pro/image-edit",
            "prompt": prompt,
            "images": [img_uri],
            "size": size,
            "n": 1,
            "thinking_mode": True,
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
                else:
                    s3_key = f"generated/{filename}"
                
                with open(filepath, "rb") as f_up:
                    s3_url = upload_file_obj(f_up, object_name=s3_key)
                logs.append(f"☁️ Uploaded to S3: {s3_key}")
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

def generate_wan_video(prompt, image_path, resolution="1080P", duration=5, ref_video_path=None, extra_images=None, extra_videos=None, model="alibaba/wan-2.7/image-to-video", output_folder="output"):
    """
    Animates an image using Alibaba Wan 2.7 models (Image-to-Video or Reference-to-Video) via Atlas Cloud API.
    Supports multi-subject references (extra_images, extra_videos) for Reference-to-Video.
    """
    logs = [f"--- Starting Wan 2.7 Video ({model}) ---"]
    api_key = os.getenv("ATLASCLOUD_API_KEY")
    
    if not api_key:
        return {"status": "failed", "error": "Missing ATLASCLOUD_API_KEY in environment.", "logs": logs}
        
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    try:
        # Convert image to Base64 URI or keep URL
        logs.append("Processing input image...")
        img_uri = image_to_base64_data_uri(image_path)
        logs.append(f"Source image processed (length: {len(img_uri) if img_uri else 0})")
        
        generate_url = "https://api.atlascloud.ai/api/v1/model/generateVideo"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Build API payload
        payload = {
            "model": model,
            "prompt": prompt,
            "resolution": resolution,
            "duration": duration,
            "seed": -1
        }
        
        if "reference-to-video" in model:
             if not ref_video_path:
                  return {"status": "failed", "error": "Missing reference video for Reference-to-Video model.", "logs": logs}
             
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
        else:
             payload["image"] = img_uri
             payload["prompt_extend"] = True
        
        logs.append(f"Submitting job to Atlas API for {model}...")
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
        filename = f"wan27_video_{timestamp}.mp4"
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
