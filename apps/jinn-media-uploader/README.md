# Jinn Media Uploader

Cloudflare R2（S3 互換 API）へ MV・BGM をアップロードし、Jinn Project Portfolio（Infinite Archive）への登録データを作る Windows 用 GUI アプリです。

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
- ポートフォリオ（`data/works.json` / `data/soundscape.json`）への登録データ出力。作品 ID・slug・BGM の id は既存データと重複しないよう自動で割り当てます
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
5. ［ポートフォリオ登録］（または［履歴］タブで選択 →［選択をポートフォリオ登録］）で、ポートフォリオへの登録データを出力します（下記）。

一時停止すると、送信中のパートが終わった時点で止まります。［アップロード開始］で続きから再開します。アプリを閉じても、次回起動時に中断分がキューに戻ります。

## 安全設計（既存ファイルを変更・削除しない）

- アプリには R2 のオブジェクトを**削除する機能がありません**。一覧は読み取り専用です。
- アップロード直前に HEAD で既存ファイルを確認します。存在する場合は、明示的に「上書きする」を選んで再確認しない限り書き込みません。
- 新規の書き込みには `If-None-Match: *` を付けます。確認から書き込みまでの間に同名ファイルが作られても、R2 側で拒否されます。上書きには、確認時に見た ETag を `If-Match` で指定するため、確認後に変わったファイルは上書きしません。
- 中止時に破棄（abort）するのは、このアプリ自身が開始したマルチパートアップロードだけです。
- サムネイルの R2 へのコピー（任意・既定オフ）は、同じキーに別内容のファイルがあれば行いません（名前も変えません）。

## ポートフォリオへの登録

対象は `flyingbaby24/Jinn-Portfolio` の `phase-3-1-soundscape` ブランチのデータ形式です。

1. 初回は［設定］→［メディア・出力］→「ポートフォリオのフォルダ」に、Jinn-Portfolio リポジトリのフォルダ（`data/works.json` があるところ）を指定します。登録画面でも指定できます。
2. 登録画面では既存データ（例: 作品 4 件 mv-0001〜mv-0004 / BGM 0 曲）を読み込みます。新しい作品には次の値が自動で割り当てられます。
   - 作品 ID: `mv-0005` から順に、既存の最大番号の次
   - slug: タイトルから作成。既存の slug と重なる場合は `human-2` のように番号を付けます
   - BGM の id: ファイル名から作成
3. タイトル・slug・状態（published / draft / unlisted）・掲載日・サムネイル位置（秒）を確認・編集し、［登録データを出力］を押します。
4. 出力フォルダ `jinn-portfolio-registration-<日時>/` の `data/` と `public/` を、リポジトリのルートにコピー（上書き）します。そのあと `npm run build && npm test`、`npm run verify:r2` で確認してください。

### 割り当てのルール

- 作品 ID・slug・BGM の id は、既存の `works.json` / `soundscape.json` と、このアプリが過去の出力で割り当てた ID（コミット前のものを含む）のどちらとも重ならない値になります。同じファイルを出力し直したときは同じ ID を使います。
- すでに登録済みの `videoKey` / `key` は二重に登録しません。登録画面に「登録済み（mv-0002）」と表示されます。
- サイトが再生できない音声形式（m4a / mp3 / aac / ogg / opus / wav / flac 以外）は BGM として登録しません。

### 出力の内容

| ファイル | 内容 |
|---|---|
| `data/works.json` | 既存の作品はそのまま（バイト単位で同一）。新しい作品を末尾に追加します |
| `data/soundscape.json` | `tracks` に `{ "id", "key" }` を追加します（キーは `audio/…` のまま。URL エンコードはサイトのビルドが行います） |
| `data/thumbnail-sources.json` | slug ごとのポスター用フレーム位置（秒）。サイトの `npm run thumbnails` でも同じ画像を再生成できます |
| `public/thumbnails/<slug>.webp` | カード用 WebP（縦長は幅 480px、横長は幅 800px） |
| `public/thumbnails/<slug>-poster.jpg` | ポスター用 JPEG（縦長は幅 720px、横長は幅 1280px） |
| `new-entries.json` / `README.txt` | 今回追加した分の一覧と手順 |

作品データはサイトの `src/data/schema.mjs` と同じ 23 項目を同じ順序で書きます。

- 解説・歌詞・ジャンル・制作日・言語など、提供されていない情報は `null` / `[]` のままにします（推測で埋めません）。
- `duration` / `width` / `height` はファイルからの実測値です（回転を考慮した表示サイズ）。
- 出力前に、サイトの `validateWorks` / `validateSoundscape` と同じ検証を行います。

### 確認済み

- 現在のデータ（4 作品）に 2 作品と BGM 1 曲を追加した出力を、リポジトリのコピーに適用しました。`npm run build` は成功し、新しい作品ページも生成されました。
- `npm test` では 6 件が失敗します。いずれも現在のデータそのもの（作品数 4、videoKey の一覧、`tracks` が空、サイトマップの件数）を固定で確認しているテストで、作品を追加するときはリポジトリ側でこれらの期待値を更新してください。

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
  3. EXE の自己診断（資格情報マネージャー、FFmpeg、サムネイル、ローカル S3 サーバーへの 320MiB マルチパート、ポートフォリオ登録）
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
| 登録画面で「data/works.json が見つかりません」 | Jinn-Portfolio リポジトリのルート（または `data` フォルダ）を指定してください |
| ログ | `%APPDATA%\JinnMediaUploader\logs\app.log`（認証情報は記録しません） |
