#!/usr/bin/env python3
"""Package ONLY the public reader assets for GitHub Pages deployment."""
from pathlib import Path
import shutil
import json
import re
import os
import hashlib
from datetime import date
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Bounded for the full 196-country photo catalog, including long travel essays.
MAX_PUBLIC_PHOTO_MANIFEST_BYTES = 8 * 1024 * 1024

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
    country_covers = set()
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
        if stop.get('coverOnly') is True:
            country_covers.add(asset)

    # Also prefetch sharp covers for the existing, source-checked portraits
    # (Spain/Japan/New Zealand and other older guides). Previously only items
    # tagged coverOnly got the 1280px version; several legacy portrait photos
    # were fetched at 500px and appeared blurry or disappeared on retina screens.
    page = root / 'index.html'
    if page.exists():
        prefix='const TODAY_COUNTRY_PHOTOS=Object.freeze('
        matches=[line for line in page.read_text(encoding='utf-8').splitlines()
                 if line.startswith(prefix)]
        # Isolated test fixtures may contain a minimal reader stub with no
        # country-photo registry. Full production site validates source data
        # separately; do not reject minimal fixtures over cover hints.
        if matches:
            if len(matches)!=1 or not matches[0].endswith(');'):
                raise ValueError('Country cover registry malformed')
            registry=json.loads(matches[0][len(prefix):-2])
            for candidates in registry.values():
                for photo in candidates:
                    asset=photo.get('asset')
                    if not photo.get('avoidCover') and asset in required:
                        country_covers.add(asset)

    # Strong native-resolution requirements apply to currently displayed
    # country portraits. Other vetted historical postcards may temporarily
    # retain their previously published 500px files under Wikimedia throttling;
    # they MUST be upgraded before becoming a new issue's active cover.
    active_covers=set(country_covers)
    active_photos=set(required)
    current_path=root/'data/current.json'
    if current_path.is_file() and page.is_file() and matches:
        from country_codes import country_codes
        current_issue=json.loads(current_path.read_text(encoding='utf-8'))
        active_codes={code for story in current_issue.get('stories',[])
                      for code in country_codes(story.get('country'))}
        active_photos={stop.get('photoAsset') for stop in stops.values()
                       if set(country_codes(stop.get('country')))&active_codes}
        active_covers={photo.get('asset') for code in active_codes
                       for photo in registry.get(code,[])
                       if not photo.get('avoidCover') and
                       photo.get('asset') in country_covers}
    # GitHub Actions can restore this cache across otherwise ephemeral builds.
    # Cache keys include the verified Wikimedia URL AND the license/author
    # provenance. A changed photo or country-cover role invalidates the entry.
    # Empty/unconfigured cache preserves the original download path.
    cache_setting=os.getenv("YORU9_PHOTO_CACHE_DIR","").strip()
    cache_root=Path(cache_setting) if cache_setting else None
    if cache_root is not None:
        cache_root.mkdir(parents=True,exist_ok=True)
        from check_release_candidate import jpeg_dimensions
    reused=0
    cache_files={}
    failures = []
    commons_throttled = False
    for asset, url in required.items():
        target = output / asset
        target.parent.mkdir(parents=True, exist_ok=True)
        # Never mistake a leftover image from an earlier build for one
        # that passed the present manifest/quality validation.
        target.unlink(missing_ok=True)
        cover=asset in country_covers
        cache_file=None
        if cache_root is not None:
            # Each asset is validated against the MANIFEST in every build;
            # only its previously downloaded image bytes may be reused.
            provenance=next(stop for stop in stops.values()
                            if stop["photoAsset"]==asset)
            identity={"asset":asset,"url":url,"page":provenance["photoPage"],
                      "author":provenance.get("author"),"license":provenance.get("license"),
                      "licenseUrl":provenance.get("licenseUrl"),
                      "country":provenance.get("country"),"place":provenance.get("place"),
                      "cover":cover}
            digest=hashlib.sha256(json.dumps(identity,sort_keys=True,
                               ensure_ascii=False).encode("utf-8")).hexdigest()
            cache_file=cache_root/(digest+".jpg")
            cache_files[asset]=cache_file
            if cache_file.is_file():
                try:
                    size=cache_file.stat().st_size
                    if not 3000<=size<=2_000_000:
                        raise ValueError("cached image size invalid")
                    with cache_file.open("rb") as src:
                        if src.read(3)!=b"\xff\xd8\xff":
                            raise ValueError("cached JPEG header invalid")
                    w,h=jpeg_dimensions(cache_file)
                    if ((w<1000 or h<540) if asset in active_covers else
                            (w<330 or h<200) if asset in active_photos else
                            (w<300 or h<140)):
                        raise ValueError("cached image resolution inadequate")
                    shutil.copyfile(cache_file,target)
                    reused+=1
                    continue
                except (OSError,ValueError):
                    cache_file.unlink(missing_ok=True)
        # Country-portrait covers are shown prominently on retina phones.
        # Package a 1280px licensed thumbnail locally when Wikimedia provides
        # one; 500px and 330px originals remain safe fallback sources.
        # No third-party URL is needed to display a successful bundled cover.
        large = url.replace('/500px-', '/1280px-')
        paths = ([large, large.replace('https://thumb.wikimedia.org/', 'https://upload.wikimedia.org/')]
                 if asset in country_covers and large != url else []) + [
            url,
            url.replace('https://thumb.wikimedia.org/', 'https://upload.wikimedia.org/'),
            url.replace('/500px-', '/330px-'),
            url.replace('https://thumb.wikimedia.org/', 'https://upload.wikimedia.org/').replace('/500px-', '/330px-'),
        ]
        last_error = 'Wikimedia rate limited; deferred until a later build' if commons_throttled else 'no sources'
        for candidate in (() if commons_throttled else dict.fromkeys(paths)):
            try:
                request = Request(candidate, headers={'User-Agent': 'Yoru9WorldLetter/1.1 (educational CC photo previews; GitHub Pages)'})
                with urlopen(request, timeout=20) as response:
                    payload = response.read(2_000_001)
                    kind = response.headers.get('Content-Type', '')
                if not (payload.startswith(b'\xff\xd8\xff') and 3000 <= len(payload) <= 2_000_000
                        and 'image/' in kind):
                    raise ValueError('response was not a valid JPEG preview')
                target.write_bytes(payload)
                if cache_file is not None:
                    try:
                        w,h=jpeg_dimensions(target)
                        if (w<1000 or h<540) if cover else (w<330 or h<200):
                            raise ValueError("photo dimensions too small")
                    except (OSError,ValueError) as exc:
                        target.unlink(missing_ok=True)
                        raise ValueError("downloaded JPEG dimensions invalid") from exc
                    # The cache is an optimization, not a replacement for
                    # the actual image provenance and pixel-quality gate.
                    shutil.copyfile(target,cache_file)
                break
            except HTTPError as exc:
                last_error = str(exc)
                if exc.code == 429:
                    # Respect the upstream restriction; do not immediately try
                    # alternate hosts or widths against the same service.
                    commons_throttled = True
                    break
            except (OSError, ValueError) as exc:
                last_error = str(exc)
        if not target.exists():
            failures.append(f'{asset}: {last_error}')
    # One trusted recovery source: the current live GitHub Pages build.
    # Reuse only if its published photo manifest confirms EXACTLY the same
    # Commons photo, author and license as the locally reviewed manifest.
    # Never substitute a new or unrelated picture when Wikimedia is throttled.
    recovered=0
    if failures and cache_root is not None:
        public_base='https://ogasawaratouei1998-lgtm.github.io/yoru9-world-letter/'
        try:
            with urlopen(Request(public_base+'travel-stops.json',
                         headers={'User-Agent':'Yoru9WorldLetter/1.1'}),timeout=12) as response:
                raw=response.read(MAX_PUBLIC_PHOTO_MANIFEST_BYTES+1)
            if len(raw)>MAX_PUBLIC_PHOTO_MANIFEST_BYTES:
                raise ValueError('published photo manifest exceeds bounded size')
            prior=json.loads(raw.decode('utf-8'))
            if not isinstance(prior,dict):
                raise ValueError('published photo manifest is malformed')
        except (OSError,ValueError,UnicodeError,TypeError):
            prior={}
        remaining=[]
        for problem in failures:
            asset=problem.split(': ',1)[0]
            selected=next((p for p in stops.values()
                           if p.get('photoAsset')==asset),None)
            matching=any(
                isinstance(p,dict) and selected is not None and
                all(p.get(field)==selected.get(field) for field in
                    ('photoAsset','photo','photoPage','author','license','licenseUrl',
                     'country','place'))
                for p in prior.values())
            if not matching:
                remaining.append(problem)
                continue
            target=output/asset
            try:
                # asset has already passed a strict local-path regexp; URLs
                # cannot point to a remote host selected by news or users.
                with urlopen(Request(public_base+asset,
                             headers={'User-Agent':'Yoru9WorldLetter/1.1'}),timeout=12) as response:
                    payload=response.read(2_000_001)
                    kind=response.headers.get('Content-Type','')
                if not (payload.startswith(b'\xff\xd8\xff') and
                        3000<=len(payload)<=2_000_000 and 'image/' in kind):
                    raise ValueError('published photo bytes are not JPEG')
                target.write_bytes(payload)
                width,height=jpeg_dimensions(target)
                if ((width<1000 or height<540) if asset in active_covers
                        else (width<330 or height<200) if asset in active_photos
                        else (width<300 or height<140)):
                    raise ValueError('published photo below native pixel requirement: '+
                                     str(width)+'x'+str(height))
                shutil.copyfile(target,cache_files[asset])
                recovered+=1
            except (OSError,ValueError) as exc:
                target.unlink(missing_ok=True)
                # Diagnostics are bounded and contain no credentials or
                # publisher article content: only an image path and failure.
                remaining.append(problem+'; published copy unavailable: '+
                                 type(exc).__name__+': '+str(exc)[:110])
        failures=remaining
    print(f'旅行写真のサイト内保存：{len(required) - len(failures)}/{len(required)} 件'
          f'（キャッシュ再利用 {reused} 件、公開済み写真から復旧 {recovered} 件）')
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
    # Country JSON is editorial source-of-truth; no unreviewed drift ships.
    if (root / 'country-content.json').is_file():
        from country_content import check_country_content
        check_country_content(root)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for relative in ('index.html', 'manifest.webmanifest', 'service-worker.js', 'notifications.js', 'world-passport.js', 'notification-config.json', 'country-catalog.json', 'country-highlights.json', 'travel-stops.json', 'assets/icon.svg', 'assets/reading-focus.css',
                     'data/current.json', 'data/archive/index.json', 'assets/world-today-illustrated.svg'):
        source = root / relative
        if not source.is_file():
            raise FileNotFoundError(relative)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    # The full editorial reader has the canonical country manifest. Lightweight
    # build fixtures deliberately use a minimal index and should remain valid.
    if (root / 'country-content.json').is_file():
        from reader_asset_split import split_reader_assets
        split_reader_assets(output)
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
    # Free illustration mode: only bundled SVG news artwork is published.
    # Retain the four-story safeguard without requiring external image APIs.
    current=json.loads((root/'data/current.json').read_text(encoding='utf-8'))
    if (current.get('editionDate','')>='2026-11-21' and
        current.get('editionType')=='regular'):
        if not (4<=len(current.get('stories',[]))<=5):
            raise ValueError('New published edition has fewer than four stories')
    # Old image URLs in archived JSON fall back to existing news SVGs.
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
