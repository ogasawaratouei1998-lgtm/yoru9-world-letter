#!/usr/bin/env python3
"""Independent 30-day research for the monthly shelf. Never publish raw leads.

Only verified firsthand reporting from a vetted publisher, or independently
corroborated articles from two publishers, can pass editor A and adversarial
fact-checker B before joining the published monthly data. The 9pm release and historical curated collection are
deliberately untouched.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlencode, urlsplit, parse_qs
from zoneinfo import ZoneInfo
import json
import os
import re
import sys

import auto_editorial as editorial
from collect_candidates import (
    BBC_FEEDS, GDELT, INDEPENDENT_FEEDS, LOCAL_LANGUAGE_FEEDS,
    fetch_bytes, parse_rss, safe_url,
)

JST = ZoneInfo("Asia/Tokyo")
ROOT = Path(__file__).resolve().parent
MONTH_ROOT = Path("data/monthly")
DAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{8,95}$")
CATEGORIES = {"person", "work", "company", "sports"}
# This preference filters retrieval, NOT evidence. All factual claims need fetched original article bodies.
MISHAP = re.compile(
    r"mistak|mix.?up|blunder|typo|accidental|misprint|wrong|error|mishap|"
    r"mistaken|confus|apolog|fail|backfir|oops|embarrass|misstep|oddity|"
    r"unusual|unexpected|odd |weird|mixing up|changed plans|"
    r"手違い|誤配達|間違|勘違い|失敗|珍事|誤記|謝罪|撤回|おわび|予想外|"
    r"Verwechslung|Panne|méprise|equivocación|실수|착각|por engano", re.I
)
GDELT_QUERIES = (
    '("mix-up" OR "blunder" OR "typo")',
    '("accidentally" OR "by mistake" OR "mishap")',
)
# Bing News RSS keeps a verifiable publisher address in the "url" parameter.
# It is a DISCOVERY source only; original publisher bodies must still be fetched.
BING_QUERIES = (
    ('"mix-up"', "en-US"),
    ('"wrong delivery"', "en-US"),
    ('"typo"', "en-GB"),
    ('"blunder"', "en-GB"),
    ("誤配達", "ja-JP"),
    ("勘違い", "ja-JP"),
)
REQUIRED = ("id", "country", "category", "categoryLabel", "label",
            "title", "summary", "detail", "quip",
            "sourceName", "sourceUrl", "reported", "expectedPlan",
            "observedOutcome", "eventKey")
# Distinct domains are required, but this list catches some obvious same-owner mirrors.
SAME_PUBLISHER = (
    {"bbc.co.uk", "bbc.com"},
    {"theguardian.com", "guardian.co.uk"},
)
# A one-source story must be an original news report on a known publisher's
# domain. These domains are reviewed in code, not inferred from RSS names or AI
# assertions. Other sites may still qualify when TWO independent reports agree.
TRUSTED_ORIGINAL_PUBLISHERS = (
    "bbc.com", "bbc.co.uk", "theguardian.com", "guardian.co.uk",
    "npr.org", "cbsnews.com", "nbcnews.com", "nytimes.com",
    "abc.net.au", "cbc.ca", "france24.com", "lemonde.fr",
    "dw.com", "elpais.com", "japantimes.co.jp", "thehindu.com",
    "globo.com", "premiumtimesng.com", "inquirer.net",
    "reuters.com", "apnews.com", "nhk.or.jp", "kyodonews.net",
)
REVIEW_METHOD = "source-quality-two-stage-AI"
LEGACY_REVIEW_METHOD = "two-source-two-stage-AI"
# A concise monthly-only brief replaces the nightly pipeline's elaborate
# editorial mission. The factual checks below remain independent and strict.
MONTHLY_BRIEF = (
    "Yoru9 is a quiet Japanese evening news app featuring real, gentle, "
    "surprising incidents. Prefer specific everyday miscommunications, "
    "small harmless mix-ups and unexpected outcomes, not celebrity or "
    "corporate importance. Facts come ONLY from the fetched publisher "
    "article bodies. Give a clear short Japanese account and one warm "
    "observational joke about the mismatch, never a victim or individual. "
    "No invented details, sensationalism, clichés, reader advice or "
    "forced optimism. Reject rumor, private-life allegations, injury, "
    "tragedy, or unfounded claims. Fewer safe, sourced stories are better "
    "than filling a quota. "
)


def date_window(today):
    return today - timedelta(days=29), today


def safe_day(value):
    if not isinstance(value, str) or not DAY_PATTERN.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def lead_day(lead):
    raw = str(lead.get("seendate", ""))
    if not raw:
        return None
    try:
        if re.fullmatch(r"\d{8}T\d{6}Z", raw):
            date = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        elif DAY_PATTERN.fullmatch(raw):
            date = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=JST)
        else:
            date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if not date.tzinfo:
                return None
        return date.astimezone(JST).date()
    except ValueError:
        return None


def bing_publisher_url(raw):
    """Resolve only the URL parameter of Bing's RSS apiclick wrapper.

    Neither Bing headlines nor this URL is considered evidence. The destination
    must still pass safe URL/host checks and later source-text verification.
    """
    try:
        parts = urlsplit(str(raw))
        if (parts.scheme != "https"):
            return None
        if parts.hostname not in ("bing.com", "www.bing.com"):
            # Never accept a lookalike apiclick wrapper on an untrusted host.
            if parts.path.endswith("/news/apiclick.aspx") or "url" in parse_qs(parts.query):
                return None
            return raw if safe_url(raw) == raw and editorial.public_host(raw) else None
        if parts.path != "/news/apiclick.aspx":
            return None
        candidates = parse_qs(parts.query).get("url", [])
        if len(candidates) != 1:
            return None
        destination = candidates[0]
        if safe_url(destination) != destination or not editorial.public_host(destination):
            return None
        return destination
    except (ValueError, TypeError):
        return None


def publisher_pair(urls):
    if (not isinstance(urls, list) or len(urls) != 2 or
            len(set(urls)) != 2):
        return False
    hosts = [editorial.host(u) for u in urls]
    if not all(hosts) or hosts[0] == hosts[1]:
        return False
    if any(set(hosts).issubset(group) for group in SAME_PUBLISHER):
        return False
    return all(safe_url(u) == u and editorial.public_host(u) for u in urls)


def trusted_original_url(url):
    """Allow a single original publisher report only on an explicitly vetted host.

    Domain presence alone NEVER proves firsthand reporting. The original
    publisher body and adversarial audit must establish that separately.
    """
    if safe_url(url) != url or not editorial.public_host(url):
        return False
    host = editorial.host(url)
    return any(host == domain or host.endswith("." + domain)
               for domain in TRUSTED_ORIGINAL_PUBLISHERS)


def source_urls_ok(urls):
    if not isinstance(urls, list):
        return False
    if len(urls) == 1:
        return trusted_original_url(urls[0])
    return publisher_pair(urls)


def discover(now, fetch=fetch_bytes):
    """Collect direct publisher URLs seen within 30 JST calendar days.

    The locale/sourcecountry of the publisher is never the incident country.
    A date on an RSS/GDELT lead is only a retrieval filter, NOT verification.
    """
    start, end = date_window(now.date())
    candidates, seen, problems = [], set(), []
    def add(lead):
        if len(candidates) >= 150:
            return
        url = lead.get("url", "")
        if (url in seen or safe_url(url) != url or
                not editorial.public_host(url) or
                not MISHAP.search(str(lead.get("title", ""))) or
                editorial.BLOCK.search(str(lead.get("title", "")))):
            return
        seen_day = lead_day(lead)
        if seen_day is None or not start <= seen_day <= end:
            return
        seen.add(url)
        candidates.append(lead)

    gdelt_rows = 0
    for query in GDELT_QUERIES:
        params = {"query": query, "mode": "ArtList", "format": "json",
                  "maxrecords": "125", "timespan": "30d", "sort": "DateDesc"}
        try:
            data = json.loads(fetch(GDELT + "?" + urlencode(params)).decode("utf-8"))
            articles = data.get("articles", [])
            gdelt_rows += len(articles) if isinstance(articles, list) else 0
            for item in articles:
                add({"title": str(item.get("title", ""))[:400],
                     "url": str(item.get("url", "")),
                     "seendate": str(item.get("seendate", "")),
                     "sourcecountry": str(item.get("sourcecountry", "")),
                     "provider": "GDELT 30-day research"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            problems.append(type(exc).__name__)

    # A second keyless discovery source helps when GDELT is rate-limited.
    # The apiclick wrapper is never stored as a source or publisher URL.
    bing_added, bing_rows, bing_resolved = 0, 0, 0
    for query, market in BING_QUERIES:
        params = {"q": query, "format": "rss", "setmkt": market}
        try:
            rss = parse_rss(fetch("https://www.bing.com/news/search?" + urlencode(params)),
                            "Bing News RSS", sourcecountry="未確認")
            bing_rows += len(rss)
            for item in rss:
                publisher = bing_publisher_url(item["url"])
                if publisher:
                    bing_resolved += 1
                    before = len(candidates)
                    add({**item, "url": publisher, "provider": "Bing News publisher discovery"})
                    bing_added += len(candidates) - before
        except (OSError, ValueError, TypeError, KeyError) as exc:
            problems.append(type(exc).__name__)
    print("Monthly GDELT raw rows:", gdelt_rows,
          "Bing RSS rows:", bing_rows,
          "decoded publisher URLs:", bing_resolved,
          "Bing dated relevant leads:", bing_added, flush=True)
    # Direct editorial publishers broaden geography and provide real bodies.
    for url, provider, language, country in LOCAL_LANGUAGE_FEEDS[:8]:
        try:
            for lead in parse_rss(fetch(url), provider, language=language,
                                  sourcecountry=country)[:35]:
                add(lead)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            problems.append(type(exc).__name__)
    for url, provider in INDEPENDENT_FEEDS:
        try:
            for lead in parse_rss(fetch(url), provider)[:35]:
                add(lead)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            problems.append(type(exc).__name__)
    for url in BBC_FEEDS:
        try:
            for lead in parse_rss(fetch(url), "BBC RSS", relevant_only=True)[:35]:
                add(lead)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            problems.append(type(exc).__name__)
    print("Monthly discovery:", len(candidates), "dated direct leads;",
          len(problems), "feed failures", flush=True)
    return candidates


def candidate_pairs(leads, ask_ai=editorial.ai):
    """Shortlist originals directly; independently corroborated pairs come first.

    A separate AI call just to match two headlines was an unnecessary gate:
    headlines can suggest duplication, but only fetched publisher bodies can
    establish whether two sources cover the same event.
    """
    allowed = {x["url"]: x for x in leads}
    pairs, seen = [], set()
    for group in editorial.corroboration_groups(leads):
        if len(group)<2:
            continue
        urls=[group[0]["url"],group[1]["url"]]
        key=tuple(sorted(urls))
        if key in seen or not publisher_pair(urls) or any(u not in allowed for u in urls):
            continue
        seen.add(key)
        pairs.append([allowed[u] for u in urls])
        if len(pairs)>=4:
            break
    # Each vetted original report has its own chance, including when a
    # tentative two-publisher match turns out to be wrong or syndicated.
    singles=[[lead] for lead in leads if trusted_original_url(lead["url"])]
    result=pairs+singles[:max(0,18-len(pairs))]
    print("Monthly source shortlist:", len(pairs), "potential pairs,",
          len(result)-len(pairs), "original publisher articles",flush=True)
    return result


def existing_articles(root=ROOT):
    """All public issued/curated monthly items, not drafts or raw candidates."""
    files = [root / "data/current.json"]
    files += sorted((root / "data/archive").glob("????-??-??.json"))
    files += sorted((root / "data/retrospective").glob("????-??-??.json"))
    files += sorted((root / "data/monthly").glob("????-??-??.json"))
    result, by_id, by_url, by_event = [], set(), set(), set()
    for file in files:
        try:
            document = json.loads(file.read_text(encoding="utf-8"))
            if document.get("status") not in ("published", "published-retrospective", "published-monthly"):
                continue
            for item in document.get("stories", []):
                if not isinstance(item, dict):
                    continue
                by_id.add(item.get("id"))
                by_event.add(item.get("eventKey"))
                by_url.update(item.get("verificationUrls", []) if isinstance(item.get("verificationUrls"), list) else [])
                by_url.add(item.get("sourceUrl"))
                result.append({"title": item.get("title", ""),
                               "summary": str(item.get("summary", ""))[:240],
                               "country": item.get("country", "")})
        except (OSError, ValueError, TypeError):
            continue
    return result[-150:], by_id, by_url, by_event


def plausible_new(story, existing):
    summaries, ids, urls, events = existing
    if (story["id"] in ids or story["eventKey"] in events or
            any(u in urls for u in story["verificationUrls"])):
        return False
    title = story["title"]
    return not any(
        old["country"] == story["country"] and
        SequenceMatcher(None, title, str(old["title"])).ratio() >= 0.75
        for old in summaries
    )


def validate_story(story, urls, today):
    if not isinstance(story, dict) or any(
        not isinstance(story.get(k), str) or not story[k].strip() for k in REQUIRED
    ):
        return False
    if (not SLUG_PATTERN.fullmatch(story["id"]) or
            not 12 <= len(story["eventKey"]) <= 150 or
            story["category"] not in CATEGORIES or
            not editorial.country_code(story["country"]) or
            not (28 <= len(story["summary"]) <= 650 and
                 75 <= len(story["detail"]) <= 2100) or
            not (10 <= len(story["quip"]) <= 90) or
            (story.get("quipSecond") is not None and (
                not isinstance(story["quipSecond"], str) or
                not 10 <= len(story["quipSecond"].strip()) <= 100 or
                story["quip"].strip() == story["quipSecond"].strip())) or
            editorial.editorial_fit_rejection(story)):
        return False
    reported = safe_day(story["reported"])
    if reported is None or not date_window(today)[0] <= reported <= today:
        return False
    verification = story.get("verificationUrls")
    if not source_urls_ok(verification) or not source_urls_ok(urls) or verification != urls:
        return False
    basis = "original-report" if len(verification)==1 else "independent-reports"
    if story.get("sourceBasis")!=basis:
        return False
    if story["sourceUrl"] not in verification:
        return False
    narrative = " ".join(str(story[k]) for k in REQUIRED if k not in
                         ("id", "sourceUrl", "reported", "eventKey"))
    if isinstance(story.get("quipSecond"),str):
        narrative += " " + story["quipSecond"]
    if editorial.BLOCK.search(narrative) or editorial.PRIVATE_GOSSIP.search(narrative):
        return False
    if editorial.READER_PRESSURE.search(narrative):
        return False
    return True


def monthly_source_text(url):
    """Short original reporting is eligible, but still article-body only."""
    return editorial.source_text(url,min_chars=350)


def make_story(group, today, old_summaries, ask_ai=editorial.ai,
               source_reader=None):
    urls = [item["url"] for item in group]
    if not source_urls_ok(urls):
        return None
    single = len(urls)==1
    evidence = []
    source_reader = source_reader or monthly_source_text
    for item in group:
        text = source_reader(item["url"])
        if not isinstance(text, str) or len(text)<350:
            return None
        evidence.append({"url": item["url"], "headline": item["title"],
                         "published": str(lead_day(item)),
                         "body": text[:10000]})
    evidence_rule = (
        "ONE vetted news publisher's firsthand original reporting is available. "
        "The original BODY must contain concrete, firsthand-reported facts, not "
        "just a press release, social media post, alleged anecdote, viral claim, "
        "rewritten wire report or third-party attribution. A trustworthy domain "
        "alone is NOT evidence. If you cannot confirm original reporting in "
        "the actual retrieved body, return null. Do not claim a second source. "
        if single else
        "TWO independent publishers' article BODIES must confirm the same "
        "specific incident. Reject syndicated rewrites, common wire copy, "
        "or different events."
    )
    directive = (
        MONTHLY_BRIEF +
        " You are monthly editor A. Draft at most ONE Japanese news story "
        "only when the evidence meets this source rule: " + evidence_rule +
        " The article must describe a real harmless, specific, human-scale "
        "surprising mismatch between an intended plan and the observed outcome. "
        "Reject emergencies, fear, harm, unverified personal anecdotes, "
        "private allegations, and corporate crises. A headline, search snippet, "
        "or publisher reputation cannot establish a claim. Every fact, incident "
        "country, expectedPlan, observedOutcome and the reporting date must "
        "be supported directly by the retrieved original article text. "
        "Do not invent quotes, motives or a happy ending. "
        "The date must be between " + str(date_window(today)[0]) +
        " and " + str(today) + ". "
        "Return JSON {story:object|null} using fields " + str(REQUIRED) +
        " plus verificationUrls containing the EXACT supplied URLs in order. "
        "quipSecond is OPTIONAL: supply it only when it adds a genuinely "
        "different, source-supported lighthearted observation. "
        "Do not invent a second URL or an official statement. "
        "The story's sourceName must accurately identify its original outlet. "
        "Return null on uncertainty. Previously released stories: " +
        json.dumps(old_summaries[-70:], ensure_ascii=False) +
        " Retrieved article bodies: " + json.dumps(evidence, ensure_ascii=False)
    )
    try:
        draft = ask_ai(directive, temperature=0.4)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        print("Monthly draft unavailable:", type(exc).__name__, flush=True)
        return None
    story = draft.get("story") if isinstance(draft, dict) else None
    if not isinstance(story, dict):
        return None
    # The AI cannot self-assert which verification tier it belongs to.
    story["sourceBasis"] = "original-report" if single else "independent-reports"
    if not story.get("quipSecond"):
        story.pop("quipSecond",None)
    if not validate_story(story, urls, today):
        return None
    try:
        verdict = ask_ai(
            MONTHLY_BRIEF +
            " You are adversarial fact checker B, INDEPENDENT of editor A. "
            "Check every substantive factual statement in the Japanese title, "
            "summary, detail, expectedPlan, observedOutcome, reported date and "
            "event country against the actual retrieved article body or bodies. "
            "Reject vague anecdotes, unsupported motives, harmful jokes, "
            "syndicated PR, stale news, uncertainty, omissions that change "
            "meaning, and misleading certainty. For a ONE-PUBLISHER submission, "
            "you MUST verify firsthand original publisher reporting rather "
            "than a summary of SNS posts, rumors or other outlets; do not demand "
            "another publisher or claim corroboration. For a TWO-PUBLISHER "
            "submission, verify distinct independent reporting of the SAME "
            "incident, not identical syndicated copy. A title and RSS date "
            "alone NEVER verify a story. Reject if a source is incomplete, "
            "does not explicitly support the precise expectation and outcome, "
            "or fails to establish a reliable reported date. "
            "Be conservative. Only approve entirely substantiated, "
            "non-tragic, respectful stories. Return JSON with EXACT fields "
            "{approved:boolean,factsVerified:boolean,originalReporting:boolean,"
            "dateVerified:boolean,safeTone:boolean,"
            "independent:boolean,bothSourcesSupport:boolean,reasonCode:string}. "
            "For ONE source, independent and bothSourcesSupport should be false; "
            "for TWO sources, both must be true. Draft: " +
            json.dumps(story, ensure_ascii=False) +
            " Retrieved original article body or bodies: " +
            json.dumps(evidence, ensure_ascii=False),
            temperature=0.1
        )
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        print("Monthly fact check unavailable:", type(exc).__name__, flush=True)
        return None
    if not isinstance(verdict, dict) or any(
        verdict.get(field) is not True
        for field in ("approved", "factsVerified", "originalReporting",
                      "dateVerified", "safeTone")
    ):
        return None
    if not single and not (verdict.get("independent") is True
                           and verdict.get("bothSourcesSupport") is True):
        return None
    if single and (verdict.get("independent") is True
                   or verdict.get("bothSourcesSupport") is True):
        return None
    if single:
        story["attributionNote"] = (
            "報道機関1社の独自取材記事を確認しています。"
            "別媒体による独立した裏付けは確認できていません。"
        )
    else:
        # Never claim independent reporting beyond the two audited original texts.
        story.pop("attributionNote", None)
    return {key: value for key, value in story.items()
            if key in (*REQUIRED, "verificationUrls", "sourceBasis",
                       "attributionNote", "correctionNote")}


def publish_monthly(stories, today, root=ROOT):
    """Write immutable daily monthly collections and an index; no empty release."""
    if not stories:
        return False
    folder = root / MONTH_ROOT
    file = folder / (today.isoformat() + ".json")
    if file.exists():
        return False
    folder.mkdir(parents=True, exist_ok=True)
    for story in stories:
        if not validate_story(story, story.get("verificationUrls", []), today):
            raise ValueError("Story failed monthly release validation")
    obj = {"status": "published-monthly",
           "collectionDate": today.isoformat(),
           "reviewMethod": REVIEW_METHOD,
           "stories": stories}
    # Never re-date older verified articles as if they had been published today:
    # collectionDate means first inclusion in this monthly shelf.
    file.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    index = folder / "index.json"
    issues = []
    if index.exists():
        doc = json.loads(index.read_text(encoding="utf-8"))
        issues = doc.get("issues", []) if isinstance(doc.get("issues"), list) else []
    dates = {x.get("date") for x in issues if isinstance(x, dict)}
    if today.isoformat() not in dates:
        issues.append({"date": today.isoformat(), "count": len(stories)})
    issues = sorted(
        (item for item in issues if isinstance(item, dict) and
         safe_day(item.get("date")) is not None),
        key=lambda x: x["date"], reverse=True
    )
    index.write_text(json.dumps({"status": "published-monthly-index",
                                  "issues": issues}, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    return True


def run(now=None, root=ROOT):
    now = now or datetime.now(JST)
    today = now.astimezone(JST).date()
    if not editorial.KEY:
        print("Monthly review has no AI key; no changes and no empty publication.")
        return False
    if (root / MONTH_ROOT / (today.isoformat() + ".json")).exists():
        print("Today's monthly collection already committed; immutable safe skip.")
        return False
    leads = discover(now)
    # Spread the scarce pairing context across publisher regions and domains,
    # rather than letting one high-volume feed consume the first 100 headlines.
    leads = editorial.balanced_source_retrieval(leads, limit=150)
    if len(leads) < 1:
        print("No recent source leads; no publication.")
        return False
    groups = candidate_pairs(leads)
    if not groups:
        print("No verified-publisher source candidates; no publication.")
        return False
    known = existing_articles(root)
    accepted = []
    for group in groups:
        if len(accepted) >= 2:
            break
        urls = [item["url"] for item in group]
        if any(u in known[2] for u in urls):
            continue
        story = make_story(group, today, known[0] + accepted)
        if not story or not plausible_new(story, known):
            continue
        known[0].append({"title":story["title"],"summary":story["summary"],
                         "country":story["country"]})
        known[1].add(story["id"])
        known[2].update(story["verificationUrls"])
        known[3].add(story["eventKey"])
        accepted.append(story)
    if not accepted:
        print("No source-grounded, approved new monthly articles; existing shelf preserved.")
        return False
    wrote = publish_monthly(accepted, today, root)
    print("Verified monthly articles saved:", len(accepted) if wrote else 0,
          "collection date:", today.isoformat())
    return wrote


if __name__ == "__main__":
    try:
        run()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        # Fail closed. Do not print page HTML, URLs, or untrusted model content.
        print("Monthly research stopped without publication:", type(exc).__name__,
              file=sys.stderr)
        sys.exit(1)
