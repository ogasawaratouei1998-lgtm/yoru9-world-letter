"""End-to-end fail-closed checks of every edition's reader experience."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest

from check_release_candidate import audit,jpeg_dimensions

ROOT=Path(__file__).resolve().parents[1]


class FullReaderReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for filename in ("index.html","world-passport.js","service-worker.js",
                         "travel-stops.json"):
            shutil.copy2(ROOT/filename,self.root/filename)
        current=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        self.expected_stories=len(current["stories"])
        from country_codes import country_codes
        self.expected_countries=len({code for story in current["stories"]
                                     for code in country_codes(story["country"])})
        for filename in ("data/current.json","data/archive/index.json",
                         "data/archive/"+current["editionDate"]+".json"):
            path=self.root/filename
            path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/filename,path)
        shutil.copytree(ROOT/"assets/news",self.root/"assets/news")

    def test_current_published_issue_and_every_travel_story_pass(self):
        result=audit(self.root)
        self.assertEqual(result["stories"],self.expected_stories)
        self.assertEqual(result["countries"],self.expected_countries)
        self.assertGreaterEqual(result["touristRecords"],34)
        self.assertFalse(result["buildPhotosChecked"])

    def test_latest_and_archived_issue_must_be_identical(self):
        current=self.root/"data/current.json"
        doc=json.loads(current.read_text(encoding="utf-8"))
        doc["stories"][0]["title"]="unexpected headline"
        current.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"アーカイブ"):
            audit(self.root)

    def test_post_nov20_issue_can_publish_three_verified_stories(self):
        doc=json.loads((self.root/"data/current.json").read_text(encoding="utf-8"))
        test_day="2026-11-24"
        doc["editionDate"]=test_day
        doc["stories"]=doc["stories"][:3]
        while len(doc["stories"])<3:
            duplicate=dict(doc["stories"][0])
            duplicate["id"]="synthetic-audit-"+str(len(doc["stories"]))
            doc["stories"].append(duplicate)
        for name in ("data/current.json","data/archive/"+test_day+".json"):
            target=self.root/name
            target.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
        index=self.root/"data/archive/index.json"
        data=json.loads(index.read_text(encoding="utf-8"))
        data["issues"].append({"date":test_day,"title":"test"})
        index.write_text(json.dumps(data),encoding="utf-8")
        self.assertEqual(audit(self.root)["stories"],3)

    def test_retired_stamp_book_must_not_reappear(self):
        page=self.root/"index.html"
        page.write_text(page.read_text(encoding="utf-8")+
                        '<div id="todayPassportBoard"></div>',encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"スタンプ帳"):
            audit(self.root)

    def test_short_travel_prose_is_not_permitted(self):
        path=self.root/"travel-stops.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        item=next(v for v in data.values() if not v.get("coverOnly") and not v.get("quizOnly"))
        item["travelStory"]=["素敵な場所です。"]
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"詳しい2段落"):
            audit(self.root)

    def test_fabricated_jpeg_dimensions_fail(self):
        path=self.root/"fake.jpg"
        path.write_bytes(b"not a real jpeg")
        with self.assertRaises(ValueError):
            jpeg_dimensions(path)

    def test_jpeg_dimensions_use_native_pixel_count(self):
        path=self.root/"synthetic.jpg"
        # SOF0: precision 8, height 600, width 1200, three channels.
        path.write_bytes(b"\xff\xd8\xff\xc0\x00\x11\x08\x02\x58\x04\xb0\x03"+
                         b"\x01\x11\x00\x02\x11\x00\x03\x11\x00\xff\xd9")
        self.assertEqual(jpeg_dimensions(path),(1200,600))

    def test_publication_workflow_preflights_before_committing_changes(self):
        workflow=(ROOT/".github/workflows/publish-nightly.yml").read_text(encoding="utf-8")
        preflight=workflow.index("- name: Preflight full reader and photo bundle before any release commit")
        commit=workflow.index("- name: Commit the released edition")
        self.assertLess(preflight,commit)
        self.assertIn("python check_release_candidate.py --site _site",workflow)
        self.assertIn("python build_site.py",workflow)
        self.assertIn("bash run_mobile_preflight.sh",workflow)
        preview=(ROOT/".github/workflows/test-publishing.yml").read_text(encoding="utf-8")
        self.assertIn("bash run_mobile_preflight.sh",preview)
        assert "READER_SITE_URL=http://127.0.0.1:8765/" in (
            ROOT/"run_mobile_preflight.sh").read_text(encoding="utf-8")
        deploy=(ROOT/".github/workflows/deploy-site.yml").read_text(encoding="utf-8")
        self.assertIn("python check_release_candidate.py --site _site",deploy)
        self.assertLess(deploy.index("python check_release_candidate.py --site _site"),
                        deploy.index("uses: actions/deploy-pages@v4"))

    def test_committed_nightly_issue_can_recover_failed_public_deployment(self):
        workflow=(ROOT/".github/workflows/publish-nightly.yml").read_text(encoding="utf-8")
        preflight=workflow.index("id: preflight")
        commit=workflow.index("id: release",preflight)
        recover=workflow[preflight:commit]
        self.assertIn('names=("data/current.json","data/archive/index.json")',recover)
        self.assertIn('Recover committed but not deployed current-day edition.',recover)
        self.assertIn('echo "deploy=true" >> "$GITHUB_OUTPUT"',recover)
        deploy=workflow[commit:]
        self.assertIn("steps.preflight.outputs.deploy == 'true'",deploy)
        self.assertIn("id: deployed_reader_retry",deploy)
        self.assertLess(deploy.index("python check_public_country_release.py"),
                        deploy.index("python send_release_notice.py"))
        self.assertIn("nightly-editorial-funnel-diagnostics",workflow)


if __name__=="__main__":
    unittest.main()
