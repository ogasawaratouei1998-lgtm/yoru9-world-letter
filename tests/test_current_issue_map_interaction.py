"""Regression checks for the mobile current-issue map and country introductions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CurrentIssueMapInteractionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = (ROOT / "index.html").read_text(encoding="utf-8")

    def test_map_is_taller_on_mobile_and_pin_layer_shares_artwork_coordinates(self):
        page = self.page
        self.assertIn(".today-map-canvas{position:relative;width:100%;aspect-ratio:1.8/1", page)
        self.assertIn(".today-map-canvas{aspect-ratio:1.65/1;min-height:190px}", page)
        self.assertIn(".today-map-art{position:absolute;inset:0;width:100%;height:100%;display:block;object-fit:fill}", page)
        self.assertIn(".today-map-pins{position:absolute;inset:0;pointer-events:none}", page)
        self.assertIn("pin.style.left=item.point.x.toFixed(3)+'%'", page)
        self.assertIn("pin.style.top=item.point.y.toFixed(3)+'%'", page)

    def test_pin_and_legend_color_are_identical_for_every_issue_position(self):
        page = self.page
        self.assertIn("const TODAY_MAP_COLORS=Object.freeze([", page)
        self.assertIn("const color=TODAY_MAP_COLORS[i%TODAY_MAP_COLORS.length]", page)
        self.assertIn("pin.style.setProperty('--country-color',color)", page)
        self.assertIn("button.style.setProperty('--country-color',color)", page)
        self.assertIn("background:var(--country-color,#FFF0C9)", page)
        self.assertNotIn(".today-map-pin:nth-child", page)
        self.assertNotIn(".today-map-country:nth-child", page)

    def test_pins_are_accessible_buttons_and_show_a_country_introduction(self):
        page = self.page
        self.assertIn('id="todayMapPins" role="group" aria-label="掲載国のピン"', page)
        self.assertNotIn('id="todayMapPins" aria-hidden="true"', page)
        for token in (
            "const pin=document.createElement('button')",
            "pin.setAttribute('aria-controls','todayMapIntro')",
            "pin.setAttribute('aria-expanded','false')",
            "pin.addEventListener('click',()=>showTodayCountryIntro(item))",
            'id="todayMapIntro" aria-labelledby="todayMapIntroName" aria-live="polite" hidden',
            "function todayCountryIntro(item)",
            "countryRecord(item.code)?.region",
            "$('todayMapIntroBody').textContent=guide?todayCountryIntro(item)+' '+guide.body:todayCountryIntro(item)",
            "$('todayMapIntro').scrollIntoView({block:'nearest'})",
            "function hideTodayCountryIntro()",
            "read.dataset.storyIndex=String(item.indices[0])",
            "openAtlasStory(index)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, page)
        self.assertIn("AR:'南アメリカ南部", page)
        self.assertIn("FR:'ヨーロッパ西部", page)
        self.assertIn("US:'北アメリカ", page)

    def test_iconic_photo_priority_is_consistent_across_countries(self):
        page = self.page
        self.assertIn("const TODAY_COUNTRY_PHOTO_RULES=Object.freeze({", page)
        for landmark in ("イグアスの滝", "エッフェル塔"):
            self.assertIn("['" + landmark + "',100]", page)
        self.assertIn("function countryPhotoPriority(code,photo)", page)
        self.assertIn("['ゴールデンゲートブリッジ',90]", page)
        self.assertIn(".sort((a,b)=>countryPhotoPriority(currentCode,b)-countryPhotoPriority(currentCode,a))", page)
        self.assertIn(".filter(p=>p.asset&&p.url&&p.author&&p.license&&p.place&&p.caption", page)

    def test_country_buttons_still_open_their_news(self):
        page = self.page
        self.assertIn("button.addEventListener('click',()=>openAtlasStory(item.indices[0]))", page)
        self.assertIn("legend.append(button)", page)
        self.assertIn("renderIssueGallery();updateSpotlight();renderTravelSlots();renderTodayMap();", page)


if __name__ == "__main__":
    unittest.main()
