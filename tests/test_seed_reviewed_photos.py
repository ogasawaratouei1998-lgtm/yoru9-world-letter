import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_site import photo_cache_path
from seed_reviewed_photos import verified_seed, restore


def jpeg(width=960, height=540):
    return (b"\xff\xd8\xff\xc0\x00\x11\x08" + height.to_bytes(2, "big") +
            width.to_bytes(2, "big") + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00" +
            b"x" * 4100 + b"\xff\xd9")


class ReviewedSeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cache = self.root / "cache"
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.stop = {"photoAsset": "assets/travel/hero.jpg",
                     "photo": "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/X.jpg/960px-X.jpg",
                     "photoPage": "https://commons.wikimedia.org/wiki/File:X.jpg",
                     "author": "Photographer", "license": "CC BY 4.0",
                     "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                     "country": "Test", "place": "Site"}
        self.record = dict(self.stop, runId=1, file="AA-1.jpg", cover=False,
                           sha256=hashlib.sha256(jpeg()).hexdigest())
        (self.bundle / "AA-1.jpg").write_bytes(jpeg())

    def test_exact_bytes_seed_existing_cache_identity(self):
        self.assertTrue(verified_seed(self.root, self.cache, self.record, self.stop, self.bundle))
        self.assertEqual(photo_cache_path(self.cache, self.stop, False).read_bytes(), jpeg())

    def test_bad_hash_license_and_native_cover_resolution_fail_closed(self):
        for record, stop in [
            (dict(self.record, sha256="0" * 64), self.stop),
            (self.record, dict(self.stop, author="Another author")),
            (dict(self.record, cover=True), dict(self.stop, coverOnly=True)),
            (dict(self.record, file="../AA-1.jpg"), self.stop),
        ]:
            self.assertFalse(verified_seed(self.root, self.cache, record, stop, self.bundle))
        self.assertFalse(list(self.cache.glob("*.jpg")))

    def test_unapproved_or_absent_manifest_asset_never_downloads(self):
        registry = self.root / "editorial-country-photo-reviews/cache-seeds.json"
        registry.parent.mkdir()
        registry.write_text(json.dumps({"photos": [self.record]}))
        (self.root / "travel-stops.json").write_text("{}")
        self.assertEqual(restore(self.root, self.cache, download=lambda *a: self.fail("network")), 0)
        (self.root / "travel-stops.json").write_text(json.dumps({"x": self.stop}))
        calls = []
        def fake(run, dest):
            calls.append(run)
            (Path(dest) / "AA-1.jpg").write_bytes(jpeg())
            return True
        self.assertEqual(restore(self.root, self.cache, download=fake), 1)
        self.assertEqual(calls, [1])
        self.assertEqual(restore(self.root, self.cache, download=lambda *a: self.fail("network")), 0)
