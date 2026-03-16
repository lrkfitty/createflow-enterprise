# Content Creation Directive

## Goal
Generate a high-quality AI image based on user-selected criteria (Vibe, Outfit) using an LLM to create a prompt and an Image Generation API to produce the visual.

## Inputs
- **Vibe**: The atmosphere or setting (e.g., "Coffee Shop").
- **Outfit**: The character's clothing (e.g., "Casual Hoodie").
- **Character**: The specific character model to use (default: "Default Influencer").

## Tools
1.  `execution/generate_prompt.py`: Uses an LLM to expand the inputs into a detailed prompt.
2.  `execution/generate_image.py`: Sends the detailed prompt to the Image Gen API.

## Output
- A generated image saved in user-specified output folder (default: `output/`).
- Logs in `.tmp/`.

## Prompt Structure (for LLM)
The LLM should return a JSON object with the following keys:
- `positive_prompt`: Detailed visual description.
- `negative_prompt`: What to avoid (e.g., "bad anatomy, blurry").
- `aspect_ratio`: Recommended aspect ratio (e.g., "9:16" for social media).
