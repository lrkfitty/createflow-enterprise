import os
import boto3
import sys
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Try loading from secrets if env missing (mimic app.py basic logic or just rely on .env/secrets.toml being handled by user env)
# For this script, we rely on .env or OS env.

bucket_name = os.getenv("S3_BUCKET_NAME")
if not bucket_name:
    print("No S3_BUCKET_NAME found. Skipping Cloud Fix.")
    sys.exit(0)

print(f"Connecting to S3 Bucket: {bucket_name}")
s3 = boto3.client('s3', region_name=os.getenv("AWS_REGION", "ap-southeast-2"))

# Prefix to scan: users/
# We want to find .../default.png
try:
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix="users/")
    
    count = 0
    for page in pages:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith("default.png"):
                # Construct new key
                # Key: users/{user}/Assets/Characters/{Name}/default.png
                parts = key.split('/')
                # parts[-1] is default.png
                # parts[-2] is Name (e.g. Chels)
                
                if len(parts) >= 2:
                    parent_name = parts[-2]
                    new_filename = f"{parent_name}.png"
                    new_key = "/".join(parts[:-1] + [new_filename])
                    
                    print(f"Migrating S3: {key} -> {new_key}")
                    
                    # Copy
                    s3.copy_object(
                        Bucket=bucket_name,
                        CopySource={'Bucket': bucket_name, 'Key': key},
                        Key=new_key
                    )
                    
                    # Delete Old
                    s3.delete_object(Bucket=bucket_name, Key=key)
                    count += 1

    print(f"S3 Migration Complete. Fixed {count} assets.")

except Exception as e:
    print(f"S3 Error: {e}")
