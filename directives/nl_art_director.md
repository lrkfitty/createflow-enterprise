# NL Art Director Directive

## Goal
Map a free-text creative brief from the user into a structured set of CreateFlow asset references (character, outfit, vibe/scenario). This removes the need for the user to navigate dropdowns — they can speak or type naturally, and the system resolves the intent to existing assets.

## Inputs
- **Brief** (str): Free-text description of the desired shot. Examples:
  - "Shay at a rooftop bar at night, black mini dress, dark and cinematic"
  - "moody coffee shop vibes, editorial look, golden hour"
  - "pool day in Mykonos, white bikini, luxury resort"

## Tools
1. `execution/parse_intent.py` → `parse_intent(brief, world_db_path)` — calls Gemini to map brief → asset dict.

## Output
Structured dict:
```json
{
  "character": "Shay",
  "outfit": "black mini dress",
  "vibe": "City Rooftop Bar",
  "scenario_key": "rooftop_bar_night",
  "aspect_ratio": "9:16",
  "additional_notes": "dark and cinematic, moonlight",
  "confidence": "high"
}
```
This dict is then passed directly to `generate_prompt_content()` and `generate_image_from_prompt()`.

## Prompt Structure (sent to Gemini)
The system prompt includes:
- Full character list from `world_db.json`
- Full scenario list from `world_db.json` (capped at 40 for token budget)
- Instructions to extract outfit as free text (no list needed)
- Instructions to determine aspect ratio from context (portrait default = 9:16)

## Edge Cases & Learnings
- **No character match**: Default to "Shay".
- **Vague brief**: Set `confidence = "low"`, pass raw brief as `additional_notes`. The generation can still proceed with whatever was captured.
- **Outfit not mentioned**: Leave as empty string — the prompt generator will still work from the character + vibe alone.
- **Multiple vibes**: Pick the single best match, put others in `additional_notes`.
- **API rate limit (429)**: `parse_intent.py` will raise — caller (app.py) should catch and retry with a short delay.
- **Gemini model**: Uses `gemini-2.0-flash` (fast + free tier). Upgrade to `gemini-1.5-pro` for complex briefs if needed.

## Integration Point
Art Director tab in `app.py`:
1. User types/speaks brief
2. `parse_intent()` called
3. Parsed result shown to user as a confirmation card
4. User can edit any field before hitting Generate
5. On confirm → `generate_prompt_content()` → `generate_image_from_prompt()`
