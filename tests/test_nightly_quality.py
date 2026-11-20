"""Regression checks for the weak 2026-11-17 "world job listing" closing."""
import unittest
from unittest.mock import patch

import auto_editorial as editorial
from nightly_quality import incident_specific_nightly_line
from publish_approved import validate_approved
from test_publish import fixture


BAD="仕事内容：その他、まさかの対応あり。世界の求人票、備考欄が足りない。"
GOOD="コーヒー4杯を頼んだら、いちばん必要だった出口まで届いた。"

STORY={
    "id":"coffee-delivery-rescue",
    "title":"コーヒー4杯を注文し、配達員にドアを開けてもらった",
    "summary":"閉じ込められた作業員がコーヒー4杯を注文。配達員がドアを開け、1杯をお礼に渡した。",
    "category":"work",
}


class NightlyLineQualityTests(unittest.TestCase):
    def test_bad_world_job_listing_rejected_even_with_footnote_keyword(self):
        self.assertFalse(incident_specific_nightly_line(BAD,[{
            **STORY,
            "summary":STORY["summary"]+"備考欄でドアを開けてほしいと頼んだ。",
        }]))
        self.assertTrue(incident_specific_nightly_line(GOOD,[STORY]))
        self.assertFalse(incident_specific_nightly_line(
            "今日も世界では、いろいろな予想外が起きました。",[STORY]))
        self.assertFalse(incident_specific_nightly_line(
            "コーヒーの注文なら何でも大丈夫です。",[]))

    def test_editor_a_and_editor_b_must_both_ground_the_actual_punchline(self):
        candidates=[BAD,GOOD,"世界の求人票は今日も予定外だらけです。"]
        with patch.object(editorial,"ai",side_effect=[
            {"candidates":candidates},
            {"approved":True,"bestIndex":0,"factAnchorVerified":True,
             "comicPayoffWorks":True,"reason":"具体的な救助の逆転"},
        ]) as mock_ai:
            self.assertEqual(editorial.compose_nightly_comedy([STORY]),GOOD)
            self.assertEqual(mock_ai.call_count,2)

        with patch.object(editorial,"ai",side_effect=[
            {"candidates":candidates},
            {"approved":True,"bestIndex":0,"factAnchorVerified":True,
             "comicPayoffWorks":False,"reason":"弱いオチ"},
        ]):
            self.assertIsNone(editorial.compose_nightly_comedy([STORY]))
        with patch.object(editorial,"ai",return_value={"candidates":[BAD,BAD,BAD]}):
            self.assertIsNone(editorial.compose_nightly_comedy([STORY]))

    def test_new_publisher_omits_weak_or_missing_line_without_blocking_news(self):
        approved=fixture("2026-11-18")
        approved["stories"]=approved["stories"][:1]
        approved["stories"][0]["reported"]="2026.11.17"
        approved["stories"][0]["title"]=STORY["title"]
        approved["stories"][0]["summary"]=STORY["summary"]
        approved["nightlyMessage"]=BAD
        self.assertEqual(validate_approved(approved,"2026-11-18")["nightlyMessage"],"")
        approved["nightlyMessage"]=GOOD
        self.assertEqual(validate_approved(approved,"2026-11-18")["nightlyMessage"],GOOD)
        del approved["nightlyMessage"]
        self.assertEqual(validate_approved(approved,"2026-11-18")["nightlyMessage"],"")

    def test_previous_edition_is_not_rewritten(self):
        approved=fixture("2026-11-17")
        approved["nightlyMessage"]=BAD
        self.assertEqual(validate_approved(approved,"2026-11-17")["nightlyMessage"],BAD)

    def test_reader_uses_sourced_daily_quote_not_old_nightly_comedy(self):
        from pathlib import Path
        page=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="closingQuote"',page)
        self.assertIn('id="closingJump"',page)
        self.assertIn("updateDailyFailureQuote(localDate(new Date()))",page)
        self.assertIn("DAILY_FAILURE_QUOTES",page)
        self.assertIn("日本語意訳",page)
        self.assertIn("$('closingQuote').hidden=false",page)
        self.assertIn("$('closingJump').hidden=false",page)
        self.assertNotIn("const nightlyLine=",page)


if __name__=="__main__":
    unittest.main()
