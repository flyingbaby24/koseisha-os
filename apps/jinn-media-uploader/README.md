# Jinn Media Uploader

Cloudflare R2（S3 互換 API）へ MV・BGM をアップロードし、Jinn Project Portfolio（Infinite Archive）へ登録する Windows 用 GUI アプリです。登録は GitHub API で直接行えます（ローカルのリポジトリ不要）。

| 項目 | 既定値 |
|---|---|
| アカウント | Jinn Project Media |
| バケット | `jinn-mv-portfolio` |
| API | S3 Compatibility API（`https://<Account ID>.r2.cloudflarestorage.com`） |
| 公開ベース URL | `https://pub-14a29b5d61e944bfa82071f29c1817f1.r2.dev` |
| 保存先 | MV → `mv/`、BGM → `audio/`（サイトの soundscape の規定）、その他 → `misc/` |

## 機能

- ファイル・フォルダのドラッグ＆ドロップ（フォルダは再帰的に展開。動画→MV、音声→BGM に自動振り分け）
- 300MB を超える動画のマルチパートアップロード（既定 16MiB × 4 並列。R2 の「最後以外は同じパートサイズ」規則に準拠）
- 複数ファイルの一括登録とキュー処理
- ファイルごと・全体の転送速度、進捗、残り時間の表示
- 失敗時の自動再試行（パート単位、指数バックオフ）と、失敗・一時停止・アプリ終了後の**途中再開**（送信済みパートは再送しません）
- R2 ファイル一覧（読み取り専用。フォルダ絞り込み・検索・URL コピー・ブラウザで開く）
- R2 使用容量と推定月額料金（R2 Standard の公開価格・無料枠を考慮。単価と為替は画面で変更可）
- 重複ファイルの検出（同じ保存先、同一内容の別名ファイル、キュー内の重複。SHA-256 / MD5 で照合）
- 上書き前の確認（「上書きする」を選び、さらに確認した場合のみ上書き）
- 公開 URL の生成とコピー
- MV・BGM・その他の保存先（フォルダ）指定。フォルダ構造の保持も選択可
- FFmpeg によるサムネイル生成（ポートフォリオの `scripts/make-thumbnails.mjs` と同じサイズ・形式・既定フレーム）
- ポートフォリオへの登録：GitHub API から最新データを取得し、確認後に 1 コミットで反映します（Cloudflare Pages が自動デプロイ）。ローカルフォルダへの出力も選べます。作品 ID・slug・BGM の id は既存データと重複しないよう自動で割り当てます
- 動画の圧縮は任意（既定は「元ファイルのまま」）。無劣化の Web 最適化（faststart）または H.264 再エンコードを選べます

## はじめに（ダウンロードと起動）

1. GitHub の **Actions → Jinn Media Uploader** で最新の成功した実行を開き、Artifacts の **`JinnMediaUploader-win64`** をダウンロードして展開します。
2. `JinnMediaUploader\JinnMediaUploader.exe` を起動します。同じフォルダの `ffmpeg\` にある FFmpeg が自動で使われます。
   - SmartScreen の警告が出た場合は「詳細情報」→「実行」を選びます（コード署名をしていないためです）。
3. 初回起動時に設定画面が開くので、R2 の認証情報を登録します（下記）。

### R2 API トークンの作成

1. Cloudflare ダッシュボード → **R2 Object Storage** → **Manage API tokens**（API トークンの管理）→ **Create API token**。
2. 権限は **Object Read & Write**、対象は **Apply to specific buckets only → `jinn-mv-portfolio`** を推奨します。
3. 作成後に表示される **Access Key ID** と **Secret Access Key**、R2 概要ページの **Account ID**（32 桁の英数字）を、アプリの［設定］→［R2 接続］に入力し、［接続テスト］→［保存］します。

### 認証情報の保存先

- **Windows 資格情報マネージャー**（コントロールパネル → 資格情報マネージャー → Windows 資格情報 → 汎用資格情報 `JinnMediaUploader/R2`）に保存されます。
- 設定ファイル（`%APPDATA%\JinnMediaUploader\config.json`）、ログ、履歴データベースには書き込みません。
- 安全な保存先が使えない環境では保存を拒否します。
- ［設定］の「保存済み認証情報を削除」で消去できます。

## 使い方

1. ［アップロード］タブにファイルやフォルダをドロップします。追加と同時に、ハッシュ計算・メディア解析（長さ・解像度）・重複確認がバックグラウンドで行われます。
2. 上部の「保存先」で MV / BGM / その他のフォルダを指定します（既定は `mv/` と `audio/`。空欄はバケット直下）。各行の「保存先キー」「種別」はダブルクリックで個別に変更できます。
3. ［アップロード開始］を押します。重複や同名ファイルがある場合は確認画面が出ます（スキップ／別名で保存／上書き）。
4. 完了した行の公開 URL は［公開URLをコピー］または右クリックからコピーできます。
5. ［ポートフォリオ登録］（または［履歴］タブで選択 →［選択をポートフォリオ登録］）で、ポートフォリオに登録します（下記）。

一時停止すると、送信中のパートが終わった時点で止まります。［アップロード開始］で続きから再開します。アプリを閉じても、次回起動時に中断分がキューに戻ります。

## 安全設計（既存ファイルを変更・削除しない）

- アプリには R2 のオブジェクトを**削除する機能がありません**。一覧は読み取り専用です。
- アップロード直前に HEAD で既存ファイルを確認します。存在する場合は、明示的に「上書きする」を選んで再確認しない限り書き込みません。
- 新規の書き込みには `If-None-Match: *` を付けます。確認から書き込みまでの間に同名ファイルが作られても、R2 側で拒否されます。上書きには、確認時に見た ETag を `If-Match` で指定するため、確認後に変わったファイルは上書きしません。
- 中止時に破棄（abort）するのは、このアプリ自身が開始したマルチパートアップロードだけです。
- サムネイルの R2 へのコピー（任意・既定オフ）は、同じキーに別内容のファイルがあれば行いません（名前も変えません）。

## ポートフォリオへの登録

アップロード済みの MV・BGM を、Jinn Project Portfolio（`flyingbaby24/Jinn-Portfolio`）の作品データに登録します。登録方法は 2 つあります。

| 方式 | 使いどころ |
|---|---|
| **GitHub に直接登録**（既定） | ローカルにリポジトリは不要です。GitHub API から最新データを取得し、確認後にコミットします。Cloudflare Pages が自動でデプロイします |
| **ローカルのリポジトリ / フォルダに出力** | 手元のクローンに反映したい場合や、オフラインで準備する場合に使います（従来の方式） |

### GitHub トークンの準備（初回のみ）

1. GitHub → Settings → Developer settings → **Personal access tokens → Fine-grained tokens** → Generate new token を開きます。
2. Repository access は **Only select repositories** で `flyingbaby24/Jinn-Portfolio` だけを選びます。
3. Permissions は次のとおりにします。
   - **Contents: Read and write**（必須）
   - **Pull requests: Read and write**（プルリクエスト方式を使う場合）
   - **Checks: Read-only**（デプロイ状況の表示用）
4. アプリの［設定］→［ポートフォリオ（GitHub）］→［トークンを登録・変更…］で貼り付け、［接続テスト］→［資格情報マネージャーに保存］します。

トークンは **Windows 資格情報マネージャー**（汎用資格情報 `JinnMediaUploader/GitHub`）にだけ保存されます。R2 の認証情報とは別の項目です。設定ファイル、ログ、履歴には書き込みません。

### GitHub に直接登録する手順

1. ［ポートフォリオ登録］（または［履歴］／［R2 ファイル一覧］で選択 → 右クリック）で登録画面を開きます。
2. 「反映先ブランチ」を選びます。画面を開くとき、ブランチを切り替えたとき、［最新データを取得］を押したときに、そのブランチの最新コミットから次の情報を読み込みます。
   - `data/works.json`、`data/soundscape.json`、`data/thumbnail-sources.json`
   - `public/thumbnails/` のファイル一覧
3. 作品 ID・slug・BGM の id が自動で割り当てられます。割り当てでは次の 3 つのどれとも重ならない値を選びます。
   - 既存の作品・BGM
   - 既存のサムネイルのファイル名
   - このアプリが過去に割り当てた ID
4. タイトル・状態・掲載日・サムネイル位置を確認し、［確認して GitHub へ反映…］を押します。
5. 確認画面に、反映先、基準のコミット、追加する作品・BGM、変更されるファイルごとの差分（画像はプレビュー）、コミットメッセージが表示されます。内容を確認してから［GitHub へ反映する］を押します。
6. 反映後の画面にコミット（またはプルリクエスト）へのリンクが表示されます。Cloudflare Pages のビルド状況と URL も、完了するまで自動で更新されます。

反映方法は 2 つから選べます。

| 反映方法 | 動き |
|---|---|
| 反映先ブランチに直接コミット | そのブランチを更新し、Cloudflare Pages がすぐにビルドします。`main` は本番、それ以外のブランチは `https://<ブランチ名>.jinn-portfolio.pages.dev` のプレビューになります |
| 新しいブランチでプルリクエスト | `register/mv-0005-…` ブランチに 1 コミットを作り、反映先ブランチへのプルリクエストを作ります。プレビューで確認してからマージできます |

### 既存データを守る仕組み

- 1 回の登録は **1 つのコミット**にまとまります（`data/*.json` と `public/thumbnails/*`）。ほかのファイルには触れません。
- ブランチは **早送り（fast-forward）でのみ**更新します。データの取得から反映までの間に他の更新（クラウド側の開発セッションによる push など）があった場合は、上書きせずに中止します。そのあと最新データを取り直します。
- 追加するサムネイルと同じパスのファイルがすでにある場合も中止します。
- 反映後に、新しいコミットの内容を GitHub から読み戻して確認します。
  - 送ったファイルが送信内容と一致すること
  - 既存の作品データが 1 件も変わっていないこと
- `works.json` の既存の記述はバイト単位で同じまま、新しい作品を末尾に追加します。未提供の項目（解説・歌詞・ジャンルなど）は `null` / `[]` のままです。
- 送信前に、サイトの `validateWorks` / `validateSoundscape` と同じ検証を行います。
- `data/soundscape.json` がないブランチ（現在の `main` など）では、BGM は登録しません。

### ローカルフォルダに出力する場合

登録画面で「ローカルのリポジトリ / フォルダに出力」を選び、Jinn-Portfolio のフォルダ（`data/works.json` があるところ）を指定します。リポジトリと同じ構成のフォルダ `jinn-portfolio-registration-<日時>/` が出力されます。中の `data/` と `public/` をリポジトリのルートにコピーし、`npm run build && npm test` で確認してください。

### 出力・コミットされるファイル

| ファイル | 内容 |
|---|---|
| `data/works.json` | 新しい作品を末尾に追加します（サイトの `src/data/schema.mjs` と同じ 23 項目を同じ順序で書きます） |
| `data/soundscape.json` | `tracks` に `{ "id", "key" }` を追加します（キーは `audio/…`） |
| `data/thumbnail-sources.json` | slug ごとのポスター用フレーム位置（秒）。サイトの `npm run thumbnails` でも同じ画像を再生成できます |
| `public/thumbnails/<slug>.webp` | カード用 WebP（縦長は幅 480px、横長は幅 800px） |
| `public/thumbnails/<slug>-poster.jpg` | ポスター用 JPEG（縦長は幅 720px、横長は幅 1280px） |

### ポートフォリオ側のテストについて

Jinn-Portfolio の単体テストの一部は、現在のデータ（作品 4 件、videoKey の一覧、`tracks` が空、サイトマップの件数）を固定値で確認しています。作品を追加すると、GitHub Actions の「Build, unit tests, browser tests」がこれらのテストで失敗します。

Cloudflare Pages のビルド（`npm run build`）は成功し、サイトには反映されます。CI を緑に保つには、リポジトリ側でこれらの期待値を更新してください。

## 推定月額料金

R2 Standard の公開価格（ストレージ $0.015/GB・月、Class A $4.50/100万回、Class B $0.36/100万回、無料枠 10GB・100万回・1000万回、エグレス無料）で概算します。

- ストレージは R2 の一覧から集計した合計サイズで計算します（1GB = 10億バイト）。
- Class A 操作数には、このアプリで今月行ったアップロード分だけを数えます。

実際の請求額は Cloudflare ダッシュボードで確認してください。単価と為替レートは［使用量・料金］タブで変更できます。

## 実機（Windows）での R2 接続確認

アップロードは画面から行えます。動作確認をまとめて行いたい場合は、資格情報マネージャーに保存した認証情報を使う検証コマンドも使えます。

```bat
JinnMediaUploader.exe --r2-verify --report r2-verify.json --cleanup
```

- 320MiB のマルチパートアップロードを行い、次の点を確認します。
  - 通信断の注入 → 自動再試行
  - 一時停止 → 再開
  - SHA-256 の照合
  - 公開 URL の確認
  - 重複検出、上書き防止
  - 既存オブジェクトがすべて変わっていないこと
- 書き込むのは `_selftest/jmu-<実行ID>/` の下だけです。`--cleanup` を付けると、その実行で作成したテスト用オブジェクトだけを削除します。
- 結果は `r2-verify.json` に出力されます。

## 開発者向け

```bash
cd apps/jinn-media-uploader
pip install -r requirements.txt -r requirements-dev.txt
python run_app.py                          # GUI を起動
python -m pytest -q -m "large or not large" # 330MiB のマルチパートとポートフォリオ互換性を含む全テスト
pyinstaller --noconfirm JinnMediaUploader.spec   # Windows 上で dist/JinnMediaUploader.exe を作成
```

- `tests/portfolio_spec/` には、ポートフォリオの検証コード（`schema.mjs` / `soundscape.mjs` / `media.mjs`）と実データを、コミットを記録してそのままコピーしています。Node があれば、出力をサイト自身の検証コードにも通し、アプリ側の検証結果とエラーメッセージまで一致することを確認します。
- `.github/workflows/media-uploader.yml` は Windows ランナー上で次の順に実行します。R2 への接続や Secrets は使いません。
  1. テスト
  2. EXE のビルド
  3. EXE の自己診断（R2・GitHub 用の資格情報マネージャー、FFmpeg、サムネイル、ローカル S3 サーバーへの 320MiB マルチパート、ポートフォリオ登録、ローカルの疑似 GitHub への直接登録）
  4. 画面キャプチャ
  5. Artifact `JinnMediaUploader-win64` の出力

EXE のコマンドライン機能です。ウィンドウアプリのため、結果は JSON ファイルに出力されます。

| コマンド | 内容 |
|---|---|
| `JinnMediaUploader.exe --selftest --report out.json [--endpoint http://127.0.0.1:5055]` | オフラインの自己診断 |
| `JinnMediaUploader.exe --r2-verify --report out.json --cleanup` | 実際の R2 での確認（上記） |
| `JinnMediaUploader.exe --screenshot out.png [--tab N]` | デモデータで画面を PNG に保存 |

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `InvalidAccessKeyId` / `SignatureDoesNotMatch` | Access Key ID / Secret Access Key を再入力してください |
| `AccessDenied` | API トークンの権限（Object Read & Write）と対象バケットを確認してください |
| 接続できない | Account ID（アカウント名ではなく 32 桁の ID）とネットワーク・プロキシ設定を確認してください |
| サムネイルが作られない | ステータスバーの「FFmpeg: 未検出」を確認し、［設定］で `ffmpeg.exe` を指定してください |
| 登録画面で「data/works.json が見つかりません」 | ローカル方式の場合はリポジトリのルート（または `data` フォルダ）を指定してください。GitHub 方式の場合は反映先ブランチを確認してください |
| GitHub で 401 / 403 / 404 | トークンの期限、対象リポジトリ（Only select repositories）、権限（Contents: Read and write）を確認してください |
| 「ブランチが更新されています」 | 取得後に他の更新がありました。最新データが自動で読み込まれるので、内容を確認して再度反映してください |
| ログ | `%APPDATA%\JinnMediaUploader\logs\app.log`（認証情報は記録しません） |
