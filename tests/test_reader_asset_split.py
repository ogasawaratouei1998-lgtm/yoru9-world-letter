"""Regression checks for the public HTML/CSS/JS split and cache safety."""
from pathlib import Path
import unittest

from reader_asset_split import rendered_reader_assets, expected_reader_assets

ROOT = Path(__file__).resolve().parents[1]


class ReaderAssetSplitTest(unittest.TestCase):
    def test_built_reader_has_separate_assets_and_keeps_demo_json(self):
        files=expected_reader_assets(ROOT)
        html=files["index.html"].decode("utf-8")
        css=files["assets/reader-core.css"].decode("utf-8")
        js=files["assets/reader-core.js"].decode("utf-8")
        country=files["assets/reader-country-data.js"].decode("utf-8")
        travel=files["assets/reader-travel.js"].decode("utf-8")
        self.assertIn('<script id="embedded-demo" type="application/json">',html)
        self.assertIn('<script src="./world-passport.js"></script>',html)
        self.assertRegex(html,r'<script src="./assets/reader-core.js\\?v=[0-9a-f]{12}"></script>')
        self.assertRegex(html,r'<script src="./assets/reader-country-data.js\\?v=[0-9a-f]{12}"></script>')
        self.assertRegex(html,r'<script src="./assets/reader-travel.js\\?v=[0-9a-f]{12}"></script>')
        self.assertLess(html.index("reader-country-data.js"),html.index("reader-travel.js"))
        self.assertLess(html.index("reader-travel.js"),html.index("reader-core.js"))
        self.assertRegex(html,r'<link rel="stylesheet" href="./assets/reader-core.css\\?v=[0-9a-f]{12}">')
        self.assertLess(html.index("world-passport.js"),html.index("reader-core.js"))
        self.assertNotIn("<script>\n'use strict';",html)
        self.assertNotIn("<style>\n",html)
        self.assertIn("function renderIssueGallery()",js)
        self.assertIn("const TODAY_COUNTRY_PHOTOS=Object.freeze(",country)
        self.assertIn("const TODAY_COUNTRY_GUIDES=Object.freeze({",country)
        self.assertNotIn("const TODAY_COUNTRY_PHOTOS=Object.freeze(",js)
        self.assertNotIn("const TODAY_COUNTRY_GUIDES=Object.freeze({",js)
        self.assertIn("function travelPostcardHtml(",travel)
        self.assertIn("function chooseTravelPhoto(",travel)
        self.assertIn("function renderTravelSlots()",travel)
        self.assertNotIn("function travelPostcardHtml(",js)
        self.assertNotIn("function chooseTravelPhoto(",js)
        self.assertIn("body.news-detail-mode",css)
        self.assertLess(len(html),len((ROOT/"index.html").read_text(encoding="utf-8"))//2)
        self.assertTrue(all(len(blob)>5000 for blob in (files["assets/reader-core.css"],files["assets/reader-core.js"])))

    def test_pwa_boot_has_automatic_recovery(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn('id="reader-boot-recovery"',html)
        self.assertIn("window.setTimeout(verify,8000)",html)
        self.assertIn("button.id='retryNewsLoad'",html)
        self.assertIn("url.searchParams.set('reader-retry'",html)
        self.assertIn("const INSTALL_SHELL = SHELL.filter(",worker)
        self.assertIn("cache.put(canonical, copy)",worker)
        self.assertIn("caches.match(canonical)",worker)

    def test_corrupt_reader_assets_fail_closed(self):
        source=(ROOT/"index.html").read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"anchors"):
            rendered_reader_assets(source.replace("<style>\n","",1))
        with self.assertRaisesRegex(ValueError,"runtime missing"):
            rendered_reader_assets(source.replace("function renderIssueGallery()","function removedGallery()",1))
        with self.assertRaisesRegex(ValueError,"Travel reader module"):
            rendered_reader_assets(source.replace("function chooseTravelPhoto(",
                                                  "function noTravelSelection(",1))
        with self.assertRaisesRegex(ValueError,"anchors"):
            rendered_reader_assets(source.replace("/* Optional 30-second journey:",
                                                  "/* malformed journey:",1))

    def test_country_registry_split_fails_when_code_is_missing(self):
        source=(ROOT/"index.html").read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"Country data anchors"):
            rendered_reader_assets(source.replace(
                "const TODAY_COUNTRY_GUIDES=Object.freeze({",
                "const REMOVED_COUNTRY_GUIDES=Object.freeze({",1))

    def test_pwa_precaches_all_extracted_files(self):
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        for path in ("assets/reader-core.css","assets/reader-core.js",
                     "assets/reader-country-data.js",
                     "assets/reader-travel.js",
                     "assets/reading-focus.css"):
            self.assertIn("'"+path+"'",worker)
        self.assertRegex(worker,r"yoru9-shell-v\d+")

    def test_release_smoke_fetches_external_code(self):
        from inspect import getsource
        from check_public_country_release import fetch_assets
        self.assertIn('"assets/reader-core.js"',getsource(fetch_assets))
        self.assertIn('"assets/reader-core.css"',getsource(fetch_assets))
        self.assertIn('"assets/reader-country-data.js"',getsource(fetch_assets))
        self.assertIn('"assets/reader-travel.js"',getsource(fetch_assets))


if __name__ == "__main__":
    unittest.main()
