#!/usr/bin/env python3
"""Free-tier AI editorial pipeline. Fail closed: no key or no verified story means no publication."""
import json, os, re, sys, ipaddress, socket, time
from country_codes import country_code, country_key, country_region
from trusted_originals import trusted_original_domain, SINGLE_SOURCE_NOTE
from editorial_quality import headline_fidelity_risk, independent_editorial_quality_passed
from editorial_identity import (
    HUMAN_FAILURE_MISSION, human_failure_rejection, comic_line_rejection,
    noncomic_incident_rejection,
    animal_novelty_headline,
)
from html.parser import HTMLParser
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

JST=ZoneInfo("Asia/Tokyo")
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
KEY=os.getenv("GEMINI_API_KEY","")
REQUIRED=("id","country","category","categoryLabel","label","title","summary","detail","quip","sourceName","sourceUrl","reported")
BLOCK=re.compile(r"死亡|殺害|負傷|災害|差別|自殺|銃撃|戦争|死者|犠牲者|killed|murder|fatal|death|died|suicide|rape|shooting|injured|hospitalized|war|bombing|disaster",re.I)
# An app about humane, verifiable mistakes must not turn personal scandals
# into entertainment. This conservative deterministic filter supplements AI.
PRIVATE_GOSSIP=re.compile(r"不倫|浮気|私生活|婚外|私的な関係|恋愛関係|交際相手|extramarital|affair\\b|alleged spy",re.I)
# Narrow, deterministic safeguard against coercive self-help framing. General
# words such as "hope" or "tomorrow" are intentionally NOT blanket-banned.
READER_PRESSURE=re.compile(r"あなたより大変|悩みなんて小さい|たかが失敗|感謝すべき|笑うべき|もっと頑張れ|努力が足りない|必ず元気になる|必ず幸せになる|明日は絶対に良くなる|笑わなければならない",re.I)

def semantic_matching_needed(headline_pair_count):
    """Expand cross-language pairing only when direct retrieved headlines yield few pairs.

    This heuristic never approves a story. Mandatory full-text evidence
    checking and independent fact review still apply to every candidate.
    """
    return headline_pair_count < 2


def editorial_fit_rejection(story):
    """Reject missing plan-versus-reality evidence and private gossip.

    Expected and observed outcomes are claims for independent source-text
    audit, not self-certifying facts. The AI audit below must confirm both.
    """
    content=" ".join(str(story.get(field,"")) for field in
                     ("title","summary","detail","quip","quipSecond"))
    if PRIVATE_GOSSIP.search(content):
        return "private_gossip"
    if READER_PRESSURE.search(content):
        return "coercive_reader_tone"
    expectation=story.get("expectedPlan")
    outcome=story.get("observedOutcome")
    if (not isinstance(expectation,str) or not isinstance(outcome,str)
            or len(expectation.strip())<12 or len(outcome.strip())<12):
        return "missing_source_grounded_plan_or_outcome"
    if expectation.strip().casefold()==outcome.strip().casefold():
        return "no_observed_failure_contrast"
    return None
# Rank incident-specific reporting ahead of generic world-news headlines.
# Ranking only changes retrieval order; it never certifies a fact or relaxes review.
EDITORIAL_MISSION=("Publish only real, source-supported HUMAN mistakes with an observable, funny plan-versus-reality reversal. "
    "Every story must have two essential parts: source-supported facts about a failure; "
    "and a warm, witty AI quip aimed at the decision, contradiction or overconfidence rather than a victim. "
    "A humane aftertaste is optional, not a compulsory lesson or an instruction for the reader to feel better. "
    "The quip must deliver a sharp, surprising payoff rather than merely restating the facts; aim for a vivid, quotable contrast between plan and reality without exaggerating evidence. "
    "For this particular evening publication, editorial fit means a verifiable, gentle human-scale surprise: a small work mix-up, harmless misunderstanding, unexpectedly funny plan, or non-tragic sports mishap can be more suitable than a nationally consequential failure. The word consequential means there was a concrete documented outcome for the people involved, not that a large company, famous CEO, or critical infrastructure was affected. "
    "Before choosing the lead, ask whether a tired reader could smile without worrying for anyone's safety. Prefer playful, relatable, unforced moments when verified alternatives exist, and avoid ominous corporate crises or technical incidents merely because they dominate headlines. "
    "Never replace a failure with generic surprising, uplifting or quirky news merely to fill a quota. "
    "A CEO resignation, appointment, product launch, earnings report or sensational headline is NOT itself a verified mistake. Publish it only if the supplied reporting independently establishes a concrete original expectation and a documented failure to meet it. "
    "Prioritize relatable, unexpected non-tragic mistakes in daily life, work, sport and small organizations; a large-company headline has no automatic priority. "
    "Exclude salacious private-life allegations and romantic rumors even about public figures, whether reported elsewhere or not. "
    "Search across continents and languages; seek balanced country and regional coverage across successive editions, not just US/UK or a few major powers. Prefer distinct countries in each issue when independently verified stories are available; never lower evidence standards or fabricate coverage for geographic quotas. "
    "Never use geography as a substitute for a real failure, independent verification, or humane humor. "
    "A reader's everyday view can narrow to the same job, home and obligations. Let specific verified incidents in real places reveal that the world beyond that view is wider, with unexpected human turns and mistakes in many countries. Show rather than preach: the experience comes from facts and a surprising joke, not therapeutic advice. "
    "The reader's burdens are not smaller because somebody else made a mistake. Never compare pain or promise relief. "
    "Treat geographic variety as a doorway to different vantage points, never a quota or substitute for evidence. "
    "Do not invent a happy ending, recovery, quote or fact. A reframing is editorial interpretation, not reporting. "
    "Our reader may have spent a long day carrying responsibilities at work and home and have little energy left. The newsletter is a quiet place to find one surprising real story and, if it happens naturally, a small laugh. "
    "Do not diagnose the reader, give mental-health advice, demand gratitude or optimism, promise that tomorrow will be better, compare anyone's suffering, or force a takeaway. "
    "Even a genuinely funny story is enough; the reader owes us no smile, reading streak or response. "
    "Do not sensationalize fear, humiliation, private hardship or collateral suffering for punchlines.")
# Human errors, not zoo sightings or generic oddities, are the publication's identity.
EDITORIAL_MISSION += HUMAN_FAILURE_MISSION
# Editorial writing craft: keep verified reporting separate from compassionate interpretation.
WRITING_CRAFT=(
    " Write for a tired Japanese reader at 9pm, not for a compliance committee. "
    "Structure each story as (1) a concrete verified plan or expectation, "
    "(2) the documented mistake and surprising contrast, (3) optionally a small humane aftertaste, never a compulsory lesson. "
    "Write a factual, curiosity-provoking Japanese headline: put the concrete plan and unexpected outcome in sharp contrast; favor vivid specifics over abstract labels. Never invent numbers, quotes, consequences or a stronger failure than sources establish. Legal accusations must retain exact procedural status (charged, to be charged, detained, arrested, convicted are DIFFERENT). Do not translate plant nursery as 植物園 or 産院, and do not turn colorful metaphors into reportable locations. Avoid imputing cunning or intent to anyone without specific source evidence. "
    "The first selected story is the nightly lead and must be the most immediately surprising, clearly verified, humane-to-laugh-at incident; do not rank by human suffering or severity. "
    "A great lead should sound like a small story somebody would retell at dinner, not an emergency alert. When a gentle, independently verified mistake exists, give it editorial preference over an airport shutdown, market shock or executive transition; never exaggerate or invent the gentle story. "
    "The title should show the specific mismatch, not generic outrage or a vague 'big failure'. "
    "When source-supported, make the actual incident country and, if relevant, its city concrete in the Japanese summary or detail. The publication's market is never evidence of where the event happened. Never invent local customs, exoticize a place, or stereotype its people. "
    "Use the surprising gap between plan and reality to create an unforced perspective shift, not a lecture about how fortunate the Japanese reader should feel. "
    "summary: two crisp Japanese sentences describing only verified facts. "
    "MANDATORY: write title, summary, detail, label, categoryLabel and quip in natural Japanese. "
    "The entire detail must be Japanese, not an English source paraphrase or an English pep talk. "
    "Keep factual reporting and the explicitly labeled AI reflection separate; never translate unverified claims as facts. "
    "detail: first explain the verifiable sequence in plain Japanese. If a gentle interpretive line genuinely adds value, clearly separate it from news facts with 'ここからはAIの見方。'; a joke can stand without any advice. "
    "Keep reflections to one or two concise sentences; never address the reader as a patient, student or person who needs fixing. "
    "Write ONE genuinely funny, precise Japanese tsukkomi with a sharp payoff (aim for 18-45 characters). Draft FOUR different options privately as a seasoned Japanese comedy writer, discard mere paraphrases and obvious motivational captions, and choose the strongest setup-to-payoff reversal. quipSecond is OPTIONAL (18-55 characters) and is only published when a distinct, equally funny angle exists. Do not fill the second slot with an explanation. The punchline must mock the human misjudgment or plan, never a victim. Both must be grounded in verified facts; never invent causes, outcomes or private wrongdoing. Clarity veto: the reader must understand both jokes on the first pass after the headline and summary, without solving metaphors. Use plain Japanese describing the verified actor and action. Reject misleading counterfactuals such as '開くはずのなかったドア' when the door actually opened, and invented dialogue presented as a real quote. "
    "quip: one quotable, tight Japanese line (roughly 18-45 characters) that lands its twist on the final words about "
    "the PLAN, ASSUMPTION or DECISION, never a victim. Prefer observational irony "
    "over ridicule, platitudes, generic encouragement or forced puns. "
    "The reader may be exhausted and may not laugh today. They must feel welcome even if they only read one paragraph and leave. "
    "Never write moral lessons, productivity advice, prescriptive coping steps or motivational slogans; favor a soft, unforced observation. "
    "Do not say 'your problems are nothing', dismiss the reader's pain, "
    "invent a happy ending, or imply the subjects were secretly fine. "
    "Before outputting JSON, privately draft four sharply different one-liners. For each, locate the HUMAN miscalculation, then put a short, concrete, surprising payoff at the end. Select the line that only works for THIS incident. Do not pad the joke with a recap or offer a lecture. Apply the comic editor's test: SETUP must contain a source-verified concrete fact, PAYOFF must invert the expectation in one understandable beat. The follow-up must have a new premise, not a synonym for the first. Do not call a simple recap a joke. Favor natural spoken Japanese over stock phrases like '情報量が多い' or a string of 'まさか'. Avoid long similes, recaps, generic cheering, forced AI/reboot metaphors, or hedged endings like \"ようです\". If unproven causes or personal allegations are the only funny angle, do not joke about them. "    "If the facts are sufficient but the first joke is weak, try three angles "
    "internally: inflated ambition versus mundane reality; a reasonable assumption "
    "that backfired; the tiny missed step behind a grand plan. Pick the kindest. "
    "Do not include these internal options in the JSON. "
    "A weak punchline is a writing problem to revise, not automatically a reason "
    "to discard a verified, safely discussable incident. "
)

# Two-stage comedy editing keeps the final line distinct from a news recap.
# The independent reviewer may choose only from the drafted, locally screened options.
NIGHTLY_COMEDY_CRAFT=(
    "あなたは『よる9じの世界便り』の放送作家です。 "
    "その日の検証済み記事を、仕事や予定が思わぬ方向に転ぶという共通の視点から見直してください。 気が向かなければ笑わなくてもよい読者に向け、笑いや元気を強要しません。 "
    "今夜のひと言はニュース3本の要約や固有名詞の羅列ではなく、読了後にだけ効く独立したオチです。 "
    "20〜60文字の自然な日本語を4案作ってください。"
    "構造は『短いフリ→予想外の着地』。一度読めば伝わり、最後の一語が笑いの芯になること。 "
    "題材が1〜2本の日は無理に共通点を捏造せず、確認された範囲の小さな皮肉でよい。 "
    "本文にない発言、事実、固有名詞、数字、被害や結果を追加しない。誰かの不運や弱さを笑わない。 "
    "よくある励まし、精神論、抽象的な『世界は自由』、記事の順番どおりのおさらい、語尾だけの『まさか』は禁止。 "
    "読者の感情や行動を指示せず、説教しない。創作的な比喩は事実の断定に見えないようにする。 "
    "JSON {\"candidates\":[\"案1\",\"案2\",\"案3\",\"案4\"]} のみ返してください。"
)

def valid_nightly_comedy_line(line, recent_lines=()):
    """Lightweight structural guard; editorial humor itself still needs review."""
    from difflib import SequenceMatcher
    if not isinstance(line,str):
        return False
    line=line.strip()
    if not (20<=len(line)<=60) or any(ch in line for ch in "<>\r\n"):
        return False
    if ("://" in line or "\\" in line) or line.count("。")>2 or line.count("、")>2:
        return False
    if any(phrase in line for phrase in (
        "世界の「まさか」は予想以上に自由", "世界は予想以上に自由",
        "おやすみなさい", "無理しないで", "元気を出して", "あなたの失敗",
        "今夜は自分に", "今夜は少し力を抜いて")):
        return False
    return all(SequenceMatcher(None,line,previous).ratio()<0.72
               for previous in recent_lines if isinstance(previous,str))

def compose_nightly_comedy(stories,recent_lines=()):
    """Draft multiple closings, then require a separate comedy/fact review."""
    if not stories:return None
    payload=[{"title":s["title"],"summary":s["summary"],
              "category":s["category"]} for s in stories]
    draft=ai(NIGHTLY_COMEDY_CRAFT+"過去の締め:"+json.dumps(list(recent_lines)[-20:],ensure_ascii=False)
             +"今日の検証済み記事:"+json.dumps(payload,ensure_ascii=False),temperature=0.65)
    proposed=draft.get("candidates") if isinstance(draft,dict) else None
    if not isinstance(proposed,list) or not (3<=len(proposed)<=5):
        return None
    candidates=[]
    for item in proposed:
        if valid_nightly_comedy_line(item,recent_lines) and item.strip() not in candidates:
            candidates.append(item.strip())
    if not candidates:
        return None
    review=ai(
        "あなたは執筆者とは独立した日本語のお笑い編集者兼事実監査者です。"
        "次の候補から『フリ→意外なオチ』『一読で分かる』『自然な日本語』『読後感』『事実に基づく』の"
        "5軸で最も良い1案のみを選んでください。確認済みのニュースにない事実を含む候補は不可。"
        "複数記事の内容をただ列挙する総集編、精神論、説教、平凡な『想定外』『自由です』、"
        "無理なダジャレ、記事本文と重複する説明は不合格。"
        "どれも弱ければ approved:false にしてください。"
        "JSON {\"approved\":true/false,\"bestIndex\":0,\"reason\":\"短い理由\"} のみ。"
        "検証済み記事:"+json.dumps(payload,ensure_ascii=False)+
        "候補:"+json.dumps(candidates,ensure_ascii=False),
        temperature=0.1)
    if not isinstance(review,dict) or review.get("approved") is not True:
        return None
    index=review.get("bestIndex")
    if type(index) is not int or not 0<=index<len(candidates):
        return None
    return candidates[index]

INCIDENT_TERMS=re.compile(r"\b(accidentally|mistak(?:e|en)|mix.?up|blunder|error|wrong|failed|failure|apolog(?:y|ise|ize)|revers(?:e|al)|scrap(?:ped)?|cancel(?:led|ed)|recall|outage|glitch|misplac(?:ed)?|misprint|confus(?:ion|ed)|fiasco|oversight|backfir(?:e|ed)|botch(?:ed)?|miscalculat(?:e|ed|ion))\b|手違い|誤発注|間違|失敗|謝罪|撤回|中止|障害|誤送信|ミス|실수|착각|Verwechslung|Fehler|Panne|par erreur|erreur|confusion|equivocaci[oó]n|por engano|equívoco|confusão|erro|falha",re.I)

# Specific harmless human miscues deserve the scarce fetched-article slots.
# Disciplinary crises and animal novelties can still be read as leads, but
# never outrank a clearly sourced typo, wrong delivery, or mistaken assumption.
COMIC_MISSTEP_TERMS=re.compile(
    r"typo|misspell|misprint|mix.?up|accidentally|by mistake|mistook|"
    r"wrong recipient|wrong order|wrong delivery|wrong address|"
    r"wrong (?:city|cities|town|landmark|cathedral|mural|sign)|"
    r"AI.generated.{0,70}(?:wrong|errors?|mistake|misspell)|"
    r"誤字|誤記|手違い|誤配達|誤送信|誤発注|勘違い|見間違い|取り違え|"
    r"verwechslung|aus versehen|por error|equivocaci[oó]n|실수",re.I
)
SERIOUS_CONFLICT_TERMS=re.compile(
    r"harass|abuse|intimidat|disciplin|suspend|protest|minister|"
    r"convocation row|emergency siren|罵倒|嫌がらせ|脅迫|"
    r"停学|懲戒|処分|大臣|抗議|起訴",re.I
)

def incident_priority(lead):
    title=lead.get("title","")
    # Discovery order is not proof: original sources and AI must still audit.
    if animal_novelty_headline(title):
        rank=4
    elif SERIOUS_CONFLICT_TERMS.search(title):
        rank=3
    elif COMIC_MISSTEP_TERMS.search(title):
        rank=0
    elif INCIDENT_TERMS.search(title):
        rank=1
    else:
        rank=2
    return (rank,1 if host(lead.get("url",""))=="news.google.com" else 0)


def prioritize_comic_groups(groups, limit=24):
    """Expose small human errors to editor A before serious paired disputes.

    This ranks unverified publisher evidence; independent fact and humor review
    still decides publication. A vetted original article does not need a
    corroborating publisher to be eligible for the shortlist.
    """
    return sorted(
        (group for group in groups if group),
        key=lambda group: (
            min(incident_priority(item)[0] for item in group),
            0 if len(group) >= 2 else 1,
            min(incident_priority(item)[1] for item in group),
        ),
    )[:limit]


def host(url):
    try:
        p=urlsplit(url)
        return p.hostname.lower().removeprefix("www.") if p.scheme=="https" and p.hostname and not p.username else ""
    except ValueError:return ""

def balanced_source_retrieval(leads, limit=240):
    """Fairly sample fetchable publisher sources across discovery markets.

    sourcecountry describes a search locale or publisher, never incident
    geography. It must not become an article's reported country.
    """
    from collections import deque
    regions={}
    for lead in sorted(leads,key=incident_priority):
        domain=host(lead.get("url",""))
        if not domain or domain=="news.google.com":
            # Google RSS results are discovery URLs, not retrievable evidence.
            continue
        region=country_region(lead.get("sourcecountry")) or "unattributed"
        hosts=regions.setdefault(region,{})
        hosts.setdefault(domain,deque()).append(lead)
    per_host={}
    ordered=[]
    while regions and len(ordered)<limit:
        progressed=False
        for region in list(regions):
            hosts=regions[region]
            # Round-robin publishers within each region; one article per
            # region per turn prevents large English-language feeds from
            # consuming the entire article-fetch budget.
            for domain in list(hosts):
                host_cap=5 if domain in ("theguardian.com","guardian.co.uk") else 30
                if per_host.get(domain,0)>=host_cap:
                    del hosts[domain]
                    continue
                group=hosts.pop(domain)
                ordered.append(group.popleft())
                per_host[domain]=per_host.get(domain,0)+1
                if group:
                    hosts[domain]=group
                progressed=True
                break
            if not hosts:
                del regions[region]
            if len(ordered)>=limit:
                break
        if not progressed:
            break
    return ordered


class ArticleText(HTMLParser):
    """Extract visible prose from a publisher article container, not navigation."""
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.hidden=0
        self.article_depth=0
        self.article_parts=[]
        self.article_containers=0
        self.stack=[]
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        classes=(attributes.get("class") or "").split()
        guardian_body=attributes.get("data-gu-name")=="body"
        # Publisher layouts vary; only explicitly article-scoped containers count.
        article_body=(tag=="article" or guardian_body or
                      any(c in classes for c in ("article-body","article__body",
                          "article-content","article__content","story-body",
                          "story__body","story-content","entry-content",
                          "articleBody","article-text","body-content")) or
                      attributes.get("itemprop")=="articleBody" or
                      attributes.get("data-testid") in ("article-body","article-content"))
        self.stack.append((tag,article_body))
        if article_body:
            self.article_depth+=1
            self.article_containers+=1
        if tag in ("script","style","noscript","svg","nav","footer","header","aside"):
            self.hidden+=1
    def handle_endtag(self,tag):
        # HTML in the wild may be imperfect; only unwind matching open tags.
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                popped=self.stack[i:]
                self.stack=self.stack[:i]
                for old_tag,is_article in popped:
                    if is_article:self.article_depth=max(0,self.article_depth-1)
                    if old_tag in ("script","style","noscript","svg","nav","footer","header","aside"):
                        self.hidden=max(0,self.hidden-1)
                break
    def handle_data(self,data):
        if self.hidden or not data.strip():return
        value=data.strip()
        self.parts.append(value)
        if self.article_depth:self.article_parts.append(value)

def extracted_article_text(html, min_chars=600):
    parser=ArticleText()
    parser.feed(html)
    # Prefer the publisher's article container; reject generic site chrome.
    if parser.article_containers:
        body=" ".join(parser.article_parts)
        if len(body)>=min_chars:return body
    # Some publishers expose the article body as schema.org structured data,
    # without a conventional <article> element. Only articleBody is trusted;
    # generic page text and navigation are never promoted to evidence.
    scripts=re.findall(r'<script\b[^>]*type=["\x27]application/ld\+json["\x27][^>]*>(.*?)</script\s*>',html,re.I|re.S)
    def article_bodies(node):
        if isinstance(node,list):
            for part in node:yield from article_bodies(part)
        elif isinstance(node,dict):
            kind=node.get("@type",[])
            kinds=kind if isinstance(kind,list) else [kind]
            if any(isinstance(k,str) and k.lower() in ("article","newsarticle","reportagearticle","blogposting") for k in kinds):
                body=node.get("articleBody")
                if isinstance(body,str) and len(body)>=min_chars:yield body
            for key in ("@graph","mainEntity"):
                if key in node:yield from article_bodies(node[key])
    for script in scripts[:12]:
        try:
            for body in article_bodies(json.loads(script)):
                return re.sub(r"\s+"," ",__import__("html").unescape(body)).strip()
        except (ValueError,TypeError):continue
    return ""

def public_host(url):
    domain=host(url)
    if not domain or domain in ("localhost",) or domain.endswith((".local",".internal")):return False
    try:
        addresses=socket.getaddrinfo(domain,443,type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(x[4][0]).is_global for x in addresses)
    except (OSError,ValueError):return False

def source_text(url, diagnostics=None, min_chars=600):
    # Only public HTTPS URLs from the collected lead list may be fetched.
    if not public_host(url):
        if diagnostics is not None:diagnostics.append("blocked_host")
        return ""
    class SafeRedirect(__import__("urllib.request",fromlist=["HTTPRedirectHandler"]).HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            if not public_host(newurl):raise ValueError("unsafe_redirect")
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    from urllib.request import build_opener
    opener=build_opener(SafeRedirect)
    req=Request(url,headers={
        "User-Agent":"Mozilla/5.0 (compatible; Yoru9EditorialResearch/1.0)",
        "Accept":"text/html,application/xhtml+xml;q=0.9",
        "Accept-Language":"en-GB,en;q=0.8",
    })
    try:
        with opener.open(req,timeout=7) as response:
            if "text/html" not in response.headers.get("Content-Type",""):
                if diagnostics is not None:diagnostics.append("non_html")
                return ""
            raw=response.read(180000)
        text=extracted_article_text(raw.decode("utf-8",errors="replace"),min_chars=min_chars)
        if len(text)<min_chars:
            if diagnostics is not None:diagnostics.append("short_html")
            return ""
        if diagnostics is not None:diagnostics.append("fetched")
        return text[:13000]
    except HTTPError as exc:
        if diagnostics is not None:diagnostics.append("http_"+str(exc.code))
        return ""
    except (OSError,ValueError,URLError) as exc:
        if diagnostics is not None:diagnostics.append(type(exc).__name__)
        return ""

def available_models():
    """List supported models, with a bounded preference order and no paid fallback."""
    endpoint="https://generativelanguage.googleapis.com/v1beta/models?pageSize=100"
    req=Request(endpoint,headers={"x-goog-api-key":KEY})
    try:
        with urlopen(req,timeout=25) as response:
            catalog=json.load(response)
    except HTTPError as exc:
        print("Gemini model catalog HTTP",exc.code,flush=True)
        raise RuntimeError("Gemini model catalog unavailable: HTTP "+str(exc.code)) from None
    models=[m["name"] for m in catalog.get("models",[])
            if "generateContent" in m.get("supportedGenerationMethods",[])
            and m.get("name","").startswith("models/gemini-")]
    # Prefer currently supported models from the live catalog, and avoid
    # retired/eligibility-limited 2.5 models as early automatic fallbacks.
    preferred=[MODEL,"gemini-3.5-flash-lite","gemini-3.8-flash",
               "gemini-3.7-flash","gemini-3.6-flash","gemini-3.5-flash",
               "gemini-3.1-flash-lite","gemini-2.5-flash-lite","gemini-2.5-flash"]
    result=[]
    for name in preferred:
        full="models/"+name
        if full in models and full not in result:result.append(full)
    if not result:raise RuntimeError("No supported Gemini model found; safe stop")
    return result[:5]

def available_model():
    return available_models()[0]

ACTIVE_MODEL=None
AI_QUOTA_BLOCKED=False
RUN_DEADLINE=None

def editorial_seconds_remaining():
    return float("inf") if RUN_DEADLINE is None else max(0.0,RUN_DEADLINE-time.monotonic())

def ai(prompt,temperature=0.1):
    global ACTIVE_MODEL, AI_QUOTA_BLOCKED
    if not KEY:raise RuntimeError("GEMINI_API_KEY not configured; no publication")
    if AI_QUOTA_BLOCKED:raise RuntimeError("Gemini API quota/permission circuit open; no publication")
    if editorial_seconds_remaining()<=5:
        raise RuntimeError("Editorial run time budget exhausted; no publication")
    call_deadline=time.monotonic()+75
    if RUN_DEADLINE is not None:call_deadline=min(call_deadline,RUN_DEADLINE)
    def bounded_timeout():
        return min(40,max(1,call_deadline-time.monotonic()))
    models=available_models()
    if ACTIVE_MODEL in models:
        models=[ACTIVE_MODEL]+[model for model in models if model!=ACTIVE_MODEL]
    data={"contents":[{"parts":[{"text":prompt}]}],
          "generationConfig":{"responseMimeType":"application/json","temperature":temperature}}
    last_error=None
    for model in models:
        for version in ("v1beta","v1"):
            if time.monotonic()>=call_deadline:
                raise RuntimeError("Gemini per-call time budget exhausted; no publication")
            url="https://generativelanguage.googleapis.com/"+version+"/"+model+":generateContent"
            req=Request(url,data=json.dumps(data).encode(),
                        headers={"Content-Type":"application/json","x-goog-api-key":KEY},method="POST")
            try:
                with urlopen(req,timeout=bounded_timeout()) as response:result=json.load(response)
                raw=result["candidates"][0]["content"]["parts"][0]["text"]
                try:
                    parsed=json.loads(raw)
                except json.JSONDecodeError:
                    print("Gemini malformed JSON; trying another model/version:",model,version,flush=True)
                    last_error="invalid_json"
                    continue
                ACTIVE_MODEL=model
                print("Gemini generation succeeded:",model,version,flush=True)
                return parsed
            except HTTPError as exc:
                # Print only status and sanitized provider reason, never headers or key.
                try:
                    err=json.loads(exc.read(4096).decode("utf-8"))
                    status=str(err.get("error",{}).get("status","UNKNOWN"))[:50]
                    message=str(err.get("error",{}).get("message",""))[:320]
                    message=re.sub(r"AIza[A-Za-z0-9_-]{20,}", "[REDACTED_KEY]", message)
                    message=re.sub(r"key=[^&\\s]+", "key=[REDACTED]", message,flags=re.I)
                except (ValueError,UnicodeError,AttributeError):status="UNKNOWN";message="unavailable"
                category=("quota_or_rate_limit" if exc.code==429 or status=="RESOURCE_EXHAUSTED" else
                          "auth_or_permission" if exc.code in (401,403) else
                          "unsupported_model_or_request" if exc.code in (400,404) else
                          "provider_transient" if exc.code in (500,502,503,504) else "other")
                print("Gemini generation failed:",model,version,"HTTP",exc.code,status,"category:",category,flush=True)
                last_error=exc.code
                if exc.code in (401,403,429):
                    # Global circuit prevents the next story batch retrying the same exhausted key.
                    AI_QUOTA_BLOCKED=True
                    raise RuntimeError("Gemini API stopped: HTTP "+str(exc.code)+" "+status+" "+category) from None
                if exc.code in (500,502,503,504):
                    # Bounded exponential backoff for provider overload,
                    # then try another catalog-supported model. Do not
                    # silently approve when all attempts fail.
                    for delay in (2,6):
                        if time.monotonic()+delay>=call_deadline:break
                        time.sleep(delay)
                        try:
                            with urlopen(req,timeout=bounded_timeout()) as response:result=json.load(response)
                            raw=result["candidates"][0]["content"]["parts"][0]["text"]
                            parsed=json.loads(raw)
                            if not isinstance(parsed,dict):raise ValueError("non-object JSON")
                            ACTIVE_MODEL=model
                            print("Gemini generation succeeded after transient retry:",model,version,flush=True)
                            return parsed
                        except HTTPError as retry_exc:
                            last_error=retry_exc.code
                            print("Gemini transient retry failed:",model,version,"HTTP",retry_exc.code,flush=True)
                            if retry_exc.code in (401,403,429):
                                AI_QUOTA_BLOCKED=True
                                raise RuntimeError("Gemini retry blocked: HTTP "+str(retry_exc.code)) from None
                            if retry_exc.code not in (500,502,503,504):break
                        except (URLError,TimeoutError,OSError,ValueError,KeyError,IndexError,TypeError) as retry_exc:
                            last_error=type(retry_exc).__name__
                            print("Gemini transient retry unavailable:",last_error,flush=True)
                            break
                    break
                if exc.code not in (404,400):raise RuntimeError("Gemini API HTTP "+str(exc.code))
            except (URLError, TimeoutError, ConnectionError, OSError) as exc:
                # Network timeouts are not editorial rejections. Try the next
                # supported model/version; do not approve an unverified story.
                print("Gemini request unavailable:",model,version,type(exc).__name__,flush=True)
                last_error=type(exc).__name__
                continue
    raise RuntimeError("No available model/version generated content; last HTTP "+str(last_error))

def select_diverse_verified_stories(pool, country_history, category_history):
    """Select up to three ALREADY audited stories, with regional fairness.

    Country is the fact-checked event country, not the RSS feed locale.
    Unknown event countries receive no fictitious diversity credit.
    """
    from collections import Counter
    from itertools import combinations
    if not pool:
        return []
    region_history=Counter()
    for country,count in country_history.items():
        region=country_region(country)
        if region:
            region_history[region]+=count
    choices=list(combinations(range(len(pool)),min(3,len(pool))))
    def diversity_score(indices):
        stories=[pool[i] for i in indices]
        countries=[country_code(story.get("country")) for story in stories]
        regions=[country_region(story.get("country")) for story in stories]
        known_countries=[country for country in countries if country]
        known_regions=[region for region in regions if region]
        categories={story["category"] for story in stories}
        # Only approved stories compete. Prefer distinct world regions, then
        # countries, then editorial perspectives; break ties by 30-day history
        # and original verified editorial ranking.
        return (len(set(known_regions)),len(categories),len(set(known_countries)),
                -sum(region_history[region] for region in known_regions),
                -sum(country_history[country] for country in known_countries),
                -sum(category_history[story["category"]] for story in stories),
                -sum(indices))
    best=max(choices,key=diversity_score)
    return [pool[i] for i in best]


def archive_summaries():
    result=[]
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            for story in json.loads(file.read_text()).get("stories",[]):
                result.append({"title":story.get("title",""),"summary":story.get("summary",""),"country":story.get("country","")})
        except (ValueError,OSError):continue
    return result[-250:]

def recent_diversity_counts(today, days=30):
    """Count published country/category exposure during the preceding 30 days."""
    from collections import Counter
    country_counts, category_counts = Counter(), Counter()
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            issue=json.loads(file.read_text(encoding="utf-8"))
            issue_date=datetime.strptime(issue.get("editionDate",""),"%Y-%m-%d").date()
            if not (today-timedelta(days=days) <= issue_date < today):
                continue
            if issue.get("status")!="published":
                continue
            for story in issue.get("stories",[]):
                country=country_key(story.get("country",""))
                category=str(story.get("category","")).strip()
                if country:country_counts[country]+=1
                if category in ("work","person","company","sports"):category_counts[category]+=1
        except (ValueError,OSError,TypeError,KeyError):
            continue
    return country_counts,category_counts

def previous_events():
    seen=set()
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            for story in json.loads(file.read_text()).get("stories",[]):
                seen.add(story.get("sourceUrl",""))
                seen.add(story.get("id",""))
        except (ValueError,OSError):continue
    return seen

# Similar headlines help discovery, but are not proof of corroboration.
STOPWORDS=set("the a an and or of to in on for with from at by as is are was were after before new latest says say report reports news world today update video live how why what who where this that about into over under amid".split())

def title_terms(title):
    return {w for w in re.findall(r"[a-z0-9]{3,}",title.lower()) if w not in STOPWORDS}

def corroboration_groups(items):
    """Group potentially matching incidents across distinct publisher domains."""
    groups=[]
    for i,item in enumerate(items):
        terms=title_terms(item["title"])
        if len(terms)<3:continue
        matches=[item]
        for other in items[i+1:]:
            if host(other["url"])==host(item["url"]):continue
            other_terms=title_terms(other["title"])
            shared=terms & other_terms
            if len(shared)>=3 and len(shared)/max(1,min(len(terms),len(other_terms)))>=0.45:
                matches.append(other)
        if len(matches)>=2:groups.append(matches[:4])
    unique={}
    for group in groups:
        key=tuple(sorted(x["url"] for x in group))
        unique[key]=group
    return list(unique.values())[:48]

def select_distinct_groups(groups, limit=24):
    """Choose many non-overlapping source groups without first-match bias.

    Candidate pairs are discovery hypotheses, not verified incidents. Keep
    publisher independence and let the later editorial/audit stages decide
    whether each group actually corroborates an event.
    """
    candidates=[]
    seen=set()
    for group in groups:
        urls=frozenset(item["url"] for item in group)
        if len(urls)<2 or len({host(url) for url in urls})<2 or urls in seen:
            continue
        seen.add(urls)
        candidates.append((group,urls))
    # Explore both taking and skipping a group. Bounded beam search prevents
    # a large early group from suppressing several independent later pairs.
    # Prefer groups with more independent sources when counts are tied.
    states=[((),frozenset())]
    for index,(_,urls) in enumerate(candidates):
        next_states=list(states)
        for chosen,used in states:
            if len(chosen)<limit and used.isdisjoint(urls):
                next_states.append((chosen+(index,),used|urls))
        next_states.sort(key=lambda state:(
            -len(state[0]),
            sum(len(candidates[i][1]) for i in state[0]),
            state[0]))
        # Retain distinct used-URL sets to preserve alternate future choices.
        unique={}
        for state in next_states:
            unique.setdefault(state[1],state)
            if len(unique)>=128:
                break
        states=list(unique.values())
    best=min(states,key=lambda state:(
        -len(state[0]),
        sum(len(candidates[i][1]) for i in state[0]),
        state[0]))
    return [candidates[i][0] for i in best[0]]

def semantic_corroboration_groups(items):
    """AI proposes pairs, but exact source URLs and distinct hosts are enforced locally."""
    if len(items)<2:return []
    # Rotate through all fetched publishers rather than silently dropping
    # every article after the first 120. Keep prompts bounded in size.
    compact=[{"title":x["title"],"url":x["url"],"excerpt":x["text"][:1800]} for x in items[:120]]
    result=ai("Find pairs of articles about the SAME specific incident, not merely the same topic. Include independently reported individual mishaps and consequential personal decisions, not only corporate or government events. "
        "Compare concrete people, places, actions and dates in the supplied excerpts. "
        "Two sources must be editorially independent, not syndicated rewrites. "
        "When uncertain, omit the pair. Return JSON object with pairs array of objects "
        "{urls:[exact_source_url_1,exact_source_url_2]}. No invented URLs. Evidence: "
        +json.dumps(compact,ensure_ascii=False))
    pairs=result.get("pairs",[])
    if not isinstance(pairs,list):return []
    by_url={x["url"]:x for x in items}
    groups=[]
    seen=set()
    for pair in pairs[:48]:
        if not isinstance(pair,dict):continue
        urls=pair.get("urls")
        if not isinstance(urls,list) or len(urls)!=2 or not all(isinstance(u,str) for u in urls):continue
        if any(u not in by_url for u in urls) or len({host(u) for u in urls})!=2:continue
        key=tuple(sorted(urls))
        if key in seen:continue
        seen.add(key)
        groups.append([by_url[u] for u in urls])
    return groups[:36]

def valid_recent_reported(raw, now):
    """Seven-day lookback matches the publisher's existing current-news limit."""
    if not isinstance(raw,str) or not re.fullmatch(r"\d{4}[-.]\d{2}[-.]\d{2}",raw):return False
    try:reported=datetime.strptime(raw.replace(".","-"),"%Y-%m-%d").date()
    except ValueError:return False
    return now.date()-timedelta(days=7)<=reported<=now.date()

def draft_preflight_viable(story,now):
    """Fast comedy and date screening, never replaces source/fact review.

    This counts only drafts worth spending scarce independent B-review calls
    on; it cannot mark any story as verified or publishable by itself.
    """
    if not isinstance(story,dict):
        return False
    if any(not isinstance(story.get(key),str) or not story[key].strip()
           for key in REQUIRED):
        return False
    if not valid_recent_reported(story["reported"],now):
        return False
    if story.get("category") not in ("person","work","company","sports"):
        return False
    if (editorial_fit_rejection(story) or human_failure_rejection(story)
            or noncomic_incident_rejection(story)
            or comic_line_rejection(story.get("quip"))):
        return False
    if BLOCK.search(" ".join(str(story.get(key,"")) for key in
                             ("title","summary","detail","quip"))):
        return False
    return True


def main():
    global RUN_DEADLINE, AI_QUOTA_BLOCKED
    now=datetime.now(JST)
    day=now.date().isoformat()
    if not KEY:
        print("No free-tier AI key configured. Safe skip.");return 0
    # Leave headroom before GitHub's 12-minute limit to fail closed, not get cancelled.
    RUN_DEADLINE=time.monotonic()+540
    AI_QUOTA_BLOCKED=False
    leads=json.loads(Path("data/candidates.json").read_text()).get("candidates",[])
    recent=[]
    for lead in leads:
        try:
            raw=lead["seendate"]
            if re.fullmatch(r"\d{8}T\d{6}Z",raw):
                stamp=datetime.strptime(raw,"%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(JST)
            else:
                stamp=datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(JST)
            if not (now - timedelta(days=7) <= stamp <= now + timedelta(minutes=10)):continue
        except (KeyError,ValueError,TypeError):continue
        if host(lead.get("url","")) and not BLOCK.search(lead.get("title","")):recent.append(lead)
    if len(recent)<5:
        print("Not enough fresh leads within 36 hours; safe skip.");return 0
    # Collect actual article bodies before asking the model to draft.
    cache={}
    source_leads=[]
    # Share scarce article-fetch slots across source markets, not just hosts.
    # Publisher country is only a retrieval hint, NEVER proof of event country.
    ordered=balanced_source_retrieval(recent,limit=240)
    from collections import Counter
    retrieval_regions=Counter(country_region(lead.get("sourcecountry")) or "unattributed"
                              for lead in ordered)
    print("Article retrieval by discovery-source region (not event country):",
          json.dumps(dict(retrieval_regions),ensure_ascii=False,sort_keys=True),flush=True)
    outcomes={}
    failure_reasons={}
    for lead in ordered:
        provider=lead.get('provider','unknown')
        label='Google RSS' if provider.startswith('Google') else ('BBC RSS' if provider.startswith('BBC') else ('Guardian RSS' if provider.startswith('The Guardian') else ('GDELT' if provider.startswith('GDELT') else 'Other')))
        outcomes.setdefault(label,[0,0])
        outcomes[label][0]+=1
        url=lead['url']
        if url not in cache:
            diagnostics=[]
            cache[url]=source_text(url,diagnostics)
            reason=diagnostics[0] if diagnostics else 'unknown'
            failure_reasons.setdefault(label,{})[reason]=failure_reasons.setdefault(label,{}).get(reason,0)+1
        if cache[url]:outcomes[label][1]+=1
        if cache[url]:source_leads.append({'title':lead['title'],'url':url,'publisher':lead.get('domain',''),'text':cache[url][:8500]})
    print('Evidence collection:',len(recent),'recent seven-day leads,',len(source_leads),'fetchable article bodies',flush=True)
    print('Article retrieval by provider (attempted, fetched):',json.dumps(outcomes,sort_keys=True),flush=True)
    print('Article retrieval diagnostic counts (no URLs or article text):',json.dumps(failure_reasons,sort_keys=True),flush=True)
    if len(source_leads)<1:
        print('No retrieved article bodies; safe skip before AI generation.');return 0
    groups=corroboration_groups(source_leads)
    print('Cross-publisher headline groups:',len(groups),flush=True)
    # Headline overlap is only a discovery heuristic. Even when it finds five
    # candidates, semantic matching can find additional consequential incidents
    # described with different wording by independent publishers.
    # Keep the bounded candidate budget; final publication still requires
    # at least one original report verified against its fetched text and an independent adversarial AI audit.
    print('Trying AI semantic incident matching to supplement headline groups.',flush=True)
    # Overlapping windows allow semantic matching across the full fetched set.
    # Headline groups are still included; AI proposals remain unverified.
    semantic=[]
    # Pair detection from confirmed retrieved headlines already gives editor A
    # concrete incident hypotheses. The separate semantic matching stage
    # consumes expensive API requests without verifying ANY story. Skip it
    # when at least two possible independent-source pairs are already known;
    # use that quota for the mandatory independent fact-checker instead.
    if semantic_matching_needed(len(groups)):
        for start in range(0,len(source_leads),90):
            if editorial_seconds_remaining()<220:
                print("Skipping remaining semantic matching to reserve time for independent review.",flush=True)
                break
            window=source_leads[max(0,start-30):start+120]
            if len(window)<2:continue
            semantic.extend(semantic_corroboration_groups(window))
    else:
        print("Skipping optional semantic matching: reserving Gemini calls for mandatory source review.",flush=True)
    existing={tuple(sorted(x['url'] for x in group)) for group in groups}
    for group in semantic:
        key=tuple(sorted(x['url'] for x in group))
        if key not in existing:
            groups.append(group)
            existing.add(key)
    # Preserve real two-publisher hypotheses first, but do not silently drop
    # the available original reports: select_distinct_groups() intentionally
    # handles PAIRS only and would otherwise throw every one-source lead away.
    raw_group_count=len(groups)
    groups=select_distinct_groups(groups,limit=18)
    paired_urls={item['url'] for group in groups for item in group}
    unpaired=sorted((item for item in source_leads if item['url'] not in paired_urls),
                    key=lambda item:(incident_priority(item)[0],
                                     0 if trusted_original_domain(item['url']) else 1,
                                     incident_priority(item)[1]))
    groups.extend([[item] for item in unpaired[:max(0,36-len(groups))]])
    groups=prioritize_comic_groups(groups,limit=24)
    print('Review groups:',len(groups),'including original single-publisher reports;',raw_group_count,'initial pair hypotheses',flush=True)
    if len(groups)<1:
        print('No retrieved candidate articles; safe skip.');return 0
    # Preserve each hypothesized incident's exact article-to-article association.
    # A flat article list can hide which sources are meant to corroborate one another.
    grouped_evidence=[{"groupId":i+1,"articles":[{"title":item["title"],
        "url":item["url"],"text":item["text"][:4800]} for item in group]}
        for i,group in enumerate(groups[:24])]
    # Preserve allowed corroboration pairs: a model must not combine unrelated sources.
    allowed_pairs=set()
    for group in groups[:36]:
        for i,first in enumerate(group):
            for second in group[i+1:]:
                if host(first["url"])!=host(second["url"]):
                    allowed_pairs.add(frozenset((first["url"],second["url"])))
    grouped_urls={item["url"] for group in groups for item in group}
    grouped_sources=[item for item in source_leads if item["url"] in grouped_urls]
    prompt=(EDITORIAL_MISSION+WRITING_CRAFT+' You are a Japanese comedy show writer working as news editor A. Discover up to 12 REAL, lightly embarrassing or absurd HUMAN BLUNDERS from these fetched original articles. First search for genuine mistakes in everyday work, deliveries, public signs, mistaken assumptions, clerical errors, confusing customer interactions, awkward sports decisions, and administrative mix-ups. Small and harmless mistakes are ideal WHEN the sourced mismatch supports a concrete sharp punchline. DO NOT favor consequential crises, high-profile resignations, serious disciplinary conflict, emergency harassment, criminal cases, politics, bad outcomes affecting victims, or news that is merely surprising. Human error must actually be in the fetched source; a dispute or apology alone is not a lighthearted mistake. For EACH incident first identify humanActor, humanMistake, expectedPlan and observedOutcome; only then privately draft FOUR radically different Japanese punchlines and pick the strongest short unexpected payoff, not a recap or lesson. Give unusual but independently documented minor errors priority over major corporate failures, provided the joke is really funny without mocking a harmed person. Return zero stories if no supported comedic mistake exists. '
      'Use ONLY supplied fetched article texts, never external knowledge. Draft stories supported by at least ONE retrieved publisher article; when two independent articles cover the same incident, use both. '
      'verificationUrls must include at least ONE exact URL of an actually retrieved, credible original publisher report. Prefer two independent publishers when available. A single ORIGINAL reporting article is acceptable; a syndicated copy, social media repost, aggregator, rumor, or headline without an original reporting body is not. Never invent facts, URLs, or details. '
      'For each include required fields '+str(REQUIRED)+', humanActor (which actual PERSON or human-run organization made the mistake), humanMistake (specific human decision or mix-up proved by the source), expectedPlan (the concrete source-supported expected plan or outcome, in Japanese, at least 12 characters), observedOutcome (the documented contrasting actual mistake or failure, in Japanese, at least 12 characters), quipSecond (OPTIONAL, only when a second genuinely funny 15-55-character angle exists), verificationUrls (1-3 original publisher URLs; prefer independent corroboration when available), eventKey (normalized incident identifier), evidence (facts explicitly supported by the supplied article text). '
      'CRITICAL OUTPUT SCHEMA: category MUST be exactly one of person, work, company, sports (lowercase English), NEVER government, politics, institution, business, organization or any Japanese category value. Use company for corporate and institutional failures INCLUDING government agencies, public institutions and large organizations; use work for workplace or operational mistakes; use person for individual decision-maker mistakes; use sports for incidents primarily occurring in competitive sport, including athletes, referees, clubs and event operations. categoryLabel is the human-readable Japanese label, not category. Do not alter these enum values even when the subject is consequential or political. '
      'For each story, make the quip an affectionate, pointed observation about the verified mistake; prioritize a crisp, unexpected punchline grounded in the plan-versus-reality contrast; avoid flat paraphrases and forced comedy. quip should land immediately in 18-45 characters; quipSecond should add a NEW comic angle in 18-55 characters. Select the funniest of three private first-hit alternatives. No explanatory second sentence and no unproven allegations as joke premises. An optional gentle reflection can add warmth, but never require a life lesson or tell the reader how to feel. Do not make empty motivational claims, imply an unreported recovery, or treat the mistake as harmless when it was not. Reject generic surprising news without a real failure, even if it is funny. Before rejecting an otherwise well-sourced failure for no_respectful_comic_angle, explore at least two different safe comic targets (the plan versus reality, the mistaken assumption versus the outcome); if neither works, reject it. ' 
      'Do not select a merely verifiable incident when its actual human mistake lacks a clear, safe, incident-specific comic reversal. Rewrite weak jokes with a new angle; do not replace comedy with vague encouragement or a lesson. Serious stakes are NOT a selection advantage. NEVER mock victims, casualties, poverty, illness or vulnerable people. For individuals, humor should target a relatable miscalculation, ironic outcome or overconfidence rather than their identity, appearance, hardship or vulnerability; avoid invasive private-life details and public shaming. For institutions, target flawed plans, contradictions and decisions, not those harmed. Exclude incidents where a respectful comic angle cannot be supported. No death, injuries, abuse or humiliation in the chosen story or quip. Edition date JST: '+day+'. Stories must have an original source-supported publication date within the preceding seven days including the edition day in Japan; keep that ACTUAL date intact and never relabel old reporting as new. Prioritize same-day reporting when otherwise comparable. '
      'Each group is only a hypothesis: check that its articles actually describe the same specific event, and that the reported date is explicit in the supplied article text. '
      'Return JSON with stories array AND diagnostics array containing one object for every input group: '
      '{groupId:integer,eligible:boolean,reasonCode:string}. Use ONLY these reasonCode values: '
      'same_incident_supported, unrelated_articles, syndicated_or_not_independent, no_explicit_recent_report_date, '
      'insufficient_facts, sensitive_incident, no_respectful_comic_angle, other. Do not reject an incident merely for being consequential or financially serious; reject only if there is no respectful, constructive comic angle. '
      'A group marked eligible still needs all story fields and source-text verification; do not fill gaps by inference. '
      'Candidate groups with their own article bodies (NOT proof): '+json.dumps(grouped_evidence,ensure_ascii=False))
    if editorial_seconds_remaining()<100:
        print("Editorial budget too low for safe independent review; no new publication.",flush=True)
        return 0
    draft_response=ai(prompt,temperature=0.65)
    draft=draft_response.get("stories",[]) if isinstance(draft_response,dict) else []
    if not isinstance(draft,list):
        print("Editorial drafting diagnostic: malformed stories response; safe skip.",flush=True)
        return 0
    # Diagnostics are model assessments, not factual verification. Never use them
    # to approve an article or to weaken any subsequent independent check.
    diagnostics=draft_response.get("diagnostics",[]) if isinstance(draft_response,dict) else []
    valid_codes={"same_incident_supported","unrelated_articles","syndicated_or_not_independent",
        "no_explicit_recent_report_date","insufficient_facts","sensitive_incident",
        "no_respectful_comic_angle","other"}
    group_reasons={}
    if isinstance(diagnostics,list):
        for item in diagnostics[:len(grouped_evidence)]:
            if not isinstance(item,dict):continue
            group_id=item.get("groupId")
            code=item.get("reasonCode")
            if type(group_id) is int and 1<=group_id<=len(grouped_evidence) and code in valid_codes:
                group_reasons[group_id]=code
    print("AI candidate group assessment:",json.dumps({
        "assessed":len(group_reasons),
        "total":len(grouped_evidence),
        "reason_counts":{code:list(group_reasons.values()).count(code) for code in sorted(set(group_reasons.values()))}
    },sort_keys=True),flush=True)
    if sum(draft_preflight_viable(item,now) for item in draft)<2:
        # Reserve API quota for independent reviewer B as soon as two draft
        # candidates exist. A big batch of unreviewed prose is not progress.
        # Separate diagnosis from drafting. A large all-groups request can
        # return only diagnostics, even when some groups are draftable.
        # Retry in small, independent batches; the same downstream source,
        # date, safety and second-AI verification gates still apply.
        # Diagnostics from the first model call are not a veto. In practice a
        # diagnostics-heavy response can label every group "other" or reject
        # viable stories without drafting them. Give each candidate a focused
        # drafting chance; the deterministic and independent audit gates below
        # remain unchanged.
        # Use model diagnostics only for ordering, NEVER as an acceptance veto.
        # An AI-generated draft of a distressing event does NOT consume the
        # chance to try a different ordinary blunder from the source pool.
        already_drafted_urls={url for item in draft if isinstance(item,dict)
            for url in (item.get("verificationUrls") or [])
            if isinstance(url,str)}
        retry_candidates=sorted((
            group for group in grouped_evidence
            if not any(article["url"] in already_drafted_urls
                       for article in group["articles"])
        ),key=lambda g:(
            min(incident_priority(article)[0] for article in g["articles"]),
            0 if group_reasons.get(g["groupId"])=="same_incident_supported" else 1,
            g["groupId"]))
        print("Supplementing insufficient editorial drafts one incident at a time:",
              len(retry_candidates),flush=True)
        for start in range(0,min(len(retry_candidates),4)):
            if AI_QUOTA_BLOCKED or editorial_seconds_remaining()<150:
                print("Ending supplemental drafts: preserving time and quota for verification.",flush=True)
                break
            batch=retry_candidates[start:start+1]
            retry_prompt=(EDITORIAL_MISSION+WRITING_CRAFT+
                " You are editor A. Draft up to five Japanese news stories ONLY "
                "when at least one retrieved publisher article in the input group "
                "supports the same specific real-world mistake. "
                "Return JSON object with stories array. Do not return diagnostics. "
                "If evidence supports the incident but an overt joke feels inappropriate, use a gentle factual irony directed at the decision or plan, not people harmed. Do not invent any event or outcome. "
                "If evidence is insufficient or the incident cannot be treated respectfully, return an empty stories array. "
                "Each story must contain fields "+str(REQUIRED)+", humanActor (person/team who erred), humanMistake (documented human mistake, in Japanese), expectedPlan (verifiable expectation), observedOutcome (what demonstrably went wrong), optional quipSecond (only a genuinely different and funny second punchline), "
                "verificationUrls (1-3 exact retrieved ORIGINAL publisher URLs from that group; prefer independently reported pairs when available), "
                "eventKey (specific incident identifier at least 12 characters), "
                "and evidence (facts supported by the supplied source text). "
                "category must be exactly person, work, company, or sports. "
                "reported must be a source-supported actual publication date within "
                "the last seven days including edition day (JST), formatted YYYY-MM-DD. "
                "Use warm humor about the mistake, never victims or suffering; "
                "allow an optional humane reflection without prescribing feelings, lessons or outcomes. "
                "Do not infer any fact absent from the supplied text. Sharpen the first hit through three private alternatives, and aim the second hit at a DIFFERENT verified contrast; avoid long explanations or rumors. "
                "Edition date JST: "+day+
                ". Candidate groups (hypotheses, NOT proof): "+
                json.dumps(batch,ensure_ascii=False))
            try:
                retry_result=ai(retry_prompt,temperature=0.65)
                retry_stories=retry_result.get("stories",[]) if isinstance(retry_result,dict) else []
                if isinstance(retry_stories,list):
                    draft.extend(retry_stories[:3])
                print("Small-batch draft count:",len(retry_stories) if isinstance(retry_stories,list) else 0,flush=True)
            except (RuntimeError,ValueError,KeyError,TypeError) as exc:
                print("Small-batch draft failed:",type(exc).__name__,flush=True)
            if sum(draft_preflight_viable(item,now) for item in draft)>=2:
                print("Two eligible comedy drafts reserved: moving to independent fact review.",flush=True)
                break
    if AI_QUOTA_BLOCKED:
        print("Gemini key has hit a provider limit; refusing any unverified publication.",flush=True)
        return 0
    if not draft:
        # A successful API call can legitimately return zero verifiable stories.
        # Log only bounded metadata, not untrusted article text or AI prose.
        print("Editorial drafting diagnostic:",json.dumps({
            "candidate_groups":len(groups),
            "group_domain_counts":[len({host(x["url"]) for x in group}) for group in groups[:36]],
            "group_article_counts":[len(group) for group in groups[:36]],
            "source_articles":len(grouped_sources),
            "drafted":0,
            "response_keys":sorted(k for k in draft_response if k in ("stories","status","reason","reasons","diagnostics")),
            "has_model_explanation":any(k in draft_response for k in ("reason","reasons","diagnostics"))
        },sort_keys=True),flush=True)
        print("No draft stories generated; evidence must not be promoted to publication.",flush=True)
        return 0
    seen=previous_events()
    selected=[]
    # Only aggregate rejection categories, never article text or model free-form reasons.
    rejection_counts={}
    def reject(reason):
        rejection_counts[reason]=rejection_counts.get(reason,0)+1
    past=archive_summaries()
    accepted_summaries=[]
    lead_urls={x['url'] for x in source_leads}
    for story in draft:
        if not isinstance(story,dict) or any(not isinstance(story.get(k),str) or not story[k].strip() for k in REQUIRED):
            reject("missing_required_fields");continue
        if not valid_recent_reported(story["reported"],now):
            reject("invalid_reporting_date");continue
        if story["category"] not in ("person","work","company","sports"):
            reject("invalid_category");continue
        # Never substitute an animal sighting or odd fact for a human error.
        fit_issue=editorial_fit_rejection(story)
        if fit_issue:
            reject(fit_issue);continue
        human_issue=human_failure_rejection(story)
        if human_issue:
            reject(human_issue);continue
        quip_issue=comic_line_rejection(story["quip"])
        if quip_issue:
            reject(quip_issue);continue
        # A serious harassment case is not comic relief merely because
        # the harasser made an unwise human choice.
        situational_risk=noncomic_incident_rejection(story)
        if situational_risk:
            reject(situational_risk);continue
        urls=story.get("verificationUrls",[])
        if not isinstance(urls,list) or not (1<=len(urls)<=3) or len(set(urls))!=len(urls) or not all(host(u) for u in urls):
            reject("insufficient_independent_urls");continue
        single_original=(len(urls)==1)
        if single_original:
            if not trusted_original_domain(urls[0]):
                reject("single_source_unvetted");continue
        elif (len({host(u) for u in urls})<2 or not any(
                frozenset(pair) in allowed_pairs
                for pair in __import__("itertools").combinations(urls,2))):
            reject("unmatched_source_pair");continue
        if story["sourceUrl"] not in urls or any(u not in lead_urls for u in urls):
            reject("urls_not_in_fetched_evidence");continue
        if story["sourceUrl"] in seen or story["id"] in seen:
            reject("previously_published");continue
        if BLOCK.search(" ".join(str(story[k]) for k in ("title","summary","detail","quip"))):
            reject("sensitive_content");continue
        event=story.get("eventKey")
        if not isinstance(event,str) or len(event)<12:
            reject("invalid_event_key");continue
        if event in seen:
            reject("duplicate_event");continue
        # Full fetched publisher articles, not model-listed headlines.
        evidence=[]
        for url in urls[:3]:
            if cache.get(url):evidence.append({"url":url,"text":cache[url]})
        if len(evidence)<1 or (not single_original and
                              (len(evidence)<2 or len({host(x["url"]) for x in evidence})<2)):
            reject("insufficient_fetched_original_reporting");continue
        situational_risk=noncomic_incident_rejection(story,evidence)
        if situational_risk:
            reject(situational_risk);continue
        headline_risk=headline_fidelity_risk(story,evidence)
        if headline_risk:
            reject("headline_"+headline_risk);continue
        if editorial_seconds_remaining()<45:
            print("Independent review stopped at editorial time budget; only prior verified articles remain.",flush=True)
            break
        try:
            audit=ai(EDITORIAL_MISSION+WRITING_CRAFT+" You are independent adversarial fact checker B. You must verify every concrete "
          "claim in this Japanese article against the fetched original source article text(s) below. "
          "One credible ORIGINAL reporter's complete fetched article may support an incident. If a second independent original is supplied, verify both. Reject press-release paraphrases, syndicated copies, aggregators, social posts and unsupported claims; for one-source cases explicitly verify FIRSTHAND reporting from the article text and return boolean flags originalReporting, factsVerified, dateVerified, safeTone. Set any uncertain flag false before approval. Reject mismatched dates, invented quotes, "
          "unsafe jokes, generic news without a genuine failure, prescriptive or humiliating reader commentary, and repeated events. An ordinary individual's consequential, independently documented mistake is as eligible as a serious corporate or institutional failure when the humor targets a decision, irony or overconfidence rather than a victim or private vulnerability. Do not reject solely because the subject is not famous or the consequences are personal, financially serious or politically significant. Reject humiliating exposure of private individuals and unsupported personal details. Compare against the prior published events and already selected events, "
          "reject the same underlying incident even if the title, source, language or URL differs. "
          "Reject if the writing shames a person, trivializes hardship, pressures readers to feel grateful, cheerful or hopeful, gives therapy-like advice, or ends every story with a preachy life lesson. The best outcome is a spontaneous smile or a calmer minute, never a promised cure. "
          "Reject location claims inferred from the feed's language or edition instead of the actual article text, invented customs, national stereotypes, or jokes comparing the reader's troubles with someone else's troubles. "
          "Reject if evidence is insufficient or unclear. BEFORE looking at the jokes verify humanActor and humanMistake against the original: the identified human actually made a specific wrong assumption, choice, mix-up or operational error that drove the outcome, rather than just reacting normally to an animal sighting, animal rescue, wildlife behavior, generic surprising fact, or innocent person's misfortune. Do not invent a human mistake. Reject generic animal oddities even if they are charming. Deliberate harassment of firefighters or emergency responders, threats, distress, abuse and unsafe confrontations are not lighthearted human blunders; reject them even when there is a clever-sounding irony in the reporter's framing. A story has to be BOTH a documented human mistake AND a genuinely safe situation to laugh at, rather than a serious conflict rebranded as comedy. A ceremony protest, disciplinary dispute, student suspension, ministerial walkout, or public call to apologize is NOT a harmless human mix-up. Reject such conflicts without a SEPARATE actual comic mistake supported by original reporting. Require humanFailureConfirmed=true ONLY if this error is explicit in the source. Verify the exact expectedPlan AND observedOutcome against retrieved source text: they must establish a real, non-tragic failure rather than merely an executive transition, surprising news or corporate PR. Recheck that the headline and both Japanese article paragraphs stay within what the cited sources substantiate. Carefully verify ENGLISH-to-JAPANESE institution words: plant nursery is a plant-growing nursery, not a botanical garden (植物園) or a human maternity ward (産院). Verify LEGAL STATUS separately: 'to be charged' is not arrested, convicted, or already prosecuted. Do not imply a criminal plan, motive, cunning, repeated actions or a quote unless the source explicitly supports it. Metaphorical institutions or invented services belong only in clearly labeled jokes, never a factual headline. Reject private-life allegations, romantic gossip, and speculation about motives, even where public figures are involved. Do not approve on journalistic fame, narrative appeal or geographic balance alone. Also reject jokes that treat uncertain causes, rumors or accusations as facts; check that quipSecond really changes comic angle rather than paraphrasing quip. Also perform a comedy-editor check on EACH quip: concrete setup supported by sources, a specific comically unexpected payoff at the END, first-read clarity in natural spoken Japanese, and a distinctly new premise for quipSecond IF PRESENT. A single superb quip is better than two weak jokes. Rate comicPunchlineWorks=true only if the first quip is a real setup→payoff based on the verified HUMAN ERROR, not a headline recap or vague 'まさか', '守備範囲が広い' or '世界は自由'. Reject generic recap disguised as a punchline, overlong commentary, forced wordplay and recycled 'unexpected!' endings, even when factual; ask the writer to sharpen before publication. Reject a quip that a Japanese reader cannot understand on the first read after the summary, and reject poetic or counterfactual wording that misstates the factual outcome. "
          "Return explicit independent booleans headlineGrounded,translationAccurate,legalStatusAccurate,humorRespectful,jokeClear; EVERY field must be true for approval, unknown must be false. Even if approved=true, any absent/false field means rejection. Output only JSON {approved:boolean,originalReporting:boolean,factsVerified:boolean,dateVerified:boolean,safeTone:boolean,headlineGrounded:boolean,translationAccurate:boolean,legalStatusAccurate:boolean,humorRespectful:boolean,jokeClear:boolean,humanFailureConfirmed:boolean,comicPunchlineWorks:boolean,reason:string}. Article: "
          +json.dumps(story,ensure_ascii=False)+" Previously published events: "
          +json.dumps(past,ensure_ascii=False)+" Already selected today: "
          +json.dumps(accepted_summaries,ensure_ascii=False)+" Fetched original source text(s): "
          +json.dumps(evidence,ensure_ascii=False))
        except RuntimeError as exc:
            print("Independent review paused safely:",type(exc).__name__,flush=True)
            # Previously audited stories remain eligible, but never accept the interrupted draft.
            break
        if audit.get("approved") is not True:
            # Free-form AI reasons are not logged; only bounded, diagnostic labels.
            reason=str(audit.get("reason","")).lower()[:500]
            if any(w in reason for w in ("date","time","old","recent")):category="audit_date"
            elif any(w in reason for w in ("same incident","duplicate","repeat","previous","syndicat")):category="audit_duplicate_or_syndication"
            elif any(w in reason for w in ("joke","humor","harm","unsafe","sensitive","victim")):category="audit_safety"
            elif any(w in reason for w in ("source","evidence","corroborat","unsupported","fact","verify","claim")):category="audit_evidence"
            else:category="audit_other_or_unspecified"
            reject(category);continue
        if not independent_editorial_quality_passed(audit):
            reject("editorial_headline_or_humor_quality_not_confirmed");continue
        if single_original:
            if any(audit.get(field) is not True for field in
                   ("originalReporting","factsVerified","dateVerified","safeTone")):
                reject("single_original_not_verified");continue
            story["sourceBasis"]="original-report"
            story["originalReportingVerified"]=True
            story["attributionNote"]=SINGLE_SOURCE_NOTE
        story["editorVerified"]=True
        story["humorSafe"]=True
        # Human error and comic impact are specifically source-verified by B.
        story["humanFailureVerified"]=True
        # Private proof; public JSON never exposes model review fields.
        story["editorQualityVerified"]=True
        seen.update((story["sourceUrl"],story["id"],event))
        second=story.get("quipSecond")
        if not (isinstance(second,str) and 12<=len(second.strip())<=100
                and second.strip()!=story["quip"].strip()
                and not BLOCK.search(second)):
            story.pop("quipSecond",None)
        else:
            story["quipSecond"]=second.strip()
        selected.append(story)
        accepted_summaries.append({"title":story["title"],"summary":story["summary"],"country":story["country"]})
        if len(selected)>=6:break
    print("Editorial decision counts:",json.dumps({"drafted":len(draft),"approved":len(selected),"rejected":rejection_counts},sort_keys=True),flush=True)
    if not selected:
        print("Source-text verification approved no stories; no publication.");return 0
    # Geographic diversity applies ONLY after source-text and AI fact review.
    country_history,category_history=recent_diversity_counts(now.date())
    selected=select_diverse_verified_stories(selected,country_history,category_history)
    print("Nightly verified selection:",len(selected),"source-checked stories;",
          "target 3, release 1-3.",flush=True)
    print("30-day editorial diversity:",json.dumps({
        "historical_countries":len(country_history),
        "selected_countries":len({country_code(story["country"]) for story in selected
                                  if country_code(story["country"])}),
        "selected_regions":len({country_region(story["country"]) for story in selected
                                if country_region(story["country"])}),
        "selected_categories":len({story["category"] for story in selected}),
        "history_articles":sum(country_history.values())
    },sort_keys=True),flush=True)
    # A fresh closing line is generated from this edition's verified summaries.
    # Never use AI-generated text as an additional factual news claim.
    recent_lines=[]
    for archive_file in Path("data/archive").glob("????-??-??.json"):
        try:
            previous=json.loads(archive_file.read_text(encoding="utf-8"))
            previous_date=datetime.strptime(previous.get("editionDate",""),"%Y-%m-%d").date()
            if previous.get("status")=="published" and 0<(now.date()-previous_date).days<=60:
                line=previous.get("nightlyMessage")
                if isinstance(line,str) and line.strip():recent_lines.append(line.strip())
        except (ValueError,OSError,TypeError,KeyError):
            continue
    recent_lines=recent_lines[-60:]
    nightly_text=None
    try:
        if editorial_seconds_remaining()>75 and not AI_QUOTA_BLOCKED:
            nightly_text=compose_nightly_comedy(selected,recent_lines)
    except (RuntimeError,ValueError,KeyError,TypeError) as exc:
        print("Nightly comedy editorial review unavailable:",type(exc).__name__)
    if nightly_text is None:
        print("Nightly line generation did not pass validation; using safe publisher fallback.")
    payload={"status":"approved","editionDate":day,"editionType":"regular","title":day+"｜世界の大失敗ニュース" ,
      "editorApproved":True,"factChecked":True,"humorReviewed":True,"approvedBy":"automated-two-stage-review","stories":selected}
    if nightly_text is not None:payload["nightlyMessage"]=nightly_text
    # The publisher's exact validation contract is also the AI approval gate.
    from publish_approved import validate_approved
    try:
        validate_approved(payload,day)
    except (ValueError,TypeError,KeyError) as exc:
        print("No publisher-valid AI edition:",type(exc).__name__,flush=True)
        return 0
    target=Path("data/approved")/(day+".json")
    if target.exists():return 0
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print("Created AI issue with",len(selected),"verified stories",day)
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("Fail-closed AI review:",type(e).__name__,str(e),file=sys.stderr)
        sys.exit(1)
