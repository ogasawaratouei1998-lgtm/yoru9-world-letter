import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from country_review_bundle import candidate_identity, cover_native_resolution_problem, make_queue, review_image_url, valid_preview_url, write_bundle

def candidate(name):
    return {"commonsPage": "https://commons.wikimedia.org/wiki/File:" + name,
            "original": "https://upload.wikimedia.org/wikipedia/commons/a/ab/" + name,
            "preview": "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/" + name + "/960px-" + name,
            "metadataChecked": True, "author": "Photographer", "license": "CC BY 4.0",
            "licenseUrl": "https://creativecommons.org/licenses/by/4.0/"}

def row(code, slot, names):
    return {"countryCode": code, "slot": slot, "origin": "existing_draft",
            "candidates": [candidate(n) for n in names]}

class ReviewBundleTests(unittest.TestCase):
    def test_distinct_assignment_and_no_approval(self):
        report = {"results": [row("AA", 0, ["A.jpg"]), row("AA", 1, ["A.jpg", "B.jpg"]),
                              row("AA", 2, ["C.jpg"]), row("BB", 0, ["B.jpg"])]}
        data = {"AA": {"name": "Draft", "status": "pending", "portrait": {"body": "Draft"}},
                "BB": {"name": "Approved", "status": "approved"}}
        queue = make_queue(report, data)
        self.assertEqual(len(queue), 1)
        self.assertTrue(queue[0]["threeDistinctCandidates"])
        self.assertFalse(queue[0]["publicationEligible"])
        self.assertEqual(candidate_identity(queue[0]["slots"][1]["candidate"]), "B.jpg")
        with tempfile.TemporaryDirectory() as tmp:
            s = write_bundle(queue, tmp, 12, fetch=lambda u: b"\xff\xd8test\xff\xd9", sleep_seconds=0)
            self.assertEqual(s["downloadedUnreviewedPreviews"], 3)
            self.assertFalse(s["publicationEligible"])
            index = json.loads((Path(tmp) / "review-index.json").read_text())
            self.assertTrue(all(not slot["visualVerified"] for slot in index["queue"][0]["slots"]))

    def test_review_requests_release_size_cover_and_pins_downloaded_bytes(self):
        report = {"results": [row("AA", s, [str(s) + ".jpg"]) for s in range(3)]}
        candidate = report["results"][0]["candidates"][0]
        candidate["dimensions"] = [4000, 3000]
        candidate["preview"] += "?utm_source=commons"
        self.assertIn("/1280px-", review_image_url(candidate, 0))
        self.assertEqual(review_image_url(candidate, 1), candidate["preview"])
        self.assertEqual(candidate_identity(candidate), "0.jpg")
        data = {"AA": {"name": "Draft", "status": "pending"}}
        queue = make_queue(report, data)
        payload = b"\xff\xd8test\xff\xd9"
        urls = []
        def fetch(url):
            urls.append(url)
            return payload
        with tempfile.TemporaryDirectory() as tmp:
            summary = write_bundle(queue, tmp, 12, fetch=fetch, sleep_seconds=0)
            self.assertEqual(len(urls), 3)
            self.assertIn("/1280px-", urls[0])
            self.assertIn("/960px-", urls[1])
            self.assertEqual(queue[0]["slots"][0]["previewSha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(queue[0]["slots"][0]["downloadedUrl"], urls[0])
            self.assertFalse(summary["publicationEligible"])
            self.assertFalse(queue[0]["slots"][0]["visualVerified"])
        candidate["dimensions"] = [800, 532]
        self.assertEqual(review_image_url(candidate, 0), candidate["preview"])

    def test_extreme_panorama_never_becomes_unbuildable_country_cover(self):
        wide = candidate("Wide.jpg")
        wide["dimensions"] = [4912, 1080]
        normal = candidate("Normal.jpg")
        normal["dimensions"] = [2400, 1600]
        self.assertIn("panorama", cover_native_resolution_problem(wide))
        self.assertIsNone(cover_native_resolution_problem(normal))
        self.assertIn("1000x540", cover_native_resolution_problem({"dimensions": [960, 720]}))
        self.assertIn("Invalid", cover_native_resolution_problem({"dimensions": [True, 720]}))
        self.assertIsNone(cover_native_resolution_problem(candidate("NoDimensions.jpg")))
        data = {"AA": {"name": "Draft", "status": "pending"}}
        result = make_queue({"results": [
            {"countryCode": "AA", "slot": 0, "origin": "existing_draft",
             "candidates": [wide, normal]},
            row("AA", 1, ["FirstStop.jpg"]),
            row("AA", 2, ["SecondStop.jpg"]),
        ]}, data)[0]
        self.assertEqual(candidate_identity(result["slots"][0]["candidate"]), "Normal.jpg")
        self.assertEqual(result["candidateCounts"], [1, 1, 1])
        self.assertEqual(len(result["slots"][0]["visualRejections"]), 1)
        self.assertFalse(result["publicationEligible"])

    def test_latest_malaysia_animal_is_not_cave_and_uzbek_panorama_not_cover(self):
        for code, slot, bad in [
            ("MY", 2, "Blue-throated_Litter_Skink_(Sphenomorphus_cyanolaemus)_female_(15385530980).jpg"),
            ("UZ", 0, "Panorama_of_Registan_Complex_-_Samarkand_-_Uzbekistan_(7480216380).jpg"),
        ]:
            with self.subTest(code=code):
                data = {code: {"name": code, "status": "pending"}}
                records = [row(code, i, [str(i)+".jpg"]) for i in range(3)]
                records[slot] = row(code, slot, [bad, "Alternate.jpg"])
                queued = make_queue({"results": records}, data)[0]
                self.assertEqual(candidate_identity(queued["slots"][slot]["candidate"]), "Alternate.jpg")
                self.assertEqual(len(queued["slots"][slot]["visualRejections"]), 1)
                self.assertTrue(queued["threeDistinctCandidates"])
                self.assertFalse(queued["publicationEligible"])

    def test_reused_original_or_mismatched_metadata_is_not_ready(self):
        self.assertFalse(valid_preview_url("https://upload.wikimedia.org.evil.example/wikipedia/commons/a/ab/A.jpg"))
        self.assertFalse(valid_preview_url("https://upload.wikimedia.org:8080/wikipedia/commons/a/ab/A.jpg"))
        c = candidate("A.jpg")
        c["preview"] = candidate("B.jpg")["preview"]
        self.assertIsNone(candidate_identity(c))
        data = {"AA": {"name": "Draft", "status": "pending"}}
        queue = make_queue({"results": [row("AA", s, ["A.jpg"]) for s in range(3)]}, data)
        self.assertFalse(queue[0]["threeDistinctCandidates"])

    def test_throttling_preserves_unreviewed_status(self):
        data = {"AA": {"name": "Draft", "status": "pending"}}
        queue = make_queue({"results": [row("AA", i, [str(i)+".jpg"]) for i in range(3)]}, data)
        def throttle(url):
            raise HTTPError(url, 429, "Too many requests", {}, None)
        with tempfile.TemporaryDirectory() as tmp:
            s = write_bundle(queue, tmp, 12, fetch=throttle, sleep_seconds=0)
            self.assertEqual(s["downloadedUnreviewedPreviews"], 0)
            self.assertEqual(queue[0]["slots"][1]["previewStatus"], "rate_limited_deferred")

    def test_visual_rejection_is_scoped_and_next_distinct_original_is_used(self):
        data = {"KE": {"name": "Kenya", "status": "pending"}}
        report = {"results": [
            row("KE", 0, ["Cover.jpg"]),
            row("KE", 1, ["Lamu_Pharmacy.jpg", "Lamu%20Pharmacy.jpg", "Old_Town.jpg"]),
            row("KE", 2, ["Fort.jpg"]),
        ]}
        queue = make_queue(report, data)
        slot = queue[0]["slots"][1]
        self.assertEqual(candidate_identity(slot["candidate"]), "Old Town.jpg")
        self.assertEqual(len(slot["visualRejections"]), 1)
        self.assertEqual(slot["visualRejections"][0]["originalIdentity"], "Lamu Pharmacy.jpg")
        self.assertFalse(slot["visualVerified"])
        self.assertFalse(queue[0]["publicationEligible"])
        report["results"][1] = row("KE", 1, ["Lamu_Pharmacy.jpg"])
        self.assertFalse(make_queue(report, data)[0]["threeDistinctCandidates"])
        report["results"][0] = row("KE", 0, ["Lamu_Pharmacy.jpg"])
        report["results"][1] = row("KE", 1, ["Old_Town.jpg"])
        self.assertFalse(make_queue(report, data)[0]["threeDistinctCandidates"])
        report["results"][0] = row("KE", 0, ["Cover.jpg"])
        self.assertTrue(make_queue(report, data)[0]["threeDistinctCandidates"])

    def test_visual_rejections_record_costa_rica_panorama_failures(self):
        data = {"CR": {"name": "Costa Rica", "status": "pending"}}
        report = {"results": [
            row("CR", 0, ["1999_casona_santa_rosa_Panorama.jpg", "Forest.jpg"]),
            row("CR", 1, ["Santa_Rosa_guanacaste.jpg", "Conservation_Area.jpg"]),
            row("CR", 2, ["Spheres.jpg"]),
        ]}
        queue = make_queue(report, data)
        self.assertEqual(queue[0]["candidateCounts"], [1, 1, 1])
        self.assertEqual([len(s["visualRejections"]) for s in queue[0]["slots"]], [1, 1, 0])
        self.assertTrue(queue[0]["threeDistinctCandidates"])
        self.assertFalse(queue[0]["publicationEligible"])

    def test_second_pharmacy_and_wrong_country_cover_are_not_selected(self):
        data = {"KE": {"name": "Kenya", "status": "pending"},
                "MU": {"name": "Mauritius", "status": "pending"}}
        report = {"results": [
            row("KE", 0, ["Cover.jpg"]),
            row("KE", 1, ["Lamu_Pharmacy2021.jpg", "Old_Town.jpg"]),
            row("KE", 2, ["Fort.jpg"]),
            row("MU", 0, ["Hausdülmen_--_2014_--_5879.jpg", "Port_Louis.jpg"]),
            row("MU", 1, ["Aapravasi.jpg"]),
            row("MU", 2, ["Le_Morne.jpg"]),
        ]}
        queue = {item["code"]: item for item in make_queue(report, data)}
        self.assertEqual(candidate_identity(queue["KE"]["slots"][1]["candidate"]), "Old Town.jpg")
        self.assertEqual(candidate_identity(queue["MU"]["slots"][0]["candidate"]), "Port Louis.jpg")
        self.assertTrue(all(not item["publicationEligible"] for item in queue.values()))

    def test_reviewed_wrong_country_and_non_site_images_are_replaced(self):
        cases = [
            ("ZA", 0, "Cape_Town_(ZA),_Table_Mountain_--_2024_--_2821.jpg"),
            ("ZA", 1, "Robben_Island,_South_Africa_(3263091144).jpg"),
            ("ZA", 2, "Cape_Town_(ZA),_Table_Mountain_--_2024_--_2822.jpg"),
            ("BW", 0, "Anhinga_rufa_-Chobe_River_front,_Botswana-8.jpg"),
            ("HN", 0, "Comayagua_Cathedral.jpg"),
            ("KE", 0, "Lamu_Pharmacy2021.jpg"),
            ("KZ", 2, "Tamgaly-Tas_Petroglyphs.JPG"),
            ("MY", 2, "Ongoing_Repairs_after_storm_of_the_previous_day_(15385239799).jpg"),
            ("UZ", 0, 'Memorial_complex_"Registan"_in_Samarkand_(10).jpg'),
            ("KE", 0, "Lamu_Pharmacy.jpg"),
            ("BD", 1, "A_view_from_the_Mosque_(8540808429).jpg"),
            ("IQ", 1, "Assur_stuck.jpg"),
            ("LB", 0, "The_landscape_of_Lebanon_with_its_famous_tree_cedar_of_Lebanon_(FL63289561).jpg"),
            ("LB", 2, "Lebanon_mountains_from_near_Maqial_el_Qalaa.jpg"),
            ("LY", 0, "The_Romantic_Landscape_-_geograph.org.uk_-_1803291.jpg"),
            ("MM", 2, "Hanlin_-_Pyu_Ancient_City.JPG"),
            ("MU", 0, "Landscape_near_Les_Mariannes,_Mauritius,_2007-09-09.jpg"),
            ("MU", 1, "Aapravasi_ghat_museum,_Port_Louis,_Mauritius.jpg"),
            ("NE", 0, "Aso_Rock_52_-_landscape_in_Abuja,_Nigeria_(2026).jpg"),
        ]
        for code, slot, rejected in cases:
            with self.subTest(code=code, slot=slot):
                data = {code: {"name": code, "status": "pending"}}
                records = [row(code, i, [str(i) + ".jpg"]) for i in range(3)]
                records[slot] = row(code, slot, [rejected, "Alternative.jpg"])
                result = make_queue({"results": records}, data)[0]
                self.assertTrue(result["threeDistinctCandidates"])
                self.assertEqual(candidate_identity(result["slots"][slot]["candidate"]), "Alternative.jpg")
                self.assertEqual(len(result["slots"][slot]["visualRejections"]), 1)
                self.assertFalse(result["publicationEligible"])
