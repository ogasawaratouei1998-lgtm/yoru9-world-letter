import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from country_review_bundle import candidate_identity, make_queue, valid_preview_url, write_bundle

def candidate(name):
    return {"commonsPage": "https://commons.wikimedia.org/wiki/File:" + name,
            "original": "https://upload.wikimedia.org/wikipedia/commons/a/ab/" + name,
            "preview": "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/" + name + "/960px-" + name,
            "metadataChecked": True, "author": "Photographer", "license": "CC BY 4.0",
            "licenseUrl": "https://creativecommons.org/licenses/by/4.0/"}

def row(code, slot, names):
    return {"countryCode": code, "slot": slot, "origin": "existing_draft",
            "candidates": [candidate(n) for n in names]}

class ReviewBundleTests(unittest.TestCase):
    def test_distinct_assignment_and_no_approval(self):
        report = {"results": [row("AA", 0, ["A.jpg"]), row("AA", 1, ["A.jpg", "B.jpg"]),
                              row("AA", 2, ["C.jpg"]), row("BB", 0, ["B.jpg"])]}
        data = {"AA": {"name": "Draft", "status": "pending", "portrait": {"body": "Draft"}},
                "BB": {"name": "Approved", "status": "approved"}}
        queue = make_queue(report, data)
        self.assertEqual(len(queue), 1)
        self.assertTrue(queue[0]["threeDistinctCandidates"])
        self.assertFalse(queue[0]["publicationEligible"])
        self.assertEqual(candidate_identity(queue[0]["slots"][1]["candidate"]), "B.jpg")
        with tempfile.TemporaryDirectory() as tmp:
            s = write_bundle(queue, tmp, 12, fetch=lambda u: b"\xff\xd8test\xff\xd9", sleep_seconds=0)
            self.assertEqual(s["downloadedUnreviewedPreviews"], 3)
            self.assertFalse(s["publicationEligible"])
            index = json.loads((Path(tmp) / "review-index.json").read_text())
            self.assertTrue(all(not slot["visualVerified"] for slot in index["queue"][0]["slots"]))

    def test_reused_original_or_mismatched_metadata_is_not_ready(self):
        self.assertFalse(valid_preview_url("https://upload.wikimedia.org.evil.example/wikipedia/commons/a/ab/A.jpg"))
        self.assertFalse(valid_preview_url("https://upload.wikimedia.org:8080/wikipedia/commons/a/ab/A.jpg"))
        c = candidate("A.jpg")
        c["preview"] = candidate("B.jpg")["preview"]
        self.assertIsNone(candidate_identity(c))
        data = {"AA": {"name": "Draft", "status": "pending"}}
        queue = make_queue({"results": [row("AA", s, ["A.jpg"]) for s in range(3)]}, data)
        self.assertFalse(queue[0]["threeDistinctCandidates"])

    def test_throttling_preserves_unreviewed_status(self):
        data = {"AA": {"name": "Draft", "status": "pending"}}
        queue = make_queue({"results": [row("AA", i, [str(i)+".jpg"]) for i in range(3)]}, data)
        def throttle(url):
            raise HTTPError(url, 429, "Too many requests", {}, None)
        with tempfile.TemporaryDirectory() as tmp:
            s = write_bundle(queue, tmp, 12, fetch=throttle, sleep_seconds=0)
            self.assertEqual(s["downloadedUnreviewedPreviews"], 0)
            self.assertEqual(queue[0]["slots"][1]["previewStatus"], "rate_limited_deferred")
