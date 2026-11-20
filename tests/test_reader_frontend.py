"""Check that the public reader and offline worker have valid JavaScript."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReaderFrontendTest(unittest.TestCase):
    def test_homepage_explains_the_editorial_concept(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("今日も一日、おつかれさま。", page)
        self.assertIn('class="atlas-brand-copy">創作の冗談</span>',page)
        self.assertIn('class="spotlight-topline"',page)
        self.assertIn('id="spotlightBrief"',page)
        self.assertIn('id="spotlightQuip"',page)

    def test_homepage_and_pwa_description_define_human_blunder_comedy(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        manifest=(ROOT/"manifest.webmanifest").read_text(encoding="utf-8")
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("世界の人間の失敗談に、一読で笑えるAIツッコミを。",page)
        self.assertIn("世界の人間の失敗・勘違い・手違いを、AIが鋭くツッコむ。",page)
        self.assertIn("世界の人間の失敗と勘違いに、鋭いAIツッコミ。",manifest)
        self.assertIn("yoru9-shell-v31",worker)
        for photo in (
            "assets/travel/iguazu-rainbow-cover.jpg",
            "assets/travel/mont-saint-michel-sunset-cover.jpg",
            "assets/travel/golden-gate-sunset-cover.jpg",
        ):
            self.assertIn(photo, worker, "Country photo must survive offline PWA visits")

    def test_november_country_intro_regression_has_full_guides_and_photo_covers(self):
        """Retain the four new country guides across later nightly editions."""
        import json
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        stops = json.loads((ROOT / "travel-stops.json").read_text(encoding="utf-8"))
        expected = {"イギリス": "GB", "スペイン": "ES", "日本": "JP", "ニュージーランド": "NZ"}
        for country, code in expected.items():
            with self.subTest(country=country):
                self.assertIn(code + ":{lead:'", page)
                self.assertIn(code + ":[[", page)
                self.assertIn('"' + code + '":[{', page)
        for asset in (
            "assets/travel/london-tower-bridge.jpg", "assets/travel/barcelona-sagrada.jpg",
            "assets/travel/fuji-cherry-blossom.jpg", "assets/travel/nz-milford-sound.jpg"
        ):
            self.assertIn(asset, page)
            self.assertIn(asset, worker)
            self.assertTrue(any(stop.get("photoAsset") == asset for stop in stops.values()))
        self.assertIn("const approvedPhotos=(TODAY_COUNTRY_PHOTOS[currentCode]||[])", page)

    def test_country_portrait_photo_precedes_body_and_current_news(self):
        """On mobile, show the country's visual introduction before long text."""
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        block=page[page.index('<section class="today-map-intro" id="todayMapIntro"'):
                   page.index('id="todayMapIntroRead"', page.index('<section class="today-map-intro" id="todayMapIntro"'))]
        self.assertLess(block.index('id="todayMapIntroName"'),
                        block.index('id="todayMapIntroFigure"'))
        self.assertLess(block.index('id="todayMapIntroFigure"'),
                        block.index('id="todayMapIntroLead"'))
        self.assertLess(block.index('id="todayMapIntroLead"'),
                        block.index('id="todayMapIntroBody"'))
        self.assertLess(block.index('id="todayMapIntroBody"'),
                        block.index('id="todayMapIntroCurrent"'))
        self.assertEqual(page.count('id="todayMapIntroFigure"'),1)
        self.assertIn('#atlasHero .today-map-intro-photo img{aspect-ratio:16/10;',page)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_country_cover_rejects_small_photos_and_prioritizes_clear_originals(self):
        """Prevent upscaled small thumbnails from appearing as full-width portraits."""
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        start=page.index("function countryPhotoSourceUrls(item){")
        end=page.index("function showTodayCountryIntro(item){",start)
        snippet=page[start:end]
        script=snippet+"""
const p={asset:'assets/travel/example.jpg',
 url:'https://thumb.wikimedia.org/wikipedia/commons/thumb/x/x/example.jpg/500px-example.jpg'};
const sources=countryPhotoSourceUrls(p);
if(!sources[0].endsWith('/1280px-example.jpg'))process.exit(2);
if(!sources[1].endsWith('/assets/travel/example.jpg'))process.exit(3);
if(countryPhotoIsSharpEnough({naturalWidth:500,naturalHeight:360}))process.exit(4);
if(!countryPhotoIsSharpEnough({naturalWidth:1280,naturalHeight:720}))process.exit(5);
"""
        run=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('"GB":[{"remoteOnly":true',page)
        self.assertIn('Tower-bridge-in-london.jpg/1280px-Tower-bridge-in-london.jpg',page)
        self.assertIn('"author":"Hexapol","license":"CC BY-SA 4.0"',page)
        self.assertIn('"avoidCover":true,"asset":"assets/travel/london-tower-bridge.jpg"',page)
        self.assertIn("if(!countryPhotoIsSharpEnough(photo))",page)
        self.assertIn("caption.append(link)",page)

    def test_country_portrait_and_destination_tour_are_separate(self):
        """A portrait is about culture and fresh verified notes, not tourist cards."""
        import json
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        catalog = json.loads((ROOT / "country-catalog.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(catalog), 190)
        self.assertIn("COUNTRY PORTRAIT · 国の魅力", page)
        self.assertIn("todayMapIntroCurrent", page)
        self.assertIn("todayMapIntroCurrentSource", page)
        self.assertIn("いま、この国で · 出典確認済み", page)
        self.assertIn("currentCountryHighlight(all,currentCode)", page)
        self.assertIn("requestId!==todayCountryIntroRequest", page)
        self.assertIn(" KR:{lead:", page)
        self.assertIn(" BR:{lead:", page)
        self.assertIn(" AG:{lead:", page)
        self.assertIn("WORLD POSTCARD · 有名観光地の小旅行", page)
        self.assertIn("FAMOUS_TOURIST_LANDMARKS", page)
        portrait=page[page.index("function showTodayCountryIntro("):
                      page.index("// Country centroid pins stay geographically anchored.")]
        self.assertNotIn("loadTravelStops(", portrait)
        self.assertNotIn("travelPhotoOptions(", portrait)
        self.assertNotIn("story.summary", portrait)
        self.assertNotIn("todayMapIntroNewsBody", page)
        self.assertIn("TODAY_COUNTRY_PHOTOS[currentCode]",portrait)
        self.assertIn("yoru9-shell-v31",worker)
        self.assertIn("'country-highlights.json'",worker)
        self.assertIn(r"/^assets\/travel\/[a-z0-9-]+\.jpg$/.test(relative)",worker)

    def test_country_highlights_are_verified_bounded_and_public(self):
        """Country notes are separate from the nightly blunder article feed."""
        import json
        from datetime import date
        from build_site import validate_country_highlights
        data=validate_country_highlights(ROOT)
        self.assertEqual(data["version"],1)
        self.assertEqual(set(data["highlights"]),{"GB","ES","JP","NZ"})
        self.assertEqual(data["updatedOn"],"2026-11-19")
        for calendar_day in (date(2026,11,19), date(2026,11,24), date(2026,11,27)):
            for country, rows in data["highlights"].items():
                self.assertTrue(any(date.fromisoformat(row["validFrom"])<=calendar_day<=
                                    date.fromisoformat(row["validThrough"]) for row in rows),
                                f"{country}: no checked cultural topic for {calendar_day}")
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        self.assertIn("'country-highlights.json'",build)
        self.assertIn("validate_country_highlights(root)",build)
        deploy=(ROOT/".github/workflows/deploy-site.yml").read_text(encoding="utf-8")
        check=(ROOT/".github/workflows/test-publishing.yml").read_text(encoding="utf-8")
        for pipeline in (deploy,check):
            self.assertIn("      - 'country-highlights.json'",pipeline)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_country_highlights_expire_and_require_sources(self):
        import json
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        begin=page.index("function currentCountryHighlight(")
        end=page.index("function todayCountryIntro(",begin)
        script=("function safeUrl(url){return url.startsWith('https://')?url:'#';}\n"
             +page[begin:end]
             +"\nconst row={title:'文化イベント',body:'説明',validFrom:'2026-11-18',"
              "validThrough:'2026-11-22',checkedOn:'2026-11-19',"
              "sourceName:'公式観光局',sourceUrl:'https://example.org/event'};\n"
              "if(!currentCountryHighlight({JP:[row]},'JP','2026-11-19'))process.exit(2);"
              "if(currentCountryHighlight({JP:[row]},'JP','2026-11-23'))process.exit(3);"
              "if(currentCountryHighlight({JP:[{...row,sourceUrl:'javascript:alert(1)'}]},'JP','2026-11-19'))process.exit(4);"
              "if(currentCountryHighlight({JP:[{...row,checkedOn:'2026-11-25'}]},'JP','2026-11-19'))process.exit(5);")
        run=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_visual_first_digests_are_local_original_art_not_news_photos(self):
        import xml.etree.ElementTree as ET
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        site=(ROOT/"build_site.py").read_text(encoding="utf-8")
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        filenames=(
            "coffee-rescue.svg","road-typo.svg","monkey-patrol.svg",
            "category-work.svg","category-company.svg",
            "category-person.svg","category-sports.svg"
        )
        for file in filenames:
            with self.subTest(file=file):
                path=ROOT/"assets"/"news"/file
                self.assertTrue(path.is_file())
                raw=path.read_text(encoding="utf-8")
                root=ET.fromstring(raw)
                self.assertTrue(root.tag.endswith("svg"))
                self.assertIn('viewBox="0 0 800 480"',raw)
                self.assertNotIn("<script",raw)
                self.assertNotIn("<foreignObject",raw)
                self.assertNotIn('href="http',raw)
                self.assertIn("assets/news/"+file,worker)
        self.assertIn("shutil.copytree(artwork_dir,output/'assets'/'news'",site)
        self.assertIn("'assets/news is required for published illustrations'",site)
        self.assertIn("'cheonan-painters-coffee-rescue-2026':'coffee-rescue.svg'",page)
        self.assertIn("'guaira-degavar-road-marking-2026':'road-typo.svg'",page)
        self.assertIn("'albert-lea-mcnugget-monkey-diaper-police-2026':'monkey-patrol.svg'",page)
        self.assertIn("const name=NEWS_ARTWORK[story?.id]||NEWS_ART_FALLBACK[story?.category]",page)
        self.assertIn("function renderIssueGallery()",page)
        self.assertIn("button.addEventListener('click',()=>openAtlasStory(index))",page)
        self.assertIn("target.replaceChildren()",page)
        self.assertIn("renderIssueGallery();updateSpotlight()",page)
        self.assertIn("id=\"issueGallery\"",page)
        self.assertIn("id=\"spotlightImage\"",page)
        self.assertIn("class=\"story-art\"",page)
        self.assertIn("ニュース現場の写真ではありません。",page)
        self.assertIn("報道写真ではありません。",page)
        self.assertIn("#atlasHero .gallery-track{width:100%;display:grid;",page)
        self.assertIn(".story .story-fact .summary{display:-webkit-box",page)
        self.assertIn("-webkit-line-clamp:2;overflow:hidden",page)
        self.assertIn(".story.expanded .story-fact .summary{display:block",page)
        self.assertLess(page.index('id="issueGallery"'),page.index('id="articleReader"'))
        self.assertLess(page.index('id="spotlightImage"'),page.index('id="spotlightTitle"'))

    def test_five_playful_improvements_appear_without_unverified_new_claims(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        cover=page[page.index('<section class="hero" id="atlasHero"'):
                   page.index('<section class="spotlight" id="spotlight"')]
        # The independently vetted first quip is the invitation to read, and
        # is sourced from the actual selected edition, never hardcoded copy.
        self.assertIn('class="quip-teaser" id="quipTeaser"',cover)
        self.assertNotIn('id="quipTeaserImage"',cover)
        self.assertNotIn('class="quip-teaser-art"',cover)
        self.assertIn('class="quip-teaser-heading"',cover)
        self.assertIn('id="quipTeaserLine"',cover)
        self.assertIn('role="note" aria-label="AIによる創作の冗談"',cover)
        self.assertIn('id="quipTeaserRead"',cover)
        self.assertNotIn('data-smile',cover)
        self.assertLess(cover.index('id="quipTeaser"'),
                        cover.index('id="issueGallery"'))
        self.assertLess(cover.index('id="issueGallery"'),
                        cover.index('id="articleReader"'))
        self.assertIn("teaser.hidden=!first||!String(first.quip||'').trim()",page)
        self.assertIn("$('quipTeaserLine').textContent=first.quip",page)
        self.assertNotIn("$('quipTeaserImage').src",page)
        self.assertIn("#atlasHero .quip-teaser{\n display:block;",page)
        self.assertIn("#atlasHero .quip-teaser-actions{display:flex;align-items:stretch;",page)
        self.assertIn("flex-wrap:nowrap;gap:8px;",page)
        self.assertIn("updateQuipTeaser();",page)
        self.assertIn("$('quipTeaserRead').addEventListener('click',()=>openAtlasStory(0))",page)
        # Short taglines use explicit vetted incident IDs and fall back to
        # editor-provided labels for future published stories.
        self.assertIn("const NEWS_COMIC_KICKERS=Object.freeze({",page)
        self.assertIn("NEWS_COMIC_KICKERS[story?.id]||story?.label||story?.categoryLabel",page)
        self.assertIn("kicker.textContent=shortComicKicker(story)",page)
        self.assertIn("label.textContent=story.title||'世界のまさか'",page)
        self.assertIn("$('galleryHeading').textContent='世界の「まさか」'+edition.stories.length+'コマ劇場'",page)
        self.assertIn("#atlasHero .gallery-tile:last-child:nth-child(odd)",page)
        self.assertIn("#atlasHero .atlas-map{aspect-ratio:2.4/1;min-height:118px}",page)
        self.assertNotIn("掲載国の代表位置です。ニュースの現場ではありません。",page)
        # Speech-bubble styling stays, but no optional smile feedback remains.
        self.assertIn(".spotlight .spotlight-joke::before{content:",page)
        self.assertIn(".story .teaserquip::after{content:",page)
        self.assertIn("$('atlasHero').addEventListener('click',handleStoryAction)",page)
        self.assertIn("saveState();update();",page)
        for removed in ("ふっと笑えた", "data-smile", "teaser-smile",
                        "smile-burst", "state.smiles", "tinyLaughStar"):
            self.assertNotIn(removed,page)
        # No new story is invented or an unpublished image or source inserted.
        self.assertIn("return './assets/news/'+name",page)
        self.assertIn("const first=Array.isArray(edition.stories)?edition.stories[0]:null;",page)

    def test_smile_feedback_removed_from_every_article_surface(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        teaser=page[page.index('<section class="quip-teaser"'):
                    page.index('<section class="issue-gallery"')]
        self.assertIn('id="quipTeaserRead"',teaser)
        self.assertNotIn("ふっと笑えた",teaser)
        for removed in ("ふっと笑えた", "data-smile", "teaser-smile",
                        "smile-burst", "state.smiles", "tinyLaughStar"):
            self.assertNotIn(removed,page)
        # Sharing and reading progress are unrelated and must remain available.
        self.assertIn('class="share" data-share="${selectedArticleIndex}"',page)
        self.assertIn('class="share" data-share="${i}"',page)
        self.assertIn('state.read.push(i);saveState();update();',page)

    def test_compact_opening_teaser_does_not_duplicate_or_crop_illustrations(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        teaser=page[page.index('<section class="quip-teaser"'):
                    page.index('<section class="issue-gallery"')]
        self.assertIn('id="quipTeaserTopic"',teaser)
        self.assertIn('id="quipTeaserLine"',teaser)
        self.assertIn('class="quip-teaser-actions"',teaser)
        self.assertNotIn('<img',teaser)
        self.assertNotIn('quipTeaserImage',page)
        self.assertNotIn('quip-teaser-art',page)
        self.assertIn("id=\"issueGallery\"",page)
        self.assertIn("img.className='gallery-art';img.src=newsArt(story)",page)
        self.assertIn('id="spotlightImage"',page)
        self.assertIn('class="atlas-brand-copy">創作の冗談</span>',page)
        self.assertIn('#atlasHero .atlas-brand::after{content:none}',page)
        self.assertIn("#atlasHero .quip-teaser{\n display:block;",page)
        self.assertIn("flex-wrap:nowrap;gap:8px;",page)
        self.assertNotIn('teaser-smile',page)
        self.assertIn('min-height:44px',page)
        # The existing full news story remains intact, with an accessible source.
        self.assertIn("body.innerHTML=",page)
        self.assertIn("safeUrl(first.sourceUrl)",page)
        self.assertIn("updateQuipTeaser();",page)

    def test_gallery_opens_one_independent_story_screen_and_supports_history(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        cover=page[page.index('<section class="hero" id="atlasHero"'):
                   page.index('<section class="article-reader" id="articleReader"')]
        self.assertIn('id="issueGallery"',cover)
        self.assertIn('id="quipTeaserLine"',cover)
        self.assertIn('class="article-reader" id="articleReader" aria-label="選んだニュースを読む" hidden',page)
        for token in ('id="readerBack"','id="readerSelected"',
                      'id="readerPrev"','id="readerNext"',
                      'id="spotlightBody" class="spotlight-body" hidden',
                      'id="spotlightTitle"'):
            self.assertIn(token,page)
        for token in (
            "button.setAttribute('aria-controls','articleReader')",
            "button.addEventListener('click',()=>openAtlasStory(index))",
            "function openAtlasStory(index,fromRoute=false)",
            "function closeArticleReader(fromRoute=false)",
            "function articleIndexFromRoute()",
            "window.addEventListener('popstate',syncArticleRoute)",
            "window.addEventListener('hashchange',syncArticleRoute)",
            "history.pushState({newsArticleId:edition.stories[index].id}",
            "history.replaceState(null,'','#issueGallery')",
            "document.body.classList.add('news-detail-mode')",
            "document.body.classList.remove('news-detail-mode')",
            "$('stories').hidden=true;",
            "selectedArticleIndex=index;",
            "const first=Array.isArray(edition.stories)?edition.stories[selectedArticleIndex]:null;",
            "if(travel)travel.dataset.travelSlot=String(index);",
            "markRead(index);",
            "renderIssueGallery();updateSpotlight();renderTravelSlots();renderTodayMap();updateFilters();applyFilter();update();observeStories();syncArticleRoute();"
        ):
            self.assertIn(token,page)
        # With an article open, map/gallery/other stories must be completely
        # absent from layout and accessibility, not just further down the page.
        self.assertIn("body.news-detail-mode main > :not(#articleReader):not(#offlineNotice){display:none!important}",page)
        self.assertIn("body.news-detail-mode #articleReader #stories,",page)
        self.assertIn("body.news-detail-mode #articleReader .spotlight-visual{display:block}",page)
        self.assertIn("body.news-detail-mode #articleReader .article-reader-toolbar{",page)
        self.assertIn("position:sticky;top:env(safe-area-inset-top,0px)",page)
        self.assertIn("body.news-detail-mode #articleReader .spotlight{display:block",page)
        self.assertIn("#articleReader[hidden]{display:none!important}",page)
        self.assertIn("storyDetailHtml(s)",page)
        self.assertIn("storyEvidenceHtml(s)",page)
        self.assertIn("storyAttributionHtml(s)",page)
        self.assertIn("storyEvidenceHtml(first)",page)

    def test_mobile_news_gallery_uses_two_plus_one_without_cropped_tiles(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('data-layout="mobile-grid-responsive"',page)
        self.assertIn("気になる絵から読む",page)
        self.assertIn("#atlasHero .gallery-track{width:100%;display:grid;",page)
        self.assertIn("grid-auto-flow:row;grid-auto-columns:auto;",page)
        self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr));",page)
        self.assertIn("gap:9px;overflow-x:visible;",page)
        self.assertIn("scroll-snap-type:none;",page)
        self.assertIn("#atlasHero .gallery-tile:last-child:nth-child(odd){",page)
        self.assertIn("grid-column:1/-1;display:grid;",page)
        self.assertIn("#atlasHero .gallery-tile:last-child:nth-child(odd) .gallery-art{",page)
        self.assertIn("@media(max-width:355px){",page)
        # The news tiles remain buttons pointing to real published stories,
        # not duplicate content or nonfunctional decorative pictures.
        self.assertIn("button.addEventListener('click',()=>openAtlasStory(index))",page)
        self.assertIn("target.replaceChildren()",page)





    def test_muted_lead_styles_remain_accessible_on_mobile(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        css=page[page.index("/* Nightly geography-first reading"):]
        self.assertIn('.country-chip{display:inline-flex',css)
        self.assertIn('font-size:1rem;font-weight:740',css)
        self.assertIn('.spotlight h1{font-size:clamp(1.5rem',css)
        self.assertIn('.spotlight-quip{font-size:clamp(1.125rem',css)
        self.assertIn('background:linear-gradient(155deg,#1c2c45,#16243b)',css)
        self.assertIn('.issue-details .status{margin:0',css)
        self.assertIn('@media(max-width:520px)',css)

    def test_optional_microtravel_after_lead_and_each_secondary_story(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('class="travel-slot" data-travel-slot="0"',page)
        self.assertIn('class="travel-slot" data-travel-slot="${i}"',page)
        self.assertIn("function renderTravelSlots()",page)
        self.assertIn("renderTravelSlots();renderTodayMap();updateFilters();",page)
        self.assertIn("class=\"travel-open\" data-travel=",page)
        self.assertIn('aria-expanded="false" aria-controls="travel-panel-',page)
        self.assertIn("panel.hidden=!opening",page)
        self.assertIn("if(!opening)return",page)

    def test_photos_load_only_after_explicit_travel_click(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("document.querySelector('main').addEventListener('click',async event=>{",page)
        self.assertIn("event.target.closest('[data-travel]')",page)
        self.assertIn("const stops=await loadTravelStops()",page)
        self.assertIn("fetch('./travel-stops.json',{cache:'no-store'})",page)
        self.assertIn('loading="lazy" decoding="async"',page)
        self.assertIn('data-remote-photo=',page)
        self.assertNotIn("travelExplainerShown",page)
        self.assertNotIn("firstIntro",page)
        self.assertIn("function mountPhoto(stop,attempt=0)",page)
        self.assertIn("const next=chooseTravelPhoto(story,stops)",page)
        self.assertIn("この写真はニュース現場の記録ではなく、旅先の風景です。",page)
        self.assertNotIn("ニュースをきっかけに、その国の有名な観光名所へ。",page)
        self.assertNotIn("(showIntro?'<p class=\"travel-disclaimer\">",page)
        self.assertNotIn("観光案内ではなく、実際の場所へ視線を向ける短い寄り道",page)
        self.assertIn("if(!img.dataset.remoteTried&&img.dataset.remotePhoto)",page)
        self.assertIn("edition.stories[i]!==story",page)
        self.assertIn("img.addEventListener('error',()=>{",page)
        self.assertNotIn("<audio autoplay",page)
        self.assertNotIn("<video autoplay",page)

    def test_travel_stop_coordinates_rights_and_event_are_specific(self):
        import json
        payload=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        self.assertIn("cheonan-painters-coffee-rescue-2026",payload)
        self.assertIn("faa-router-ground-stop-2026",payload)
        self.assertIn("jensen-huang-nvidia-resignation-2026",payload)
        self.assertIn("spacex-starship-booster-failure-2026",payload)
        self.assertTrue(all(payload[key].get("countryOnly") for key in
            ("faa-router-ground-stop-2026","jensen-huang-nvidia-resignation-2026",
             "spacex-starship-booster-failure-2026")))
        self.assertIn("guaira-degavar-road-marking-2026",payload)
        self.assertIn("flight-wrong-country",payload)
        for key,stop in payload.items():
            with self.subTest(event=key):
                self.assertIn(stop["country"],("韓国","ブラジル","イギリス","日本","アメリカ合衆国","スペイン","アンティグア・バーブーダ","アルゼンチン","フランス","ニュージーランド"))
                self.assertTrue(-90<=stop["latitude"]<=90)
                self.assertTrue(-180<=stop["longitude"]<=180)
                self.assertTrue(stop["photo"].startswith("https://thumb.wikimedia.org/wikipedia/commons/thumb/"))
                # Wikimedia disallows arbitrary 640px thumbnails since 2026.
                self.assertIn("/500px-",stop["photo"])
                self.assertRegex(stop["photoAsset"],r"^assets/travel/[a-z0-9-]+\.jpg$")
                self.assertTrue(stop["photoPage"].startswith("https://commons.wikimedia.org/wiki/File:"))
                self.assertTrue(stop["licenseUrl"].startswith("https://creativecommons.org/"))
                self.assertNotIn("ニュース現場の写真ではありません",stop["photoCaption"])
                self.assertNotIn("ニュース現場",stop["note"])
                self.assertLessEqual(len(stop["note"]),110)
                self.assertLessEqual(len(stop["photoCaption"]),70)
        for country in ("韓国","ブラジル","イギリス","日本","アメリカ合衆国"):
            self.assertTrue(any(stop["country"]==country and stop.get("countryOnly")
                                for stop in payload.values()),country)
        self.assertEqual("東京・浅草寺",payload["japan-country-postcard"]["place"])
        self.assertEqual("天安・独立記念館",payload["cheonan-painters-coffee-rescue-2026"]["place"])
        self.assertEqual("エディンバラ城",payload["flight-wrong-country"]["place"])
        self.assertIn("edition.stories[i]!==story",(ROOT/"index.html").read_text(encoding="utf-8"))
        self.assertIn("travelCountryNames(story.country).includes(stop.country)",(ROOT/"index.html").read_text(encoding="utf-8"))

    def test_all_november_18_reissued_stories_have_valid_destination_photo(self):
        import json
        from country_codes import country_codes
        stops=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        # Historical November 18 photos are tested against the immutable
        # archive, not against today's current issue after nightly rollover.
        issue=json.loads((ROOT/"data/archive/2026-11-18.json").read_text(encoding="utf-8"))
        self.assertEqual(issue["editionDate"],"2026-11-18")
        self.assertEqual(len(issue["stories"]),3)
        for story in issue["stories"]:
            with self.subTest(story=story["id"]):
                country=story["country"]
                photos=[stop for stop in stops.values() if
                        country_codes(stop["country"])==country_codes(country)]
                self.assertTrue(photos,"missing same-country photo: "+country)
                if story["id"] in ("argentina-goalkeeper-throws-own-goal-2026",
                                   "france-candy-police-mock-wanted-2026"):
                    self.assertIn(story["id"],stops)
                    selected=stops[story["id"]]
                    self.assertTrue(selected["photo"].startswith(
                        "https://thumb.wikimedia.org/wikipedia/commons/thumb/"))
                    self.assertEqual(selected["license"],"CC BY-SA 4.0")
                    self.assertIn(selected["photoAsset"],(ROOT/"travel-stops.json").read_text())

    def test_every_postcard_distinguishes_news_country_from_tourist_photography(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        block=page[page.index("function travelPostcardHtml("):
                   page.index("document.querySelector('main').addEventListener('click',async event=>{")]
        self.assertIn("const reportCountry=countryLabel(story.country||'')",block)
        self.assertIn("class=\"travel-context\" aria-label=\"記事と旅先の違い\"",block)
        self.assertIn("記事の舞台（国） ",block)
        self.assertIn("旅先 ",block)
        self.assertIn("class=\"travel-trust\" role=\"note\"",block)
        self.assertIn("この写真はニュース現場の記録ではなく、旅先の風景です。",block)
        self.assertNotIn("写真や地図は記事の証拠ではなく",block)
        self.assertNotIn("travel-disclaimer",block)
        self.assertIn("この国の有名観光地は確認中。",block)
        self.assertIn("掲載国を地図で見る",block)
        self.assertIn("旅先を地図で見る",block)
        self.assertIn("countryRecord(countryKeys(story.country)[0]||'')",block)
        # Every trip has exactly one clear, concise photo disclaimer.
        self.assertEqual(block.count('class="travel-trust" role="note"'),1)
        self.assertIn("panel.innerHTML=travelPostcardHtml(story,stop)",page)
        self.assertIn(".travel-trust{display:block",page)
        self.assertIn(".travel-context-story,.travel-context-destination{",page)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_travel_priority_is_specific_same_country_or_honest_empty(self):
        import json
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        start=page.index("const travelSelections=new Map();")
        end=page.index("function travelPostcardHtml(",start)
        logic=page[start:end]
        row=lambda country,asset: {
          "country":country,"place":("京都・金閣寺" if asset=="kyoto" else "東京・浅草寺" if asset=="tokyo" else "ニューヨークの街並み"),"region":"風景",
          "latitude":35,"longitude":135,
          "photo":"https://thumb.wikimedia.org/wikipedia/commons/thumb/x/photo.jpg",
          "photoAsset":"assets/travel/"+asset+".jpg",
          "photoPage":"https://commons.wikimedia.org/wiki/File:Photo.jpg",
          "licenseUrl":"https://creativecommons.org/licenses/by/4.0/"
        }
        stops={"article-specific":row("日本","kyoto"),
               "japan-generic":row("日本","tokyo"),
               "us":row("アメリカ合衆国","usa")}
        script=(
          "function countryKeys(){return [];} function countryLabel(x){return x;}\n"+
          logic+"\nconst stops="+json.dumps(stops,ensure_ascii=False)+";\n"+
          "const exact=chooseTravelPhoto({id:'article-specific',country:'日本'},stops);"
          "if(exact!==stops['article-specific'])process.exit(2);"
          "const other=chooseTravelPhoto({id:'other',country:'日本'},stops);"
          "if(!other||other.country!=='日本')process.exit(3);"
          "const missing=chooseTravelPhoto({id:'no-photo',country:'ケニア'},stops);"
          "if(missing!==null)process.exit(4);"
        )
        run=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_microtravel_selects_famous_attractions_only(self):
        import json
        from country_codes import country_codes
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        photos=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        self.assertIn("famousAttractionScore(stop)<80",page)
        self.assertIn("FAMOUS_TOURIST_LANDMARKS",page)
        # Each current-edition country has a verified landmark photograph.
        names={
          "イギリス":"エディンバラ城","スペイン":"サグラダ・ファミリア",
          "日本":"富士山","ニュージーランド":"ミルフォード・サウンド"
        }
        for country,landmark in names.items():
            self.assertTrue(any(stop["country"]==country and
                                landmark in stop["place"] for stop in photos.values()))

    def test_travel_data_changes_trigger_validation_and_site_deploy(self):
        deploy=(ROOT/".github/workflows/deploy-site.yml").read_text(encoding="utf-8")
        check=(ROOT/".github/workflows/test-publishing.yml").read_text(encoding="utf-8")
        self.assertIn("      - 'travel-stops.json'",deploy)
        self.assertIn("      - 'travel-stops.json'",check)

    def test_published_travel_guide_is_offline_safe(self):
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("'travel-stops.json'",build)
        self.assertIn("'travel-stops.json'",worker)
        self.assertRegex(worker,r"const SHELL_CACHE = 'yoru9-shell-v(?:[3-9]|[1-9][0-9]+)';")
        self.assertIn("travel-photo-error", (ROOT/"index.html").read_text(encoding="utf-8"))
        self.assertIn("bundle_travel_photos(root, output)",build)
        self.assertIn("data-remote-photo=", (ROOT/"index.html").read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_photo_selection_never_switches_country_just_to_avoid_repetition(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        start=page.index("const travelSelections=new Map();")
        end=page.index("function travelPostcardHtml(",start)
        logic=page[start:end]
        # Small deterministic catalog: the second American article should
        # reuse a US photograph rather than mislabel a Japan photograph as US.
        payload={
          "one":{"country":"アメリカ合衆国","place":"ニューヨークの街並み","region":"USA","latitude":40,"longitude":-70,
                  "photo":"https://thumb.wikimedia.org/wikipedia/commons/thumb/x/photo.jpg",
                  "photoAsset":"assets/travel/usa.jpg",
                  "photoPage":"https://commons.wikimedia.org/wiki/File:USA.jpg",
                  "licenseUrl":"https://creativecommons.org/licenses/by/4.0/"},
          "two":{"country":"日本","place":"東京・浅草寺","region":"日本","latitude":35,"longitude":139,
                  "photo":"https://thumb.wikimedia.org/wikipedia/commons/thumb/y/photo.jpg",
                  "photoAsset":"assets/travel/japan.jpg",
                  "photoPage":"https://commons.wikimedia.org/wiki/File:Japan.jpg",
                  "licenseUrl":"https://creativecommons.org/licenses/by/4.0/"}
        }
        import json
        script=logic+chr(10)+"const stops="+json.dumps(payload,ensure_ascii=False)+";"+chr(10)+(
            "const first=chooseTravelPhoto({id:'first',country:'アメリカ'},stops);"
            "const second=chooseTravelPhoto({id:'second',country:'アメリカ'},stops);"
            "if(!first||!second||first.country!=='アメリカ合衆国'||"
            "second.country!=='アメリカ合衆国')process.exit(3);"
        )
        p=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_mobile_cover_puts_verified_story_above_quip_without_intrusive_intro(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('name="apple-mobile-web-app-status-bar-style" content="black"',page)
        self.assertIn('env(safe-area-inset-top,0px)',page)
        self.assertIn('padding-top:calc(var(--safe-top) + 5px)',page)
        self.assertIn('position:sticky;top:var(--safe-top)',page)
        self.assertIn('height:var(--safe-top);background:#0b1528;z-index:40',page)
        self.assertLess(page.index('id="spotlightTitle"'),page.index('id="spotlightBrief"'))
        self.assertLess(page.index('id="spotlightBrief"'),page.index('id="spotlightQuip"'))
        self.assertLess(page.index('id="spotlightQuip"'),page.index('id="spotlightRead"'))
        self.assertLess(page.index('id="spotlightRead"'),page.index('id="stories"'))
        self.assertIn("firstSentence=summary.split('。')[0].trim()",page)
        self.assertIn('width:auto;min-height:44px;',page)
        self.assertIn('font-size:clamp(1.4rem,5.75vw,1.75rem)',page)
        self.assertNotIn('class="hero-description"',page)
        self.assertNotIn('class="hero-truth"',page)

    def test_lead_story_spotlight_is_dynamic_and_readable(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for token in ('id="spotlight"', 'id="spotlightTitle"',
                      'id="spotlightQuip"', 'id="spotlightRead"',
                      "function updateSpotlight()", "updateSpotlight();",
                      "first.quip", "first.title", "panel.scrollIntoView"):
            self.assertIn(token, page)

    def test_cover_matches_award_first_layout(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        cover = page[page.index('<header class="nav">'):page.index('<div id="offlineNotice"')]
        self.assertLess(cover.index('class="hero"'), cover.index('class="spotlight"'))
        for token in ('class="spotlight-award"', 'class="evening-moon"', 'id="spotlightTitle"',
                      'class="spotlight-divider"', 'AIツッコミ',
                      'id="spotlightQuip"', 'この話の続きへ ↓'):
            self.assertIn(token, cover)

    def test_mishap_award_is_dynamic_and_archive_aware(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for token in ('id="spotlightAward"', "今夜のひと話",
                      "公開済みの便りから", "体験版の実話",
                       "d.slice(1).map((s,offset)"):
            self.assertIn(token, page)

    def test_article_cards_separate_reported_facts_from_creative_ai_comedy(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        lead=page[page.index('<section class="spotlight"'):page.index('<div id="offlineNotice"')]
        self.assertIn('class="spotlight-fact" aria-label="出来事の要点"',lead)
        self.assertIn('class="spotlight-joke" role="note" aria-label="AIによる創作の冗談"',lead)
        self.assertIn('<span class="fact-kicker">起きたこと</span>',lead)
        self.assertIn('<span class="humor-marker">創作の冗談</span>',lead)
        self.assertLess(lead.index('id="spotlightTitle"'),lead.index('class="spotlight-fact"'))
        self.assertLess(lead.index('id="spotlightBrief"'),lead.index('id="spotlightQuip"'))
        self.assertLess(lead.index('class="spotlight-joke"'),lead.index('id="spotlightRead"'))
        second=page[page.index("d.slice(1).map((s,offset)"):page.index("renderIssueGallery();updateSpotlight()")]
        self.assertIn('<div class="story-fact"><span class="fact-kicker">起きたこと</span>',second)
        self.assertIn('class="teaserquip" role="note" aria-label="AIによる創作の冗談"',second)
        self.assertIn('class="humor-marker">創作の冗談</small>',second)
        self.assertIn('escapeHtml(s.title)',second)
        self.assertIn('escapeHtml(s.summary)',second)
        self.assertIn('escapeHtml(s.quip)',second)
        self.assertIn('escapeHtml(s.sourceName',second)
        self.assertIn('data-open=',second)
        self.assertIn('class="details" hidden',second)
        # The visual treatment must not overwrite reporting, source details
        # or the separate human/AI editorial review process.
        self.assertIn('role="note" aria-label="AIによる創作の冗談"',page)
        self.assertIn('style',page)
        self.assertIn('.spotlight-joke{margin:0 0 13px',page)
        self.assertIn('.story .readbtn{display:flex',page)
        self.assertIn('.story .teaserquip .humor-marker{',page)
        self.assertIn('@media(max-width:520px)',page)

    def test_lead_story_is_inside_main_landmark_and_summary_not_repeated(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('</header>\n<main>\n<section class="evening-entry"', page)
        self.assertLess(page.index('class="evening-entry"'),page.index('class="spotlight"'))
        self.assertNotIn('<main><p class="release-status"', page)
        # The standalone news screen must NOT repeat the digest/lead above
        # the full text (reported by iPhone readers as two news articles).
        self.assertNotIn("isJapaneseText(first.detail)?'<p",page)
        self.assertIn('class="article-narrative" aria-label="記事本文"',page)
        self.assertIn('body.news-detail-mode #articleReader .spotlight-fact,',page)
        self.assertIn('body.news-detail-mode #articleReader #spotlightRead{display:none!important}',page)
        self.assertIn('body.news-detail-mode #articleReader #spotlightBody{order:3;',page)
        self.assertIn('body.news-detail-mode #articleReader .spotlight-joke{order:4;',page)
        self.assertIn("detail.split(",page)
        self.assertNotIn("報道時期：${escapeHtml(first.reported||'出典に記載')}<br>出典：",page)
        self.assertIn("storyDetailHtml(first)", page)

    def test_lead_story_is_not_duplicated_and_can_expand_in_place(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="spotlightBody" class="spotlight-body" hidden', page)
        self.assertIn('id="spotlightRead" aria-expanded="false" aria-controls="spotlightBody"', page)
        self.assertIn("body.innerHTML=", page)
        self.assertIn("storyDetailHtml(first)", page)
        self.assertIn("if(show){markRead(selectedArticleIndex);panel.scrollIntoView(", page)
        self.assertIn("d.slice(1).map((s,offset)", page)
        self.assertNotIn('.story:first-child{', page)
        self.assertNotIn('今夜の１本目', page)
        self.assertIn('.story .teaserquip{', page)
        self.assertIn("data-story-index=", page)
        self.assertIn("el.closest('.story').dataset.storyIndex", page)
        self.assertNotIn("first.scrollIntoView", page)
        self.assertIn("$('spotlightBody').addEventListener('click',handleStoryAction)", page)
        self.assertIn('data-share="${selectedArticleIndex}"', page)

    def test_filter_buttons_match_available_secondary_categories(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("function updateFilters()", page)
        self.assertIn("edition.stories.slice(1).map(s=>s.category)", page)
        self.assertIn("controls.hidden=edition.stories.length<=3||available.size<=1", page)
        self.assertIn("button.hidden=button.dataset.filter!=='all'&&!available.has(", page)
        self.assertIn(".filters[hidden],.filter[hidden]", page)
        self.assertIn("updateSpotlight();renderTravelSlots();renderTodayMap();updateFilters();applyFilter();", page)
        self.assertIn("document.querySelector('.sectionhead').hidden=d.length<=1", page)
        self.assertIn("$('intro').hidden=d.length<=1", page)

    def test_mobile_reader_typography_is_legible(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(".status #editionMessage,.edition-context,.note,.source,.storytop,.small{font-size:13px}", page)
        self.assertIn(".hero .hero-description,.hero .hero-truth{font-size:13px}", page)
        self.assertIn(".spotlight-body .summary{font-size:15px", page)
        self.assertIn(".spotlight #spotlightRead{", page)
        self.assertNotIn(".spotlight button{", page)

    def test_single_ai_punchline_and_nightly_payoff(self):
        """Keep one punchline per article; archived second jokes remain editorial data."""
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="spotlightQuip"', page)
        self.assertIn('id="nightlyMessage"', page)
        self.assertIn('今日のひと言 · 失敗と挑戦', page)
        self.assertNotIn('もうひとつ、AIのひと言', page)
        spotlight = page[page.index('function updateSpotlight(){'):
                         page.index("$('spotlightRead').addEventListener")]
        self.assertNotIn('quipSecond', spotlight)
        self.assertIn('storyDetailHtml(first)', spotlight)
        self.assertIn('ここからはAIの見方。', page)
        self.assertIn('quipRevealObserver', page)
        self.assertIn('article-quip-pop', page)
        self.assertIn('body.news-detail-mode #articleReader #spotlightTitle{', page)
        self.assertIn('body.news-detail-mode #articleReader .spotlight-joke .spotlight-quip{', page)
        editor = (ROOT / "auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn('quipSecond', editor)
        self.assertIn('distinct', editor)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_story_detail_keeps_report_facts_and_removes_legacy_ai_view(self):
        """The older paragraph marked as AI opinion must not duplicate the punchline."""
        import json
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        detail_js = page[page.index('function storyDetailHtml(story){'):
                         page.index('function storyEvidenceHtml(story){')]
        runner = (
            'function isJapaneseText(v){return /[ぁ-んァ-ヶ一-龯々]/.test(String(v||""));}\n'
            'function escapeHtml(v){return String(v).replaceAll("&","&amp;").replaceAll("<","&lt;");}\n'
            + detail_js
            + '\nconst html=storyDetailHtml(JSON.parse(process.argv[1]));'
              '\nif(!html.includes("事実を確認した。")||html.includes("これはAIの感想")) process.exit(1);'
        )
        case = {"detail": "事実を確認した。\n\nここからはAIの見方。\nこれはAIの感想。",
                "summary": "事実の概要"}
        proc = subprocess.run(["node", "-e", runner, json.dumps(case, ensure_ascii=False)],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_sports_filter_is_available(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-filter="sports"', page)
        self.assertIn('>スポーツ</button>', page)

    def test_reader_ids_and_offline_honesty(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for token in ('id="editionTag"', 'id="storyHeading"', 'id="dateGuide"',
                      'id="offlineNotice"', 'serviceWorker.register',
                      "edition.editionType==='special'", '`前回の配信号'):
            with self.subTest(token=token):
                self.assertIn(token, page)

    def test_read_progress_counts_visible_summaries(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("function observeStories()", page)
        self.assertIn("new IntersectionObserver(", page)
        self.assertIn("readObserver.observe(el)", page)
        self.assertIn("markRead(i)", page)
        self.assertIn("state.read.includes(i)", page)


    def test_compact_mobile_edition_and_expandable_previews(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(page.count('id="dateGuide"'), 1)
        self.assertEqual(page.count('id="clock"'), 1)
        self.assertIn('<details class="edition-context">', page)
        self.assertIn('配信日・報道期間について', page)
        self.assertIn('-webkit-line-clamp:4', page)
        self.assertIn("classList.toggle('expanded',show)", page)
        self.assertIn('.story.expanded .summary{display:block}', page)
        self.assertIn('.story.expanded .teaserquip{display:block}', page)

    def test_english_only_detail_is_collapsed_below_japanese_overview(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("function storyDetailHtml(story)", page)
        self.assertIn("if(isJapaneseText(detail))", page)
        self.assertIn("日本語の詳しい本文は準備中です。", page)
        self.assertIn("英語の補足文を表示", page)
        self.assertIn('lang="en"', page)
        self.assertIn("${storyDetailHtml(s)}", page)

    def test_mobile_reader_actions_and_nightly_quote_layout(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('詳しく読む ↓', page)
        self.assertIn('閉じる ↑', page)
        self.assertNotIn('補足文を見る（英語）', page)
        self.assertIn('.filter,.readbtn,.share{min-height:44px', page)
        self.assertIn('.night-quote p{font-size:clamp(19px', page)
        self.assertIn('.hero .eyebrow,.hero-audience{display:none}', page)


    def test_final_mobile_typography_has_legible_reading_sizes(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        css = page[page.index("/* Reader typography v7"):page.index("</style>")]
        self.assertIn(".status #editionMessage{font-size:.875rem", css)
        self.assertIn(".release-status{font-size:.9375rem", css)
        self.assertIn(".edition-context{font-size:.9375rem", css)
        self.assertIn(".hero .hero-description,.hero .hero-truth{font-size:1rem", css)
        self.assertIn(".story .summary{font-size:1rem;line-height:1.85}", css)
        self.assertIn(".reported,.story .reported{font-size:.875rem", css)
        self.assertIn(".teaserquip,.story .teaserquip{font-size:1rem", css)
        self.assertIn(".readbtn{font-size:1rem", css)
        self.assertIn(".night-quote span{font-size:.9375rem", css)
        self.assertIn(".note{font-size:.9375rem", css)
        self.assertIn(".footerpanel .bye{font-size:.9375rem", css)
        self.assertGreater(page.index("/* Reader typography v7"),
                           page.index(".status #editionMessage{font-size:11px}"))

    def test_long_mobile_metadata_wraps_without_cutting_off_text(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        css = page[page.index("/* Reader typography v7"):page.index("</style>")]
        self.assertIn(".nav{flex-wrap:wrap;row-gap:6px}", css)
        self.assertIn(".nav .tag{max-width:50%;font-size:.8125rem;overflow-wrap:anywhere}", css)
        self.assertIn(".release-status{font-size:.9375rem;line-height:1.7;overflow-wrap:anywhere}", css)
        self.assertIn(".sectionhead .small{flex-shrink:0}", css)
        self.assertIn(".archivepanel select,.worldpanel select{font-size:1rem;min-height:44px}", css)

    def test_nightly_closing_has_single_primary_message(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        closing = page[page.index('<section class="footerpanel" id="closing">'):page.index('</section>', page.index('<section class="footerpanel" id="closing">'))]
        self.assertEqual(closing.count('id="nightlyMessage"'), 1)
        self.assertIn('世界からの便りは、ここまで。', closing)
        self.assertIn('次の「まさか」も、世界のどこかから。', closing)
        self.assertIn('また、次の便りで。', closing)
        self.assertNotIn('おやすみなさい', closing)
        self.assertNotIn('気が向いた夜に', closing)
        self.assertNotIn('完璧じゃないのは', closing)

    def test_compact_closing_is_appropriate_for_daytime_and_previous_editions(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        closing=page[page.index('<section class="footerpanel" id="closing">'):
                     page.index('</section>',page.index('<section class="footerpanel" id="closing">'))]
        self.assertIn('世界からの便りは、ここまで。',closing)
        self.assertIn('class="closing-afterword"',closing)
        self.assertIn('次の「まさか」も、世界のどこかから。',closing)
        self.assertIn('また、次の便りで。',closing)
        self.assertNotIn('今日の便りは',closing)
        self.assertNotIn('おやすみなさい',closing)
        self.assertNotIn('毎晩必ず',closing)
        self.assertEqual(closing.count('id="nightlyMessage"'),1)
        self.assertIn('#closing.footerpanel{margin:20px 0 16px;padding:17px 18px 15px;',page)
        self.assertIn('#closing .closing-moon{font-size:1.2rem;',page)
        self.assertIn('#closing .closing-afterword{border-top:1px solid #637993;',page)
        self.assertIn('#closing .night-quote:not([hidden])~.closing-afterword',page)
        self.assertIn('#closing .night-quote p{font-size:clamp(.96rem',page)
        self.assertIn("$('closingQuote').hidden=false",page)
        self.assertIn("$('closingJump').hidden=false",page)

    def test_iso_country_catalog_is_used_across_reader(self):
        import json
        catalog=json.loads((ROOT/"country-catalog.json").read_text(encoding="utf-8"))
        codes=[row["code"] for row in catalog]
        self.assertEqual(len(codes),len(set(codes)))
        usa=next(row for row in catalog if row["code"]=="US")
        self.assertIn("米国",usa["aliases"])
        self.assertIn("アメリカ",usa["aliases"])
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        for token in ("function countryKey(name)","function countryRecord(name)",
                      "function travelCountryNames(raw)","country-catalog.json"):
            self.assertIn(token,page)
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        self.assertIn("'country-catalog.json'",build)


    def test_app_refreshes_on_resume_and_updates_offline_cache(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        for token in ("function refreshOnForeground()", "visibilitychange",
                      "pageshow", "reg.update()", "controllerchange"):
            with self.subTest(token=token):
                self.assertIn(token, page)
        self.assertRegex(worker,r"yoru9-shell-v(?:[3-9]|[1-9][0-9]+)")
        self.assertIn("yoru9-released-issues-v3", worker)
        self.assertIn("event.respondWith(fetch(req).then(response => {", worker)





    def test_iphone_refinement_keeps_atlas_and_removes_duplicate_metadata(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="atlasLede"',page)
        self.assertIn("currentIssue?'世界で報じられた、思わず「まさか」な失敗と珍事件。':'この号に収録された、世界の失敗・勘違い・珍事件。'",page)
        self.assertIn("const count=Math.max(0,edition.stories.length-1)",page)
        self.assertIn("$('progress').hidden=count<=3",page)
        self.assertIn(".atlas-brand{display:block}",page)
        self.assertIn("#atlasHero .atlas-brand{display:block!important;",page)
        self.assertIn(".spotlight h1{font-size:clamp(1.31rem",page)
        self.assertNotIn('id="coverWorldMap"',page)
        # Edition's old nightly message is no longer the footer quotation.
        self.assertIn("updateDailyFailureQuote(localDate(new Date()))",page)
        self.assertNotIn("const nightlyLine=",page)
        self.assertIn("$('closingQuote').hidden=false",page)
        self.assertIn("$('closingJump').hidden=false",page)
        self.assertIn("この号に収録された、世界の失敗・勘違い・珍事件。",page)
        self.assertIn("この写真はニュース現場の記録ではなく、旅先の風景です。",page)
        self.assertNotIn("map.open=true",page)



    def test_footer_trust_note_is_readable_but_not_an_extra_huge_card(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('<details class="disclosure-details">',page)
        self.assertIn('<summary>編集方針・出典と配信情報について</summary>',page)
        self.assertIn('<aside class="note" id="disclosure">',page)
        self.assertIn('.disclosure-details>summary{min-height:44px',page)


    def test_sources_correction_and_notification_are_unobtrusive(self):
        page = (ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('function storyEvidenceHtml(story)',page)
        self.assertIn('function storyCorrectionHtml(story)',page)
        self.assertIn('追加の確認資料',page)
        self.assertIn('編集訂正あり',page)
        header=page.split('<header class="nav">',1)[1].split('</header>',1)[0]
        self.assertIn('id="notificationSection"',header)
        self.assertIn('id="notificationDetails"',header)
        self.assertIn('夜9時のお知らせ<small>通知設定</small>',header)
        self.assertIn('id="editionTag" hidden',header)
        self.assertEqual(page.count('id="notificationSection"'),1)
        self.assertNotIn('id="notificationSection" hidden',page)
        self.assertIn('background:linear-gradient(130deg,#ffe6a6,#f2b869)',page)
        self.assertIn('width:min(350px,calc(100vw - 32px))',page)
        self.assertIn('id="editionMessage" hidden',page)
        self.assertIn('.status .release-status{margin:0;padding:0;',page)

    def test_evening_reading_is_an_invitation_not_a_task(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('href="#closing"',page)
        self.assertIn('今夜は、ひと言だけ読む',page)
        self.assertIn('id="closing"',page)
        self.assertIn('また、次の便りで。',page)
        self.assertIn('Math.max(0,edition.stories.length-1)',page)
        self.assertNotIn('state.read.length} /',page)
        self.assertNotIn('やらかし大賞',page)
        self.assertNotIn('AIツッコミ・追撃',page)
        self.assertIn('.evening-entry',page)
        self.assertIn('min-height:44px',page)

    def test_failure_quote_rotates_by_japan_date_and_keeps_real_sources(self):
        import json
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        prefix="const DAILY_FAILURE_QUOTES=Object.freeze("
        start=page.index(prefix)+len(prefix)
        end=page.index(");",start)
        quotes=json.loads(page[start:end])
        self.assertGreaterEqual(len(quotes),12)
        self.assertGreaterEqual(len({q["person"] for q in quotes}),8)
        for entry in quotes:
            self.assertTrue(entry["ja"] and entry["original"] and entry["person"])
            self.assertTrue(entry["source"] and entry["url"].startswith("https://"))
        self.assertIn("failureQuoteForDate(jstDate)",page)
        self.assertIn("updateDailyFailureQuote(localDate(new Date()))",page)
        self.assertIn("lastRenderedLocalDate!==localDate(now))render()",page)
        self.assertIn("日本語意訳",page)
        self.assertNotIn("const nightlyLine=",page)
        self.assertIn('id="dailyQuoteSource"',page)
        self.assertIn('id="dailyQuoteAuthor"',page)
        self.assertIn('id="dailyQuoteDate"',page)
        self.assertIn("text-align:center;text-wrap:balance;overflow-wrap:anywhere",page)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_failure_quote_changes_on_next_jst_day_and_not_on_refresh(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        start=page.index("const DAILY_FAILURE_QUOTES=Object.freeze(")
        end=page.index("function updateDailyFailureQuote(jstDate){",start)
        logic=page[start:end]
        checker="""
const a=failureQuoteForDate('2026-11-20');
const again=failureQuoteForDate('2026-11-20');
const b=failureQuoteForDate('2026-11-21');
if(a!==again)process.exit(1);
if(a===b || a.ja===b.ja)process.exit(2);
const firstTwelve=Array.from({length:12},(_,i)=>failureQuoteForDate('2026-11-'+String(i+1).padStart(2,'0')));
if(new Set(firstTwelve).size!==12)process.exit(3);
"""
        run=subprocess.run(["node","-e",logic+checker],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_past_quote_collection_is_below_today_and_above_farewell(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        start=page.index('<section class="footerpanel" id="closing">')
        end=page.index('</section>',start)
        closing=page[start:end]
        self.assertLess(closing.index('id="dailyQuoteSource"'),
                        closing.index('id="pastQuoteArchive"'))
        self.assertLess(closing.index('id="pastQuoteArchive"'),
                        closing.index('class="closing-afterword"'))
        self.assertIn('<summary>過去の名言集を見る',closing)
        self.assertIn('id="pastQuoteList" aria-label="過去の日替わり名言"',closing)
        self.assertIn('id="pastQuoteStatus" role="status"',closing)
        self.assertIn('id="pastQuoteMore" hidden',closing)
        self.assertEqual(closing.count('id="pastQuoteArchive"'),1)
        self.assertIn('#closing .quote-archive summary{',page)
        self.assertIn('#closing .quote-archive summary:focus-visible',page)
        self.assertIn('min-height:48px',page)
        self.assertIn('link.href=safeUrl(quote.url)',page)
        self.assertIn("link.rel='noopener noreferrer'",page)
        self.assertIn("source.append(link)",page)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_past_quote_history_starts_on_actual_launch_date(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        start=page.index("const DAILY_FAILURE_QUOTES=Object.freeze(")
        end=page.index("function appendPastQuoteBatch(){",start)
        pure=page[start:end]
        checks="""
function assert(ok,why){if(!ok)throw new Error(why);}
assert(pastQuoteTotalDays('2026-11-19')===0,'prelaunch');
assert(pastQuoteTotalDays('2026-11-20')===0,'launchday');
assert(pastQuoteEntries('2026-11-20').length===0,'no fabricated prior quotes');
const yesterday=pastQuoteEntries('2026-11-21');
assert(yesterday.length===1,'one prior entry');
assert(yesterday[0].date==='2026-11-20','correct prior date');
assert(yesterday[0].quote===failureQuoteForDate('2026-11-20'),'same quotation');
const twelve=pastQuoteEntries('2026-12-03');
assert(twelve.length===12,'default batch size');
assert(twelve[0].date==='2026-12-02','newest first');
assert(twelve[11].date==='2026-11-21','end of first batch');
const last=pastQuoteEntries('2026-12-03',12,12);
assert(last.length===1 && last[0].date==='2026-11-20','pagination reaches first day');
assert(pastQuoteEntries('2026-12-03',13).length===0,'no future pages');
assert(pastQuoteEntries('2026-11-19').length===0,'no quote before launch');
"""
        run=subprocess.run(["node","-e",pure+checks],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_past_quote_archive_updates_daily_and_paginates_when_opened(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("updatePastQuoteArchive(jstDate);",page)
        self.assertIn("pastQuotesDate=jstDate;",page)
        self.assertIn("pastQuotesRendered=0;",page)
        self.assertIn("$('pastQuoteList').replaceChildren()",page)
        self.assertIn("$('pastQuoteArchive').addEventListener('toggle'",page)
        self.assertIn("$('pastQuoteMore').addEventListener('click',appendPastQuoteBatch)",page)
        self.assertIn("pastQuotesRendered+=items.length",page)
        self.assertIn("lastRenderedLocalDate!==localDate(now))render()",page)
        self.assertNotIn("localStorage.setItem('pastQuotes",page)

    def test_nightly_message_is_rendered_without_share_button(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="nightlyMessage"', page)
        self.assertIn("updateDailyFailureQuote(localDate(new Date()))", page)
        self.assertIn('今日のひと言 · 失敗と挑戦', page)
        self.assertNotIn('shareNightQuote', page)
        self.assertNotIn('この言葉を共有', page)
        self.assertNotIn(".night-quote button{", page)
        # Article-level sharing remains available for source-attributed news.
        self.assertIn("data-share", page)
        self.assertIn("navigator.share({title:s.title,text:txt,url:articleUrl})", page)
        self.assertIn("const articleUrl=new URL(articleRouteHash(s),location.href).href", page)

    def test_editor_can_prepare_regular_or_special_issue(self):
        page = (ROOT / "editor.html").read_text(encoding="utf-8")
        for token in ('id="editionType"', 'id="specialReason"',
                      "kind==='regular'&&age>7", "editionType:kind",
                      "specialReason:reason", "if(!/^\\d{4}-\\d{2}-\\d{2}$/.test(date)"):
            with self.subTest(token=token):
                self.assertIn(token, page)

    def test_opt_in_local_notification_smoke_has_no_dispatch_side_effect(self):
        page=(ROOT / 'index.html').read_text(encoding='utf-8')
        js=(ROOT / 'notifications.js').read_text(encoding='utf-8')
        self.assertIn('id="notificationTestButton" type="button" hidden disabled',page)
        self.assertIn('Notification.permission',js)
        self.assertIn('reg.showNotification',js)
        self.assertIn("tag:'yoru9-local-test'",js)
        self.assertIn('ニュース配信ではありません。',js)
        self.assertIn('iPhoneの設定→通知',js)
        self.assertIn('User-triggered local display test',js)
    def test_push_settings_visible_but_subscribe_gated_until_backend_ready(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        cfg = __import__("json").loads((ROOT / "notification-config.json").read_text(encoding="utf-8"))
        script = (ROOT / "notifications.js").read_text(encoding="utf-8")
        self.assertTrue(cfg["enabled"])
        self.assertTrue(cfg["backendUrl"].startswith("https://"))
        self.assertIn('id="notificationSection" aria-label=', page)
        self.assertNotIn('id="notificationSection" hidden', page)
        self.assertIn('id="notificationButton" type="button" disabled', page)
        self.assertIn('夜9時の通知を受け取る', page)
        self.assertIn('notification-config.json', script)
        self.assertIn("if(!health.ready||!health.vapidPublicKey)", script)
        self.assertNotIn('area.hidden=false;', script)
        self.assertIn("if(!validConfig(x)){unavailable(", script)
        self.assertIn("unavailable('通知サービスに接続できません。", script)
        self.assertIn("details.querySelector('summary')?.focus();",script)
        self.assertIn('button.disabled=false;', script)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for JS syntax checks")
    def test_reader_and_worker_javascript_syntax(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", page, flags=re.S)
        self.assertGreaterEqual(len(scripts), 2)
        editor_page = (ROOT / "editor.html").read_text(encoding="utf-8")
        editor_scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", editor_page, flags=re.S)
        self.assertGreaterEqual(len(editor_scripts), 2)
        scripts = [item for item in scripts if item.strip()]
        sources = [("reader.js", scripts[-1]),
                   ("notifications.js", (ROOT / "notifications.js").read_text(encoding="utf-8")),
                   ("editor.js", editor_scripts[-1]),
                   ("service-worker.js", (ROOT / "service-worker.js").read_text(encoding="utf-8"))]
        for name, source in sources:
            with self.subTest(source=name), tempfile.TemporaryDirectory() as directory:
                temp = Path(directory) / name
                temp.write_text(source, encoding="utf-8")
                result = subprocess.run(["node", "--check", str(temp)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
