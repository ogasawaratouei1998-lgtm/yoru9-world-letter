#!/usr/bin/env python3
"""Alert GitHub Actions if an approved JST nightly issue was not released."""
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import sys

JST = ZoneInfo("Asia/Tokyo")


def check_release(root: Path, now: datetime):
    now = now.astimezone(JST)
    issue_date = now.date().isoformat()
    if now.time() < time(21, 30):
        return True, "21:30前のため監視のみスキップ"
    approved = root / "data" / "approved" / (issue_date + ".json")
    if not approved.is_file():
        return True, "今日の承認済み記事が未登録。これは配信失敗とは判定しません"
    current_file = root / "data" / "current.json"
    if not current_file.is_file():
        return False, "承認済み記事がありますが current.json がありません"
    current = json.loads(current_file.read_text(encoding="utf-8"))
    approved_data=json.loads(approved.read_text(encoding="utf-8"))
    expected_count=len(approved_data.get("stories",[]))
    kind=approved_data.get("editionType","regular")
    if kind=="special":
        valid_count=(expected_count>=1 if issue_date>="2026-11-23"
                     else expected_count==5)
    elif kind=="regular":
        # Current editions have no fixed count; historic editions retain
        # their original contract for archive consistency.
        if issue_date >= "2026-11-21":
            valid_count=expected_count>=1
        elif issue_date >= "2026-11-19":
            valid_count=1<=expected_count<=5
        else:
            valid_count=1<=expected_count<=3
    else:
        valid_count=False
    if not valid_count:
        return False, "承認済み記事数が配信ルールを満たしません"
    if not (current.get("status") == "published" and
            current.get("editionDate") == issue_date and
            isinstance(current.get("stories"), list) and
            len(current["stories"]) == expected_count):
        return False, "承認済み記事があるのに今日の公開号がありません"
    archive = root / "data" / "archive" / (issue_date + ".json")
    if not archive.is_file():
        return False, "今日のアーカイブが欠落しています"
    index_file = root / "data" / "archive" / "index.json"
    if not index_file.is_file() or not any(
        x.get("date") == issue_date
        for x in json.loads(index_file.read_text(encoding="utf-8")).get("issues", [])
    ):
        return False, "アーカイブ一覧に今日の公開号がありません"
    archived=json.loads(archive.read_text(encoding="utf-8"))
    if archived!=current:
        return False, "公開号とアーカイブが一致していません"
    return True, f"今日の承認済み{expected_count}本が公開データとアーカイブに反映されています"


def main():
    ok, message = check_release(Path(__file__).resolve().parent, datetime.now(timezone.utc))
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
