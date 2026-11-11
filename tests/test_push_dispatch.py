import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from send_release_notice import notice_for,dispatch
JST=ZoneInfo("Asia/Tokyo")

class PushDispatchTest(unittest.TestCase):
    def test_unpublished_cannot_send(self):
        self.assertIsNone(notice_for({"status":"approved","editionDate":"2026-11-11","stories":[{}]*5},
                      datetime(2026,11,11,21,40,tzinfo=JST)))
    def test_past_edition_cannot_send(self):
        self.assertIsNone(notice_for({"status":"published","editionDate":"2026-11-10","stories":[{}]*5},
                      datetime(2026,11,11,21,40,tzinfo=JST)))
    def test_five_published_special_story_notice(self):
        p=notice_for({"status":"published","editionDate":"2026-11-11","editionType":"special","stories":[{}]*5},
                     datetime(2026,11,11,21,40,tzinfo=JST))
        self.assertEqual(p["editionDate"],"2026-11-11")
        self.assertIn("特集",p["body"])
    def test_missing_backend_does_not_send(self):
        self.assertFalse(dispatch("","",{"editionDate":"2026-11-11"}))
    def test_insecure_dispatch_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            dispatch("http://example.org/dispatch","secret",{"editionDate":"2026-11-11"})

if __name__=="__main__":unittest.main()
