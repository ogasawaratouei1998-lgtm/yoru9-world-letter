"""Four-story hard gate, generated-image integrity, safe cache rotation."""
import base64
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from publish_approved import validate_approved,publish
from prepare_news_images import (
    expected_path,visual_prompt,extract_image_bytes,rotate_old_generated_images,
    valid_webp,prepare,
)

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-21"

def fake_webp():
    return b"RIFF"+(22000).to_bytes(4,"little")+b"WEBP"+b"0"*21900

def approved(count=4,date=DAY):
    stories=[]
    for i in range(count):
        url=f"https://original{i}.example.com/news-{i}"
        stories.append({
            "id":f"verified-story-{i}","country":"日本",
            "category":"person","categoryLabel":"個人の失敗",
            "label":"検証用","title":f"確認済み実話の見出し {i}",
            "summary":"根拠のある出来事のみ紹介します。",
            "detail":"原文に記録された出来事を短く紹介する文章です。",
            "quip":"事実に即した思い違いへの鋭いツッコミ。",
            "sourceName":"取材元","sourceUrl":url,"reported":date,
            "verificationUrls":[url,f"https://independent{i}.example.org/news-{i}"],
            "editorVerified":True,"humorSafe":True,
            "imagePath":expected_path(date,{"id":f"verified-story-{i}"}),
        })
    return {"status":"approved","editionDate":date,"editionType":"regular",
            "title":date+"｜世界の大失敗ニュース",
            "editorApproved":True,"factChecked":True,
            "humorReviewed":True,"approvedBy":"人手確認済み",
            "stories":stories}

class StrictFourAndImagesTest(unittest.TestCase):
    def test_new_issues_require_four_to_five_verified_stories(self):
        for n in (0,1,2,3,6):
            with self.subTest(stories=n),self.assertRaises(ValueError):
                validate_approved(approved(n),DAY)
        for n in (4,5):
            with self.subTest(stories=n):
                self.assertEqual(len(validate_approved(approved(n),DAY)["stories"]),n)
        # An old two-story issue stays a valid historical archive.
        old=approved(2,"2026-11-20")
        for story in old["stories"]:story.pop("imagePath")
        self.assertEqual(len(validate_approved(old,"2026-11-20")["stories"]),2)

    def test_image_path_must_match_verified_story_and_day(self):
        case=approved()
        first=case["stories"][0]
        for path in ("","/tmp/bad.webp","assets/news-generated/2026-11-20/verified-story-0.webp",
                     "assets/news-generated/2026-11-21/../bad.webp",
                     "assets/news-generated/2026-11-21/other.webp"):
            with self.subTest(path=path):
                first["imagePath"]=path
                with self.assertRaises(ValueError):
                    validate_approved(case,DAY)
        first["imagePath"]=expected_path(DAY,first)
        published=validate_approved(case,DAY)
        self.assertEqual(published["stories"][0]["imagePath"],first["imagePath"])
        self.assertEqual(published["stories"][0]["imageType"],
                         "ai-generated-photorealistic-impression")

    def test_cannot_publish_without_four_real_image_assets(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"data/approved").mkdir(parents=True)
            document=approved()
            (root/"data/approved"/(DAY+".json")).write_text(
                json.dumps(document,ensure_ascii=False),encoding="utf-8")
            now=datetime(2026,11,21,21,20,tzinfo=ZoneInfo("Asia/Tokyo"))
            with self.assertRaises(ValueError):
                publish(root,now)
            for story in document["stories"][:-1]:
                path=root/story["imagePath"]
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(fake_webp())
            with self.assertRaises(ValueError):
                publish(root,now)
            final=root/document["stories"][-1]["imagePath"]
            final.write_bytes(fake_webp())
            self.assertTrue(publish(root,now))
            current=json.loads((root/"data/current.json").read_text(encoding="utf-8"))
            self.assertEqual(len(current["stories"]),4)

    def test_early_or_incomplete_edition_never_cleans_previous_image(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            old=root/"assets/news-generated/2026-11-20/old.webp"
            old.parent.mkdir(parents=True)
            old.write_bytes(fake_webp())
            (root/"data").mkdir()
            (root/"data/current.json").write_text(json.dumps({"editionDate":"2026-11-20","stories":[]}))
            self.assertEqual(rotate_old_generated_images(root,DAY),0)
            self.assertTrue(old.is_file())
            document=approved()
            current=validate_approved(document,DAY)
            (root/"data/current.json").write_text(json.dumps(current))
            with self.assertRaises(ValueError):
                rotate_old_generated_images(root,DAY)
            self.assertTrue(old.is_file())
            for story in current["stories"]:
                path=root/story["imagePath"];path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(fake_webp())
            self.assertEqual(rotate_old_generated_images(root,DAY),1)
            self.assertFalse(old.exists())
            self.assertEqual(rotate_old_generated_images(root,DAY),0)
            for story in current["stories"]:
                self.assertTrue(valid_webp(root/story["imagePath"]))

    def test_preparation_never_uses_paid_model_before_four_articles(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/"data/approved").mkdir(parents=True)
            (root/"data/approved"/(DAY+".json")).write_text(json.dumps(approved(3)))
            with self.assertRaises(ValueError):
                prepare(root,DAY,key="FAKE",render=lambda *_:self.fail("Should not call API"))
            self.assertEqual(prepare(root,"2026-11-20",key="FAKE"),0)

    def test_image_api_parser_and_non_documentary_prompt(self):
        raw=b"\xff\xd8\xff"+b"0"*22000
        response={"steps":[{"type":"model_output","content":[
            {"type":"text","text":"illustration"},
            {"type":"image","mime_type":"image/jpeg",
             "data":base64.b64encode(raw).decode()}]}]}
        self.assertEqual(extract_image_bytes(response),raw)
        with self.assertRaises(ValueError):
            extract_image_bytes({"steps":[]})
        prompt=visual_prompt(approved()["stories"][0])
        for condition in ("FICTIONAL","NOT","anonymous","no","words"):
            self.assertIn(condition,prompt)

    def test_reader_labels_every_new_generated_image_and_falls_back(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        service=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        builder=(ROOT/"build_site.py").read_text(encoding="utf-8")
        workflow=(ROOT/".github/workflows/publish-nightly.yml").read_text(encoding="utf-8")
        self.assertIn("function hasDailyGeneratedImage(story){",page)
        self.assertIn("イメージ画像（AI生成）",page)
        self.assertIn("報道写真ではありません",page)
        self.assertIn("img.src=fallbackNewsArt(story)",page)
        self.assertIn("assets/news-generated",service)
        self.assertIn("expirePreviousGeneratedImages",service)
        self.assertIn("IMAGE_CACHE",service)
        self.assertIn("target=output/rel",builder)
        self.assertIn("python prepare_news_images.py",workflow)
        self.assertIn("python prepare_news_images.py --rotate",workflow)
        self.assertIn("git add -A assets/news-generated/",workflow)
