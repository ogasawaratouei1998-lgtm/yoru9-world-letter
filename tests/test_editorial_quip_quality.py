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
        current=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        story=next(s for s in current["stories"] if s["id"]=="jensen-huang-nvidia-resignation-2026")
        for phrase in ("私的な関係","アリス・フアン","スパイ","不倫","Megaspeed"):
            self.assertNotIn(phrase,story["summary"]+story["detail"])
        self.assertIn("correctionNote",story)
        self.assertIn("SEC",story["detail"])
        self.assertIn("sec.gov", " ".join(story["verificationUrls"]))
        self.assertTrue(all(url.startswith("https://") for url in story["verificationUrls"]))

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
