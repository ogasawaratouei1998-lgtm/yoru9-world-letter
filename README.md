# よる9じの世界便り — 創刊準備号

> 個人も、会社員も、企業も。ニュースは実話、ツッコミ担当はAI。うまくいかない日の、世界の大失敗５連発。

これはGitHub Pagesで公開できる**静的サイトの創刊準備号**です。過去に報道された実話５本を使っています。現在のニュースの自動収集・検証・毎晩21時の更新やプッシュ通知は実装・稼働していません。

## GitHub Pagesで公開

1. GitHubでパブリックリポジトリ `yoru9-world-letter` を作成します。
2. このフォルダ内のファイルを**中身のまま**リポジトリ直下に追加してコミットします。`index.html` がリポジトリの最上位に必要です（ZIPそのものを置くだけでは公開されません）。
3. リポジトリの **Settings → Pages → Build and deployment → Source: Deploy from a branch → main → /(root) → Save** を設定します。
4. サイトのURLは `https://<GitHubユーザー名>.github.io/yoru9-world-letter/` の形式です。実際のURLは Pages の「Visit site」で確認します。

詳しくは [GitHub公式の日本語ガイド](https://docs.github.com/ja/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) をご覧ください。

## このリポジトリの内容

- `index.html`: 読者向け画面。実話とAIの創作ツッコミを分けて表示
- `assets/`: SVGのアイコン（ブラウザ用）
- `manifest.webmanifest`: ホーム画面用メタデータ（SVGアイコン）
- `data/current.json`: 配信データ（現在は `draft`、未配信）
- `data/archive/index.json`: 過去号一覧（現在は空）

### 公開に関する注意

本パッケージには編集室・ニュース収集プログラム・承認待ちデータは含まれていません。実際の日次配信には、出典の確認と編集者の承認、配信処理の追加が必要です。事実の根拠は各記事の出典リンクで確認してください。