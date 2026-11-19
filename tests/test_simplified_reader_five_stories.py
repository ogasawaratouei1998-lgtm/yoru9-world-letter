"""Requested November 19 reader simplification and five-item nightly ceiling."""
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from publish_approved import publish, validate_approved
from test_publish import fixture

ROOT=Path(__file__).resolve().parents[1]


def synthetic_issue(count):
    issue=fixture("2026-11-19")
    seed=issue["stories"][0]
    issue["stories"]=[]
    for i in range(count):
        item=dict(seed)
        item["id"]=f"verified-case-{i}"
        item["title"]=f"Verified case number {i}: genuinely surprising news"
        item["sourceUrl"]=f"https://original{i}.example.org/report"
        item["verificationUrls"]=[
            item["sourceUrl"],f"https://second{i}.example.net/report"]
        item["reported"]="2026-11-19"
        issue["stories"].append(item)
    return issue


class SimplifiedReaderTest(unittest.TestCase):
    def test_no_past_edition_reader_or_world_map_exists_in_public_ui(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        for forbidden in (
            "過去の配信を読む","世界地図を見る",
            'id="archiveExtras"','id="mapExtras"','id="archiveSelect"',
            'id="worldMap"','id="coverWorldMap"','id="coverWorldLink"',
            'id="worldInvitation"','id="atlasPreview"','id="coverMapPins"',
            "openWorldExplorer(","loadWorldBoundaries()","loadArchives()",
            "archiveMenu","archiveStatus",
        ):
            self.assertNotIn(forbidden,page,forbidden)
        for required in (
            'id="issueGallery"','id="articleReader"',
            'id="todayMapSection"','id="notificationSection"',
            'data-travel-slot="0"','id="releaseStatus"',
            "function loadPublishedMonthDates()",
            "function renderIssueGallery()",
        ):
            self.assertIn(required,page,required)

    def test_live_reader_accepts_five_and_gallery_follows_actual_story_count(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("x.stories.length<=5",page)
        self.assertIn("for(const [index,story] of edition.stories.entries())",page)
        self.assertIn("edition.stories.length+'コマ劇場'",page)
        self.assertIn("String(d.length)",page)
        self.assertNotIn("renderWorld();",page)


class FiveStoryPublicationTest(unittest.TestCase):
    def test_publish_all_available_count_one_through_five(self):
        for count in (1,2,3,4,5):
            with self.subTest(count=count),TemporaryDirectory() as tmp:
                root=Path(tmp)
                (root/"data/approved").mkdir(parents=True)
                (root/"data/archive").mkdir(parents=True)
                (root/"data/archive/index.json").write_text('{"issues":[]}')
                (root/"data/current.json").write_text(
                    '{"status":"demo","stories":[]}')
                approved=synthetic_issue(count)
                result=validate_approved(approved,"2026-11-19")
                self.assertEqual(len(result["stories"]),count)
                (root/"data/approved/2026-11-19.json").write_text(
                    json.dumps(approved,ensure_ascii=False),encoding="utf-8")
                self.assertTrue(publish(root,datetime.fromisoformat(
                    "2026-11-19T21:30:00+09:00")))
                live=json.loads((root/"data/current.json").read_text())
                archived=json.loads(
                    (root/"data/archive/2026-11-19.json").read_text())
                self.assertEqual(live,archived)
                self.assertEqual(len(live["stories"]),count)
                self.assertEqual(len({
                    s["id"] for s in live["stories"]}),count)

    def test_zero_and_six_stories_never_publish(self):
        for count in (0,6):
            with self.subTest(count=count):
                with self.assertRaisesRegex(ValueError,"1〜5本"):
                    validate_approved(synthetic_issue(count),"2026-11-19")

    def test_independent_comedy_editor_gate_is_not_relaxed(self):
        data=synthetic_issue(5)
        data["approvedBy"]="automated-two-stage-review"
        with self.assertRaises(ValueError):
            validate_approved(data,"2026-11-19")

    def test_legacy_three_story_limit_and_special_issue_stay_unchanged(self):
        four=synthetic_issue(4)
        four["editionDate"]="2026-11-18"
        with self.assertRaisesRegex(ValueError,"1〜3本"):
            validate_approved(four,"2026-11-18")


if __name__=="__main__":
    unittest.main()
