import os
import jwt
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

class KlingClient:
    def __init__(self):
        self.ak = os.getenv("KLING_ACCESS_KEY")
        self.sk = os.getenv("KLING_SECRET_KEY")
        self.base_url = "https://api.klingai.com/v1"
        self.token = None
        self.token_expiry = 0

    def _get_token(self):
        """Generates or refreshes the JWT token."""
        now = int(time.time())
        # Refresh if expired or soon to expire (within 60s)
        if not self.token or now >= self.token_expiry - 60:
            if not self.ak or not self.sk:
                raise ValueError("KLING_ACCESS_KEY or KLING_SECRET_KEY not set.")
            
            headers = {
                "alg": "HS256",
                "typ": "JWT"
            }
            payload = {
                "iss": self.ak,
                "exp": now + 1800, # 30 mins
                "nbf": now - 5
            }
            self.token = jwt.encode(payload, self.sk, algorithm="HS256", headers=headers)
            self.token_expiry = now + 1800
        
        return self.token

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json"
        }

    def create_video_from_image(self, image_url, prompt, negative_prompt="", duration=5):
        """
        Starts an Image-to-Video task.
        Note: Kling requires a publicly accessible URL for the image or base64 (check doc specific).
        For now assuming public URL or S3 Presigned URL is passed.
        """
        url = f"{self.base_url}/videos/image2video"
        
        payload = {
            "model_name": "kling-v1", # or specific version
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": 0.5,
            "mode": "std", # 'std' or 'pro'
            "duration": duration
        }
        
        response = requests.post(url, headers=self._get_headers(), json=payload)
        response.raise_for_status()
        return response.json() # Returns task_id

    def create_video_from_text(self, prompt, negative_prompt="", duration=5):
        """Starts a Text-to-Video task."""
        url = f"{self.base_url}/videos/text2video"
        
        payload = {
            "model_name": "kling-v1",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": 0.5,
            "mode": "std",
            "duration": duration
        }
        
        response = requests.post(url, headers=self._get_headers(), json=payload)
        response.raise_for_status()
        return response.json()

    def get_task_status(self, task_id):
        """Checks the status of a generation task."""
        url = f"{self.base_url}/videos/{task_id}"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    # Quick Test
    try:
        client = KlingClient()
        token = client._get_token()
        print(f"✅ Client Initialized. Token: {token[:10]}...")
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
