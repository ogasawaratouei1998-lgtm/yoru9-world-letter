"""Editorial risk guards independent of the creative and source-reviewing AI.

The guards are intentionally conservative. They never establish that a
headline is true; they can only stop a misleading draft or demand explicit
fact-checker approval. All factual/translation checks must still be done
against fetched publisher source text by the independent AI reviewer.
"""
import re

REVIEW_FIELDS=(
    "headlineGrounded",
    "translationAccurate",
    "legalStatusAccurate",
    "humorRespectful",
    "jokeClear",
    "humanFailureConfirmed",
    "comicPunchlineWorks",
    "firstQuipIncidentSpecific",
    "firstQuipNotRecap",
    "firstQuipAngleEarned",
    "firstQuipNaturalSpeech",
    "firstQuipFinalBeat",
)


def independent_editorial_quality_passed(review):
    """Unreported/unknown verdicts fail closed; not a prose-only approval."""
    return (isinstance(review,dict) and review.get("approved") is True
            and all(review.get(key) is True for key in REVIEW_FIELDS))


def headline_fidelity_risk(story, fetched_articles):
    """Detect severe known translation, legal-status and factual-metaphor risks.

    A negative result is not certification. Fact-checker B must explicitly
    validate headline claims, proper terms and comedy independently.
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

    Editor B checks factual grounding, distinct premise, and an actual payoff
    in the SAME existing fact-check call. These flags are independent of the
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
