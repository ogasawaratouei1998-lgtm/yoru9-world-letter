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

    def test_preview_job_guard_is_yaml_safe_and_scheduled_in_utc(self):
        preview=(Path(__file__).resolve().parents[1]/
                 ".github/workflows/ai-editorial-preview.yml").read_text(encoding="utf-8")
        guard="github.event_name != 'push' || startsWith(github.event.head_commit.message, 'Local editorial trial: ')"
        # A colon followed by a space cannot appear in a YAML plain scalar.
        # Keep the complete expression in a folded scalar instead.
        self.assertIn("    if: >-\n      "+guard,preview)
        self.assertNotIn("    if: "+guard,preview)
        self.assertIn("- cron: '15 9 * * *'",preview)  # 18:15 JST
        self.assertIn("- cron: '45 10 * * *'",preview)  # 19:45 JST
        self.assertNotIn("timezone:",preview)

    def test_daily_recovery_slots_and_archived_issue_skip(self):
        root=Path(__file__).resolve().parents[1]
        preview=(root/".github/workflows/ai-editorial-preview.yml").read_text(encoding="utf-8")
        for cron in ("15 6 * * *", "15 9 * * *", "45 10 * * *", "15 12 * * *"):
            self.assertIn("- cron: '"+cron+"'",preview)
        self.assertIn('if [ -f "data/archive/$DAY.json" ]; then',preview)
        self.assertIn('ARCHIVED: ${{ steps.edition.outputs.archived }}',preview)
        self.assertIn('elif [ "$ARCHIVED" = true ]; then',preview)
        self.assertIn("- cron: '2 12 * * *'",WORKFLOW)
        health=(root/".github/workflows/publication-health.yml").read_text(encoding="utf-8")
        self.assertIn("No new public edition for ",health)
        self.assertIn("Approved '+previous_day+",health)
        self.assertIn("date<previous_day",health)

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

    def test_internal_ai_first_and_gemini_is_explicit_opt_in(self):
        root=Path(__file__).resolve().parents[1]
        preview=(root/".github/workflows/ai-editorial-preview.yml").read_text(encoding="utf-8")
        self.assertIn("vars.YORU9_ENABLE_GEMINI != 'true'",preview)
        self.assertIn("run: bash run_local_editorial.sh",preview)
        self.assertIn("vars.YORU9_ENABLE_GEMINI == 'true'",preview)
        self.assertEqual(WORKFLOW.count("vars.YORU9_ENABLE_GEMINI == 'true' &&"),2)
        self.assertIn("python publish_approved.py",WORKFLOW)
        from publish_approved import validate_approved
        import json
        approved=json.loads((root/"data/approved/2026-11-23.json").read_text(encoding="utf-8"))
        approved["approvedBy"]="chatgpt-editorial-review"
        validate_approved(approved,"2026-11-23")
        approved["stories"][0]["editorQualityVerified"]=False
        with self.assertRaises(ValueError):
            validate_approved(approved,"2026-11-23")

    def test_explicit_cpu_trial_hands_off_only_via_guarded_main_publisher(self):
        guard=WORKFLOW[WORKFLOW.index("    if: >-"):WORKFLOW.index("    steps:")]
        self.assertIn("github.event.workflow_run.conclusion == 'success'",guard)
        self.assertIn("github.event.workflow_run.head_branch == 'main'",guard)
        self.assertIn("startsWith(github.event.workflow_run.head_commit.message, 'Local editorial trial: ')",guard)
        self.assertIn("validate_approved(payload,day)",WORKFLOW)
        self.assertIn("python check_public_country_release.py",WORKFLOW)
        self.assertLess(WORKFLOW.index("Verify the actual public Pages data"),
                        WORKFLOW.index("Dispatch optional release notification"))

    def test_nightly_status_distinguishes_live_site_from_notification(self):
        self.assertIn("NOTICE_RESULT: ${{ steps.dispatch_notice.outputs.result }}",WORKFLOW)
        for result in ("notice_accepted","notice_not_configured","notice_unconfirmed"):
            self.assertIn("live_verified; "+result,WORKFLOW)
        self.assertIn('if result=="accepted":',WORKFLOW)
        self.assertIn('elif result=="not_configured":',WORKFLOW)

    def test_missing_approved_issue_prefers_latest_valid_review_not_story_count(self):
        self.assertIn('key=lambda p:int(p.parent.name),reverse=True',WORKFLOW)
        self.assertIn('count,source,payload=valid[0]',WORKFLOW)
        self.assertIn('if [ -f "data/archive/$DAY.json" ]; then',WORKFLOW)

if __name__=="__main__":
    unittest.main()
