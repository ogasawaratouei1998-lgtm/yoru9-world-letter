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

    def test_grounded_object_beats_a_vague_universal_reaction(self):
        generic="まあ、世の中にはいろいろな展開が起こるものですね。"
        grounded="コーヒーを注文したのに、配達員の本業が救助係に。"
        story={
            "title":"閉じ込められた男性が配達で助かった",
            "summary":"閉じ込められた男性は配達員にコーヒーを頼み、救助された。",
            "humanMistake":"男性はコーヒーの宅配を注文して助けを呼んだ",
            "expectedPlan":"配達員にコーヒーを届けてもらう",
            "observedOutcome":"配達員が扉を開け、男性を救助した",
            "quip":generic,"quipCandidates":[grounded],
        }
        self.assertEqual(choose_pre_review_quip(story),grounded)
        self.assertEqual(len(quip_candidates_ranked(story)),2)
        self.assertNotIn("editorVerified",story,
                         "A deterministic anchor is not source verification")

    def test_identical_punchline_with_punctuation_variations_collapses(self):
        original="コーヒーを注文して、欲しかったのはコーヒーより出口。"
        variant="コーヒーを注文して欲しかったのはコーヒーより出口！"
        alternative="宅配の用事は注文、到着後の本業は救助係だった。"
        story={"title":"玄関の鍵が開かず宅配員に助けてもらう",
               "summary":"閉じ込められた人が配達で助けを求めた。",
               "humanMistake":"コーヒーの注文",
               "expectedPlan":"コーヒーを受け取る",
               "observedOutcome":"配達員が閉じ込められた人を救助した",
               "quip":original,"quipCandidates":[variant,alternative]}
        ranked=quip_candidates_ranked(story)
        self.assertEqual(len(ranked),2,ranked)
        self.assertIn(alternative,ranked)
        self.assertEqual(sum(x in ranked for x in (original,variant)),1)

    def test_anchor_scoring_does_not_block_unusual_metaphors_or_legacy_drafts(self):
        metaphor="注文書だけが先に休暇を申請してしまった。"
        story={"title":"業務手順の不備","summary":"予定の配達が延期された。",
               "quip":metaphor}
        self.assertEqual(choose_pre_review_quip(story),metaphor)
        self.assertIsNone(choose_pre_review_quip(
            {"title":"同一記事","summary":"報道内容","quip":""}))

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
