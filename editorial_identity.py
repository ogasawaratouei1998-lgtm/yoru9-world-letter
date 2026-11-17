"""Editorial identity for Yoru9: human errors with a genuinely comic reversal.

Animal sightings and general oddities are not stories about human mistakes.
These cheap checks are discovery/editing vetoes, not fact verification: the
independent reviewer still verifies each human mistake against source text.
"""
import re

HUMAN_FAILURE_MISSION=(
    "THIS IS A COMEDY COLUMN ABOUT HUMANS MAKING MISTAKES. It is NOT an animal "
    "oddities, cute creature, weird wildlife, heartwarming rescue, nature, or "
    "general surprising-news column. Every selected story MUST demonstrate a "
    "specific HUMAN actor (person, worker, team, official or organization) "
    "making a mistaken decision, error, wrong assumption, miscommunication, "
    "bungled plan, or avoidable mix-up with a concrete ironic result. "
    "A rare animal, escaped monkey, strange deer, crab migration, sea lion "
    "nursery, animal rescue, or unusual sighting is NEVER itself a human mistake. "
    "An incident involving an animal is eligible ONLY when the documented "
    "human's actual mistake (for example mistaking an inflatable toy for an "
    "alligator, or leaving a gate unlocked) is the central story and the "
    "headline and punchline focus on THAT HUMAN ERROR, not the animal. "
    "For EACH proposed story, include humanActor (who acted or misjudged) "
    "and humanMistake (what the human actually got wrong, in clear Japanese). "
    "Do not invent a human mistake to force an amusing animal sighting into "
    "the column. Ordinary, harmless personal, workplace or public-relations "
    "blunders are welcome even with no big consequences. "
)

ANIMAL_TOPIC=re.compile(
    r"サル|猿|シカ|鹿|アシカ|トド|カニ|蟹|ワニ|鰐|ヘビ|蛇|"
    r"ペンギン|アライグマ|ネコ|猫|イヌ|犬|ユニコーン|"
    r"monkey|sea.?lion|deer|crab|alligator|crocodile|"
    r"snake|penguin|unicorn|raccoon|otter|lion cub",
    re.I
)
HUMAN_ERROR_SIGNAL=re.compile(
    r"間違|ミス|誤|勘違|思い込|思い違|取り違|見間違|失敗|"
    r"手違|見落と|うっかり|判断|過信|勘を頼|混同|取り落と|"
    r"送信し.?ま|忘れ|失念|しくじ|やりすぎ|やり過ぎ|"
    r"wrong|mistak|error|misidentif|mistook|mix.?up|blunder",
    re.I
)
ANIMAL_MISTAKE_HEADLINE=re.compile(
    r"間違|ミス|誤|勘違|見間違|取り違|思い込|"
    r"鍵を.?忘れ|閉め忘れ|逃がし|誤発注|誤送信|"
    r"ワニだと|ヘビだと|サルだと|(?:だ|と)と思ったら",
    re.I
)
ANIMAL_ONLY_ACTOR=re.compile(
    r"^(?:サル|猿|シカ|鹿|カニ|蟹|ワニ|鰐|ヘビ|蛇|"
    r"アシカ|イヌ|犬|ネコ|猫|野生動物|動物|自然|"
    r"monkey|deer|crab|alligator|animal|wildlife)$",
    re.I
)


def human_failure_rejection(story):
    """Require the source-checkable identity of a person's actual mistake."""
    if not isinstance(story,dict):
        return "invalid_human_failure_story"
    actor=story.get("humanActor")
    error=story.get("humanMistake")
    if (not isinstance(actor,str) or not 2<=len(actor.strip())<=90
            or ANIMAL_ONLY_ACTOR.fullmatch(actor.strip())):
        return "missing_human_mistake_actor"
    if (not isinstance(error,str) or not 10<=len(error.strip())<=220
            or not HUMAN_ERROR_SIGNAL.search(error)):
        return "missing_concrete_human_error"
    title=story.get("title","")
    if not isinstance(title,str):
        return "missing_human_error_headline"
    if ANIMAL_TOPIC.search(title) and not ANIMAL_MISTAKE_HEADLINE.search(title):
        return "animal_novelty_not_human_failure"
    return None


def comic_line_rejection(quip):
    """Only catch obvious non-jokes; comic timing is decided by a real editor."""
    if not isinstance(quip,str) or not 12<=len(quip.strip())<=100:
        return "no_usable_first_punchline"
    if re.search(r"^(?:世界|人生|世の中).*(?:予想外|自由|奥深い|不思議)(?:です|だ)?[。！]?$",
                 quip.strip()):
        return "generic_slogan_not_punchline"
    if re.search(r"^(?:まさか|驚き|予想外)(?:の展開|でした|です)[。！]?$",
                 quip.strip()):
        return "surprise_recapped_without_joke"
    return None
