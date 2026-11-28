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

def is_automatic_extension(seed, candidate):
    """Accept only a strictly additive, independently validated automatic issue.

    Neither edition metadata nor a single approved story may be rewritten.
    Curated and special editions are not eligible.
    """
    return (approval_origin(seed) == approval_origin(candidate) == "automated"
            and seed.get("editionType") == candidate.get("editionType") == "regular"
            and {k:v for k,v in seed.items() if k!="stories"} ==
                {k:v for k,v in candidate.items() if k!="stories"}
            and len(candidate["stories"])>len(seed["stories"])
            and all(story in candidate["stories"] for story in seed["stories"]))


def recover_review(root, day, incoming, *, require_assets=True, allow_extension=False):
    """Preserve curated/archived issues; optionally accept additive automatic reviews."""
    root=Path(root)
    target=root/"data"/"approved"/(day+".json")
    if (root/"data"/"archive"/(day+".json")).exists():
        return "archived",0
    existing=None
    if target.exists():
        existing=json.loads(target.read_text(encoding="utf-8"))
        validate_release_input(root,existing,day,require_assets=require_assets)
        if (not allow_extension or approval_origin(existing)!="automated"
                or existing.get("editionType")!="regular"):
            return "existing",len(existing["stories"])
    candidates=sorted((p for p in Path(incoming).glob("*/"+day+".json")
                       if p.parent.name.isdecimal()),
                      key=lambda p:int(p.parent.name),reverse=True)
    if existing is not None:
        # Follow the monotonic history oldest-first, not the largest count.
        # A newer stale/forked artifact cannot discard an already accepted addition.
        seed=existing
        selected=None
        for candidate in reversed(candidates):
            try:
                payload=json.loads(candidate.read_text(encoding="utf-8"))
                validate_release_input(root,payload,day,require_assets=require_assets)
                if not is_automatic_extension(seed,payload):
                    continue
            except (ValueError,KeyError,TypeError,OSError,IndexError):
                print("Rejected invalid preview:",candidate.parent.name,flush=True)
                continue
            seed=payload
            selected=candidate
        if selected is None:
            return "existing",len(existing["stories"])
        # All four callers operate on isolated checkouts; only the publisher
        # can commit, under its existing lock and non-forced rebase safeguards.
        if (root/"data"/"archive"/(day+".json")).exists():
            return "archived",0
        if json.loads(target.read_text(encoding="utf-8"))!=existing:
            raise ValueError("Committed approval changed during recovery")
        tmp=target.with_suffix(".recover.tmp")
        tmp.write_text(json.dumps(seed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        tmp.replace(target)
        print("Recovered additive automatic review",selected.parent.name,
              "stories",len(existing["stories"]),"->",len(seed["stories"]),flush=True)
        return "extended",len(seed["stories"])
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
    """Extend recovered or committed automatic previews regardless of count.
    
    This is a search trigger, not a minimum publication count. Preserve the
    last preparation window for the 21:00 release and never edit curated files.
    """
    from zoneinfo import ZoneInfo
    if state not in ("recovered","existing","extended") or count < 1 or now.tzinfo is None:
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
    if not is_automatic_extension(seed,payload):
        raise ValueError("Refill cannot remove or rewrite approved stories or issue metadata")
    validate_release_input(root, payload, day, require_assets=True)
    tmp = target.with_suffix(".refill.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    tmp.replace(target)
    return True
