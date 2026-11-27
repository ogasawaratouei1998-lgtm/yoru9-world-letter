"""Shared day-specific release contract. Never publishes or dispatches itself."""
import json
from pathlib import Path

def require_release_assets(root):
    from publish_approved import require
    root=Path(root)
    require(all((root/name).is_file() for name in
                ("index.html","world-passport.js","travel-stops.json")),
            "Missing release reader assets")

def validate_release_input(root, payload, day, *, require_assets=False):
    """Validate the news and required reader shell, not optional tourism assets."""
    from publish_approved import validate_approved
    public=validate_approved(payload,day)
    if require_assets:
        require_release_assets(root)
    return public

def recover_review(root, day, incoming, *, require_assets=True):
    """Preserve committed/archived issues. Choose newest valid same-day artifact."""
    root=Path(root)
    target=root/"data"/"approved"/(day+".json")
    if (root/"data"/"archive"/(day+".json")).exists():
        return "archived",0
    if target.exists():
        payload=json.loads(target.read_text(encoding="utf-8"))
        validate_release_input(root,payload,day,require_assets=require_assets)
        return "existing",len(payload["stories"])
    candidates=sorted((p for p in Path(incoming).glob("*/"+day+".json")
                       if p.parent.name.isdecimal()),
                      key=lambda p:int(p.parent.name),reverse=True)
    for candidate in candidates:
        try:
            payload=json.loads(candidate.read_text(encoding="utf-8"))
            validate_release_input(root,payload,day,require_assets=require_assets)
        except (ValueError,KeyError,TypeError,OSError,IndexError):
            print("Rejected invalid preview:",candidate.parent.name,flush=True)
            continue
        target.parent.mkdir(parents=True,exist_ok=True)
        # The caller holds the serialized publisher lock; never replace a curated file.
        with target.open("x",encoding="utf-8") as out:
            out.write(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
        print("Selected latest verified review",candidate.parent.name,flush=True)
        return "recovered",len(payload["stories"])
    return "missing",0

def approval_origin(payload):
    if not isinstance(payload,dict):return "unknown"
    return ("automated" if payload.get("approvedBy")=="automated-two-stage-review"
            else "manual" if payload.get("approvedBy") else "unknown")


def should_refill_recovered(root, day, state, count, now):
    """Extend a recovered automatic preview regardless of its article count.
    
    This is a search trigger, not a minimum publication count. Preserve the
    last preparation window for the 21:00 release and never edit curated files.
    """
    from zoneinfo import ZoneInfo
    if state != "recovered" or count < 1 or now.tzinfo is None:
        return False
    local = now.astimezone(ZoneInfo("Asia/Tokyo"))
    if local.date().isoformat() != day or local.hour >= 19:
        return False
    root = Path(root)
    if (root/"data"/"archive"/(day+".json")).exists():
        return False
    payload = json.loads((root/"data"/"approved"/(day+".json")).read_text(encoding="utf-8"))
    return (approval_origin(payload) == "automated" and
            payload.get("editionType") == "regular" and
            len(payload["stories"]) == count)


def load_refill_seed(root, day):
    """Read and revalidate the private recovered preview, never trust a count."""
    root = Path(root)
    target = root/"data"/"approved"/(day+".json")
    if (root/"data"/"archive"/(day+".json")).exists():
        raise ValueError("Cannot extend an archived issue")
    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_release_input(root, payload, day, require_assets=True)
    if (approval_origin(payload) != "automated" or
            payload.get("editionType") != "regular" or not payload["stories"]):
        raise ValueError("Only a nonempty recovered automatic regular preview can be extended")
    return payload


def save_refilled_preview(root, day, seed, payload):
    """Replace only the unchanged recovered preview, preserving every old story."""
    root = Path(root)
    target = root/"data"/"approved"/(day+".json")
    if load_refill_seed(root, day) != seed:
        raise ValueError("Recovered preview changed during refill")
    if len(payload["stories"]) <= len(seed["stories"]):
        return False
    if not all(story in payload["stories"] for story in seed["stories"]):
        raise ValueError("Refill cannot remove or rewrite approved stories")
    validate_release_input(root, payload, day, require_assets=True)
    tmp = target.with_suffix(".refill.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    tmp.replace(target)
    return True
