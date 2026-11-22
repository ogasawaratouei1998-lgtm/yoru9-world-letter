"""Regression checks for the quota-efficient A-editor discovery/refill queue."""
import unittest
import inspect
import auto_editorial as editorial


def group(group_id, title, *urls):
    return {"groupId": group_id,
            "articles": [{"title": title, "url": url} for url in urls]}


class NeverRepeatedSourceGroupTests(unittest.TestCase):
    def test_refill_does_not_repeat_empty_or_failed_draft_calls(self):
        groups = [
            group(1, "A personal mistake with a big reversal", "https://news-a.example/1"),
            group(2, "A work mix-up", "https://news-b.example/2"),
            group(3, "A sports blunder", "https://news-c.example/3"),
            group(4, "Another work mistake", "https://news-d.example/4"),
        ]
        # Group 1 was in the initial model request and group 3 produced
        # zero drafts in a focused retry. Neither can be re-prompted.
        result = editorial.select_untried_source_groups(
            groups, {1, 3}, {"https://news-b.example/2"})
        self.assertEqual([item["groupId"] for item in result], [4])

    def test_reused_article_in_another_group_cannot_circumvent_gate(self):
        same_url = "https://local.example/the-event"
        groups = [
            group(1, "Someone made a serious mistake", same_url),
            group(2, "Apparently independent incident", same_url, "https://other.example/2"),
            group(3, "Another original article", "https://new.example/3"),
        ]
        result = editorial.select_untried_source_groups(groups, {1}, set())
        self.assertEqual([item["groupId"] for item in result], [3])
        # The duplicate article is blocked solely by the attempted publisher
        # URL; a missing draft/verification URL never erases that history.
        second = editorial.select_untried_source_groups(groups, {1}, {same_url})
        self.assertEqual([item["groupId"] for item in second], [3])

    def test_three_group_batches_keep_each_publisher_provenance(self):
        urls = [f"https://publisher-{i}.example/real-news" for i in range(3)]
        groups = [group(i + 1, "Human error and documented consequence", url)
                  for i, url in enumerate(urls)]
        drafts = [{"sourceUrl": url, "verificationUrls": [url]} for url in urls]
        cross = {"sourceUrl": urls[0], "verificationUrls": [urls[0], urls[2]]}
        selected = editorial.source_bound_batch_drafts(
            {"stories": [cross, *drafts]}, groups)
        self.assertEqual(selected, drafts)
        self.assertEqual(editorial.MAX_FOCUSED_DRAFT_GROUPS, 3)

    def test_initial_context_is_focused_and_source_pool_is_large(self):
        self.assertLessEqual(editorial.PRIMARY_EDITORIAL_GROUPS, 8)
        self.assertGreaterEqual(editorial.EDITORIAL_SHORTLIST_LIMIT, 48)
        self.assertGreater(editorial.EDITORIAL_SHORTLIST_LIMIT,
                           editorial.PRIMARY_EDITORIAL_GROUPS)

    def test_independent_editor_and_publication_requirements_still_apply(self):
        source = inspect.getsource(editorial.main)
        self.assertIn('attempted_group_ids.update(group["groupId"] for group in batch)', source)
        self.assertIn("select_untried_source_groups(", source)
        for check in (
            "source_bound_batch_drafts(response,batch)",
            "trusted_original_domain(urls[0])",
            "headline_fidelity_risk(story,evidence)",
            "independent_editorial_quality_passed(audit)",
            "validate_approved(payload,day)",
        ):
            self.assertIn(check, source)


if __name__ == "__main__":
    unittest.main()
