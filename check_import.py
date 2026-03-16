import sys
import os
sys.path.append(os.getcwd())

try:
    from execution.generate_video import generate_video_kling
    print("Import Successful!")
except Exception as e:
    print(f"Import Failed: {e}")
