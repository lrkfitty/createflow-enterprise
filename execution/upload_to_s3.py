import os
import boto3
import mimetypes
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Configuration
# Load from Environment if possible, otherwise rely on ~/.aws/credentials
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "vlmcreateflowbucket") 
REGION = os.getenv("AWS_REGION", "ap-southeast-2")
ASSET_DIR = "assets"

def upload_to_s3():
    """
    Recursively uploads the 'assets' folder to the specified S3 Bucket.
    """
    s3 = boto3.client('s3', region_name=REGION)
    
    if not os.path.exists(ASSET_DIR):
        print(f"❌ Asset directory '{ASSET_DIR}' not found.")
        return

    print(f"🚀 Starting Upload to s3://{BUCKET_NAME}...")
    
    files_to_upload = []
    for root, dirs, files in os.walk(ASSET_DIR):
        for file in files:
            if file.startswith("."): continue # Skip hidden
            local_path = os.path.join(root, file)
            # S3 Key: Maintain structure, e.g. assets/Characters/Shay.png
            # Or just Characters/Shay.png if we want root to be cleaner.
            # Let's keep 'assets' prefix to match local structure logic or remove it?
            # load_assets.py usually expects relative paths.
            # Let's remove 'assets/' prefix for cleaner bucket structure.
            # relative_path = os.path.relpath(local_path, ASSET_DIR)
            
            # Actually, keeping 'assets' folder in bucket is safer for organization.
            relative_path = os.path.relpath(local_path, os.getcwd())
            
            files_to_upload.append((local_path, relative_path))

    total = len(files_to_upload)
    print(f"Found {total} files.")
    
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

    print("\n✅ Upload Complete!")
    print(f"Files are available at: https://{BUCKET_NAME}.s3.amazonaws.com/assets/...")

if __name__ == "__main__":
    # Check env
    if not os.getenv("S3_BUCKET_NAME"):
        print("⚠️  Warning: S3_BUCKET_NAME not set in .env. Using default 'viral-lens-assets'.")
        print("To fix, add S3_BUCKET_NAME=your-bucket-name to .env")
        confirm = input("Continue with default? (y/n): ")
        if confirm.lower() != 'y':
            exit()
            
    upload_to_s3()
