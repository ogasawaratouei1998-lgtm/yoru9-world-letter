"""Safety and integration tests for the independent 30-day monthly editor."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import monthly_research as m

TODAY = datetime(2026, 11, 17, 13, 0, tzinfo=ZoneInfo("Asia/Tokyo")).date()
URLS = ["https://publisher-a.example/story", "https://publisher-b.example/report"]


def sample_story():
    return {
        "id": "friendly-workplace-mixup-2026",
        "eventKey": "independent-workplace-mixup-2026",
        "country": "日本", "category": "work", "categoryLabel": "仕事",
        "label": "世界のまさか",
        "title": "注文の行き先を間違えたら、意外な展開が待っていた",
        "summary": "店員が注文の送り先を間違えたことに気づき、届け先に連絡しました。話し合いの結果、穏やかな形で対応することになりました。",
        "detail": "ある店で、スタッフが注文品の届け先を間違えてしまいました。"
                  "本来の注文者のもとに商品が届かず、スタッフは状況を確認しました。"
                  "相手方に事情を説明し、連絡の行き違いがあったことを認めました。"
                  "双方が話し合って対応を決め、問題の解決に向けて動きました。",
        "quip": "配達先より先に、予想外の結末へ到着しました。",
        "quipSecond": "この注文、行き先の確認がいちばんの難関でした。",
        "sourceName": "Publisher A",
        "sourceUrl": URLS[0],
        "verificationUrls": URLS[:],
        "reported": TODAY.isoformat(),
        "expectedPlan": "注文品を正しい届け先へ配達する予定でした。",
        "observedOutcome": "届け先を取り違え、予定とは違う対応が必要になりました。",
    }


class MonthlyResearchTest(unittest.TestCase):
    def test_window_is_jst_thirty_calendar_dates(self):
        start, end = m.date_window(TODAY)
        self.assertEqual(start.isoformat(), "2026-10-19")
        self.assertEqual(end.isoformat(), "2026-11-17")
        self.assertEqual((end-start).days, 29)
        self.assertIsNone(m.safe_day("2026-11-31"))

    def test_two_independent_retrieved_publishers_are_mandatory(self):
        with patch.object(m.editorial, "public_host", return_value=True):
            self.assertTrue(m.publisher_pair(URLS))
            self.assertFalse(m.publisher_pair([URLS[0]]))
            self.assertFalse(m.publisher_pair([URLS[0], URLS[0]]))
            self.assertFalse(m.publisher_pair(["https://bbc.co.uk/a", "https://bbc.com/b"]))
            self.assertFalse(m.publisher_pair(["https://publisher-a.example/a", "https://publisher-a.example/b"]))

    def test_invalid_dates_unverified_media_and_harm_are_rejected(self):
        with patch.object(m.editorial, "public_host", return_value=True):
            self.assertTrue(m.validate_story(sample_story(), URLS, TODAY))
            for mutated in (
                {"verificationUrls": [URLS[0]]},
                {"reported": "2026-10-18"},
                {"reported": "2026-11-18"},
                {"id": "犬のまさか"},
                {"title": "事故で負傷者が発生"},
            ):
                story = {**sample_story(), **mutated}
                self.assertFalse(m.validate_story(story, URLS, TODAY), mutated)

    def test_sources_are_both_fetched_and_audited_before_acceptance(self):
        calls = []
        def ask(prompt, temperature=0.1):
            calls.append(prompt)
            if "monthly editor A" in prompt:
                return {"story": sample_story()}
            return {"approved": True, "independent": True,
                    "bothSourcesSupport": True, "reasonCode": "verified"}
        group = [{"url": URLS[0], "title": "mix-up", "seendate": "2026-11-17"},
                 {"url": URLS[1], "title": "mix-up", "seendate": "2026-11-17"}]
        with patch.object(m.editorial, "public_host", return_value=True):
            result = m.make_story(group, TODAY, [], ask_ai=ask,
                                  source_reader=lambda url: "publisher body " * 65)
            self.assertIsNotNone(result)
            self.assertEqual(len(calls), 2)
            self.assertEqual(result["verificationUrls"], URLS)
            self.assertNotIn("evidence", result)
            self.assertIsNone(m.make_story(group, TODAY, [], ask_ai=ask,
                                           source_reader=lambda url: "too short"))
            def reject(prompt, temperature=0.1):
                if "monthly editor A" in prompt:
                    return {"story": sample_story()}
                return {"approved": False, "independent": False,
                        "bothSourcesSupport": False}
            self.assertIsNone(m.make_story(group, TODAY, [], ask_ai=reject,
                                           source_reader=lambda url: "body " * 150))

    def test_no_key_is_safe_skip_with_no_public_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m.editorial, "KEY", ""):
                self.assertFalse(m.run(root=Path(directory)))
            self.assertFalse((Path(directory)/"data/monthly").exists())

    def test_release_is_immutable_and_manifest_has_real_collection_date(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(m.editorial, "public_host", return_value=True):
                self.assertTrue(m.publish_monthly([sample_story()], TODAY, root))
                self.assertFalse(m.publish_monthly([sample_story()], TODAY, root))
            file = root/"data/monthly/2026-11-17.json"
            index = root/"data/monthly/index.json"
            self.assertEqual(json.loads(file.read_text())["reviewMethod"], "two-source-two-stage-AI")
            self.assertEqual(json.loads(index.read_text())["issues"],
                             [{"date": "2026-11-17", "count": 1}])

    def test_released_archive_and_existing_monthly_stories_prevent_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            archive=root/"data/archive"
            archive.mkdir(parents=True)
            (archive/"2026-11-16.json").write_text(json.dumps({
                "status":"published",
                "stories":[sample_story()]
            },ensure_ascii=False),encoding="utf-8")
            known=m.existing_articles(root)
            self.assertFalse(m.plausible_new(sample_story(),known))
            self.assertIn(sample_story()["eventKey"],known[3])

    def test_monthly_reader_and_public_bundle_only_load_approved_records(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/"index.html").read_text(encoding="utf-8")
        build=(root/"build_site.py").read_text(encoding="utf-8")
        worker=(root/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("async function loadMonthlyVerified()",html)
        self.assertIn("document.reviewMethod!=='two-source-two-stage-AI'",html)
        self.assertIn("...monthRollingStories,...monthPublishedStories,...monthStories",html)
        self.assertIn("loadMonthlyVerified();",html)
        self.assertIn("data/monthly/index.json",build)
        self.assertIn("validate_story(story, story.get('verificationUrls', []), day)",build)
        self.assertIn("data/monthly/index.json",worker)
        self.assertIn("data/monthly/",worker)
        self.assertIn("published-monthly-index",json.loads((root/"data/monthly/index.json").read_text())["status"])


if __name__ == "__main__":
    unittest.main()
