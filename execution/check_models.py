
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json().get('models', [])
        print(f"Found {len(models)} models:")
        for m in models:
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                print(m.get('name'))
    else:
        print(f"Error listing models: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Exception: {e}")
