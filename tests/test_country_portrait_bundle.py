"""Verify country-portrait photography is packaged before rendering on mobile."""

from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_site import bundle_travel_photos


class CountryPortraitBundleTest(unittest.TestCase):
    def test_country_cover_prefers_local_high_resolution_then_regular_preview(self):
        prefix="https://thumb.wikimedia.org/wikipedia/commons/thumb/"
        def entry(name, cover):
            return {
                "photoAsset": "assets/travel/"+name+".jpg",
                "photo": prefix+"a/ab/"+name+".jpg/500px-"+name+".jpg",
                "photoPage": "https://commons.wikimedia.org/wiki/File:"+name+".jpg",
                "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
                "coverOnly":cover
            }

        class Response(BytesIO):
            def __init__(self):
                super().__init__(b"\xff\xd8\xff"+b"x"*4100)
                self.headers={"Content-Type":"image/jpeg"}
            def __enter__(self):
                return self
            def __exit__(self,*args):
                self.close()

        requested=[]
        def fetch(request,timeout):
            requested.append(request.full_url)
            return Response()

        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"source"
            root.mkdir()
            output=Path(temp)/"site"
            (root/"travel-stops.json").write_text(json.dumps({
                "cover":entry("hero",True),
                "other":entry("postcard",False),
            }),encoding="utf-8")
            with patch("build_site.urlopen",side_effect=fetch):
                self.assertEqual(bundle_travel_photos(root,output),2)
            self.assertEqual(len(requested),2)
            self.assertIn("/1280px-hero.jpg",requested[0])
            self.assertIn("/500px-postcard.jpg",requested[1])
            self.assertTrue((output/"assets/travel/hero.jpg").is_file())
            self.assertTrue((output/"assets/travel/postcard.jpg").is_file())

    def test_country_cover_falls_back_to_bundle_when_high_res_is_unavailable(self):
        class Response(BytesIO):
            def __init__(self):
                super().__init__(b"\xff\xd8\xff"+b"x"*4000)
                self.headers={"Content-Type":"image/jpeg"}
            def __enter__(self):
                return self
            def __exit__(self,*args):
                self.close()

        seen=[]
        def fetch(request,timeout):
            seen.append(request.full_url)
            if "/1280px-" in request.full_url:
                from urllib.error import URLError
                raise URLError("high res unavailable")
            return Response()

        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"source"
            root.mkdir()
            output=Path(temp)/"site"
            (root/"travel-stops.json").write_text(json.dumps({
                "cover":{
                    "photoAsset":"assets/travel/local-cover.jpg",
                    "photo":"https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/local-cover.jpg/500px-local-cover.jpg",
                    "photoPage":"https://commons.wikimedia.org/wiki/File:local-cover.jpg",
                    "licenseUrl":"https://creativecommons.org/licenses/by-sa/4.0/",
                    "coverOnly":True,
                }
            }),encoding="utf-8")
            with patch("build_site.urlopen",side_effect=fetch):
                self.assertEqual(bundle_travel_photos(root,output),1)
            self.assertTrue(any("/500px-" in u for u in seen))
            self.assertTrue((output/"assets/travel/local-cover.jpg").is_file())


if __name__=="__main__":
    unittest.main()
