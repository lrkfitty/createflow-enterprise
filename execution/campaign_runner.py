import os
import json
import time
from datetime import datetime
from execution.generate_image import generate_image_from_prompt
from execution.generate_video import generate_video_kling, generate_video_humo

class CampaignManager:
    def __init__(self, campaign_file="current_campaign.json"):
        self.campaign_file = campaign_file
        self.queue = self.load_queue()
        self.cleanup_stuck_jobs() # Auto-recover on startup

    def cleanup_stuck_jobs(self):
        """Resets any jobs stuck in 'running' state back to 'pending' on startup."""
        modified = False
        for job in self.queue:
            if job["status"] == "running":
                print(f"⚠️ Resetting stuck job '{job['name']}' to pending.")
                job["status"] = "pending"
                modified = True
        if modified:
            self.save_queue()

    def load_queue(self):
        if os.path.exists(self.campaign_file):
            try:
                with open(self.campaign_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_queue(self):
        with open(self.campaign_file, 'w') as f:
            json.dump(self.queue, f, indent=4)

    def add_job(self, name, description, prompt_data, settings, output_folder, 
                char_path=None, outfit_path=None, vibe_path=None, job_type="image"):
        
        job = {
            "id": f"job_{int(time.time())}_{len(self.queue)}",
            "name": name,
            "description": description,
            "status": "pending", # pending, running, completed, failed
            "type": job_type, # image, video_kling, video_humo
            "created_at": str(datetime.now()),
            "data": {
                "prompt_data": prompt_data,
                "settings": settings, # e.g. repeat count
                "paths": {
                    "output_folder": output_folder,
                    "char_path": char_path,
                    "outfit_path": outfit_path,
                    "vibe_path": vibe_path
                }
            },
            "results": []
        }
        self.queue.append(job)
        self.save_queue()
        return job

    def clear_queue(self):
        self.queue = []
        self.save_queue()
        
    def remove_job(self, index):
        if 0 <= index < len(self.queue):
            self.queue.pop(index)
            self.save_queue()

    def get_pending_count(self):
        return len([j for j in self.queue if j["status"] == "pending"])

    def get_next_pending_job(self):
        """Finds and reserves the next pending job."""
        for i, job in enumerate(self.queue):
            if job["status"] == "pending":
                job["status"] = "running"
                self.save_queue()
                return job
        return None

    def process_job(self, job):
        """Runs the generation logic for a specific job."""
        print(f"🚀 Processing Job: {job['name']} ({job.get('type', 'image')})")
        
        # Extract Data
        p_data = job["data"]["prompt_data"]
        paths = job["data"]["paths"]
        job_type = job.get("type", "image")
        settings = job["data"]["settings"]
        repeats = settings.get("batch_count", 1)
        
        job_results = []
        
        try:
            # --- VIDEO JOBS ---
            if job_type == "video_kling":
                # Kling Video (Single Run usually, repeats supported but minimal)
                # p_data expects: { "prompt", "image_path", "duration", "model", "mode", "camera" }
                result = generate_video_kling(
                    image_path=p_data.get("image_path"),
                    prompt=p_data.get("prompt"),
                    duration=p_data.get("duration", "5s").replace("s",""),
                    model_version=p_data.get("model", "2.6"),
                    quality_mode=p_data.get("mode", "pro"),
                    camera_control=p_data.get("camera"),
                    ref_video_path=p_data.get("ref_video"),
                    ref_orientation=p_data.get("ref_orientation", "image"),
                    output_folder=paths["output_folder"]
                )
                job_results.append(result)
                
            elif job_type == "video_humo":
                # HuMo Video
                result = generate_video_humo(
                    image_path=p_data.get("image_path"),
                    prompt=p_data.get("prompt"),
                    audio_path=p_data.get("audio_path"),
                    num_frames=p_data.get("num_frames", 49),
                    output_folder=paths["output_folder"]
                )
                job_results.append(result)
                
            else:
                # --- IMAGE JOBS ---
                # Cascading Context: Check if previous job was from the same scene
                # Job names like "Ep1_S1_Sh2" — share "Ep1_S1" prefix with prior shot
                job_name = job.get("name", "")
                scene_prefix = "_".join(job_name.split("_")[:-1])  # e.g. "Ep1_S1"
                
                if scene_prefix:
                    # Find the most recent completed job with same scene prefix
                    prior_image_path = None
                    for prev_job in reversed(self.queue):
                        if prev_job is job:
                            continue
                        if prev_job["status"] == "completed" and prev_job.get("name", "").startswith(scene_prefix):
                            # Get the output image from prior result
                            for r in prev_job.get("results", []):
                                if r.get("status") == "success" and r.get("image_path"):
                                    if os.path.exists(r["image_path"]):
                                        prior_image_path = r["image_path"]
                                    break
                            break
                    
                    # Inject prior shot as cascading context
                    if prior_image_path:
                        p_data["positive_prompt"] += (
                            "\n\nSCENE CONTINUITY: The attached 'Prior Shot' image shows the PREVIOUS moment "
                            "from this same scene. Match the EXACT environment, lighting, color palette, "
                            "set design, and character wardrobe from that image."
                        )
                        if "assets" not in p_data:
                            p_data["assets"] = []
                        p_data["assets"].append({
                            "path": prior_image_path,
                            "label": "Prior Shot (SCENE CONTINUITY - MATCH ENVIRONMENT & LIGHTING)"
                        })
                        print(f"   🔗 Cascading context: attached prior shot from same scene")
                
                for r in range(repeats):
                    print(f"   ... Batch {r+1}/{repeats}")
                    
                    # Call the generator
                    result = generate_image_from_prompt(
                        p_data, 
                        output_folder=paths["output_folder"],
                        reference_image_path=paths["char_path"],
                        outfit_path=paths["outfit_path"],
                        vibe_path=paths["vibe_path"]
                    )
                    job_results.append(result)
                
            # Mark complete
            # Check if actual failure occurred in result
            if job_results and job_results[-1].get("status") == "failed":
                 job["status"] = "failed"
                 job["error"] = job_results[-1].get("error", "Unknown Error")
            else:
                 job["status"] = "completed"
                 
            job["results"] = job_results
            job["completed_at"] = str(datetime.now())
            self.save_queue()
            return job
            
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            self.save_queue()
            return job
