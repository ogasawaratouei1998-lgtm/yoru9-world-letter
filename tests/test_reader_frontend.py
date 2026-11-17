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
        self.assertIn("世界の「まさか」に、ふっとひと息。", page)
        self.assertIn("思いがけない実話と、小さなユーモアを夜9時に。", page)
        self.assertIn("気になる話を、ひとつだけ。", page)
        self.assertIn('class="hero-description"', page)

    def test_global_perspective_is_visible_and_grounded_in_incident_country(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="spotlightLocation"',page)
        self.assertIn("first.country?'この話の国・地域：'+countryLabel(first.country)",page)
        self.assertIn("今見えている場所の外にも、いろんな毎日がある。",page)
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
        self.assertIn("edition.status==='demo'?'体験版の舞台は'",page)
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
        self.assertIn("event.target.closest('[data-travel]')",page)
        self.assertIn("const stops=await loadTravelStops()",page)
        self.assertIn("fetch('./travel-stops.json',{cache:'no-store'})",page)
        self.assertIn('loading="lazy" decoding="async"',page)
        self.assertIn('data-remote-photo=',page)
        self.assertIn("if(!img.dataset.remoteTried&&img.dataset.remotePhoto)",page)
        self.assertIn("if(!panel.isConnected||panel.hidden||edition.stories[i]!==story)return",page)
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
                self.assertIn(stop["country"],("韓国","ブラジル","イギリス","アメリカ合衆国"))
                self.assertTrue(-90<=stop["latitude"]<=90)
                self.assertTrue(-180<=stop["longitude"]<=180)
                self.assertTrue(stop["photo"].startswith("https://thumb.wikimedia.org/wikipedia/commons/thumb/"))
                # Wikimedia disallows arbitrary 640px thumbnails since 2026.
                self.assertIn("/500px-",stop["photo"])
                self.assertRegex(stop["photoAsset"],r"^assets/travel/[a-z0-9-]+\.jpg$")
                self.assertTrue(stop["photoPage"].startswith("https://commons.wikimedia.org/wiki/File:"))
                self.assertTrue(stop["licenseUrl"].startswith("https://creativecommons.org/"))
                self.assertIn("ニュース現場の写真ではありません",stop["photoCaption"])
        self.assertIn("if(!panel.isConnected||panel.hidden||edition.stories[i]!==story)",(ROOT/"index.html").read_text(encoding="utf-8"))
        self.assertIn("stop.country===story.country",(ROOT/"index.html").read_text(encoding="utf-8"))

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
        self.assertIn("'yoru9-shell-v3'",worker)
        self.assertIn("travel-photo-error", (ROOT/"index.html").read_text(encoding="utf-8"))
        self.assertIn("bundle_travel_photos(root, output)",build)
        self.assertIn("data-remote-photo=", (ROOT/"index.html").read_text(encoding="utf-8"))

    def test_monthly_special_is_separate_from_the_nightly_issue(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="monthRetrospective" hidden',page)
        self.assertIn('id="monthCards"',page)
        self.assertLess(page.index('id="stories"'),page.index('id="monthRetrospective"'))
        self.assertLess(page.index('id="monthRetrospective"'),page.index('id="releaseStatus"'))
        self.assertIn("function validMonthStory(s,start,end)",page)
        self.assertIn("function renderMonthRetrospective()",page)
        self.assertIn("function loadMonthRetrospective()",page)
        self.assertIn("loadState();render();loadMonthRetrospective();",page)
        self.assertIn("s.reported<start||s.reported>end",page)
        self.assertIn("!edition.stories.some(current=>current.id===s.id)",page)
        self.assertIn("過去に報道された実話です。今日起きた出来事ではありません。",page)
        self.assertIn("data/retrospective/2026-11-17.json",(ROOT/"build_site.py").read_text(encoding="utf-8"))
        self.assertIn("data/retrospective/2026-11-17.json",(ROOT/"service-worker.js").read_text(encoding="utf-8"))

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
                      "前回のひと話", "体験版のひと話",
                      "data-smile=\"0\"", "d.slice(1).map((s,offset)"):
            self.assertIn(token, page)

    def test_lead_story_is_inside_main_landmark_and_summary_not_repeated(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('</header>\n<main><section class="evening-entry"', page)
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
        self.assertIn("controls.hidden=available.size<=1", page)
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
                      "const country=countryKey(story.country);","country-catalog.json"):
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
        self.assertIn("yoru9-shell-v3", worker)
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
