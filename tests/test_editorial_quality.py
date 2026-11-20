"""Fail-closed checks for factual Japanese headlines and humane jokes."""
import unittest
from editorial_quality import (
    REVIEW_FIELDS, headline_fidelity_risk, independent_editorial_quality_passed,
)


class EditorialQualityTests(unittest.TestCase):
    def test_review_requires_all_independent_quality_dimensions(self):
        review={"approved":True, **{key:True for key in REVIEW_FIELDS}}
        self.assertTrue(independent_editorial_quality_passed(review))
        for key in REVIEW_FIELDS:
            with self.subTest(field=key):
                failed=dict(review)
                failed.pop(key)
                self.assertFalse(independent_editorial_quality_passed(failed))
                failed[key]=False
                self.assertFalse(independent_editorial_quality_passed(failed))
                failed[key]="true"
                self.assertFalse(independent_editorial_quality_passed(failed))
        self.assertFalse(independent_editorial_quality_passed({"approved":True}))
        review["approved"]=False
        self.assertFalse(independent_editorial_quality_passed(review))

    def test_compact_review_relies_on_specific_story_craft_without_micro_vetoes(self):
        from auto_editorial import MANZAI_CRAFT, WRITING_CRAFT
        self.assertIn("headline already tells WHO and WHAT",MANZAI_CRAFT)
        self.assertIn("Clarity veto:",WRITING_CRAFT)
        for redundant in ("firstQuipIncidentSpecific","firstQuipNotRecap",
                          "firstQuipAngleEarned","firstQuipNaturalSpeech",
                          "firstQuipFinalBeat"):
            self.assertNotIn(redundant,REVIEW_FIELDS)
        full={"approved":True, **{key:True for key in REVIEW_FIELDS}}
        self.assertTrue(independent_editorial_quality_passed(full))
        # Missing optional second-opinion micro-scores must not block factual stories.
        self.assertTrue(independent_editorial_quality_passed(
            {**full,"firstQuipAngleEarned":False,"firstQuipFinalBeat":False}))

    def test_tight_source_gate_still_requires_safe_specific_comedy(self):
        mandatory=("jokeClear","comicPunchlineWorks","humorRespectful",
                   "shockFactorConfirmed","stageTsukkomiConfirmed")
        for field in mandatory:
            self.assertIn(field,REVIEW_FIELDS)
        full={"approved":True, **{key:True for key in REVIEW_FIELDS}}
        self.assertTrue(independent_editorial_quality_passed(full))
        for field in mandatory:
            with self.subTest(field=field):
                self.assertFalse(independent_editorial_quality_passed({**full,field:False}))
                missing={k:v for k,v in full.items() if k!=field}
                self.assertFalse(independent_editorial_quality_passed(missing))

    def test_interchangeable_lazy_tsukkomi_endings_are_vetoed_early(self):
        from editorial_identity import comic_line_rejection
        for line in (
            "コーヒー4杯の注文メモがSOS欄。配達アプリ、守備範囲が広い。",
            "道路の文字が違っていた。情報量が多い。",
            "計画を立てたら予想の斜め上。",
        ):
            with self.subTest(line=line):
                self.assertEqual(comic_line_rejection(line),
                                 "stock_reaction_instead_of_punchline")
        # An original, verified object-based twist remains eligible for
        # *independent* editorial review; this check never certifies humor.
        self.assertIsNone(comic_line_rejection(
            "コーヒー4杯を頼んで、いちばん先に欲しかったのが出口。"))
        self.assertIsNone(comic_line_rejection(
            "「ゆっくり」を書き損ねて、読む人にはゆっくり読ませた。"))

    def test_second_quip_requires_three_independent_positive_verdicts(self):
        from editorial_quality import independently_approved_secondary_quip
        first="配達アプリでコーヒーを注文し、ドアを開けてもらった。"
        second="扉の鍵より先に、コーヒーの注文が救助隊を呼んだ。"
        story={"quip":first,"quipSecond":second}
        audit={"secondQuipFactsVerified":True,
               "secondQuipHasNewAngle":True,
               "secondQuipPunchlineWorks":True}
        self.assertEqual(independently_approved_secondary_quip(story,audit),second)
        for field in audit:
            with self.subTest(field=field):
                wrong={**audit,field:False}
                self.assertIsNone(independently_approved_secondary_quip(story,wrong))
                unknown={k:v for k,v in audit.items() if k!=field}
                self.assertIsNone(independently_approved_secondary_quip(story,unknown))
        self.assertIsNone(independently_approved_secondary_quip(
            {"quip":first,"quipSecond":first},audit))
        self.assertIsNone(independently_approved_secondary_quip(
            {"quip":first,"quipSecond":"世界は予想外です。"},audit))
        self.assertIsNone(independently_approved_secondary_quip(
            {"quip":first,"quipSecond":"短い"},audit))
        self.assertIsNone(independently_approved_secondary_quip(
            {"quip":first},audit))

    def test_botanical_garden_is_not_plant_nursery(self):
        story={"title":"防護柵の意味なし、アシカが植物園を占拠"}
        article=[{"text":"Sea lions entered a Dunedin plant nursery after barriers were installed."}]
        self.assertEqual(headline_fidelity_risk(story,article),
                         "plant_nursery_mistranslated")
        story["title"]="アシカが植物の育苗施設に入り込む"
        self.assertIsNone(headline_fidelity_risk(story,article))

    def test_future_charges_are_not_an_arrest_or_conviction(self):
        article=[{"text":"Two women will be charged after disrupting crow population management."}]
        story={"title":"女性2人がカラス対策を妨害し摘発された"}
        self.assertEqual(headline_fidelity_risk(story,article),
                         "future_charge_stated_as_completed_action")
        story["title"]="カラス対策を妨害した疑い、女性2人が起訴される見通し"
        self.assertIsNone(headline_fidelity_risk(story,article))

    def test_legal_intent_and_human_maternity_metaphor_do_not_become_facts(self):
        text=[{"text":"Authorities said they would charge people who moved bird traps."}]
        self.assertEqual(headline_fidelity_risk(
            {"title":"巧妙な妨害計画が発覚"},text),
            "unproven_criminal_intent_in_headline")
        self.assertEqual(headline_fidelity_risk(
            {"title":"アシカが施設を無料の産院にした"},text),
            "imaginary_facility_presented_as_fact")

    def test_empty_or_unrelated_source_is_not_approval(self):
        self.assertEqual(headline_fidelity_risk({"title":"ニュース"},[]),"missing_source_text")
        self.assertEqual(headline_fidelity_risk({"title":"ニュース"},[{"text":""}]),"missing_source_text")


if __name__=="__main__":
    unittest.main()
