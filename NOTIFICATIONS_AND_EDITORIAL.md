# 新機能の導入手順：通知と編集下書き（2026-11-11）

## 今どこまで動いているか

| 機能 | 現在 |
|---|---|
| 世界10地域のニュース候補収集 | 自動実行を確認済み |
| 未確認候補の編集用整理 | 自動実行を確認済み。事実確認とは別 |
| AIによる日本語ツッコミ案 | **手動起動コード＋事前オプトイン型の自動実行コード**。無料モデル用APIキーは未登録・実行未確認 |
| プッシュ通知の受信画面、Service Worker | GitHubに実装済み。バックエンド未接続のため通知ボタンは表示しない |
| 読者への実際のプッシュ通知 | **未稼働**。安全なバックエンド・鍵・購読者データベースが必要 |
| AI・人間による検証・公開 | 未確認記事は一切自動承認・自動公開しない。編集者による確認と承認が必要 |

## 料金を発生させない編集工程

`Collect unverified news leads` が、候補75件のURLに加えて `data/editorial-inbox.json` を生成します。公開サイトには置かず、GitHub Actionsの実行結果（`unverified-news-leads`）として提供します。

- 報道日の推定値を解析し、7日より古い候補を除外
- 国・地域ごとに6件を上限とする偏りの緩和
- タイトルに重大な人的被害を示す語があるものを暫定除外（漏れがあるので必ず人が確認）
- 原文の出典元、推定報道日、検索URL、確認チェックを付与
- `factStatus: "NOT_VERIFIED"` として保存（**自動事実確認ではありません**）

`editor.html` で該当候補を読み込み、実際に報道機関の本文と独立した一次・二次資料を読み、関係者への被害がないことを確かめてください。出典URLがGoogle Newsのリダイレクトなら、**本来の報道機関のリンクを確認・登録し直してください**。

## AIのツッコミ案を使う場合（任意・料金注意）

[Actions → Suggest AI quips for editor review (manual, free/paid choice)](https://github.com/ogasawaratouei1998-lgtm/yoru9-world-letter/actions/workflows/suggest-ai-quips.yml) に、運営者が明示的に操作したときだけ実行するプログラムを配置しています。

**無料モデルの選択肢を追加しました。** OpenRouterでAPIキーを作成し、GitHub Secretsの `OPENROUTER_API_KEY` に保存すると、手動ワークフローで `openrouter-free` を選べます。現在の無料モデルのトークン価格は0ドルですが、モデルの品質・上限・提供状況は変わり得ます。APIに渡すのは公表済み見出しとURLのみで、機密情報は入力しないでください。

さらに、[Optional automatic free AI draft after research](https://github.com/ogasawaratouei1998-lgtm/yoru9-world-letter/actions/workflows/optional-ai-draft.yml) も用意しました。GitHub Secrets `OPENROUTER_API_KEY` を設定し、リポジトリの Actions Variables に `AI_AUTODRAFT_ENABLED=true` と明示的に登録したとき**だけ**、ニュース候補の収集成功後に無料モデルを自動呼び出しします。**現在はオフ**です。

OpenAIの有料モデルを選ぶ場合は、別途OpenAI API利用登録、料金・利用上限の確認、GitHub Actions Secretsへの `OPENAI_API_KEY` 登録が必要です。**ChatGPT Plus等の契約とは別料金です。** 有料モデルは手動実行でのみ選択できます。APIキーをGitHubのコードやチャットに貼り付けないでください。

本ワークフローは最新の候補を最大12件読み込み、無料モデル `openrouter/free` または任意の有料モデル `gpt-5.4-mini` で、日本語の短いジョーク案・気を付ける点・追加調査の質問を生成し、`AI-draft-ideas-UNVERIFIED` 成果物に保存します。**採用も公開も自動では行いません。** ニュース見出ししか確認していないため、AIの出力を「事実確認済み」と扱ってはいけません。生成物を使う場合、原文を読んだ編集者が修正してください。

## プッシュ通知：仕組みと必要な追加設定

iPhone/iPad（iOS/iPadOS 16.4以降）では、アプリをホーム画面に追加して開いた場合に通知を有効化できます。PCや対応Androidブラウザーでも、ユーザーの明示的な許可が必要です。

今のGitHub Pagesは静的サイトです。そのため、通知用の**別バックエンド**と購読データの保存先が必要です。専用のサーバーレスDB/関数サービスなどに構築します。すでに他の用途のデータを保存しているプロジェクトへ許可なく混在させないでください。

### バックエンドとの公開インターフェース

- `POST https://<backend>/subscribe`：`{"subscription":<PushSubscription.toJSON()>}` を受け、HTTPSプッシュ先・p256dh/auth鍵の形式を検証して**非公開のデータベース**に登録。リクエストサイズ・送信元・IPレートを制限します
- `POST https://<backend>/unsubscribe`：`{"endpoint":"https://..."}` を受け、その端末の購読を削除。購読停止は送信元確認と必要な認証を実装します
- `POST https://<backend>/dispatch`：GitHub Actionsが `Authorization: Bearer <PUSH_DISPATCH_TOKEN>` を付けて送ります。送信先は登録済み端末のみ。受信した `editionDate` ごとに原子的に**重複配信を防止**し、無効になったプッシュ先を削除します

**注意**：このインターフェースは実装仕様です。現時点では外部サーバーにはデプロイしていません。Web PushのVAPID秘密鍵・購読一覧・トークンをGitHub Pagesや公開リポジトリに保存してはいけません。

### 実際に有効にする順番

1. 専用の通知バックエンドと非公開DBを用意し、VAPID鍵ペアを生成する。**秘密鍵はバックエンドのみ**へ格納。
2. 上記3つのエンドポイント、CORS、レート制限、購読解除、無効購読の消去、重複配信防止をサーバーに実装・テストする。
3. GitHub Actions Secretsに `PUSH_DISPATCH_URL` （サーバーの /dispatch URL）と `PUSH_DISPATCH_TOKEN` を登録する。鍵をコードに書かない。
4. `notification-config.json` の `enabled` を `true` にし、**公開してよい** `backendUrl` （/subscribe と /unsubscribe の前まで）と `vapidPublicKey` のみを入れる。この設定を公開するとボタンが初めて表示されます。
5. 実機で登録、21時台の正常公開後の通知、タップ時のサイト表示、解除を検証する。

バックエンド未稼働のまま `enabled:true` にしてはいけません。GitHub Pagesのファイルを変更するだけで配信できるわけではありません。

## 安全設計

- 通知は **正式な配信号がGitHub Pagesへのデプロイに成功した後** だけ送信を試みます。バックエンド未設定では静かにスキップします。
- 端末ごとに許可と解除が可能です。通知購読URLは機微な識別子なので秘匿が必要です。
- GitHub Actionsのリトライ時に同じ日付の通知を連投しないよう、送信側のバックエンドには必ず重複制御を実装してください。
- AIの提案を受けても、`data/approved/` への**自動書き込みは行いません**。真偽・独立性・人への配慮の最終承認は人間が担当します。
- 有料APIは常に手動起動のみとし、自動実行は `openrouter/free` 限定かつ変数による明示的なオプトインでしか有効にしません。いずれも秘密鍵は公開リポジトリやクライアントへ送信しないでください。
