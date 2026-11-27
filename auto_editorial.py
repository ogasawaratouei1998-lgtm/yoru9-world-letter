#!/usr/bin/env python3
"""Free-tier AI editorial pipeline. Fail closed: no key or no verified story means no publication."""
import json, os, re, sys, ipaddress, socket, time
from country_codes import catalog, country_code, country_codes, country_region, normalize_reporting_country
from trusted_originals import trusted_original_domain, SINGLE_SOURCE_NOTE
from editorial_quality import (headline_fidelity_risk, independent_editorial_quality_passed,
    editorial_review_reasons,
    independently_approved_secondary_quip, editorial_rubric,
    editorial_rubric_rejection, verified_rubric_for_edition,
    choose_pre_review_quip)
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
LOCAL_EDITORIAL=os.getenv("YORU9_EDITORIAL_BACKEND","gemini")=="local"
LOCAL_BACKEND_FAILED=False
LOCAL_CANDIDATE_ERRORS=0
LOCAL_DRAFT_OUTCOMES={"empty":0,"invalid":0}
LOCAL_DRAFT_REASONS={}
REQUIRED=("id","country","category","categoryLabel","label","title","summary","detail","quip","sourceName","sourceUrl","reported")
BLOCK=re.compile(r"死亡|殺害|負傷|災害|差別|自殺|銃撃|戦争|死者|犠牲者|killed|murder|fatal|death|died|suicide|rape|shooting|injured|hospitalized|war|bombing|disaster",re.I)
# An app about humane, verifiable mistakes must not turn personal scandals
# into entertainment. This conservative deterministic filter supplements AI.
PRIVATE_GOSSIP=re.compile(r"不倫|浮気|私生活|婚外|私的な関係|恋愛関係|交際相手|extramarital|affair\\b|alleged spy",re.I)
# Narrow, deterministic safeguard against coercive self-help framing. General
# words such as "hope" or "tomorrow" are intentionally NOT blanket-banned.
READER_PRESSURE=re.compile(r"あなたより大変|悩みなんて小さい|たかが失敗|感謝すべき|笑うべき|もっと頑張れ|努力が足りない|必ず元気になる|必ず幸せになる|明日は絶対に良くなる|笑わなければならない",re.I)

def semantic_matching_needed(headline_pair_count):
    """AI cross-publisher corroboration has no role in publisher-trust mode.

    One vetted news company's article is sufficient. Local headline grouping
    can still supply optional creative context without model calls. Keep this
    helper for stable caller/test compatibility.
    """
    return False


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
            or len(expectation.strip())<6 or len(outcome.strip())<6):
        return "missing_source_grounded_plan_or_outcome"
    if expectation.strip().casefold()==outcome.strip().casefold():
        return "no_observed_failure_contrast"
    return None
# Rank incident-specific reporting ahead of generic world-news headlines.
# Ranking only changes retrieval order; it never certifies a fact or relaxes review.
EDITORIAL_MISSION=("Publish only source-supported HUMAN FAILURES with extraordinary, safe-to-report consequences: overwhelmingly prioritize a concrete INDIVIDUAL who personally made an astonishing misjudgment, catastrophic non-tragic miscalculation or spectacular blunder. The source need not literally say mistake, but the actual flawed decision and consequence MUST be documented. Mere unusual decisions, routine corporate setbacks and minor mix-ups are NOT substitutes. "
    "Every story must have two essential parts: source-supported facts about a specific human action and surprising outcome; "
    "and a warm, witty AI quip aimed at the decision, contradiction or overconfidence rather than a victim. "
    "A humane aftertaste is optional, not a compulsory lesson or an instruction for the reader to feel better. "
    "The quip MUST deliver a hard spoken manzai-stage punch with a new angle, never a mild observation or rewording; aim for a vivid, quotable contrast between plan and reality without exaggerating evidence. "
    "The primary editorial target is a BIG, reported failure caused by a SPECIFIC PERSON: an extraordinary wrong judgment, ambitious bet, spectacular miscalculation, preventable personal oversight, or overconfident plan with a striking, documented non-tragic outcome. Big means the scale of the mismatch or practical consequences for the actor, not their fame or the size of a company. Prefer real consequential personal blunders over ordinary typos, trivial customer mix-ups and routine harmless slips. Small mistakes are backups only when exceptional and genuinely funny; never manufacture seriousness. "
    "Choose a 4/5 or 5/5 spontaneous EH?! from the personally made mistake and its unusually large, ironic or lasting result. When multiple safe, reported incidents qualify, first select a substantial personal failure with a concrete chain of cause and consequence; do NOT prefer a mundane small mix-up just because it seems gentler. Avoid crises, loss of life and victims used as entertainment. "
    "Never replace a genuine hard-to-believe sourced human episode with boring council votes, corporate plans, animal filler or generic news to fill a quota. "
    "A CEO resignation, appointment, product launch, earnings report or sensational headline is NOT itself a verified mistake. Publish it only if the supplied reporting describes a concrete original expectation and a documented failure to meet it. "
    "Give priority to unbelievable but documented personal, sports, cultural, street and work episodes; corporate stories are a rare exception, not the default. "
    "Exclude salacious private-life allegations and romantic rumors even about public figures, whether reported elsewhere or not. "
    "Search across continents and languages; seek balanced country and regional coverage across successive editions, not just US/UK or a few major powers. Prefer distinct countries in each issue when suitable reported stories are available; never invent coverage for geographic quotas. "
    "Never use geography as a substitute for a real failure or humane humor. "
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
    "The first selected story is the nightly lead and should be the largest reported, directly attributable and humane-to-laugh-at INDIVIDUAL failure, if one qualifies. Rank by a striking documented decision-versus-result contrast, not human suffering, infamy, rumors or raw financial losses. "
    "A great lead is a genuine, remarkable INDIVIDUAL miscalculation with enough real-world scale to surprise even before the joke: what the person planned, the decision they botched, and the costly or astonishing result. Prefer striking but safe personal failures over tiny typos and routine signage errors. Avoid emergency alerts, financial suffering of victims, unproven blame and empty executive-transition headlines. Never overstate amounts or consequences. "
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
    "the PLAN, ASSUMPTION or DECISION, never a victim. Prefer hard-hitting absurdity "
    "over ridicule, platitudes, generic encouragement or forced puns. "
    "The reader may be exhausted and may not laugh today. They must feel welcome even if they only read one paragraph and leave. "
    "Never write moral lessons, productivity advice, prescriptive coping steps or motivational slogans; land a crisp, hard, unmistakably spoken comedic final beat instead of polite commentary. "
    "Do not say 'your problems are nothing', dismiss the reader's pain, "
    "invent a happy ending, or imply the subjects were secretly fine. "
    "Before outputting JSON, privately draft four sharply different one-liners. For each, locate the HUMAN-SCALE CONTRADICTION, then put a short, concrete, surprising payoff at the end. Select the line that only works for THIS incident. Do not pad the joke with a recap or offer a lecture. Apply the comic editor's test: SETUP must contain a source-verified concrete fact, PAYOFF must invert the expectation in one understandable beat. The follow-up must have a new premise, not a synonym for the first. Do not call a simple recap a joke. Favor natural spoken Japanese over stock phrases like '情報量が多い' or a string of 'まさか'. Avoid long similes, recaps, generic cheering, forced AI/reboot metaphors, or hedged endings like \"ようです\". If unproven causes or personal allegations are the only funny angle, do not joke about them. "    "If the facts are sufficient but the first joke is weak, try three angles "
    "internally: inflated ambition versus mundane reality; a reasonable assumption "
    "that backfired; the tiny missed step behind a grand plan. Pick the hardest accurate joke that targets the absurdity rather than a harmed person. "
    "Do not include these internal options in the JSON. "
    "A weak punchline is a writing problem to revise, not automatically a reason "
    "to discard a verified, safely discussable incident. "
)

# A's comedy process is distinct from B's independent verdict.
# In manzai the article's verified headline is already the "furi" (setup).
# The quip should be the "tsukkomi", not a second reporting paragraph.
MANZAI_CRAFT=(
    " YOU ARE AN UNCOMPROMISING MANZAI TSUKKOMI ARTIST, NOT A POLITE NEWS COMMENTATOR. "
    " The user needs a quick hard spoken punch, not a would-you-believe remark. "
    " The verified article is the setup; interrupt the ABSURDITY with a sharp "
    " new angle and decisive landing beat: やろ, すな, どうすんねん, なんでやねん when natural. "
    " Be aggressive toward paradoxes, never identities, vulnerable people or tragedy. "
    " If the line sounds like a pleasant comment, discard it. "
    " You are writing short Japanese MANZAI TSUKKOMI, not a summary, gag list, "
    "advertising slogan or moral. The factual article has ALREADY done the setup. "
    "Start from ONE source-proven human action or astonishing contradiction, then flip the "
    "reader's expected role, purpose or result in the last short phrase. "
    "Privately compare FOUR genuinely different mechanisms: (a) intended "
    "function versus actual function, (b) accidental role reversal, "
    "(c) a literal meaning colliding with its practical result, and "
    "(d) a tiny real oversight defeating a grand plan. Pick the strongest; "
    "never force all four or invent a joke-shaped extra incident. "
    "Do a read-aloud one-breath test: short natural spoken Japanese, no "
    "translation-like bureaucracy, two explanations, long lead-in, "
    "abstract analogy, or 'you had to be there' context. The headline "
    "already tells WHO and WHAT, so never just retell it with 'まさか' "
    "or add the funny proper noun as the supposed payoff. "
    "Across an issue, do not end every tsukkomi with the same catchphrase "
    "such as やないか or かい. Try genuinely different punchline rhythms "
    "only when natural: a terse role reversal, an earned question, "
    "a concrete noun-ending twist, or a sharp standard-Japanese observation. "
    "Kansai dialect is welcome when it fits, not a mandatory template. "
    "NEVER sacrifice fact fidelity, humane tone or the incident-specific "
    "last beat merely to make the grammatical ending different. "
    "The LAST beat must add a new, source-grounded funny connection or "
    "role inversion that was not already explicit in the title/summary; "
    "it must make sense on a first reading WITHOUT the audience doing "
    "extra homework. Avoid generic endings like '守備範囲が広い', "
    "'情報量が多い', 'すごい時代', or '仕事が増えた'. "
    "Do NOT invent literal dialogue, quotes, feelings, institutions, "
    "consequences, blame or heroics: creative figurative language is OK "
    "only when unmistakably a joke, not a factual claim. "
    "Make the TARGET the mistake or contradictory plan, not a victim, "
    "worker who helped, nationality, identity or private person. "
    "For quipSecond, require a distinct verified setup AND distinct payoff; "
    "if it is merely a different metaphor for quip, omit it. "
    "If all safe angles are plain recaps, return no quip-worthy story. "
)
QUIP_ALTERNATIVE_REQUIREMENT=(
    " For each story return quipCandidates: THREE different concise Japanese "
    "first-punchlines (18-55 characters each), not paraphrases of one another. "
    "Try (1) the real purpose becoming its opposite, (2) a documented role "
    "reversal, and (3) a concrete object or decision becoming the unlikely "
    "star of the outcome. Do not invent any events, quotes, motives or harm. "
    "Avoid interchangeable endings and headline recaps. The best candidate "
    "goes into quip; the downstream selector compares all options BEFORE the "
    "same mandatory independent source, safety and comedy review. "
)

MANZAI_REVIEW=(
    " Reject soft comments, essay conclusions and headline recaps. "
    " A 4/5 WOW fact and independently hilarious spoken final beat are required. "
    " Return shockFactorConfirmed and stageTsukkomiConfirmed true only after "
    " independent original-report fact checks and a first-read punchline test. "
    " You are an independent tough Japanese MANZAI stage editor and source "
    "fact-checker, NOT the writer's friend. A clever fact by itself is not "
    "a punchline. Examine the FIRST quip against the already-shown title "
    "and summary. Explicitly return firstQuipAngleEarned=true ONLY if it "
    "draws a NEW, article-specific, document-supported comic contradiction "
    "in human purpose/role/result; reject obvious recap and mere renaming. "
    "Return firstQuipNaturalSpeech=true ONLY if the quip can be said aloud "
    "in one natural Japanese breath and understood immediately without "
    "obscure metaphors, extra reading, translated phrasing or explaining "
    "the joke. Return firstQuipFinalBeat=true ONLY if its FINAL meaningful "
    "phrase lands a distinct surprise rather than finishing with "
    "'まさか', an adjective, a generic remark, a name or a life lesson. "
    "Any doubt means false. A named animal or improbable event is not "
    "automatically a human mistake or a funny tsukkomi. Preserve accurate "
    "reporting and never soften safety or factual standards for humor. "
)

# Two-stage comedy editing keeps the final line distinct from a news recap.
# The independent reviewer may choose only from the drafted, locally screened options.
NIGHTLY_COMEDY_CRAFT=(
    "あなたは『よる9じの世界便り』の放送作家です。 "
    "その日の検証済み記事から、最も笑える具体的な出来事を一つだけ選んでください。無理に3本をまとめて共通テーマを作らないこと。気が向かなければ笑わなくてもよい読者に向け、笑いや元気を強要しません。 "
    "今夜のひと言はニュースの要約でも固有名詞の羅列でもなく、実際に紹介した記事の具体物・行為・数字を一つ以上言葉として出し、読後にだけ効く鋭いオチです。根拠のない職業一般の設定、架空の求人票・担当欄・台本・会議・マニュアルを持ち込むのは禁止。 "
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
    # Do not ask the reviewer to rescue an ungrounded abstract metaphor.
    from nightly_quality import incident_specific_nightly_line
    candidates=[item for item in candidates
                if incident_specific_nightly_line(item,stories)]
    if not candidates:
        return None
    review=ai(
        "あなたは執筆者とは独立した日本語のお笑い編集者兼事実監査者です。"
        "次の候補から『フリ→意外なオチ』『一読で分かる』『自然な日本語』『読後感』『事実に基づく』の"
        "5軸で最も良い1案のみを選んでください。確認済みのニュースにない事実を含む候補は不可。"
        "複数記事の内容をただ列挙する総集編、精神論、説教、平凡な『想定外』『自由です』、"
        "無理なダジャレ、記事本文と重複する説明は不合格。"
        "記事に実在する物・行為にひも付かない世界全体の比喩や、根拠のない求人票・仕事内容・予定表のような新しい設定は失格。"
        "事実に根差す具体的なフリがあるか、オチが本当に意外で一度で伝わるか、それぞれ別個に判定してください。"
        "どれも弱ければ approved:false にしてください。"
        "JSON {\"approved\":true/false,\"bestIndex\":0,\"factAnchorVerified\":true/false,\"comicPayoffWorks\":true/false,\"reason\":\"短い理由\"} のみ。"
        "検証済み記事:"+json.dumps(payload,ensure_ascii=False)+
        "候補:"+json.dumps(candidates,ensure_ascii=False),
        temperature=0.1)
    if not isinstance(review,dict) or review.get("approved") is not True:
        return None
    if review.get("factAnchorVerified") is not True or review.get("comicPayoffWorks") is not True:
        return None
    index=review.get("bestIndex")
    if type(index) is not int or not 0<=index<len(candidates):
        return None
    return candidates[index]

# Headline text NEVER proves blame: ranking is a separate, unverified discovery stage.
from editorial_discovery import (incident_priority, discovery_desk, prioritize_comic_groups,
    host, source_reading_stop_reason, balanced_source_retrieval, source_title_is_policy_explainer,
    INCIDENT_TERMS, COMIC_MISSTEP_TERMS, SERIOUS_CONFLICT_TERMS, POLICY_EXPLAINER_TITLE,
    PERSONAL_ACTOR_TERMS, LARGE_PERSONAL_CONSEQUENCE_TERMS)

def prioritize_personal_drafts_for_review(drafts, ready, source_leads):
    """Prioritize major personal evidence independently of destination-photo readiness.

    Draft wording and claimed location are unverified at this stage. Use the
    already-fetched *publisher headline* only as a ranking hint; full source
    fidelity and the independent audit still decide publication. The legacy
    ready argument is ignored; country enrichment is separate.
    """
    by_url={lead.get("url"):lead for lead in source_leads
            if isinstance(lead,dict) and isinstance(lead.get("url"),str)}
    def key(draft):
        urls=draft.get("verificationUrls",[]) if isinstance(draft,dict) else []
        if not isinstance(urls,list):
            urls=[]
        ranks=[incident_priority(by_url[url])[0] for url in urls
               if isinstance(url,str) and url in by_url]
        major=bool(ranks) and min(ranks)<0
        return 0 if major else 1
    return sorted(drafts,key=key)


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

class PublicationMetadata(HTMLParser):
    """Read explicit publication metadata, never feed discovery or modified dates."""
    def __init__(self):
        super().__init__()
        self.values=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="meta" and (a.get("property")=="article:published_time"
                            or a.get("itemprop")=="datePublished"):
            self.values.append(a.get("content"))

def publisher_publication_date(html):
    parser=PublicationMetadata()
    parser.feed(html)
    values=list(parser.values)
    def walk(node):
        if isinstance(node,list):
            for item in node:walk(item)
        elif isinstance(node,dict):
            kind=node.get("@type",[])
            kinds=kind if isinstance(kind,list) else [kind]
            if any(isinstance(k,str) and k.lower() in
                   ("article","newsarticle","reportagearticle","blogposting") for k in kinds):
                values.append(node.get("datePublished"))
            for key in ("@graph","mainEntity"):
                if key in node:walk(node[key])
    scripts=re.findall(r'<script\b[^>]*type=["\x27]application/ld\+json["\x27][^>]*>(.*?)</script\s*>',html,re.I|re.S)
    for script in scripts[:12]:
        try:walk(json.loads(script))
        except (ValueError,TypeError,RecursionError):continue
    dates=set()
    for value in values:
        if not isinstance(value,str) or not re.match(r"^\d{4}-\d{2}-\d{2}(?:$|T|\s)",value):
            continue
        try:dates.add(datetime.strptime(value[:10],"%Y-%m-%d").date().isoformat())
        except ValueError:continue
    # Conflicting dates must not be resolved by guessing.
    return next(iter(dates)) if len(dates)==1 else None

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
            if trusted_original_domain(url) and not trusted_original_domain(newurl):
                raise ValueError("unapproved_publisher_redirect")
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
        html=raw.decode("utf-8",errors="replace")
        text=extracted_article_text(html,min_chars=min_chars)
        if len(text)<min_chars:
            if diagnostics is not None:diagnostics.append("short_html")
            return ""
        if diagnostics is not None:diagnostics.append("fetched")
        published=publisher_publication_date(html)
        if published:
            text="Publisher datePublished: "+published+"\n"+text
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
# The public model catalog is constant for one 9-minute review session.
# Avoid an extra authenticated provider GET on every A/B-editor call.
RUN_MODEL_CATALOG=None
# A repeatedly unavailable model should not consume the next editorial call.
# This is run-local only; no account rotation or quota bypass.
RUN_UNAVAILABLE_MODELS=set()

def editorial_seconds_remaining():
    return float("inf") if RUN_DEADLINE is None else max(0.0,RUN_DEADLINE-time.monotonic())

def ai(prompt,temperature=0.1):
    global ACTIVE_MODEL, AI_QUOTA_BLOCKED, RUN_MODEL_CATALOG, LOCAL_BACKEND_FAILED, LOCAL_CANDIDATE_ERRORS
    if LOCAL_EDITORIAL:
        from local_editorial import (generate_json, LocalCandidateError, SCREEN_PREFIX,
                                     COPY_PREFIX,COUNTRY_PREFIX,JOKE_PREFIX)
        if LOCAL_BACKEND_FAILED:
            raise RuntimeError("Local editorial circuit open")
        audit_prompt=prompt.startswith("JAPANESE EDITORIAL AND HUMOR REVIEW")
        screen=prompt.startswith(SCREEN_PREFIX)
        remaining=editorial_seconds_remaining()
        reserve=0 if audit_prompt else 420 if screen else 300
        if remaining-reserve<30:
            raise LocalCandidateError("Local editorial time budget exhausted")
        stage_limit=1000 if prompt.startswith(COPY_PREFIX) else 80 if prompt.startswith(COUNTRY_PREFIX) else 300 if prompt.startswith(JOKE_PREFIX) else 1300
        try:
            return generate_json(prompt,temperature,
                                 min(45 if screen else 240,remaining-reserve),
                                 160 if screen else 512 if audit_prompt else stage_limit)
        except LocalCandidateError as exc:
            # A bad JSON response or token limit is local to this request.
            # A connection/HTTP failure still opens the backend circuit below.
            LOCAL_CANDIDATE_ERRORS+=1
            print("Local candidate request rejected:",type(exc).__name__,str(exc),flush=True)
            raise
        except RuntimeError:
            LOCAL_BACKEND_FAILED=True
            raise
    if not KEY:raise RuntimeError("GEMINI_API_KEY not configured; no publication")
    if AI_QUOTA_BLOCKED:raise RuntimeError("Gemini API quota/permission circuit open; no publication")
    if editorial_seconds_remaining()<=5:
        raise RuntimeError("Editorial run time budget exhausted; no publication")
    call_deadline=time.monotonic()+75
    if RUN_DEADLINE is not None:call_deadline=min(call_deadline,RUN_DEADLINE)
    def bounded_timeout():
        return min(40,max(1,call_deadline-time.monotonic()))
    if RUN_DEADLINE is None:
        # Standalone/test calls still resolve the live catalog independently.
        models=available_models()
    else:
        if RUN_MODEL_CATALOG is None:
            RUN_MODEL_CATALOG=tuple(available_models())
        models=list(RUN_MODEL_CATALOG)
    if RUN_DEADLINE is not None:
        models=[model for model in models if model not in RUN_UNAVAILABLE_MODELS]
    if ACTIVE_MODEL in models:
        models=[ACTIVE_MODEL]+[model for model in models if model!=ACTIVE_MODEL]
    if not models:
        raise RuntimeError("Gemini provider unavailable across all attempted models")
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
                    for delay in ((2,) if RUN_DEADLINE is not None else (2,6)):
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
                    if RUN_DEADLINE is not None:
                        RUN_UNAVAILABLE_MODELS.add(model)
                    break
                if exc.code not in (404,400):raise RuntimeError("Gemini API HTTP "+str(exc.code))
            except (URLError, TimeoutError, ConnectionError, OSError) as exc:
                # Network timeouts are not editorial rejections. Try the next
                # supported model/version; do not approve an unverified story.
                print("Gemini request unavailable:",model,version,type(exc).__name__,flush=True)
                last_error=type(exc).__name__
                continue
    raise RuntimeError("No available model/version generated content; last HTTP "+str(last_error))

def surprise_topic(story):
    """Small, explainable motifs for avoiding repetitive nightly stories."""
    words=" ".join(str(story.get(key,"")) for key in
                   ("title","summary","humanMistake")).lower()
    motifs=(
        ("sports",r"審判|選手|試合|得点|ゴール|\b(?:referee|match|goal|athlete|coach)\b"),
        ("signs",r"誤字|綴り|看板|表示|壁画|スペル|\b(?:typo|misspell|mural|signage)\b"),
        ("orders",r"配送|配達|発注|注文|荷物|\b(?:delivery|delivered|order|parcel)\b"),
        ("mistaken_identity",r"見間違|人違い|勘違い|取り違え|\b(?:mistook|misidentif|mistaken identity)\b"),
        ("technology",r"人工知能|生成ai|システム|アプリ|\b(?:ai.generated|software|app|algorithm)\b"),
        ("public_plans",r"市役所|行政|式典|イベント|\b(?:council|mayor|ceremony|festival)\b"),
        ("work",r"職場|従業員|仕事|店員|\b(?:workplace|employee|worker|staff)\b"),
    )
    for theme,pattern in motifs:
        if re.search(pattern,words,re.I):
            return theme
    return "other:"+str(story.get("category","unknown"))


def recent_topic_counts(today,days=30):
    """Only published issues contribute to last-month motif rotation."""
    from collections import Counter
    counts=Counter()
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            issue=json.loads(file.read_text(encoding="utf-8"))
            archive_day=datetime.strptime(issue.get("editionDate",""),"%Y-%m-%d").date()
            if issue.get("status")!="published" or not (
                    today-timedelta(days=days)<=archive_day<today):
                continue
            for story in issue.get("stories",[]):
                counts[surprise_topic(story)]+=1
        except (OSError,ValueError,TypeError,KeyError):
            continue
    return counts


def recent_country_cooldown_counts(today, days=3):
    """Penalize a country featured in the immediately preceding editions.

    Never infer the location from RSS publisher. Count actual countries in
    published archives only; 1-day recency carries more weight than 3 days.
    This affects ranking solely among independently verified candidates.
    """
    from collections import Counter
    weights={1:9,2:4,3:2}
    counts=Counter()
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            issue=json.loads(file.read_text(encoding="utf-8"))
            day=datetime.strptime(issue.get("editionDate",""),"%Y-%m-%d").date()
            age=(today-day).days
            if (issue.get("status")!="published" or
                    not 1<=age<=days):
                continue
            for story in issue.get("stories",[]):
                for code in set(country_codes(story.get("country",""))):
                    counts[code]+=weights.get(age,1)
        except (OSError,ValueError,TypeError,KeyError):
            continue
    return counts


def audited_major_personal_failure(story):
    """Read ONLY independent audit verdict, never infer stakes from a headline.

    This private ranking hint cannot approve or reject reporting. The verifier
    checks the named actor, source-backed decision and concrete significance.
    """
    return (story.get("category") in ("person","work","sports")
            and story.get("majorPersonalFailureVerified") is True)

def select_diverse_verified_stories(pool, country_history, category_history, topic_history=None, lifetime_country_history=None, recent_country_cooldown=None, selection_seed=None):
    """Select all eligible audited stories without a fixed daily article quota.

    Country is the fact-checked event country, not the RSS feed locale.
    Unknown event countries receive no fictitious diversity credit.
    """
    from collections import Counter
    from quip_variety import repeated_cadence_count, repeated_exact_quip_count
    if not pool:
        return []
    region_history=Counter()
    for country,count in country_history.items():
        region=country_region(country)
        if region:
            region_history[region]+=count
    topic_history=topic_history or Counter()
    lifetime_country_history=lifetime_country_history or Counter()
    recent_country_cooldown=recent_country_cooldown or Counter()
    # ALL already-audited stories survive, including unusual corporate
    # stories that individually passed the same strict comic editorial audit.
    # Rotate ordering for diversity; never drop a valid article to hit a
    # numeric target, desk allotment or regional quota.
    def random_tiebreak(indices):
        if selection_seed is None:
            return -sum(indices)
        # Date-seeded stable shuffle among equally qualified combinations.
        # This never chooses unverified news or changes factual countries.
        import hashlib
        identifiers=sorted(str(pool[i].get("id","")) for i in indices)
        digest=hashlib.sha256((str(selection_seed)+"|"+
                               "|".join(identifiers)).encode("utf-8")).digest()
        return int.from_bytes(digest[:8],"big")
    def diversity_score(indices):
        stories=[pool[i] for i in indices]
        country_groups=[country_codes(story.get("country")) for story in stories]
        known_countries=[country for group in country_groups for country in group]
        known_regions=[country_region(country) for country in known_countries
                       if country_region(country)]
        categories={story["category"] for story in stories}
        topics=[surprise_topic(story) for story in stories]
        # Actual country breadth and desk breadth beat stale dominant markets.
        # A country used yesterday is penalized heavily BEFORE any long-run
        # frequency and genre tie-breakers, not silently treated as "fresh".
        return (sum(audited_major_personal_failure(story) for story in stories),
                # Audited content strength takes priority over novelty of country.
                sum(sum((editorial_rubric(story) or {}).values()) for story in stories),
                len(set(known_countries)),len(categories),
                -sum(recent_country_cooldown[country] for country in known_countries),
                len(set(known_regions)),
                len({country for country in known_countries
                     if lifetime_country_history[country]==0}),
                -sum(category_history[story["category"]] for story in stories),
                len(set(topics)),
                -sum(topic_history[topic] for topic in topics),
                -sum(region_history[region] for region in known_regions),
                -sum(country_history[country] for country in known_countries),
                -sum(lifetime_country_history[country] for country in known_countries),
                # At otherwise equal factual/region/genre priority, avoid an
                # issue that ends every gag with the same verbal tic.
                # It is a *tie-breaker*, never a story-quality or truth veto.
                -repeated_cadence_count(stories),
                # A noun-ending gag can repeat verbatim without a cadence tag.
                # Prefer a fresh, already verified angle at an otherwise exact tie.
                -repeated_exact_quip_count(stories),
                random_tiebreak(indices))
    # Greedy ordering considers the articles already chosen, so repeated
    # countries/topics/cadences spread through the issue without removing
    # independently approved articles. This is ordering, not a selection cap.
    remaining=set(range(len(pool)))
    ordered=[]
    while remaining:
        winner=max(remaining,key=lambda i:diversity_score(tuple(ordered)+(i,)))
        ordered.append(winner)
        remaining.remove(winner)
    return [pool[i] for i in ordered]


def archive_summaries():
    result=[]
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            for story in json.loads(file.read_text()).get("stories",[]):
                result.append({"title":story.get("title",""),"summary":story.get("summary",""),"country":story.get("country","")})
        except (ValueError,OSError):continue
    return result[-250:]

def lifetime_country_counts(today):
    """All published editions contribute to the long-term 196-region goal.

    Do not count discovery sources, pending drafts, or guessed countries.
    Verified cross-border historical articles count for both named locations.
    """
    from collections import Counter
    counts=Counter()
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            issue=json.loads(file.read_text(encoding="utf-8"))
            issue_date=datetime.strptime(issue.get("editionDate",""),"%Y-%m-%d").date()
            if issue.get("status")!="published" or issue_date>=today:
                continue
            for story in issue.get("stories",[]):
                for code in country_codes(story.get("country")):
                    counts[code]+=1
        except (ValueError,OSError,TypeError,KeyError):
            continue
    return counts


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
                category=str(story.get("category","")).strip()
                for country in country_codes(story.get("country","")):
                    country_counts[country]+=1
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

from editorial_dates import valid_recent_reported


def screen_local_groups(groups, budget=240):
    """Cheap bounded ranking pass; preserve all unselected/unseen candidates."""
    from local_editorial import screen_prompt, preferred_ids
    end=time.monotonic()+budget
    preferred=[]
    screened=0
    for start in range(0,len(groups),8):
        if LOCAL_BACKEND_FAILED or time.monotonic()>=end or editorial_seconds_remaining()<500:
            break
        batch=groups[start:start+8]
        try:
            result=ai(screen_prompt(batch),temperature=0.0)
            preferred.extend(preferred_ids(result,batch))
            screened+=len(batch)
        except RuntimeError:
            if LOCAL_BACKEND_FAILED:break
    positions={group_id:i for i,group_id in enumerate(preferred)}
    ranked=sorted(groups,key=lambda g:(
        # Retain highest-signal major-personal discovery evidence ahead of
        # less substantial guesses. Triage is only a tie-break/order hint.
        min(incident_priority(a)[0] for a in g["articles"])!=-1,
        g["groupId"] not in positions,positions.get(g["groupId"],len(groups)),
        min(incident_priority(a)[0] for a in g["articles"]),g["groupId"]))
    return ranked,screened,len(positions)

def draft_local_group(group, day, temperature):
    from local_editorial import staged_draft,SKIP_CODES
    bound=staged_draft(group,day,ai,temperature,
                       viable_joke=lambda story:choose_pre_review_quip(story) is not None)
    if not bound["stories"]:
        reason=bound.get("reasonCode","other")
        if reason not in SKIP_CODES:reason="other"
        key="invalid" if reason.startswith("invalid_") else "empty"
        LOCAL_DRAFT_OUTCOMES[key]+=1
        LOCAL_DRAFT_REASONS[reason]=LOCAL_DRAFT_REASONS.get(reason,0)+1
        print("Local draft outcome:",key,reason,flush=True)
        from local_editorial import COPY_KEYS
        for field in bound.get("invalidFields",[]):
            if field in COPY_KEYS:
                code="invalid_copy_field_"+field
                LOCAL_DRAFT_REASONS[code]=LOCAL_DRAFT_REASONS.get(code,0)+1
    # Save progress only after a complete model response. A timeout remains pending.
    from editorial_resume import EditorialResume
    EditorialResume.from_environment(day).record_attempt(group)
    return bound

MAX_FOCUSED_DRAFT_GROUPS=1 if LOCAL_EDITORIAL else 3

def source_bound_batch_drafts(response, groups):
    """Keep at most one unverified draft per article-evidence group.

    Provenance-only prefilter: it does not verify a fact, a country, or the
    quality of a joke. Independent reviewer B still must approve everything.
    A model must not combine unrelated original articles from separate
    groups or invent a URL to reach any arbitrary edition size.
    """
    proposed=response.get("stories",[]) if isinstance(response,dict) else []
    if not isinstance(proposed,list) or not isinstance(groups,list):
        return []
    selected=[]
    for group in groups[:MAX_FOCUSED_DRAFT_GROUPS]:
        articles=group.get("articles",[]) if isinstance(group,dict) else []
        allowed={article.get("url") for article in articles
                 if isinstance(article,dict)
                 and isinstance(article.get("url"),str)
                 and host(article["url"])}
        if not allowed:
            continue
        for story in proposed:
            if not isinstance(story,dict):
                continue
            urls=story.get("verificationUrls")
            if not isinstance(urls,list) or not (1<=len(urls)<=3):
                continue
            if (all(isinstance(url,str) for url in urls)
                    and len(set(urls))==len(urls)
                    and set(urls).issubset(allowed)
                    and story.get("sourceUrl") in allowed):
                selected.append(story)
                break
    return selected


# The November 22 A-editor request combined 24 long article groups with
# diagnostics and returned two drafts. A smaller initial evidence window
# leaves model context for actual incident writing; a larger overall queue
# preserves independent sources for post-audit recovery.
PRIMARY_EDITORIAL_GROUPS=1 if LOCAL_EDITORIAL else 6
EDITORIAL_SHORTLIST_LIMIT=64

def select_untried_source_groups(groups, attempted_ids, used_urls):
    """Select source groups never attempted by the A-editor.

    Never spend scarce independent review quota re-prompting the same evidence
    when an earlier response returned zero stories. A failed/empty request is
    still an attempt. Every recovered draft remains UNVERIFIED and goes through
    the ordinary publisher-text, human-humor and B-editor checks.
    """
    attempted_urls={
        article["url"] for group in groups
        if group["groupId"] in attempted_ids
        for article in group["articles"]
    }
    # Different group IDs may still refer to the same publisher article.
    excluded_urls=attempted_urls | set(used_urls)
    return sorted(
        (group for group in groups
         if group["groupId"] not in attempted_ids
         and not any(article["url"] in excluded_urls for article in group["articles"])),
        key=lambda group:(
            min(incident_priority(article)[0] for article in group["articles"]),
            group["groupId"],
        ),
    )

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
    if not country_codes(story.get("country")):
        return False
    if (editorial_fit_rejection(story) or human_failure_rejection(story)
            or noncomic_incident_rejection(story)
            or choose_pre_review_quip(story) is None):
        return False
    if BLOCK.search(" ".join(str(story.get(key,"")) for key in
                             ("title","summary","detail","quip"))):
        return False
    return True


# Pipeline diagnostics deliberately contain COUNTS ONLY. Never write source
# article text, individuals' names, URLs, model prompts or unverified events.
FUNNEL_COUNT_FIELDS=frozenset({
    "collected","fresh","planned_fetches","fetchable_original_bodies",
    "high_signal_original_bodies","source_fetch_attempts",
    "candidate_review_groups","paired_groups","single_original_groups",
    "first_ai_batch_groups","drafted","preflight_eligible",
    "independent_approved","selected_for_edition",
    "country_ready_articles","country_ready_count",
    "supplemental_attempts","supplemental_generated",
    "supplemental_groups_examined",
    "source_groups_attempted","untried_source_groups_remaining",
    "repeated_quip_cadences","recognized_quip_cadences",
    "local_screened","local_screen_preferred","local_candidate_errors","explicit_publisher_dates",
    "local_empty_draft_responses","local_invalid_draft_responses"
})
FUNNEL_MAP_FIELDS=frozenset({
    "publisher_regions_fetch_plan","publisher_regions_fetched",
    "publisher_regions_shortlist","rejection_reasons",
    "unready_country_codes","local_draft_reasons"
})
FUNNEL_STAGES=frozenset({
    "fresh_filter","publisher_leads_unavailable",
    "fetch_plan","body_fetch","publisher_articles_unavailable",
    "shortlist","budget_blocked","model_quota_blocked","model_unavailable",
    "draft","draft_empty","audit","country_readiness",
    "no_publishable_stories","selected"
})

def save_editorial_funnel(stage, counts, path="data/editorial-funnel.json"):
    """Persist bounded, nonpublic stage counts for operational audit only."""
    if stage not in FUNNEL_STAGES:
        raise ValueError("unrecognized editorial funnel stage")
    output={"status":"DIAGNOSTIC_ONLY_UNVERIFIED",
            "meaning":"Publisher regions are not incident locations.",
            "phase":stage}
    for key,value in counts.items():
        if key in FUNNEL_COUNT_FIELDS and type(value) is int and 0<=value<=100000:
            output[key]=value
        elif key in FUNNEL_MAP_FIELDS and isinstance(value,dict):
            if len(value)<=80 and all(
                    isinstance(k,str) and 1<=len(k)<=90
                    and type(v) is int and 0<=v<=100000
                    for k,v in value.items()):
                output[key]=dict(sorted(value.items()))
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("Editorial funnel checkpoint:",json.dumps(output,ensure_ascii=False,sort_keys=True),flush=True)
    return output

def main():
    global RUN_DEADLINE, AI_QUOTA_BLOCKED, RUN_MODEL_CATALOG, LOCAL_BACKEND_FAILED, LOCAL_CANDIDATE_ERRORS
    LOCAL_BACKEND_FAILED=False
    LOCAL_CANDIDATE_ERRORS=0
    LOCAL_DRAFT_OUTCOMES.update(empty=0,invalid=0)
    LOCAL_DRAFT_REASONS.clear()
    now=datetime.now(JST)
    day=now.date().isoformat()
    if not KEY and not LOCAL_EDITORIAL:
        print("No free-tier AI key configured. Safe skip.");return 0
    # Leave headroom before GitHub's 12-minute limit to fail closed, not get cancelled.
    RUN_DEADLINE=time.monotonic()+(1800 if LOCAL_EDITORIAL else 540)
    AI_QUOTA_BLOCKED=False
    RUN_MODEL_CATALOG=None
    RUN_UNAVAILABLE_MODELS.clear()
    leads=json.loads(Path("data/candidates.json").read_text()).get("candidates",[])
    funnel={"collected":len(leads)}
    def checkpoint(stage, **fields):
        funnel.update(fields)
        save_editorial_funnel(stage,funnel)
    from editorial_resume import EditorialResume
    resume=EditorialResume.from_environment(day) if LOCAL_EDITORIAL else EditorialResume(day)
    leads=resume.restore_pending(leads)
    previously_seen=previous_events()
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
        if trusted_original_domain(lead.get("url","")) and not BLOCK.search(lead.get("title","")) and lead["url"] not in previously_seen:recent.append(lead)
    checkpoint("fresh_filter",fresh=len(recent))
    if not recent:
        checkpoint("publisher_leads_unavailable",fresh=0)
        print("No recent approved-publisher articles; keep existing edition.")
        return 0
    # Collect actual article bodies before asking the model to draft.
    cache={}
    source_leads=[]
    # Share scarce article-fetch slots across source markets, not just hosts.
    # Publisher country is only a retrieval hint, NEVER proof of event country.
    ordered=resume.order_leads(balanced_source_retrieval(recent,limit=240),recent,limit=240)
    from collections import Counter
    retrieval_regions=Counter(country_region(lead.get("sourcecountry")) or "unattributed"
                              for lead in ordered)
    print("Article retrieval by discovery-source region (not event country):",
          json.dumps(dict(retrieval_regions),ensure_ascii=False,sort_keys=True),flush=True)
    checkpoint("fetch_plan",planned_fetches=len(ordered),
               publisher_regions_fetch_plan=dict(retrieval_regions))
    outcomes={}
    failure_reasons={}
    high_signal_source_count=0
    fetch_stop_reason=None
    for lead in ordered:
        fetch_stop_reason=source_reading_stop_reason(
            len(source_leads),high_signal_source_count,
            editorial_seconds_remaining())
        if fetch_stop_reason:
            print("Original-source fetch budget preserved for AI source audits:",
                  fetch_stop_reason,flush=True)
            break
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
        if cache[url]:
            source_leads.append({
                'title':lead['title'],'url':url,'publisher':lead.get('domain',''),
                'text':cache[url][:8500],
                # Publisher *market*, not a report of the incident's location.
                'sourcecountry':lead.get('sourcecountry',''),
                'language':lead.get('language',''),
                'focus':lead.get('focus',''),
            })
            if incident_priority(lead)[0]<=1:
                high_signal_source_count+=1
    fetched_regions=Counter(country_region(x.get("sourcecountry")) or "unattributed" for x in source_leads)
    checkpoint("body_fetch",fetchable_original_bodies=len(source_leads),
               high_signal_original_bodies=high_signal_source_count,
               source_fetch_attempts=sum(row[0] for row in outcomes.values()),
               publisher_regions_fetched=dict(fetched_regions))
    checkpoint("body_fetch",explicit_publisher_dates=sum(
        item["text"].startswith("Publisher datePublished: ") for item in source_leads))
    print('Approved-publisher article reading:',len(recent),'recent seven-day leads,',len(source_leads),'readable articles',flush=True)
    print('Article retrieval by provider (attempted, fetched):',json.dumps(outcomes,sort_keys=True),flush=True)
    print('Article retrieval diagnostic counts (no URLs or article text):',json.dumps(failure_reasons,sort_keys=True),flush=True)
    if not source_leads:
        checkpoint("publisher_articles_unavailable",fetchable_original_bodies=0)
        print('No readable approved-publisher articles; '
              'save free AI calls and keep existing edition.')
        return 0
    groups=corroboration_groups(source_leads)
    print('Cross-publisher headline groups:',len(groups),flush=True)
    # Headline overlap is only a discovery heuristic. Even when it finds
    # candidate stories, semantic matching can find additional consequential incidents
    # described with different wording by independent publishers.
    # Keep the bounded candidate budget; publication still requires the cited
    # original publisher text and a separate adversarial AI editing audit.
    print('Trying AI semantic incident matching to supplement headline groups.',flush=True)
    # Overlapping windows allow semantic matching across the full fetched set.
    # Headline groups are still included; AI proposals remain unverified.
    semantic=[]
    # One trusted publisher is sufficient, so AI corroboration is never
    # needed. Local headline pairing remains an optional discovery heuristic,
    # not a requirement to write or publish any story.
    if semantic_matching_needed(len(groups)):
        for start in range(0,len(source_leads),90):
            if editorial_seconds_remaining()<220:
                print("Skipping remaining semantic matching to reserve time for source-fidelity review.",flush=True)
                break
            window=source_leads[max(0,start-30):start+120]
            if len(window)<2:continue
            semantic.extend(semantic_corroboration_groups(window))
    else:
        print("Skipping optional semantic matching: reserving inference for source-fidelity checks.",flush=True)
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
    # Do not truncate single-original reports BEFORE the multilingual,
    # multi-region shortlist. Doing that selected only the first English
    # keyword matches and made newly registered local publishers invisible.
    groups.extend([[item] for item in unpaired])
    all_groups=groups
    groups=prioritize_comic_groups(groups,limit=EDITORIAL_SHORTLIST_LIMIT)
    if LOCAL_EDITORIAL:
        groups=resume.merge_shortlist(groups,all_groups,EDITORIAL_SHORTLIST_LIMIT)
    shortlisted_regions=Counter()
    for group in groups:
        for region in {country_region(x.get("sourcecountry")) for x in group}:
            if region: shortlisted_regions[region]+=1
    checkpoint("shortlist",candidate_review_groups=len(groups),
               paired_groups=sum(len(g)>=2 for g in groups),
               single_original_groups=sum(len(g)==1 for g in groups),
               first_ai_batch_groups=min(PRIMARY_EDITORIAL_GROUPS,len(groups)),
               publisher_regions_shortlist=dict(shortlisted_regions))
    print('Review groups:',len(groups),'including original single-publisher reports;',raw_group_count,'initial pair hypotheses',flush=True)
    if len(groups)<1:
        print('No retrieved candidate articles; safe skip.');return 0
    # Preserve each hypothesized incident's exact article-to-article association.
    # A flat article list can hide which sources are meant to corroborate one another.
    grouped_evidence=[{"groupId":i+1,"articles":[{"title":item["title"],
        "url":item["url"],"text":item["text"][:4800]} for item in group]}
        for i,group in enumerate(groups[:EDITORIAL_SHORTLIST_LIMIT])]
    # Existing discovery ranking already prioritizes major personal mistakes.
    # No extra AI ranking call before writing; conserve CPU for the actual articles.
    if LOCAL_EDITORIAL:
        checkpoint("shortlist",local_screened=0,local_screen_preferred=0,
                   local_candidate_errors=LOCAL_CANDIDATE_ERRORS)
    if LOCAL_EDITORIAL:
        grouped_evidence=resume.order_groups(grouped_evidence)
        resume.checkpoint_queue(grouped_evidence,recent)
        print("Same-day continuation: pending",len(resume.pending),"previous attempts",len(resume.attempted),flush=True)
    local_rank={g["groupId"]:i for i,g in enumerate(grouped_evidence)}
    # Preserve allowed corroboration pairs: a model must not combine unrelated sources.
    allowed_pairs=set()
    for group in groups[:EDITORIAL_SHORTLIST_LIMIT]:
        for i,first in enumerate(group):
            for second in group[i+1:]:
                if host(first["url"])!=host(second["url"]):
                    allowed_pairs.add(frozenset((first["url"],second["url"])))
    grouped_urls={item["url"] for group in groups for item in group}
    grouped_sources=[item for item in source_leads if item["url"] in grouped_urls]
    prompt=(EDITORIAL_MISSION+WRITING_CRAFT+MANZAI_CRAFT+' You are a Japanese comedy show writer working as news editor A. Discover up to 12 REAL, jaw-dropping, comic PERSONAL FAILURES from these fetched original articles. The reporter need not literally call it a mistake, but the actual flawed judgment by an individual and extraordinary consequence must be supported by the article text. FIRST seek spectacular PERSONAL misjudgments: costly but non-tragic wrong purchases or sales, major individual miscalculations, failed ambitious plans, huge self-caused reversals and dramatic sports or workplace blunders with concrete consequences. Routine typos, small orders, minor signs and trivial harmless mix-ups are lower-priority backups, NEVER the first choice when verified substantial individual failures qualify. Do not favor corporate headlines, high-profile resignations, serious disciplinary conflict, emergency harassment, criminal cases, politics, or outcomes that primarily harm victims. A huge loss is not funny by itself; require a clear source-proven decision and safe unexpected reversal. The specific human action, mistake or unexpected decision and its comic consequence must actually be in the fetched source; the reporter need not literally call it a mistake. A dispute or apology alone is not comedy. For EACH incident first identify humanActor, humanMistake (the documented misstep or ironic choice), expectedPlan and observedOutcome; only then privately draft FOUR radically different Japanese punchlines and pick the strongest short unexpected payoff, not a recap or lesson. Give a genuine, substantial individual mistake priority over minor errors and routine corporate stories; require directly documented stakes and a safe comic target, not personal humiliation. Return zero stories if no supported comedic mistake exists. '
      'Use ONLY supplied fetched article texts, never external knowledge. Draft stories supported by at least ONE retrieved publisher article; one vetted publisher is sufficient. '
      'Choose at least one article published by a vetted news company; ONE article is enough, with no requirement to prove original reporting or locate a second source. verificationUrls should contain the cited article URL; no further evidence verification is needed. Use its text to draft the summary but do not invent people, quotes, numbers or consequences. The catalog supports 196 reporting locations; never confuse a publisher market with an incident country. '
      'For each include required fields '+str(REQUIRED)+', humanActor (which actual PERSON or human-run organization made the mistake), humanMistake (specific human decision or mix-up proved by the source), expectedPlan (the original purpose or expectation, in Japanese, at least 6 characters), observedOutcome (the documented surprising actual outcome, in Japanese, at least 6 characters), quipSecond (OPTIONAL, only when a second genuinely funny 15-55-character angle exists), verificationUrls (the cited publisher URL), eventKey (normalized incident identifier). '
      'CRITICAL OUTPUT SCHEMA: category MUST be exactly one of person, work, company, sports (lowercase English), NEVER government, politics, institution, business, organization or any Japanese category value. Use company for corporate and institutional failures INCLUDING government agencies, public institutions and large organizations; use work for workplace or operational mistakes; use person for individual decision-maker mistakes; use sports for incidents primarily occurring in competitive sport, including athletes, referees, clubs and event operations. categoryLabel is the human-readable Japanese label, not category. No category balance, category quota, or five-slot target is permitted. When several verified and safe stories qualify, prioritize an astonishing INDIVIDUAL failure (including employees, artisans and athletes) before ordinary work and company stories; company is a rare exception with a documented human error, not a default. A small typo cannot displace a major personal failure. Make work about employees and operators, person about individual choices, sports about sporting decisions, and company only about exceptional organization-level failures. Avoid labeling every interesting workplace incident as company. Do not alter these enum values even when the subject is consequential or political. '
      'For each story, make the quip an affectionate, pointed observation about the verified mistake; prioritize a crisp, unexpected punchline grounded in the plan-versus-reality contrast; avoid flat paraphrases and forced comedy. quip should land immediately in 18-45 characters; quipSecond should add a NEW comic angle in 18-55 characters. Provide three distinct first-quips as quipCandidates (a JSON array, 18-55 Japanese characters per option) and put your strongest first choice in quip. The pipeline compares candidates before independent source review. Never include a mere headline recap. No explanatory second sentence and no unproven allegations as joke premises. An optional gentle reflection can add warmth, but never require a life lesson or tell the reader how to feel. Do not make empty motivational claims, imply an unreported recovery, or treat the mistake as harmless when it was not. Reject generic routine news without a 4/5 startling documented contrast; an intentionally unusual choice alone is NOT an eligible failure unless the article demonstrates what the person actually misjudged and how it went wrong. Before rejecting an otherwise well-sourced failure for no_respectful_comic_angle, explore at least two different safe comic targets (the plan versus reality, the mistaken assumption versus the outcome); if neither works, reject it. ' 
      'Do not select a merely verifiable incident when its actual human mistake lacks a clear, safe, incident-specific comic reversal. Rewrite weak jokes with a new angle; do not replace comedy with vague encouragement or a lesson. Source-proven significant PERSONAL stakes or exceptionally large plan-versus-reality contrast are a selection advantage when humane comedy is possible. Serious harm to victims is NEVER a selection advantage. NEVER mock victims, casualties, poverty, illness or vulnerable people. For individuals, humor should target a relatable miscalculation, ironic outcome or overconfidence rather than their identity, appearance, hardship or vulnerability; avoid invasive private-life details and public shaming. For institutions, target flawed plans, contradictions and decisions, not those harmed. Exclude incidents where a respectful comic angle cannot be supported. No death, injuries, abuse or humiliation in the chosen story or quip. Edition date JST: '+day+'. Stories must have an original source-supported publication date within the preceding seven days including the edition day in Japan; keep that ACTUAL date intact and never relabel old reporting as new. Prioritize same-day reporting when otherwise comparable. '
      'Use one article per story and retain its actual publication date. '
      'Return JSON with stories array AND diagnostics array containing one object for every input group: '
      '{groupId:integer,eligible:boolean,reasonCode:string}. Use ONLY these reasonCode values: '
      'same_incident_supported, unrelated_articles, syndicated_or_not_independent, no_explicit_recent_report_date, '
      'insufficient_facts, sensitive_incident, no_respectful_comic_angle, other. Do not reject an incident merely for being consequential or financially serious; reject only if there is no respectful, constructive comic angle. '
      'A group marked eligible still needs the story fields; do not add facts beyond the published report. '
      'Candidate groups with their own article bodies (NOT proof): '+json.dumps(grouped_evidence[:PRIMARY_EDITORIAL_GROUPS],ensure_ascii=False))
    attempted_group_ids={g["groupId"] for g in grouped_evidence[:PRIMARY_EDITORIAL_GROUPS]}
    if editorial_seconds_remaining()<100:
        checkpoint("budget_blocked")
        print("Editorial budget too low for safe independent review; no new publication.",flush=True)
        return 0
    try:
        draft_response=(draft_local_group(grouped_evidence[0],day,0.55)
                        if LOCAL_EDITORIAL else ai(prompt,temperature=0.65))
    except RuntimeError as exc:
        from local_editorial import LocalCandidateError
        if LOCAL_EDITORIAL and isinstance(exc,LocalCandidateError):
            # Continue with the existing focused-draft recovery loop, not the
            # failed source. No partial model response can become a draft.
            draft_response={"stories":[]}
            print("Initial candidate failed; trying a different source group.",flush=True)
        else:
            checkpoint("model_quota_blocked" if AI_QUOTA_BLOCKED else "model_unavailable")
            print("Initial editorial generation unavailable; no unverified publication.",flush=True)
            return 0
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
        for item in diagnostics[:min(PRIMARY_EDITORIAL_GROUPS,len(grouped_evidence))]:
            if not isinstance(item,dict):continue
            group_id=item.get("groupId")
            code=item.get("reasonCode")
            if type(group_id) is int and 1<=group_id<=min(PRIMARY_EDITORIAL_GROUPS,len(grouped_evidence)) and code in valid_codes:
                group_reasons[group_id]=code
    print("AI candidate group assessment:",json.dumps({
        "assessed":len(group_reasons),
        "total":min(PRIMARY_EDITORIAL_GROUPS,len(grouped_evidence)),
        "fresh_backup_groups":max(0,len(grouped_evidence)-PRIMARY_EDITORIAL_GROUPS),
        "reason_counts":{code:list(group_reasons.values()).count(code) for code in sorted(set(group_reasons.values()))}
    },sort_keys=True),flush=True)
    supplemental_attempts=0
    supplemental_generated=0
    supplemental_groups_examined=0
    if not any(draft_preflight_viable(item,now) for item in draft):
        # Only recover drafts when none are viable; audit the first viable
        # draft before spending more provider calls. The after-review refill
        # can continue finding additional stories without a publication quota.
        # Draft budget is NOT a required or maximum published article count.
        # The large first batch can return diagnostics only, with no actual
        # drafts: try additional *individual* incident reports without
        # weakening the original-text evidence or independent B audit gates.
        # Always preserve time and model quota for B. More unreviewed prose
        # alone is not progress.
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
            if (not LOCAL_EDITORIAL or group["groupId"] not in attempted_group_ids)
            and not any(article["url"] in already_drafted_urls
                       for article in group["articles"])
        ),key=lambda g:(
            local_rank[g["groupId"]] if LOCAL_EDITORIAL else 0,
            min(incident_priority(article)[0] for article in g["articles"]),
            0 if g["groupId"]>PRIMARY_EDITORIAL_GROUPS else 1,
            0 if group_reasons.get(g["groupId"])=="same_incident_supported" else 1,
            g["groupId"]))
        # Use three independent incident groups per A-editor request.
        # Prior read-only runs needed many A calls to obtain
        # a few drafts, and B eventually hit HTTP 429. Batching three
        # groups per request reserves more of the quota/time budget for B.
        # Each drafted incident must cite exactly its OWN group evidence;
        # cross-group invented corroboration is rejected downstream.
        print("Supplementing insufficient editorial drafts in pairs:",
              len(retry_candidates),flush=True)
        retry_limit=len(retry_candidates) if LOCAL_EDITORIAL else min(len(retry_candidates),20)
        for start in range(0,retry_limit,MAX_FOCUSED_DRAFT_GROUPS):
            if LOCAL_BACKEND_FAILED or AI_QUOTA_BLOCKED or editorial_seconds_remaining()<(420 if LOCAL_EDITORIAL else 150):
                print("Ending supplemental drafts: preserving time and quota for verification.",flush=True)
                break
            batch=retry_candidates[start:min(start+MAX_FOCUSED_DRAFT_GROUPS,retry_limit)]
            retry_prompt=(EDITORIAL_MISSION+WRITING_CRAFT+MANZAI_CRAFT+QUIP_ALTERNATIVE_REQUIREMENT+
                " You are editor A. Review each incident candidate SEPARATELY. "
                "FIRST seek a verifiable, significant PERSONAL miscalculation or "
                "large non-tragic outcome of a named individual's decision. "
                "Do NOT downgrade to trivial typos, routine deliveries or minor "
                "misprints merely because they are easy to joke about. "
                "Draft up to one "
                "Japanese news story PER GROUP, but ONLY when the publisher article "
                "inside THAT SAME GROUP supports a specific real-world mistake. "
                "NEVER merge facts, people, locations, or sources from different groups. "
                "Return JSON object with stories array. Do not return diagnostics. "
                "If the verifiable major mistake has no respectful, genuinely funny punchline, return no story. Do not downgrade to a vague gentle observation or fabricate a laugh. Do not invent any event or outcome. "
                "If evidence is insufficient or the incident cannot be treated respectfully, return an empty stories array. "
                "Each story must contain fields "+str(REQUIRED)+", humanActor (person/team who erred), humanMistake (documented human mistake, in Japanese), expectedPlan (verifiable expectation), observedOutcome (what demonstrably went wrong), optional quipSecond (only a genuinely different and funny second punchline), "
                "verificationUrls (the cited publisher URL from that group), "
                "eventKey (specific incident identifier at least 12 characters), "
                "Use the publisher text as writing context, not for a second fact check. "
                "category must be exactly person, work, company, or sports. "
                "reported must be a source-supported actual publication date within "
                "the last seven days including edition day (JST), formatted YYYY-MM-DD. "
                "Use warm humor about the mistake, never victims or suffering; "
                "allow an optional humane reflection without prescribing feelings, lessons or outcomes. "
                "Do not infer any fact absent from the supplied text. Sharpen the first hit through three private alternatives, and aim the second hit at a DIFFERENT verified contrast; avoid long explanations or rumors. "
                "Edition date JST: "+day+
                ". Candidate groups (hypotheses, NOT proof): "+
                json.dumps(batch,ensure_ascii=False))
            # A failed or empty A call still marks its source groups as tried.
            # Keep post-audit refill for independent, never-prompted articles.
            attempted_group_ids.update(group["groupId"] for group in batch)
            try:
                supplemental_attempts+=1
                supplemental_groups_examined+=len(batch)
                if LOCAL_EDITORIAL:
                    retry_result=draft_local_group(batch[0],day,0.55)
                else:
                    retry_result=ai(retry_prompt,temperature=0.65)
                retry_stories=source_bound_batch_drafts(retry_result,batch)
                supplemental_generated+=len(retry_stories)
                draft.extend(retry_stories)
                print("Small-batch source-bound (NOT verified) drafts:",len(retry_stories),flush=True)
            except (RuntimeError,ValueError,KeyError,TypeError) as exc:
                print("Small-batch draft failed:",type(exc).__name__,flush=True)
            if any(draft_preflight_viable(item,now) for item in draft):
                print("Viable draft available: switch immediately to independent editorial review.",flush=True)
                break
    checkpoint("draft",drafted=len(draft),local_candidate_errors=LOCAL_CANDIDATE_ERRORS,
               local_empty_draft_responses=LOCAL_DRAFT_OUTCOMES["empty"],
               local_invalid_draft_responses=LOCAL_DRAFT_OUTCOMES["invalid"],
               local_draft_reasons=dict(LOCAL_DRAFT_REASONS),
               preflight_eligible=sum(draft_preflight_viable(x,now) for x in draft),
               supplemental_attempts=supplemental_attempts,
               supplemental_generated=supplemental_generated,
               supplemental_groups_examined=supplemental_groups_examined,
               source_groups_attempted=len(attempted_group_ids),
               untried_source_groups_remaining=len(
                   select_untried_source_groups(grouped_evidence, attempted_group_ids, set())))
    if AI_QUOTA_BLOCKED:
        checkpoint("model_quota_blocked")
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
        if LOCAL_BACKEND_FAILED or (RUN_MODEL_CATALOG and all(model in RUN_UNAVAILABLE_MODELS for model in RUN_MODEL_CATALOG)):
            checkpoint("model_unavailable",drafted=0)
        else:
            checkpoint("draft_empty",drafted=0)
        print("No usable drafts from approved-publisher articles; keep previous edition.",flush=True)
        return 0
    # Rank candidates by editorial evidence alone.
    draft=prioritize_personal_drafts_for_review(draft,set(),source_leads)
    print("Review budget priority: editorial evidence only",flush=True)
    seen=previous_events()
    selected=[]
    from publish_approved import prepare_reviewed_story,release_failure_message
    # Only aggregate rejection categories, never article text or model free-form reasons.
    rejection_counts={}
    def reject(reason):
        rejection_counts[reason]=rejection_counts.get(reason,0)+1
    past=archive_summaries()
    accepted_summaries=[]
    lead_urls={x['url'] for x in source_leads}
    publisher_titles={x['url']:x['title'] for x in source_leads}

    def candidates_with_after_review_refill():
        nonlocal supplemental_attempts,supplemental_generated,supplemental_groups_examined
        # Review initial candidates FIRST. Refill from untouched sources
        # while independent audit budget and runtime still allow it.
        # actually fetched publisher articles, never by inventing a news event.
        yield from draft
        if AI_QUOTA_BLOCKED or editorial_seconds_remaining()<130 or LOCAL_BACKEND_FAILED:
            return
        used_urls={url for candidate in draft if isinstance(candidate,dict)
                   for url in (candidate.get("verificationUrls") or [])
                   if isinstance(url,str)}
        remaining=select_untried_source_groups(
            grouped_evidence, attempted_group_ids, used_urls)
        if LOCAL_EDITORIAL:
            remaining.sort(key=lambda g:local_rank[g["groupId"]])
        print("After-review never-prompted source groups:",len(remaining),
              "earlier groups attempted:",len(attempted_group_ids),flush=True)
        refill_limit=len(remaining) if LOCAL_EDITORIAL else min(len(remaining),20)
        for offset in range(0,refill_limit,MAX_FOCUSED_DRAFT_GROUPS):
            # Scarce free-tier quota belongs to factual fidelity before extra jokes.
            if AI_QUOTA_BLOCKED or editorial_seconds_remaining()<125 or LOCAL_BACKEND_FAILED:
                print("Ending after-review refill: independent audit time or AI quota limit.",flush=True)
                break
            if LOCAL_EDITORIAL and editorial_seconds_remaining()<420:
                break
            batch=remaining[offset:offset+MAX_FOCUSED_DRAFT_GROUPS]
            retry_prompt=(
                EDITORIAL_MISSION+WRITING_CRAFT+MANZAI_CRAFT+
                QUIP_ALTERNATIVE_REQUIREMENT+
                " Editor A: these independent original-article groups were NOT "
                "approved or rejected yet. Seek a BIG, independently documented "
                "individual mistake, spectacular but non-tragic reversal, or "
                "extraordinary personal misjudgment. Do not select trivial "
                "typos, everyday deliveries or generic corporate headlines "
                "merely to fill slots. A reported mistake and its "
                "documented consequence must BOTH be in that same article. "
                "Produce at most one short Japanese story PER GROUP, with "
                "the strongest fact-based punchline and no fabricated details. "
                "Keep each group separate; do not mix countries, names or "
                "sources across groups. Use original article dates and "
                "the regular required fields, humanActor, humanMistake, "
                "expectedPlan, observedOutcome, eventKey and verificationUrls "
                "from that group. Return JSON {stories:[...]}, or an empty list "
                "when evidence is missing, harmful or not funny. Edition date: "+
                day+". Candidate publisher text: "+
                json.dumps(batch,ensure_ascii=False))
            attempted_group_ids.update(group["groupId"] for group in batch)
            try:
                supplemental_attempts+=1
                supplemental_groups_examined+=len(batch)
                if LOCAL_EDITORIAL:
                    response=draft_local_group(batch[0],day,0.5)
                else:
                    response=ai(retry_prompt,temperature=0.5)
                new_drafts=source_bound_batch_drafts(response,batch)
                supplemental_generated+=len(new_drafts)
                print("After-review additional SOURCE-BOUND drafts:",len(new_drafts),flush=True)
                for candidate in new_drafts:
                    yield candidate  # re-enters every normal fact, safety and B check
            except (RuntimeError,ValueError,TypeError,KeyError) as exc:
                print("After-review refill paused safely:",type(exc).__name__,flush=True)
                if AI_QUOTA_BLOCKED:break

    for story in candidates_with_after_review_refill():
        if not isinstance(story,dict) or any(not isinstance(story.get(k),str) or not story[k].strip() for k in REQUIRED):
            reject("missing_required_fields");continue
        if not valid_recent_reported(story["reported"],now):
            reject("invalid_reporting_date");continue
        if story["category"] not in ("person","work","company","sports"):
            reject("invalid_category");continue
        normalized_country=normalize_reporting_country(story["country"])
        if not normalized_country:
            reject("unrecognized_event_country");continue
        story["country"]=normalized_country
        # Never substitute an animal sighting or odd fact for a human error.
        fit_issue=editorial_fit_rejection(story)
        if fit_issue:
            reject(fit_issue);continue
        human_issue=human_failure_rejection(story)
        if human_issue:
            reject(human_issue);continue
        # Compare proposed punchlines before the editorial joke review.
        selected_quip=choose_pre_review_quip(story,reviewed=selected)
        if selected_quip is None:
            # Never fall back to a headline paraphrase or generic punchline.
            # Source-verified reporting needs an independently witty angle too.
            reject("quip_without_original_angle");continue
        story["quip"]=selected_quip
        quip_issue=comic_line_rejection(story["quip"])
        if quip_issue:
            reject(quip_issue);continue
        # A serious harassment case is not comic relief merely because
        # the harasser made an unwise human choice.
        situational_risk=noncomic_incident_rejection(story)
        if situational_risk:
            reject(situational_risk);continue
        # The journalist/publisher is accountable for reporting the facts.
        # Our app only needs the primary story to come from a trusted outlet.
        # One cited publisher is sufficient; no original-reporting proof or
        # cross-publisher corroboration is demanded of the news article.
        urls=[story.get("sourceUrl","")]
        if not trusted_original_domain(urls[0]):
            reject("publisher_not_in_approved_news_registry");continue
        if urls[0] not in lead_urls or not cache.get(urls[0]):
            # We still need the article's words to WRITE a faithful Japanese
            # summary; this is not an independent investigation of journalism.
            reject("publisher_article_not_readable_for_summary");continue
        story["verificationUrls"]=urls
        if source_title_is_policy_explainer(publisher_titles.get(urls[0],"")):
            reject("policy_explainer_without_incident_reporting");continue
        if story["sourceUrl"] in seen or story["id"] in seen:
            reject("previously_published");continue
        if BLOCK.search(" ".join(str(story[k]) for k in ("title","summary","detail","quip"))):
            reject("sensitive_content");continue
        event=story.get("eventKey")
        if not isinstance(event,str) or len(event)<12:
            reject("invalid_event_key");continue
        if event in seen:
            reject("duplicate_event");continue
        # The publisher article is composition context, not proof to be
        # corroborated or fact-checked again by the app.
        evidence=[{"url":urls[0],"text":cache[urls[0]]}]
        situational_risk=noncomic_incident_rejection(story,evidence)
        if situational_risk:
            reject(situational_risk);continue
        headline_risk=headline_fidelity_risk(story,evidence)
        if headline_risk:
            reject("headline_"+headline_risk);continue
        if editorial_seconds_remaining()<45:
            print("Source-fidelity review stopped at editorial time budget; only reviewed articles remain.",flush=True)
            break
        try:
            # Compare AI wording against first-hand reporting; do not investigate
            # the publisher's news again or run a redundant full editorial review.
            audit=ai(
                "JAPANESE EDITORIAL AND HUMOR REVIEW (not a fact-check): "
                "The article was published by an approved news outlet. "
                "Trust the reporting company to substantiate its own facts; NEVER "
                "investigate, corroborate, or demand proof of the journalism. "
                "Our job is to write an accurate Japanese introduction and "
                "a brilliant, humane, incident-specific comic remark. Use the "
                "publisher's text only as writing context so our Japanese prose "
                "does not introduce invented people, motives, numbers, locations "
                "or conclusions that the publisher did not say. Review the "
                "headline's clarity and translation, including legal-status words. "
                "Respect victims and private individuals. "
                "Reject if the writing shames a person, mocks a victim, "
                "or compares reader pain with other people. "
                "Reject harassment of firefighters or emergency responders "
                "as comedy, and reject cruelty, a boring headline recap, "
                "generic platitudes or an unclear mistake/outcome contrast. "
                "Reject location claims inferred from the feed's language "
                "or the publisher's market rather than the article's incident. "
                "The first joke must be accurate, understandable on first read, "
                "and end with a fresh incident-specific punchline. "
                "Set majorPersonalFailureConfirmed true ONLY for a "
                "documented major individual error with extraordinary, "
                "non-tragic results, as described by the reporting company. "
                "The human decision and reversal must be in that article. "
                "Do not create extra reporting claims or guess intent. "
                "Check the second joke only for a genuinely different, safe "
                "angle and readable punchline, not for independent evidence. "
                "Score FOUR app-owned editorial dimensions 1-5: surprise, "
                "mistakeClarity, outcomeIrony and humane safety. Safety must "
                "be 5; the other three must be at least 4. No evidence score. "
                "copyAccurate means our Japanese headline, summary and detail accurately "
                "represent the reporting, including any legal status when applicable; "
                "no independent proof is required. comicPunchlineWorks means the first "
                "joke is readable, fresh and sharp without adding reporting claims. "
                "Use the scores for theme and safety; do not repeat them as boolean checks. "
                "Return JSON {copyAccurate:boolean,comicPunchlineWorks:boolean,"
                "majorPersonalFailureConfirmed:boolean,"
                "editorialScores:{surprise:number,mistakeClarity:number,"
                "outcomeIrony:number,safety:number}}. "
                "Only if a second joke is present, also return secondQuipFactsVerified, "
                "secondQuipHasNewAngle and secondQuipPunchlineWorks (booleans); "
                "a missing or weak second joke never blocks the first. "
                "Draft: "+json.dumps(story,ensure_ascii=False)+
                " Already chosen: "+json.dumps(accepted_summaries,ensure_ascii=False)+
                " Publisher's article as WRITING context: "+json.dumps(evidence,ensure_ascii=False),
                temperature=0.1)
        except RuntimeError as exc:
            print("Editorial copy review paused safely:",type(exc).__name__,flush=True)
            # Previously audited stories remain eligible, but never accept the interrupted draft.
            from local_editorial import LocalCandidateError
            if LOCAL_EDITORIAL and isinstance(exc,LocalCandidateError):
                reject("local_candidate_review_failed")
                continue
            break
        if not independent_editorial_quality_passed(audit):
            for code in editorial_review_reasons(audit):
                reject(code)
            continue
        score_issue=editorial_rubric_rejection(audit)
        if not verified_rubric_for_edition(audit,day):
            reject(score_issue or "mandatory_four_factor_editorial_review_missing");continue
        # No original-report/independent-evidence audit: editorial review
        # judges only the app's Japanese writing and safe comic interpretation.
        story.pop("sourceBasis",None)
        story.pop("originalReportingVerified",None)
        story.pop("attributionNote",None)
        story["editorVerified"]=True
        story["humorSafe"]=True
        # Human error and comic impact are reviewed as presentation choices.
        story["humanFailureVerified"]=True
        story["majorPersonalFailureVerified"]=(audit.get("majorPersonalFailureConfirmed") is True)
        story["surpriseVerified"]=editorial_rubric(audit)["surprise"]>=4
        story["stageTsukkomiVerified"]=audit.get("comicPunchlineWorks") is True
        # Private proof; public JSON never exposes model review fields.
        story["editorQualityVerified"]=True
        verified_scores=editorial_rubric(audit)
        if verified_scores is not None:
            story["editorialScores"]=verified_scores
        # The editorial safety review also vets any optional second joke. A good
        # first joke and verified news article must survive a rejected extra.
        second=independently_approved_secondary_quip(story,audit)
        if second is None or BLOCK.search(second):
            story.pop("quipSecond",None)
            story.pop("secondQuipVerified",None)
        else:
            story["quipSecond"]=second
            story["secondQuipVerified"]=True
        # Draft alternatives are not published or retained in approved data.
        story.pop("quipCandidates",None)
        # Isolate malformed or unsafe release inputs before issue assembly.
        try:
            story=prepare_reviewed_story(story,day)
        except (ValueError,TypeError,KeyError) as exc:
            reject("release_story_validation_failed")
            print("Article release validation rejected:",release_failure_message(exc),flush=True)
            continue
        seen.update((story["sourceUrl"],story["id"],event))
        selected.append(story)
        accepted_summaries.append({"title":story["title"],"summary":story["summary"],"country":story["country"]})
        # No publication-count limit: the time and AI quota guards above
        # bound how many separate stories can be safely reviewed in one run.
    checkpoint("audit",independent_approved=len(selected),local_candidate_errors=LOCAL_CANDIDATE_ERRORS,
               local_empty_draft_responses=LOCAL_DRAFT_OUTCOMES["empty"],
               local_invalid_draft_responses=LOCAL_DRAFT_OUTCOMES["invalid"],
               local_draft_reasons=dict(LOCAL_DRAFT_REASONS),
               supplemental_attempts=supplemental_attempts,
               supplemental_generated=supplemental_generated,
               supplemental_groups_examined=supplemental_groups_examined,
               source_groups_attempted=len(attempted_group_ids),
               untried_source_groups_remaining=len(
                   select_untried_source_groups(grouped_evidence, attempted_group_ids, set())),
               rejection_reasons=rejection_counts)
    print("Editorial decision counts:",json.dumps({"drafted":len(draft),"approved":len(selected),"rejected":rejection_counts},sort_keys=True),flush=True)
    # Country enrichment needs are diagnostic, not an article selection gate.
    from country_readiness import article_country_backlog
    reviewed_count=len(selected)
    unready,prepared=article_country_backlog(selected,Path.cwd(),day)
    country_ready_articles=sum(set(country_codes(s.get("country","")))<=prepared
                               for s in selected)
    checkpoint("country_readiness",independent_approved=reviewed_count,
               country_ready_articles=country_ready_articles,
               country_ready_count=len(prepared),
               unready_country_codes=unready,
               rejection_reasons=rejection_counts)
    print("Article-driven country enrichment queue:",json.dumps({
        "reviewed":reviewed_count,"countries_needing_curated_assets":unready},
        sort_keys=True),flush=True)
    if not selected:
        failure_phase=("model_quota_blocked" if AI_QUOTA_BLOCKED else
                       "model_unavailable" if LOCAL_BACKEND_FAILED or (RUN_MODEL_CATALOG and all(
                           model in RUN_UNAVAILABLE_MODELS for model in RUN_MODEL_CATALOG)) else
                       "no_publishable_stories")
        checkpoint(failure_phase,independent_approved=reviewed_count,
                   country_ready_articles=0,country_ready_count=len(prepared),
                   unready_country_codes=unready,rejection_reasons=rejection_counts)
        print("No publisher-sourced, independently approved stories; no publication.");return 0
    # Publish all approved stories without filling a target count.
    # The rejection reasons distinguish real scarcity
    # from blocked retrieval, model quota, timing and overly narrow editorial drafting.
    # Personal scale and diversity apply only after editorial safety review.
    country_history,category_history=recent_diversity_counts(now.date())
    topic_history=recent_topic_counts(now.date())
    lifetime_history=lifetime_country_counts(now.date())
    cooldown=recent_country_cooldown_counts(now.date())
    selected=select_diverse_verified_stories(selected,
        country_history,category_history,topic_history,lifetime_history,
        recent_country_cooldown=cooldown,selection_seed=now.date().isoformat())
    from quip_variety import quip_variety_metrics
    cadence_metrics=quip_variety_metrics(selected)
    checkpoint("selected",selected_for_edition=len(selected),**cadence_metrics)
    print("Quip cadence diagnostic (aggregate only):",
          json.dumps(cadence_metrics,sort_keys=True),flush=True)
    print("Nightly verified selection:",len(selected),
          "vetted-publisher stories; no minimum or maximum edition count.",flush=True)
    print("30-day editorial diversity:",json.dumps({
        "historical_countries":len(country_history),
        "selected_countries":len({code for story in selected
                                  for code in country_codes(story["country"])}),
        "selected_regions":len({country_region(code) for story in selected
                                for code in country_codes(story["country"])
                                if country_region(code)}),
        "lifetime_countries_seen":len(lifetime_history),
        "reporting_countries_target":len(catalog()),
        "selected_categories":len({story["category"] for story in selected}),
        "selected_comic_themes":len({surprise_topic(story) for story in selected}),
        "recent_category_counts":dict(category_history),
        "immediate_country_cooldown":dict(cooldown),
        "history_articles":sum(country_history.values())
    },sort_keys=True),flush=True)
    # The reader now displays a sourced quote by JST date (index.html);
    # generating an unused AI nightly joke would consume TWO extra model calls.
    # Leave publication fallback to validate_approved, not fresh AI prose.
    payload={"status":"approved","editionDate":day,"editionType":"regular",
             "title":day+"｜世界の大失敗ニュース","editorApproved":True,
             "humorReviewed":True,
             "approvedBy":"automated-two-stage-review","stories":selected}
    # The reader draws original, bundled SVG illustrations for every story.
    # Never write paid-image WebP plans or imagePath into the approval artifact.
    # The publisher's identity and editorial-humor rules are the release gate.
    from publish_approved import validate_approved
    from release_contract import require_release_assets
    try:
        validate_approved(payload,day)
        require_release_assets(Path.cwd())
    except (ValueError,TypeError,KeyError) as exc:
        print("No publisher-valid AI edition:",release_failure_message(exc),flush=True)
        checkpoint("no_publishable_stories",selected_for_edition=0,
                   rejection_reasons={**rejection_counts,"release_issue_validation_failed":1})
        return 0
    target=Path("data/approved")/(day+".json")
    if target.exists():return 0
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print("Created AI issue with",len(selected),"publisher-sourced stories",day)
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("Fail-closed AI review:",type(e).__name__,str(e),file=sys.stderr)
        sys.exit(1)
