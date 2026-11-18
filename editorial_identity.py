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
    "Do not turn intentional intimidation, disruptive political protest, "
    "university disciplinary confrontations or public-safety disputes into "
    "jokes. Someone being disciplined for alleged misconduct is NOT the "
    "same as a documented accidental human blunder with an ironic payoff. "
)

ANIMAL_TOPIC=re.compile(
    r"サル|ザル|猿|シカ|鹿|アシカ|トド|カニ|蟹|ワニ|鰐|ヘビ|蛇|"
    r"ペンギン|アライグマ|ネコ|猫|イヌ|犬|競走馬|ユニコーン|"
    r"monkey|sea.?lion|deer|crab|alligator|crocodile|"
    r"snake|penguin|unicorn|raccoon|otter|lion cub|racehorse|horse",
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


# Serious intimidation of emergency responders is not a lighthearted
# human mistake. Do not turn a real public-safety dispute into a comedy beat.
# This narrowly targets harassment/abuse, not innocent mistaken callouts
# (such as reporting an inflatable toy as a real alligator).
EMERGENCY_RESPONSE=re.compile(
    r"消防|消防団|消防士|救急|救命|緊急出動|消防車|救急車|"
    r"firefighters?|emergency (?:service|responder)|ambulance",
    re.I,
)
RESPONDER_HARASSMENT=re.compile(
    r"嫌がらせ|ハラスメント|暴言|罵倒|脅迫|威嚇|"
    r"abuse|harass|threat|intimidat",
    re.I,
)

# Death, abuse or disposal of animals is not a light comedy situation, even
# when a model rewrites the headline to suggest an ironic human blunder.
# Apply this to publisher article bodies as well as Japanese draft text.
ANIMAL_DISTRESS=re.compile(
    r"死亡|死体|遺体|死骸|死んだ|埋葬|遺棄|投棄|"
    r"dead|deceased|killed|died|carcass|burial|buried|"
    r"dumped|waste facility|skip bin",
    re.I,
)

# Deliberate disciplinary and institutional protest disputes are not
# lighthearted, accidental blunders. Conjunction keeps harmless ceremony
# mishaps like forgetting one's speech admissible.
FORMAL_CONFLICT_CONTEXT=re.compile(
    r"学位授与式|卒業式|式典|学内評議会|学生リーダー|学内処分|"
    r"大学.*(?:抗議|処分)|convocation|graduation ceremony|student council",
    re.I,
)
DELIBERATE_CONFLICT_ACTION=re.compile(
    r"妨害|乱し|退席させ|抗議|対立|停学|処分|懲戒|"
    r"disrupt|protest|suspended|disciplin|confrontation",
    re.I,
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
    # Natural descriptions of mistakes do not always contain specific
    # words like ミス/間違い. Let the independent fact checker determine
    # whether the incident is genuinely a documented human blunder.
    if not isinstance(error,str) or not 10<=len(error.strip())<=220:
        return "missing_concrete_human_error"
    if re.match(r"^(?:珍しい|珍奇な|不思議な|見たことのない)(?:動物|生物|鳥|鹿|シカ)",error.strip()):
        return "animal_sighting_is_not_a_human_error"
    title=story.get("title","")
    if not isinstance(title,str):
        return "missing_human_error_headline"
    if ANIMAL_TOPIC.search(title) and not ANIMAL_MISTAKE_HEADLINE.search(title):
        return "animal_novelty_not_human_failure"
    situation=" ".join(str(story.get(field,"")) for field in
                       ("title","summary","detail","humanMistake","observedOutcome"))
    if EMERGENCY_RESPONSE.search(situation) and RESPONDER_HARASSMENT.search(situation):
        return "emergency_responder_harassment_not_comic_blunder"
    if FORMAL_CONFLICT_CONTEXT.search(situation) and DELIBERATE_CONFLICT_ACTION.search(situation):
        return "institutional_confrontation_not_comic_miscalculation"
    return None


def animal_novelty_headline(title):
    """Demote animal spectacles while preserving documented human mistakes."""
    return (isinstance(title,str) and bool(ANIMAL_TOPIC.search(title))
            and not bool(ANIMAL_MISTAKE_HEADLINE.search(title)))


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

# Intentional intimidation or harassment of emergency responders is not
# a harmless mix-up, even if an AI can invent an ironic "lesson" about it.
# Check the full publisher text as well as the selected Japanese headline.
EMERGENCY_WORK=re.compile(
    r"消防|救急|消防団|救命|緊急出動|emergency|fire.?fighter|paramedic|ambulance",
    re.I
)
HARASSMENT=re.compile(
    r"嫌がらせ|罵倒|暴言|脅迫|威嚇|harass|abus(?:e|ed|ive)|threat|intimidat",
    re.I
)
SERVICE_PROTEST=re.compile(
    r"消防|救急|消防団|緊急出動|サイレン|fire.?fighter|emergency|siren",
    re.I
)
PROTEST_PATTERN=re.compile(r"苦情|抗議|クレーム|complain|protest",re.I)


def noncomic_incident_rejection(story, fetched_articles=()):
    """Veto real harassment of emergency workers, not routine comic blunders.

    Fetched evidence is used to detect serious incidents even if the drafted
    Japanese headline softens the original report. This is not an exhaustive
    moderation mechanism, so independent editorial judgment remains mandatory.
    """
    if not isinstance(story,dict):
        return "invalid_story"
    fields=("title","summary","detail","humanMistake")
    surface=" ".join(str(story.get(key,"")) for key in fields)
    bodies=" ".join(str(item.get("text",item.get("body","")))
                    for item in fetched_articles if isinstance(item,dict))
    combined=surface+" "+bodies
    if ANIMAL_TOPIC.search(combined) and ANIMAL_DISTRESS.search(combined):
        return "animal_death_or_disposal_not_comedy"
    # Source-text veto also catches a confrontational student/minister story
    # when an AI rewrites its Japanese headline as harmless entertainment.
    if ((FORMAL_CONFLICT_CONTEXT.search(surface)
         and DELIBERATE_CONFLICT_ACTION.search(surface))
        or (FORMAL_CONFLICT_CONTEXT.search(bodies)
            and DELIBERATE_CONFLICT_ACTION.search(bodies))):
        return "disciplinary_confrontation_not_comic_error"
    if ((EMERGENCY_WORK.search(surface) and HARASSMENT.search(surface)) or
            (EMERGENCY_WORK.search(bodies) and HARASSMENT.search(bodies))):
        return "harassment_of_emergency_responders"
    if (SERVICE_PROTEST.search(surface) and PROTEST_PATTERN.search(surface)
            and (re.search(r"救急|消防|消防団|緊急出動|救命",surface)
                 or (EMERGENCY_WORK.search(bodies) and HARASSMENT.search(bodies)))):
        return "emergency_service_protest_not_comic_mixup"
    return None
