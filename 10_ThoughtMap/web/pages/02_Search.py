
ユーザーの添付画像
現状、ThoughtMap Unity UIで「窓枠」と「パネル内コンテンツ」が分離して移動している。
ドラッグ/リサイズ時にWindow背景だけが動き、検索欄・結果リスト・詳細内容・グラフ等が追従していない。

原因調査と修正をしてください。

重要方針:
- Windowとして動く単位は必ず1つのRoot GameObjectに統一する
- 背景Panel、Header、Content、ScrollView、ResizeHandle、Close/ActionButton、グラフ表示はすべて同じWindowRoot配下に置く
- ドラッグ対象はWindowRootのRectTransformのみ
- Contentや子要素のRectTransformを個別にドラッグ/移動しない
- Canvas直下に散らばった子UIをWindowRoot配下へ再構成する
- LayoutGroupはWindowRoot直下ではなく、Content内部だけに限定する
- ResizeHandleはWindowRoot配下だがLayoutGroup管理外に置く
- 実行時生成されるUIも必ず対応するWindowRoot/Content配下に生成する
- AnchoredPositionを更新する対象が背景PanelではなくWindowRootになっているか確認する
- SetParent時は worldPositionStays=false を使い、ローカル座標基準を壊さない
- FastAPI/API/Repository/SQLite/Pythonには触らずUnity側だけ修正する

修正対象:
- Search Window
- Result List Window
- Detail Window
- グラフ/レーダーチャート表示
- Source Link / Save to My Library などのボタン類

最初に現在のCanvas階層を調査し、
「どのUI要素がWindowRoot外に残っているか」をREADMEに記録。
その後、全UI要素がWindowRootに追従するように修正。

展開
11:04

4m 26s作業しました
原因は、前回のBlock化で HeaderBlock / ResultProfileBlock / ActionBlock / QueryProfileBlock 自体を個別ドラッグ対象にしていたことです。これらが DetailContent の VerticalLayoutGroup 配下から ignoreLayout で外れ、背景・中身・レーダー・ボタンが同じWindowRootとして動かなくなっていました。

今回は方針を修正して、DetailPanelV2は ThoughtMapDetailPanelV2 Rootだけが移動・リサイズされる構造に戻しました。FastAPI / Repository / SQLite / Python は触っていません。

変更ファイル

outputs/10_ThoughtMap/unity/Assets/Scripts/UI/ThoughtMapDetailPanelV2View.cs
outputs/10_ThoughtMap/unity/Assets/Scripts/UI/ThoughtMapDraggableWindow.cs
outputs/10_ThoughtMap/unity/README.md
修正内容

DetailPanelV2の各Block個別ドラッグ/リサイズを廃止
ThoughtMapDetailPanelV2 Rootを唯一の移動・リサイズ対象に統一
DetailContent 配下に残った古い ThoughtMapDraggableWindow / ThoughtMapResizableWindow をruntimeで削除
各Blockの LayoutElement.ignoreLayout をfalseへ復旧
Block順序を Header -> Selected Profile -> Footer -> Source Link -> Query Profile に復旧
Rootの ResizeHandle を復活
Drag TargetはRootを動かすように変更
HeaderBlock
ProfileHeadingText
QueryProfileHeadingText
READMEにRuntime階層調査メモを追加
現在のWindowRoot構造

SearchHeaderV2
WindowContent
ResizeHandle
ResultListV2
WindowContent
ResizeHandle
ThoughtMapDetailPanelV2
DetailContent
HeaderBlock
ResultProfileBlock
FooterBlock
ActionBlock
QueryProfileBlock
ResizeHandle
Unity Editorで確認する項目

DetailPanelV2をHeader/見出しからドラッグした時、全ブロック・グラフ・ボタンが一緒に動くこと
DetailPanelV2右下のResizeHandleで、全体が一体としてリサイズされること
ActionBlock の Open Link / Save to My Library がクリック可能なままであること
Debug Block Interaction をONにすると、古いBlock操作コンポーネントが掃除されRoot操作が準備されるログが出ること
未実施

Unity Editorでのコンパイル確認
Play Modeでの実操作確認
Prefab再保存確認

README.md
ドキュメント・MD
11:09
修正方針は良いです。
次はUnity Editorでの確認前に、再発防止として以下を追加してください。

1. DetailContent配下のBlockには
   ThoughtMapDraggableWindow
   ThoughtMapResizableWindow
   を絶対に付与しない構造にしてください。

2. Runtime生成・再構築時にも、
   Block単位にドラッグ/リサイズ系コンポーネントが再付与されないことを保証してください。

3. Drag TargetはHeaderBlock等でもよいが、
   実際に移動するRectTransformは必ず ThoughtMapDetailPanelV2 Root にしてください。

4. DetailContent配下のBlockの LayoutElement.ignoreLayout は常に false に戻してください。

5. READMEに
   「WindowRootだけが移動・リサイズ対象」
   「BlockはLayout管理対象であり、移動対象ではない」
   というルールを明記してください。

追加不具合です。

検索実行後、DetailPanelV2がドラッグ移動できなくなります。
初期状態では動くが、検索結果表示後またはResult選択後にドラッグできなくなる可能性があります。

推定原因:
DetailContent配下のHeaderBlock / ProfileHeadingText / QueryProfileHeadingText等が検索後に再生成・再配置され、
ドラッグイベントの登録またはDrag Target設定が失われている。

修正方針:
- DetailPanelV2のドラッグ機能は検索後・結果選択後・ShowResult/ShowQueryParameters後も維持する
- UI再生成後に必ずRootドラッグ設定を再適用する
- Drag TargetはHeaderBlock等でもよいが、移動対象は必ず ThoughtMapDetailPanelV2 Root
- HeaderBlock / ProfileHeadingText / QueryProfileHeadingText が再生成された場合も、Rootへドラッグを伝える
- 古いBlock個別ドラッグ/リサイズは復活させない
- DetailContent配下のBlockには ThoughtMapDraggableWindow / ThoughtMapResizableWindow を付与しない
- Runtime cleanup後にもRootの ThoughtMapDraggableWindow / ThoughtMapResizableWindow は削除しない
- CanvasGroup / Graphic.raycastTarget / Button / ScrollRect がドラッグ開始イベントを奪っていないか確認する
- 検索後にRootの Drag Target / ResizeHandle / LayoutElement 状態をログ出力できるようにする
- FastAPI / Repository / SQLite / Python には触らずUnity側のみ修正

確認項目:
1. 起動直後にDetailPanelV2をドラッグできる
2. 検索後もDetailPanelV2をドラッグできる
3. Result選択後もDetailPanelV2をドラッグできる
4. Open Link / Save to My Libraryボタンはクリック可能
5. DetailContent配下のBlockはLayout管理下に残る

展開
11:12

6m 8s作業しました
修正しました。Unity側のみです。FastAPI / Repository / SQLite / Python は触っていません。

変更ファイル

ThoughtMapDetailPanelV2View.cs (line 543)
README.md (line 89)
原因
DetailPanelV2 は「Rootを動かす」設計に戻していましたが、実際には HeaderBlock や見出し側へ ThoughtMapDraggableWindow が付く経路が残っていました。検索後・選択後の再構築/修復でその状態が崩れ、ドラッグ不能になる可能性がありました。

修正内容

ThoughtMapDetailPanelV2 Root だけに ThoughtMapDraggableWindow を付けるよう変更。
DetailContent 配下のBlockには ThoughtMapDraggableWindow / ThoughtMapResizableWindow を付けないよう保証。
検索後・ShowResult() 後・ShowQueryParameters() 後に Root のドラッグ/リサイズ設定を再適用。
DetailContent 配下のBlockは常に LayoutElement.ignoreLayout = false に戻す。
Block内の背景やテキストはドラッグを邪魔しないよう Raycast を無効化。ただし Open Link / Save ボタンはクリック可能なまま維持。
Debug Block Interaction 有効時に、rootDrag/rootResize/illegalBlockDrag/illegalBlockResize をログ出力。
READMEに「WindowRootだけが移動・リサイズ対象」「BlockはLayout管理対象」と明記。
確認済み

C#波括弧バランス確認済み。
DetailContent 配下へドラッグ/リサイズを追加するコード経路が残っていないことを検索確認。
README内の古いBlock個別ドラッグ説明をRoot専用ルールへ更新。
Unity Editorで確認する項目

起動直後にDetailPanelV2をドラッグできる。
検索後もDetailPanelV2をドラッグできる。
Result選択後もDetailPanelV2をドラッグできる。
Open Link / Save to My Library がクリックできる。
Debug Block Interaction をONにして、Consoleで rootDrag=True, rootResize=True, illegalBlockDrag=0, illegalBlockResize=0 を確認。
この環境ではUnity Editor実行確認まではできていません。


README.md
ドキュメント・MD
11:18
02_Search.py
Streamlit側は既存のUI土台として使う。
ただし検索処理やデータ構造は、現在Unityが使っているFastAPI検索システムに寄せる。

目的:
Unityで作ってきたThoughtMap検索システムをStreamlitからも操作できるようにする。
Streamlit単体の別実装に置き換えない。

方針:
- Unity側で使っているFastAPIエンドポイントをStreamlitから呼ぶ
- Streamlit内でCSVを直接読んで独自検索しない
- Repository / SQLite / Python検索ロジックは既存API側を正とする
- StreamlitはAPIクライアント兼UIにする
- UnityとStreamlitで同じ検索結果・同じQuery Profile・同じSelected Profileを表示する
- Unity側の実装資産を捨てない
- Streamlit版はWeb確認・UI確認・API確認用の管理画面として使う

実装内容:
- Streamlitに API Base URL 入力を追加
- 検索ボタンで FastAPI の検索エンドポイントを呼ぶ
- レスポンスJSONをそのまま表示・整形
- Similar works / Similar authors / Query Profile / Selected Profile / Radar chart を表示
- APIレスポンス保存/ダウンロード機能を追加
- 既存のCSV直読み検索は残す場合も Legacy mode 扱いにする

重要:
既存Streamlitの中身を単純に書き換えて別検索にしない。
Unityが参照しているFastAPI検索システムをStreamlitから叩く形にしてください。

展開
11:26

6m 49s作業しました
実装しました。対象は 02_Search.py (line 1) です。

変更内容:

Streamlit側に FastAPI / shared backend モードを追加し、これを標準にしました。
API Base URL 入力を追加しました。標準は http://127.0.0.1:8000。
/search?q=...&top=...&mode=...&source=...&filter=... をStreamlitから呼ぶようにしました。
semantic / keyword / hybrid、source filter、general などのfilter選択に対応しました。
APIレスポンスJSONをそのまま st.json() で確認できるようにしました。
APIレスポンスJSONと検索結果CSVをダウンロード可能にしました。
Similar works、API結果からの Similar authors 集計、Query Profile、Selected Profile、Radar chartを表示します。
既存CSV直読み検索は削除せず、Legacy CSV local mode として残しました。
確認:

02_Search.py の Python 構文チェックは通過済みです。
FastAPI / Unity / Repository / SQLite 側は触っていません。
補足:

Similar authors は現時点の /search レスポンスだけから集計しています。別のCSV検索や独自検索はしていません。完全なauthor similarityをUnity/Streamlit共通にするなら、将来API契約として追加するのが安全です。

ウェブプレビュー
ウェブサイト
11:33
ローカルで FastAPI / shared backend mode の検索動作を確認しました。
Streamlitから /search に接続でき、Plato検索で10件取得できています。

次の改善をお願いします。

対象:
- web/pages/02_Search.py のみ

条件:
- FastAPI / Repository / SQLite / Unity は触らない
- API契約は変更しない
- 既存のshared backend modeとLegacy CSV local modeは維持

改善:
1. Raw JSONは常時表示ではなくexpander内に入れる
2. Similar worksの表で行を選択できるようにする
3. 選択した作品の詳細パネルを下に表示する
4. Query Profile / Selected Profileを見やすく並べる
5. Radar chartが欠損値で落ちないようにする
6. Similar authorsを表と棒グラフで表示する
7. request URL / status code / response timeをDebug expanderにまとめる
8. 結果0件・APIエラー時でも画面が崩れないようにする

完了後、変更内容と確認手順を報告してください。

展開
11:50

5m 27s作業しました
実装しました。対象は 02_Search.py (line 1) のみです。FastAPI / Repository / SQLite / Unity は触っていません。

変更内容:

Raw JSONを常時表示ではなく Debug: API request / response expander 内へ移動。
Debug expanderに request URL / status code / response time を集約。
Similar works を行選択できる表に変更。Streamlitの選択APIが使えない場合はselectboxへ fallback します。
選択した作品の詳細パネルをSimilar worksの下に表示。
Query Profile / Selected Profileを2カラムで並べて表示。
Radar chartは欠損値・空値・3項目未満で落ちないように防御。
Similar authorsをAPI検索結果から集計し、表と棒グラフで表示。
APIエラー時、0件時も画面が崩れないように表示分岐を整理。
APIレスポンスJSONのダウンロードはDebug expander内に配置。
確認:

02_Search.py のPython構文チェックは通過済みです。
確認手順:

FastAPIを起動。
Streamlitで FastAPI / shared backend を選択。
Plato を検索。
Similar worksの行をクリックし、下の詳細パネルとSelected Profileが切り替わることを確認。
Debug expanderでURL、status code、response time、Raw JSONを確認。
0件になりそうな検索語でも画面が崩れないことを確認。
11:56




出力
127.0.0.1:8000
README.md
127.0.0.1:8000/users/default/save
README.md
README.md
README.md

情報源










refactor-request-stratagems-research-database-repository
outputs
10_ThoughtMap
web
pages
02_Search.py
    categories: list[str],
    top: int,
    include_same_author: bool,
) -> None:
    st.subheader("Upload embeddings CSV")
    st.caption(
        "既存ThoughtMapの Export > Download document embeddings CSV をアップロードして、"
        "DB登録せずに近い作品・作者を検索します。"
    )

    uploaded = st.file_uploader("Embedding CSV", type=["csv"])
    if uploaded is None:
        st.info("embedding列を含むCSVをアップロードしてください。")
        st.stop()

    try:
        upload_df = load_uploaded_embeddings(uploaded)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    db_dim = int(df["_dim"].value_counts().idxmax())
    upload_df = upload_df[upload_df["_dim"] == db_dim].copy()

    if upload_df.empty:
        st.error(f"DB側のembedding次元({db_dim})と一致する行がありません。")
        st.stop()

    c1, c2 = st.columns(2)
    c1.metric("Uploaded works", len(upload_df))
    c2.metric("Embedding dim", db_dim)

    compare_category = st.selectbox("Compare against category", categories, index=0)
    compare_df = filter_catalog(df, "", "All", compare_category)
    if compare_df.empty:
        st.warning("比較対象カテゴリに作品がありません。")
        st.stop()

    query = st.text_input("Filter uploaded title / author / doc_id", value="")
    filtered = filter_catalog(upload_df, query, "All", "All")

    if filtered.empty:
        st.warning("該当作品がありません。")
        st.stop()

    view_cols = ["_row_id", "doc_id", "author", "title", "source"]
    st.dataframe(filtered[view_cols].head(200), use_container_width=True, hide_index=True)

    upload_mode = st.radio(
        "Uploaded search type",
        ["Single uploaded work", "Uploaded personality average"],
        horizontal=True,
    )

    if upload_mode == "Uploaded personality average":
        avg_vec = normalized_average_vector(upload_df["_embedding_vec"].to_list())

        render_results(
            df=compare_df,
            target_title=f"Uploaded personality average ({len(upload_df)} works)",
            target_author="Uploaded CSV",
            target_doc_id="uploaded_personality_average",
            target_gutenberg_id="",
            target_source_url="",
            target_vec=avg_vec,
            target_category=compare_category if compare_category != "All" else "",
            target_subcategory="",
            top=top,
            include_self=False,
            include_same_author=include_same_author,
            source_label="Upload",
            button_key="upload_average_search",
        )
        return

    selected_label = st.selectbox(
        "Uploaded target",
        options=filtered["label"].tolist(),
        index=0,
    )
    target = filtered.loc[filtered["label"] == selected_label].iloc[0]

    render_results(
        df=compare_df,
        target_title=target.get("title", ""),
        target_author=target.get("author", ""),
        target_doc_id=target.get("doc_id", "") or target.get("_row_id", ""),
        target_gutenberg_id=target.get("gutenberg_id", ""),
        target_source_url=target.get("source_url", ""),
        target_vec=target["_embedding_vec"],
        target_category=target.get("category", ""),
        target_subcategory=target.get("subcategory", ""),
        top=top,
        include_self=False,
        include_same_author=include_same_author,
        source_label="Upload",
        button_key="upload_single_search",
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    search_backend = st.sidebar.radio(
        "Search backend",
        ["FastAPI / shared backend", "Legacy CSV local mode"],
        index=0,
    )

    if search_backend == "FastAPI / shared backend":
        render_api_search_mode()
        return

    st.warning(
        "Legacy CSV local mode is kept for manual CSV workflows only. "
        "Unity and the future shared backend use FastAPI /search as the source of truth."
    )

    with st.sidebar:
        st.header("Legacy CSV DB")
        db_dir = str(DEFAULT_DB_DIR)
        st.caption(f"DB: {DEFAULT_DB_DIR.name}")

        top = st.slider("Top results", min_value=5, max_value=50, value=20, step=5)
        include_same_author = st.checkbox(
            "Include the same author in the author ranking",
            value=False,
        )
        include_self = st.checkbox(
            "Include benchmark works in the work rankings",
            value=False,
        )

        if st.button("Reload DB"):
            st.cache_data.clear()

    try:
        df = load_db_cached(db_dir)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    sources = ["All"] + sorted(
        [s for s in df["source"].map(normalize_text).unique().tolist() if s]
    )
    categories = ["All"] + sorted(
        [c for c in df["category"].map(normalize_text).unique().tolist() if c]
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Works", len(df))
    c2.metric("Authors", df["author"].replace("", pd.NA).dropna().nunique())
    c3.metric("Sources", max(0, len(sources) - 1))

    mode = st.radio(
        "Search mode",
        ["DB work", "Upload embeddings CSV"],
        horizontal=True,
    )

    if mode == "DB work":
        render_db_work_mode(
            df=df,
            sources=sources,
            categories=categories,
            top=top,
            include_self=include_self,
            include_same_author=include_same_author,
        )
    else:
        render_upload_mode(
            df=df,
            categories=categories,
            top=top,
            include_same_author=include_same_author,
        )

    with st.expander("DB columns"):
        st.write(df.drop(columns=["_embedding_vec"], errors="ignore").columns.tolist())


if __name__ == "__main__":
    main()

