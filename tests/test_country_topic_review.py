"""Official country-topic verification cannot turn speculative or altered copy into publication."""
import json
import tempfile
import unittest
from pathlib import Path
from country_topic_drafts import event_candidates
from country_topic_review import review, validated_topic, second_read

DAY="2026-11-28"
SOURCE={"name":"Official cultural agency","url":"https://example.org/culture"}
EVENT={"@type":"Festival","name":"Winter Festival","eventStatus":"https://schema.org/EventScheduled",
       "startDate":DAY,"endDate":"2026-11-29","location":{"address":{"addressCountry":"BE"}}}
OLD={"name":"ベルギー","status":"approved","highlights":[],"portraitPhotos":[]}
def page(event=EVENT,visible=True):
    return ("<h1>Winter Festival</h1>" if visible else "")+'<script type="application/ld+json">'+json.dumps(event)+'</script>'
def candidate():
    return event_candidates(page(),"BE",SOURCE,DAY,[DAY])[0]

class CountryTopicReviewTest(unittest.TestCase):
    def test_second_read_rejects_cancellation_wrong_country_dates_and_generic_event(self):
        for altered in ({"eventStatus":"https://schema.org/EventCancelled"},
                        {"location":{"address":{"addressCountry":"FR"}}},
                        {"endDate":"2026-11-30"},{"@type":"Event"}):
            self.assertIsNone(second_read(page({**EVENT,**altered}),"BE",SOURCE,DAY,[DAY],candidate()))
        self.assertIsNone(second_read(page(visible=False),"BE",SOURCE,DAY,[DAY],candidate()))

    def test_actual_second_fetch_and_exact_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"country-content.json").write_text(json.dumps({"countries":{"BE":OLD}}))
            (root/"country-highlight-sources.json").write_text(json.dumps({"sources":{"BE":[SOURCE]}}))
            tasks={"editionDate":DAY,"tasks":[{"countryCode":"BE"}]}
            draft={"editionDate":DAY,"countries":[{"countryCode":"BE","candidates":[{**candidate(),"body":"invented"}]}]}
            seen=[]
            def fetch(url):
                seen.append(url)
                return page()
            report=review(root,DAY,tasks,draft,fetch=fetch)
            self.assertEqual(seen,[SOURCE["url"]])
            record=report["records"]["BE"]
            updated=validated_topic(OLD,record,"BE",DAY,[SOURCE])
            self.assertNotEqual(updated["highlights"][0]["body"],"invented")
            self.assertEqual({k:v for k,v in updated.items() if k!="highlights"},
                             {k:v for k,v in OLD.items() if k!="highlights"})
            for old,changed,code,day in [(OLD,{**record,"topic":{**record["topic"],"body":"invented"}},"BE",DAY),
                (updated,record,"BE",DAY),(OLD,record,"FR",DAY),(OLD,record,"BE","2026-11-29")]:
                with self.assertRaises(ValueError):
                    validated_topic(old,changed,code,day,[SOURCE])
            self.assertEqual(review(root,DAY,tasks,draft,fetch=lambda _:page(visible=False))["records"],{})
            self.assertEqual(review(root,DAY,tasks,draft,fetch=lambda _:page({**EVENT,"eventStatus":"EventCancelled"}))["records"],{})

    def test_pending_country_and_unregistered_source_never_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"country-content.json").write_text(json.dumps({"countries":{"BE":{**OLD,"status":"pending"}}}))
            (root/"country-highlight-sources.json").write_text(json.dumps({"sources":{"BE":[SOURCE]}}))
            tasks={"editionDate":DAY,"tasks":[{"countryCode":"BE"}]}
            draft={"editionDate":DAY,"countries":[{"countryCode":"BE","candidates":[candidate()]}]}
            def prohibited(_):raise AssertionError("unexpected request")
            self.assertEqual(review(root,DAY,tasks,draft,fetch=prohibited)["records"],{})
            (root/"country-content.json").write_text(json.dumps({"countries":{"BE":OLD}}))
            draft["countries"][0]["candidates"][0]["sourceUrl"]="https://unregistered.example"
            self.assertEqual(review(root,DAY,tasks,draft,fetch=prohibited)["records"],{})
