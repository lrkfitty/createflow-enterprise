import json
import os

# 1. Define Talking Head Scenarios
talking_head_scenarios = [
    # Podcast / Interview Style Talking Heads
    {
        "name": "Podcast Monologue (Solo)",
        "category": "Talking Head",
        "template": "Close-up talking head shot, [PROTAGONIST] speaking directly to camera, [PROPS_AND_CAST], wearing [OUTFIT], podcast microphone visible, sound foam background, engaging storytelling expression, warm studio lighting, [LOCATION] background."
    },
    {
        "name": "Interview Q&A (Looking Slightly Off)",
        "category": "Talking Head",
        "template": "Medium talking head shot, [PROTAGONIST] answering questions, [PROPS_AND_CAST], wearing [OUTFIT], looking slightly off-camera at interviewer, thoughtful expression, professional interview setup, [LOCATION] background."
    },
    {
        "name": "Vlog Update (Casual Talk)",
        "category": "Talking Head",
        "template": "Arm's length vlog talking head, [PROTAGONIST] speaking casually to camera, [PROPS_AND_CAST], wearing [OUTFIT], natural hand gestures, friendly expression, bedroom or home office background, [LOCATION] setting."
    },
    {
        "name": "Tutorial Explanation",
        "category": "Talking Head",
        "template": "Medium close-up talking head, [PROTAGONIST] explaining a concept, [PROPS_AND_CAST], wearing [OUTFIT], using hand gestures to emphasize points, clear educational tone, clean background, [LOCATION] setting."
    },
    {
        "name": "Product Review Commentary",
        "category": "Talking Head",
        "template": "Talking head medium shot, [PROTAGONIST] reviewing a product while speaking to camera, [PROPS_AND_CAST], wearing [OUTFIT], holding or gesturing to product, honest review expression, [LOCATION] background."
    },
    {
        "name": "Announcement (Direct Address)",
        "category": "Talking Head",
        "template": "Centered talking head close-up, [PROTAGONIST] making an important announcement, [PROPS_AND_CAST], wearing [OUTFIT], serious or excited expression, direct eye contact with camera, professional backdrop, [LOCATION] background."
    },
    {
        "name": "Life Update (Personal Story)",
        "category": "Talking Head",
        "template": "Intimate talking head shot, [PROTAGONIST] sharing personal story or life update, [PROPS_AND_CAST], wearing [OUTFIT], emotional and vulnerable expression, cozy home setting, soft natural lighting, [LOCATION] background."
    },
    {
        "name": "Expert Commentary",
        "category": "Talking Head",
        "template": "Professional talking head medium shot, [PROTAGONIST] providing expert commentary, [PROPS_AND_CAST], wearing [OUTFIT], confident and authoritative expression, corporate or professional background, [LOCATION] setting."
    },
    {
        "name": "Motivational Speech",
        "category": "Talking Head",
        "template": "Dynamic talking head shot, [PROTAGONIST] delivering motivational message, [PROPS_AND_CAST], wearing [OUTFIT], passionate and inspiring expression, powerful hand gestures, dramatic lighting, [LOCATION] background."
    },
    {
        "name": "Reaction Video (Talking Head)",
        "category": "Talking Head",
        "template": "Close-up talking head reaction shot, [PROTAGONIST] reacting to content while speaking, [PROPS_AND_CAST], wearing [OUTFIT], expressive facial reactions, screen glow on face, [LOCATION] background."
    },
    {
        "name": "Behind the Scenes Commentary",
        "category": "Talking Head",
        "template": "Candid talking head shot, [PROTAGONIST] sharing behind the scenes insights, [PROPS_AND_CAST], wearing [OUTFIT], casual and authentic vibe, production equipment visible in background, [LOCATION] setting."
    },
    {
        "name": "Answer Questions (DMs/Comments)",
        "category": "Talking Head",
        "template": "Talking head medium shot, [PROTAGONIST] answering fan questions from phone, [PROPS_AND_CAST], wearing [OUTFIT], reading from phone and responding to camera, casual friendly atmosphere, [LOCATION] background."
    },
    {
        "name": "Morning Routine Voiceover",
        "category": "Talking Head",
        "template": "Morning talking head shot, [PROTAGONIST] narrating morning routine, [PROPS_AND_CAST], wearing [OUTFIT], fresh-faced natural look, window light, bathroom or bedroom setting, [LOCATION] background."
    },
    {
        "name": "Confessional / Raw Talk",
        "category": "Talking Head",
        "template": "Intimate close-up talking head, [PROTAGONIST] having raw honest conversation with camera, [PROPS_AND_CAST], wearing [OUTFIT], vulnerable emotional expression, minimal makeup, simple background, [LOCATION] setting."
    },
    {
        "name": "News Update / Current Events",
        "category": "Talking Head",
        "template": "News-style talking head shot, [PROTAGONIST] discussing current events or news, [PROPS_AND_CAST], wearing [OUTFIT], informative and engaging expression, professional news-style backdrop, [LOCATION] background."
    },
    {
        "name": "Storytime (Animated Telling)",
        "category": "Talking Head",
        "template": "Engaging talking head shot, [PROTAGONIST] animatedly telling a story, [PROPS_AND_CAST], wearing [OUTFIT], dramatic facial expressions and hand gestures, cozy storytelling atmosphere, [LOCATION] background."
    },
    {
        "name": "Advice Column (Answering Questions)",
        "category": "Talking Head",
        "template": "Warm talking head medium shot, [PROTAGONIST] giving advice to audience, [PROPS_AND_CAST], wearing [OUTFIT], empathetic and wise expression, comforting home setting, [LOCATION] background."
    },
    {
        "name": "Day in the Life Intro",
        "category": "Talking Head",
        "template": "Opening talking head shot, [PROTAGONIST] introducing their day, [PROPS_AND_CAST], wearing [OUTFIT], energetic morning vibe, looking at camera with excitement, bedroom or living room, [LOCATION] setting."
    }
]

# 2. Load Existing Database
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "world_db.json")
with open(db_path, "r") as f:
    db = json.load(f)

current_scenarios = db.get("scenarios", {})

# 3. Merge Scenarios
count = 0
for item in talking_head_scenarios:
    # Generate a key from name (snake_case)
    key = item["name"].lower().replace(" ", "_").replace("-", "_").replace("'", "").replace("/", "_").replace("(", "").replace(")", "")
    
    # Overwrite or Add
    if key not in current_scenarios:
        count += 1
        
    current_scenarios[key] = {
        "name": item["name"],
        "template_prompt": item["template"],
        "category": item["category"]
    }

print(f"Added/Updated {count} talking head scenarios.")
print(f"Total Scenarios: {len(current_scenarios)}")

# 4. Save Back
db["scenarios"] = current_scenarios

with open(db_path, "w") as f:
    json.dump(db, f, indent=4)

print("Database successfully updated with talking head scenarios.")
