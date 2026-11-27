"""Every news card must have its own original artwork or unique safe fallback.

The current four-story edition has bespoke illustration assets. Future approved
editions can still publish on time using deterministic, offline-safe compositions;
never silently reuse the generic clipboard four times.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

NOVEMBER_ARTWORK = {
    "uk-french-weir-swimming-2026": "uk-river-water-warning.svg",
    "mussolini-colador-2026": "spain-mussels-colander-pan.svg",
    "jp-gov-youtuber-pr-2026": "japan-policy-youtuber-pr.svg",
    "nz-cricket-collapse-2026": "nz-cricket-comeback.svg",
}


class NewsArtworkTest(unittest.TestCase):
    def test_current_edition_has_four_bespoke_verified_local_svgs(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        sw = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        for story_id, filename in NOVEMBER_ARTWORK.items():
            with self.subTest(story=story_id):
                self.assertIn(f"'{story_id}':'{filename}'", html)
                self.assertIn("assets/news/" + filename, sw)
                path = ROOT / "assets" / "news" / filename
                self.assertTrue(path.is_file(), "Missing commissioned art: " + filename)
                data = path.read_text(encoding="utf-8")
                self.assertGreater(len(data), 2500)
                self.assertNotIn("<script", data.lower())
                self.assertNotIn("<foreignobject", data.lower())
                self.assertNotIn('href="http', data.lower())
                svg = ET.fromstring(data)
                self.assertTrue(svg.tag.endswith("svg"))
                self.assertEqual(svg.attrib.get("viewBox"), "0 0 800 480")
                title = next((e.text for e in svg if e.tag.endswith("title")), "")
                self.assertGreater(len(title or ""), 10)
                # Art must actually be illustrated, not an unfilled empty file.
                shapes = sum(1 for node in svg.iter() if node.tag.rsplit("}", 1)[-1]
                             in ("path", "circle", "rect", "ellipse", "text"))
                self.assertGreaterEqual(shapes, 13)
        self.assertEqual(len(set(NOVEMBER_ARTWORK.values())), len(NOVEMBER_ARTWORK))

    def test_all_curated_artwork_names_are_unique_and_bundled(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        sw = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        section = html[html.index("const NEWS_ARTWORK="):
                       html.index("const NEWS_ART_FALLBACK=")]
        items = re.findall(r"'([^']+)':'([a-z0-9-]+\.svg)'", section)
        self.assertGreaterEqual(len(items), 10)
        self.assertEqual(len(items), len(set(x[0] for x in items)), "Duplicate story IDs")
        self.assertEqual(len(items), len(set(x[1] for x in items)), "Repeated artwork asset")
        for _, name in items:
            with self.subTest(file=name):
                self.assertTrue((ROOT / "assets" / "news" / name).is_file())
                self.assertIn("assets/news/" + name, sw)
        self.assertIn("shutil.copytree(artwork_dir,output/'assets'/'news'",
                      (ROOT / "build_site.py").read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("node"), "Node.js is required")
    def test_all_published_stories_render_distinct_art_offline(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        scripts = page[page.index("const NEWS_ARTWORK="):
                       page.index("function renderIssueGallery()")]
        current = json.loads((ROOT / "data" / "current.json").read_text(
            encoding="utf-8"))
        stories = current["stories"]
        self.assertGreaterEqual(len(stories), 1)
        js = r"""
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,
    c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
""" + scripts + "\nconst stories=" + json.dumps(stories, ensure_ascii=False) + r""";
const images=stories.map(newsArt);
if(new Set(images).size!==images.length)process.exit(11);
for(const path of images){
 if(!path.startsWith('./assets/news/')&&!path.startsWith('data:image/svg+xml;charset=utf-8,'))
  process.exit(12);
 if(path.endsWith('/category-work.svg')||path.endsWith('/category-sports.svg')
    ||path.endsWith('/category-person.svg')||path.endsWith('/category-company.svg'))
  process.exit(13);
}
// Future unmapped stories must have visibly distinct, inline, offline-safe art.
const unknown1={id:'future-1',title:'道路の工事でミス',country:'日本',label:'手違い',category:'work'};
const unknown2={id:'future-2',title:'道路の工事でミス',country:'日本',label:'手違い',category:'work'};
const generated1=newsArt(unknown1),generated2=newsArt(unknown2);
if(generated1===generated2)process.exit(14);
if(!generated1.startsWith('data:image/svg+xml;charset=utf-8,'))process.exit(15);
if(!decodeURIComponent(generated1.split(',')[1]).includes('<svg'))process.exit(16);
const unsafe=fallbackNewsArt({id:'future-unsafe',label:'<script>alert(1)</script>',country:'日本'});
// English/non-Japanese labels are replaced by a Japanese fallback. Both
// the fallback and the actual Japanese label path must resist injection.
const unsafeSvg=decodeURIComponent(unsafe.split(',')[1]);
if(unsafeSvg.includes('<script')||unsafeSvg.includes('alert(1)')||!unsafeSvg.includes('世界のまさか'))process.exit(17);
const mixed=fallbackNewsArt({id:'future-mixed',label:'失敗<script>',country:'日本'});
const mixedSvg=decodeURIComponent(mixed.split(',')[1]);
if(mixedSvg.includes('<script')||!mixedSvg.includes('失敗&lt;script&gt;'))process.exit(18);
"""
        result = subprocess.run(["node", "-e", js], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_november_edition_has_all_expected_story_ids(self):
        edition = json.loads((ROOT / "data" / "archive" /
                              "2026-11-19.json").read_text(encoding="utf-8"))
        self.assertEqual({s["id"] for s in edition["stories"]},
                         set(NOVEMBER_ARTWORK))


if __name__ == "__main__":
    unittest.main()
