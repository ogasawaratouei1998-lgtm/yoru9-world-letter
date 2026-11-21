"""Objective scoring metadata cannot replace the independent source audit."""
import unittest

from editorial_quality import (
    editorial_rubric, editorial_rubric_rejection, verified_rubric_for_edition,
    choose_pre_review_quip, quip_candidates_ranked,
)


class EditorialRubricTests(unittest.TestCase):
    def test_five_explicit_dimensions_and_non_compensatory_vetoes(self):
        top={"surprise":4,"mistakeClarity":5,"outcomeIrony":4,
             "evidence":5,"safety":5}
        self.assertEqual(editorial_rubric({"editorialScores":top}),top)
        self.assertIsNone(editorial_rubric_rejection({"editorialScores":top}))
        for name in ("surprise","mistakeClarity","outcomeIrony"):
            self.assertEqual(editorial_rubric_rejection(
                {"editorialScores":{**top,name:3}}),
                "story_not_extraordinary_or_specific")
        for name in ("evidence","safety"):
            self.assertEqual(editorial_rubric_rejection(
                {"editorialScores":{**top,name:4}}),
                "evidence_or_safety_below_standard")
        self.assertEqual(editorial_rubric_rejection(
            {"editorialScores":{**top,"evidence":True}}),
            "editorial_scores_invalid")
        self.assertEqual(editorial_rubric_rejection(
            {"editorialScores":{**top,"unsafeUnknown":5}}),
            "editorial_scores_invalid")
        # Older approved editions need not invent retrospective model scores.
        self.assertIsNone(editorial_rubric_rejection({"approved":True}))

    def test_new_editions_require_all_five_review_dimensions(self):
        top={"surprise":4,"mistakeClarity":5,"outcomeIrony":4,
             "evidence":5,"safety":5}
        self.assertFalse(verified_rubric_for_edition({"approved":True},"2026-11-21"))
        self.assertTrue(verified_rubric_for_edition({"editorialScores":top},"2026-11-21"))
        self.assertFalse(verified_rubric_for_edition({"editorialScores":{**top,"safety":4}},"2026-11-21"))
        self.assertTrue(verified_rubric_for_edition({"approved":True},"2026-11-20"))

    def test_weak_recap_rejected_when_stronger_option_exists(self):
        headline="コーヒーの注文で助けを呼び、扉が開く"
        good="コーヒー4杯を頼んで、いちばん先に欲しかったのが出口。"
        story={"title":headline,"summary":"扉を開けてほしくて宅配を依頼した。",
               "quip":headline,"quipCandidates":[headline,good]}
        self.assertEqual(choose_pre_review_quip(story),good)
        self.assertEqual(quip_candidates_ranked(story),[good])
        # No model candidate is a verified fact; reviewer B must still audit.
        self.assertNotIn("editorVerified",story)

    def test_pipeline_cannot_use_a_headline_echo_when_every_quip_fails(self):
        import inspect
        import auto_editorial
        echo="荷物を送り間違え、受取先も書き間違えた"
        self.assertIsNone(choose_pre_review_quip(
            {"title":echo,"summary":echo+"。","quip":echo,
             "quipCandidates":[echo]}))
        source=inspect.getsource(auto_editorial.main)
        self.assertIn('reject("quip_without_original_angle");continue',source)
        self.assertIn('story["quip"]=selected_quip',source)

    def test_every_refill_gets_same_three_way_quip_selection(self):
        # Normal and post-review refills used to ask for just one first joke.
        # The existing selector must receive alternatives without another
        # paid model call or any relaxation of independent fact review.
        import inspect
        from auto_editorial import main, QUIP_ALTERNATIVE_REQUIREMENT
        source=inspect.getsource(main)
        self.assertEqual(source.count("QUIP_ALTERNATIVE_REQUIREMENT"),2)
        self.assertIn("quipCandidates",QUIP_ALTERNATIVE_REQUIREMENT)
        self.assertIn("Do not invent any events",QUIP_ALTERNATIVE_REQUIREMENT)
        self.assertEqual(source.count("audit=ai("),1)
        self.assertIn('story["quip"]=selected_quip',source)

    def test_repetitive_stock_reaction_is_discarded(self):
        good="コーヒー4杯を頼んで、いちばん先に欲しかったのが出口。"
        story={"title":"救助のために配達を注文",
               "summary":"閉じ込められた男性はコーヒーを頼んだ。",
               "quip":"計画は予想の斜め上。","quipCandidates":[good]}
        self.assertEqual(choose_pre_review_quip(story),good)
        self.assertIsNone(choose_pre_review_quip(
            {"title":"新聞の見出し","summary":"何も書かれていない。",
             "quip":"世界は予想外です。","quipCandidates":[]}))


if __name__=="__main__":
    unittest.main()
