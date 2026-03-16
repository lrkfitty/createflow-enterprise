import boto3
import os
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")

def list_keys():
    s3 = boto3.client('s3', region_name=REGION)
    
    print(f"🔍 Searching S3 Bucket: {BUCKET_NAME}")
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix="AI Content Creators/Influencer")
        
        for page in pages:
            for obj in page.get('Contents', []):
                key = obj['Key']
                if "Matching Sets" in key:
                    print(f"🔑 Key found: '{key}'")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_keys()
