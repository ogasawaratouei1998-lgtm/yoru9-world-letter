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
        self.assertIn("今日も世界は、", page)
        self.assertIn("ちょっとやらかした。", page)
        self.assertIn("世界の失敗・勘違い・まさかのニュースを、夜9時にお届け。", page)
        self.assertIn("あなたも自分に優しく。", page)
        self.assertIn('class="hero-description"', page)

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
        self.assertLess(cover.index('class="spotlight"'), cover.index('class="hero"'))
        for token in ('class="spotlight-award"', '<svg', 'id="spotlightTitle"',
                      'class="spotlight-divider"', 'AIツッコミ',
                      'id="spotlightQuip"', 'この話の続きへ ↓'):
            self.assertIn(token, cover)

    def test_mishap_award_is_dynamic_and_archive_aware(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for token in ('id="spotlightAward"', "今夜のやらかし大賞",
                      "前回のやらかし大賞", "体験版のやらかし大賞",
                      "data-smile=\"0\"", "d.slice(1).map((s,offset)"):
            self.assertIn(token, page)

    def test_lead_story_is_inside_main_landmark_and_summary_not_repeated(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('</header>\\n<main><section class="spotlight"', page)
        self.assertNotIn('<main><p class="release-status"', page)
        self.assertIn("isJapaneseText(first.detail)?'<p class=\\\"summary\\\">'", page)
        self.assertIn("storyDetailHtml(first)", page)

    def test_lead_story_is_not_duplicated_and_can_expand_in_place(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="spotlightBody" class="spotlight-body" hidden', page)
        self.assertIn('id="spotlightRead" aria-expanded="false" aria-controls="spotlightBody"', page)
        self.assertIn("body.innerHTML=", page)
        self.assertIn("storyDetailHtml(first)", page)
        self.assertIn("if(show){markRead(0);panel.scrollIntoView(", page)
        self.assertIn("d.slice(1).map((s,offset)", page)
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
        self.assertIn("updateSpotlight();updateFilters();applyFilter();", page)
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
        for token in ('AIツッコミ・追撃', 's.quipSecond',
                      'class="second-quip"', '今夜のオチ',
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
        self.assertLess(page.index('id="releaseStatus"'),page.index('id="stories"'))
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

    def test_nightly_closing_has_single_primary_message(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        closing = page[page.index('<section class="footerpanel">'):page.index('</section>', page.index('<section class="footerpanel">'))]
        self.assertEqual(closing.count('id="nightlyMessage"'), 1)
        self.assertIn('今日の便りは、ここまでです。', closing)
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

    def test_nightly_message_is_rendered_without_share_button(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="nightlyMessage"', page)
        self.assertIn("edition.nightlyMessage", page)
        self.assertIn('今夜のオチ', page)
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
