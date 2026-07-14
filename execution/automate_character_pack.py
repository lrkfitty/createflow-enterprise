"""
CreateFlow Character Studio Automation
Navigates the local Streamlit app, fills in all Character Studio parameters
for 20 diverse characters, and queues them all for batch generation.
"""

import time
import sys
from playwright.sync_api import sync_playwright, Page

APP_URL = "http://localhost:8502"
USERNAME = "TyrieLarkin@gmail.com"
PASSWORD = "Larkin2017!"

# ─────────────────────────────────────────────
# 20 DIVERSE CHARACTERS — mapped to app options
# ─────────────────────────────────────────────
CHARACTERS = [
    {
        "name": "Marcus",
        "gender": "Male",
        "ethnicity": "Nigerian (Yoruba / Igbo / Hausa)",
        "age": 38,
        "hair_color": "Black",
        "hair_style": "Medium Length",
        "custom_hairstyle": "clean fade, close-cropped sides",
        "facial_hair": "Stubble",
        "eye_color": "Brown",
        "earrings": "None",
        "necklace": "None",
        "watch": "Rolex (Classic Jubilee)",
        "description": "Sharp entrepreneur energy. Strong jawline, confident dark eyes, athletic build, warm brown skin."
    },
    {
        "name": "Sofia",
        "gender": "Female",
        "ethnicity": "Mixed Race",
        "age": 25,
        "hair_color": "Dark Brown",
        "hair_style": "Long Wavy",
        "custom_hairstyle": "",
        "facial_hair": "None",
        "eye_color": "Hazel",
        "earrings": "Small Hoops",
        "necklace": "Dainty Gold Chain",
        "watch": "None",
        "lashes": "Natural",
        "lips": "Subtle Gloss",
        "blush": "Subtle",
        "description": "Latina female. Olive skin, petite but toned, bright warm energy. Lifestyle coach vibes."
    },
    {
        "name": "Yuki",
        "gender": "Female",
        "ethnicity": "Any",
        "age": 31,
        "hair_color": "Black",
        "hair_style": "Bob Cut",
        "custom_hairstyle": "sleek low bun, East Asian features",
        "facial_hair": "None",
        "eye_color": "Brown",
        "earrings": "Studs (small)",
        "necklace": "Dainty Silver Chain",
        "watch": "None",
        "lashes": "Natural",
        "lips": "Natural",
        "description": "East Asian female. Fair porcelain skin, sharp almond eyes, elegant posture. Fashion editorial look."
    },
    {
        "name": "Darius",
        "gender": "Male",
        "ethnicity": "Nigerian (Yoruba / Igbo / Hausa)",
        "age": 22,
        "hair_color": "Black",
        "hair_style": "Coily",
        "custom_hairstyle": "locs pulled back loosely",
        "facial_hair": "None",
        "eye_color": "Brown",
        "earrings": "Studs (small)",
        "necklace": "Dainty Gold Chain",
        "watch": "None",
        "description": "Tall athletic build. Deep brown skin, expressive eyes, easy confident smile. Streetwear / sports energy."
    },
    {
        "name": "Camille",
        "gender": "Female",
        "ethnicity": "Mixed Race",
        "age": 28,
        "hair_color": "Auburn",
        "hair_style": "Curly",
        "custom_hairstyle": "natural curly auburn hair with volume",
        "facial_hair": "None",
        "eye_color": "Hazel",
        "earrings": "Medium Hoops",
        "necklace": "Dainty Gold Chain",
        "watch": "None",
        "lashes": "Natural",
        "lips": "Subtle Gloss",
        "blush": "Natural",
        "description": "Mixed-race (Black and French). Medium brown skin, freckles, warm amber-hazel eyes. Parisian travel lifestyle."
    },
    {
        "name": "Raj",
        "gender": "Male",
        "ethnicity": "Any",
        "age": 35,
        "hair_color": "Black",
        "hair_style": "Medium Length",
        "custom_hairstyle": "neat short dark hair, South Asian features",
        "facial_hair": "Clean Shaven",
        "eye_color": "Brown",
        "earrings": "None",
        "necklace": "None",
        "watch": "Apple Watch (Sport)",
        "description": "South Asian male. Warm golden-brown skin, sharp intelligent eyes, medium build. Tech startup professional."
    },
    {
        "name": "Elena",
        "gender": "Female",
        "ethnicity": "Any",
        "age": 43,
        "hair_color": "Platinum Blonde",
        "hair_style": "Shoulder Length",
        "custom_hairstyle": "sleek, straight, Eastern European refined features",
        "facial_hair": "None",
        "eye_color": "Grey",
        "earrings": "Studs (diamond/gem)",
        "necklace": "Pearl Strand",
        "watch": "Cartier Santos / Tank",
        "lashes": "Wispy Lashes",
        "lips": "Matte Lipstick",
        "blush": "Subtle",
        "description": "Eastern European female. Cool pale skin, striking blue-grey eyes, refined features, poised. Luxury executive."
    },
    {
        "name": "Kofi",
        "gender": "Male",
        "ethnicity": "Ghanaian",
        "age": 28,
        "hair_color": "Black",
        "hair_style": "Any",
        "custom_hairstyle": "very short close-cropped hair",
        "facial_hair": "None",
        "eye_color": "Brown",
        "earrings": "None",
        "necklace": "None",
        "watch": "None",
        "description": "Tall lean build, very dark rich skin, high cheekbones, broad warm smile. Vibrant cultural energy."
    },
    {
        "name": "Priya",
        "gender": "Female",
        "ethnicity": "Any",
        "age": 31,
        "hair_color": "Black",
        "hair_style": "Long Straight",
        "custom_hairstyle": "long silky black hair worn loose, South Asian features",
        "facial_hair": "None",
        "eye_color": "Brown",
        "earrings": "Studs (small)",
        "necklace": "Dainty Gold Chain",
        "watch": "None",
        "lashes": "Natural",
        "lips": "Natural",
        "blush": "Subtle",
        "description": "South Asian female. Warm caramel skin, graceful build, serene expression. Wellness and mindfulness brand."
    },
    {
        "name": "Jake",
        "gender": "Male",
        "ethnicity": "Any",
        "age": 35,
        "hair_color": "Dirty Blonde",
        "hair_style": "Medium Length",
        "custom_hairstyle": "tousled, sandy brown, outdoorsy look",
        "facial_hair": "Stubble",
        "eye_color": "Hazel",
        "earrings": "None",
        "necklace": "None",
        "watch": "None",
        "description": "White male. Light skin, hazel eyes, athletic-lean build. Rugged outdoorsy Pacific Northwest adventure look."
    },
    {
        "name": "Amara",
        "gender": "Female",
        "ethnicity": "Nigerian (Yoruba / Igbo / Hausa)",
        "age": 25,
        "hair_color": "Black",
        "hair_style": "Any",
        "custom_hairstyle": "shaved head, clean razor-short hair",
        "facial_hair": "None",
        "eye_color": "Brown",
        "earrings": "Studs (small)",
        "necklace": "None",
        "watch": "None",
        "lashes": "Dramatic Lashes",
        "lips": "Bold Lipstick",
        "blush": "Heavy Contour",
        "description": "Deep ebony skin, strong bone structure, powerful bold gaze. High-fashion editorial."
    },
    {
        "name": "Carlos",
        "gender": "Male",
        "ethnicity": "Mixed Race",
        "age": 52,
        "hair_color": "Dark Brown",
        "hair_style": "Medium Length",
        "custom_hairstyle": "short salt-and-pepper hair, Latino features",
        "facial_hair": "Heavy Stubble",
        "eye_color": "Brown",
        "earrings": "None",
        "necklace": "None",
        "watch": "None",
        "description": "Latino male. Warm tan skin, laugh lines, kind brown eyes, stocky distinguished build. Community leader warmth."
    },
    {
        "name": "Mei Lin",
        "gender": "Female",
        "ethnicity": "Any",
        "age": 47,
        "hair_color": "Black",
        "hair_style": "Bob Cut",
        "custom_hairstyle": "short stylish bob with silver streaks, East Asian features",
        "facial_hair": "None",
        "eye_color": "Brown",
        "earrings": "Studs (diamond/gem)",
        "necklace": "Dainty Gold Chain",
        "watch": "Cartier Santos / Tank",
        "lashes": "Natural",
        "lips": "Matte Lipstick",
        "blush": "Natural",
        "description": "Chinese-American female. Fair skin, sophisticated dark eyes. Executive / finance power portrait."
    },
    {
        "name": "Tobias",
        "gender": "Male",
        "ethnicity": "Any",
        "age": 22,
        "hair_color": "Dirty Blonde",
        "hair_style": "Medium Length",
        "custom_hairstyle": "disheveled, indie creative look, European features",
        "facial_hair": "Light Stubble",
        "eye_color": "Brown",
        "earrings": "Studs (small)",
        "necklace": "None",
        "watch": "None",
        "description": "German male. Fair skin, round wire-frame glasses, creative intellectual look. Gen Z Berlin arts scene."
    },
    {
        "name": "Aaliyah",
        "gender": "Female",
        "ethnicity": "Nigerian (Yoruba / Igbo / Hausa)",
        "age": 30,
        "hair_color": "Black",
        "hair_style": "Long Straight",
        "custom_hairstyle": "long box braids with gold cuffs adorning them",
        "facial_hair": "None",
        "eye_color": "Brown",
        "earrings": "Large Statement Hoops",
        "necklace": "Layered Chains (2-3)",
        "watch": "None",
        "lashes": "Dramatic Lashes",
        "lips": "High Gloss",
        "blush": "Bronzed",
        "description": "Rich dark brown skin, full lips, glowing warm eyes. Curvy and glamorous. Miami lifestyle influencer."
    },
    {
        "name": "Hiroshi",
        "gender": "Male",
        "ethnicity": "Any",
        "age": 60,
        "hair_color": "Any",
        "hair_style": "Any",
        "custom_hairstyle": "silver short cropped hair, Japanese features",
        "facial_hair": "Clean Shaven",
        "eye_color": "Brown",
        "earrings": "None",
        "necklace": "None",
        "watch": "None",
        "description": "Japanese male, 60s. Silver cropped hair, calm wise eyes, lean composed build. Zen garden serene wisdom."
    },
    {
        "name": "Zara",
        "gender": "Female",
        "ethnicity": "Any",
        "age": 25,
        "hair_color": "Black",
        "hair_style": "Long Wavy",
        "custom_hairstyle": "thick dark wavy hair, Middle Eastern features",
        "facial_hair": "None",
        "eye_color": "Brown",
        "earrings": "Studs (small)",
        "necklace": "Dainty Gold Chain",
        "watch": "None",
        "lashes": "Natural",
        "lips": "Natural",
        "blush": "Subtle",
        "description": "Middle Eastern female. Olive-toned skin, large expressive dark eyes, full bold brows. Fitness wellness brand."
    },
    {
        "name": "Jerome",
        "gender": "Male",
        "ethnicity": "Nigerian (Yoruba / Igbo / Hausa)",
        "age": 52,
        "hair_color": "Black",
        "hair_style": "Any",
        "custom_hairstyle": "completely bald head, no hair",
        "facial_hair": "Heavy Stubble",
        "facial_hair_color": "Dark Brown",
        "eye_color": "Brown",
        "earrings": "None",
        "necklace": "None",
        "watch": "Rolex (Classic Jubilee)",
        "description": "Bald, full grey beard, deep rich brown skin, strong broad build. Commanding calm authority. Mentor executive."
    },
    {
        "name": "Luna",
        "gender": "Female",
        "ethnicity": "Mixed Race",
        "age": 22,
        "hair_color": "Brunette",
        "hair_style": "Long Wavy",
        "custom_hairstyle": "ombre from dark to caramel highlights",
        "facial_hair": "None",
        "eye_color": "Green",
        "earrings": "Dangling / Drop Earrings",
        "necklace": "Layered Chains (2-3)",
        "watch": "None",
        "lashes": "Wispy Lashes",
        "lips": "Subtle Gloss",
        "blush": "Natural",
        "description": "Latina female. Medium tan skin, bright playful green eyes, petite and energetic. Tropical beach travel social."
    },
    {
        "name": "Aiden",
        "gender": "Male",
        "ethnicity": "Mixed Race",
        "age": 25,
        "hair_color": "Dark Brown",
        "hair_style": "Wavy",
        "custom_hairstyle": "medium wavy dark hair, mixed Asian-White features",
        "facial_hair": "Light Stubble",
        "eye_color": "Grey",
        "earrings": "None",
        "necklace": "None",
        "watch": "Apple Watch (Sport)",
        "description": "Mixed-race (Asian and White). Light skin with warm undertones, bright grey-blue eyes. Content creator clean look."
    }
]


def set_selectbox(page: Page, label: str, value: str):
    """Select a value from a Streamlit selectbox by label."""
    if not value or value == "None":
        return
    try:
        sb = page.locator('[data-testid="stSelectbox"]').filter(has_text=label).first
        sb.click()
        time.sleep(0.5)
        opt = page.locator('[role="option"]').filter(has_text=value).first
        opt.click()
        time.sleep(0.4)
    except Exception as e:
        print(f"    ⚠️ Could not set {label}={value}: {e}")


def set_age_slider(page: Page, age: int):
    """Set the age slider (range 18–90) by clicking at the right proportion."""
    try:
        slider = page.locator('[data-testid="stSlider"]').filter(has_text="Age").first
        track = slider.locator('[role="slider"]').first

        # Focus the slider and use keyboard to hit the value
        track.click()
        time.sleep(0.3)

        # Get current value
        current = int(track.get_attribute('aria-valuenow') or 25)
        target = age

        # Move with arrow keys
        diff = target - current
        key = 'ArrowRight' if diff > 0 else 'ArrowLeft'
        for _ in range(abs(diff)):
            page.keyboard.press(key)
            time.sleep(0.02)
        time.sleep(0.3)
    except Exception as e:
        print(f"    ⚠️ Could not set age slider: {e}")


def set_text_field(page: Page, label: str, value: str):
    """Fill a text input by its aria-label."""
    if not value:
        return
    try:
        field = page.get_by_label(label).first
        field.fill(value)
        time.sleep(0.3)
    except Exception as e:
        print(f"    ⚠️ Could not set text field {label}: {e}")


def reset_character_form(page: Page):
    """Navigate back to Character Studio to reset the form."""
    # Use the radio button in the nav (not the heading on the page)
    page.get_by_test_id('stRadio').get_by_text('Character Studio').click()
    time.sleep(3)
    # Expand all sections
    for exp in page.locator('[data-testid="stExpander"]').all():
        try:
            exp.click()
            time.sleep(0.2)
        except:
            pass
    time.sleep(0.5)


def fill_and_queue_character(page: Page, char: dict, idx: int, total: int):
    """Fill all Character Studio fields for one character and queue it."""
    print(f"\n[{idx}/{total}] Queuing: {char['name']}")

    reset_character_form(page)

    # Generation Mode
    set_selectbox(page, "Generation Mode", "Concept Portrait (Vertical)")

    # Core Identity
    set_selectbox(page, "Gender", char["gender"])
    set_selectbox(page, "Ethnicity / Background", char["ethnicity"])
    set_age_slider(page, char["age"])

    # Hair
    set_selectbox(page, "Hair Color", char.get("hair_color", "Any"))
    set_selectbox(page, "Hair Style", char.get("hair_style", "Any"))
    custom_hs = char.get("custom_hairstyle", "")
    if custom_hs:
        set_text_field(page, "Custom Hairstyle (Optional)", custom_hs)

    # Facial Hair (males)
    fh = char.get("facial_hair", "None")
    if fh and fh != "None":
        set_selectbox(page, "Facial Hair Style", fh)
        fhc = char.get("facial_hair_color", "Same as Hair")
        set_selectbox(page, "Facial Hair Color", fhc)

    # Eyes
    set_selectbox(page, "Eye Color", char.get("eye_color", "Any"))

    # Accessories
    set_selectbox(page, "Earrings", char.get("earrings", "None"))
    set_selectbox(page, "Necklace", char.get("necklace", "None"))
    set_selectbox(page, "Watch", char.get("watch", "None"))

    # Makeup (females)
    if char["gender"] == "Female":
        set_selectbox(page, "Lashes", char.get("lashes", "None"))
        set_selectbox(page, "Lips", char.get("lips", "None"))
        set_selectbox(page, "Blush/Bronzer", char.get("blush", "None"))

    # Character Description
    desc = char.get("description", "")
    if desc:
        set_text_field(page, "Nuanced Details", desc)

    # Character Name
    set_text_field(page, "Character Name", char["name"])

    # Add to Queue
    try:
        page.get_by_text("Add to Queue").click()
        time.sleep(2)
        # Check for success toast
        toast = page.locator('[data-testid="stToast"]')
        if toast.count() > 0:
            print(f"    ✅ Queued: {char['name']} — {toast.first.inner_text()[:60]}")
        else:
            print(f"    ✅ Queued: {char['name']}")
    except Exception as e:
        print(f"    ❌ Failed to queue {char['name']}: {e}")


def check_campaign_queue(page: Page):
    """Navigate to Campaign Queue and show its contents."""
    page.get_by_text('Campaign Queue').click()
    time.sleep(4)
    text = page.evaluate('() => document.body.innerText')
    print("\n--- Campaign Queue ---")
    # Find relevant lines
    for line in text.split('\n'):
        l = line.strip()
        if l and len(l) > 2:
            print(' ', l)
    page.screenshot(path='/tmp/cf_queue.png', full_page=True)


def main():
    total = len(CHARACTERS)
    print(f"\n🎬 CreateFlow Automation — Queuing {total} characters via Character Studio\n")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1280, 'height': 2400})

        # Login
        print("Logging in...")
        page.goto(APP_URL, timeout=30000)
        time.sleep(5)
        page.locator('input').nth(0).fill(USERNAME)
        page.locator('input').nth(1).fill(PASSWORD)
        page.get_by_test_id('stBaseButton-primary').click()
        time.sleep(6)
        print("✅ Logged in")

        # Queue all characters
        for i, char in enumerate(CHARACTERS, 1):
            fill_and_queue_character(page, char, i, total)
            time.sleep(1)

        # Check the queue
        print("\n✅ All characters queued. Checking Campaign Queue...")
        check_campaign_queue(page)

        browser.close()

    print("\n" + "=" * 60)
    print(f"✅ Done — {total} characters added to Campaign Queue")
    print("📸 Queue screenshot saved: /tmp/cf_queue.png\n")


if __name__ == "__main__":
    main()
