"""Only the exact previously tested candidate can skip a duplicate build."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json
from prepared_release import seal, verify

class PreparedReleaseTest(unittest.TestCase):
    def test_changed_source_or_bundle_cannot_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"data/archive").mkdir(parents=True)
            (root/"data/current.json").write_text(json.dumps({"editionDate":"2026-11-27"}))
            (root/"index.html").write_text("source")
            site=root/"site"
            site.mkdir()
            (site/"index.html").write_text("built")
            manifest=root/"manifest.json"
            with patch("prepared_release.subprocess.check_output",return_value=b"index.html\0data/current.json\0"), patch("check_release_candidate.audit"):
                seal(root,site,manifest)
                self.assertTrue(verify(root,site,manifest))
                (root/"index.html").write_text("changed")
                with self.assertRaises(ValueError):
                    verify(root,site,manifest)
                (root/"index.html").write_text("source")
                (site/"index.html").write_text("tampered")
                with self.assertRaises(ValueError):
                    verify(root,site,manifest)
