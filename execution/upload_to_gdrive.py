"""
Upload Character Pack to Google Drive.
First run: opens browser for OAuth consent. Token is saved for future runs.
"""

import os
import sys
import json
import pickle

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']
PACK_DIR = "output/character_pack"
DRIVE_FOLDER_NAME = "CreateFlow — Free Character Pack"
CREDS_FILE = "credentials.json"
TOKEN_FILE = "token_drive.pickle"


def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                print("""
❌  Missing credentials.json

To set up Google Drive access:
1. Go to https://console.cloud.google.com/
2. Create a project → Enable Google Drive API
3. Create OAuth credentials (Desktop app) → Download JSON
4. Save as 'credentials.json' in the CreateFlow-Enterprise folder
5. Re-run this script
""")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
        print("✅ Google Drive authorized and token saved.")

    return build('drive', 'v3', credentials=creds)


def create_folder(service, name, parent_id=None):
    meta = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        meta['parents'] = [parent_id]
    folder = service.files().create(body=meta, fields='id').execute()
    return folder['id']


def upload_file(service, filepath, filename, parent_id):
    meta = {'name': filename, 'parents': [parent_id]}
    media = MediaFileUpload(filepath, resumable=True)
    f = service.files().create(body=meta, media_body=media, fields='id,webViewLink').execute()
    return f.get('webViewLink', '')


def run():
    print("\n📤 Uploading CreateFlow Character Pack to Google Drive...\n")
    service = get_drive_service()

    # Create root folder in Drive
    root_id = create_folder(service, DRIVE_FOLDER_NAME)
    print(f"✅ Created Drive folder: '{DRIVE_FOLDER_NAME}' (id: {root_id})")

    # Make it shareable (anyone with link can view)
    service.permissions().create(
        fileId=root_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    root_link = f"https://drive.google.com/drive/folders/{root_id}"
    print(f"🔗 Shareable link: {root_link}\n")

    uploaded = 0
    failed = 0

    # Walk character subdirectories
    char_dirs = sorted([
        d for d in os.listdir(PACK_DIR)
        if os.path.isdir(os.path.join(PACK_DIR, d))
    ])

    for char_dir in char_dirs:
        char_path = os.path.join(PACK_DIR, char_dir)
        # Create subfolder per character
        sub_id = create_folder(service, char_dir, parent_id=root_id)

        for fname in os.listdir(char_path):
            if fname.endswith(('.jpg', '.jpeg', '.png')) and '_thumb' not in fname:
                fpath = os.path.join(char_path, fname)
                try:
                    link = upload_file(service, fpath, fname, sub_id)
                    print(f"  ✅ {char_dir}/{fname}")
                    uploaded += 1
                except Exception as e:
                    print(f"  ❌ {char_dir}/{fname}: {e}")
                    failed += 1

    print(f"\n{'='*50}")
    print(f"✅ Uploaded: {uploaded} images")
    if failed:
        print(f"❌ Failed:   {failed}")
    print(f"\n📁 Google Drive Folder:\n   {root_link}\n")

    # Save link to manifest
    manifest_path = os.path.join(PACK_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest_meta = {"drive_folder": root_link, "total_uploaded": uploaded}
        with open(manifest_path, 'w') as f:
            json.dump({"meta": manifest_meta, "characters": manifest}, f, indent=2)
        print(f"📋 Drive link saved to manifest.json")


if __name__ == "__main__":
    run()
