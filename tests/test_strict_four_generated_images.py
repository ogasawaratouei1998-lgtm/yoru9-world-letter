"""Four-story hard gate, free SVG illustration publishing, safe cache rotation."""
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
        self.assertEqual(len(validate_approved(old,"2026-11-20")["stories"]),2)

    def test_static_four_story_issue_needs_no_image_files_or_api(self):
        from unittest.mock import patch
        document=approved()
        document["stories"][0]["imagePath"]=expected_path(DAY,document["stories"][0])
        public=validate_approved(document,DAY)
        self.assertEqual(len(public["stories"]),4)
        for story in public["stories"]:
            self.assertNotIn("imagePath",story)
            self.assertNotIn("imageType",story)

        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"data/approved").mkdir(parents=True)
            (root/"data/approved"/(DAY+".json")).write_text(
                json.dumps(document,ensure_ascii=False),encoding="utf-8")
            now=datetime(2026,11,21,21,20,tzinfo=ZoneInfo("Asia/Tokyo"))
            with patch("prepare_news_images.urlopen",side_effect=AssertionError("Paid API must not run")):
                self.assertTrue(publish(root,now))
            current=json.loads((root/"data/current.json").read_text(encoding="utf-8"))
            self.assertEqual(len(current["stories"]),4)
            self.assertFalse((root/"assets/news-generated").exists())

    def test_static_release_cleans_old_images_only_after_publication(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            old=root/"assets/news-generated/2026-11-20/old.webp"
            old.parent.mkdir(parents=True)
            old.write_bytes(fake_webp())
            (root/"data").mkdir()
            (root/"data/current.json").write_text(json.dumps({"editionDate":"2026-11-20","stories":[]}))
            self.assertEqual(rotate_old_generated_images(root,DAY),0)
            self.assertTrue(old.is_file())
            doc=approved()
            current=validate_approved(doc,DAY)
            (root/"data/current.json").write_text(json.dumps(current))
            self.assertEqual(rotate_old_generated_images(root,DAY),1)
            self.assertFalse(old.exists())
            self.assertEqual(rotate_old_generated_images(root,DAY),0)

    def test_preparation_never_calls_image_api_in_free_mode(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/"data/approved").mkdir(parents=True)
            for n in (3,4,5):
                (root/"data/approved"/(DAY+".json")).write_text(json.dumps(approved(n)))
                with patch("prepare_news_images.urlopen",
                           side_effect=AssertionError("No image API allowed")):
                    self.assertEqual(prepare(root,DAY,key="TEST",render=lambda *_:
                                     self.fail("Never render in free mode")),0)

    def test_zero_image_quota_stops_without_retrying_or_publishing(self):
        from io import BytesIO
        from urllib.error import HTTPError
        from unittest.mock import patch
        from prepare_news_images import gemini_image

        def denied(*args,**kwargs):
            body=json.dumps({"error":{"code":429,
                "message":"Quota exceeded for free_tier_requests, limit: 0"}}).encode()
            raise HTTPError("https://example.com",429,"Too Many Requests",{},BytesIO(body))

        with patch("prepare_news_images.urlopen",side_effect=denied) as api, \
             patch("prepare_news_images.sleep") as pause:
            with self.assertRaisesRegex(RuntimeError,"quota is zero"):
                gemini_image("fictional safe editorial image","TEST_API_KEY")
            self.assertEqual(api.call_count,1)
            pause.assert_not_called()

    def test_transient_image_rate_limit_retries_only_twice(self):
        from io import BytesIO
        from urllib.error import HTTPError
        from unittest.mock import patch
        from prepare_news_images import gemini_image

        def rate_limited(*args,**kwargs):
            body=b'{"error":{"code":429,"message":"rate limited for a minute"}}'
            raise HTTPError("https://example.com",429,"Too Many Requests",{},BytesIO(body))

        with patch("prepare_news_images.urlopen",side_effect=rate_limited) as api, \
             patch("prepare_news_images.sleep") as pause:
            with self.assertRaisesRegex(RuntimeError,"persisted after bounded retries"):
                gemini_image("fictional safe editorial image","TEST_API_KEY")
            self.assertEqual(api.call_count,3)
            self.assertEqual(pause.call_count,2)

    def test_openai_response_validation_and_request_contract(self):
        from io import BytesIO
        from unittest.mock import patch
        from prepare_news_images import openai_image,extract_openai_image_bytes

        raw=fake_webp()
        response={"data":[{"b64_json":base64.b64encode(raw).decode("ascii")}]}
        self.assertEqual(extract_openai_image_bytes(response),raw)
        for invalid in ({},{"data":[]},{"data":[{"b64_json":"not base64"}]}):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                extract_openai_image_bytes(invalid)

        class FakeResponse:
            def __enter__(self):
                return BytesIO(json.dumps(response).encode("utf-8"))
            def __exit__(self,*args):
                return False

        with patch("prepare_news_images.urlopen",return_value=FakeResponse()) as urlopen:
            self.assertEqual(openai_image("A fictional editorial scene","TEST_OPENAI_KEY"),raw)
            request=urlopen.call_args.args[0]
            self.assertEqual(request.full_url,"https://api.openai.com/v1/images/generations")
            self.assertEqual(request.get_header("Authorization"),"Bearer TEST_OPENAI_KEY")
            submitted=json.loads(request.data)
            self.assertEqual(submitted["model"],"gpt-image-2.6-flare")
            self.assertEqual(submitted["n"],1)
            self.assertEqual(submitted["quality"],"medium")
            self.assertEqual(submitted["size"],"1536x864")
            self.assertEqual(submitted["output_format"],"webp")
            self.assertNotIn("response_format",submitted)

    def test_image_provider_prefers_openai_then_falls_back_once(self):
        import os
        from unittest.mock import patch
        from prepare_news_images import image_with_fallback

        raw=fake_webp()
        env={"OPENAI_API_KEY":"TEST_OPENAI","GEMINI_IMAGE_API_KEY":"TEST_GEMINI",
             "IMAGE_PROVIDER":"auto"}
        with patch.dict(os.environ,env,clear=True), \
             patch("prepare_news_images.openai_image",return_value=raw) as op, \
             patch("prepare_news_images.gemini_image",return_value=raw) as gm:
            self.assertEqual(image_with_fallback("fictional scene"),raw)
            op.assert_called_once()
            gm.assert_not_called()
        with patch.dict(os.environ,env,clear=True), \
             patch("prepare_news_images.openai_image",
                   side_effect=RuntimeError("OpenAI image API HTTP 429")) as op, \
             patch("prepare_news_images.gemini_image",return_value=raw) as gm:
            self.assertEqual(image_with_fallback("fictional scene"),raw)
            op.assert_called_once()
            gm.assert_called_once()

    def test_image_provider_safety_refusal_never_falls_back(self):
        import os
        from unittest.mock import patch
        from prepare_news_images import image_with_fallback,ImageSafetyRefusal
        env={"OPENAI_API_KEY":"TEST_OPENAI","GEMINI_IMAGE_API_KEY":"TEST_GEMINI",
             "IMAGE_PROVIDER":"auto"}
        with patch.dict(os.environ,env,clear=True), \
             patch("prepare_news_images.openai_image",
                   side_effect=ImageSafetyRefusal("safety rejection")), \
             patch("prepare_news_images.gemini_image") as fallback:
            with self.assertRaises(ImageSafetyRefusal):
                image_with_fallback("unsafe request")
            fallback.assert_not_called()

    def test_openai_only_provider_and_missing_keys_fail_closed(self):
        import os
        from unittest.mock import patch
        from prepare_news_images import image_with_fallback
        raw=fake_webp()
        with patch.dict(os.environ,{"OPENAI_API_KEY":"TEST_OPENAI",
                                   "IMAGE_PROVIDER":"openai"},clear=True), \
             patch("prepare_news_images.openai_image",return_value=raw) as op, \
             patch("prepare_news_images.gemini_image") as gm:
            self.assertEqual(image_with_fallback("fictional scene"),raw)
            op.assert_called_once()
            gm.assert_not_called()
        with patch.dict(os.environ,{"IMAGE_PROVIDER":"auto"},clear=True):
            with self.assertRaisesRegex(RuntimeError,"No configured image provider"):
                image_with_fallback("fictional scene")

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
        self.assertIn("news-generated",service)
        self.assertIn("expirePreviousGeneratedImages",service)
        self.assertIn("IMAGE_CACHE",service)
        self.assertIn("shutil.copytree(artwork_dir,output/",builder)
        self.assertNotIn("target=output/rel",builder)
        self.assertNotIn("python prepare_news_images.py\n",workflow)
        self.assertNotIn("OPENAI_API_KEY:",workflow)
        self.assertNotIn("GEMINI_IMAGE_API_KEY:",workflow)
        self.assertIn("python prepare_news_images.py --rotate",workflow)
        self.assertIn("git add -A assets/news-generated/",workflow)
