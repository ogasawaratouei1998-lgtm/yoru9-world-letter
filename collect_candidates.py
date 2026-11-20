#!/usr/bin/env python3
"""Collect UNVERIFIED news leads. Editorial verification is mandatory before publication."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import re
import sys
import time
import xml.etree.ElementTree as ET

# Different search editions prevent US/English-only headlines from occupying all slots.
# These links are only leads; article details and harm must be reviewed manually.
SEARCHES = [
    # User preference: outsized but non-tragic PERSONAL mistakes, not tiny typos.
    # All hits are unverified leads; no claim of blame or amount is accepted here.
    ('(個人 OR 男性 OR 女性 OR 旅行者) (大失敗 OR 判断ミス OR 勘違い) (巨額 OR 高額 OR 大損 OR 全財産) when:7d', 'ja', 'JP', 'JP:ja'),
    ('("bizarre mistake" OR "major blunder" OR "costly miscalculation") when:7d','en','US','US:en'),
    ('("false alarm" OR "AI hoax") (police OR firefighters OR search) when:7d','en','GB','GB:en'),
    ('("price is right" OR "game show") (mistake OR blunder) when:7d','en','US','US:en'),
    ('(誤入札 OR 誤購入 OR 売却ミス OR 大損) (個人 OR 旅行者 OR 落札者) when:7d', 'ja', 'JP', 'JP:ja'),
    ('("costly mistake" OR "expensive blunder" OR "huge mistake") (man OR woman OR tourist OR employee) when:7d', 'en', 'US', 'US:en'),
    ('("accidentally bought" OR "accidentally sold" OR "wrong country") (man OR woman OR tourist) when:7d', 'en', 'GB', 'GB:en'),
    ('(turista OR hombre OR mujer) ("error millonario" OR "compra por error") when:7d', 'es', 'ES', 'ES:es'),
    ('(Mann OR Frau OR Tourist) ("teurer Fehler" OR "versehentlich gekauft") when:7d', 'de', 'DE', 'DE:de'),
    ('(手違い OR 誤発注 OR 間違えて) when:7d', 'ja', 'JP', 'JP:ja'),
    # Additional leads for underrepresented people, workplaces and sports.
    ('(職場 OR 店員 OR 従業員) (手違い OR 勘違い OR 失敗) when:7d', 'ja', 'JP', 'JP:ja'),
    ('(個人 OR 住民 OR 客) (間違い OR 勘違い) when:7d', 'ja', 'JP', 'JP:ja'),
    ('(スポーツ OR 試合 OR 審判) (珍事 OR 勘違い OR 手違い) when:7d', 'ja', 'JP', 'JP:ja'),
    ('(workplace OR employee) (mix-up OR mistake) when:7d', 'en', 'GB', 'GB:en'),
    ('(sports OR referee OR match) (mix-up OR blunder) when:7d', 'en', 'GB', 'GB:en'),
    ('(Sport OR Schiedsrichter) (Panne OR Verwechslung) when:7d', 'de', 'DE', 'DE:de'),
    ('(sport OR arbitre) (erreur OR confusion) when:7d', 'fr', 'FR', 'FR:fr'),
    ('(deporte OR árbitro) (error OR confusión) when:7d', 'es', 'ES', 'ES:es'),
    ('(esporte OR árbitro) (erro OR confusão) when:7d', 'pt', 'BR', 'BR:pt-419'),
    ('"mix-up" OR "blunder" when:7d', 'en', 'GB', 'GB:en'),
    ('"Verwechslung" OR "aus Versehen" when:7d', 'de', 'DE', 'DE:de'),
    ('"par erreur" OR "méprise" when:7d', 'fr', 'FR', 'FR:fr'),
    ('"por error" OR "equivocación" when:7d', 'es', 'ES', 'ES:es'),
    ('"por engano" OR "erro de pedido" when:7d', 'pt', 'BR', 'BR:pt-419'),
    ('(실수 OR 착각) when:7d', 'ko', 'KR', 'KR:ko'),
    ('"mistake" OR "mix-up" when:7d', 'en', 'IN', 'IN:en'),
    # Human-caused errors, not animal oddities or generic surprise clips.
    ('"sent by mistake" OR "wrong recipient" OR "accidental email" when:7d', 'en', 'GB', 'GB:en'),
    ('"wrong order" OR "order mix-up" OR "misprinted" when:7d', 'en', 'US', 'US:en'),
    ('"mistaken identity" OR "mistook for" when:7d', 'en', 'AU', 'AU:en'),
    ('(間違えて送信 OR 誤発注 OR 確認ミス OR 人違い) when:7d', 'ja', 'JP', 'JP:ja'),
    ('("se equivocó" OR "por equivocación") when:7d', 'es', 'MX', 'MX:es'),
    ('("falsche Bestellung" OR "versehentlich geschickt") when:7d', 'de', 'DE', 'DE:de'),
    ('"accidentally ordered" OR "wrong destination" when:7d', 'en', 'US', 'US:en'),
    ('"mix-up" OR "wrong" when:7d', 'en', 'AU', 'AU:en'),
    # Broaden the search beyond the ten original editions; every result remains unverified.
    ('"mistake" OR "blunder" when:7d', 'en', 'ZA', 'ZA:en'),
    ('"error" OR "fracaso" when:7d', 'es', 'MX', 'MX:es'),
    ('"error" OR "equivocación" when:7d', 'es', 'AR', 'AR:es'),
    ('"error" OR "equivocación" when:7d', 'es', 'CO', 'CO:es'),
    ('"mistake" OR "blunder" when:7d', 'en', 'NG', 'NG:en'),
    ('"mistake" OR "blunder" when:7d', 'en', 'KE', 'KE:en'),
    ('"mistake" OR "mix-up" when:7d', 'en', 'NZ', 'NZ:en'),
    ('"mistake" OR "blunder" when:7d', 'en', 'PH', 'PH:en'),
    ('"mistake" OR "blunder" when:7d', 'en', 'SG', 'SG:en'),
    ('"خطأ" OR "بالخطأ" when:7d', 'ar', 'AE', 'AE:ar'),
    ('"خطأ" OR "بالخطأ" when:7d', 'ar', 'SA', 'SA:ar'),
    ('"kesalahan" OR "keliru" when:7d', 'id', 'ID', 'ID:id'),
]
BBC_FEEDS = [
    'https://feeds.bbci.co.uk/news/uk/rss.xml',
    'https://feeds.bbci.co.uk/news/business/rss.xml',
    'https://feeds.bbci.co.uk/news/technology/rss.xml',
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
    # Local reporting is often where small, funny signage/work errors appear.
    'https://feeds.bbci.co.uk/news/england/lancashire/rss.xml',
    'https://feeds.bbci.co.uk/news/england/leicestershire/rss.xml',
    'https://feeds.bbci.co.uk/news/england/merseyside/rss.xml',
]
INDEPENDENT_FEEDS = [
    ('https://www.theguardian.com/world/rss', 'The Guardian RSS'),
    ('https://www.theguardian.com/uk-news/rss', 'The Guardian RSS'),
    ('https://www.theguardian.com/business/rss', 'The Guardian RSS'),
    ('https://www.theguardian.com/technology/rss', 'The Guardian RSS'),
    ('https://feeds.npr.org/1001/rss.xml', 'NPR RSS'),
    ('https://www.cbsnews.com/latest/rss/main', 'CBS RSS'),
    ('https://feeds.nbcnews.com/nbcnews/public/news', 'NBC RSS'),
    ('https://rss.nytimes.com/services/xml/rss/nyt/World.xml', 'NYT RSS'),
    ('https://www.abc.net.au/news/feed/45910/rss.xml', 'ABC Australia RSS'),
    ('https://www.cbc.ca/webfeed/rss/rss-topstories', 'CBC RSS'),
    ('https://www.france24.com/en/rss', 'France24 RSS'),
]
# Direct local/regional publisher feeds complement aggregators across continents.
# sourcecountry is the publisher/search market, NOT the country where an
# incident happened. Only audited article facts may determine story.country.
# A failing or changed feed is reported in diagnostics, never treated as evidence.
LOCAL_LANGUAGE_FEEDS = [
    ('https://www.lemonde.fr/rss/une.xml', 'Le Monde RSS', 'fr', 'FR'),
    ('https://rss.dw.com/rdf/rss-de-all', 'Deutsche Welle Deutsch RSS', 'de', 'DE'),
    ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada', 'El País RSS', 'es', 'ES'),
    ('https://www.japantimes.co.jp/feed/', 'Japan Times RSS', 'en', 'JP'),
    ('https://www.thehindu.com/news/national/feeder/default.rss', 'The Hindu India RSS', 'en', 'IN'),
    ('https://g1.globo.com/rss/g1/', 'G1 Brazil RSS', 'pt', 'BR'),
    ('https://www.premiumtimesng.com/feed', 'Premium Times Nigeria RSS', 'en', 'NG'),
    ('https://www.inquirer.net/feed/', 'Inquirer Philippines RSS', 'en', 'PH'),
]
GOOGLE = 'https://news.google.com/rss/search'
GDELT = 'https://api.gdeltproject.org/api/v2/doc/doc'
EXCLUDE = re.compile(r'\b(killed|murder|fatal|death|died|suicide|rape|shooting|injured|hospitalized|war|bombing|disaster|fire killed|crash killed)\b|死亡|殺害|負傷|災害|殺人|自殺|銃撃|戦争|死者|犠牲者', re.I)
BBC_RELEVANT = re.compile(r'\b(accidentally|mix.?up|blunder|mistake|wrong|error|apolog|embarrass|confus|fiasco|misprint|misplac|oversiz|typo|ordered|delivered)\w*\b', re.I)


def safe_url(raw):
    try:
        p=urlsplit(str(raw).strip())
        return p._replace(fragment='').geturl() if p.scheme=='https' and p.hostname and not p.username and not p.password and p.port in (None,443) else None
    except (ValueError, TypeError):
        return None


def fetch_bytes(url, timeout=20):
    req=Request(url, headers={
        'User-Agent':'Mozilla/5.0 (compatible; Yoru9-WorldLetter-Research/1.0)',
        'Accept':'application/rss+xml, application/xml, text/xml, application/json;q=0.8',
    })
    with urlopen(req,timeout=timeout) as response:
        return response.read(2_000_000)


def parse_rss(body, provider, relevant_only=False, language='en', sourcecountry='未確認'):
    root=ET.fromstring(body)
    if root.tag not in ('rss', '{http://www.w3.org/2005/Atom}feed', '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'):
        raise ValueError('Not an RSS feed')
    result=[]
    rdf_feed = root.tag == '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'
    atom_feed = root.tag == '{http://www.w3.org/2005/Atom}feed'
    if rdf_feed:
        # RSS 1.0 places items directly below rdf:RDF, in the RSS 1.0 namespace.
        items = root.findall('./{http://purl.org/rss/1.0/}item')
        ns = '{http://purl.org/rss/1.0/}'
    elif atom_feed:
        items = root.findall('./{http://www.w3.org/2005/Atom}entry')
        ns = '{http://www.w3.org/2005/Atom}'
    else:
        items = root.findall('./channel/item')
        ns = ''
    for item in items:
        title=(item.findtext(ns+'title') or '').strip()
        raw_link=item.findtext(ns+'link') or ''
        if atom_feed:
            link_tag=item.find(ns+'link')
            raw_link=link_tag.get('href','') if link_tag is not None else ''
        link=safe_url(raw_link)
        if not title or not link or EXCLUDE.search(title):
            continue
        if relevant_only and not BBC_RELEVANT.search(title):
            continue
        pubdate=(item.findtext('pubDate') or item.findtext(ns+'date') or item.findtext(ns+'updated') or '').strip()
        if pubdate:
            try: pubdate=parsedate_to_datetime(pubdate).astimezone(timezone.utc).isoformat(timespec='seconds')
            except (ValueError, TypeError): pass
        source=item.find('source')
        publisher=source.text.strip() if source is not None and source.text else urlsplit(link).hostname
        result.append({
            'title':title[:400], 'url':link, 'domain':publisher[:120],
            'seendate':pubdate[:30], 'sourcecountry':sourcecountry, 'language':language,
            'status':'unverified', 'provider':provider,
        })
    return result


def get_google(query, lang='en', country='US', ceid='US:en'):
    params={'q':query,'hl':lang,'gl':country,'ceid':ceid}
    url=GOOGLE+'?'+urlencode(params)
    items=parse_rss(fetch_bytes(url),f'Google News RSS ({country})')
    return [dict(item,sourcecountry=country,language=lang) for item in items]


def uncovered_country_searches(day=None, max_countries=9):
    """Rotate discovery requests across NEVER-featured reporting countries.

    A GDELT match is merely an UNVERIFIED lead. The article's occurrence
    country is independently checked later against ORIGINAL publisher text.
    Publisher sourcecountry, RSS market and geography keywords are not proof.
    """
    from country_codes import catalog, country_codes
    if day is None:
        day=datetime.now(timezone(timedelta(hours=9))).date()
    from collections import Counter
    appeared=Counter()
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            issue=json.loads(file.read_text(encoding="utf-8"))
            issue_day=datetime.strptime(issue.get("editionDate",""),"%Y-%m-%d").date()
            if issue.get("status")!="published" or issue_day>day:
                continue
            for story in issue.get("stories",[]):
                appeared.update(country_codes(story.get("country")))
        except (ValueError,OSError,TypeError,KeyError):
            continue
    unseen=sorted((x for x in catalog() if appeared[x["code"]]==0),
                  key=lambda x:x["code"])
    if not unseen:
        return ()
    # 9-country daily windows step through the whole set without sticking
    # permanently to alphabetically early and high-publication countries.
    start=(day.toordinal()*max_countries)%len(unseen)
    selected=[unseen[(start+i)%len(unseen)]
              for i in range(min(max_countries,len(unseen)))]
    def english_name(item):
        # Use original English country names rather than abbreviations and
        # keep GDELT query fragments strictly quoted and bounded.
        for alias in item["aliases"]:
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9 .-]{2,64}",alias) and len(alias)>3:
                return alias
        return None
    names=[english_name(x) for x in selected]
    names=[name for name in names if name]
    return tuple(
        "("+" OR ".join('"'+name+'"' for name in names[i:i+3])+
        ') ("mistake" OR "mix-up" OR "blunder" OR "unexpected")'
        for i in range(0,len(names),3)
    )


def get_gdelt(extra_searches=(), min_interval_seconds=10.5, diagnostics=None,
              day=None, max_queries=5):
    """Discover original publisher links; respect GDELT's public API pacing.

    A rate-limited, malformed or empty GDELT response must be visible as a
    COUNTER, not silently treated as zero funny news in the world.
    No API response or title is considered a verified news event.
    """
    from collections import Counter
    if not isinstance(min_interval_seconds,(int,float)) or not 0<=min_interval_seconds<=30:
        raise ValueError("GDELT delay must be between 0 and 30 seconds")
    if type(max_queries) is not int or not 1<=max_queries<=5:
        raise ValueError("GDELT query budget must be 1-5")
    if day is None:
        day=datetime.now(timezone(timedelta(hours=9))).date()
    health=Counter()
    # Discover consequential personal blunders BEFORE tiny misspellings:
    # 5 GDELT calls max, original article URL required, no headline-only approval.
    searches=(
        '("million dollar mistake" OR "costly mistake" OR "expensive blunder")',
        '("accidentally bought" OR "accidentally sold" OR "wrong bid")',
        '("huge mistake" OR "spectacular mistake" OR "major blunder")',
        '("AI hoax" OR "false alarm" OR "search for days")',
        '("accidental purchase" OR "wrong country" OR "wrong house")',
        '("costly error" OR "wrong price" OR "game show mistake")',
        '("error millonario" OR "compra por error" OR "grave equivocación")',
        '("teurer Fehler" OR "versehentlich verkauft" OR "großer Irrtum")',
        '("失敗で大損" OR "数千万円のミス" OR "誤落札")',
        # Backups only: small everyday slips do not displace large stories.
        '("wrong delivery" OR "misprint" OR "mix-up")',
    )
    articles,seen=[],set()
    # Always devote at least 3/5 queries to the higher-impact themes,
    # while preserving one geographically diverse query each day.
    country_queries=tuple(extra_searches)[:min(1,max(0,max_queries-3))]
    remaining=max_queries-len(country_queries)
    # Rotate the ten creative search themes rather than hammering all ten
    # every morning. The three country targets continue to cover nine
    # never-featured locations each day. Over several days all headline
    # languages and error motifs receive their turn.
    offset=(day.toordinal()*max(1,remaining))%9
    generic=tuple(searches[(offset+i)%len(searches)]
                  for i in range(remaining))
    queries=(*country_queries,*generic)
    health["planned"]=len(queries)
    consecutive_rate_limited=0
    for index,query in enumerate(queries):
        # Live evidence: 11 of 13 responses were HTTP 429 despite 5.5-second
        # pacing. Limit to five rotated queries, increase the interval and
        # stop when the provider repeatedly requests throttling.
        if index:
            time.sleep(min_interval_seconds)
        health["attempted"]+=1
        params={'query':query,'mode':'ArtList','format':'json','maxrecords':40,
                'timespan':'7d','sort':'DateDesc'}
        try:
            body=fetch_bytes(GDELT+'?'+urlencode(params))
            if not isinstance(body,bytes):
                health["invalid_json_or_plaintext"]+=1
                consecutive_rate_limited=0
                continue
            # HTTP 200 may contain a plain-text "limit requests" notice.
            # Recognize the throttle without ever printing response contents.
            if not body.lstrip().startswith(b"{"):
                text=body[:256].decode("utf-8",errors="replace").lower()
                if any(term in text for term in
                       ("limit requests","too many requests","rate limit",
                        "please wait","requests per")):
                    health["rate_limit_notice"]+=1
                    consecutive_rate_limited+=1
                    if consecutive_rate_limited>=2:
                        health["circuit_open"]=1
                        break
                else:
                    health["invalid_json_or_plaintext"]+=1
                    consecutive_rate_limited=0
                continue
            data=json.loads(body.decode('utf-8'))
        except HTTPError as exc:
            health["http_"+str(exc.code)]+=1
            if exc.code==429:
                consecutive_rate_limited+=1
                if consecutive_rate_limited>=2:
                    health["circuit_open"]=1
                    break
            else:
                consecutive_rate_limited=0
            continue
        except (URLError,OSError,TimeoutError):
            health["network_failure"]+=1
            consecutive_rate_limited=0
            continue
        except (ValueError,UnicodeError):
            health["invalid_json_or_plaintext"]+=1
            consecutive_rate_limited=0
            continue
        consecutive_rate_limited=0
        if not isinstance(data,dict) or not isinstance(data.get("articles"),list):
            health["missing_articles"]+=1
            continue
        if not data["articles"]:
            health["empty"]+=1
        else:
            health["responded"]+=1
        added=0
        for item in data['articles']:
            if not isinstance(item,dict):continue
            title=str(item.get('title','')).strip()
            link=safe_url(item.get('url',''))
            if not link or link in seen or not title or EXCLUDE.search(title):
                continue
            if added>=10:break
            seen.add(link)
            added+=1
            articles.append({
                'title':title[:400],'url':link,
                'domain':str(item.get('domain',''))[:120],
                'seendate':str(item.get('seendate',''))[:30],
                'sourcecountry':str(item.get('sourcecountry',''))[:100],
                'language':str(item.get('language',''))[:40],
                'status':'unverified','provider':'GDELT DOC API',
            })
    health["unverified_original_links"]=len(articles)
    if diagnostics is not None:
        diagnostics.update(dict(sorted(health.items())))
    return articles

def main():
    from news_sources import fetch_registry_feeds, source_registry
    leads, errors, seen=[],[],set()
    def keep(items, limit=75):
        added=0
        for item in items:
            if item['url'] not in seen and len(leads)<750 and added<limit:
                seen.add(item['url']);leads.append(item);added+=1
    # The dedicated incident discovery must run BEFORE broad publisher feeds
    # fill the global 750-lead cap. A previous production run collected 750
    # general headlines with ZERO Google or GDELT mishap-search leads.
    # GDELT gives original publisher article URLs, unlike Google News RSS
    # aggregator links that cannot serve as independently verified evidence.
    # No GDELT result is publication-approved by being found here.
    try:
        gdelt_health={}
        focused=get_gdelt(extra_searches=uncovered_country_searches(),
                          diagnostics=gdelt_health)
        keep(focused,limit=90)
        print("Focused original-publisher search health (counts only):",
              json.dumps(gdelt_health,sort_keys=True),flush=True)
        print("Original-publisher mishap search leads:",
              sum(lead.get("provider")=="GDELT DOC API" for lead in leads),
              "(UNVERIFIED)",flush=True)
    except (HTTPError,URLError,ValueError,TimeoutError,OSError) as exc:
        errors.append("GDELT: "+type(exc).__name__)
    # Continue with direct original-publisher feeds, never an automatic
    # inference that the publisher's market is the incident location.
    # Isolate failing feeds; preserve the global cap and source scrutiny.
    try:
        registered=fetch_registry_feeds(
            sources=source_registry(),fetch=fetch_bytes,parse=parse_rss,
            max_workers=10,per_feed=18,
            report_path="data/source-health.json")
        # Give 42+ markets a real chance in a fixed 750-lead budget.
        # The collector still preserves other-source and BBC opportunities.
        keep(registered,limit=350)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        errors.append("Publisher RSS catalog: "+type(exc).__name__)
    for url,provider,language,country in LOCAL_LANGUAGE_FEEDS:
        try:
            keep(parse_rss(fetch_bytes(url),provider,language=language,sourcecountry=country),limit=18)
        except (HTTPError, URLError, ET.ParseError, ValueError, TimeoutError) as e:
            errors.append(f'{provider}: {type(e).__name__}: {e}')
    for url,provider in INDEPENDENT_FEEDS:
        try: keep(parse_rss(fetch_bytes(url),provider,relevant_only=False),limit=18)
        except (HTTPError, URLError, ET.ParseError, ValueError, TimeoutError) as e:
            errors.append(f'{provider}: {type(e).__name__}: {e}')
    for url in BBC_FEEDS:
        try: keep(parse_rss(fetch_bytes(url),'BBC RSS (unverified)',relevant_only=False,sourcecountry='GB'),limit=18)
        except (HTTPError, URLError, ET.ParseError, ValueError, TimeoutError) as e:
            errors.append(f'BBC RSS: {type(e).__name__}: {e}')
    for i,(q,lang,country,ceid) in enumerate(SEARCHES):
        if i: time.sleep(0.5)
        try: keep(get_google(q,lang,country,ceid),limit=8)
        except (HTTPError, URLError, ET.ParseError, ValueError, TimeoutError) as e:
            errors.append(f'Google News {country}: {type(e).__name__}: {e}')
        if len(leads)>=750:break
    if not leads:
        print('Could not collect unverified leads: '+'; '.join(errors),file=sys.stderr)
        return 1
    data={
        'generatedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'provider':'GDELT focused original-publisher search first; then reviewed global publisher RSS registry, original publisher RSS, BBC RSS, Google News RSS (where capacity permits)',
        'note':'UNVERIFIED headline links ONLY. These are not verified news facts and may be irrelevant. Automatic review must independently verify publisher article bodies before preparing any approved edition; never publish unverified leads.',
        'errors':errors,
        'candidates':leads,
    }
    dest=Path('data/candidates.json')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    from collections import Counter
    markets=Counter(x.get('sourcecountry','未確認') for x in leads)
    print('Unverified discovery-source markets (NOT incident countries):',
          json.dumps(dict(markets.most_common()),ensure_ascii=False),flush=True)
    print(f'Collected {len(leads)} UNVERIFIED links, from {sorted(set(x["provider"] for x in leads))}. Saved for editor review.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
