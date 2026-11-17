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


def build(root, output):
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for relative in ('index.html', 'manifest.webmanifest', 'service-worker.js', 'notifications.js', 'notification-config.json', 'country-catalog.json', 'travel-stops.json', 'assets/icon.svg',
                     'data/current.json', 'data/archive/index.json', 'data/retrospective/2026-11-17.json'):
        source = root / relative
        if not source.is_file():
            raise FileNotFoundError(relative)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    # The standalone iOS and Android icons are built locally from the same
    # Moon / envelope / 9 artwork. No third-party image processing needed.
    from app_icon import render_icons
    render_icons(output / 'assets')
    for source in (root / 'data' / 'archive').glob('????-??-??.json'):
        shutil.copy2(source, output / 'data' / 'archive' / source.name)
    # Only publish explicitly audited monthly collections. Immutable source
    # files stay in Git, while the reader sees only recent collections.
    monthly_index = root / 'data/monthly/index.json'
    if monthly_index.exists():
        from monthly_research import safe_day, validate_story, REVIEW_METHOD, LEGACY_REVIEW_METHOD
        manifest = json.loads(monthly_index.read_text(encoding='utf-8'))
        if (manifest.get('status') != 'published-monthly-index'
                or not isinstance(manifest.get('issues'), list)):
            raise ValueError('invalid published monthly index')
        index_dest = output / 'data/monthly/index.json'
        index_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(monthly_index, index_dest)
        for record in manifest['issues']:
            date_str = record.get('date') if isinstance(record, dict) else None
            day = safe_day(date_str)
            if day is None or (date.today() - day).days > 400:
                continue
            source = root / 'data/monthly' / (date_str + '.json')
            if not source.is_file():
                raise FileNotFoundError('missing published monthly collection')
            document = json.loads(source.read_text(encoding='utf-8'))
            stories = document.get('stories')
            if (document.get('status') != 'published-monthly'
                    or document.get('collectionDate') != date_str
                    or document.get('reviewMethod') not in (REVIEW_METHOD, LEGACY_REVIEW_METHOD)
                    or not isinstance(stories, list) or not stories
                    or len(stories) > 3):
                raise ValueError('invalid monthly public collection')
            if any(not validate_story(story, story.get('verificationUrls', []), day)
                   for story in stories):
                raise ValueError('monthly collection failed independent-source validation')
            shutil.copy2(source, output / 'data/monthly' / source.name)
    bundle_travel_photos(root, output)
    print('公開用サイトを生成しました: ' + str(output))
    return output


if __name__ == '__main__':
    home = Path(__file__).resolve().parent
    build(home, home / '_site')
