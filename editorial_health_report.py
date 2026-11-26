#!/usr/bin/env python3
"""Concise, private, count-only explanation of nightly editorial progress.

No article text, URLs, model prompt, individual names or unverified drafts are
included. A diagnostic is NEVER evidence that an issue was published.
"""
import json
import os
from pathlib import Path

PHASE_MESSAGES={
    "fresh_filter":"信頼済み媒体からの新着候補を選別中",
    "publisher_leads_unavailable":"7日以内の承認済み報道機関の記事候補がゼロ",
    "fetch_plan":"報道機関の記事を読み込む準備中",
    "body_fetch":"報道機関の記事を読み込み済み",
    "publisher_articles_unavailable":"本文を読める記事がゼロのため、AI編集を実行しない",
    "shortlist":"記事候補の優先順位を整理済み",
    "budget_blocked":"無料AIの実行時間が不足し、記事生成を停止",
    "model_quota_blocked":"無料AIの利用枠が不足し、記事生成を停止",
    "model_unavailable":"AI提供元の障害により編集を停止（記事不足とは別）",
    "draft":"記事の下書きを作成済み（未承認）",
    "draft_empty":"承認済み報道機関の記事から採用候補を生成できなかった",
    "audit":"日本語・ツッコミの編集審査を実施済み",
    "country_readiness":"国紹介・写真・クイズの整合性を審査中",
    "no_publishable_stories":"編集・国別素材審査を通過した記事がゼロのため前回号を維持",
    "selected":"公開候補を選定済み（実際の公開は別途確認）",
}
COUNTS=("fresh","fetchable_original_bodies","candidate_review_groups",
        "drafted","preflight_eligible","independent_approved",
        "country_ready_articles","selected_for_edition",
        "explicit_publisher_dates","local_screened","local_screen_preferred",
        "local_candidate_errors","local_empty_draft_responses","local_invalid_draft_responses",
        "source_groups_attempted","untried_source_groups_remaining")


def summarize_funnel(source):
    if not isinstance(source,dict):
        return "編集診断：記録がありません。配信成功とは判定しません。"
    phase=source.get("phase")
    if phase not in PHASE_MESSAGES:
        return "編集診断：不明な段階です。配信成功とは判定しません。"
    output=["### 世界便り・自動編集の診断",
            "**状態：** "+PHASE_MESSAGES[phase]]
    for key in COUNTS:
        value=source.get(key)
        if type(value) is int and 0<=value<=100000:
            output.append("- "+key+": "+str(value))
    # Rejections are internal fixed-code categories, never free-form reasons.
    rejected=source.get("rejection_reasons")
    if isinstance(rejected,dict):
        safe=[(key,value) for key,value in rejected.items()
              if isinstance(key,str) and key.replace("_","").isalnum()
              and key.isascii() and len(key)<=50
              and type(value) is int and 0<=value<=100000]
        for key,value in sorted(safe,key=lambda item:(-item[1],item[0]))[:5]:
            output.append("- rejection "+key+": "+str(value))
    output.append("編集診断は公開成功・失敗の確定通知ではありません。")
    return "\n".join(output)


def main():
    path=Path("data/editorial-funnel.json")
    try:
        report=summarize_funnel(json.loads(path.read_text(encoding="utf-8")))
    except (OSError,ValueError,UnicodeError):
        report=summarize_funnel(None)
    print(report)
    summary=os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as sink:
            sink.write(report+"\n")


if __name__=="__main__":
    main()
