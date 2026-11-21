"""Keep visual QA representative of actual Japanese mobile typography."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VisualQAConfigTests(unittest.TestCase):
    def test_public_smoke_does_not_confuse_demo_with_published_news(self):
        source=(ROOT/"tests/mobile_visual_smoke.mjs").read_text(encoding="utf-8")
        self.assertIn("edition.status!=='published'",source)
        self.assertIn("document.querySelectorAll('#issueGallery .gallery-tile').length===n",source)
        self.assertIn("document.querySelectorAll('#stories .story').length===Math.max(0,n-1)",source)
        self.assertIn("document.querySelector('#galleryHeading')?.textContent===",source)
        self.assertNotIn("!el.textContent.includes('準備中')",source)

    def test_github_chrome_has_japanese_fonts_for_real_layout_geometry(self):
        workflow = (ROOT / ".github/workflows/mobile-visual-smoke.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("google-chrome --version", workflow)
        self.assertIn("NotoSansCJKjp-Regular.otf", workflow)
        self.assertIn("raw.githubusercontent.com/notofonts/noto-cjk", workflow)
        self.assertNotIn("apt-get", workflow)
        self.assertIn("fc-list :lang=ja", workflow)
        self.assertIn("node tests/mobile_visual_smoke.mjs", workflow)


if __name__ == "__main__":
    unittest.main()
