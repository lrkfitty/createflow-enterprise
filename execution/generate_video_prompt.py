import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load Env
load_dotenv()

def generate_motion_prompt(image_path, movement_type="Auto", physics_focus="standard", emotion="Neutral", additional_context=""):
    """
    Analyzes an image and generates a high-fidelity motion prompt for AI Video Generators (Kling/Veo).
    Enforces physics tokens (jiggle, water, skin) based on user preference.
    """
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: Missing GOOGLE_API_KEY for Motion Analysis."

    genai.configure(api_key=api_key)
    # Using 2.0 Flash as verified in available models list
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
    except:
        model = genai.GenerativeModel('gemini-2.0-flash') # Fallback to free model

    # Read Image Data
    import PIL.Image
    # Read Image Data
    import PIL.Image
    import requests
    from io import BytesIO
    
    try:
        if image_path.startswith(('http://', 'https://')):
            resp = requests.get(image_path)
            resp.raise_for_status()
            img = PIL.Image.open(BytesIO(resp.content))
        else:
            img = PIL.Image.open(image_path)
    except Exception as e:
        return f"Error loading image: {e}"

    # Construct Constraints based on user input
    physics_keywords = ""
    if "High Physics" in physics_focus:
        physics_keywords = "Ensure highly realistic physics: emphasize skin texture realism, natural soft-body dynamics, fabric movement, and detailed fluid simulation if water is present."
    elif "Jiggle" in physics_focus:
         physics_keywords = "Emphasize soft-body dynamics, natural jiggle physics, bounce, and reactive skin movement. High fidelity skin texture."
    elif "Water/Liquids" in physics_focus:
         physics_keywords = "Focus on fluid dynamics, water caustics, wet skin texture, droplets, and splashes. Realistic liquid simulation."

    prompt_instruction = f"""
    ROLE: You are "Cinematography Royalty" — the world's most sophisticated AI Content Director. You specialize in hyper-realistic video generation (Kling/Sora/Veo).
    
    TASK: Analyze the provided image and write a **massive, high-fidelity prompt** (At LEAST 2000 characters) to animate it.
    
    INTENT: Make the video feel human, alive, and physically grounded. Focus on "Micromovements" — small, nearly imperceptible details that sell reality.
    
    USER INPUTS:
    - Camera Move: {movement_type}
    - Physics Priority: {physics_focus} {physics_keywords}
    - Vibe: {emotion}
    - Context: {additional_context}
    
    
    STRUCTURE YOUR PROMPT AS A SINGLE, FLOWING NARRATIVE INCORPORATING:
    1. **The Core Action**: What is happening? (e.g., "She turns her head slowly...")
    2. **Micromovements (CRITICAL)**: Describe the twitch of a muscle, the flutter of an eyelash, the shift of weight, the breathing pattern. 
    3. **Physics & Atmosphere**: How does the hair react to wind? How does the fabric fold? How does the light caustic shift?
    4. **Cinematography**: {movement_type}. Lens flares, depth of field rack focus, film grain, exposure.
    5. **Humanity**: If a person is present, describe their thought process through micro-expressions.
    
    ## THE REALISM BIBLE (STRICT ADHERENCE REQUIRED):
    Prioritize human realism above all else. This is observational realism, not animation.
    
    [HUMAN BODY]
    - Subtlety: Breath visible in chest/clavicle. Posture shifts due to fatigue/balance.
    - Timing: Imperfect synchronization between limbs.
    - Eyes: Micro-saccades, focus drift, re-locking. No rhythmic blinking.
    - Face: Jaw relaxation. Emotion registers in eyes/tension, not just mouth.
    
    [PHYSICS]
    - Momentum: Bodies accelerate/decelerate naturally. No floatiness. No instant stops.
    - Materials: Hair lags behind head. Fabric has weight/delay. 
    - Interactions: Objects react with correct mass/rebound.
    
    [LIGHT]
    - Specular highlights slide across skin.
    - Subsurface scattering visible in motion.
    - Shadows soften/sharpen based on distance.
    - Skin must show pores, texture, sheen. NEVER plastic.
    
    [CAMERA]
    - {movement_type}.
    - Handheld = micro-jitter. Focus breathing feels optical. 
    - Stillness is powerful.
    
    [BEHAVIOR]
    - Reaction speed: Eyes move, then head, then body.
    - Thoughts vary micro-expressions before macro actions.
    
    [ABSOLUTE CONSTRAINTS]
    - No animation artifacts. No looped motion. No "AI Smoothness".
    - Result must be indistinguishable from live-action 8K footage.
    
    REQUIREMENTS:
    - LENGTH: **STRICTLY between 1000 and 2000 characters.** (Optimized for Kling)
    - TONE: Professional, Artistic, Technical.
    - NO: "Here is the prompt", just give me the raw prompt text.
    """

    try:
        response = model.generate_content([prompt_instruction, img])
        return response.text.strip()
    except Exception as e:
        return f"Error analyzing image: {e}"
