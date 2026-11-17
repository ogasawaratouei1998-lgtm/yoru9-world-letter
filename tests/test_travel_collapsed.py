"""Regression checks for opt-in travel panels on the nightly and monthly reader."""
from pathlib import Path
import unittest


HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")


class TravelDefaultCollapsedTests(unittest.TestCase):
    def test_daily_story_travel_starts_closed(self):
        self.assertIn('aria-expanded="false" aria-controls="travel-panel-', HTML)
        self.assertIn('class="travel-panel" id="travel-panel-', HTML)
        self.assertIn("""'" hidden></div>';""", HTML)

    def test_monthly_story_travel_starts_closed(self):
        self.assertIn('aria-expanded="false" aria-controls="month-travel-', HTML)
        self.assertIn('class="travel-panel" id="month-travel-', HTML)
        self.assertIn("INITIAL_MONTHLY_COLLAPSED", HTML)

    def test_reopening_ios_app_closes_all_optional_travel(self):
        self.assertIn("function closeOptionalTravelPanels()", HTML)
        self.assertIn("document.querySelectorAll('.travel-slot').forEach", HTML)
        self.assertIn("panel.hidden=true;\n  panel.replaceChildren();", HTML)
        self.assertIn("control.setAttribute('aria-expanded','false');", HTML)
        self.assertIn("closeOptionalTravelPanels();\n if(!navigator.onLine)return;", HTML)

    def test_monthly_article_does_not_programmatically_expand_travel(self):
        self.assertNotIn("if(button&&button.getAttribute('aria-expanded')==='false')button.click();", HTML)


if __name__ == "__main__":
    unittest.main()
