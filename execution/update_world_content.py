import json
import os

# 1. Define New Scenarios Data
new_scenarios_list = [
    # Lifestyle / Daily IG Life
    {"name": "Rooftop Brunch with Friends", "category": "Lifestyle", "template": "High-end rooftop restaurant, sunny morning, mimosas on table, city skyline background, vibrant brunch aesthetic, soft diffused lighting."},
    {"name": "Poolside Hotel Afternoon", "category": "Lifestyle", "template": "Luxury hotel pool deck, turquoise water, lounge chair, oversized sunglasses, tropical drink, vacation relax mood, golden sunlight."},
    {"name": "Getting Ready in Luxury Bathroom", "category": "Lifestyle", "template": "White marble bathroom, vanity mirror, makeup products spread out, bathrobe, soft cosmetic lighting, clean aesthetic."},
    {"name": "Sunset Balcony Chill", "category": "Lifestyle", "template": "Private apartment balcony, golden hour sunset, city view, holding wine glass, warm orange glow, relaxed evening vibe."},
    {"name": "Coffee Run in Matching Athleisure", "category": "Lifestyle", "template": "City street sidewalk, holding iced coffee cup, wearing matching athletic set, busy street bokeh, morning errand energy."},
    {"name": "Gym Mirror Moment", "category": "Lifestyle", "template": "Upscale gym interior, full length mirror, fitness equipment background, harsh gym lighting, workout glow."},
    {"name": "Post-Workout Smoothie Stop", "category": "Lifestyle", "template": "Juice bar interior, colorful fruit display, holding green smoothie, athletic wear, clean health aesthetic."},
    {"name": "Dressing Room Try-On", "category": "Lifestyle", "template": "Boutique dressing room, multiple outfits hanging, mirror selfie angle, soft fitting room lighting, fashion indecision."},
    {"name": "Airport Terminal Fit Check", "category": "Lifestyle", "template": "Modern airport terminal, large windows with planes, luggage cart, comfy travel outfit, travel anticipation vibe."},
    {"name": "Late-Night City Drive", "category": "Lifestyle", "template": "Car interior, dashboard lights, city streetlights blurring outside, night mood, moody cinematic lighting."},
    {"name": "Casual Lunch Café", "category": "Lifestyle", "template": "Trendy outdoor café seating, salad bowl, sparkling water, dappled sunlight through trees, casual dining vibe."},
    {"name": "Hotel Hallway Walk", "category": "Lifestyle", "template": "Long luxury hotel corridor, patterned carpet, wall sconces, walking away from camera, depth of field."},
    {"name": "Morning Bed Sunlight", "category": "Lifestyle", "template": "White hotel bedding, messy sheets, bright morning window light, coffee mug on nightstand, cozy wake-up mood."},
    {"name": "Bathroom Mirror Selfie", "category": "Lifestyle", "template": "Clean bathroom mirror reflection, phone covering face slightly, casual home outfit, ring light reflection."},
    {"name": "Pre-Game Apartment Vibes", "category": "Lifestyle", "template": "Living room, music playing vibe, drinks on table, getting hyped, pre-party energy, warm indoor lighting."},
    {"name": "Morning Stretch at Home", "category": "Lifestyle", "template": "Yoga mat in living room, sunlight streaming in, stretching pose, plants in background, wellness aesthetic."},
    {"name": "Journaling in Sunlight", "category": "Lifestyle", "template": "Cozy nook, leather journal, pen in hand, sunbeam hitting paper, peaceful mindfulness vibe, dust motes in air."},
    {"name": "Late-Night Kitchen Conversation", "category": "Lifestyle", "template": "Kitchen island, midnight snack, dim under-cabinet lighting, leaning on counter, intimate talk vibe."},
    {"name": "Sitting in Parked Car Thinking", "category": "Lifestyle", "template": "Driver's seat, parked car, rain on window or streetlights, contemplative mood, staring out, moody lighting."},
    {"name": "Sunday Reset at Home", "category": "Lifestyle", "template": "Tidying up living space, fresh flowers, vacuum cleaner or laundry basket, clean home aesthetic, bright airy light."},

    # Podcaster / Creator Life
    {"name": "Recording Podcast in Home Studio", "category": "Podcast", "template": "Home studio setup, Shure SM7B microphone, boom arm, headphones on, sound foam on walls, focused speaking vibe."},
    {"name": "Podcast Mic Setup in Hotel", "category": "Podcast", "template": "Hotel desk, portable podcast mic setup, laptop open, window view, working on the go aesthetic."},
    {"name": "Café Podcast Recording Overseas", "category": "Podcast", "template": "Outdoor European café, portable recorder on table, espresso cup, ambient street background, digital nomad vibe."},
    {"name": "Late-Night Editing Podcast Episode", "category": "Podcast", "template": "Dark room, monitor screen glow, timeline visible on screen, coffee cup, focused work mode, blue light."},
    {"name": "Recording Voice Notes while Traveling", "category": "Podcast", "template": "Walking down foreign street, holding phone like mic, speaking intently, travel vlog style, dynamic background."},
    {"name": "Planning Goals on Laptop", "category": "Podcast", "template": "Cozy workspace, laptop open to spreadsheet/notion, notebook, focused planning, ambitious mood."},
    {"name": "Working at Café Solo", "category": "Podcast", "template": "Busy coffee shop, laptop open, noise cancelling headphones, deep work focus, blurred background customers."},
    {"name": "Evening Balcony Reflection", "category": "Podcast", "template": "Balcony railing, city lights at night, looking out, contemplative thinker pose, cinematic night lighting."},

    # Bossed-Up Travel / Luxury Life
    {"name": "Luxury Hotel Lobby Arrival", "category": "Travel", "template": "Grand hotel lobby, chandeliers, marble floors, bellhop with luggage, grand entrance moment, expensive architecture."},
    {"name": "Checking Into Five-Star Hotel", "category": "Travel", "template": "Hotel reception desk, handing over credit card, passport on counter, concierge smiling, premium service vibe."},
    {"name": "Airport Lounge Business Moment", "category": "Travel", "template": "Exclusive airport lounge, glass of champagne, laptop open, runway view, business class travel aesthetic."},
    {"name": "International Flight Window Seat", "category": "Travel", "template": "Airplane window view, clouds and wing, champagne glass on tray table, first class seat, luxury travel."},
    {"name": "Packing Luxury Carry-On Suitcase", "category": "Travel", "template": "Open Rimowa suitcase on bed, organized packing cubes, designer items, travel prep, clean layout."},
    {"name": "Taxi Ride Through New City", "category": "Travel", "template": "Backseat of black car, city blur outside window, looking out, motion blur, arrival excitement."},
    {"name": "Balcony View Overlooking City", "category": "Travel", "template": "High-rise balcony, sprawling city view below, day or night, feeling on top of the world, wide shot."},
    {"name": "Rooftop Dinner in Foreign City", "category": "Travel", "template": "Rooftop dining table, exotic city skyline, candlelit dinner, white tablecloth, romantic luxury vibes."},
    {"name": "Morning Espresso Abroad", "category": "Travel", "template": "Small italian street table, single espresso cup, newspaper, cobblestone street, slow morning travel vibe."},
    {"name": "Private Villa Morning", "category": "Travel", "template": "Infinity pool edge, ocean horizon, breakfast floating tray, tropical villa architecture, paradise morning."},
    {"name": "Vacation Resort Check-In", "category": "Travel", "template": "Open-air resort lobby, welcome drink, ocean breeze, palm trees visible, tropical arrival mood."},

    # High-Fashion / Shopper World
    {"name": "Shopping Designer Boutique Abroad", "category": "Fashion", "template": "High-end boutique interior, minimalist racks, designer bags display, shopping in Paris/Milan vibe."},
    {"name": "Private Shopping Appointment", "category": "Fashion", "template": "VIP room, champagne, fashion assistant holding items, exclusive shopping experience, luxury velvet seating."},
    {"name": "Window Shopping Luxury District", "category": "Fashion", "template": "Street view, looking into luxury store window, reflection visible, holding shopping bags, high fashion street style."},
    {"name": "Reviewing Outfits in Hotel Mirror", "category": "Fashion", "template": "Full length hotel mirror, checking fit, multiple outfit options on bed, getting ready sequence."},
    {"name": "Luxury Mall Shopping Spree", "category": "Fashion", "template": "Grand mall atrium, holding multiple designer bags, walking confidently, marble floors, consumerism pop."},
    {"name": "Fashion Week Street Style Moment", "category": "Fashion", "template": "Busy street, paparazzi background (blurred), wearing statement outfit, walking like runway, editorial street shot."},
    {"name": "Golden Hour Street Photos", "category": "Fashion", "template": "City street, warm golden sunlight, casting long shadows, influencer posing, sun flare, warm aesthetic."},

    # Basketball Game Scenarios
    {"name": "Courtside NBA Game Night", "category": "Sports", "template": "Courtside seats, bright arena lights, basketball court floor visible, energetic crowd background, expensive seat view."},
    {"name": "Walking Into Arena Tunnel", "category": "Sports", "template": "Concrete arena tunnel, walking confidently, security guards in background, VIP entrance vibe."},
    {"name": "Watching Warmups Courtside", "category": "Sports", "template": "Leaning on courtside railing, players warming up in background, holding drink, pre-game anticipation."},
    {"name": "Celebrating Big Play Courtside", "category": "Sports", "template": "Standing up clapping, excited expression, blurry crowd cheering, high energy sports moment."},
    {"name": "Sitting Floor Seats Confidently", "category": "Sports", "template": "Sitting leg crossed, floor seat view, court lines very close, 'seen at the game' vibe."},
    {"name": "Arena Concourse Halftime Walk", "category": "Sports", "template": "Wide arena concourse, buying snacks or walking to lounge, bright lights, bustling crowd."},
    {"name": "Post-Game Arena Exit", "category": "Sports", "template": "Walking out of arena, night time, crowd dispersing, city lights, post-event buzz."},
    {"name": "Watching Game From Luxury Suite", "category": "Sports", "template": "Glass window view of court, high angle, lounge seating, catering food, private suite luxury."},

    # REAL-LIFE GLOBAL LANDMARKS
    {"name": "Eiffel Tower Sunset Paris", "category": "Travel", "template": "Parisian balcony or Trocadero, Eiffel Tower in background, pink and orange sunset sky, romantic travel cliché."},
    {"name": "Louvre Courtyard Afternoon", "category": "Travel", "template": "Louvre glass pyramid, sunny day, beige stone architecture, touristy but chic location."},
    {"name": "Colosseum Rome Daylight", "category": "Travel", "template": "Ancient Rome Colosseum arches in background, sunny blue sky, cobblestone path, history meets fashion."},
    {"name": "Trevi Fountain Evening Stroll", "category": "Travel", "template": "Trevi Fountain lit up at night, turquoise water, crowds blurred, coin toss moment, magical evening."},
    {"name": "Big Ben London Walk", "category": "Travel", "template": "Westminster Bridge, Big Ben and Parliament in background, red bus passing, overcast London light."},
    {"name": "Tower Bridge Golden Hour", "category": "Travel", "template": "Tower Bridge structure, river Thames, warm sunset light, iconic London landmark."},
    {"name": "Times Square Night Lights", "category": "Travel", "template": "Neon billboards everywhere, bright chaotic lights, yellow taxis blurred, NYC energy, night shot."},
    {"name": "Brooklyn Bridge Morning Walk", "category": "Travel", "template": "Wooden walkway of Brooklyn Bridge, cables leading up, Manhattan skyline in distance, morning mist."},
    {"name": "Hollywood Hills Overlook", "category": "Travel", "template": "Hiking trail or overlook, Hollywood sign distant, LA basin view, sunny hazy California vibe."},
    {"name": "Santa Monica Pier Sunset", "category": "Travel", "template": "Ferris wheel funfair background, beach sand, purple sunset, pier pilings, west coast vibe."},
    {"name": "Burj Khalifa Observation Deck", "category": "Travel", "template": "Glass floor observation deck, incredibly high view of Dubai, futuristic skyline, luxury travel."},
    {"name": "Dubai Mall Luxury Stroll", "category": "Travel", "template": "Massive aquarium or waterfall background, polished expansive mall, luxury brands, Dubai wealth."},
    {"name": "Santorini Cliffside View", "category": "Travel", "template": "White buildings with blue domes, Aegean sea below, bright harsh white sunlight, greek island aesthetic."},
    {"name": "Mykonos Seaside Walk", "category": "Travel", "template": "Windmills in background, white stone path, ocean spray, windy island vibe, chic summer outfit."},
    {"name": "Tokyo Shibuya Crossing", "category": "Travel", "template": "Massive crosswalk, neon signs, thousands of people (blurred), rain or night, cyberpunk city energy."},
    {"name": "Kyoto Temple Pathway", "category": "Travel", "template": "Red Torii gates tunnel or bamboo forest, green dappled light, peaceful spiritual path, japan travel."},
    {"name": "Bali Jungle Resort", "category": "Travel", "template": "Lush green jungle, infinity pool, wooden architecture, rice terraces, tropical zen paradise."},
    {"name": "Tulum Beach Ruins", "category": "Travel", "template": "Mayan ruins on cliff, white sand beach below, turquoise caribbean sea, boho chic vibe."},
    {"name": "Rio de Janeiro Overlook", "category": "Travel", "template": "Sugarloaf mountain view, ocean bay, green mountains, sunny vibrant Brazil weather."},
    {"name": "Cape Town Table Mountain View", "category": "Travel", "template": "Table Mountain flat top background, blue sky, waterfront or beach foreground, scenic nature."}
]

# 2. Load Existing Database
db_path = "world_db.json"
with open(db_path, "r") as f:
    db = json.load(f)

current_scenarios = db.get("scenarios", {})

# 3. Merge Scenarios
count = 0
for item in new_scenarios_list:
    # Generate a key from name (snake_case)
    key = item["name"].lower().replace(" ", "_").replace("-", "_").replace("'", "")
    
    # Overwrite or Add
    if key not in current_scenarios:
        count += 1
        
    current_scenarios[key] = {
        "name": item["name"],
        "template_prompt": item["template"],
        "category": item["category"]
    }

print(f"Added/Updated {count} scenarios.")
print(f"Total Scenarios: {len(current_scenarios)}")

# 4. Save Back
db["scenarios"] = current_scenarios

with open(db_path, "w") as f:
    json.dump(db, f, indent=4)

print("Database successfully updated.")
