"""Low-cost cadence diagnostics for AI news quips.

This is a *stylistic* tie-breaker, NEVER a factual approval or publication
veto. It compares repetitive sentence endings only after source and safety
checks; it must not rewrite news, add jokes or consume AI API calls.
"""
from collections import Counter
import re


_PUNCTUATION=re.compile(r"[\s。！!？?…」』\u3000]+$")

# Specific repeated punchline cadences, not a ban on Kansai Japanese.
# Plain standard Japanese, noun-ending gags, etc. are left as "other":
# automatically judging all spoken Japanese endings is too error-prone.
_ENDINGS=(
    ("janaika", re.compile(r"(?:やないか|じゃないか|やんけ)$")),
    ("kai", re.compile(r"(?:かい|かいな)$")),
    ("nandeyanen", re.compile(r"(?:なんでやねん|何でやねん)$")),
    ("suna", re.compile(r"(?:すな|するな|やめろ)$")),
    ("dousunnen", re.compile(r"(?:どうすんねん|どうするんだ)$")),
)


def quip_cadence(quip):
    """Find only recognizable overused last-beat patterns."""
    if not isinstance(quip,str):
        return None
    trimmed=_PUNCTUATION.sub("",quip.strip())
    if not trimmed:
        return None
    for code,pattern in _ENDINGS:
        if pattern.search(trimmed):
            return code
    return None


def repeated_cadence_count(stories):
    """How many quips reuse one already-seen recognizable punchline ending."""
    count=Counter(quip_cadence(row.get("quip")) for row in stories
                  if isinstance(row,dict))
    count.pop(None,None)
    return sum(max(0,n-1) for n in count.values())



def repeated_exact_quip_count(stories):
    """Count verbatim punchline repetitions after ignoring whitespace.

    This is only an issue-level selection tiebreaker; it cannot approve or
    rewrite a joke, add invented facts, or disqualify a published article.
    """
    text=[re.sub(r"\s+","",row.get("quip","")) for row in stories
          if isinstance(row,dict) and isinstance(row.get("quip"),str)]
    counts=Counter(line for line in text if line)
    return sum(max(0,n-1) for n in counts.values())

def quip_variety_metrics(stories):
    """Aggregate anonymous counters only; never log article text or names."""
    count=Counter(quip_cadence(row.get("quip")) for row in stories
                  if isinstance(row,dict))
    count.pop(None,None)
    return {
        "repeated_quip_cadences":sum(max(0,n-1) for n in count.values()),
        "recognized_quip_cadences":sum(count.values()),
    }
