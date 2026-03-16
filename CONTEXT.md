# CreateFlow System Context

**CreateFlow** is a local AI Content Creation Platform built with Streamlit and Python. It orchestrates multiple AI models (Flux Nano, Kling AI, Sora, GPT-4o) to generate high-quality images and videos for social media content.

## 🏗️ Architecture

- **Frontend**: Streamlit (`app.py`) for the UI.
- **Backend/Execution**: Python scripts in `execution/` folder.
- **Data Layer**: JSON files for state/queues (`campaign_mgr`, `assets_manifest`) and local filesystem for assets.
- **Output Storage**: Local filesystem `output/` (Cloud-synced via S3 for video generation steps).

## 🚀 Core Features & Modules

### 1. Workflow Wizard ("Quick Create")
- **Purpose**: Rapid iteration of single character images.
- **Logic**: Select Character + Outfit + Vibe -> Generate prompt via LLM -> Generate Image.
- **Batching**: Supports parallel generation (Threaded).

### 2. World Builder ("Scene Director")
- **Purpose**: Complex scene composition with multiple assets.
- **Features**:
    - **Single Scene**: Inject multiple LoRAs (Characters, Outfits, Props, Pets) into one image.
    - **Storyboard**: AI Director (LLM) breaks down a scene into 4 distinct shots and generates them sequentially.
    - **AI Rewrite**: "Director Mode" rewrites simple prompts into cinematic descriptions.

### 3. Mini Series Studio ("Episodic Content")
- **Purpose**: Create consistent episodic content (e.g., "The Influencer Life").
- **Workflow**: 
    - **Series Bible**: Define Genre, Tone, Regular Cast, and Environments.
    - **Script Writer**: LLM generates a 4-scene script based on a plot summary.
    - **Production**: Batch renders all scenes, resolving character/outfit consistency automatically.

### 4. Video Studio ("Motion")
- **Purpose**: Animate generated images into videos.
- **Engines**: Kling AI v2.6 (Pro/Standard), Sora v2 (Experimental).
- **Features**:
    - **Motion Control**: Camera Pan/Zoom/Tilt.
    - **Motion Transfer**: Use a reference video URL to drive character motion.
    - **Gallery**: User-isolated gallery for viewing/downloading results.

### 5. Campaign Manager ("Queue")
- **Purpose**: Asynchronous job queue for bulk generation.
- **Flow**: Add jobs from Wizard/Storyboard -> Review Queue -> "Run" to process effectively in background.

## 📂 Folder Structure

### Assets (`assets/`)
Organized by category. The system auto-scans these on startup:
- `assets/AI Content Creators/` (Characters)
- `assets/.../Outfits/`
- `assets/.../Vibes/` (Locations)
- `assets/.../Props/`

### Output Isolation (`output/`)
All outputs are strictly isolated by **Username** to support multi-user environments.

| Feature | Output Path |
| :--- | :--- |
| **Video Studio** | `output/users/{Username}/Videos` |
| **Wizard Images** | `output/users/{Username}/Wizard` |
| **World Scenes** | `output/users/{Username}/World` |
| **Storyboards** | `output/users/{Username}/Storyboard` |
| **Campaigns** | `output/users/{Username}/Campaign` |
| **Mini Series** | `output/users/{Username}/Series/{Series_Name}/{Ep_Name}` |

## 🔑 Key Files

- **`app.py`**: Main entry point. Contains all Streamlit UI code, tab logic, and state management.
- **`execution/generate_image.py`**: Core image generation logic (handling API calls/local pipelines).
- **`execution/generate_video.py`**: Wrapper for Kling/Sora APIs.
- **`execution/campaign_runner.py`**: Logic for managing the job queue.
- **`world_manager.py`**: Asset scanning and metadata management.

## 🛠️ Environment Variables (.env)
- `KLING_ACCESS_KEY` / `KLING_SECRET_KEY`: For Video Gen.
- `OPENAI_API_KEY`: For LLM Prompt Enhancement.
- `AWS_ACCESS_KEY_ID`...: For S3 (Intermediate asset storage for Video APIs).
