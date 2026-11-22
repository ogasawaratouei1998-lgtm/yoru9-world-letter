"""Photo caching must preserve source/license provenance and mobile resolution."""
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_site import bundle_travel_photos, MAX_PUBLIC_PHOTO_MANIFEST_BYTES
from check_release_candidate import jpeg_dimensions


def jpeg(width=1300,height=720):
    header=(b"\xff\xd8\xff\xc0\x00\x11\x08"+height.to_bytes(2,"big")+
            width.to_bytes(2,"big")+b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00")
    return header+b"x"*4100+b"\xff\xd9"


class Response(BytesIO):
    def __init__(self,payload):
        super().__init__(payload)
        self.headers={"Content-Type":"image/jpeg"}
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


class TravelPhotoCacheTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"source"
        self.root.mkdir()
        self.output=Path(self.temp.name)/"site"
        self.cache=Path(self.temp.name)/"cache"
        self.manifest=self.root/"travel-stops.json"
        self.record={"photoAsset":"assets/travel/hero.jpg",
                     "photo":"https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/hero.jpg/500px-hero.jpg",
                     "photoPage":"https://commons.wikimedia.org/wiki/File:hero.jpg",
                     "author":"Named photographer",
                     "license":"CC BY-SA 4.0",
                     "licenseUrl":"https://creativecommons.org/licenses/by-sa/4.0/",
                     "coverOnly":True}
        self.write_manifest()
    def write_manifest(self):
        self.manifest.write_text(json.dumps({"hero":self.record}),encoding="utf-8")

    def test_cache_is_validated_and_reused_without_network(self):
        hits=[]
        def network(req,timeout):
            hits.append(req.full_url)
            return Response(jpeg())
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            self.assertEqual(bundle_travel_photos(self.root,self.output),1)
        self.assertEqual(len(hits),1)
        self.assertIn("/1280px-",hits[0])
        image=self.output/"assets/travel/hero.jpg"
        self.assertEqual(jpeg_dimensions(image),(1300,720))
        self.assertEqual(len(list(self.cache.glob("*.jpg"))),1)
        image.unlink()
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=AssertionError("Network should not run")):
            self.assertEqual(bundle_travel_photos(self.root,self.output),1)
        self.assertEqual(jpeg_dimensions(image),(1300,720))
        self.assertEqual(len(hits),1)

    def test_nonstandard_reviewed_cover_width_upgrades_to_retina_resolution(self):
        for original in (600, 960, 1024):
            with self.subTest(original=original):
                self.record["photo"]=self.record["photo"].replace("/500px-",f"/{original}px-")
                self.write_manifest()
                hits=[]
                def network(req,timeout):
                    hits.append(req.full_url)
                    self.assertIn("/1280px-hero.jpg",req.full_url)
                    return Response(jpeg())
                with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
                     patch("build_site.urlopen",side_effect=network):
                    self.assertEqual(bundle_travel_photos(self.root,self.output),1)
                self.assertEqual(len(hits),1)
                self.assertEqual(jpeg_dimensions(self.output/"assets/travel/hero.jpg"),(1300,720))
                self.record["photo"]=self.record["photo"].replace(f"/{original}px-","/500px-")

    def test_service_unavailable_defers_other_wikimedia_requests(self):
        from urllib.error import HTTPError
        second={**self.record,"photoAsset":"assets/travel/second.jpg",
                "photo":self.record["photo"].replace("hero.jpg","second.jpg"),
                "photoPage":self.record["photoPage"].replace("hero.jpg","second.jpg")}
        self.manifest.write_text(json.dumps({"hero":self.record,"second":second}),encoding="utf-8")
        hits=[]
        def network(req,timeout):
            hits.append(req.full_url)
            if "wikimedia.org" in req.full_url:
                raise HTTPError(req.full_url,503,"temporarily unavailable",{},None)
            if req.full_url.endswith("/travel-stops.json"):
                return Response(b"{}")
            raise AssertionError(req.full_url)
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            with self.assertRaisesRegex(RuntimeError,"Wikimedia rate limited"):
                bundle_travel_photos(self.root,self.output)
        self.assertEqual(sum("wikimedia.org" in u for u in hits),1)

    def test_changed_license_or_source_forces_new_fetch(self):
        hits=[]
        def network(req,timeout):
            hits.append(req.full_url)
            return Response(jpeg())
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            bundle_travel_photos(self.root,self.output)
            self.record["license"]="CC BY 4.0"
            self.record["licenseUrl"]="https://creativecommons.org/licenses/by/4.0/"
            self.write_manifest()
            bundle_travel_photos(self.root,self.output)
        self.assertEqual(len(hits),2,"Changed attribution may not reuse stale cached bytes")
        self.assertEqual(len(list(self.cache.glob("*.jpg"))),2)

    def test_corrupt_cache_never_used(self):
        hits=[]
        def network(req,timeout):
            hits.append(req.full_url)
            return Response(jpeg())
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            bundle_travel_photos(self.root,self.output)
            cache=next(self.cache.glob("*.jpg"))
            cache.write_bytes(b"not a JPEG")
            bundle_travel_photos(self.root,self.output)
        self.assertEqual(len(hits),2)
        self.assertEqual(jpeg_dimensions(self.output/"assets/travel/hero.jpg"),(1300,720))

    def test_low_resolution_cover_fails_closed_and_is_not_cached(self):
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",return_value=Response(jpeg(500,300))):
            with self.assertRaisesRegex(RuntimeError,"旅行写真の欠落を防ぐため公開停止"):
                bundle_travel_photos(self.root,self.output)
        self.assertEqual(list(self.cache.glob("*.jpg")),[])

    def test_wikimedia_rate_limit_recovers_only_provenance_matched_previous_photo(self):
        from urllib.error import HTTPError
        hits=[]
        prior={"hero":dict(self.record)}
        def network(req,timeout):
            url=req.full_url
            hits.append(url)
            if "wikimedia.org" in url:
                raise HTTPError(url,429,"rate limited",{},None)
            if url.endswith("/travel-stops.json"):
                return Response(json.dumps(prior).encode("utf-8"))
            if url.endswith("/assets/travel/hero.jpg"):
                return Response(jpeg())
            raise AssertionError("Unexpected download: "+url)
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            self.assertEqual(bundle_travel_photos(self.root,self.output),1)
        self.assertTrue(any(url.endswith("/travel-stops.json") for url in hits))
        self.assertTrue(any(url.endswith("/assets/travel/hero.jpg") for url in hits))
        self.assertEqual(jpeg_dimensions(self.output/"assets/travel/hero.jpg"),(1300,720))
        self.assertEqual(len(list(self.cache.glob("*.jpg"))),1)

    def test_large_public_manifest_recovers_without_repeated_wikimedia_requests(self):
        from urllib.error import HTTPError
        second={**self.record,"photoAsset":"assets/travel/second.jpg",
                "photo":self.record["photo"].replace("hero.jpg","second.jpg"),
                "photoPage":self.record["photoPage"].replace("hero.jpg","second.jpg")}
        self.manifest.write_text(json.dumps({"hero":self.record,"second":second}),encoding="utf-8")
        prior={"padding":{"note":"x"*250_000},"hero":dict(self.record),"second":second}
        payload=json.dumps(prior).encode("utf-8")
        self.assertGreater(len(payload),150_001)
        hits=[]
        def network(req,timeout):
            url=req.full_url
            hits.append(url)
            if "wikimedia.org" in url:
                raise HTTPError(url,429,"rate limited",{},None)
            if url.endswith("/travel-stops.json"):
                return Response(payload)
            if url.endswith(("/assets/travel/hero.jpg","/assets/travel/second.jpg")):
                return Response(jpeg())
            raise AssertionError(url)
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            self.assertEqual(bundle_travel_photos(self.root,self.output),2)
        self.assertEqual(sum("wikimedia.org" in u for u in hits),1)
        self.assertEqual(len(list(self.cache.glob("*.jpg"))),2)

    def test_oversized_public_manifest_fails_closed(self):
        from urllib.error import HTTPError
        payload=json.dumps({"padding":"x"*MAX_PUBLIC_PHOTO_MANIFEST_BYTES,
                            "hero":dict(self.record)}).encode("utf-8")
        def network(req,timeout):
            if "wikimedia.org" in req.full_url:
                raise HTTPError(req.full_url,429,"rate limited",{},None)
            if req.full_url.endswith("/travel-stops.json"):
                return Response(payload)
            raise AssertionError("Must not recover from oversized manifest")
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            with self.assertRaisesRegex(RuntimeError,"旅行写真の欠落を防ぐため公開停止"):
                bundle_travel_photos(self.root,self.output)
        self.assertFalse(list(self.cache.glob("*.jpg")))

    def test_old_site_with_different_photo_attribution_cannot_substitute(self):
        from urllib.error import HTTPError
        prior={"hero":{**self.record,"author":"Different photographer"}}
        hits=[]
        def network(req,timeout):
            hits.append(req.full_url)
            if "wikimedia.org" in req.full_url:
                raise HTTPError(req.full_url,429,"rate limited",{},None)
            if req.full_url.endswith("/travel-stops.json"):
                return Response(json.dumps(prior).encode("utf-8"))
            raise AssertionError("Must never fetch unverified old-site JPEG")
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            with self.assertRaisesRegex(RuntimeError,"旅行写真の欠落を防ぐため公開停止"):
                bundle_travel_photos(self.root,self.output)
        self.assertFalse(any(url.endswith("/assets/travel/hero.jpg") for url in hits))
        self.assertFalse(list(self.cache.glob("*.jpg")))

    def test_older_inactive_photo_can_recover_but_cannot_become_new_active_blurry_cover(self):
        from urllib.error import HTTPError
        # Fixture page has a US portrait; the current issue is initially DE.
        (self.root/"index.html").write_text(
            'const TODAY_COUNTRY_PHOTOS=Object.freeze({"US":[{"asset":"assets/travel/hero.jpg"}]});\n',
            encoding="utf-8")
        current=self.root/"data/current.json"
        current.parent.mkdir(parents=True,exist_ok=True)
        current.write_text(json.dumps({"stories":[{"country":"Germany"}]}),encoding="utf-8")
        prior={"hero":dict(self.record)}
        def network(req,timeout):
            url=req.full_url
            if "wikimedia.org" in url:
                raise HTTPError(url,429,"rate limited",{},None)
            if url.endswith("/travel-stops.json"):
                return Response(json.dumps(prior).encode("utf-8"))
            if url.endswith("/assets/travel/hero.jpg"):
                return Response(jpeg(500,153))
            raise AssertionError("Unexpected request "+url)
        with patch.dict(os.environ,{"YORU9_PHOTO_CACHE_DIR":str(self.cache)}), \
             patch("build_site.urlopen",side_effect=network):
            self.assertEqual(bundle_travel_photos(self.root,self.output),1)
            self.assertEqual(jpeg_dimensions(self.output/"assets/travel/hero.jpg"),(500,153))
            # The same 500px saved image is NOT an acceptable full-width
            # country hero when this country becomes the active edition.
            current.write_text(json.dumps({"stories":[{"country":"United States"}]}),
                               encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError,"旅行写真の欠落を防ぐため公開停止"):
                bundle_travel_photos(self.root,self.output)

    def test_actions_enable_same_cache_for_preview_release_and_deploy(self):
        repo=Path(__file__).resolve().parents[1]
        for path in (".github/workflows/test-publishing.yml",
                     ".github/workflows/publish-nightly.yml",
                     ".github/workflows/deploy-site.yml"):
            with self.subTest(workflow=path):
                source=(repo/path).read_text(encoding="utf-8")
                self.assertIn("uses: actions/cache@v4",source)
                self.assertIn("YORU9_PHOTO_CACHE_DIR: .cache/yoru9-photos",source)
                self.assertIn("hashFiles('travel-stops.json', 'index.html')",source)


if __name__=="__main__":
    unittest.main()
