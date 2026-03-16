
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("S3_BUCKET_NAME")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")

def check_user_assets():
    print(f"🕵️ Checking S3 Bucket: {BUCKET}")
    s3 = boto3.client('s3', region_name=REGION)
    
    # 1. List root 'users/' to check casing
    print("\n--- Users Folder Roots ---")
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="users/", Delimiter="/")
    if 'CommonPrefixes' in resp:
        for p in resp['CommonPrefixes']:
            print(f"📁 {p['Prefix']}")
    else:
        print("⚠️ No 'users/' folder found or empty.")

    # 2. Check specific user 'TyTheGuyTTG' (case variants)
    target_users = ["TyTheGuyTTG", "tytheguyttg"]
    
    for u in target_users:
        prefix = f"users/{u}/Assets/"
        print(f"\n--- Checking {prefix} ---")
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, MaxKeys=10)
        if 'Contents' in resp:
            print(f"✅ Found {resp['KeyCount']} items (showing first 5):")
            for obj in resp['Contents'][:5]:
                print(f"   - {obj['Key']}")
        else:
            print(f"❌ No items found in {prefix}")

if __name__ == "__main__":
    check_user_assets()
