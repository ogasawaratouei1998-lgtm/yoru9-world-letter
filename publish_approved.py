#!/usr/bin/env python3
"""Release only manually approved, fact-checked news editions after 21:00 JST."""
from __future__ import annotations
import argparse
from datetime import date, datetime, time, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from trusted_originals import trusted_original_domain, SINGLE_SOURCE_NOTE
from zoneinfo import ZoneInfo

JST = ZoneInfo('Asia/Tokyo')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
CATEGORIES = {'person', 'work', 'company', 'sports'}
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


NIGHT_MESSAGES = {
    'sports': [
        '勝負にも予定外はつきもの。今夜は自分への採点を少し休みましょう。',
        '思いどおりにならない一日も、最後まで過ごしたことに意味があります。',
        '世界の競技場でも予想外は起きる。あなたも今夜はひと休み。',
    ],
    'work': [
        '予定がひとつ狂った日も、今日をやり切ったことまで消えたりしません。',
        '思いどおりに進まない仕事は、あなたひとりの物語ではありません。',
        '机の上に残った仕事は、明日の自分と相談しても大丈夫。',
        '今日の反省会はここまで。温かい飲み物に、次の出番を譲りましょう。',
        '世界にも計画どおりにいかない日がある。今夜は少し力を抜いて。',
        '失敗を数えるより、今日ここまで来たことをひとつ覚えておこう。',
        'うまくできなかった場面だけが、今日のあなたのすべてではありません。',
        '仕事の続きを考えるのは、ひと晩眠ってからでも遅くありません。',
    ],
    'person': [
        '今日の勘違いも、いつか少し笑える思い出になるかもしれません。',
        'まちがえた自分にまで、厳しい採点をしなくていい夜です。',
        '思わぬ展開に出会った一日。まずは無事に帰ってきた自分におつかれさま。',
        'きれいにまとまらない日もあります。今夜はそのまま、おやすみなさい。',
        '誰かの失敗談を読んだあと、自分にも少し優しくなれますように。',
        '今日の小さなつまずきは、あなたの明日を決める判決ではありません。',
        '世界は予想外でいっぱい。あなたの今日も、きっとその一ページ。',
        '何もかも正解にしなくていい。夜は休むためにもあります。',
    ],
    'company': [
        '大きな組織でも予定が外れるのだから、今夜は自分を責めすぎずに。',
        '立派な計画にも「まさか」はあります。あなたの今日にも、おつかれさま。',
        '世界があちこちで試行錯誤している夜。焦らず眠っていいのです。',
        '大きな失敗を知ると、今日の小さな失敗を少し遠くから眺められます。',
        '想定外は世界共通。今夜のあなたには、静かな時間が似合います。',
        '明日の予定は明日のもの。今夜は心の会議を閉じましょう。',
        '世界の仕組みも完璧ではありません。あなたも完璧でなくて大丈夫。',
        '何事も計画どおりとはいかないから、今夜くらいは余白を残して。',
    ],
}

# Short comic fallbacks for future editions when the AI comedy editor cannot
# approve a line. Historical editions retain their original deterministic text.
COMIC_NIGHT_MESSAGES={
    'work': [
        '手順書の最後に「ただし、現実はアドリブ」と書き足したい。',
        '仕事の担当欄、たまに「その他、予想外」が勝手に増える。',
        '予定表に書き忘れた「まさか」が、今日も一番働いていた。',
    ],
    'company': [
        '計画書は完璧。でも現実は、勝手に別の台本を持ってくる。',
        '世界のマニュアル、最後のページは「そんなはずでは」に空けておこう。',
        '会議で決めた筋書きほど、現場のアドリブに弱かったりする。',
    ],
    'person': [
        '予定どおりならニュースにならない。今日も現実が台本を破った。',
        '世の中の予定表には、ときどき「番外編」が紛れ込む。',
        '「そんな予定はない」が、いちばん予定どおりに起こる。',
    ],
    'sports': [
        '作戦会議にいなかった「まさか」が、試合でいちばん目立っている。',
        '今日の試合、台本にない一行が一番の見せ場だった。',
        'きっちり組んだ作戦に限って、現実がアドリブを入れてくる。',
    ],
}

def nightly_message(edition_date, stories, recent_messages=()):
    """Pick a stable, non-repeating editorial line when AI text is unavailable."""
    from hashlib import sha256
    from difflib import SequenceMatcher
    categories = [story['category'] for story in stories]
    seed = int.from_bytes(sha256(edition_date.encode('ascii')).digest()[:8], 'big')
    category = categories[seed % len(categories)]
    options = (COMIC_NIGHT_MESSAGES if edition_date >= '2026-11-18' else NIGHT_MESSAGES)[category]
    ordered = options[seed % len(options):] + options[:seed % len(options)]
    for line in ordered:
        if all(SequenceMatcher(None,line,old).ratio() < 0.72 for old in recent_messages):
            return line
    return ordered[0]

def publication_nightly_message(data, edition_date, stories):
    """A closing gag is optional, never a reason to publish unrelated filler.

    Preserve archived-era behavior; new editions need a real incident anchor.
    Without a qualifying approved line, retain a clean neutral sign-off.
    """
    raw=data.get("nightlyMessage")
    if isinstance(raw,str):
        clean=raw.strip()
        if (20<=len(clean)<=110 and not any(c in clean for c in "<>\\r\\n")
                and not re.search(r"\\\\[rn]",clean)):
            if edition_date < "2026-11-18":
                return clean
            from nightly_quality import incident_specific_nightly_line
            if incident_specific_nightly_line(clean, stories):
                return clean
    return nightly_message(edition_date,stories) if edition_date < "2026-11-18" else ""


def recent_nightly_messages(root, edition_date, days=60):
    from datetime import timedelta
    today=date.fromisoformat(edition_date)
    messages=[]
    for file in (root/'data'/'archive').glob('????-??-??.json'):
        try:
            issue=json.loads(file.read_text(encoding='utf-8'))
            issue_date=date.fromisoformat(issue.get('editionDate',''))
            if issue.get('status')!='published' or not (today-timedelta(days=days)<=issue_date<today):
                continue
            line=issue.get('nightlyMessage')
            if isinstance(line,str) and line.strip():messages.append(line.strip())
        except (OSError,ValueError,TypeError):
            continue
    return messages

def validate_approved(data, expected_date):
    require(isinstance(data, dict), '配信号がJSONオブジェクトではありません')
    require(data.get('status') == 'approved', 'status が approved ではありません')
    require(data.get('editionDate') == expected_date, '配信日が承認ファイル名と一致しません')
    require(bool(DATE.fullmatch(expected_date)), '配信日が正しくありません')
    issue_day = date.fromisoformat(expected_date)
    edition_type = data.get('editionType', 'regular')
    require(edition_type in ('regular', 'special'), '配信号の種類が不正です')
    if edition_type == 'special':
        require('特集' in data.get('title', ''), '特集号のタイトルを明示してください')
        require(isinstance(data.get('specialReason'), str) and len(data['specialReason'].strip()) >= 15,
                '特集号には過去の報道を掲載する理由と説明が必要です')
    require(isinstance(data.get('title'), str) and 5 <= len(data['title'].strip()) <= 100, '配信号タイトルが必要です')
    require(data.get('editorApproved') is True and data.get('factChecked') is True and data.get('humorReviewed') is True,
            '編集承認・事実確認・ユーモア審査が未完了です')
    require(isinstance(data.get('approvedBy'), str) and len(data['approvedBy'].strip()) >= 2, '承認者名がありません')
    stories = data.get('stories')
    if edition_type == 'regular' and issue_day >= date(2026, 11, 17):
        # Three is the editorial goal, not a minimum or an exact quota.
        # The editorial process selects at most three from a larger vetted
        # candidate pool; release all 1-3 verified approved stories.
        require(isinstance(stories, list) and 1 <= len(stories) <= 3,
                '通常号は検証・編集承認済みのニュース1〜3本を公開します。0本と4本以上は公開用の最終選定を確認してください')
    else:
        # Historical regular issues and the five-article specials are immutable.
        require(isinstance(stories, list) and
                ((1 <= len(stories) <= 5) if edition_type == 'regular' else len(stories) == 5),
                '過去の通常号は1〜5本、特集号は5本の記事が必要です')
    ids, sources = set(), set()
    public_stories = []
    for i, story in enumerate(stories, 1):
        require(isinstance(story, dict), f'{i}本目の記事形式が不正です')
        for key in REQUIRED_STORY:
            value = story.get(key)
            require(isinstance(value, str) and bool(value.strip()), f'{i}本目の {key} が空です')
            require(len(value) <= (2000 if key == 'detail' else 600), f'{i}本目の {key} が長すぎます')
        # Preserve previously approved editions through 2026-11-16 without
        # silently rewriting their reporting. Enforce Japanese details for
        # newly approved editions starting 2026-11-17.
        if issue_day >= date(2026, 11, 17):
            require(bool(re.search(r'[ぁ-んァ-ヶ一-龯々]', story['detail'])),
                    f'{i}本目のdetailが日本語ではありません。日本語で事実確認してから承認してください')
        require(story['category'] in CATEGORIES, f'{i}本目のcategoryが不正です')
        reported = story['reported']
        require(bool(re.fullmatch(r'\d{4}[-.]\d{2}[-.]\d{2}', reported)), f'{i}本目の報道日の形式が不正です')
        reported_day = date.fromisoformat(reported.replace('.', '-'))
        delta_days = (issue_day - reported_day).days
        require(delta_days >= 0, f'{i}本目の報道日が配信予定日より未来です')
        if edition_type == 'regular':
            require(delta_days <= 7, f'{i}本目の報道が8日以上古いです。通常号には掲載せず特集号として明示してください')
        require(valid_url(story['sourceUrl']), f'{i}本目のsourceUrlが安全なHTTPS URLではありません')
        require(story.get('editorVerified') is True and story.get('humorSafe') is True,
                f'{i}本目は個別の事実確認・危害配慮が未承認です')
        if (issue_day >= date(2026, 11, 18) and
                data.get('approvedBy') == 'automated-two-stage-review'):
            require(story.get('editorQualityVerified') is True,
                    f'{i}本目は見出しの事実性・翻訳・法的表現・ユーモアの独立審査が未完了です')
            require(story.get('humanFailureVerified') is True and
                    isinstance(story.get('humanActor'), str) and
                    isinstance(story.get('humanMistake'), str),
                    f'{i}本目は人間の具体的な失敗が確認されていません')
            from country_codes import country_codes
            require(country_codes(story["country"]),
                    f'{i}本目の出来事が起きた国・地域を認識できません')
            from editorial_identity import (human_failure_rejection,
                                            comic_line_rejection,noncomic_incident_rejection)
            require(human_failure_rejection(story) is None,
                    f'{i}本目は人間の失敗中心のニュースではありません')
            require(noncomic_incident_rejection(story) is None,
                    f'{i}本目は深刻な事件であり、笑いの題材として不適切です')
            require(comic_line_rejection(story['quip']) is None,
                    f'{i}本目はツッコミとして成立していません')
        urls = story.get('verificationUrls')
        # Existing historical/special records retain their original two-source
        # contract. New regular issues may use ONE verified original publisher
        # if the separate AI fact review confirmed its actual article text.
        min_sources = 1 if edition_type == 'regular' and issue_day >= date(2026, 11, 17) else 2
        require(isinstance(urls, list) and len(urls) >= min_sources and all(valid_url(u) for u in urls),
                f'{i}本目は{min_sources}件以上の検証用HTTPS URLが必要です')
        require(story['sourceUrl'] in urls, f'{i}本目の出典が検証用URLに含まれていません')
        require(len(set(urls)) == len(urls), f'{i}本目の検証用URLが重複しています')
        domains = {urlsplit(u).hostname.lower().removeprefix('www.') for u in urls}
        if len(urls) == 1:
            require(trusted_original_domain(urls[0]),
                    f'{i}本目の単独報道元は審査済み媒体ではありません')
            require(story.get('sourceBasis') == 'original-report' and
                    story.get('originalReportingVerified') is True,
                    f'{i}本目の独自取材を独立審査で確認してください')
            require(story.get('attributionNote') == SINGLE_SOURCE_NOTE,
                    f'{i}本目の単独報道の注意書きがありません')
        else:
            require(len(domains) >= 2, f'{i}本目の複数出典は独立したドメインが必要です')
        require(story['id'] not in ids and story['sourceUrl'] not in sources, '記事IDまたは出典URLが重複しています')
        ids.add(story['id'])
        sources.add(story['sourceUrl'])
        # Editorial review metadata is kept in the repository, not public story JSON.
        public_story = {key: story[key].strip() for key in REQUIRED_STORY}
        # Readers can inspect supporting sources, without exposing private AI
        # verification prompts or editorial-review records.
        public_story['verificationUrls'] = list(urls)
        if len(urls) == 1:
            public_story['sourceBasis'] = 'original-report'
            public_story['attributionNote'] = SINGLE_SOURCE_NOTE
        if 'correctionNote' in story:
            note = story['correctionNote']
            require(isinstance(note, str) and 15 <= len(note.strip()) <= 250
                    and not any(ch in note for ch in '<>\r\n'),
                    f'{i}本目の編集訂正文が不正です')
            public_story['correctionNote'] = note.strip()
        if isinstance(story.get('flag'), str):
            public_story['flag'] = story['flag']
        if 'quipSecond' in story:
            second = story['quipSecond']
            require(isinstance(second, str),
                    f'{i}本目のquipSecondは文章で指定してください')
            require(second.strip() != story['quip'].strip(),
                    f'{i}本目のquipSecondが最初のツッコミと重複しています')
            require(15 <= len(second.strip()) <= 160,
                    f'{i}本目のquipSecondは15〜160文字で指定してください')
            require(not any(ch in second for ch in '<>\r\n'),
                    f'{i}本目のquipSecondに不正な制御文字またはHTML記号があります')
            public_story['quipSecond'] = second.strip()
        public_stories.append(public_story)
    return {'status': 'published', 'editionDate': expected_date, 'title': data['title'].strip(),
            'editionType': edition_type,
            'nightlyMessage': publication_nightly_message(data, expected_date, public_stories),
            **({'specialReason': data['specialReason'].strip()} if edition_type == 'special' else {}),
            'stories': public_stories,
            'nightQuote': nightly_line(expected_date, public_stories),
            'credits': 'Facts based on the cited reporting. AI one-liners are fictional humor, not news facts.'}



# Editorially curated closing lines. A stable date/story-based choice gives
# each released edition its own warm message without a new unverified AI call.
NIGHT_LINES = {
    'sports': [
        '思いどおりにならない日もある。今夜は自分にやさしく。',
        '勝敗のつかない悩みは、今夜のうちに決めなくてもいい。',
        '世界の競技場にも想定外がある。あなたもひと休み。',
    ],
    'work': [
        '仕事でつまずく日もある。世界のどこかでも、きっと同じ。',
        '予定どおりにいかない日も、今日を終えたなら十分です。',
        'ひとつの失敗で、今日のあなた全部は決まりません。',
        'うまくいかなかったことも、明日には少し違って見えるかも。',
    ],
    'person': [
        '思い違いは、誰にでもある。今夜は自分にもやさしく。',
        '今日の小さな失敗が、いつか笑い話になりますように。',
        '完璧じゃない一日にも、おやすみなさい。',
        '世界には、思いどおりにならない話がたくさんある。',
    ],
    'company': [
        '大きな組織だって、想定外に出会う。あなたも焦らなくていい。',
        '立派な計画にも、まさかは起こる。今夜はひと休み。',
        '世界が思いどおりにいかない夜も、眠っていい。',
        '失敗の規模は違っても、明日はまた始められる。',
    ],
}

def nightly_line(edition_date, stories):
    import hashlib
    key = edition_date + '|' + '|'.join(story['id'] for story in stories)
    digest = hashlib.sha256(key.encode('utf-8')).digest()
    category = stories[digest[0] % len(stories)]['category']
    lines = NIGHT_LINES[category]
    return lines[digest[1] % len(lines)]

def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def publish(root: Path, now: datetime, allow_early: bool = False):
    now = now.astimezone(JST)
    date = now.date().isoformat()
    if now.time() < time(21, 0) and not allow_early:
        print(f'まだ21時前です（日本時間 {now:%H:%M}）。公開しません。')
        return False
    approved_path = root / 'data' / 'approved' / f'{date}.json'
    if not approved_path.is_file():
        print(f'{date} の承認済み記事がありません。現在の公開号を保持します。')
        return False
    data = json.loads(approved_path.read_text(encoding='utf-8'))
    public_issue = validate_approved(data, date)
    from difflib import SequenceMatcher
    recent = recent_nightly_messages(root, date)
    proposed = public_issue['nightlyMessage']
    if proposed and any(SequenceMatcher(None, proposed, old).ratio() >= 0.72 for old in recent):
        # Published text is not reused just to fill a decorative slot.
        public_issue['nightlyMessage'] = (nightly_message(date, public_issue['stories'], recent)
                                          if date < '2026-11-18' else '')
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
    print(f'{date} の承認済みニュース{len(public_issue['stories'])}本を公開データに反映しました。')
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--now', help='テスト用の日時。例: 2026-11-10T21:05:00+09:00')
    parser.add_argument('--publish-now', action='store_true', help='明示的な即時公開指示がある場合に限り21時前の公開を許可')
    args = parser.parse_args(argv)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    require(now.tzinfo is not None, '--now にはタイムゾーンが必要です')
    publish(args.root, now, allow_early=args.publish_now)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print('公開を中止しました: ' + str(exc), file=sys.stderr)
        sys.exit(1)
