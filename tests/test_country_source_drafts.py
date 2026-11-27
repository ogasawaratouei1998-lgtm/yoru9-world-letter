import json
import unittest
from country_source_drafts import generate_heritage_drafts
from country_topic_drafts import event_candidates, discover_topics
from country_unesco_source_catalog import collect_sites

DAY="2026-11-27"
SOURCE={"name":"公式観光局","url":"https://tourism.example/events"}
SITES=[
    {"name":"遺産A","sourceUrl":"https://whc.unesco.org/en/list/1/","inscribedYear":1999},
    {"name":"遺産B","sourceUrl":"https://whc.unesco.org/en/list/2/","inscribedYear":2005},
]


def event(**changes):
    return {"@type":"Festival","name":"文化祭","eventStatus":"https://schema.org/EventScheduled",
            "startDate":"2026-11-26","endDate":"2026-11-29",
            "location":{"address":{"addressCountry":"ES"}},**changes}


def html(*events):
    return '<script type="application/ld+json">'+json.dumps({"@graph":events})+'</script>'


class CountryDraftTests(unittest.TestCase):
    def test_official_feed_year_and_two_source_bound_quizzes(self):
        xml=b"<query><row><id_number>1</id_number><site>Site A</site><iso_code>es</iso_code><date_inscribed>1999</date_inscribed></row></query>"
        self.assertEqual(collect_sites(xml)["ES"][0]["inscribedYear"],1999)
        generated=generate_heritage_drafts("スペイン",SITES,DAY)
        self.assertEqual(len(generated["travelDrafts"]),2)
        self.assertEqual(len(generated["quizDrafts"]),2)
        self.assertFalse(generated["publicationEligible"])
        self.assertEqual(generated["quizDrafts"][0]["options"][0],"1999年")

    def test_missing_year_and_duplicate_sources_do_not_invent_quiz(self):
        rows=[{"name":"Site","sourceUrl":"https://whc.unesco.org/en/list/1/"}]*2
        draft=generate_heritage_drafts("スペイン",rows,DAY)
        self.assertEqual(len(draft["travelDrafts"]),1)
        self.assertEqual(draft["quizDrafts"],[])
        self.assertIsNone(generate_heritage_drafts("スペイン",[],DAY)["portraitDraft"])

    def test_unapproved_url_cannot_be_used_for_generated_drafts(self):
        draft=generate_heritage_drafts("スペイン",[{"name":"Site","sourceUrl":"https://whc.unesco.org.evil.example/en/list/1/"}],DAY)
        self.assertIsNone(draft["portraitDraft"])

    def test_only_explicit_scheduled_current_same_country_event(self):
        valid=event()
        invalid=[
            event(eventStatus="https://schema.org/EventCancelled"),
            event(eventStatus=None),
            event(location={"address":{"addressCountry":"FR"}}),
            event(location={}),
            event(endDate="2026-11-26"),
            event(endDate=None),
        ]
        rows=event_candidates(html(valid,*invalid),"ES",SOURCE,DAY,[DAY,"2026-11-28"])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["validFrom"],DAY)
        self.assertEqual(rows[0]["sourceEndDate"],"2026-11-29")
        self.assertFalse(rows[0]["publicationEligible"])

    def test_official_sources_missing_or_unavailable_remain_unfilled(self):
        tasks={"editionDate":DAY,"tasks":[{"countryCode":"ES","missingTopicDates":[DAY],
            "officialTopicSources":[]}]}
        result=discover_topics(tasks,fetch=lambda url:html(event()))
        self.assertEqual(result["countries"][0]["candidates"],[])
        self.assertFalse(result["publicationEligible"])


if __name__=="__main__":
    unittest.main()
