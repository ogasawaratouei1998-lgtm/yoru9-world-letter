#!/usr/bin/env python3
"""Package ONLY the public reader assets for GitHub Pages deployment."""
from pathlib import Path
import shutil
import json
import re
from datetime import date
from urllib.parse import urlparse
from urllib.request import Request, urlopen

def bundle_travel_photos(root, output):
    """Package real, rights-checked destination photos with the page.

    If a photo cannot be packaged, do not release partially illustrated cards.
    This leaves the previous working GitHub Pages version live.
    """
    manifest = root / 'travel-stops.json'
    if not manifest.is_file():
        return 0
    stops = json.loads(manifest.read_text(encoding='utf-8'))
    required = {}
    for key, stop in stops.items():
        asset = stop.get('photoAsset', '')
        url = stop.get('photo', '')
        page = stop.get('photoPage', '')
        license_url = stop.get('licenseUrl', '')
        if not re.fullmatch(r'assets/travel/[a-z0-9-]+\.jpg', asset):
            raise ValueError(f'{key}: invalid local photo path')
        parts = urlparse(url)
        source = urlparse(page)
        if not (parts.scheme == 'https' and parts.hostname == 'thumb.wikimedia.org'
                and parts.path.startswith('/wikipedia/commons/thumb/')
                and source.scheme == 'https' and source.hostname == 'commons.wikimedia.org'
                and source.path.startswith('/wiki/File:')
                and license_url.startswith('https://creativecommons.org/')):
            raise ValueError(f'{key}: photo or license information invalid')
        if asset in required and required[asset] != url:
            raise ValueError(f'{key}: photo path is assigned to two different images')
        required[asset] = url

    failures = []
    for asset, url in required.items():
        target = output / asset
        target.parent.mkdir(parents=True, exist_ok=True)
        paths = [
            url,
            url.replace('https://thumb.wikimedia.org/', 'https://upload.wikimedia.org/'),
            url.replace('/500px-', '/330px-'),
            url.replace('https://thumb.wikimedia.org/', 'https://upload.wikimedia.org/').replace('/500px-', '/330px-'),
        ]
        last_error = 'no sources'
        for candidate in dict.fromkeys(paths):
            try:
                request = Request(candidate, headers={'User-Agent': 'Yoru9WorldLetter/1.1 (educational CC photo previews; GitHub Pages)'})
                with urlopen(request, timeout=20) as response:
                    payload = response.read(2_000_001)
                    kind = response.headers.get('Content-Type', '')
                if not (payload.startswith(b'\xff\xd8\xff') and 3000 <= len(payload) <= 2_000_000
                        and 'image/' in kind):
                    raise ValueError('response was not a valid JPEG preview')
                target.write_bytes(payload)
                break
            except (OSError, ValueError) as exc:
                last_error = str(exc)
        if not target.exists():
            failures.append(f'{asset}: {last_error}')
    print(f'旅行写真のサイト内保存：{len(required) - len(failures)}/{len(required)} 件')
    if failures:
        raise RuntimeError('旅行写真の欠落を防ぐため公開停止：' + '; '.join(failures))
    return len(required)


def validate_country_highlights(root):
    """Reject ungrounded, future-dated or invalid Country Portrait topics."""
    from datetime import datetime, timedelta
    known = {record['code'] for record in json.loads(
        (root / 'country-catalog.json').read_text(encoding='utf-8'))}
    data = json.loads((root / 'country-highlights.json').read_text(encoding='utf-8'))
    if data.get('version') != 1 or not isinstance(data.get('highlights'), dict):
        raise ValueError('invalid country-highlights registry')
    sources = json.loads((root / 'country-highlight-sources.json').read_text(encoding='utf-8'))
    if sources.get('version') != 1 or not isinstance(sources.get('sources'), dict):
        raise ValueError('invalid country highlight source allowlist')
    trusted_hosts = {}
    for country, records in sources['sources'].items():
        if country not in known or not isinstance(records, list) or not records:
            raise ValueError('invalid country-source mapping: ' + str(country))
        approved = set()
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get('name'), str):
                raise ValueError(country + ': invalid official publisher name')
            source = urlparse(record.get('url', ''))
            if source.scheme != 'https' or not source.hostname or source.username or source.password:
                raise ValueError(country + ': invalid official source URL')
            approved.add(source.hostname)
        trusted_hosts[country] = approved
    for country, rows in data['highlights'].items():
        if country not in known or not isinstance(rows, list):
            raise ValueError('invalid country highlight: ' + str(country))
        for item in rows:
            try:
                if not isinstance(item, dict):
                    raise ValueError('not an object')
                for key in ('title', 'body', 'sourceName', 'sourceUrl',
                            'validFrom', 'validThrough', 'checkedOn'):
                    if not isinstance(item.get(key), str) or not item[key].strip():
                        raise ValueError('missing ' + key)
                start, stop, checked = [
                    datetime.strptime(item[key], '%Y-%m-%d').date()
                    for key in ('validFrom', 'validThrough', 'checkedOn')
                ]
                if start > stop or (stop - start) > timedelta(days=60):
                    raise ValueError('invalid publication window')
                if checked > stop or checked < start - timedelta(days=30):
                    raise ValueError('invalid source check date')
                url = urlparse(item['sourceUrl'])
                if url.scheme != 'https' or url.hostname not in trusted_hosts.get(country, set()) or url.username or url.password:
                    raise ValueError('unapproved source host')
                if len(item['title']) > 80 or len(item['body']) > 350:
                    raise ValueError('oversized editorial text')
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f'{country}: unsafe or unsupported current topic: {exc}') from exc
    return data


def build_country_coverage(root,output):
    """Publish a truthful all-time 196-location scoreboard from released issues.

    Unverified news leads, draft stories and publisher markets NEVER count.
    One historical cross-border article can count in two reporting locations.
    """
    from collections import Counter
    from country_codes import country_codes
    catalog=json.loads((root/'country-catalog.json').read_text(encoding='utf-8'))
    known={item['code'] for item in catalog}
    counts=Counter()
    published_dates=[]
    for file in sorted((root/'data/archive').glob('????-??-??.json')):
        try:
            issue=json.loads(file.read_text(encoding='utf-8'))
            if issue.get('status')!='published' or issue.get('editionDate')!=file.stem:
                continue
            published_dates.append(file.stem)
            for story in issue.get('stories',[]):
                for code in country_codes(story.get('country')):
                    if code in known:
                        counts[code]+=1
        except (OSError,TypeError,ValueError,KeyError):
            continue
    result={
        'basis':'published-archive-only',
        'total':len(known),
        'covered':len(counts),
        'remaining':len(known)-len(counts),
        'byCountry':dict(sorted(counts.items())),
        'latestEdition':max(published_dates) if published_dates else None,
        'note':'Counts come from released, source-reviewed editions. These are reporting locations, not a claim of diplomatic recognition.'
    }
    dest=output/'data/country-coverage.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"累計ニュース掲載国：{len(counts)}/{len(known)} か国・地域")
    return result


def build(root, output):
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for relative in ('index.html', 'manifest.webmanifest', 'service-worker.js', 'notifications.js', 'world-passport.js', 'notification-config.json', 'country-catalog.json', 'country-highlights.json', 'travel-stops.json', 'assets/icon.svg',
                     'data/current.json', 'data/archive/index.json', 'assets/world-today-illustrated.svg'):
        source = root / relative
        if not source.is_file():
            raise FileNotFoundError(relative)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    validate_country_highlights(root)
    # Original in-house SVG illustrations are editorial artwork, NOT incident
    # photographs. Bundle each verified static asset; no outside image server
    # or mutable media URL is needed to render the news cards.
    artwork_dir=root/'assets'/'news'
    if not artwork_dir.is_dir():
        raise FileNotFoundError('assets/news is required for published illustrations')
    required_artwork={
        'coffee-rescue.svg','road-typo.svg','monkey-patrol.svg',
        'category-work.svg','category-company.svg',
        'category-person.svg','category-sports.svg'
    }
    if not required_artwork.issubset({x.name for x in artwork_dir.glob('*.svg')}):
        raise FileNotFoundError('A published news illustration is missing')
    shutil.copytree(artwork_dir,output/'assets'/'news',dirs_exist_ok=True)
    # Ship ONLY the active issue's own generated photos. On the next issue,
    # old WebPs never enter the public build even if the repository retained
    # a file for audit. Historical article JSON falls back to its safe SVG.
    from prepare_news_images import valid_webp,expected_path
    current=json.loads((root/'data/current.json').read_text(encoding='utf-8'))
    if (current.get('editionDate','')>='2026-11-21' and
        current.get('editionType')=='regular'):
        stories=current.get('stories',[])
        if not (4<=len(stories)<=5):
            raise ValueError('New published edition has fewer than four stories')
        for story in stories:
            if story.get('imagePath')!=expected_path(current['editionDate'],story):
                raise ValueError('Missing or unexpected generated image path')
            rel=story['imagePath']
            source=root/rel
            if not valid_webp(source):
                raise FileNotFoundError('Published image is missing or invalid: '+rel)
            target=output/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
    # The standalone iOS and Android icons are built locally from the same
    # Moon / envelope / 9 artwork. No third-party image processing needed.
    from app_icon import render_icons
    render_icons(output / 'assets')
    for source in (root / 'data' / 'archive').glob('????-??-??.json'):
        shutil.copy2(source, output / 'data' / 'archive' / source.name)
    # Historical retrospective/monthly research stays in Git for audit,
    # but is no longer shipped to readers as an optional 30-day shelf.
    build_country_coverage(root, output)
    bundle_travel_photos(root, output)
    print('公開用サイトを生成しました: ' + str(output))
    return output


if __name__ == '__main__':
    home = Path(__file__).resolve().parent
    build(home, home / '_site')
