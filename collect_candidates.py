#!/usr/bin/env python3
"""Collect UNVERIFIED news leads. Editorial verification is mandatory before publication."""
from __future__ import annotations
from datetime import datetime, timezone
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


def get_gdelt():
    q='("blunder" OR "mix-up")'
    params={'query':q,'mode':'ArtList','format':'json','maxrecords':75,'timespan':'7d','sort':'DateDesc'}
    obj=json.loads(fetch_bytes(GDELT+'?'+urlencode(params)).decode('utf-8'))
    articles=[]
    for a in obj.get('articles',[]):
        title=str(a.get('title','')).strip()
        link=safe_url(a.get('url',''))
        if not link or not title or EXCLUDE.search(title):
            continue
        articles.append({'title':title[:400],'url':link,'domain':str(a.get('domain',''))[:120],
          'seendate':str(a.get('seendate',''))[:30],'sourcecountry':str(a.get('sourcecountry',''))[:100],
          'language':str(a.get('language',''))[:40],'status':'unverified','provider':'GDELT DOC API'})
    return articles


def main():
    from news_sources import fetch_registry_feeds, source_registry
    leads, errors, seen=[],[],set()
    def keep(items, limit=75):
        added=0
        for item in items:
            if item['url'] not in seen and len(leads)<750 and added<limit:
                seen.add(item['url']);leads.append(item);added+=1
    # Direct publishers come before Google News aggregator links, which are
    # unsuitable as evidence without an original publisher article body.
    # Feed failures are isolated and never treated as proof that news occurred.
    try:
        registered=fetch_registry_feeds(
            sources=source_registry(),fetch=fetch_bytes,parse=parse_rss,
            max_workers=10,per_feed=18,
            report_path="data/source-health.json")
        keep(registered,limit=285)
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
        try: keep(parse_rss(fetch_bytes(url),'BBC RSS (unverified)',relevant_only=False),limit=18)
        except (HTTPError, URLError, ET.ParseError, ValueError, TimeoutError) as e:
            errors.append(f'BBC RSS: {type(e).__name__}: {e}')
    try:keep(get_gdelt(),limit=40)
    except (HTTPError, URLError, ValueError, TimeoutError) as e:
        errors.append(f'GDELT: {type(e).__name__}: {e}')
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
        'provider':'Reviewed global publisher RSS registry, Google News RSS, BBC RSS, independent publisher RSS, local-language RSS, GDELT (all attempted)',
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
