#!/bin/bash

# 1. Upload new files to S3
echo "🚀 Syncing Assets to Cloud (S3)..."
python3 execution/upload_to_s3.py

# 2. Update the Application Map
echo "🗺️  Generating Asset Manifest..."
python3 execution/generate_asset_manifest.py

echo "✅ Done! 'assets_manifest.json' has been updated."
echo "👉 Now commit and push 'assets_manifest.json' to GitHub to see changes in the deployed app."
