#!/usr/bin/env python3
"""Release only manually approved, fact-checked news editions after 21:00 JST."""
from __future__ import annotations
import argparse
from datetime import datetime, time, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

JST = ZoneInfo('Asia/Tokyo')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
CATEGORIES = {'person', 'work', 'company'}
REQUIRED_STORY = ('id', 'country', 'category', 'categoryLabel', 'label', 'title', 'summary', 'detail', 'quip', 'sourceName', 'sourceUrl', 'reported')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_url(url):
    if not isinstance(url, str) or len(url) > 1000:
        return False
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and bool(p.hostname) and not p.username and not p.password and (p.port is None or p.port == 443)
    except ValueError:
        return False


def validate_approved(data, expected_date):
    require(isinstance(data, dict), '配信号がJSONオブジェクトではありません')
    require(data.get('status') == 'approved', 'status が approved ではありません')
    require(data.get('editionDate') == expected_date, '配信日が承認ファイル名と一致しません')
    require(bool(DATE.fullmatch(expected_date)), '配信日が正しくありません')
    require(isinstance(data.get('title'), str) and 5 <= len(data['title'].strip()) <= 100, '配信号タイトルが必要です')
    require(data.get('editorApproved') is True and data.get('factChecked') is True and data.get('humorReviewed') is True,
            '編集承認・事実確認・ユーモア審査が未完了です')
    require(isinstance(data.get('approvedBy'), str) and len(data['approvedBy'].strip()) >= 2, '承認者名がありません')
    stories = data.get('stories')
    require(isinstance(stories, list) and len(stories) == 5, '承認済みの記事が5本必要です')
    ids, sources = set(), set()
    public_stories = []
    for i, story in enumerate(stories, 1):
        require(isinstance(story, dict), f'{i}本目の記事形式が不正です')
        for key in REQUIRED_STORY:
            value = story.get(key)
            require(isinstance(value, str) and bool(value.strip()), f'{i}本目の {key} が空です')
            require(len(value) <= (2000 if key == 'detail' else 600), f'{i}本目の {key} が長すぎます')
        require(story['category'] in CATEGORIES, f'{i}本目のcategoryが不正です')
        require(valid_url(story['sourceUrl']), f'{i}本目のsourceUrlが安全なHTTPS URLではありません')
        require(story.get('editorVerified') is True and story.get('humorSafe') is True,
                f'{i}本目は個別の事実確認・危害配慮が未承認です')
        urls = story.get('verificationUrls')
        require(isinstance(urls, list) and len(urls) >= 2 and all(valid_url(u) for u in urls),
                f'{i}本目は2件以上の検証用HTTPS URLが必要です')
        require(story['sourceUrl'] in urls, f'{i}本目の出典が検証用URLに含まれていません')
        require(len(set(urls)) == len(urls), f'{i}本目の検証用URLが重複しています')
        require(story['id'] not in ids and story['sourceUrl'] not in sources, '記事IDまたは出典URLが重複しています')
        ids.add(story['id'])
        sources.add(story['sourceUrl'])
        # Editorial review metadata is kept in the repository, not public story JSON.
        public_stories.append({key: story[key].strip() for key in REQUIRED_STORY} |
                              ({'flag': story['flag']} if isinstance(story.get('flag'), str) else {}))
    return {'status': 'published', 'editionDate': expected_date, 'title': data['title'].strip(), 'stories': public_stories,
            'credits': 'Facts based on the cited reporting. AI one-liners are fictional humor, not news facts.'}


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def publish(root: Path, now: datetime):
    now = now.astimezone(JST)
    date = now.date().isoformat()
    if now.time() < time(21, 0):
        print(f'まだ21時前です（日本時間 {now:%H:%M}）。公開しません。')
        return False
    approved_path = root / 'data' / 'approved' / f'{date}.json'
    if not approved_path.is_file():
        print(f'{date} の承認済み記事5本がありません。現在の公開号を保持します。')
        return False
    data = json.loads(approved_path.read_text(encoding='utf-8'))
    public_issue = validate_approved(data, date)
    current_path = root / 'data' / 'current.json'
    current = json.loads(current_path.read_text(encoding='utf-8')) if current_path.exists() else {}
    old_date = current.get('editionDate') or ''
    require(not old_date or old_date <= date, '現在より古い配信号で上書きすることは禁止です')
    archive_path = root / 'data' / 'archive' / f'{date}.json'
    if archive_path.exists():
        require(json.loads(archive_path.read_text(encoding='utf-8')) == public_issue,
                '同じ日付の公開号が既に存在し、内容が違います。無断の差し替えを中止しました')
        if current == public_issue:
            print('この配信号はすでに公開済みです。変更しません。')
            return False
    index_path = root / 'data' / 'archive' / 'index.json'
    index = json.loads(index_path.read_text(encoding='utf-8')) if index_path.exists() else {'issues': []}
    issues = [item for item in index.get('issues', []) if isinstance(item, dict) and item.get('date') != date]
    issues.append({'date': date, 'title': public_issue['title']})
    issues.sort(key=lambda item: item['date'], reverse=True)
    atomic_json(archive_path, public_issue)
    atomic_json(index_path, {'issues': issues, 'timeZone': 'Asia/Tokyo', 'releaseTime': '21:00'})
    atomic_json(current_path, public_issue)
    print(f'{date} の承認済みニュース5本を公開データに反映しました。')
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--now', help='テスト用の日時。例: 2026-11-10T21:05:00+09:00')
    args = parser.parse_args(argv)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    require(now.tzinfo is not None, '--now にはタイムゾーンが必要です')
    publish(args.root, now)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print('公開を中止しました: ' + str(exc), file=sys.stderr)
        sys.exit(1)
