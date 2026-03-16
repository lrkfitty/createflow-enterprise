#!/usr/bin/env python3
"""
Consolidate user assets from users/Tytheguyttg to users/TyTheGuyTTG in S3.
This script copies all assets while preserving folder structure and avoiding duplicates.
"""

import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")

SOURCE_PREFIX = "users/Tytheguyttg/Assets/"
TARGET_PREFIX = "users/TyTheGuyTTG/Assets/"

def consolidate_assets():
    """Copy all assets from source to target folder in S3."""
    
    s3 = boto3.client('s3', region_name=REGION)
    
    print("=" * 70)
    print("🔄 S3 ASSET CONSOLIDATION")
    print("=" * 70)
    print(f"📦 Bucket: {BUCKET_NAME}")
    print(f"📁 Source: {SOURCE_PREFIX}")
    print(f"📁 Target: {TARGET_PREFIX}")
    print("=" * 70)
    print()
    
    # Step 1: List all source assets
    print("📋 Listing source assets...")
    source_objects = []
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=SOURCE_PREFIX)
        
        for page in pages:
            for obj in page.get('Contents', []):
                key = obj['Key']
                # Only include actual image files
                if key.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    source_objects.append(key)
        
        print(f"✅ Found {len(source_objects)} source assets\n")
    
    except ClientError as e:
        print(f"❌ Error listing source: {e}")
        return
    
    # Step 2: Copy each asset
    print("🚀 Starting copy process...\n")
    
    copied = 0
    skipped = 0
    errors = 0
    
    for source_key in source_objects:
        # Build target key by replacing prefix
        target_key = source_key.replace(SOURCE_PREFIX, TARGET_PREFIX, 1)
        
        try:
            # Check if target already exists
            try:
                s3.head_object(Bucket=BUCKET_NAME, Key=target_key)
                print(f"⏭️  SKIP (exists): {os.path.basename(source_key)}")
                skipped += 1
                continue
            except ClientError:
                # Target doesn't exist, proceed with copy
                pass
            
            # Copy object
            copy_source = {'Bucket': BUCKET_NAME, 'Key': source_key}
            s3.copy_object(
                CopySource=copy_source,
                Bucket=BUCKET_NAME,
                Key=target_key
            )
            
            print(f"✅ COPIED: {source_key} → {target_key}")
            copied += 1
            
        except ClientError as e:
            print(f"❌ ERROR copying {source_key}: {e}")
            errors += 1
    
    # Step 3: Summary
    print()
    print("=" * 70)
    print("📊 CONSOLIDATION SUMMARY")
    print("=" * 70)
    print(f"✅ Copied:  {copied}")
    print(f"⏭️  Skipped: {skipped} (already existed)")
    print(f"❌ Errors:  {errors}")
    print(f"📊 Total:   {len(source_objects)}")
    print("=" * 70)
    
    if errors == 0:
        print("✅ Consolidation completed successfully!")
    else:
        print("⚠️  Consolidation completed with errors. Review output above.")
    
    # Step 4: Verify target folder
    print("\n🔍 Verifying target folder...")
    try:
        target_count = 0
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=TARGET_PREFIX)
        
        for page in pages:
            for obj in page.get('Contents', []):
                if obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    target_count += 1
        
        print(f"✅ Target folder now contains: {target_count} assets")
    except ClientError as e:
        print(f"❌ Error verifying target: {e}")

if __name__ == "__main__":
    consolidate_assets()
