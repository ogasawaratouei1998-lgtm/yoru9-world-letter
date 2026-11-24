"""Preserve curated nightly issues against stale review artifact replacement."""
from pathlib import Path
import unittest

WORKFLOW=(Path(__file__).resolve().parents[1]/".github/workflows/publish-nightly.yml").read_text(encoding="utf-8")

class WorkflowEditorialPriorityTest(unittest.TestCase):
    def test_committed_approved_issue_wins_even_with_fewer_stories(self):
        self.assertIn('if [ -f "data/approved/$DAY.json" ]; then',WORKFLOW)
        self.assertIn('print("Preserving previously approved editorial issue:"',WORKFLOW)
        self.assertIn('validate_approved(data,day)',WORKFLOW)
        self.assertLess(WORKFLOW.index('if [ -f "data/approved/$DAY.json" ]; then'),
                        WORKFLOW.index('mkdir -p /tmp/yoru9-reviewed'))
        self.assertNotIn('max(valid,key=lambda item:item[0])',WORKFLOW)

    def test_verified_review_uploads_exact_date_only(self):
        preview=(Path(__file__).resolve().parents[1]/
                 ".github/workflows/ai-editorial-preview.yml").read_text(encoding="utf-8")
        self.assertIn("stage_review.py --day",preview)
        self.assertIn("steps.staged.outputs.ready == 'true'",preview)
        self.assertIn("path: ${{ steps.staged.outputs.path }}",preview)
        self.assertNotIn("path: data/approved/*.json",preview)

    def test_preview_handoff_never_runs_duplicate_ai_or_premature_pages(self):
        # Same-day on-demand GitHub push is explicit; ordinary code pushes
        # must not spend AI quota or duplicate a normal scheduled review.
        self.assertEqual(WORKFLOW.count(
            "steps.edition.outputs.exists == 'false' &&"),2)
        self.assertEqual(WORKFLOW.count(
            "startsWith(github.event.head_commit.message, 'Editorial retry on demand: ')"),2)
        self.assertEqual(WORKFLOW.count(
            "github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'"),2)
        # Pages/build steps require a fresh release or a verified need to recover
        # a previously committed edition; preflight must succeed in either case.
        # The final notification step may retry an already published edition;
        # the notifier and Supabase backend both guard duplicate delivery.
        self.assertEqual(WORKFLOW.count(
            "steps.preflight.outputs.deploy == 'true' && success()"),4)
        self.assertIn("- name: Dispatch optional release notification (server must be configured)\n        id: dispatch_notice\n        if: success()",WORKFLOW)
        self.assertIn('echo "published=true" >> "$GITHUB_OUTPUT"',WORKFLOW)
        self.assertIn('echo "published=false" >> "$GITHUB_OUTPUT"',WORKFLOW)

    def test_missing_approved_issue_prefers_latest_valid_review_not_story_count(self):
        self.assertIn('key=lambda p:int(p.parent.name),reverse=True',WORKFLOW)
        self.assertIn('count,source,payload=valid[0]',WORKFLOW)
        self.assertIn('if [ -f "data/archive/$DAY.json" ]; then',WORKFLOW)

if __name__=="__main__":
    unittest.main()
