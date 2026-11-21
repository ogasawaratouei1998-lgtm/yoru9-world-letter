"""Issue-level joke cadence diversity without weakening news fact checks."""
import json
from collections import Counter
from pathlib import Path
import tempfile
import unittest

from auto_editorial import select_diverse_verified_stories,save_editorial_funnel,MANZAI_CRAFT
from quip_variety import (quip_cadence, repeated_cadence_count,
                          repeated_exact_quip_count, quip_variety_metrics)

ROOT=Path(__file__).resolve().parents[1]


class QuipVarietyTest(unittest.TestCase):
    def test_only_obvious_cadence_tics_are_classified(self):
        self.assertEqual(quip_cadence("オチがそこにあるんかい！"),"kai")
        self.assertEqual(quip_cadence("鍵もなくしてるやないか！"),"janaika")
        self.assertEqual(quip_cadence("そこになんでやねん！？"),"nandeyanen")
        self.assertEqual(quip_cadence("さらにやらかすな！"),"suna")
        self.assertEqual(quip_cadence("いったいどうすんねん！"),"dousunnen")
        self.assertIsNone(quip_cadence("観客より先に値札が登場。"))
        self.assertIsNone(quip_cadence(None))

    def test_variety_is_only_a_final_tiebreaker_among_verified_stories(self):
        # All factual, historical, regional, topic and category priorities tie.
        # Diversity must prefer the two distinctive punches to a fourth
        # article with exactly the same final verbal tic.
        common={"country":"US","category":"work",
                "title":"同じ種類の間違いで意外な結果",
                "humanMistake":"予定とは異なる結果になった",
                "majorPersonalFailureVerified":False}
        stories=[{**common,"id":str(i),"quip":"思惑と違う結果になっとるやないか！"}
                 for i in range(4)]
        stories.append({**common,"id":"E","quip":"予想よりも結果が先に来たんかい！"})
        stories.append({**common,"id":"F","quip":"思い切って全部逆にすな！"})
        picked=select_diverse_verified_stories(
            stories,Counter(),Counter(),Counter(),Counter(),
            selection_seed="2026-11-21")
        self.assertEqual(len(picked),5)
        self.assertEqual({s["id"] for s in picked}&{"E","F"},{"E","F"})
        self.assertEqual(repeated_cadence_count(picked),2)

    def test_exact_duplicate_gags_lose_tiebreak_without_recognizable_cadence(self):
        common={"country":"US","category":"work",
                "title":"記録と実際が食い違った事件",
                "humanMistake":"計画と結果の差が確認された"}
        repeated=[{**common,"id":str(i),
                   "quip":"伝票を出したはずが、帰宅したのは伝票だけ。"}
                  for i in range(4)]
        distinct=[
            {**common,"id":"E","quip":"上司の予定表だけが先に謝罪した。"},
            {**common,"id":"F","quip":"荷物が出勤した頃、伝票は休日だった。"},
        ]
        self.assertEqual(repeated_cadence_count(repeated+distinct),0)
        self.assertEqual(repeated_exact_quip_count(repeated+distinct),3)
        self.assertEqual(repeated_exact_quip_count(
            [{"quip":"同じ 笑い。"},{"quip":"同じ笑い。"}]),1)
        chosen=select_diverse_verified_stories(
            repeated+distinct,Counter(),Counter(),selection_seed="2026-11-21")
        self.assertEqual(len(chosen),5)
        self.assertEqual({x["id"] for x in chosen}&{"E","F"},{"E","F"})
        self.assertEqual(repeated_exact_quip_count(chosen),2)

    def test_five_verified_similar_quips_remain_eligible(self):
        # Never suppress a sourced article or manufacture an alternative joke
        # just to satisfy a stylistic goal.
        rows=[{"id":str(i),"country":"US","category":"work",
               "title":"Source-checked mistake","quip":"驚くしかないやないか！"}
              for i in range(5)]
        self.assertEqual(len(select_diverse_verified_stories(
            rows,Counter(),Counter(),selection_seed="2026-11-21")),5)
        self.assertEqual(repeated_cadence_count(rows),4)

    def test_aggregate_diagnostics_never_include_news_or_quip_text(self):
        quips=[{"quip":"大騒動やないか！"},
               {"quip":"同じツッコミやないか！"},
               {"quip":"別のオチなんかい！"},
               {"quip":"固有の余韻で幕。"}]
        stats=quip_variety_metrics(quips)
        self.assertEqual(stats,{"repeated_quip_cadences":1,
                                "recognized_quip_cadences":3})
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"private.json"
            record=save_editorial_funnel("selected",{
                "selected_for_edition":4,**stats,
                "storyTitle":"SECRET NEWS STORY",
                "quipText":"THIS MUST NOT BE LOGGED"},dest)
            self.assertEqual(record["repeated_quip_cadences"],1)
            data=dest.read_text(encoding="utf-8")
            self.assertNotIn("SECRET",data)
            self.assertNotIn("THIS MUST NOT",data)

    def test_current_published_issue_is_not_mutated_or_rewritten(self):
        issue=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        before=json.loads((ROOT/"data/archive"/(issue["editionDate"]+".json")).read_text(encoding="utf-8"))
        self.assertEqual(issue,before)
        self.assertIn("Kansai dialect is welcome when it fits",MANZAI_CRAFT)
        code=(ROOT/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("-repeated_cadence_count(stories)",code)
        self.assertIn("quip_variety_metrics(selected)",code)
        self.assertIn("validate_approved(payload,day)",code)


if __name__=="__main__":
    unittest.main()
