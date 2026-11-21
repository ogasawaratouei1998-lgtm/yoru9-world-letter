"""Source-verified news must never ship with a foreign photo or generic country stub."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from country_readiness import (ready_country_codes, select_ready_stories,
                               prioritize_ready_drafts, story_has_prepared_countries)
from auto_editorial import save_editorial_funnel

ROOT=Path(__file__).resolve().parents[1]


class CountryReadinessTest(unittest.TestCase):
    def test_current_real_countries_are_eligible_but_unprepared_world_locations_are_not(self):
        ready,incomplete=ready_country_codes(ROOT)
        self.assertTrue({"IT","DE","US","FR","AR","JP","GB","ES"}.issubset(ready))
        self.assertNotIn("NG",ready)
        self.assertIn("ES",ready,
                      "Reviewed Spanish destination assets must be eligible")
        self.assertNotIn("NZ",ready,
                         "Prepared source photos never constitute editorial approval")
        self.assertTrue(set(incomplete).isdisjoint(ready))
        articles=[
            {"id":"a","country":"イタリア"},
            {"id":"b","country":"Nigeria"},
            {"id":"c","country":"アメリカ合衆国"},
            {"id":"d","country":"ドイツ"},
            {"id":"e","country":"イタリア・ナイジェリア"},
            {"id":"f","country":"架空の国"},
        ]
        eligible,blocked,prepared,_=select_ready_stories(articles,ROOT)
        self.assertEqual([s["id"] for s in eligible],["a","c","d"])
        self.assertEqual(blocked["NG"],2)
        self.assertEqual(blocked["unrecognized"],1)
        self.assertEqual(prepared,ready)
        self.assertEqual(articles[1]["country"],"Nigeria",
                         "An unready story must not be reassigned to another country")

    def test_unverified_drafts_are_only_reordered_not_promoted(self):
        drafts=[
            {"id":"a","country":"Nigeria"},
            {"id":"b","country":"ドイツ"},
            {"id":"c","country":"Italy"},
            {"id":"d","country":"イタリア・ナイジェリア"},
            {"id":"e","country":"US"},
            {"id":"f","country":"不明な国"},
        ]
        snapshot=json.dumps(drafts,ensure_ascii=False,sort_keys=True)
        ordered=prioritize_ready_drafts(drafts,{"DE","IT","US"})
        self.assertEqual([s["id"] for s in ordered],["b","c","e","a","d","f"])
        self.assertEqual(json.dumps(drafts,ensure_ascii=False,sort_keys=True),snapshot)
        self.assertFalse(story_has_prepared_countries(drafts[0],{"IT","DE"}))
        self.assertFalse(story_has_prepared_countries(drafts[3],{"IT"}))
        self.assertTrue(story_has_prepared_countries(drafts[1],{"DE"}))
        # This merely schedules independent article verification; a draft
        # has no editorVerified flag and no approval/publishing side effects.
        self.assertTrue(all("editorVerified" not in s for s in ordered))

    def test_refill_gate_counts_ready_verified_stories_not_all_reviewed(self):
        verified=[{"country":"Nigeria"},{"country":"US"},
                  {"country":"ドイツ"},{"country":"Unknown"}]
        self.assertEqual(sum(story_has_prepared_countries(s,{"US","DE","IT"})
                             for s in verified),2)
        pipeline=(ROOT/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertEqual(pipeline.count(
            "if ready_reviewed_count()>=4 or AI_QUOTA_BLOCKED"),2)
        self.assertIn("if len(selected)>=9:break",pipeline,
                      "Review budget remains bounded by existing quota guard")

    def test_bad_license_blocks_that_country_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ("index.html","world-passport.js","travel-stops.json"):
                shutil.copyfile(ROOT/name,root/name)
            manifest=root/"travel-stops.json"
            data=json.loads(manifest.read_text(encoding="utf-8"))
            data["italy-pisa-tower-postcard"]["licenseUrl"]="https://example.com/fake"
            manifest.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
            ready,incomplete=ready_country_codes(root)
            self.assertNotIn("IT",ready)
            self.assertIn("IT",incomplete)
            self.assertIn("DE",ready)
            self.assertIn("US",ready)

    def test_readiness_metadata_only_never_contains_unverified_source_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"funnel.json"
            saved=save_editorial_funnel("country_readiness",{
                "independent_approved":6,
                "country_ready_articles":4,
                "country_ready_count":8,
                "unready_country_codes":{"NG":2},
                "privateArticleTitle":"MUST NOT LEAK",
                "rejection_reasons":{"unprepared_country":2},
            },path=output)
            self.assertEqual(saved["unready_country_codes"],{"NG":2})
            self.assertEqual(saved["country_ready_articles"],4)
            self.assertNotIn("privateArticleTitle",output.read_text())

    def test_four_story_failure_diagnostic_stage_is_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            saved=save_editorial_funnel("four_story_gate",{
                "independent_approved":6,
                "country_ready_articles":3,
                "unready_country_codes":{"TW":3},
            },path=Path(temp)/"funnel.json")
            self.assertEqual(saved["phase"],"four_story_gate")
            self.assertEqual(saved["unready_country_codes"],{"TW":3})

    def test_free_svg_approval_never_assigns_paid_webp_image_path(self):
        code=(ROOT/"auto_editorial.py").read_text(encoding="utf-8")
        main=code.split("def main():",1)[-1]
        self.assertIn("select_ready_stories(selected,Path.cwd())",main)
        self.assertIn('checkpoint("four_story_gate"',main)
        self.assertNotIn("prepare_news_images",main)
        self.assertNotIn("expected_path(day,story)",main)
        self.assertNotIn("story['imagePath']=",main)
        self.assertIn("validate_approved(payload,day)",main)


if __name__=="__main__":
    unittest.main()
