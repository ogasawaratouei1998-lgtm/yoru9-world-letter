"""Publication-time guard for incident-specific, optional nightly comedy.

A passing string check is never a fact check or a comedy-editor approval.
AI drafts need an independent reviewer as well. If the line is weak or
unavailable, the reader gets a normal closing without manufactured humor.
"""
from difflib import SequenceMatcher

# These are generic cross-issue frames, not the verified incidents themselves.
# The first published example ("世界の求人票...") sounded like improvised filler.
HOLLOW_FRAMES = (
    "仕事内容：", "仕事内容:", "世界の求人票", "担当欄", "現実はアドリブ",
    "世界のマニュアル", "今日の試合、台本", "世界の「まさか」",
    "予定表に書き忘れた", "世界の仕組み", "まさかの対応あり",
    "備考欄が足りない",
)

def incident_specific_nightly_line(line, stories):
    """Require a concrete phrase from ONE factual headline/summary.

    This is a structural safety net, not natural-language truth detection.
    Referencing an article's concrete object is necessary, not sufficient;
    independent human-like editorial review must still approve the joke.
    """
    if not isinstance(line, str) or not (20 <= len(line.strip()) <= 110):
        return False
    text=line.strip()
    if any(x in text for x in HOLLOW_FRAMES):
        return False
    if any(x in text for x in ("<", ">", "\\", "\n", "\r", "://")):
        return False
    if text.count("。") > 2 or text.count("、") > 3:
        return False
    if not isinstance(stories, list) or not stories:
        return False
    for story in stories:
        if not isinstance(story, dict):
            continue
        original=" ".join(str(story.get(k) or "") for k in ("title","summary"))
        # The source phrase must be at least four consecutive characters.
        # Thus three-letter generic labels and a stray "備考欄" cannot
        # certify the unsupported world-wide "求人票" metaphor.
        match=SequenceMatcher(None,text,original,autojunk=False).find_longest_match()
        concrete=text[match.a:match.a + match.size]
        if len(concrete) >= 4 and not any(
            phrase in concrete for phrase in ("世界の", "今日の", "今夜の", "予定外", "まさか")
        ):
            return True
    return False
