"""Pure reference validation; never submits a generation request."""
import hashlib
import json
import re
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def file_identity(path):
    p = Path(str(path))
    if not str(path).startswith(("http://", "https://", "data:")):
        if not p.is_file():
            raise ValueError(f"Reference file is missing: {p.name}")
        return hashlib.sha256(p.read_bytes()).hexdigest()
    return str(path)


def build_review(prompt, images, videos, audios, labels, previz=False, blocking="", duration=10):
    if not prompt.strip():
        raise ValueError("Enter the scene action and dialogue first.")
    if len(images) > 30 or len(videos) > 10 or len(audios) > 10:
        raise ValueError("Seedance 2.5 supports 30 images, 10 videos and 10 audio references. Remove extras; none will be silently dropped.")
    if not 4 <= duration <= 30:
        raise ValueError("Seedance 2.5 reference duration must be 4–30 seconds.")
    if previz and (not videos or not blocking.strip()):
        raise ValueError("Blender guidance requires a video and a description of which proxy represents each character.")
    # Old numeric tags cannot safely identify a character after the rig changes.
    if previz and re.search(r"(?<![A-Za-z0-9])@?(?:Image|Video|Audio)\d+\b", prompt, re.I):
        raise ValueError("For Blender guidance, paste only the scene/action text and use character names. Remove old Image/Video/Audio numbered tags; the current rig supplies them automatically.")
    rows = []
    for kind, paths in (("Image", images), ("Video", videos), ("Audio", audios)):
        for i, path in enumerate(paths, 1):
            tag = f"{kind}{i}"
            rows.append({"Reference": "@" + tag, "Role": labels.get(str(path), "Additional " + kind.lower()), "Asset": str(path), "identity": file_identity(path)})
    valid = {r["Reference"].lower() for r in rows}
    for tag in re.findall(r"(?<![A-Za-z0-9])@?((?:Image|Video|Audio)\d+)\b", prompt, re.I):
        if "@" + tag.lower() not in valid:
            raise ValueError(f"{tag} has no attached reference. Update the prompt or attach the asset.")
    header = "\n".join(f"{r['Reference']}: {r['Role']}" for r in rows)
    binding = "Character references define facial identity. Outfit references define clothing for their named character. Location references define the finished setting and lighting."
    if previz:
        binding += " @Video1 supplies camera trajectory, framing, timing and actor blocking only. Render the people and setting using the image references, with realistic skin, fabric and finished surfaces. Proxy-to-character assignment: " + blocking.strip()
    return rows, header + "\n" + binding + "\n\n" + prompt.strip()
