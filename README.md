# よる9じの世界便り

> ニュースは実話、ツッコミ担当はAI。世界の「まさか」を、今夜も。

[公開サイト](https://ogasawaratouei1998-lgtm.github.io/yoru9-world-letter/)

無料・非営利のニュースサイト。個人の想像を絶する大失敗を最優先し、原文の事実とAIの創作ツッコミを区別する。審査合格が1本以上なら固定本数・上限なしで公開、0本なら前号を維持する。

## 現行の指示

- [OPERATIONS.md](OPERATIONS.md)：日常運用・開発・公開品質・国別素材の正式な規則。朝から編集、記事完成後に該当国のみ準備、21:00公開目標。
- [EDITORIAL_PROMISE.md](EDITORIAL_PROMISE.md)：記事とユーモアの編集理念。
- [NOTIFICATIONS_AND_EDITORIAL.md](NOTIFICATIONS_AND_EDITORIAL.md)：通知インターフェース等の技術資料。
- 196カ国・地域は地理索引。国別コンテンツの事前整備はニュース公開の条件ではない。未承認素材は表示せず、既存の承認済み素材を再利用する。
- 過去の改善経緯や一回限りの指示はGit履歴を参照する。現行方針に読み替えず、再実施しない。

## 構成

- collect_candidates.py / editorial_discovery.py：未確認ニュース発掘と優先順位。
- auto_editorial.py / local_editorial.py / editorial_dates.py：承認済み報道機関の本文から直接日本語原稿とツッコミを作成し、当サイトの編集品質のみ審査。報道の再検証は行わない。
- release_contract.py / stage_review.py / publish_approved.py：当日号の安全な引き継ぎと21時ゲート。
- country-content.json / country-catalog.json：国別編集原本と地理索引。python country_content.py --sync で生成する。
- research_article_countries.py / country_editorial_queue.py：記事起点の補充対象と調査候補。自動承認ではない。
- reader_sources/：画面の編集原本。python reader_source.py --sync で index.html を生成する。
- build_site.py / check_release_candidate.py / check_public_country_release.py：公開用ビルドと前後検査。
- data/current.json / data/archive/：公開号。data/approved/：承認用データ（Publicリポジトリのため閲覧可能だがサイトには同梱しない）。
- send_release_notice.py：公開確認後の通知。サーバー受理と端末受信は別。

## 検証

python -m unittest discover -s tests -v
python country_content.py --check
python reader_source.py --check
python build_site.py
python check_release_candidate.py --site _site
bash run_mobile_preflight.sh

詳細・安全要件は OPERATIONS.md を参照。自動配信の成功は実運用ログで判定する。CI合格だけでは証明にならない。
