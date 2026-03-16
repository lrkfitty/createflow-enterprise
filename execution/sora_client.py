import os
import time
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class SoraClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        self.client = OpenAI(api_key=self.api_key)

    def create_video_from_text(self, prompt, duration=5, aspect_ratio="16:9", resolution="1080p"):
        """
        Generates a video from text using Sora 2.
        """
        try:
            # Placeholder for actual Sora API endpoint schema
            # Assuming standard OpenAI async pattern
            response = self.client.video.generations.create(
                model="sora-2",  # or sora-1.0-turbo
                prompt=prompt,
                quality="standard", # or hd
                response_format="url",
                size=self._map_aspect_ratio(aspect_ratio, resolution)
            )
            # OpenAI usually returns a URL immediately or a job ID. 
            # If it's a job ID, we'd need polling. Assuming URL for simplest implementation or handled by library.
            # But mostly likely it's async.
            
            # Since standard lib doesn't support 'video' yet in all versions, we might need raw request if library is old.
            # For this implementation, we will assume the lib is updated.
            # If not, we fall back to requests.
            return response.data[0].url
            
        except AttributeError:
             # Fallback to direct API call if local openai lib is outdated
             return self._raw_api_call(prompt, None, aspect_ratio)
        except Exception as e:
            return {"error": str(e)}

    def create_video_from_image(self, image_url, prompt, duration=5, aspect_ratio="16:9"):
        """
        Generates a video from an image + text.
        """
        # Sora 2 supports image inputs
        return self._raw_api_call(prompt, image_url, aspect_ratio)

    def _raw_api_call(self, prompt, image_url, aspect_ratio):
        """
        Raw HTTP implementation in case SDK is behind.
        """
        url = "https://api.openai.com/v1/videos/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sora-2",
            "prompt": prompt,
            "max_duration": 5, # Seconds
        }
        
        if image_url:
            payload["image"] = image_url
            
        # Add size mapping
        width, height = self._get_dimensions(aspect_ratio)
        payload["width"] = width
        payload["height"] = height

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                # Assuming direct return or revision ID
                if 'data' in data and len(data['data']) > 0:
                    return data['data'][0]['url']
                elif 'id' in data:
                    return self._poll_result(data['id'])
            else:
                return {"error": f"API Error {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": f"Request Failed: {e}"}
            
    def _poll_result(self, task_id):
        # Poll for 2 minutes
        url = f"https://api.openai.com/v1/videos/generations/{task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        for _ in range(24): # 24 * 5s = 120s
            time.sleep(5)
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                stat = r.json()
                if stat.get('status') == 'succeeded':
                    return stat['result']['url']
                elif stat.get('status') == 'failed':
                    return {"error": "Generation Failed"}
        return {"error": "Timeout waiting for Sora"}

    def _get_dimensions(self, ar):
        if ar == "16:9": return 1920, 1080
        if ar == "9:16": return 1080, 1920
        return 1024, 1024
