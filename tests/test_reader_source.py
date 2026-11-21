"""Authoring components must generate the identical compatibility reader."""
from pathlib import Path
import shutil
import tempfile
import unittest

from reader_source import check_reader_source, render_reader, sync_reader_source, sync_country_component

ROOT = Path(__file__).resolve().parents[1]


class ReaderSourceTest(unittest.TestCase):
    def test_component_roundtrip_matches_existing_reader(self):
        check_reader_source(ROOT)
        self.assertEqual(render_reader(ROOT).encode("utf-8"), (ROOT/"index.html").read_bytes())
        from reader_asset_split import rendered_reader_assets
        self.assertEqual(rendered_reader_assets(render_reader(ROOT)),
                         rendered_reader_assets((ROOT/"index.html").read_text(encoding="utf-8")))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT/"reader_sources", self.root/"reader_sources")
        shutil.copy2(ROOT/"index.html", self.root/"index.html")

    def test_css_change_requires_explicit_regeneration(self):
        css = self.root/"reader_sources/core.css"
        css.write_bytes(css.read_bytes()+b"\n/* test source-only change */")
        with self.assertRaisesRegex(ValueError, "Reader source drift"):
            check_reader_source(self.root)
        sync_reader_source(self.root)
        check_reader_source(self.root)
        self.assertIn("test source-only change", (self.root/"index.html").read_text(encoding="utf-8"))

    def test_missing_or_duplicated_marker_fails_closed(self):
        template = self.root/"reader_sources/template.html"
        content = template.read_text(encoding="utf-8")
        template.write_text(content.replace("/* @reader-css@ */", ""), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "reader source marker"):
            render_reader(self.root)
        template.write_text(content+"/* @reader-css@ */", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "reader source marker"):
            render_reader(self.root)

    def test_country_sync_changes_only_generated_component(self):
        before = {p.name:p.read_bytes() for p in (self.root/"reader_sources").iterdir()}
        html = render_reader(self.root)
        registry = before["country-data.js"].decode("utf-8")
        changed = registry+"\n"
        updated = render_reader(self.root, country_data=changed)
        sync_country_component(self.root, updated)
        sync_reader_source(self.root)
        check_reader_source(self.root)
        self.assertEqual((self.root/"reader_sources/country-data.js").read_bytes(), changed.encode("utf-8"))
        for name in before:
            if name != "country-data.js":
                self.assertEqual((self.root/"reader_sources"/name).read_bytes(), before[name])
        self.assertNotEqual(updated, html)

    def test_country_sync_never_imports_unrelated_html_edits(self):
        html = render_reader(self.root) + "\n<!-- unauthorized direct edit -->"
        with self.assertRaisesRegex(ValueError, "outside generated country data"):
            sync_country_component(self.root, html)
        check_reader_source(self.root)


if __name__ == "__main__":
    unittest.main()
