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
        self.assertIn("yoru9-shell-v15",worker)

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
        self.assertIn('data-smile="0" aria-pressed="false"',cover)
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
        # CSS has physically identifiable comic bubble tails and one-tap
        # sparkle feedback, with motion disabled when requested.
        self.assertIn(".spotlight .spotlight-joke::before{content:",page)
        self.assertIn(".story .teaserquip::after{content:",page)
        self.assertIn("@keyframes tinyLaughStar{",page)
        self.assertIn(".smile.smile-burst::before,.smile.smile-burst::after",page)
        self.assertIn("!window.matchMedia('(prefers-reduced-motion: reduce)').matches",page)
        self.assertIn("smile.classList.add('smile-burst')",page)
        self.assertIn("$('atlasHero').addEventListener('click',handleStoryAction)",page)
        self.assertIn("const wasOn=state.smiles.includes(i)",page)
        self.assertIn("saveState();update();",page)
        # No new story is invented or an unpublished image or source inserted.
        self.assertIn("return './assets/news/'+name",page)
        self.assertIn("const first=Array.isArray(edition.stories)?edition.stories[0]:null;",page)

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
        self.assertIn('#atlasHero .teaser-smile{flex:0 0 auto;',page)
        self.assertIn('min-height:44px',page)
        # The existing full news story remains intact, with an accessible source.
        self.assertIn("body.innerHTML=",page)
        self.assertIn("safeUrl(first.sourceUrl)",page)
        self.assertIn("updateQuipTeaser();",page)

    def test_gallery_is_the_only_default_news_index_and_detail_is_on_demand(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        cover=page[page.index('<section class="hero" id="atlasHero"'):
                   page.index('<section class="article-reader" id="articleReader"')]
        self.assertIn('id="issueGallery"',cover)
        self.assertIn('id="quipTeaserLine"',cover)
        self.assertNotIn('id="coverWorldMap"',cover)
        self.assertIn('class="article-reader" id="articleReader" aria-label="選んだニュースを読む" hidden',page)
        self.assertIn('id="readerBack"',page)
        self.assertIn('id="readerSelected"',page)
        self.assertIn("button.setAttribute('aria-controls','articleReader')",page)
        self.assertIn("button.setAttribute('aria-expanded','false')",page)
        self.assertIn("$('articleReader').hidden=true;",page)
        self.assertIn("const stage=$('articleReader');",page)
        self.assertIn("stage.hidden=false;",page)
        self.assertIn("stage.hidden=true;",page)
        self.assertIn("card.hidden=Number(card.dataset.storyIndex)!==index;",page)
        self.assertIn("$('spotlight').hidden=index!==0;",page)
        self.assertIn("$('stories').hidden=index===0;",page)
        self.assertIn("document.querySelector('.sectionhead').hidden=true;",page)
        self.assertIn("document.querySelector('.filters').hidden=true;",page)
        self.assertIn("$('intro').hidden=true;",page)
        self.assertIn("if(index===0)$('spotlightAward').textContent='このニュースの詳しい話';",page)
        self.assertIn("$('readerBack').addEventListener('click',closeArticleReader);",page)
        self.assertIn("#articleReader[hidden]{display:none!important}",page)
        self.assertIn("#articleReader .spotlight-visual,#articleReader .story-visual{display:none}",page)
        self.assertIn("#articleReader #stories .story[hidden]{display:none!important}",page)
        self.assertIn('<a class="skip-link" href="#issueGallery">ニュースを選ぶ</a>',page)
        # Article facts, evidence, original source and travel button remain in
        # the DOM for the explicitly selected article.
        self.assertIn('id="spotlightBody" class="spotlight-body" hidden',page)
        self.assertNotIn('id="worldInvitation"',page)
        self.assertIn("storyDetailHtml(s)",page)
        self.assertIn("storyEvidenceHtml(s)",page)
        self.assertIn("storyAttributionHtml(s)",page)
        self.assertIn("storyEvidenceHtml(first)",page)

    def test_mobile_news_gallery_uses_two_plus_one_without_cropped_tiles(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('data-layout="mobile-grid-2plus1"',page)
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
        self.assertIn("renderTravelSlots();updateFilters();",page)
        self.assertIn("class=\"travel-open\" data-travel=",page)
        self.assertIn('aria-expanded="false" aria-controls="travel-panel-',page)
        self.assertIn("panel.hidden=!opening",page)
        self.assertIn("if(!opening)return",page)

    def test_photos_load_only_after_explicit_travel_click(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("document.querySelector('main').addEventListener('click',async event=>{",page)
        self.assertIn("event.target.closest('[data-travel],[data-month-travel]')",page)
        self.assertIn("const stops=await loadTravelStops()",page)
        self.assertIn("fetch('./travel-stops.json',{cache:'no-store'})",page)
        self.assertIn('loading="lazy" decoding="async"',page)
        self.assertIn('data-remote-photo=',page)
        self.assertIn("let travelExplainerShown=false",page)
        self.assertIn("travelExplainerShown=true",page)
        self.assertIn("firstIntro=!travelExplainerShown",page)
        self.assertIn("function mountPhoto(stop,attempt=0)",page)
        self.assertIn("const next=chooseTravelPhoto(story,stops)",page)
        self.assertIn("ニュースをきっかけに、世界の街角へ。",page)
        self.assertIn("この写真はニュース現場の記録ではなく、旅先の風景です。",page)
        self.assertIn("(showIntro?'<p class=\"travel-disclaimer\">",page)
        self.assertNotIn("観光案内ではなく、実際の場所へ視線を向ける短い寄り道",page)
        self.assertIn("if(!img.dataset.remoteTried&&img.dataset.remotePhoto)",page)
        self.assertIn("(!isMonth&&edition.stories[i]!==story)",page)
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
                self.assertIn(stop["country"],("韓国","ブラジル","イギリス","日本","アメリカ合衆国","スペイン","アンティグア・バーブーダ","アルゼンチン","フランス"))
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
        self.assertIn("(!isMonth&&edition.stories[i]!==story)",(ROOT/"index.html").read_text(encoding="utf-8"))
        self.assertIn("travelCountryNames(story.country).includes(stop.country)",(ROOT/"index.html").read_text(encoding="utf-8"))

    def test_all_november_18_reissued_stories_have_valid_destination_photo(self):
        import json
        from country_codes import country_codes
        stops=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        issue=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
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
        self.assertIn("写真や地図は記事の証拠ではなく",block)
        self.assertIn("この国の写真はまだ準備中。",block)
        self.assertIn("掲載国を地図で見る",block)
        self.assertIn("旅先を地図で見る",block)
        self.assertIn("countryRecord(countryKeys(story.country)[0]||'')",block)
        # All trips, not just the first of the evening, show the truth marker.
        self.assertLess(block.index("'<p class=\"travel-trust\""),block.index("(showIntro?'<p class=\"travel-disclaimer\""))
        self.assertIn("panel.innerHTML=travelPostcardHtml(story,stop,firstIntro)",page)
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
          "country":country,"place":"観光の写真","region":"風景",
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

    def test_monthly_special_is_separate_from_the_nightly_issue(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="monthRetrospective" hidden',page)
        self.assertIn('id="monthCards"',page)
        self.assertLess(page.index('id="stories"'),page.index('id="monthRetrospective"'))
        self.assertLess(page.index('id="monthRetrospective"'),page.index('id="releaseStatus"'))
        self.assertIn("function validMonthStory(s)",page)
        self.assertIn("function renderMonthRetrospective()",page)
        self.assertIn("function loadMonthRetrospective()",page)
        self.assertIn("loadState();render();loadMonthRetrospective();",page)
        self.assertIn("isMonthDate(monthRetentionDate(s),start,end)",page)
        self.assertIn("new Set(edition.stories.map(s=>s.id))",page)
        self.assertIn("if(seen.has(s.id)||keys.some(key=>seenSources.has(key)))return false",page)
        self.assertIn("過去に報道された実話です。今日起きた出来事ではありません。",page)
        self.assertIn("data/retrospective/2026-11-17.json",(ROOT/"build_site.py").read_text(encoding="utf-8"))
        self.assertIn("data/retrospective/2026-11-17.json",(ROOT/"service-worker.js").read_text(encoding="utf-8"))

    def test_monthly_expanders_explicitly_show_open_and_close(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        for text in ('month-closed-label','month-open-label',
                     'month-story-closed','month-story-opened',
                     'month-chevron','month-story-chevron','記事を開く','記事を閉じる'):
            self.assertIn(text,page)
        self.assertIn('.month-story>details[open] .month-story-opened',page)
        self.assertIn('.month-retrospective>details[open] .month-open-label',page)
        self.assertIn('transform:rotate(180deg)',page)
        self.assertIn(':focus-visible',page)
        self.assertIn('prefers-reduced-motion:reduce',page)

    def test_monthly_collection_updates_only_from_published_archives(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('function monthWindow()',page)
        self.assertIn('now.getTime()-29*86400000',page)
        self.assertIn('async function updateMonthFromArchives(issues)',page)
        self.assertIn("issue.status!=='published'",page)
        self.assertIn('issue.editionDate!==item.date',page)
        self.assertIn("item.stories.map(s=>({...s,monthOrigin:'published',publishedAt:item.editionDate}))",page)
        self.assertIn('updateMonthFromArchives(m.issues)',page)
        self.assertIn('...monthPublishedStories,...monthStories',page)
        self.assertIn('if(seen.has(s.id)||keys.some(key=>seenSources.has(key)))return false',page)
        self.assertIn('配信・特集収録から30日 · ',page)
        self.assertIn('30日を過ぎるとこの一覧から外れます',page)
        self.assertIn("cache:'no-store'",page)


    def test_monthly_trip_uses_shared_postcard_component(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('data-month-travel=',page)
        self.assertIn('id="month-travel-',page)
        self.assertIn("control.nextElementSibling",page)
        self.assertIn("visibleMonthStories.find(s=>s.id===control.dataset.monthTravel)",page)
        self.assertIn("panel.innerHTML=travelPostcardHtml(story,stop,firstIntro)",page)
        self.assertIn("const stops=await loadTravelStops()",page)
        self.assertIn("control.firstChild.textContent=opening?'小旅行を閉じる ':",page)
        self.assertIn("ニュースの余韻で、30秒の小旅行",page)
        self.assertNotIn("ニュースとは別の旅先へ",page)
        self.assertNotIn("この場所に30秒だけ寄り道",page)
        self.assertNotIn("この国へ30秒だけ寄り道",page)
        self.assertIn("(isMonth&&!visibleMonthStories.includes(story))",page)
        self.assertIn('aria-expanded="false"',page)

    def test_monthly_travel_requires_explicit_reader_action(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("addEventListener('toggle',event=>{",page)
        self.assertIn("details.matches?.('.month-story > details')",page)
        self.assertNotIn("if(button&&button.getAttribute('aria-expanded')==='false')button.click()",page)
        self.assertIn('aria-expanded="false" aria-controls="month-travel-',page)
        self.assertIn("document.querySelector('main').addEventListener('click',async event=>{",page)
        self.assertIn("const control=event.target.closest('[data-travel],[data-month-travel]')",page)
        self.assertIn("const next=chooseTravelPhoto(story,stops)",page)
        self.assertIn("travelFailedPhotos.add(stop.photoAsset)",page)

    def test_monthly_countries_have_photographic_coverage(self):
        import json
        stops=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        curated=json.loads((ROOT/"data/retrospective/2026-11-17.json").read_text(encoding="utf-8"))
        needed={story["country"] for story in curated["stories"]}
        covered={stop["country"] for stop in stops.values() if stop.get("countryOnly")}
        self.assertTrue(needed.issubset(covered),needed-covered)
        photos={stop["photoAsset"] for stop in stops.values()}
        self.assertGreaterEqual(len(photos),len(curated["stories"]))
        self.assertEqual(len(photos),len({stop["photo"] for stop in stops.values()}))

    def test_monthly_postcard_appears_before_detailed_article_and_disclaimer_once(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        month=page.split("function renderMonthRetrospective(){",1)[1].split(
            "async function updateMonthFromArchives(issues)",1)[0]
        self.assertLess(month.index("'<p class=\"month-quip\">"),
                        month.index("class=\"travel-slot month-travel-slot"))
        self.assertLess(month.index("class=\"travel-slot month-travel-slot"),
                        month.index("storyDetailHtml(s)+"))
        self.assertEqual(page.count("過去に報道された実話です。今日起きた出来事ではありません。"),1)

    def test_monthly_live_updates_preserve_open_cards(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("const monthlyExpandedStories=new Set()",page)
        self.assertIn("if(details.open)monthlyExpandedStories.add(card.dataset.monthStoryId)",page)
        self.assertIn("details.open=monthlyExpandedStories.has(s.id)",page)
        self.assertIn("if(details.open)monthlyExpandedStories.add(storyId)",page)
        self.assertIn("else monthlyExpandedStories.delete(storyId)",page)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_photo_selection_never_switches_country_just_to_avoid_repetition(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        start=page.index("const travelSelections=new Map();")
        end=page.index("function travelPostcardHtml(",start)
        logic=page[start:end]
        # Small deterministic catalog: the second American article should
        # reuse a US photograph rather than mislabel a Japan photograph as US.
        payload={
          "one":{"country":"アメリカ合衆国","place":"A","region":"USA","latitude":40,"longitude":-70,
                  "photo":"https://thumb.wikimedia.org/wikipedia/commons/thumb/x/photo.jpg",
                  "photoAsset":"assets/travel/usa.jpg",
                  "photoPage":"https://commons.wikimedia.org/wiki/File:USA.jpg",
                  "licenseUrl":"https://creativecommons.org/licenses/by/4.0/"},
          "two":{"country":"日本","place":"B","region":"日本","latitude":35,"longitude":139,
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

    def test_monthly_retention_uses_actual_publish_or_collection_date(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("function isMonthDate(date,start,end)",page)
        self.assertIn("s.monthOrigin==='curated'?s.collectionDate:s.publishedAt",page)
        self.assertIn("monthOrigin:'published',publishedAt:item.editionDate",page)
        self.assertIn("monthOrigin:'curated',collectionDate:data.collectionDate",page)
        self.assertIn("s.reported.replaceAll('.','-')>monthRetentionDate(s)",page)
        self.assertNotIn("s.reported<start||s.reported>end",page)
        self.assertIn("monthRetentionDate(b).localeCompare(monthRetentionDate(a))",page)
        self.assertIn("item&&isMonthDate(item.date,start,end)",page)
        self.assertIn("配信日 ",page)
        self.assertIn("特集収録日 ",page)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for boundary test")
    def test_month_window_is_exactly_thirty_japan_dates(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        body=page.split("function isMonthDate(date,start,end){",1)[1].split("\n}",1)[0]
        code="function isMonthDate(date,start,end){"+body+"\n}\n"+\
             "if(!isMonthDate('2026-11-17','2026-10-19','2026-11-17'))process.exit(1);"+\
             "if(!isMonthDate('2026-10-19','2026-10-19','2026-11-17'))process.exit(2);"+\
             "if(isMonthDate('2026-10-18','2026-10-19','2026-11-17'))process.exit(3);"+\
             "if(isMonthDate('2026-11-18','2026-10-19','2026-11-17'))process.exit(4);"
        result=subprocess.run(["node","-e",code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


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
                      "data-smile=\"0\"", "d.slice(1).map((s,offset)"):
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
        self.assertIn("isJapaneseText(first.detail)?'<p class=\"summary\">'", page)
        self.assertIn("storyDetailHtml(first)", page)

    def test_lead_story_is_not_duplicated_and_can_expand_in_place(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="spotlightBody" class="spotlight-body" hidden', page)
        self.assertIn('id="spotlightRead" aria-expanded="false" aria-controls="spotlightBody"', page)
        self.assertIn("body.innerHTML=", page)
        self.assertIn("storyDetailHtml(first)", page)
        self.assertIn("if(show){markRead(0);panel.scrollIntoView(", page)
        self.assertIn("d.slice(1).map((s,offset)", page)
        self.assertNotIn('.story:first-child{', page)
        self.assertNotIn('今夜の１本目', page)
        self.assertIn('.story .teaserquip{', page)
        self.assertIn("data-story-index=", page)
        self.assertIn("el.closest('.story').dataset.storyIndex", page)
        self.assertNotIn("first.scrollIntoView", page)
        self.assertIn("$('spotlightBody').addEventListener('click',handleStoryAction)", page)
        self.assertIn("data-share=\"0\"", page)

    def test_filter_buttons_match_available_secondary_categories(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("function updateFilters()", page)
        self.assertIn("edition.stories.slice(1).map(s=>s.category)", page)
        self.assertIn("controls.hidden=edition.stories.length<=3||available.size<=1", page)
        self.assertIn("button.hidden=button.dataset.filter!=='all'&&!available.has(", page)
        self.assertIn(".filters[hidden],.filter[hidden]", page)
        self.assertIn("updateSpotlight();renderTravelSlots();updateFilters();applyFilter();", page)
        self.assertIn("document.querySelector('.sectionhead').hidden=d.length<=1", page)
        self.assertIn("$('intro').hidden=d.length<=1", page)

    def test_mobile_reader_typography_is_legible(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(".status #editionMessage,.edition-context,.note,.source,.storytop,.small{font-size:13px}", page)
        self.assertIn(".hero .hero-description,.hero .hero-truth{font-size:13px}", page)
        self.assertIn(".spotlight-body .summary{font-size:15px", page)
        self.assertIn(".spotlight #spotlightRead{", page)
        self.assertNotIn(".spotlight button{", page)

    def test_two_stage_ai_joke_and_nightly_payoff(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for token in ('もうひとつ、AIのひと言', 's.quipSecond',
                      'class="second-quip"', '今夜のひと言',
                      'id="nightlyMessage"'):
            self.assertIn(token, page)
        editor = (ROOT / "auto_editorial.py").read_text(encoding="utf-8")
        self.assertIn('quipSecond', editor)
        self.assertIn('distinct', editor)

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
        self.assertIn('.filter,.readbtn,.smile,.share{min-height:44px', page)
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
        self.assertIn("$('closingQuote').hidden=!nightlyLine",page)
        self.assertIn("$('closingJump').hidden=!nightlyLine",page)

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
        self.assertIn("yoru9-released-issues-v2", worker)
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
        # Source JSON stays immutable. UI doesn't give a failed 11/17
        # off-topic punchline a second life as the current homepage closing.
        self.assertIn("const nightlyLine=typeof edition.nightlyMessage==='string'?edition.nightlyMessage.trim():''",page)
        self.assertNotIn("staleClosing",page)
        self.assertIn("$('closingQuote').hidden=!nightlyLine",page)
        self.assertIn("$('closingJump').hidden=!nightlyLine",page)
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
        self.assertIn('<section class="notification-panel" id="notificationSection" hidden><details',page)
        self.assertIn('<summary>夜9時のお知らせ・通知設定</summary>',page)
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

    def test_nightly_message_is_rendered_without_share_button(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="nightlyMessage"', page)
        self.assertIn("edition.nightlyMessage", page)
        self.assertIn('今夜のひと言', page)
        self.assertNotIn('shareNightQuote', page)
        self.assertNotIn('この言葉を共有', page)
        self.assertNotIn(".night-quote button{", page)
        # Article-level sharing remains available for source-attributed news.
        self.assertIn("data-share", page)
        self.assertIn("navigator.share({title:s.title,text:txt})", page)

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
    def test_push_panel_hidden_until_backend_ready(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        cfg = __import__("json").loads((ROOT / "notification-config.json").read_text(encoding="utf-8"))
        script = (ROOT / "notifications.js").read_text(encoding="utf-8")
        self.assertTrue(cfg["enabled"])
        self.assertTrue(cfg["backendUrl"].startswith("https://"))
        self.assertIn('id="notificationSection" hidden', page)
        self.assertIn('id="notificationButton" type="button" disabled', page)
        self.assertIn('夜9時の通知を受け取る', page)
        self.assertIn('notification-config.json', script)
        self.assertIn("if(!health.ready||!health.vapidPublicKey)", script)
        self.assertIn('area.hidden=false;', script)
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
