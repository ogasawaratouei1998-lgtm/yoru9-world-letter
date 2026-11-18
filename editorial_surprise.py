"""Source-backed extraordinary-news gate. Editing veto; never substitutes fact checking.

This gate rejects mundane newsroom summaries and soft commentary. A numerical
rating is an editorial hint only; independent source verification is mandatory.
"""
from __future__ import annotations
import re

SURPRISE_TYPES = frozenset({
    "impossible-looking-blunder",
    "institutional-role-reversal",
    "extreme-devotion-reversal",
    "absurd-bet",
    "unexpected-record",
    "outcome-flips-intent",
})
SOFT_COMMENT_ENDINGS = re.compile(
    r"(?:とは[。！!]?|(?:よう|そう)です[。！!]?|"
    r"(?:驚き|意外|すごい|びっくり)(?:ですね|だ)[。！!]?|"
    r"気がします[。！!]?|かもしれません[。！!]?|"
    r"ことになりました[。！!]?|という話[。！!]?)$"
)
# Full-stop summaries do not earn the right to become the joke.
NATURAL_STAGE_BEAT = re.compile(
    r"(?:やろ|やないか|やねん|やがな|すな|せえ|しろや|"
    r"かい|どうすんねん|なんでやねん|やで|とる|してんねん|"
    r"するな|あかん|なのか|んかい|ろや)[！!?！？]*$"
)


def stage_quip_rejection(quip):
    """Rule out flat commentary; a human stage editor still judges quality."""
    if not isinstance(quip, str) or not 17 <= len(quip.strip()) <= 75:
        return "quip_not_stage_length"
    line=quip.strip()
    if SOFT_COMMENT_ENDINGS.search(line):
        return "quip_ends_as_soft_comment"
    if not NATURAL_STAGE_BEAT.search(line):
        return "quip_lacks_spoken_final_beat"
    if re.search(r"(?:ように思う|と感じる|印象的です|考えさせられる|"
                 r"守備範囲が広い|情報量が多い)",line):
        return "quip_is_commentary"
    return None


def extraordinary_rejection(story):
    """Hard-review metadata is private. Evidence check remains separate."""
    if not isinstance(story,dict):
        return "malformed_story"
    if story.get("surpriseVerified") is not True:
        return "extraordinary_gap_not_reviewed"
    if story.get("stageTsukkomiVerified") is not True:
        return "stage_comedy_not_reviewed"
    score=story.get("surpriseScore")
    if type(score) is not int or not 4 <= score <= 5:
        return "surprise_not_four_out_of_five"
    if story.get("surpriseType") not in SURPRISE_TYPES:
        return "no_supported_surprise_mechanism"
    a=story.get("surpriseSetup")
    b=story.get("surprisePayoff")
    if (not isinstance(a,str) or not isinstance(b,str)
            or not 12<=len(a.strip())<=180 or not 12<=len(b.strip())<=180
            or a.strip()==b.strip()):
        return "no_concrete_setup_payoff"
    for name in ("quip","quipSecond"):
        if name in story:
            issue=stage_quip_rejection(story[name])
            if issue:
                return f"{name}_{issue}"
    return None


def edition_mixture_rejection(stories):
    """Three stories must not be a feed of corporate routine reports."""
    if not isinstance(stories,list) or len(stories)!=3:
        return "exactly_three_approved_stories_required"
    if len({s.get("category") for s in stories})<3:
        return "three_different_desks_required"
    if sum(s.get("category")=="company" for s in stories)>1:
        return "corporate_monoculture"
    if len({s.get("country") for s in stories})<2:
        return "geographic_monoculture"
    return None
