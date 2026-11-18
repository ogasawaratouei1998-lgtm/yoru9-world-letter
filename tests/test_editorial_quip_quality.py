"""Quality safeguards for the published two-stage Japanese quips."""
import json
from pathlib import Path
import unittest
from auto_editorial import WRITING_CRAFT
from publish_approved import validate_approved

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-16"

class EditorialQuipQualityTest(unittest.TestCase):
    def test_edition_text_is_consistent_in_published_archive_and_approved(self):
        current=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        archive=json.loads((ROOT/"data/archive"/(DAY+".json")).read_text(encoding="utf-8"))
        approved=json.loads((ROOT/"data/approved"/(DAY+".json")).read_text(encoding="utf-8"))
        # The approved source must reproduce exactly the public edition, not
        # merely have matching headlines. Catch stale workflow overwrites of
        # summaries, sources, jokes, closings and computed quote as well.
        self.assertEqual(validate_approved(approved,DAY),archive)
        if current["editionDate"]==DAY:
            self.assertEqual(current,archive)

    def test_quips_are_short_and_avoid_unproven_private_allegations(self):
        issue=json.loads((ROOT/"data/archive"/(DAY+".json")).read_text(encoding="utf-8"))
        for story in issue["stories"]:
            with self.subTest(story=story["id"]):
                self.assertTrue(15<=len(story["quip"])<=45)
                self.assertTrue(15<=len(story["quipSecond"])<=55)
                self.assertNotEqual(story["quip"],story["quipSecond"])
                for unsafe in ("甘い誘い","怪しい人物","スキャンダルによる","反抗期があったようです"):
                    self.assertNotIn(unsafe,story["quip"]+story["quipSecond"]+story["title"])

    def test_revised_nvidia_story_excludes_private_life_allegations_and_shows_sources(self):
        # The incident belongs to the archived Nov 16 release, not
        # data/current.json after the next nightly edition goes live.
        archived=json.loads((ROOT/"data/archive"/(DAY+".json")).read_text(encoding="utf-8"))
        story=next(s for s in archived["stories"] if s["id"]=="jensen-huang-nvidia-resignation-2026")
        for phrase in ("私的な関係","アリス・フアン","スパイ","不倫","Megaspeed"):
            self.assertNotIn(phrase,story["summary"]+story["detail"])
        self.assertIn("correctionNote",story)
        self.assertIn("SEC",story["detail"])
        self.assertIn("sec.gov", " ".join(story["verificationUrls"]))
        self.assertTrue(all(url.startswith("https://") for url in story["verificationUrls"]))

    def test_november_17_coffee_joke_is_clear_in_all_published_copies(self):
        day="2026-11-17"
        approved=json.loads((ROOT/"data/approved"/(day+".json")).read_text(encoding="utf-8"))
        archive=json.loads((ROOT/"data/archive"/(day+".json")).read_text(encoding="utf-8"))
        current=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_approved(approved,day),archive)
        if current.get("editionDate")==day:
            self.assertEqual(current,archive)
        story=next(s for s in archive["stories"] if s["id"]=="cheonan-painters-coffee-rescue-2026")
        self.assertEqual(story["quipSecond"],"コーヒーを注文したら、配達員が救助隊まで兼任してくれた。")
        self.assertIn("コーヒー4杯",story["summary"])
        self.assertIn("配達員",story["summary"])
        self.assertIn("報道に基づく事実関係は変更していません",story["correctionNote"])
        self.assertNotIn("開くはずのなかったドア",story["quipSecond"])

    def test_manzai_craft_requires_furi_zurashi_and_a_last_beat(self):
        from auto_editorial import MANZAI_CRAFT,MANZAI_REVIEW
        from editorial_quality import REVIEW_FIELDS
        code=(ROOT/"auto_editorial.py").read_text(encoding="utf-8")
        for idea in ("actual function","role reversal","last short phrase",
                     "read-aloud one-breath test","LAST beat",
                     "headline already tells WHO and WHAT"):
            self.assertIn(idea,MANZAI_CRAFT)
        for flag in ("firstQuipAngleEarned","firstQuipNaturalSpeech",
                     "firstQuipFinalBeat"):
            self.assertIn(flag,MANZAI_REVIEW)
            self.assertIn(flag,REVIEW_FIELDS)
            self.assertIn(flag+":boolean",code)
        self.assertIn("MANZAI_CRAFT+' You are a Japanese comedy show writer",code)
        self.assertIn("MANZAI_CRAFT+\n",code)
        self.assertIn('MANZAI_REVIEW+" You are independent adversarial',code)
        self.assertEqual(code.count("audit=ai("),1,
                         "quality upgrade must not add a scarce AI fact-review call")
        self.assertIn("no quip-worthy story",MANZAI_CRAFT)
        self.assertIn("Do NOT invent literal dialogue",MANZAI_CRAFT)
        # Strict new rules apply to NEW content; immutable past records
        # remain unchanged and are not retroactively misrepresented.
        archive=json.loads((ROOT/"data/archive"/"2026-11-17.json").read_text(encoding="utf-8"))
        self.assertEqual(len(archive["stories"]),3)

    def test_generated_jokes_have_first_read_clarity_rule(self):
        self.assertIn("Clarity veto:",WRITING_CRAFT)
        self.assertIn("the reader must understand both jokes on the first pass",WRITING_CRAFT)
        code=(ROOT/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("Reject a quip that a Japanese reader cannot understand on the first read after the summary",code)

    def test_november_17_all_six_quips_and_closing_have_editorial_quality(self):
        day="2026-11-17"
        approved=json.loads((ROOT/"data/approved"/(day+".json")).read_text(encoding="utf-8"))
        archive=json.loads((ROOT/"data/archive"/(day+".json")).read_text(encoding="utf-8"))
        self.assertEqual(validate_approved(approved,day),archive)
        current=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        if current.get("editionDate")==day:self.assertEqual(current,archive)
        expected={
            "cheonan-painters-coffee-rescue-2026":(
                "コーヒー4杯の注文メモが、まさかのSOS欄。配達アプリ、守備範囲が広い。",
                "コーヒーを注文したら、配達員が救助隊まで兼任してくれた。"),
            "guaira-degavar-road-marking-2026":(
                "「ゆっくり」のつづりは間違えた。でも目立つ仕事だけは大成功。",
                "市は誤字を塗り直し、その失敗談を交通安全係にスカウト。"),
            "albert-lea-mcnugget-monkey-diaper-police-2026":(
                "「不審者」の正体は、おむつ姿のサル。しかも名前がマックナゲット。",
                "警察の冗談は「弁護士とバナナを要求」。ボケ役、まさかの警察側。"),
        }
        self.assertEqual(set(expected),{s["id"] for s in archive["stories"]})
        for story in archive["stories"]:
            with self.subTest(id=story["id"]):
                self.assertEqual((story["quip"],story["quipSecond"]),expected[story["id"]])
                self.assertTrue(15<=len(story["quip"])<=45)
                self.assertTrue(15<=len(story["quipSecond"])<=55)
                self.assertIn("correctionNote",story)
                self.assertNotEqual(story["quip"],story["quipSecond"])
        self.assertEqual(archive["nightlyMessage"],
                         "仕事内容：その他、まさかの対応あり。世界の求人票、備考欄が足りない。")

    def test_closing_comedy_requires_concrete_payoff_and_independent_review(self):
        from unittest.mock import patch
        from auto_editorial import valid_nightly_comedy_line,compose_nightly_comedy,NIGHTLY_COMEDY_CRAFT
        # Previously published as the 11/17 closing, but it must never
        # pass the stronger evidence-and-comedy gates for new editions.
        good="コーヒー4杯を頼んだら、いちばん必要だった出口まで届いた。"
        old="コーヒーの配達が出口になり、誤字が安全の呼びかけに。警察が保護したのは、おむつ姿のサル。世界の「まさか」は予想以上に自由です。"
        self.assertTrue(valid_nightly_comedy_line(good))
        self.assertFalse(valid_nightly_comedy_line(old))
        self.assertFalse(valid_nightly_comedy_line("おやすみなさい。元気を出してください。"))
        self.assertFalse(valid_nightly_comedy_line(good,[good]))
        self.assertFalse(valid_nightly_comedy_line("これはテスト用の文章です。\\nふたつに分かれています。"))
        self.assertFalse(valid_nightly_comedy_line("これはテスト用の文章です。\\r改行が混じっています。"))
        self.assertFalse(valid_nightly_comedy_line("これはテスト用の文章です。 https://example.org/"))

        self.assertIn("20〜60文字",NIGHTLY_COMEDY_CRAFT)
        stories=[{"title":"コーヒー4杯を注文し、配達員にドアを開けてもらった",
                  "summary":"閉じ込められた作業員がコーヒー4杯を注文し、配達員がドアを開けて救助した。",
                  "category":"work"}]
        drafts={"candidates":["短すぎる",good,"予定どおりならニュースにならない。今日も現実が台本を破った。"]}
        verdict={"approved":True,"bestIndex":0,"factAnchorVerified":True,
                 "comicPayoffWorks":True,"reason":"原記事の事実からオチまでつながる"}
        with patch("auto_editorial.ai",side_effect=[drafts,verdict]) as mocked:
            self.assertEqual(compose_nightly_comedy(stories),good)
            self.assertEqual(mocked.call_count,2)
        with patch("auto_editorial.ai",side_effect=[drafts,{"approved":False,"bestIndex":0}]):
            self.assertIsNone(compose_nightly_comedy(stories))

    def test_legacy_closing_fallback_preserved_and_future_fallback_short(self):
        from publish_approved import nightly_message,COMIC_NIGHT_MESSAGES,NIGHT_MESSAGES
        stories=[{"category":"work"}]
        self.assertTrue(NIGHT_MESSAGES["work"])
        self.assertIn(nightly_message("2026-11-18",stories),COMIC_NIGHT_MESSAGES["work"])
        self.assertNotIn(nightly_message("2026-11-17",stories),COMIC_NIGHT_MESSAGES["work"])

    def test_generator_creativity_and_fact_checker_remain_separate(self):
        self.assertIn("four sharply different one-liners",WRITING_CRAFT)
        self.assertIn("unproven causes",WRITING_CRAFT)
        code=(ROOT/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn('def ai(prompt,temperature=0.1):',code)
        self.assertIn('draft_response=ai(prompt,temperature=0.65)',code)
        self.assertIn('retry_result=ai(retry_prompt,temperature=0.65)',code)
        self.assertIn('audit=ai(',code)

if __name__=="__main__":
    unittest.main()
