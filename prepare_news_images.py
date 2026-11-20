#!/usr/bin/env python3
"""Generate real photorealistic editorial concept art for each new verified article.

This is an illustration, NEVER a news photograph or evidence of the incident.
Never invent missing news stories or publish without all four images present.
Gemini image generation may require paid image-model quota; fail closed if absent.
"""
import base64
from datetime import datetime
import io
import json
import os
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from time import sleep
from zoneinfo import ZoneInfo

MIN_PUBLISH_DATE="2026-11-20"
IMAGE_MODEL=os.getenv("GEMINI_IMAGE_MODEL","gemini-3.1-flash-lite-image")
IMAGE_DIR="assets/news-generated"
IMAGE_RE=re.compile(r"assets/news-generated/(\d{4}-\d{2}-\d{2})/([a-z0-9][a-z0-9-]{2,90})\.webp\Z")
MAX_IMAGE_BYTES=2_500_000

def expected_path(day,story):
    slug=story["id"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,90}",slug):
        raise ValueError("Unsafe story id for image file")
    return f"{IMAGE_DIR}/{day}/{slug}.webp"

def visual_prompt(story):
    # No literal photo reconstruction, private faces, third-party logos,
    # identifying uniforms or text that may falsely assert what happened.
    title=str(story.get("title",""))[:180]
    summary=str(story.get("summary",""))[:430]
    return (
      "Create ONE photorealistic editorial conceptual illustration, cinematic "
      "documentary-grade photographic lighting and real camera optics, horizontal 16:9. "
      "This is a FICTIONAL depiction inspired by a VERIFIED news summary, NOT "
      "a photograph of an actual event, NOT a recreation of actual people's faces. "
      "Use generic anonymous adult characters if needed (do not show real victims "
      "or identifiable minors), accurate everyday objects and plausible environments. "
      "Show the surprising PLAN versus RESULT contrast in an instantly comprehensible "
      "single frame, visually engaging but without cruelty, gore, emergency spectacle, "
      "shaming, fake police evidence, real logos, branding, celebrities, labels, "
      "numbers, prices, news watermarks, captions or ANY words inside the image. "
      "Avoid showing an AI-fabricated item as a real physical event: if the report "
      "concerns a fake image or rumor, show it clearly contained ON a phone screen, "
      "with the actual environment separate. The original article's facts must NOT "
      "be embellished by invented actions or consequences. "
      "News headline for concept: "+title+"; verified summary: "+summary
    )

def extract_image_bytes(response):
    # Interactions API represents model output as content blocks in steps.
    options=[]
    image=response.get("output_image")
    if isinstance(image,dict):options.append(image)
    for step in response.get("steps",[]):
        if not isinstance(step,dict) or step.get("type")!="model_output":continue
        for part in step.get("content",[]):
            if isinstance(part,dict) and part.get("type")=="image":options.append(part)
    for item in reversed(options):
        encoded=item.get("data")
        if not isinstance(encoded,str) or len(encoded)>12_000_000:continue
        if item.get("mime_type",item.get("mimeType","image/jpeg")) not in ("image/png","image/jpeg","image/webp"):continue
        try:
            raw=base64.b64decode(encoded,validate=True)
        except (ValueError,base64.binascii.Error):
            continue
        if 20_000<=len(raw)<=9_000_000 and (
            raw[:3]==b"\xff\xd8\xff" or raw[:8]==b"\x89PNG\r\n\x1a\n" or
            (raw[:4]==b"RIFF" and raw[8:12]==b"WEBP")
        ):
            return raw
    raise ValueError("Image API returned no valid image output")

def gemini_image(prompt,key,model=IMAGE_MODEL):
    if not key:raise RuntimeError("GEMINI_IMAGE_API_KEY/GEMINI_API_KEY is not configured")
    if not re.fullmatch(r"gemini-[a-z0-9.-]+-image",model):
        raise ValueError("Unsupported image model name")
    payload={"model":model,"input":[{"type":"text","text":prompt}],
             "response_format":{"type":"image","mime_type":"image/jpeg",
                                "aspect_ratio":"16:9","image_size":"1K"}}
    req=Request("https://generativelanguage.googleapis.com/v1beta/interactions",
                json.dumps(payload,ensure_ascii=False).encode("utf-8"),
                headers={"x-goog-api-key":key,"Content-Type":"application/json"},
                method="POST")
    # A 429 can mean either a brief rate limit or an image model with ZERO
    # granted requests (often a free-tier key). Repeatedly hammering an
    # unavailable paid model cannot create an image; protect quotas and the
    # existing published edition. Never log credentials or raw API responses.
    for attempt in range(3):
        try:
            with urlopen(req,timeout=110) as response:
                result=json.load(response)
            return extract_image_bytes(result)
        except HTTPError as exc:
            if exc.code!=429:
                raise RuntimeError(f"Image API HTTP {exc.code}; previous issue preserved") from exc
            try:
                payload=json.loads(exc.read(8000))
                problem=payload.get("error",{})
                message=str(problem.get("message","")).lower()
                details=str(problem.get("details",[])).lower()
            except (ValueError,UnicodeDecodeError,TypeError,AttributeError):
                message=details=""
            if any(term in message+" "+details for term in
                   ("free_tier_requests","freetier","free tier","limit: 0","limit=0",
                    "quota limit 0")):
                raise RuntimeError(
                    "Image quota is zero (possibly free tier). Check the Gemini "
                    "API project's paid-tier entitlement, billing, and AI Studio "
                    "rate limits; no edition was published.") from None
            if attempt==2:
                raise RuntimeError(
                    "Image API 429 persisted after bounded retries; check paid "
                    "quota and rate limits; previous edition preserved.") from None
            sleep((2,6)[attempt])
    raise RuntimeError("Image generation did not complete")

def encode_webp(raw,path):
    from PIL import Image,ImageOps
    with Image.open(io.BytesIO(raw)) as source:
        source.load()
        if source.width<640 or source.height<360:
            raise ValueError("Generated image too small")
        if source.width/source.height<1.3 or source.width/source.height>2.2:
            raise ValueError("Generated image has wrong aspect ratio")
        frame=ImageOps.fit(source.convert("RGB"),(1200,675),method=Image.Resampling.LANCZOS)
        buffer=io.BytesIO()
        frame.save(buffer,"WEBP",quality=82,method=5)
    data=buffer.getvalue()
    if not (20_000<=len(data)<=MAX_IMAGE_BYTES and data[:4]==b"RIFF" and data[8:12]==b"WEBP"):
        raise ValueError("Generated WebP failed verification")
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp")
    temp.write_bytes(data)
    temp.replace(path)

def valid_webp(path):
    if not path.is_file() or not (20_000<=path.stat().st_size<=MAX_IMAGE_BYTES):
        return False
    with path.open("rb") as f:header=f.read(12)
    return header[:4]==b"RIFF" and header[8:12]==b"WEBP"

def prepare(root,day,key=None,render=None):
    if day<MIN_PUBLISH_DATE:return 0
    root=Path(root)
    approved_path=root/"data/approved"/(day+".json")
    if not approved_path.is_file():return 0
    doc=json.loads(approved_path.read_text(encoding="utf-8"))
    if doc.get("editionType","regular")!="regular":return 0
    # Nov 20 historical drafts remain unchanged; only the explicitly requested
    # four-story photorealistic reissue is eligible for new image generation.
    if day=="2026-11-20" and doc.get("editionRequiresImages") is not True:return 0
    from publish_approved import validate_approved
    # A public image does NOT compensate for insufficient verified reporting.
    if not isinstance(doc.get("stories"),list):
        raise ValueError("Approved stories must be a list")
    if not (4<=len(doc.get("stories",[]))<=5):
        raise ValueError("Four source-checked articles required before image generation")
    validate_approved(doc,day)
    generate=render or gemini_image
    secrets=key if key is not None else (
        os.getenv("GEMINI_IMAGE_API_KEY") or os.getenv("GEMINI_API_KEY",""))
    if not secrets and any(not valid_webp(root/expected_path(day,s)) for s in doc["stories"]):
        raise RuntimeError("Image generation key unavailable: preserve previous issue")
    for story in doc["stories"]:
        path=root/expected_path(day,story)
        if story.get("imagePath")!=expected_path(day,story):
            raise ValueError("Image path does not match verified story id")
        if valid_webp(path):continue
        raw=generate(visual_prompt(story),secrets)
        encode_webp(raw,path)
        print("Completed image:",path.name,flush=True)
    if not all(valid_webp(root/expected_path(day,s)) for s in doc["stories"]):
        raise ValueError("Images incomplete; preserve previous edition")
    return len(doc["stories"])

def rotate_old_generated_images(root,day):
    """Called only AFTER a successful actual public release, not during drafts."""
    root=Path(root)
    current=root/"data/current.json"
    if not current.is_file():return 0
    doc=json.loads(current.read_text(encoding="utf-8"))
    if day<MIN_PUBLISH_DATE or doc.get("editionDate")!=day:return 0
    if doc.get("editionType")!="regular" or len(doc.get("stories",[]))<4:return 0
    keep={expected_path(day,s) for s in doc["stories"]}
    if not all(s.get("imagePath")==expected_path(day,s) and
               valid_webp(root/expected_path(day,s)) for s in doc["stories"]):
        raise ValueError("Cannot remove previous images before new issue is complete")
    parent=root/IMAGE_DIR
    if not parent.is_dir():return 0
    removed=0
    for child in parent.iterdir():
        if not child.is_dir() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",child.name):continue
        for image in child.glob("*.webp"):
            relative=image.relative_to(root).as_posix()
            if relative not in keep:
                image.unlink()
                removed+=1
        if not any(child.iterdir()):child.rmdir()
    return removed

if __name__=="__main__":
    root=Path(__file__).resolve().parent
    day=datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    if len(sys.argv)>1 and sys.argv[1]=="--rotate":
        print("Removed obsolete generated images:",rotate_old_generated_images(root,day))
    else:
        print("Prepared generated story images:",prepare(root,day))
