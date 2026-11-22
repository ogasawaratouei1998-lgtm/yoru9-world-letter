#!/usr/bin/env python3
"""Restore explicitly reviewed, checksum-pinned JPEGs from research artifacts.

No approval, manifest changes, or Wikimedia requests. An expired artifact is
a cache miss; the existing build still enforces its normal image quality gate.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from build_site import photo_cache_path
from check_release_candidate import jpeg_dimensions

FIELDS = ("photoAsset", "photo", "photoPage", "author", "license",
          "licenseUrl", "country", "place")
REPO = "ogasawaratouei1998-lgtm/yoru9-world-letter"


def verified_seed(root, cache, record, stop, bundle):
    """Do not seed edited provenance, mismatched bytes or undersized images."""
    if any(record.get(k) != stop.get(k) for k in FIELDS):
        return False
    cover = stop.get("coverOnly") is True
    if record.get("cover") is not cover:
        return False
    name = record.get("file", "")
    digest = record.get("sha256", "")
    if not re.fullmatch(r"[A-Z]{2}-[012]\.jpg", name) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return False
    source = Path(bundle) / name
    try:
        if not source.is_file() or source.is_symlink() or not 3000 <= source.stat().st_size <= 2_000_000:
            return False
        data = source.read_bytes()
        if not data.startswith(b"\xff\xd8\xff") or not data.endswith(b"\xff\xd9"):
            return False
        if hashlib.sha256(data).hexdigest() != digest:
            return False
        w, h = jpeg_dimensions(source)
        if (w < 1000 or h < 540) if cover else (w < 330 or h < 200):
            return False
        target = photo_cache_path(cache, stop, cover)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(source, target)
        return True
    except (OSError, ValueError):
        return False


def restore(root, cache, download=None):
    root, cache = Path(root), Path(cache)
    registry = root / "editorial-country-photo-reviews/cache-seeds.json"
    if not registry.is_file():
        return 0
    records = json.loads(registry.read_text(encoding="utf-8"))["photos"]
    stops = {s["photoAsset"]: s for s in json.loads(
        (root / "travel-stops.json").read_text(encoding="utf-8")).values()}
    groups = {}
    for record in records:
        stop = stops.get(record["photoAsset"])
        if stop is None or any(record.get(k) != stop.get(k) for k in FIELDS):
            continue
        cover = stop.get("coverOnly") is True
        if record.get("cover") is not cover or photo_cache_path(cache, stop, cover).is_file():
            continue
        run = record.get("runId")
        if type(run) is not int or run <= 0:
            raise ValueError("Invalid reviewed artifact run")
        groups.setdefault(run, []).append((record, stop))
    if download is None:
        def download(run, dest):
            return subprocess.run(["gh", "run", "download", str(run), "--repo", REPO,
                                   "--name", "editorial-review-bundle", "--dir", str(dest)],
                                  check=True, timeout=90).returncode == 0
    restored = 0
    for run, selections in groups.items():
        with tempfile.TemporaryDirectory() as tmp:
            try:
                if not download(run, tmp):
                    continue
            except (OSError, subprocess.SubprocessError):
                print("Reviewed artifact unavailable; normal build remains required:", run)
                continue
            for record, stop in selections:
                if verified_seed(root, cache, record, stop, tmp):
                    restored += 1
                else:
                    print("Reviewed seed rejected:", record["photoAsset"])
    print("Checksum-verified reviewed photographs restored:", restored)
    return restored


if __name__ == "__main__":
    import os
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--cache", type=Path, default=Path(os.getenv("YORU9_PHOTO_CACHE_DIR", ".cache/yoru9-photos")))
    args = p.parse_args()
    restore(args.root, args.cache)
