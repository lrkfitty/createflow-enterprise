"""
plan_campaign.py
----------------
Autonomous Campaign Planner — takes a high-level brief and generates N
campaign job plans, ready to be queued into CampaignManager.

Layer 3 (Execution) script. Called by the Auto Campaign section in app.py.

Input:
    brief       (str)  — e.g. "30 days of luxury lifestyle content for Shay"
    num_posts   (int)  — number of posts to plan (default: 10)
    character   (str)  — optional lock to a specific character name

Output:
    list of dicts, each matching the structure expected by CampaignManager.add_job()
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()


def _load_scenario_catalog(world_db_path: str = "world_db.json") -> list:
    """Return a flat list of scenario names + keys from world_db for LLM context."""
    if not os.path.exists(world_db_path):
        return []

    with open(world_db_path, "r") as f:
        db = json.load(f)

    scenarios = []
    for key, val in db.get("scenarios", {}).items():
        scenarios.append({
            "key": key,
            "name": val.get("name", key),
            "category": val.get("category", "Lifestyle"),
        })
    return scenarios


def plan_campaign(
    brief: str,
    num_posts: int = 10,
    character: str = None,
    world_db_path: str = "world_db.json",
    model_engine: str = "gemini-2.0-flash",
) -> list:
    """
    Generate N campaign job plans from a high-level content brief.

    Args:
        brief:          High-level creative brief ("30 days of fitness content for Shay").
        num_posts:      Number of posts to plan.
        character:      Optional: lock all posts to a specific character name.
        world_db_path:  Path to world_db.json.
        model_engine:   Gemini model to use.

    Returns:
        List of job plan dicts, each with:
            name, description, character, outfit, vibe, scenario_key,
            aspect_ratio, post_number, day_of_week (estimated)
    """
    import google.generativeai as genai

    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        print("[plan_campaign] ERROR: GOOGLE_API_KEY not found in .env")
        return []

    scenarios = _load_scenario_catalog(world_db_path)

    # Group scenarios by category for the LLM
    by_category: dict = {}
    for s in scenarios:
        cat = s.get("category", "Lifestyle")
        by_category.setdefault(cat, []).append(f"{s['name']} (key: {s['key']})")

    catalog_str = ""
    for cat, items in by_category.items():
        catalog_str += f"\n{cat}:\n" + "\n".join(f"  - {i}" for i in items[:12])  # cap per category

    character_instruction = (
        f"LOCK all posts to character: '{character}'."
        if character
        else "Choose appropriate characters from: Shay (main protagonist)."
    )

    system_prompt = f"""You are an expert Social Media Content Strategist and Creative Director.

Your job is to plan a {num_posts}-post content campaign based on a creative brief.
You will output a structured content calendar with specific visual scenarios.

AVAILABLE VISUAL SCENARIOS:
{catalog_str}

CHARACTER: {character_instruction}

PLANNING RULES:
1. Create exactly {num_posts} posts.
2. Vary the scenarios — don't repeat the same one consecutively.
3. Mix content categories to keep the feed dynamic (lifestyle, travel, fashion, etc.).
4. Suggest realistic, visually distinct outfit descriptions per post.
5. Assign a post number (1–{num_posts}) and a suggested day of the week.
6. Make names short and slug-friendly (e.g., "Post_01_Beach_Sunset").

OUTPUT: Return ONLY a valid JSON array with exactly {num_posts} objects. Each object:
{{
    "post_number": <int>,
    "name": "<slug_name>",
    "description": "<one sentence describing the post>",
    "character": "<character name>",
    "outfit": "<outfit description>",
    "vibe": "<scenario name from the list>",
    "scenario_key": "<scenario key from the list>",
    "aspect_ratio": "<9:16|1:1|16:9>",
    "day_of_week": "<Monday|Tuesday|...|Sunday>"
}}
"""

    user_message = f'Plan a {num_posts}-post campaign for:\n\n"{brief}"'

    try:
        genai.configure(api_key=google_key)
        model = genai.GenerativeModel(model_engine)
        response = model.generate_content([system_prompt, user_message])
        raw = response.text.strip()

        # Strip markdown fences
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        # Find JSON array
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]

        posts = json.loads(raw)

        # Validate structure
        validated = []
        for p in posts:
            if not isinstance(p, dict):
                continue
            validated.append({
                "post_number": p.get("post_number", len(validated) + 1),
                "name": p.get("name", f"Post_{len(validated)+1:02d}"),
                "description": p.get("description", ""),
                "character": p.get("character", character or "Shay"),
                "outfit": p.get("outfit", ""),
                "vibe": p.get("vibe", ""),
                "scenario_key": p.get("scenario_key", ""),
                "aspect_ratio": p.get("aspect_ratio", "9:16"),
                "day_of_week": p.get("day_of_week", ""),
            })

        print(f"[plan_campaign] ✅ Generated {len(validated)} post plans.")
        return validated

    except Exception as e:
        print(f"[plan_campaign] Error calling Gemini: {e}")
        return []


def build_campaign_job(post_plan: dict, output_base: str, username: str = "default") -> dict:
    """
    Convert a post plan dict (from plan_campaign) into a CampaignManager.add_job() payload.

    Args:
        post_plan:    One item from plan_campaign() output.
        output_base:  Base output directory (e.g. "output/users/{username}/Campaign").
        username:     Username for output isolation.

    Returns:
        kwargs dict ready to splat into CampaignManager.add_job(**kwargs).
    """
    prompt_data = {
        "positive_prompt": post_plan.get("vibe", "") + " — " + post_plan.get("description", ""),
        "negative_prompt": "blurry, low quality, cartoon, watermark",
        "aspect_ratio": post_plan.get("aspect_ratio", "9:16"),
    }

    return {
        "name": post_plan["name"],
        "description": post_plan.get("description", ""),
        "prompt_data": prompt_data,
        "settings": {"batch_count": 1},
        "output_folder": output_base,
        "char_path": None,
        "outfit_path": None,
        "vibe_path": None,
        "job_type": "image",
    }


# ─── Quick Test (run directly) ────────────────────────────────────────────────
if __name__ == "__main__":
    test_brief = "luxury lifestyle and travel content for Shay — mix of fashion, rooftop moments, and travel vibes"
    print(f"\n📋 Brief: {test_brief}")
    print(f"📊 Planning 5 posts...\n")

    posts = plan_campaign(test_brief, num_posts=5, character="Shay")

    for p in posts:
        print(f"  [{p['post_number']:02d}] {p['name']} — {p['vibe']} ({p['day_of_week']})")
        print(f"       Outfit: {p['outfit']}")
        print(f"       {p['description']}\n")
