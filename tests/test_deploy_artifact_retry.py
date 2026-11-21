"""GitHub Pages metadata indexing is eventually consistent, not a source failure."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class GitHubPagesArtifactIndexingTest(unittest.TestCase):
    def test_pages_deploy_retries_only_after_first_artifact_lookup_failure(self):
        workflow=(ROOT/".github/workflows/deploy-site.yml").read_text(encoding="utf-8")
        first=workflow.index("      - name: Deploy to GitHub Pages\n")
        second=workflow.index("      - name: Retry GitHub Pages deployment after indexing delay\n")
        verify=workflow.index("      - name: Verify published country portraits and tourist microtravel\n")
        self.assertLess(first,second)
        self.assertLess(second,verify)
        self.assertEqual(workflow.count("uses: actions/deploy-pages@v4"),2)
        first_block=workflow[first:second]
        second_block=workflow[second:verify]
        self.assertIn("id: deployment",first_block)
        self.assertIn("continue-on-error: true",first_block)
        self.assertIn("if: steps.deployment.outcome == 'failure'",first_block)
        self.assertIn("sleep 20",first_block)
        self.assertIn("id: deployment_retry",second_block)
        self.assertIn("if: steps.deployment.outcome == 'failure'",second_block)
        self.assertNotIn("continue-on-error:",second_block)

    def test_final_publication_check_uses_successful_attempt_or_fails_closed(self):
        workflow=(ROOT/".github/workflows/deploy-site.yml").read_text(encoding="utf-8")
        final=workflow.split("      - name: Verify published country portraits and tourist microtravel",1)[1]
        self.assertIn("steps.deployment_retry.outputs.page_url || steps.deployment.outputs.page_url",final)
        self.assertIn("PUBLISHED_SITE:?GitHub Pages did not return a deployment URL",final)
        self.assertIn("python check_public_country_release.py",final)
        before=workflow.split("      - name: Deploy to GitHub Pages\n",1)[0]
        for step in ("Validate release rules","Create safe public site bundle",
                     "Validate every published reader feature and licensed image",
                     "Wait for GitHub Pages artifact"):
            self.assertIn(step,before)
        # Failed source/country/media quality MUST NOT enter retry deployment.
        self.assertNotIn("continue-on-error: true",before)


if __name__=="__main__":
    unittest.main()
