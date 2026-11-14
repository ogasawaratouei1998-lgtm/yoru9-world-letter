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
    ('(手違い OR 誤発注 OR 間違えて) when:1d', 'ja', 'JP', 'JP:ja'),
    ('"mix-up" OR "blunder" when:1d', 'en', 'GB', 'GB:en'),
    ('"Verwechslung" OR "aus Versehen" when:1d', 'de', 'DE', 'DE:de'),
    ('"par erreur" OR "méprise" when:1d', 'fr', 'FR', 'FR:fr'),
    ('"por error" OR "equivocación" when:1d', 'es', 'ES', 'ES:es'),
    ('"por engano" OR "erro de pedido" when:1d', 'pt', 'BR', 'BR:pt-419'),
    ('(실수 OR 착각) when:1d', 'ko', 'KR', 'KR:ko'),
    ('"mistake" OR "mix-up" when:1d', 'en', 'IN', 'IN:en'),
    ('"accidentally ordered" OR "wrong destination" when:1d', 'en', 'US', 'US:en'),
    ('"mix-up" OR "wrong" when:1d', 'en', 'AU', 'AU:en'),
]
BBC_FEEDS = [
    'https://feeds.bbci.co.uk/news/uk/rss.xml',
    'https://feeds.bbci.co.uk/news/business/rss.xml',
    'https://feeds.bbci.co.uk/news/technology/rss.xml',
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


def parse_rss(body, provider, relevant_only=False):
    root=ET.fromstring(body)
    if root.tag not in ('rss', '{http://www.w3.org/2005/Atom}feed'):
        raise ValueError('Not an RSS feed')
    result=[]
    for item in root.findall('./channel/item'):
        title=(item.findtext('title') or '').strip()
        link=safe_url(item.findtext('link') or '')
        if not title or not link or EXCLUDE.search(title):
            continue
        if relevant_only and not BBC_RELEVANT.search(title):
            continue
        pubdate=(item.findtext('pubDate') or '').strip()
        if pubdate:
            try: pubdate=parsedate_to_datetime(pubdate).astimezone(timezone.utc).isoformat(timespec='seconds')
            except (ValueError, TypeError): pass
        source=item.find('source')
        publisher=source.text.strip() if source is not None and source.text else urlsplit(link).hostname
        result.append({
            'title':title[:400], 'url':link, 'domain':publisher[:120],
            'seendate':pubdate[:30], 'sourcecountry':'未確認', 'language':'en',
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
    params={'query':q,'mode':'ArtList','format':'json','maxrecords':30,'timespan':'7d','sort':'DateDesc'}
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
    leads, errors, seen=[],[],set()
    def keep(items, limit=75):
        added=0
        for item in items:
            if item['url'] not in seen and len(leads)<150 and added<limit:
                seen.add(item['url']);leads.append(item);added+=1
    for i,(q,lang,country,ceid) in enumerate(SEARCHES):
        if i: time.sleep(1)
        try: keep(get_google(q,lang,country,ceid),limit=15)
        except (HTTPError, URLError, ET.ParseError, ValueError, TimeoutError) as e:
            errors.append(f'Google News {country}: {type(e).__name__}: {e}')
        if len(leads)>=150:break
    if len(leads)<150:
        for url in BBC_FEEDS:
            try: keep(parse_rss(fetch_bytes(url),'BBC RSS (filtered)',relevant_only=True))
            except (HTTPError, URLError, ET.ParseError, ValueError, TimeoutError) as e:
                errors.append(f'BBC RSS: {type(e).__name__}: {e}')
    if not leads:
        try:keep(get_gdelt())
        except (HTTPError, URLError, ValueError, TimeoutError) as e:
            errors.append(f'GDELT: {type(e).__name__}: {e}')
    if not leads:
        print('Could not collect unverified leads: '+'; '.join(errors),file=sys.stderr)
        return 1
    data={
        'generatedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'provider':'Google News RSS, BBC RSS, GDELT (fallback as available)',
        'note':'UNVERIFIED headline links ONLY. These are not verified news facts and may be irrelevant. Read primary reporting and independent sources, check outcomes and harm, then approve manually. Never auto-publish.',
        'errors':errors,
        'candidates':leads,
    }
    dest=Path('data/candidates.json')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Collected {len(leads)} UNVERIFIED links, from {sorted(set(x["provider"] for x in leads))}. Saved for editor review.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
