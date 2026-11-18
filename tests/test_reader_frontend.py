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
        self.assertIn("世界の「やらかし」に、AIが本気でツッコむ。",page)
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
        self.assertIn("yoru9-shell-v11",worker)

    def test_global_perspective_is_visible_and_grounded_in_incident_country(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="spotlightLocation"',page)
        self.assertIn("first.country?'舞台：'+countryLabel(first.country)",page)
        self.assertIn("世界の「やらかし」に、AIが本気でツッコむ。",page)
        self.assertIn('id="worldInvitation" href="#mapExtras"',page)
        self.assertIn("$('worldInvitation').addEventListener('click',event=>{",page)
        self.assertIn("map.open=true;",page)
        self.assertIn("window.matchMedia('(prefers-reduced-motion: reduce)')",page)
        self.assertIn(".world-invitation:focus-visible",page)

    def test_world_countries_are_readable_before_the_first_story(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('class="issue-countries" id="issueCountries"',page)
        self.assertLess(page.index('id="issueCountries"'),page.index('id="spotlightTitle"'))
        self.assertIn("function renderIssueCountries()",page)
        self.assertIn("const names=new Map()",page)
        self.assertIn("countryKey(country)",page)
        self.assertIn("countryLabel(country)",page)
        self.assertIn("if(country&&key&&!names.has(key))",page)
        self.assertIn("renderWorld();renderIssueCountries();",page)
        self.assertIn("renderIssueCountries();updateSpotlight();renderTravelSlots();updateFilters();",page)
        self.assertIn("edition.status==='demo'?'体験版の舞台'",page)
        self.assertNotIn("sourcecountry",page)

    def test_reading_flow_prioritizes_stories_over_release_metadata(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertLess(page.index('id="issueCountries"'),page.index('id="spotlight"'))
        self.assertLess(page.index('id="spotlight"'),page.index('id="stories"'))
        self.assertLess(page.index('id="stories"'),page.index('class="issue-details"'))
        self.assertLess(page.index('class="issue-details"'),page.index('id="exploreExtras"'))
        self.assertLess(page.index('id="exploreExtras"'),page.index('id="closing"'))
        self.assertIn('もうひとつ、世界のどこかから',page)
        self.assertIn('id="worldInvitation" href="#mapExtras"',page)
        self.assertIn("map.open=true;",page)
        self.assertIn('id="releaseStatus"',page)
        self.assertIn('id="dateGuide"',page)

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
                self.assertIn(stop["country"],("韓国","ブラジル","イギリス","日本","アメリカ合衆国","スペイン","アンティグア・バーブーダ"))
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
        self.assertLess(page.index('id="spotlightRead"'),page.index('id="worldInvitation"'))
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
        second=page[page.index("d.slice(1).map((s,offset)"):page.index("renderIssueCountries();updateSpotlight()")]
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

    def test_stories_before_collapsed_exploration_and_release_status(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertLess(page.index('id="stories"'),page.index('id="exploreExtras"'))
        self.assertLess(page.index('id="stories"'),page.index('id="releaseStatus"'))
        self.assertIn('function displayReleaseStatus()',page)
        self.assertIn('本日分の公開後に自動更新します。',page)
        self.assertIn('<summary>過去の配信を読む</summary>',page)
        self.assertIn('<summary>世界地図を見る</summary>',page)
        self.assertLess(page.index('id="archiveExtras"'),page.index('id="mapExtras"'))

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

    def test_initial_render_does_not_read_uninitialized_archive_menu(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        startup = page.index("loadState();render();")
        declaration = page.index("const archiveMenu=$('archiveSelect');")
        self.assertLess(startup, declaration)
        status = page[page.index("function displayReleaseStatus(){"):page.index("function render(){")]
        self.assertIn("$('archiveSelect').value", status)
        self.assertNotIn("archiveMenu.value", status)

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
        self.assertIn('今日の便りは、ここまで。', closing)
        self.assertNotIn('完璧じゃないのは', closing)

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
                      "for(const country of countryKeys(story.country))","country-catalog.json"):
            self.assertIn(token,page)
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        self.assertIn("'country-catalog.json'",build)

    def test_full_country_catalog_and_truthful_lifetime_scoreboard_are_exposed(self):
        import json
        from tempfile import TemporaryDirectory
        from build_site import build_country_coverage
        catalog=json.loads((ROOT/"country-catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(len(catalog),196)
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        for marker in ("function countryKeys(name)",
                       "loadLifetimeCoverage()",
                       "country-coverage.json",
                       "累計：","未紹介",
                       "countryKeys(story.country)",
                       "countryKeys(s.country).includes(country)"):
            self.assertIn(marker,page)
        with TemporaryDirectory() as tmp:
            from pathlib import Path
            result=build_country_coverage(ROOT,Path(tmp))
            report=json.loads((Path(tmp)/"data/country-coverage.json").read_text(encoding="utf-8"))
        self.assertEqual(result,report)
        self.assertEqual(report["total"],196)
        self.assertEqual(report["covered"],len(report["byCountry"]))
        self.assertEqual(report["remaining"],196-report["covered"])
        self.assertIn("US",report["byCountry"])
        self.assertIn("GB",report["byCountry"])
        self.assertIn("AG",report["byCountry"])
        self.assertNotIn("sourcecountry",report)
        self.assertEqual(report["basis"],"published-archive-only")

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

    def test_editor_dashboard_has_30_day_country_and_region_coverage(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for token in ('id="editorDashboard"', 'id="editorStats"',
                      'id="editorMapPins"', 'id="editorRegionStats"',
                      'id="editorCountryStats"', 'function editorialRegion(country)',
                      'function renderEditorialDashboard(issues,failed=0)',
                      'if(age<0||age>=30)continue',
                      "issue?.status!=='published'",
                      'renderEditorialDashboard(all.filter(Boolean)'):
            with self.subTest(token=token):
                self.assertIn(token, page)

    def test_world_map_uses_visible_monthly_stories_and_links_to_special(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        for text in (
            "function mapDisplayStories()",
            "[...edition.stories,...visibleMonthStories]",
            "for(const story of mapDisplayStories())",
            "function countryResultsFor(country)",
            "visibleMonthStories.filter(s=>countryKeys(s.country).includes(country))",
            "const matches=countryResultsFor(country)",
            "card.dataset.monthStoryId=s.id",
            "node.dataset.monthStoryId===item.id",
            "$('monthDetails').open=true",
            "if(details)details.open=true",
            "renderWorld();refreshCountryChoices();refreshMonthlyDashboard();",
            "表示中の配信号と月間特集の掲載国",
        ):
            with self.subTest(marker=text):
                self.assertIn(text,page)
        self.assertIn("配信号と月間特集の記事を探せます",page)

    def test_monthly_special_appears_in_30_day_editorial_coverage(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        for token in (
            "function refreshMonthlyDashboard()",
            "let dashboardIssues=[],dashboardFailed=0",
            "for(const story of monthStories)",
            "isMonthDate(monthRetentionDate(story),monthWindow().start,now)",
            "if(usedIds.has(story.id)||keys.some(key=>usedSources.has(key)))",
            "特集収録'+curated+'本",
            "pin.addEventListener('click',()=>{",
            "renderEditorialDashboard(all.filter(Boolean),all.filter(x=>!x).length)",
        ):
            with self.subTest(marker=token):
                self.assertIn(token,page)
        self.assertIn("国・地域の累計紹介数は公開済みの過去号から集計",page)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for map behavior test")
    def test_world_map_pins_count_current_and_monthly_articles(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        funcs="function mapDisplayStories(){"+page.split("function mapDisplayStories(){",1)[1].split("function includeCurrentCountries(){",1)[0]
        js=r"""
const edition={stories:[{id:'now',country:'日本'}]};
const visibleMonthStories=[
 {id:'old-a',country:'韓国'},
 {id:'old-b',country:'韓国'},
 {id:'now',country:'日本'}
];
const dom={
 mapPins:{children:[],replaceChildren(){this.children=[]},append(x){this.children.push(x)}},
 mapCaption:{textContent:''},
 countrySelect:{value:'',options:[],scrollIntoView(){this.didScroll=true}}
};
const $=id=>dom[id];
const countryKey=name=>({'韓国':'KR','日本':'JP'})[name]||name;
const countryKeys=name=>[countryKey(name)];
const countryRecord=name=>({'KR':{name:'韓国'},'JP':{name:'日本'}})[name]||null;
const countryLabel=name=>({'KR':'韓国','JP':'日本'})[name]||name;
const mapPoint=name=>name==='JP'?[80,25]:[77,27];
let selected=0;
const showCountryResults=()=>{selected++};
const document={createElement:()=>({
 style:{},setAttribute(name,value){this[name]=value},
 addEventListener(name,callback){if(name==='click')this.click=callback}
})};
"""
        assertions=r"""
if(mapDisplayStories().length!==3)process.exit(1);
renderWorld();
if(dom.mapPins.children.length!==2)process.exit(2);
const countries=Object.fromEntries(dom.mapPins.children.map(p=>[p['aria-label'],p.textContent]));
if(countries['韓国：配信号と月間特集に2本']!=='2')process.exit(3);
if(countries['日本：配信号と月間特集に1本']!=='1')process.exit(4);
if(!dom.mapCaption.textContent.includes('韓国'))process.exit(5);
dom.mapPins.children.find(p=>p.textContent==='2').click();
if(dom.countrySelect.value!=='KR'||selected!==1||!dom.countrySelect.didScroll)process.exit(6);
"""
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/"map-test.js"
            script.write_text(js+"\n"+funcs+"\n"+assertions,encoding="utf-8")
            p=subprocess.run(["node",str(script)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)

    def test_iphone_refinement_keeps_atlas_and_removes_duplicate_metadata(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="atlasLede"',page)
        self.assertIn("currentIssue?'今夜の「まさか」は、どこの国から？':'この号の「まさか」は、どこの国から？'",page)
        self.assertIn("const count=Math.max(0,edition.stories.length-1)",page)
        self.assertIn("$('progress').hidden=count<=3",page)
        self.assertIn(".atlas-brand{display:none}",page)
        self.assertIn(".spotlight h1{font-size:clamp(1.31rem",page)
        self.assertIn(".atlas-map-caption{font-size:.73rem}",page)
        # Source JSON stays immutable. UI doesn't give a failed 11/17
        # off-topic punchline a second life as the current homepage closing.
        self.assertIn("edition.editionDate==='2026-11-17'&&nightlyOriginal===staleClosing",page)
        self.assertIn("$('closingQuote').hidden=!nightlyLine",page)
        self.assertIn("$('closingJump').hidden=!nightlyLine",page)
        self.assertIn("この号の「まさか」",page)
        self.assertIn("ニュースの現場ではありません",page)
        self.assertIn("map.open=true",page)

    def test_atlas_country_previews_only_published_issue_stories(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('class="atlas-preview" id="atlasPreview"',page)
        self.assertIn('aria-live="polite" hidden></section>',page)
        self.assertIn('.atlas-preview[hidden]{display:none!important}',page)
        self.assertIn('function showAtlasPreview(code,trigger)',page)
        self.assertIn('function closeAtlasPreview(restoreFocus=false)',page)
        self.assertIn('function openAtlasStory(index)',page)
        self.assertIn("edition.stories.map((story,index)=>({story,index}))",page)
        self.assertIn(".filter(item=>countryKeys(item.story.country).some(key=>selectedCodes.includes(key)))",page)
        self.assertIn("label.textContent=story.title||'掲載記事'",page)
        self.assertIn('read.dataset.atlasRead=String(index)',page)
        self.assertIn('read.addEventListener(\'click\',()=>openAtlasStory(index))',page)
        self.assertIn("closeAtlasPreview();openWorldExplorer(code)",page)
        self.assertIn("showAtlasPreview(code,button)",page)
        self.assertIn("showAtlasPreview(code,chip)",page)
        self.assertIn("aria-controls','atlasPreview'",page)
        self.assertIn("aria-pressed','false'",page)
        self.assertIn("if(index===0)",page)
        self.assertIn("filter='all';applyFilter()",page)
        self.assertIn("card.querySelector('[data-open=\"'+index+'\"]')",page)
        self.assertIn("panel.replaceChildren()",page)
        self.assertIn("panel.hidden=false",page)
        self.assertIn("panel.hidden=true",page)
        # Never interpolate untrusted source titles into raw HTML or use
        # source discovery markets as the article's incident location.
        block=page[page.index("function showAtlasPreview(code,trigger)"):
                   page.index("function openWorldExplorer(country='')")]
        self.assertNotIn('innerHTML',block)
        self.assertNotIn('sourcecountry',block)
        self.assertNotIn('visibleMonthStories',block)
        self.assertLess(page.index('id="coverMapPins"'),page.index('id="atlasPreview"'))

    def test_atlas_cover_maps_only_article_countries_and_opens_archive(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="coverWorldMap"',page)
        self.assertIn('id="coverWorldCoastlines"',page)
        self.assertIn('id="coverMapPins"',page)
        self.assertIn('id="atlasStoryCount"',page)
        self.assertIn('id="coverWorldLink"',page)
        self.assertIn('function renderCoverMap()',page)
        self.assertIn("for(const story of edition.stories)",page)
        self.assertIn("for(const country of countryKeys(story.country))",page)
        self.assertIn("const point=mapPoint(code)",page)
        self.assertIn("openWorldExplorer(code)",page)
        self.assertIn("renderCoverMap();",page)
        self.assertIn("$('coverWorldCoastlines').innerHTML=svg.innerHTML",page)
        self.assertIn("ニュースの現場ではありません",page)
        self.assertLess(page.index('id="coverWorldMap"'),page.index('id="spotlightTitle"'))
        # The atlas is a locator of *published incident country*, not a
        # second listing of publishers' source markets or unverified leads.
        block=page[page.index("function renderCoverMap(){"):page.index("function renderIssueCountries(){")]
        self.assertNotIn("sourcecountry",block)
        self.assertNotIn("registeredSource",block)
        self.assertNotIn("visibleMonthStories",block)

    def test_footer_trust_note_is_readable_but_not_an_extra_huge_card(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('<details class="disclosure-details">',page)
        self.assertIn('<summary>編集方針・出典と配信情報について</summary>',page)
        self.assertIn('<aside class="note" id="disclosure">',page)
        self.assertIn('.disclosure-details>summary{min-height:44px',page)

    def test_world_map_and_country_archive(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for token in ('id="worldMap"', 'id="mapPins"', 'id="countrySelect"',
                      'id="countryResults"', 'function renderWorld()',
                      'async function loadCountryIndex(issues)', 'showCountryResults()',
                      "data.status==='published'", 'renderWorld();'):
            with self.subTest(token=token):
                self.assertIn(token, page)

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
        self.assertIn('また、気が向いた夜に。',page)
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
