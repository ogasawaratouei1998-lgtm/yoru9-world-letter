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

    def test_generated_jokes_have_first_read_clarity_rule(self):
        self.assertIn("Clarity veto:",WRITING_CRAFT)
        self.assertIn("the reader must understand both jokes on the first pass",WRITING_CRAFT)
        code=(ROOT/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn("Reject a quip that a Japanese reader cannot understand on the first read after the summary",code)

    def test_generator_creativity_and_fact_checker_remain_separate(self):
        self.assertIn("three alternative first-hit jokes",WRITING_CRAFT)
        self.assertIn("unproven causes",WRITING_CRAFT)
        code=(ROOT/"auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn('def ai(prompt,temperature=0.1):',code)
        self.assertIn('draft_response=ai(prompt,temperature=0.65)',code)
        self.assertIn('retry_result=ai(retry_prompt,temperature=0.65)',code)
        self.assertIn('audit=ai(',code)

if __name__=="__main__":
    unittest.main()
