"""Pure, unverified lead ranking and retrieval budgeting. No AI, publication or writes."""
import re
from urllib.parse import urlsplit
from country_codes import country_code, country_region
from editorial_identity import animal_novelty_headline

INCIDENT_TERMS=re.compile(r"\b(accidentally|mistak(?:e|en)|mix.?up|blunder|error|wrong|failed|failure|apolog(?:y|ise|ize)|revers(?:e|al)|scrap(?:ped)?|cancel(?:led|ed)|recall|outage|glitch|misplac(?:ed)?|misprint|confus(?:ion|ed)|fiasco|oversight|backfir(?:e|ed)|botch(?:ed)?|miscalculat(?:e|ed|ion))\b|手違い|誤発注|間違|失敗|謝罪|撤回|中止|障害|誤送信|ミス|실수|착각|Verwechslung|Fehler|Panne|par erreur|erreur|confusion|equivocaci[oó]n|por engano|equívoco|confusão|erro|falha",re.I)

# Discovery prioritizes headline clues for significant individual blunders.
# Trivial slips remain backup leads; disciplinary crises and animal novelties
# stay low priority. This does not certify fault, magnitude or suitability.
COMIC_MISSTEP_TERMS=re.compile(
    r"typo|misspell|misprint|mix.?up|accidentally|by mistake|mistook|"
    r"wrong recipient|wrong order|wrong delivery|wrong address|"
    r"wrong (?:city|cities|town|landmark|cathedral|mural|sign)|"
    r"AI.generated.{0,70}(?:wrong|errors?|mistake|misspell)|"
    r"誤字|誤記|手違い|誤配達|誤送信|誤発注|勘違い|見間違い|取り違え|"
    r"verwechslung|aus versehen|por error|equivocaci[oó]n|"
    r"erreur|m[eé]prise|faux|sbagli|scambiat|errore|"
    r"equ[ií]voc|confus[aã]o|engano|enganou|"
    r"\b(?:salah|keliru|tertukar|kesalahan)\b|"
    r"\b(?:nh[aầ]m|sai|l[oỗ]i)\b|"
    r"pomy[lł]k|yanl[iı][sş]|hata|خطأ|خطا|"
    r"실수|착각|오류|잘못",re.I
)
SERIOUS_CONFLICT_TERMS=re.compile(
    r"harass|abuse|intimidat|disciplin|suspend|protest|minister|"
    r"convocation row|emergency siren|罵倒|嫌がらせ|脅迫|"
    r"停学|懲戒|処分|大臣|抗議|起訴",re.I
)

POLICY_EXPLAINER_TITLE=re.compile(
    r"(?:\bwhat\b.{0,90}\b(?:rules?|policy|policies|law|changes)\b"
    r".{0,90}\bmean for\b)|"
    r"(?:\b(?:guide|explainer)\s*:\s*(?:proposed|new)\b)|"
    r"(?:新(?:制度|規則|ルール).{0,20}(?:解説|影響|とは))",
    re.I,
)

def source_title_is_policy_explainer(title):
    """A general policy guide is not itself a documented human blunder."""
    return isinstance(title,str) and bool(POLICY_EXPLAINER_TITLE.search(title))
# Retrieval signal only: two distinct clues are needed to rank personal
# LARGE mistakes above harmless typos. Headline text NEVER proves blame.
PERSONAL_ACTOR_TERMS=re.compile(
    r"\b(?:man|woman|person|individual|tourist|traveler|traveller|driver|"
    r"employee|worker|customer|referee|athlete|artist|chef|owner|collector|"
    r"investor|bidder|buyer|seller|gambler|pilot|student|teacher)\b|"
    r"個人|男性|女性|旅行者|観光客|運転手|店員|従業員|選手|審判|"
    r"職人|料理人|持ち主|所有者|購入者|出品者|落札者|投資家",re.I)
LARGE_PERSONAL_CONSEQUENCE_TERMS=re.compile(
    r"\b(?:million|billion|thousand|six.figure|seven.figure|"
    r"lost (?:everything|a fortune|his job|her job)|spent (?:a fortune|thousands)|"
    r"wrong (?:country|continent|house|flight)|huge|massive|record|"
    r"entire (?:collection|savings)|bankrupt|costly|expensive|"
    r"accidental (?:bid|purchase|sale)|accidentally (?:sold|bought|deleted))\b|"
    r"数千万|数億|数千万円|数億円|\d+億|\d+万(?:円|ドル)|"
    r"全財産|大損|巨額|高額|破産|全て失|すべて失|"
    r"世界記録|誤落札|誤入札|全削除|売却ミス|購入ミス|"
    r"別の国|別の大陸",re.I)

def incident_priority(lead):
    title=lead.get("title","")
    # Discovery order is not proof: original sources and AI must still audit.
    if source_title_is_policy_explainer(title):
        rank=4
    elif animal_novelty_headline(title):
        rank=4
    elif SERIOUS_CONFLICT_TERMS.search(title):
        rank=3
    elif (PERSONAL_ACTOR_TERMS.search(title)
          and LARGE_PERSONAL_CONSEQUENCE_TERMS.search(title)
          and (COMIC_MISSTEP_TERMS.search(title) or INCIDENT_TERMS.search(title))):
        # Personal + substantial + demonstrable mistake signal (still unverified).
        rank=-1
    elif COMIC_MISSTEP_TERMS.search(title):
        rank=0
    elif INCIDENT_TERMS.search(title):
        rank=1
    else:
        rank=2
    return (rank,1 if host(lead.get("url",""))=="news.google.com" else 0)


def discovery_desk(lead):
    """Provisional headline desk: retrieval diversity, never fact approval."""
    title=str(lead.get("title",""))
    if re.search(r"\b(?:sport|sports|match|referee|athlete|football|soccer|cricket|tennis|goal|marathon|coach|tournament|olympic)\b|試合|審判|選手|スポーツ|サッカー|野球|競技",title,re.I):
        return "sports"
    if re.search(r"\b(?:employee|worker|staff|delivery|workplace|office|chef|waiter|shop|customer|teacher|school|restaurant|order|job)\b|店員|職員|配達|注文|職場|教師|授業|作業員",title,re.I):
        return "work"
    if re.search(r"\b(?:man|woman|couple|tourist|resident|passenger|neighbor|neighbour|driver|parent|visitor|individual)\b|観光客|旅行者|住民|個人|夫婦|運転手|乗客|親子",title,re.I):
        return "person"
    if re.search(r"\b(?:company|corporation|council|firm|agency|government|mayor|brand|business|startup)\b|企業|会社|市役所|自治体|組織|行政|メーカー",title,re.I):
        return "company"
    return "other"


def prioritize_comic_groups(groups, limit=24):
    """Expose sizeable personal mistakes to editor A before small slips/disputes.

    This ranks unverified publisher evidence; independent fact and humor review
    still decides publication. A vetted original article does not need a
    corroborating publisher to be eligible for the shortlist.
    """
    ranked=sorted(
        (group for group in groups if group),
        key=lambda group: (
            min(incident_priority(item)[0] for item in group),
            0 if len(group) >= 2 else 1,
            min(incident_priority(item)[1] for item in group),
        ),
    )
    if limit<8:
        return ranked[:limit]
    # Reserve ALL top-tier major personal cases before allocating a single
    # editorial slot to regional or category diversity. Source validation and
    # editorial safety still apply independently; this is not a truth claim.
    seeded=[group for group in ranked
            if min(incident_priority(item)[0] for item in group)<0][:limit]
    if len(seeded)>=limit:
        return seeded
    # Secondary categories/regions only fill remaining editorial capacity.
    per_desk=max(1,min(3,limit//12))
    for desk in ("person","work","sports","company"):
        chosen=0
        for group in ranked:
            if min(incident_priority(item)[0] for item in group)>1:
                continue
            if not any(discovery_desk(item)==desk for item in group):
                continue
            if group not in seeded:
                seeded.append(group)
                chosen+=1
            if chosen>=per_desk:
                break
    # Next preserve qualified human-mishap evidence from *publisher* regions.
    # These are discovery markets, NOT asserted event countries. Geographic
    # exposure never overrides the actual original-article/AI verification.
    from collections import Counter
    regional_counts=Counter()
    for group in seeded:
        for region in {country_region(item.get("sourcecountry")) for item in group}:
            if region: regional_counts[region]+=1
    region_allowance=max(1,min(2,limit//18))
    for group in ranked:
        if len(seeded)>=limit:
            break
        if min(incident_priority(item)[0] for item in group)>2 or group in seeded:
            continue
        regions={country_region(item.get("sourcecountry")) for item in group}
        if any(region and regional_counts[region]<region_allowance
               for region in regions):
            seeded.append(group)
            for region in regions:
                if region: regional_counts[region]+=1
    # Within continents, expose a few distinct local media markets. A
    # high-volume US/UK publisher must not occupy every creative review slot.
    represented={country_code(item.get("sourcecountry"))
                 for group in seeded for item in group}
    new_market_budget=max(0,min(limit//3,limit-len(seeded)))
    for group in ranked:
        if new_market_budget<=0 or len(seeded)>=limit:
            break
        if min(incident_priority(item)[0] for item in group)>2 or group in seeded:
            continue
        countries={country_code(item.get("sourcecountry")) for item in group}
        countries.discard(None)
        if countries-represented:
            seeded.append(group)
            represented.update(countries)
            new_market_budget-=1
    return (seeded+[group for group in ranked if group not in seeded])[:limit]


def host(url):
    try:
        p=urlsplit(url)
        return p.hostname.lower().removeprefix("www.") if p.scheme=="https" and p.hostname and not p.username else ""
    except ValueError:return ""

def source_reading_stop_reason(readable_count, high_signal_count, remaining_seconds):
    """Stop generic URL reading while reserving time for full AI source audits.

    These thresholds concern only retrieval resource budgeting, never news
    approval or a minimum/maximum number of published articles.
    """
    if remaining_seconds < 280:
        return "reserve_time_for_independent_review"
    if readable_count >= 72 and high_signal_count >= 12:
        return "enough_promising_original_reports_for_editorial_review"
    return None


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
    # Source-fetch budget serves the most significant person-led failures
    # first; within each tier retain host and region-balanced ordering.
    return sorted(ordered,key=lambda lead:(incident_priority(lead)[0]>=0,))


