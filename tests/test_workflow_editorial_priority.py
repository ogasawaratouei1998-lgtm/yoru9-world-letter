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

    def test_missing_approved_issue_prefers_latest_valid_review_not_story_count(self):
        self.assertIn('key=lambda p:int(p.parent.name),reverse=True',WORKFLOW)
        self.assertIn('count,source,payload=valid[0]',WORKFLOW)
        self.assertIn('if [ -f "data/archive/$DAY.json" ]; then',WORKFLOW)

if __name__=="__main__":
    unittest.main()
