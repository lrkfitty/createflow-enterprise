import os
import boto3
import mimetypes
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# Load Env
load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "vlmcreateflowbucket")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")
USERS_DIR = os.path.join("output", "users")

def sync_users():
    s3 = boto3.client('s3', region_name=REGION)
    
    if not os.path.exists(USERS_DIR):
        print(f"❌ Users directory '{USERS_DIR}' not found.")
        return

    print(f"🚀 Starting User Gallery Sync to s3://{BUCKET_NAME}...")
    
    files_to_upload = []
    for root, dirs, files in os.walk(USERS_DIR):
        for file in files:
            if file.startswith("."): continue # Skip hidden
            
            local_path = os.path.join(root, file)
            
            # S3 Key Logic
            # Local: output/users/Tytheguyttg/Series/Image.png
            # S3 Key: users/Tytheguyttg/Series/Image.png
            
            # Get path relative to 'output' folder?
            # root is 'output/users/Ty...'
            # rel to 'output' is 'users/Ty...'
            
            # Normalized relative path
            # We want it to start with "users/"
            # os.path.relpath("output/users/Ty", "output") -> "users/Ty"
            
            relative_path = os.path.relpath(local_path, "output")
            files_to_upload.append((local_path, relative_path))

    total = len(files_to_upload)
    print(f"Found {total} user files to sync.")
    
    for i, (local, remote) in enumerate(files_to_upload):
        content_type, _ = mimetypes.guess_type(local)
        if content_type is None:
            content_type = 'binary/octet-stream'
            
        try:
            print(f"[{i+1}/{total}] Uploading {remote}...")
            s3.upload_file(
                local, 
                BUCKET_NAME, 
                remote, 
                ExtraArgs={'ContentType': content_type}
            )
        except NoCredentialsError:
            print("❌ AWS Credentials not found.")
            return
        except Exception as e:
            print(f"❌ Failed to upload {remote}: {e}")

    print("\n✅ User Sync Complete!")

if __name__ == "__main__":
    sync_users()
