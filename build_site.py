#!/usr/bin/env python3
"""Package ONLY the public reader assets for GitHub Pages deployment."""
from pathlib import Path
import shutil
import json
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

def bundle_travel_photos(root, output):
    """Download licensed Wikimedia photo previews at build time.

    Photos are served from GitHub Pages itself, avoiding mobile-browser
    hotlink restrictions. A failing upstream source never blocks news reading.
    """
    manifest = root / 'travel-stops.json'
    if not manifest.is_file():
        return 0
    stops = json.loads(manifest.read_text(encoding='utf-8'))
    downloaded = 0
    for key, stop in stops.items():
        asset = stop.get('photoAsset', '')
        url = stop.get('photo', '')
        if not re.fullmatch(r'assets/travel/[a-z0-9-]+\.jpg', asset):
            continue
        parts = urlparse(url)
        if parts.scheme != 'https' or parts.hostname != 'thumb.wikimedia.org' or not parts.path.startswith('/wikipedia/commons/'):
            continue
        target = output / asset
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            request = Request(url, headers={'User-Agent': 'Yoru9WorldLetter/1.0 (public educational travel preview; GitHub Pages)'})
            with urlopen(request, timeout=12) as response:
                payload = response.read(1_500_001)
                kind = response.headers.get('Content-Type', '')
            if not (payload.startswith(b'\xff\xd8\xff') and len(payload) >= 3000
                    and len(payload) <= 1_500_000 and 'image/' in kind):
                raise ValueError('not a valid small JPEG preview')
            target.write_bytes(payload)
            downloaded += 1
        except (OSError, ValueError) as exc:
            print(f'旅行写真を一時的に取得できませんでした: {key}: {exc}')
    print(f'旅行写真のサイト内保存：{downloaded}/{len(stops)} 件')
    if stops and not downloaded:
        raise RuntimeError('旅行写真が1枚も保存できませんでした。配信すると画像が欠けるため停止します。')
    return downloaded



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
    for source in (root / 'data' / 'archive').glob('????-??-??.json'):
        shutil.copy2(source, output / 'data' / 'archive' / source.name)
    bundle_travel_photos(root, output)
    print('公開用サイトを生成しました: ' + str(output))
    return output


if __name__ == '__main__':
    home = Path(__file__).resolve().parent
    build(home, home / '_site')
