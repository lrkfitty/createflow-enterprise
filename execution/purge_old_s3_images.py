import os
import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")

def purge_oldest_images(username, keep_count=500):
    if not BUCKET_NAME:
        print("❌ S3_BUCKET_NAME not found in environment.")
        return

    s3 = boto3.client('s3', region_name=REGION)
    prefix = f"users/{username}/"
    
    print(f"☁️ Scanning s3://{BUCKET_NAME}/{prefix}...")
    
    all_images = []
    paginator = s3.get_paginator('list_objects_v2')
    
    try:
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                # Target gallery images, skip structured Assets
                if key.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and '/Assets/' not in key:
                    all_images.append({
                        "key": key,
                        "time": obj.get('LastModified').timestamp()
                    })
    except Exception as e:
        print(f"❌ Failed to list objects: {e}")
        return
        
    total_images = len(all_images)
    print(f"📸 Found {total_images} gallery images for user '{username}'.")
    
    if total_images <= keep_count:
        print(f"✅ User has {total_images} images, which is less than or equal to the keep count of {keep_count}. No purging needed.")
        return
        
    # Sort from newest to oldest
    all_images.sort(key=lambda x: x["time"], reverse=True)
    
    # Images to delete are everything after the keep_count
    images_to_delete = all_images[keep_count:]
    delete_count = len(images_to_delete)
    
    print(f"🗑️ Purging {delete_count} oldest images (keeping the newest {keep_count})...")
    
    # S3 specifies we can delete up to 1000 objects in a single API call
    batch_size = 1000
    for i in range(0, delete_count, batch_size):
        batch = images_to_delete[i:i + batch_size]
        objects_to_delete = [{'Key': item['key']} for item in batch]
        
        print(f"  -> Deleting batch of {len(batch)} objects...")
        try:
            response = s3.delete_objects(
                Bucket=BUCKET_NAME,
                Delete={
                    'Objects': objects_to_delete,
                    'Quiet': True
                }
            )
            print(f"  -> Batch complete.")
        except Exception as e:
            print(f"❌ Failed to delete batch: {e}")
            
    print(f"\n✅ Successfully purged {delete_count} images for user '{username}'.")

if __name__ == "__main__":
    purge_oldest_images("TyTheGuyTTG", keep_count=500)
