"""Shared day-specific release contract. Never publishes or dispatches itself."""
import json
from pathlib import Path

def validate_release_input(root, payload, day, *, require_assets=False):
    """Validate the news and required reader shell, not optional tourism assets."""
    from publish_approved import validate_approved
    public=validate_approved(payload,day)
    root=Path(root)
    if require_assets and not all((root/name).is_file() for name in
                   ("index.html","world-passport.js","travel-stops.json")):
        raise ValueError("Missing release reader assets")
    # Country identity is still validated by validate_approved.
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
