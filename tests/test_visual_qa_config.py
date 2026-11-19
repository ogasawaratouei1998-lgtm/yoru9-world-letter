"""Keep visual QA representative of actual Japanese mobile typography."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VisualQAConfigTests(unittest.TestCase):
    def test_github_chrome_has_japanese_fonts_for_real_layout_geometry(self):
        workflow = (ROOT / ".github/workflows/mobile-visual-smoke.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("google-chrome --version", workflow)
        self.assertIn("fonts-noto-cjk", workflow)
        self.assertNotIn("apt-get update -qq", workflow)
        self.assertIn("fc-list :lang=ja", workflow)
        self.assertIn("node tests/mobile_visual_smoke.mjs", workflow)


if __name__ == "__main__":
    unittest.main()
