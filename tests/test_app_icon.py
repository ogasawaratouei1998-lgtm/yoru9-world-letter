"""Home-screen icon and concise nightly reader design safety checks."""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from app_icon import icon_png, render_icons

ROOT = Path(__file__).resolve().parents[1]


class AppIconTest(unittest.TestCase):
    def test_icons_are_valid_png_with_correct_dimensions(self):
        for size in (180, 192, 512):
            with self.subTest(size=size):
                content = icon_png(size)
                self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual(struct.unpack(">II", content[16:24]), (size, size))
                self.assertTrue(content.endswith(b"IEND\xaeB\x60\x82"))
                self.assertLess(len(content), 350_000)

    def test_generated_icons_match_site_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            render_icons(directory)
            icons = {p.name for p in Path(directory).glob("*.png")}
            self.assertEqual(icons, {
                "apple-touch-icon.png", "icon-192.png", "icon-512.png"
            })
        manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
        sources = {item["src"] for item in manifest["icons"]}
        self.assertIn("./assets/icon-192.png", sources)
        self.assertIn("./assets/icon-512.png", sources)
        self.assertIn("./assets/icon.svg", sources)

    def test_home_screen_links_and_semantic_brand_are_present(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('rel="apple-touch-icon"', html)
        self.assertIn('href="./assets/apple-touch-icon.png"', html)
        self.assertIn('class="logo-mark"', html)
        self.assertIn('class="skip-link"', html)
        self.assertIn("controls.hidden=edition.stories.length<=3||available.size<=1", html)
        self.assertIn('id="spotlightRead"', html)
        self.assertNotIn('id="worldInvitation"', html)

    def test_icons_do_not_require_external_fonts_or_network_services(self):
        code = (ROOT / "app_icon.py").read_text(encoding="utf-8")
        for forbidden in ("requests", "urllib", "cairosvg", "PIL", "urlopen"):
            self.assertNotIn("import " + forbidden, code)
        svg = (ROOT / "assets/icon.svg").read_text(encoding="utf-8")
        self.assertIn("月と手紙", svg)
        self.assertIn('viewBox="0 0 512 512"', svg)
        self.assertNotIn("<image ", svg)


if __name__ == "__main__":
    unittest.main()
