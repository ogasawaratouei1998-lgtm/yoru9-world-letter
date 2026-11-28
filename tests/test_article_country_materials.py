"""Regression: material work follows all approved article countries."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from article_country_materials import material_tasks, prepare_material_bundle
from country_content import load_country_content

ROOT=Path(__file__).resolve().parents[1]


class ArticleCountryMaterialsTests(unittest.TestCase):
    def test_approved_country_missing_topics_still_gets_work(self):
        tasks=material_tasks(ROOT,[{"country":"ES"}],"2027-01-01")
        self.assertEqual(tasks["articleCountries"],["ES"])
        row=tasks["tasks"][0]
        self.assertEqual(row["status"],"approved")
        self.assertIn("current_country_topics",row["missing"])
        self.assertTrue(row["officialTopicSources"])
        self.assertFalse(row["publicationEligible"])

    def test_pending_country_reuses_existing_drafts_and_source_leads(self):
        data=load_country_content(ROOT)["countries"]
        code=next(k for k,v in data.items()
                  if v["status"]=="pending" and v.get("portrait") and v.get("travelDrafts"))
        sites=[{"name":"Example official source","sourceUrl":"https://whc.unesco.org/en/list/1/"}]
        row=material_tasks(ROOT,[{"country":code}],"2026-11-27",
                           heritage_sites={code:sites})["tasks"][0]
        self.assertEqual(row["portraitDraft"],data[code]["portrait"])
        self.assertEqual(row["travelDrafts"],data[code]["travelDrafts"])
        self.assertEqual(row["officialHeritageSources"],sites)
        self.assertIn("country_publication_review",row["missing"])

    def test_all_target_countries_included_without_twenty_country_limit(self):
        data=load_country_content(ROOT)["countries"]
        codes=sorted(k for k,v in data.items() if v["status"]=="pending")[:25]
        previews=Mock(return_value={"publicationEligible":False})
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            result=prepare_material_bundle(ROOT,[{"country":c} for c in codes],
                         "2026-11-27",{"results":[]},out,write_previews=previews)
            self.assertEqual(result["articleCountries"],codes)
            self.assertEqual(result["countriesNeedingMaterials"],len(codes))
            self.assertTrue((out/"material-tasks.json").is_file())
            self.assertTrue((out/"material-summary.json").is_file())
        queue,_,limit=previews.call_args.args
        self.assertEqual(sorted(row["code"] for row in queue),codes)
        self.assertEqual(limit,len(codes))

    def test_article_photo_plan_matches_original_draft_order(self):
        from research_article_countries import align_article_photo_plan
        import json
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"country-content.json").write_text(json.dumps({"countries":{"MW":{"travelDrafts":[
                {"title":"Lake Malawi","sourceUrl":"https://whc.unesco.org/en/list/289"},
                {"title":"Chongoni","sourceUrl":"https://whc.unesco.org/en/list/476"}]}}}))
            plan={"countries":[{"code":"MW","officialSourceCandidates":[
                {"name":"Chongoni Rock-Art Area","sourceUrl":"https://whc.unesco.org/en/list/476/"},
                {"name":"Lake Malawi National Park","sourceUrl":"https://whc.unesco.org/en/list/289/"}],
                "slots":[{"slot":i,"origin":"unesco_inventory_candidate","searchQuery":"wrong"} for i in range(3)]}]}
            slots=align_article_photo_plan(root,plan)["countries"][0]["slots"]
            self.assertIn("/289/",slots[0]["officialSourceCandidate"])
            self.assertIn("/289/",slots[1]["officialSourceCandidate"])
            self.assertIn("/476/",slots[2]["officialSourceCandidate"])
            self.assertEqual(slots[1]["place"],"Lake Malawi")
            self.assertEqual(slots[2]["place"],"Chongoni")
            self.assertIn("Chongoni",slots[2]["alternateSearchQuery"])

    def test_duplicate_country_does_not_duplicate_work(self):
        result=material_tasks(ROOT,[{"country":"ES"},{"country":"ES"}],"2027-01-01")
        self.assertEqual(result["articleCountries"],["ES"])
        self.assertEqual(len(result["tasks"]),1)


if __name__=="__main__":
    unittest.main()
