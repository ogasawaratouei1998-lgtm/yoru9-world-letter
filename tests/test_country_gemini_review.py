"""Offline, no API calls: fail-closed review contract."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from country_gemini_review import (heritage_positions,strict_license,official_url,
    quote_matches,construct_record,packet_for,validate_packet,review_once,MODEL)
from country_review_apply import digest
from test_country_review_bundle import candidate

DAY="2026-11-28"
URL="https://whc.unesco.org/en/list/1399/"
BODY="The historic port town of Levuka is a significant trading centre with colonial buildings and local architectural traditions. "*3
QUOTE="historic port town of Levuka"
META="Historic port town of Levuka in Fiji"
def fixture():
    old={"status":"pending","name":"フィジー","portrait":{"sourceName":"UNESCO","sourceUrl":URL,"lead":"下書き","body":"下書き"},
         "travelDrafts":[{"sourceName":"UNESCO","sourceUrl":URL},{"sourceName":"UNESCO","sourceUrl":URL}],
         "travelStops":{},"portraitPhotos":[],"quiz":[],"highlights":[]}
    photos=[]
    for i in range(3):
        a={**candidate(str(i)+".jpg"),"description":META,"file":"File:"+str(i)+".jpg"}
        photos.append({"slot":i,"candidate":a,"downloadedUrl":a["preview"],"sha256":str(i+1)*64})
    evidence={"countryCode":"FJ","editionDate":DAY,"baseDigest":digest(old),"portraitDraft":old["portrait"],
              "travelDrafts":old["travelDrafts"],"sourceUrls":[URL]*3,"sources":{URL.rstrip("/"):{
                "url":URL,"text":BODY,"sha256":hashlib.sha256(BODY.encode()).hexdigest()}},
              "sites":[{"name":"Levuka","latitude":-17.68,"longitude":178.83,"countryCode":"FJ"}]*2,"images":photos}
    response={"verdict":"PASS","portrait":{"lead":"レブカの歴史を資料から読み解く","body":"港町の歴史と文化交流を考える文章です。"*9,
              "facts":["港町の文化と交易の記録","地域社会に残る建物の歴史"],"sourceQuote":QUOTE},
              "photos":[{"slot":i,"siteIndex":max(0,i-1),"place":"レブカ歴史港町","caption":"レブカの歴史的な港町の景観",
                         "metadataQuote":META,"sourceQuote":QUOTE} for i in range(3)],
              "travel":[{"paragraphs":["港町の建物や交易の歴史を公式資料から読み解く文章です。"*5]*2,
                        "sourceQuote":QUOTE,"quizQuote":QUOTE,"quiz":{"question":"この港町が伝える歴史は何でしょうか",
                          "options":["交易","氷河","砂漠"],"answer":0,"fact":"港町の建物は交易と文化交流の歴史を示す資料です。",
                          "quip":"写真から歴史の手がかりを読み取ろう。"}} for _ in range(2)]}
    return old,evidence,response

class GeminiCountryReviewTest(unittest.TestCase):
    def test_fixed_model_and_license_url_exact(self):
        self.assertEqual(MODEL,"gemini-3.5-flash-lite")
        self.assertTrue(strict_license(candidate("x.jpg")))
        self.assertFalse(strict_license({**candidate("x.jpg"),"licenseUrl":"https://creativecommons.org/licenses/by-nc/4.0/"}))
        self.assertTrue(official_url(URL))
        self.assertFalse(official_url("https://whc.unesco.org.evil.test/en/list/1399/"))
        self.assertFalse(quote_matches("invented source quote",BODY))
    def test_country_bound_official_coordinates(self):
        xml=b"<root><row><id_number>1399</id_number><site>Levuka</site><iso_code>fj</iso_code><latitude>-17.68</latitude><longitude>178.83</longitude></row></root>"
        self.assertIn("1399",heritage_positions(xml,"FJ"))
        self.assertEqual(heritage_positions(xml,"MW"),{})
    def test_reconstruct_exact_record_and_reject_wrong_evidence(self):
        old,e,r=fixture()
        new,proof=construct_record(old,e,r,"FJ",DAY)
        self.assertEqual(new["status"],"approved")
        self.assertEqual(len(proof),3)
        self.assertEqual(len(new["quiz"]),2)
        self.assertNotIn("travelDrafts",new)
        self.assertEqual(new["highlights"],old["highlights"])
        for bad in ({**r,"verdict":"DEFER"},{**r,"photos":[{**r["photos"][0],"metadataQuote":"unrelated imaginary place"},*r["photos"][1:]]},
                    {**r,"photos":[r["photos"][0],{**r["photos"][1],"siteIndex":1},r["photos"][2]]}):
            with self.assertRaises(ValueError):construct_record(old,e,bad,"FJ",DAY)
        with self.assertRaises(ValueError):construct_record(old,e,r,"MW",DAY)
        packet=packet_for(old,e,r,"FJ",DAY)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):validate_packet(old,packet,"FJ",DAY,Path(td))
            with self.assertRaises(ValueError):validate_packet(old,{**packet,"recordDigest":"bad"},"FJ",DAY,Path(td))
    def test_workflow_only_existing_opt_in_and_single_call(self):
        root=Path(__file__).resolve().parents[1]
        w=(root/".github/workflows/research-article-countries.yml").read_text()
        self.assertIn("vars.YORU9_ENABLE_GEMINI == 'true'",w)
        self.assertIn("secrets.GEMINI_API_KEY",w)
        self.assertIn("python country_gemini_review.py",w)
        self.assertIn("contents: read",w)

    def test_previous_accepted_country_does_not_starve_next_or_repeat_api(self):
        import json
        from country_article_recovery import atomic_json
        old,e,r=fixture()
        mw={**old,"name":"マラウイ"}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);prior=root/"prior";work=root/"work"
            atomic_json(root/"country-content.json",{"countries":{"FJ":old,"MW":mw}})
            atomic_json(work/"photo-review"/"article-preview-checkpoint.json",{"editionDate":DAY})
            previous=prior/"123"/"gemini-review"/"FJ"
            previous.mkdir(parents=True)
            atomic_json(previous/"packet.json",{"countryCode":"FJ"})
            for i in range(3):(previous/("FJ-"+str(i)+".jpg")).write_bytes(b"fixture")
            call=Mock(return_value={"verdict":"DEFER"})
            evidence=Mock(return_value={"fixture":True})
            def validate(old,packet,code,day,folder):
                if code!="FJ" or packet.get("countryCode")!="FJ":raise ValueError("no packet")
                return {},{}
            with patch("country_gemini_review.validate_packet",side_effect=validate),patch("country_gemini_review.image_inputs",return_value=[]):
                status=review_once(root,{"stories":[{"country":"FJ"},{"country":"MW"}]},DAY,work,prior,"key",call=call,make_evidence=evidence)
            self.assertEqual(status,"EVIDENCE_OR_REVIEW_DEFERRED")
            call.assert_called_once()
            self.assertTrue((work/"gemini-review"/"FJ"/"packet.json").is_file())
            self.assertTrue((work/"gemini-review"/"MW"/"attempt.json").is_file())
