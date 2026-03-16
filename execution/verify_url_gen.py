import boto3
import os
from dotenv import load_dotenv

load_dotenv()

print("--- TESTING URL GENERATION ---")

# Simulate the client init from load_assets.py
s3 = boto3.client(
    's3', 
    region_name=os.getenv("AWS_REGION", "ap-southeast-2"),
    endpoint_url="https://s3.ap-southeast-2.amazonaws.com"
)

bucket = "vlmcreateflowbucket"
key = "users/Tytheguyttg/Assets/Characters/Shay blonde bob back.png"

url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': key},
    ExpiresIn=3600
)

print(f"Generated URL: {url}")

if "s3.ap-southeast-2.amazonaws.com" in url:
    print("✅ SUCCESS: Regional Endpoint Verified")
else:
    print("❌ FAILURE: Still using standard endpoint")
