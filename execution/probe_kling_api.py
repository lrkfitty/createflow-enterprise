import os
import time
import requests
import jwt
import json
from dotenv import load_dotenv

load_dotenv()

def get_kling_token(access_key, secret_key):
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": access_key,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time()) - 5
    }
    return jwt.encode(payload, secret_key, algorithm="HS256", headers=headers)

def probe_motion_endpoint():
    print("🕵️‍♂️ Probing Motion Control Endpoint...")
    ak = os.getenv("KLING_ACCESS_KEY")
    sk = os.getenv("KLING_SECRET_KEY")
    token = get_kling_token(ak, sk)
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # The suspected endpoint
    url = "https://api.klingai.com/v1/videos/motion-control"
    
    try:
        resp = requests.get(url, headers=headers, params={"page": 1, "page_size": 20})
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text[:1000]}") # First 1000 chars
        
        if resp.status_code == 200:
             data = resp.json()
             tasks = data.get("data", {}).get("tasks", [])
             print(f"\n✅ Found {len(tasks)} Motion Control Tasks!")
             for t in tasks:
                  print(f" - {t.get('task_id')} | {t.get('task_status')}")
    except Exception as e:
        print(f"Fail: {e}")

if __name__ == "__main__":
    probe_motion_endpoint()
