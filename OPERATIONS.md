# よる9じの世界便り — 運用手順

## いま稼働しているもの

- 読者サイト: https://ogasawaratouei1998-lgtm.github.io/yoru9-world-letter/
- ニュース候補の収集: `.github/workflows/collect-candidates.yml`。日本時間16:37に起動を予定。候補はGitHub Actionsの実行成果物として保存し、公開はしません。
- 記事の安全チェック: `publish_approved.py`。日本時間21:00より前、承認のない日、5本未満、出典情報や確認項目のない日は公開しません。
- 夜の公開予約: `.github/workflows/publish-nightly.yml`。毎日日本時間21:07ごろを予定。GitHub Actionsの混雑などで遅れる場合があります。
- 公開処理のテスト: `.github/workflows/test-publishing.yml`。例示記事により公開可否をチェックします。テストに合格してもニュースの事実が自動的に保証されるわけではありません。

## 重要: GitHub Pagesの公開方式

**2026-11-10にGitHub Actionsの「Deploy reader website」実行が成功しています。** 現在の公開サイトが引き続き表示されることを確認してください。もし今後の配信が反映されない場合は、GitHubリポジトリの **Settings → Pages → Build and deployment → Source** が **GitHub Actions** になっているか確認してください。

従来の `Deploy from a branch` 方式では、GitHub Actionsの `GITHUB_TOKEN` が保存したコミットだけではPagesのビルドが始まりません。新しい配信号はこのリポジトリの **Publish approved news at night (JST)** がGitHub Pagesへの直接デプロイも実行する設計です。

## 毎日の流れ

1. **候補を収集する。** GitHubのActionsから **Collect unverified news leads** の当日の成果物 `unverified-news-leads` をダウンロードし、中の `candidates.json` を取り出す。候補は**未確認**であり、掲載禁止。
2. **編集する。** `editor.html` をローカルのブラウザで開く。候補JSONを読み込み、元記事に加えて**独立した出典をもう1件以上**確認。事件性・深刻な被害・差別・プライバシー問題がないかチェック。報道内容とAIのジョークを明確に分け、5本を選ぶ。
3. **明示的に承認する。** 編集室で配信日（日本時間）と最終承認者を入力し、`YYYY-MM-DD.json` を保存する。ダウンロードされたファイルを読み直して内容を最終確認する。
4. **GitHubへ登録する。** リポジトリの `data/approved/` フォルダーを開き、Add file → Upload filesから該当日のJSONをアップロード。**21時より前に承認済みとして置く必要があります**。
5. **公開を確認する。** 21:07以降のGitHub Actions **Publish approved news at night (JST)** を確認。成功したら公開サイトの最新号とアーカイブを確認する。

21時を過ぎてから承認ファイルを置いた場合は、次の日の通常予約ではその前日の配信号は自動公開されません。手動でワークフローを実行し、同日中に公開してください。

## 安全上の重要事項

- **ニュースを自動で「真実」と判定する機能はありません。** 必ず人が原文を確認してください。URLが2件あるだけでも正確さは保証されません。
- **AIのジョークを自動生成するAPIは未接続です。** 編集時に人やChatGPTなどが準備し、出典事実と別に承認してください。
- 人の命・重大な被害・名誉・プライバシーを損なう内容は笑いのネタにしないでください。
- `data/approved/` はGitHubリポジトリ内では**公開情報**です。社外秘・個人情報を入れないでください。GitHub Actions方式でデプロイするサイトの成果物からは除外します。
- 当日の承認済み5本がない場合は、公開データを変更せず、直前の公開号（または創刊準備号）を維持します。
- 21:07はGitHub Actionsの起動予定であり、配信完了の保証時刻ではありません。プッシュ通知も未実装です。
