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
    for relative in ('index.html', 'manifest.webmanifest', 'service-worker.js', 'notifications.js', 'notification-config.json', 'country-catalog.json', 'travel-stops.json', 'assets/icon.svg',
                     'data/current.json', 'data/archive/index.json', 'assets/world-today-illustrated.svg'):
        source = root / relative
        if not source.is_file():
            raise FileNotFoundError(relative)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
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
