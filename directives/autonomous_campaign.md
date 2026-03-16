# Autonomous Campaign Planning Directive

## Goal
Convert a single high-level content brief into a fully planned N-post campaign, automatically generating distinct visual scenarios and queuing them as jobs in `CampaignManager`. The user inputs one sentence and gets a full content calendar ready to run.

## Inputs
- **Brief** (str): High-level creative direction. Examples:
  - "30 days of luxury lifestyle content for Shay — mix of travel, fashion, and rooftop moments"
  - "fitness influencer daily content, gym sessions and healthy eating, energetic and motivational"
  - "promote a new clothing line with diverse editorial looks across 15 posts"
- **num_posts** (int): Number of posts to plan (range: 5–30).
- **character** (str, optional): Lock all posts to a specific character name.

## Tools
1. `execution/plan_campaign.py` → `plan_campaign(brief, num_posts, character)` — calls Gemini to generate the content calendar.
2. `execution/plan_campaign.py` → `build_campaign_job(post_plan, output_base, username)` — converts each plan to a `CampaignManager.add_job()` payload.
3. `execution/campaign_runner.py` → `CampaignManager.add_job(**kwargs)` — queues each job.

## Output
- N jobs added to `current_campaign.json` with status `pending`.
- User can review the planned calendar as a preview table before queuing.
- Jobs appear in the existing Campaign Manager tab, processed with the existing runner.

## LLM Prompt Structure (sent to Gemini)
The system prompt includes:
- Complete scenario list from `world_db.json` grouped by category
- Character lock instruction if provided
- Rules for variety, category mixing, and slug naming
- Output schema: JSON array of N post plan objects

## Edge Cases & Learnings
- **Gemini returns < N posts**: Validate count in `plan_campaign.py`. If short, log a warning — do not pad with empty jobs.
- **Gemini returns invalid JSON**: Log error, return `[]`. App shows an error message to user.
- **Scenario key not in world_db**: The `scenario_key` field may not exactly match any world_db key (LLM hallucination). `build_campaign_job()` gracefully omits the vibe_path in this case — the job still runs with prompt text only.
- **Large batches (30 posts)**: Gemini 2.0 Flash handles this fine. If output is truncated, reduce to 20 and run twice.
- **Token budget**: Scenario list is capped at 12 per category to stay within context limits.

## Integration Point
Campaign Manager tab in `app.py` — "🤖 Auto-Plan Campaign" expander:
1. User enters brief + sets num_posts slider
2. `plan_campaign()` called → returns list of post plans
3. App renders preview table (post #, name, vibe, outfit, day)
4. "Queue All" button → loops through plans, calls `build_campaign_job()` + `CampaignManager.add_job()` for each
5. Jobs appear in existing Campaign Manager job list, run with existing "▶ Run Campaign" button
