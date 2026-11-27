"""
Cartoon character sheets + location plates via Atlas Cloud (Nano Banana 2).

Reads a design bible JSON (e.g. little_ty/cast.json) with a shared style, characters
and locations, builds one prompt per item, and generates images into .tmp/.

  python execution/cartoon_sheet.py --spec little_ty/cast.json --dry-run
  python execution/cartoon_sheet.py --spec little_ty/cast.json --only little_ty
  python execution/cartoon_sheet.py --spec little_ty/cast.json --kind locations
  python execution/cartoon_sheet.py --spec little_ty/cast.json --only beauty_shop --angles reverse,close

Location coverage:
  Each location renders every angle in "location_angles" (or its own "angles"). The first angle is
  the master shot; the others are drawn from it so walls, props and light match between cuts.
  --angles without the master reuses the latest saved master for that location.
  python execution/cartoon_sheet.py --spec little_ty/cast.json --only mom_neicy \
      --ref .tmp/little_ty/refs/mom_photo.jpg --style-ref .tmp/little_ty/refs/style.png

Reference images:
  --ref        photo(s) of the real person, used for likeness (face shape, features).
  --style-ref  an image used ONLY for drawing style (never copy its character).
  --anchor     an approved sheet (e.g. Little Ty) so new characters match the same style.
With any reference the reference-to-image endpoint is used; otherwise text-to-image.

Key: ATLASCLOUD_API_KEY from .env / environment. Never hardcoded.
Cost: about $0.08 per image (Atlas list price, Nov 2026). --dry-run prints the estimate.
"""

import argparse
import base64
import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import requests
from dotenv import load_dotenv

API = "https://api.atlascloud.ai/api/v1/model"
T2I = "google/nano-banana-2/text-to-image"
R2I = "google/nano-banana-2/reference-to-image-developer"
PRICE_PER_IMAGE = 0.08


def get_key():
    load_dotenv()
    key = (os.getenv("ATLASCLOUD_API_KEY") or "").strip()
    if not key:
        sys.exit("ATLASCLOUD_API_KEY is not set. Add it to .env (make one in the Atlas Cloud dashboard).")
    return key


def encode_image(path, max_dim=1280):
    """Load a local image, shrink it, and return a JPEG data URI."""
    from PIL import Image
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((max_dim, max_dim))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_prompt(spec, kind, item, refs, style_refs, anchors, plates=(), angle=None):
    """Compose the full prompt for a character sheet or a location plate (one camera angle)."""
    parts = []
    n = 1
    bindings = []
    for _ in refs:
        bindings.append(f"Image {n}: photo of the real person this character is based on. "
                        "Use it only for likeness (face shape, features, skin tone); redraw fully in the cartoon style.")
        n += 1
    for _ in anchors:
        if kind == "locations":
            bindings.append(f"Image {n}: an approved character sheet from the same show. "
                            "Match its drawing style, line weight and coloring exactly. Do not draw this character or any person.")
        else:
            bindings.append(f"Image {n}: an approved character sheet from the same show. "
                            "Match its drawing style, line weight, coloring and proportions exactly. Do not copy that character.")
        n += 1
    for _ in plates:
        bindings.append(f"Image {n}: the master shot of this SAME location. Keep the place identical: same walls and colors, "
                        "same furniture and props in the same places, same lighting and time of day. Use it ONLY to match the look of the place; "
                        "do not copy its framing. Follow the CAMERA line for where the camera stands and which way it faces.")
        n += 1
    for _ in style_refs:
        bindings.append(f"Image {n}: STYLE REFERENCE ONLY. Copy the drawing technique (outlines, flat cel shading, palette). "
                        "Do not copy that character's face, body, hair, clothes or pose.")
        n += 1
    if bindings:
        parts.append("REFERENCE IMAGES:\n" + "\n".join(bindings))

    parts.append("ART STYLE: " + spec["style"])
    parts.append("SETTING ERA: " + spec.get("era", ""))
    if kind == "characters":
        parts.append(f"CHARACTER: {item['name']}. {item['design']}")
        parts.append("EXPRESSION HEADS (bottom row): " + item.get("expressions", ""))
        parts.append("LAYOUT: " + spec["sheet_layout"])
    else:
        parts.append(f"LOCATION: {item['name']}. {item['design']}")
        if angle:
            parts.append("CAMERA: " + angle["camera"].format(focus=item.get("focus", "the main area of the space"),
                                                   reverse_view=item.get("reverse_view", "the side of the space that was behind the master camera")))
        parts.append("LAYOUT: " + spec["location_layout"])
    return "\n\n".join(p for p in parts if p.strip())


def submit(key, prompt, images, aspect, resolution):
    if images:
        payload = {"model": R2I, "prompt": prompt, "images": images, "aspect_ratio": aspect,
                   "resolution": resolution, "thinking_level": "default",
                   "enable_sync_mode": False, "enable_base64_output": False, "enable_web_search": False}
    else:
        payload = {"model": T2I, "prompt": prompt, "aspect_ratio": aspect, "resolution": resolution,
                   "enable_sync_mode": False, "enable_base64_output": False}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    for attempt in range(3):
        r = requests.post(f"{API}/generateImage", headers=headers, json=payload, timeout=90)
        if r.status_code == 200:
            return r.json()["data"]["id"]
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(4 * (attempt + 1))
            continue
        break
    raise RuntimeError(f"Atlas submit failed: HTTP {r.status_code} {r.text[:300]}")


def wait_for(key, pred_id, timeout_s=300):
    headers = {"Authorization": f"Bearer {key}"}
    start = time.time()
    while time.time() - start < timeout_s:
        time.sleep(3)
        r = requests.get(f"{API}/prediction/{pred_id}", headers=headers, timeout=60)
        if r.status_code != 200:
            continue
        data = r.json().get("data", {})
        status = data.get("status")
        if status in ("completed", "succeeded"):
            outs = data.get("outputs") or []
            if not outs:
                raise RuntimeError("Atlas returned success with no outputs")
            return outs[0]
        if status == "failed":
            raise RuntimeError(f"Atlas generation failed: {data.get('error')}")
    raise RuntimeError("Timed out waiting for Atlas")


def render(key, prompt, images, aspect, resolution, path):
    """Generate one image, save it plus its prompt, return the path."""
    url = wait_for(key, submit(key, prompt, images, aspect, resolution))
    img = requests.get(url, timeout=120)
    img.raise_for_status()
    with open(path, "wb") as f:
        f.write(img.content)
    with open(path.rsplit(".", 1)[0] + ".prompt.txt", "w") as f:
        f.write(prompt)
    return path


def latest_master(out_dir, item_id, master_id):
    found = sorted(glob.glob(os.path.join(out_dir, f"{item_id}_{master_id}_*_v*.png")))
    return found[-1] if found else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--kind", choices=["characters", "locations", "all"], default="all")
    ap.add_argument("--only", default="", help="comma-separated ids")
    ap.add_argument("--angles", default="", help="comma-separated location angle ids (default: all angles)")
    ap.add_argument("--ref", action="append", default=[], help="likeness photo (repeatable)")
    ap.add_argument("--style-ref", action="append", default=[], help="style-only image (repeatable)")
    ap.add_argument("--anchor", action="append", default=[], help="approved sheet to match style (repeatable)")
    ap.add_argument("--variants", type=int, default=1)
    ap.add_argument("--resolution", default="2k", choices=["1k", "2k", "4k"])
    ap.add_argument("--out", default=None, help="output dir (default .tmp/<show>/)")
    ap.add_argument("--dry-run", action="store_true", help="print prompts and cost, generate nothing")
    args = ap.parse_args()

    spec = json.load(open(args.spec))
    show_slug = spec.get("show", "show").lower().replace(" ", "_")
    out_root = args.out or os.path.join(".tmp", show_slug)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    want_angles = {s.strip() for s in args.angles.split(",") if s.strip()}

    # Each job: (kind, item, angles). Locations get coverage angles; the first angle is the
    # master shot and every other angle is drawn from it so the room stays continuous.
    jobs = []
    for kind in ("characters", "locations"):
        if args.kind not in (kind, "all"):
            continue
        for item in spec.get(kind, []):
            if only and item["id"] not in only:
                continue
            angles = (item.get("angles") or spec.get("location_angles") or []) if kind == "locations" else []
            jobs.append((kind, item, angles))
    if not jobs:
        sys.exit("Nothing matched --kind/--only.")

    def todo(angles):
        return [a for a in angles if not want_angles or a["id"] in want_angles] or [None]

    total = sum(len(todo(angles)) for _, _, angles in jobs) * args.variants
    print(f"{total} image(s) planned, about ${total * PRICE_PER_IMAGE:.2f} at ${PRICE_PER_IMAGE}/image.")

    if args.dry_run:
        for kind, item, angles in jobs:
            for angle in todo(angles):
                plates = ["master"] if angle and angle is not angles[0] else []
                print(f"\n===== {kind}: {item['id']}{' / ' + angle['id'] if angle else ''} =====")
                print(build_prompt(spec, kind, item, args.ref, args.style_ref, args.anchor, plates, angle))
        return

    key = get_key()
    images = [encode_image(p) for p in args.ref + args.anchor + args.style_ref]
    results = []
    for kind, item, angles in jobs:
        aspect = "16:9" if kind == "characters" else "9:16"
        out_dir = os.path.join(out_root, kind)
        os.makedirs(out_dir, exist_ok=True)
        stamp = int(time.time())

        if not angles:
            prompt = build_prompt(spec, kind, item, args.ref, args.style_ref, args.anchor)
            for v in range(1, args.variants + 1):
                print(f"-> {item['id']} v{v} ({'reference' if images else 'text'}-to-image, {aspect})...", flush=True)
                try:
                    path = render(key, prompt, images, aspect, args.resolution,
                                  os.path.join(out_dir, f"{item['id']}_{int(time.time())}_v{v}.png"))
                    print(f"   saved {path}")
                    results.append({"id": item["id"], "path": path})
                except Exception as e:
                    print(f"   FAILED {item['id']} v{v}: {e}")
                    results.append({"id": item["id"], "error": str(e)})
            continue

        master, rest = angles[0], [a for a in todo(angles) if a is not angles[0]]
        master_path = None
        if not want_angles or master["id"] in want_angles:
            prompt = build_prompt(spec, kind, item, args.ref, args.style_ref, args.anchor, (), master)
            for v in range(1, args.variants + 1):
                print(f"-> {item['id']} / {master['id']} v{v} (master)...", flush=True)
                try:
                    path = render(key, prompt, images, aspect, args.resolution,
                                  os.path.join(out_dir, f"{item['id']}_{master['id']}_{stamp}_v{v}.png"))
                    master_path = master_path or path
                    print(f"   saved {path}")
                    results.append({"id": item["id"], "angle": master["id"], "path": path})
                except Exception as e:
                    print(f"   FAILED {item['id']} / {master['id']} v{v}: {e}")
                    results.append({"id": item["id"], "angle": master["id"], "error": str(e)})
        else:
            master_path = latest_master(out_dir, item["id"], master["id"])
        if not rest:
            continue
        if not master_path:
            print(f"   SKIPPED {item['id']}: no {master['id']} master to draw the other angles from")
            results.append({"id": item["id"], "error": "no master plate"})
            continue

        # The remaining angles only depend on the master, so they go out together.
        plate_images = images + [encode_image(master_path)]
        with ThreadPoolExecutor(max_workers=len(rest) * args.variants) as pool:
            futures = {}
            for angle in rest:
                # Some angles (a true reverse) come out as copies of the master when it is attached,
                # so they can opt out and rely on the written description instead.
                from_master = angle.get("from_master", True)
                plates = [master_path] if from_master else []
                prompt = build_prompt(spec, kind, item, args.ref, args.style_ref, args.anchor, plates, angle)
                for v in range(1, args.variants + 1):
                    print(f"-> {item['id']} / {angle['id']} v{v} ({'from ' + os.path.basename(master_path) if from_master else 'text only'})...", flush=True)
                    path = os.path.join(out_dir, f"{item['id']}_{angle['id']}_{stamp}_v{v}.png")
                    futures[pool.submit(render, key, prompt, plate_images if from_master else images, aspect, args.resolution, path)] = (angle, v)
            for fut, (angle, v) in futures.items():
                try:
                    path = fut.result()
                    print(f"   saved {path}")
                    results.append({"id": item["id"], "angle": angle["id"], "path": path})
                except Exception as e:
                    print(f"   FAILED {item['id']} / {angle['id']} v{v}: {e}")
                    results.append({"id": item["id"], "angle": angle["id"], "error": str(e)})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
