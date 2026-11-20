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
            "$('todayMapIntroBody').textContent=guide",
            "  ?guide.body",
            ":todayCountryIntro(item)+' 観光名所を案内する",
            "currentCountryHighlight(all,currentCode)",
            "COUNTRY PORTRAIT · 国の魅力",
            "$('todayMapIntro').scrollIntoView({block:'start'})",
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
        self.assertIn(".filter(p=>(p.asset||p.remoteOnly)&&p.url&&p.author&&p.license&&p.place&&p.caption", page)

    def test_country_hero_and_travel_postcard_use_distinct_assets(self):
        import json
        import re
        page = self.page
        match = re.search(r"const TODAY_COUNTRY_PHOTOS=Object.freeze\((\{.*?\})\);", page)
        self.assertIsNotNone(match)
        heroes = json.loads(match.group(1))
        catalog = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        countries = {"AR": "アルゼンチン", "FR": "フランス", "US": "アメリカ合衆国"}
        hero_assets = {
            "AR": "assets/travel/iguazu-rainbow-cover.jpg",
            "FR": "assets/travel/mont-saint-michel-sunset-cover.jpg",
            "US": "assets/travel/golden-gate-sunset-cover.jpg",
        }
        for code, country in countries.items():
            with self.subTest(country=country):
                hero = next(p for p in heroes[code] if p["asset"] == hero_assets[code])
                self.assertEqual(heroes[code][0]["asset"], hero["asset"])
                self.assertTrue(hero["url"].startswith("https://thumb.wikimedia.org/"))
                matching = [p for p in catalog.values()
                            if p.get("country") == country and
                            p.get("photoAsset") == hero["asset"]]
                self.assertEqual(len(matching), 1)
                self.assertIs(matching[0].get("coverOnly"), True)
                self.assertTrue(matching[0]["photoPage"].startswith(
                    "https://commons.wikimedia.org/wiki/File:"))
                self.assertTrue(matching[0]["licenseUrl"].startswith(
                    "https://creativecommons.org/licenses/"))
                alternatives = [p for p in catalog.values()
                                if p.get("country") == country and
                                p.get("photoAsset") != hero["asset"]]
                self.assertGreaterEqual(len({p["photoAsset"] for p in alternatives}), 2,
                    "Not enough different licensed travel photos: " + country)
        self.assertIn("function conflictsWithCountryCover(stop)", page)
        self.assertIn("!conflictsWithCountryCover(s)", page)
        self.assertIn("displayedCountryCoverAssets.set(currentCode,chosen.asset||'')", page)

    def test_featured_country_photo_is_prominent_on_narrow_phones(self):
        page = self.page
        self.assertIn("#atlasHero .today-map-intro{margin-left:-12px;margin-right:-12px;", page)
        self.assertIn("#atlasHero .today-map-intro-photo img{aspect-ratio:16/10;", page)
        self.assertIn("max-width:calc(100% + 24px)", page)
        self.assertIn("displayedCountryCoverAssets.set(currentCode,chosen.asset||'')", page)
        self.assertIn("!conflictsWithCountryCover(s)", page)

    def test_country_buttons_launch_passport_game_not_the_article(self):
        page = self.page
        game = (ROOT / "world-passport.js").read_text(encoding="utf-8")
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        bundle = (ROOT / "build_site.py").read_text(encoding="utf-8")
        self.assertIn('id="todayCountryQuiz"', page)
        self.assertIn('id="todayQuizChoices"', page)
        self.assertIn('id="todayQuizPassport"', page)
        self.assertIn('world-passport.js', page)
        self.assertIn("button.addEventListener('click',()=>startWorldPassport(item))", page)
        self.assertNotIn("button.addEventListener('click',()=>openAtlasStory(item.indices[0]))", page)
        self.assertIn("pin.addEventListener('click',()=>showTodayCountryIntro(item))", page)
        self.assertIn("legend.append(button)", page)
        self.assertIn("renderIssueGallery();updateSpotlight();renderTravelSlots();renderTodayMap();", page)
        self.assertIn("WORLD_PASSPORT_QUIZZES", game)
        self.assertIn("AIツッコミ（創作の冗談）", game)
        self.assertIn("passportQuizQuestions(item)", game)
        self.assertIn("persistWorldPassport()", game)
        self.assertIn("world-passport.js", bundle)
        self.assertIn("world-passport.js", worker)

    def test_passport_correct_answer_photos_match_licensed_manifest(self):
        import json
        import re
        game = (ROOT / "world-passport.js").read_text(encoding="utf-8")
        catalog = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        photo_keys = re.findall(r"photoKey:'([^']+)'", game)
        labels = re.findall(r"photoLabel:'([^']+)'", game)
        self.assertGreaterEqual(len(photo_keys), 16, "Restored Italy/Germany answer photos must be vetted")
        self.assertEqual(len(labels), len(photo_keys))
        self.assertEqual(len(set(photo_keys)), len(photo_keys))
        covers = {
            "assets/travel/iguazu-rainbow-cover.jpg",
            "assets/travel/mont-saint-michel-sunset-cover.jpg",
            "assets/travel/golden-gate-sunset-cover.jpg",
            "assets/travel/italy-colosseum-cover.jpg",
            "assets/travel/germany-brandenburg-cover.jpg",
        }
        for key, label in zip(photo_keys, labels):
            with self.subTest(quiz_image=key):
                photo = catalog[key]
                self.assertNotIn(photo["photoAsset"], covers)
                self.assertTrue(label.startswith("正解"))
                self.assertTrue(photo["photo"].startswith(
                    "https://thumb.wikimedia.org/wikipedia/commons/thumb/"))
                self.assertTrue(photo["photoPage"].startswith(
                    "https://commons.wikimedia.org/wiki/File:"))
                self.assertTrue(photo["licenseUrl"].startswith(
                    "https://creativecommons.org/"))
                self.assertTrue(photo["author"])
                self.assertTrue(photo["photoCaption"])
                self.assertIn(photo["photoAsset"], worker,
                    "All answer images must be cached offline")
        self.assertTrue(catalog["ar-mate-quiz-image"].get("quizOnly"))
        self.assertTrue(catalog["fr-mediterranean-quiz-image"].get("quizOnly"))
        self.assertIn("stop.quizOnly===true", self.page,
            "Quiz answer images must not pollute travel-photo rotation")
        self.assertIn('id="todayQuizPhotoFigure" hidden', self.page,
            "Do not spoil answers with a photograph before a choice")
        self.assertIn('id="todayQuizPhotoDialog"', self.page)
        self.assertIn("revealWorldPassportAnswerPhoto(question)", game)
        self.assertIn("picture.src='./'+stop.photoAsset", game)
        self.assertIn("photoPage", game)
        self.assertIn("licenseUrl", game)
        self.assertIn("resetWorldPassportPhoto()", game)

    def test_passport_country_questions_are_factual_and_have_valid_answers(self):
        import json
        import re
        game = (ROOT / "world-passport.js").read_text(encoding="utf-8")
        # Real-world key facts in published country guides must also be present
        # in quiz answer explanations: no fake country trivia.
        for term in ("イグアスの滝", "マテ茶", "モン・サン＝ミシェル",
                     "地中海", "ゴールデンゲートブリッジ", "ヨセミテ"):
            self.assertIn(term, game)
            self.assertIn(term, self.page)
        self.assertNotIn("openAtlasStory(", game)
        self.assertNotIn("newsArticle", game)


if __name__ == "__main__":
    unittest.main()
