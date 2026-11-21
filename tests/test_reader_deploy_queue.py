"""Queued country-reader deployments must not be replaced by nightly news jobs.

GitHub concurrency groups allow one active and one pending run; a newer
pending run replaces the older one even with cancel-in-progress: false.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def concurrency_group(source):
    match = re.search(r"(?m)^concurrency:\s*\n\s+group:\s*([^\s#]+)", source)
    if not match:
        raise AssertionError("Missing workflow concurrency group")
    return match.group(1)


class ReaderDeployConcurrencyTests(unittest.TestCase):
    def test_nightly_publishing_cannot_evict_pending_country_deployment(self):
        deploy = (ROOT / ".github/workflows/deploy-site.yml").read_text(encoding="utf-8")
        nightly = (ROOT / ".github/workflows/publish-nightly.yml").read_text(encoding="utf-8")
        self.assertEqual(concurrency_group(deploy), "reader-pages-deploy")
        self.assertNotEqual(concurrency_group(deploy), concurrency_group(nightly))
        self.assertIn("cancel-in-progress: false", deploy)
        self.assertIn("cancel-in-progress: false", nightly)

    def test_reader_rebuild_uses_latest_main_and_checks_published_photo_assets(self):
        deploy = (ROOT / ".github/workflows/deploy-site.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", deploy)
        self.assertIn("ref: main", deploy)
        self.assertIn("python -m unittest discover -s tests -v", deploy)
        self.assertIn("python build_site.py", deploy)
        self.assertIn("python check_release_candidate.py --site _site", deploy)
        self.assertIn("python check_public_country_release.py --site", deploy)


if __name__ == "__main__":
    unittest.main()
