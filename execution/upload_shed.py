import boto3
import os
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")

def upload_specific_asset():
    s3 = boto3.client('s3', region_name=REGION)
    
    local_path = "assets/AI Content Creators/Environments/Old Wooden Shed.jpg"
    s3_key = "assets/AI Content Creators/Environments/Old Wooden Shed.jpg"
    
    print(f"Uploading {local_path} -> s3://{BUCKET_NAME}/{s3_key}")
    
    try:
        s3.upload_file(
            local_path, 
            BUCKET_NAME, 
            s3_key, 
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        print("✅ Upload Success!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    upload_specific_asset()
