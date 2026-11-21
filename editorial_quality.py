"""Compact source-fidelity and editorial safety guards.

Publisher reporting is the factual source. A second AI is used only to detect
errors introduced while rewriting/ translating the original article in Japanese,
not to re-investigate established journalism or rerun a full editorial panel.
The code's known-risk rules are vetoes; absence of a match never proves truth.
"""
import re

# Core errors worth blocking publication. Do not require a dozen overlapping
# model opinions about the same punchline; editor A already writes it.
REVIEW_FIELDS=(
    "headlineGrounded",
    "translationAccurate",
    "legalStatusAccurate",
    "humorRespectful",
    "jokeClear",
    "humanFailureConfirmed",
    "comicPunchlineWorks",
    "shockFactorConfirmed",
    "stageTsukkomiConfirmed",
)


def independent_editorial_quality_passed(review):
    """Require explicit source fidelity, human error, safe joke and real surprise."""
    return (isinstance(review,dict) and review.get("approved") is True
            and all(review.get(key) is True for key in REVIEW_FIELDS))


def headline_fidelity_risk(story, fetched_articles):
    """Detect severe known translation, legal-status and factual-metaphor risks.

    A negative result is not certification. The concise model comparison must
    verify that the Japanese headline and translation match the source body.
    """
    if not isinstance(story,dict):
        return "malformed_draft"
    title=story.get("title","")
    if not isinstance(title,str) or not title.strip():
        return "missing_headline"
    if not isinstance(fetched_articles,list) or not fetched_articles:
        return "missing_source_text"
    source=" ".join(str(x.get("text","")) for x in fetched_articles
                    if isinstance(x,dict)).lower()
    if not source.strip():
        return "missing_source_text"
    # English "plant nursery" means a nursery growing plants, not a
    # botanical garden or human maternity hospital.
    if ("植物園" in title and
            re.search(r"\bplant\s+nurser(?:y|ies)\b",source) and
            not re.search(r"\bbotanic(?:al)?\s+gardens?\b",source)):
        return "plant_nursery_mistranslated"
    # "To be charged" is a future prosecution step, not an arrest,
    # completed conviction or proof of a criminal conspiracy.
    planned_charge=bool(re.search(
        r"\b(?:to\s+be\s+charged|will\s+be\s+charged|expected\s+to\s+be\s+charged)\b",
        source))
    if planned_charge and not re.search(r"\b(?:arrested|detained|convicted)\b",source):
        if re.search(r"逮捕(?:された|済み)?|摘発(?:された|済み)?|有罪(?:判決)?|起訴された",title):
            return "future_charge_stated_as_completed_action"
    if re.search(r"無料の(?:産院|保育園|託児所|ホテル|宿泊所)",title):
        return "imaginary_facility_presented_as_fact"
    if re.search(r"(?:巧妙|周到)な(?:妨害|犯行|犯罪|計画)",title):
        return "unproven_criminal_intent_in_headline"
    return None


def independently_approved_secondary_quip(story, review):
    """Return only a separately vetted second angle; never reject the first joke.

    The lightweight fidelity gate checks facts, a distinct premise and payoff
    in the SAME existing comparison call. These flags are independent of the
    first joke's verdict: a poor second joke must simply disappear.
    """
    from difflib import SequenceMatcher
    from editorial_identity import comic_line_rejection
    if not isinstance(story,dict) or not isinstance(review,dict):
        return None
    first=story.get("quip")
    second=story.get("quipSecond")
    if not isinstance(first,str) or not isinstance(second,str):
        return None
    second=second.strip()
    if (not 15<=len(second)<=55 or first.strip()==second or
            any(ord(c) in (10,13,60,62,92) for c in second) or
            comic_line_rejection(second) is not None):
        return None
    if SequenceMatcher(None,first.strip(),second).ratio()>=0.82:
        return None
    if not all(review.get(field) is True for field in
               ("secondQuipFactsVerified","secondQuipHasNewAngle",
                "secondQuipPunchlineWorks")):
        return None
    return second

# Editorial scores are a secondary ranking and review aid, never evidence that
# a story happened. A reviewer still needs the factual boolean vetoes above.
RUBRIC_FIELDS=("surprise","mistakeClarity","outcomeIrony","evidence","safety")


def editorial_rubric(story_or_review):
    """Five explicit 1-5 dimensions; absent model metadata stays unscored.

    Safety and evidence are non-compensatory: an amusing outcome cannot offset
    weak journalism or an unsafe target.
    """
    data=story_or_review.get("editorialScores") if isinstance(story_or_review,dict) else None
    if not isinstance(data,dict) or set(data)!=set(RUBRIC_FIELDS):
        return None
    if any(type(data[k]) is not int or not 1<=data[k]<=5 for k in RUBRIC_FIELDS):
        return None
    return {key:data[key] for key in RUBRIC_FIELDS}


def editorial_rubric_rejection(review):
    """Only score an actually supplied rubric; legacy verified fixtures remain valid."""
    if not isinstance(review,dict) or "editorialScores" not in review:
        return None
    scores=editorial_rubric(review)
    if scores is None:
        return "editorial_scores_invalid"
    if scores["evidence"]<5 or scores["safety"]<5:
        return "evidence_or_safety_below_standard"
    if min(scores[key] for key in ("surprise","mistakeClarity","outcomeIrony"))<4:
        return "story_not_extraordinary_or_specific"
    return None


# Japanese noun and numeric fragments are small deterministic hints, not facts.
# Rank tangible, incident-specific punchlines above free-floating generic
# reactions when draft context supplies several identifiable objects. The
# independent source reviewer remains the ONLY factual/safety decision-maker.
_QUIP_ANCHOR_TOKEN=re.compile(r"[一-龯]{2,}|[ァ-ヴー]{3,}|[A-Za-z]{3,}|\d{2,}")
_QUIP_GENERIC_TOKENS=frozenset((
    "結果","予想","予定","計画","現実","事件","今回","世界","人生","人間",
    "状態","事態","状況","対応","仕事","判断","説明","内容","理由",
    "自分","本人","失敗","間違","可能","最初","最後","以上",
))


def _quip_event_anchor_bonus(line,story):
    """Small, bounded preference for objects actually named in draft evidence.

    Matching an AI-provided source summary does NOT verify a fact; every
    selected line is checked against the original publisher text afterwards.
    Older/partial drafts with no concrete anchors retain the same ranking.
    """
    narrative=" ".join(
        story.get(field,"") for field in
        ("humanMistake","expectedPlan","observedOutcome","summary")
        if isinstance(story.get(field),str))
    terms={term for term in _QUIP_ANCHOR_TOKEN.findall(narrative)
           if term not in _QUIP_GENERIC_TOKENS}
    if len(terms)<2:
        return 0
    hits=sum(term in line for term in terms)
    return min(2,hits)*9-(10 if hits==0 else 0)


def _quip_cadence_normalized(line):
    """Normalize cosmetic punctuation only when comparing candidate repeats."""
    return re.sub(r"[\s。、！!？?「」『』…]+","",line)


def quip_candidates_ranked(story):
    """Compare proposed first-line punchlines before independent fact review.

    Deterministic form checks remove headline recaps and overused cadences.
    A bounded source-anchor bonus favors actual incident objects over generic
    reactions; near-duplicate first-quips collapse after ranking.
    These scores cannot determine whether a quip is *true* or respectful.
    The selected line must pass the subsequent source-fidelity AI reviewer.
    """
    from difflib import SequenceMatcher
    from editorial_identity import comic_line_rejection
    from quip_variety import quip_cadence
    if not isinstance(story,dict):
        return []
    original=story.get("quip")
    proposed=story.get("quipCandidates")
    options=[original]+(proposed if isinstance(proposed,list) else [])
    headline=str(story.get("title","")).strip()
    summary=str(story.get("summary","")).strip()
    distinct=[]
    for index,candidate in enumerate(options[:7]):
        if not isinstance(candidate,str) or candidate.strip() in {x[2] for x in distinct}:
            continue
        line=candidate.strip()
        if (not 17<=len(line)<=75 or comic_line_rejection(line) is not None):
            continue
        title_similarity=SequenceMatcher(None,line,headline).ratio()
        summary_similarity=SequenceMatcher(None,line,summary).ratio()
        if title_similarity>=0.82 or summary_similarity>=0.85:
            continue
        score=(max(0,100-round(72*title_similarity+28*summary_similarity))
               - (10 if quip_cadence(line) else 0)
               - (12 if line.endswith(("という話。","という話","ですね。","ですね")) else 0)
               + _quip_event_anchor_bonus(line,story)
               + (3 if index==0 else 0))
        distinct.append((score,index,line))
    distinct.sort(key=lambda pair:(-pair[0],pair[1]))
    # Several LLM alternatives can be the same joke with a different comma
    # or sentence ending; keep the strongest scored version, not every echo.
    selected=[]
    for _,_,line in distinct:
        cleaned=_quip_cadence_normalized(line)
        if any(SequenceMatcher(None,cleaned,
                               _quip_cadence_normalized(chosen)).ratio()>=0.86
               for chosen in selected):
            continue
        selected.append(line)
    return selected


def choose_pre_review_quip(story, reviewed=()):
    """Select a fresh existing candidate; all jokes still require source audit."""
    from quip_variety import prefer_fresh_quip
    candidates=quip_candidates_ranked(story)
    return prefer_fresh_quip(candidates,reviewed)



def verified_rubric_for_edition(review, edition_date):
    """For fresh AI issues require a complete human-impact-aware 5-factor audit.

    Historical hand-reviewed issues keep their original contract and records.
    A missing dimension must NOT silently bypass the modern quality threshold.
    """
    if not isinstance(review,dict):
        return False
    if str(edition_date)>="2026-11-21":
        return (editorial_rubric(review) is not None
                and editorial_rubric_rejection(review) is None)
    return editorial_rubric_rejection(review) is None
