# よる9じの世界便り — 通知バックエンド導入手順

**2026年11月11日現在:** 専用Supabase Freeプロジェクト `yoru9-push` を東京リージョンに新規作成し、RLS付きDBスキーマとEdge Function `yoru9-push` を導入しました。プロジェクトIDは `kdvkbkdfnrwvrbugpnaq` です。[Supabaseダッシュボード](https://supabase.com/dashboard/project/kdvkbkdfnrwvrbugpnaq) で状態を確認できます。**VAPID秘密鍵・認証トークン・GitHub Actions Secretsは未登録で、読者への通知は未稼働です。** 既存の研究用DBには変更していません。

## 専用環境に配置するもの

- push-backend/schema.sql：3つのテーブルと匿名の登録回数を制限するSQL関数。全テーブルでRLSを有効にし、anon / authenticated のデータアクセスを禁止
- push-backend/index.ts：Supabase Edge Function yoru9-push
- push-backend/validation.ts：ブラウザ通知の送信先のホワイトリスト、購読データの検査、JWTではなく送信トークンによる認可
- push-backend/validation_test.ts：Denoで実行する基本セキュリティテスト
- 通知送信のライブラリ：@mmmike/web-push 1.5.0、Supabase JS 2.119.0（固定バージョン）

## 専用プロジェクトの設定

1. **完了:** 専用Supabase Freeプロジェクトに schema.sql をマイグレーションとして適用しました。3テーブルはRLS有効で匿名・通常認証ユーザーの権限はありません。
2. **完了:** Edge Function yoru9-push を verify_jwt=false でデプロイしました。匿名端末が使う subscribe / unsubscribe は内部でOrigin、レート制限、データの正当性を検査し、配信のdispatchは最低32文字のBearerトークンで認証します。
3. Edge FunctionのSecretsに VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT, PUSH_DISPATCH_TOKEN, PUSH_RATE_SALT を登録します。VAPID_SUBJECTは実際に運営者が確認できる mailto: のメールアドレスにしてください。
4. PUSH_SIGNUPS_ENABLED=true を設定して初めて端末登録を受付けます。それまでは503を返します。
5. GitHub Actions Secretsに PUSH_DISPATCH_URL と PUSH_DISPATCH_TOKEN を登録します。送信先URLは https://専用プロジェクトID.supabase.co/functions/v1/yoru9-push/dispatch です。
6. GitHubの notification-config.json に公開可能な backendUrl、vapidPublicKey を設定し、最後に enabled=true にします。
7. テスト端末で同意、登録、公開後の通知受信、通知タップ、登録解除を確認します。iPhoneはホーム画面に追加したWebアプリとして起動します。

秘密鍵、購読者のエンドポイント、GitHub Actionsトークンは公開ファイルに置かないでください。

## セキュリティと無料枠の限界

- Supabase Freeは現在2つのアクティブプロジェクトまで。無料プランの非アクティブなプロジェクトは停止する場合があり、必ず届く通知を保証できません。
- 受信登録のブラウザ通知サービスはApple、Mozilla、Googleなど特定のHTTPSホストのみに限定しています。新規の通知サービスは追加審査が必要です。
- 送信処理は最大200端末まで。超える場合は部分配信せずエラーにします。大規模運用前にキュー型配信へ変更してください。
- 同じ発行日の重複通知はDB上の一意キーで防止しています。途中の失敗、再送、受信端末での到達保証は別の課題です。
- 登録APIには簡易なレート制限があります。公開後の大量不正登録にはTurnstileなどのbot対策も検討してください。
- 全購読情報は専用DBでのみ保持されます。購読の解除は本人端末に保持された秘匿性の高いプッシュエンドポイントを利用する設計です。
- プッシュ受信はWebサイトの正式号が公開されてから行います。未承認記事は送信しません。
- モデル料金など別サービスの課金は、自動的に有効化しません。

## 検証

GitHub Actionsの「Test isolated push backend」は、Denoの型検査、許可ホスト、SSRF防止、21時以降の配信日、購読データ、秘密トークンをテストします。

端末への実際の通知送信は、運営者のVAPID鍵・秘密トークン・GitHub Actions Secretsを設定した後、実機による登録/解除/受信テストが必要です。現時点のEdge FunctionはSecrets不足の場合は503を返す構成です。
