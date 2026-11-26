# Jinn Media Uploader

Cloudflare R2（S3 互換 API）へ MV・BGM をアップロードする Windows 用 GUI アプリです。

| 項目 | 既定値 |
|---|---|
| アカウント | Jinn Project Media |
| バケット | `jinn-mv-portfolio` |
| API | S3 Compatibility API（`https://<Account ID>.r2.cloudflarestorage.com`） |
| 公開ベース URL | `https://pub-14a29b5d61e944bfa82071f29c1817f1.r2.dev` |

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
- FFmpeg によるサムネイル生成（動画: ポスター JPG ＋ WebP サムネイル、音声: カバーアートまたは波形画像）
- Infinite Archive 登録用 JSON の出力
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
2. 上部の「保存先」で MV / BGM / その他のフォルダを指定します（例: `mv/2026/`。空欄はバケット直下）。各行の「保存先キー」「種別」はダブルクリックで個別に変更できます。
3. ［アップロード開始］を押します。重複や同名ファイルがある場合は確認画面が出ます（スキップ／別名で保存／上書き）。
4. 完了した行の公開 URL は［公開URLをコピー］または右クリックからコピーできます。
5. ［JSON 出力］（または［履歴］タブで選択 →［選択を JSON 出力］）で、Infinite Archive 登録用 JSON を出力します。出力前にタイトル・slug・ID 番号・説明を編集できます。

一時停止すると、送信中のパートが終わった時点で止まります。［アップロード開始］で続きから再開します。アプリを閉じても、次回起動時に中断分がキューに戻ります。

## 安全設計（既存ファイルを変更・削除しない）

- アプリには R2 のオブジェクトを**削除する機能がありません**。一覧は読み取り専用です。
- アップロード直前に HEAD で既存ファイルを確認します。存在する場合は、明示的に「上書きする」を選んで再確認しない限り書き込みません。
- 新規の書き込みには `If-None-Match: *` を付けます。確認から書き込みまでの間に同名ファイルが作られても、R2 側で拒否されます。上書きには、確認時に見た ETag を `If-Match` で指定するため、確認後に変わったファイルは上書きしません。
- 中止時に破棄（abort）するのは、このアプリ自身が開始したマルチパートアップロードだけです。
- 生成サムネイルが既存ファイルと同名になる場合は、`name (2).webp` のように別名にします。

## Infinite Archive 登録用 JSON

`works` の各要素は、Infinite Archive のページに埋め込まれている `#x-data` の作品データと同じ形式です。

```json
{
  "works": [{
    "id": "mv-0005", "slug": "night-drive", "title": "Night Drive", "artist": "Jinn Project",
    "w": 1920, "h": 1080, "durationText": "3:12",
    "thumb": "https://pub-…r2.dev/thumbnails/night-drive.webp",
    "poster": "https://pub-…r2.dev/thumbnails/night-drive-poster.jpg",
    "video": "https://pub-…r2.dev/mv/Night%20Drive.mp4",
    "page": "/music-videos/night-drive/", "description": null, "lyrics": null,
    "uploadDate": "2026-11-26", "duration": "PT3M12S", "encodingFormat": "video/mp4",
    "category": "music-videos", "genre": "", "themes": [], "year": "2026"
  }],
  "soundscape": { "tracks": [{ "id": "bgm-0001", "title": "…", "src": "https://pub-…r2.dev/bgm/….mp3", "…": "…" }] },
  "assets": [{ "key": "mv/Night Drive.mp4", "sizeBytes": 0, "sha256": "…", "…": "…" }]
}
```

- 先頭 13 項目（`id`〜`lyrics`）がサイトの作品データと同じです。続く `uploadDate` / `duration` / `encodingFormat` は作品ページの VideoObject、`category` / `genre` / `themes` / `year` はライブラリのカードで使われている項目です。
- `w` / `h` は回転メタデータを考慮した表示サイズです（縦動画は 1080×1920）。
- `thumb` / `poster` は、サムネイルを R2 にアップロードした場合は公開 URL、ローカルのみの場合は `/thumbnails/<ファイル名>`（サイトの `thumbnails/` にコピーする前提）です。
- ID 番号の初期値は［設定］→［メディア・出力］の「次の MV 番号」です（既定 5。現在の公開作品は mv-0001〜0004）。出力後は自動で進みます。

## 推定月額料金

R2 Standard の公開価格（ストレージ $0.015/GB・月、Class A $4.50/100万回、Class B $0.36/100万回、無料枠 10GB・100万回・1000万回、エグレス無料）で概算します。

- ストレージは R2 の一覧から集計した合計サイズで計算します（1GB = 10億バイト）。
- Class A 操作数には、このアプリで今月行ったアップロード分だけを数えます。

実際の請求額は Cloudflare ダッシュボードで確認してください。単価と為替レートは［使用量・料金］タブで変更できます。

## 開発者向け

```bash
cd apps/jinn-media-uploader
pip install -r requirements.txt -r requirements-dev.txt
python run_app.py                          # GUI を起動
python -m pytest -q -m "large or not large" # 330MiB のマルチパートを含む全テスト（ローカル S3 互換サーバー使用）
pyinstaller --noconfirm JinnMediaUploader.spec   # Windows 上で dist/JinnMediaUploader.exe を作成
```

EXE には検証用のコマンドライン機能があります。ウィンドウアプリのため、結果は JSON ファイルに出力されます。

| コマンド | 内容 |
|---|---|
| `JinnMediaUploader.exe --selftest --report out.json [--endpoint http://127.0.0.1:5055]` | Qt、資格情報マネージャー、FFmpeg を確認します。`--endpoint` を指定すると、ローカル S3 サーバーへの 320MiB アップロードまで行います |
| `JinnMediaUploader.exe --r2-verify --report out.json --cleanup` | 実際の R2 で検証します（詳細は下の「実 R2 での検証」） |
| `JinnMediaUploader.exe --screenshot out.png [--tab N]` | デモデータで画面を PNG に保存します |

### CI と実 R2 での検証

`.github/workflows/media-uploader.yml` は Windows ランナー上で次の順に実行します。

1. テスト
2. EXE のビルド
3. EXE の自己診断（資格情報マネージャー、FFmpeg、ローカル S3 への 320MiB マルチパート）
4. 画面キャプチャ

実 R2 での検証は、リポジトリの Secrets に `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` を登録したうえで、次のどちらかで実行します。

- **Run workflow** で `r2_live` にチェックを入れて実行する
- コミットメッセージに `[r2-live]` を含めて push する

実行内容は次のとおりです。

- 資格情報マネージャーへの保存と読み出し
- 320MiB のマルチパートアップロード（通信断の注入 → 自動再試行、一時停止 → 再開）
- SHA-256 の照合
- 公開 URL への HEAD リクエスト
- 重複検出、上書き防止、BGM の単一 PUT、サムネイル生成、JSON 出力
- 既存オブジェクトがすべて変わっていないことの比較

書き込むのは `_selftest/jmu-<実行ID>/` の下だけです。終了時には、その実行で作成したテスト用オブジェクト（`jmu-selftest-run` メタデータで識別）だけを削除します。

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `InvalidAccessKeyId` / `SignatureDoesNotMatch` | Access Key ID / Secret Access Key を再入力してください |
| `AccessDenied` | API トークンの権限（Object Read & Write）と対象バケットを確認してください |
| 接続できない | Account ID（アカウント名ではなく 32 桁の ID）とネットワーク・プロキシ設定を確認してください |
| サムネイルが作られない | ステータスバーの「FFmpeg: 未検出」を確認し、［設定］で `ffmpeg.exe` を指定してください |
| ログ | `%APPDATA%\JinnMediaUploader\logs\app.log`（認証情報は記録しません） |
