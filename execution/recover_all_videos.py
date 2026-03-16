import os
import time
import requests
import jwt
import json
from dotenv import load_dotenv

load_dotenv()

def get_kling_token(access_key, secret_key):
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    payload = {
        "iss": access_key,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time()) - 5
    }
    return jwt.encode(payload, secret_key, algorithm="HS256", headers=headers)

def recover_videos():
    ak = os.getenv("KLING_ACCESS_KEY")
    sk = os.getenv("KLING_SECRET_KEY")
    if not ak or not sk:
        print("Missing credentials")
        return

    try:
        token = get_kling_token(ak, sk)
    except Exception as e:
        print(f"Token Error: {e}")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Using the exact string that worked in probe
    url = "https://api.klingai.com/v1/videos" 

    # CORRECT ENDPOINT FOUND VIA PROBE
    url = "https://api.klingai.com/v1/videos/image2video" 

    print("🕵️‍♂️ Fetching Video List...")
    
    try:
        # Request with default page size (should handle ~50)
        resp = requests.get(url, headers=headers)
        
        if resp.status_code != 200:
            print(f"API Error: {resp.status_code} {resp.text}")
            return
            
        data = resp.json()
        print(f"DEBUG: Data Type: {type(data)}")
        if isinstance(data, dict):
             print(f"DEBUG: keys: {data.keys()}")
        
        # Robust Parsing
        tasks = []
        if isinstance(data, dict):
            # Format A: data['data']['tasks']
            if "data" in data and isinstance(data["data"], dict) and "tasks" in data["data"]:
                tasks = data["data"]["tasks"]
            # Format B: data['data'] is list
            elif "data" in data and isinstance(data["data"], list):
                tasks = data["data"]
            # Format C: data['tasks']
            elif "tasks" in data:
                tasks = data["tasks"]
                
        print(f"📋 Found {len(tasks)} tasks.")
        
        if not os.path.exists("output"): os.makedirs("output")
        
        count = 0
        for t in tasks:
            tid = t.get("task_id")
            status = t.get("task_status")
            
            if status == "succeed":
                 # Extract URL
                 video_url = None
                 result = t.get("task_result")
                 if result and "videos" in result and len(result["videos"]) > 0:
                      video_url = result["videos"][0].get("url")
                      
                 if video_url:
                      filename = f"output/kling_{tid}.mp4"
                      if os.path.exists(filename):
                          print(f"  ⏭️  Skipping existing: {tid}")
                          continue
                          
                      print(f"  ⬇️  Downloading Task {tid}...")
                      try:
                          v_resp = requests.get(video_url, stream=True)
                          if v_resp.status_code == 200:
                              with open(filename, 'wb') as f:
                                  for chunk in v_resp.iter_content(chunk_size=8192):
                                      f.write(chunk)
                              print(f"     ✅ Saved!")
                              count += 1
                          else:
                              print(f"     ❌ Download Failed: {v_resp.status_code}")
                      except Exception as e:
                          print(f"     ❌ Error: {e}")
            else:
                 # print(f"  ⏳ Task {tid} is {status}")
                 pass
                 
        print(f"\n🎉 Recovery Complete! Downloaded {count} new videos.")

    except Exception as e:
        print(f"Net Error: {e}")

if __name__ == "__main__":
    recover_videos()
