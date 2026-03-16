import boto3
import os
from dotenv import load_dotenv

load_dotenv()

bucket_name = os.getenv("S3_BUCKET_NAME")
if not bucket_name:
    print("❌ S3_BUCKET_NAME not set in .env")
    exit()

s3 = boto3.client('s3', region_name=os.getenv("AWS_REGION", "ap-southeast-2"))

def list_prefix(prefix):
    print(f"\n📂 Scanning Prefix: {prefix}")
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"   - {obj['Key']} (Size: {obj['Size']})")
        else:
            print("   (Empty or Not Found)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# 1. Inspect Chels (Tytheguyttg)
# print("--- CHELS INSPECTION ---")
# list_prefix("users/Tytheguyttg/Assets/Characters/Chels/")
# list_prefix("users/Tytheguyttg/Assets/characters/Chels/") # Case check

# 2. Inspect Angeil (Broad Scan)
print("\n--- ANGEIL BROAD SCAN ---")
list_prefix("users/angeil.lark@gmail.com/")

print("\n--- DONE ---")
