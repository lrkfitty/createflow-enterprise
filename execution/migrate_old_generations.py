"""
Script to migrate old generations from generated/ to users/{username}/ for gallery visibility.
Run this once to fix yesterday's images that weren't showing in the gallery.
"""
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

def migrate_generations_to_gallery(username, target_category="Gallery"):
    """
    Moves all files from S3 generated/ folder to users/{username}/{category}/
    """
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        print("❌ No S3_BUCKET_NAME configured. Skipping migration.")
        return
    
    region = os.getenv("AWS_REGION", "ap-southeast-2")
    s3 = boto3.client('s3', region_name=region)
    
    print(f"🔍 Scanning S3 bucket: {bucket_name}")
    print(f"   Looking for files in: generated/")
    print(f"   Will move to: users/{username}/{target_category}/\n")
    
    # List all objects in generated/
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix="generated/")
    
    moved_count = 0
    skipped_count = 0
    
    for page in pages:
        for obj in page.get('Contents', []):
            old_key = obj['Key']
            
            # Only process image files
            if not old_key.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue
            
            # Extract filename from old path
            filename = old_key.split('/')[-1]
            
            # Build new key
            new_key = f"users/{username}/{target_category}/{filename}"
            
            try:
                # Copy to new location
                copy_source = {'Bucket': bucket_name, 'Key': old_key}
                s3.copy_object(CopySource=copy_source, Bucket=bucket_name, Key=new_key)
                
                # Delete old file
                s3.delete_object(Bucket=bucket_name, Key=old_key)
                
                print(f"✅ Moved: {filename}")
                print(f"   From: {old_key}")
                print(f"   To:   {new_key}\n")
                moved_count += 1
                
            except Exception as e:
                print(f"❌ Failed to move {filename}: {e}\n")
                skipped_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Migration Complete!")
    print(f"   Moved: {moved_count} files")
    print(f"   Skipped: {skipped_count} files")
    print(f"{'='*60}")
    print(f"\n💡 Now refresh your 'My Gallery' tab in the app to see your images!")

if __name__ == "__main__":
    # TODO: Replace with your actual username
    # You can find it in app.py session state or users.json
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrate_old_generations.py <username>")
        print("\nExample: python migrate_old_generations.py Tytheguyttg")
        sys.exit(1)
    
    username = sys.argv[1]
    migrate_generations_to_gallery(username, target_category="Gallery")
