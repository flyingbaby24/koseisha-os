# ThoughtMap Unity Setup

This guide explains how to wire the current Unity scene to the FastAPI ThoughtMap backend and the new filter/detail/parameter UI placeholders.

The current repository copy contains Unity scripts, but no editable scene or prefab asset is present here. Update `ThoughtMapMain` in the Unity Editor using the steps below.

## Goal

Add these UI pieces to the existing `ThoughtMapMain` scene without breaking the current search flow:

- Filter Dropdown for `filters/*.json` selection
- Right-side Detail Panel
- Parameter Scores Panel inside the Detail Panel
- Inspector references for `ThoughtMapSearchManager`, `DetailPanelView`, and `FilterSelectorView`


## Dark SF / Neon UI Theme

The first-stage product UI pass keeps the current hierarchy and behavior, then layers a dark navy / cyan neon style on top.

### Add Theme Applier

1. Create an empty GameObject under Canvas named `NeonTheme`.
2. Add `ThoughtMapNeonTheme` to it.
3. Assign `Canvas` or the main UI root to `Theme Root`.
4. Assign `Main Camera` to `Target Camera` if available.
5. Enable `Apply On Enable`.
6. In the component menu, use `Apply Neon Theme` if you want to apply the style immediately in the Editor.

This changes:

- Camera/background to dark navy
- Panels to translucent dark blue
- Text to white/cyan tones
- Buttons, dropdowns, and inputs to neon bordered controls
- Result cards to dark card surfaces with cyan outlines

### Result Item Card Style

`ResultItemView` now supports selected-state visuals.

Recommended ResultItem prefab setup:

1. Add an Image to the ResultItem root if it does not already have one.
2. Assign it to `Background Image`.
3. Add or assign an Outline to `Selection Outline`.
4. Optional: add a TMP Text for similarity score and assign it to `Similarity Text`.
5. Keep `Title Text`, `Author Text`, and `Select Button` assigned.

When a result is clicked, `SearchResultsListView` clears the previous selection and calls `SetSelected(true)` on the clicked item. This creates the glowing selected-card effect.

### Detail Panel Product Card

Keep the existing DetailPanel hierarchy, but style its root Image as a large translucent dark card. Add an Outline with cyan color for a thin neon frame.

Optional additions:

- Add `RadarHeadingText` near the selected-result radar chart and assign it to `DetailPanelView.Radar Heading Text`.
- Add `RadarHeadingText` near the query radar chart and assign it to `QueryParameterPanelView.Radar Heading Text`.
- The Save button label is set by script to `☆ Save to My Library`.

### Recommended Layout Pass

Use this as the first non-breaking layout direction:

```text
Canvas
  NeonTheme
  TitleText
  SearchControlsRow
  MainContentRow
    ResultsPanel
      Scroll View
    DetailPanel
      Header
      ResultRadarChart
      ParameterScoresPanel
      UrlText / OpenLinkButton
      SaveButton / SaveStatusText
```

Keep the existing object names and script references where possible. The goal of this phase is visual polish without breaking search, save, URL, radar, or D-S rank behavior.

## Existing Objects To Keep

Do not replace the working search UI.

Keep the existing:

- Search Input
- Search Button
- Mode Dropdown
- Source Dropdown
- Results Scroll View
- ResultItem prefab
- `ThoughtMapApiClient`
- `ThoughtMapSearchManager`
- `SearchResultsListView`

## Recommended Scene Layout

Use a simple two-column layout first. Appearance can be refined later.

```text
Canvas
  MainRoot
    LeftPanel
      SearchControls
        SearchInput
        SearchButton
        ModeDropdown
        SourceDropdown
        FilterDropdown
      ResultsScrollView
    RightPanel
      DetailPanel
        EmptyState
        Content
          TitleText
          AuthorText
          SourceText
          DocIdText
          SimilarityText
          BodyText
          ParameterScoresPanel
            ParameterScoresText
```

Suggested first-pass layout:

- `LeftPanel`: anchored left, width about 55-65% of screen
- `RightPanel`: anchored right, width about 35-45% of screen
- `ResultsScrollView`: keep the current working setup
- `DetailPanel`: ScrollView-based if the content can grow
- `ParameterScoresText`: plain TMP Text, one key/value pair per line

## Add Filter Dropdown

1. In `ThoughtMapMain`, create a new TMP Dropdown near the existing Mode and Source dropdowns.
2. Name it `FilterDropdown`.
3. Add options manually for now:
   - `all`
   - `general`
4. Create an empty GameObject near the dropdown named `FilterSelector`.
5. Add `FilterSelectorView` to `FilterSelector`.
6. Assign `FilterDropdown` to the `Filter Dropdown` field on `FilterSelectorView`.
7. If JSON filter files are imported as Unity `TextAsset`s later, assign them to `Filter Json Files`.

Note: `FilterSelectorView` uses `all` plus assigned JSON asset names. Manual dropdown options are useful while the JSON assets are not imported into Unity yet.

## Add Detail Panel

1. Create a right-side Panel named `DetailPanel`.
2. Add `DetailPanelView` to `DetailPanel`.
3. Inside it, create two child roots:
   - `EmptyState`
   - `Content`
4. Under `EmptyState`, add a TMP Text such as `Select a result`.
5. Under `Content`, add TMP Text objects:
   - `TitleText`
   - `AuthorText`
   - `SourceText`
   - `DocIdText`
   - `SimilarityText`
   - `BodyText`
6. Assign these objects to the matching fields in `DetailPanelView`.
7. Assign `EmptyState` to `Empty State Root`.
8. Assign `Content` to `Content Root`.

`DetailPanelView` currently displays selected search result data. It does not call `GET /document/{doc_id}` yet.

## Add Parameter Scores Panel

1. Under `DetailPanel/Content`, create a child Panel named `ParameterScoresPanel`.
2. Add a TMP Text child named `ParameterScoresText`.
3. Add `ParameterScoresPanelView` to `ParameterScoresPanel`.
4. Assign `ParameterScoresText` to the `Output Text` field.
5. On `DetailPanelView`, assign `ParameterScoresPanel` to `Parameter Scores Panel View`.

When `/search?...&filter=general` returns `parameters`, this panel shows key/value rows. If parameters are absent, it shows the empty message.


## Add Query Parameter Panel

This panel shows parameter scores for the search input text itself, separate from the selected result.

1. Place the panel under the Search Input or at the top of the right Detail area.
2. Name it `QueryParameterPanel`.
3. Add a child TMP Text for the title, such as `QueryParameterTitleText`.
4. Add a child area with `ParameterScoresPanelView` and a TMP Text for key/value output.
5. Add `QueryParameterPanelView` to `QueryParameterPanel`.
6. Assign the nested `ParameterScoresPanelView` to `Parameter Scores Panel View`.
7. Assign the title TMP Text to `Title Text`.
8. On `ThoughtMapSearchManager`, assign `QueryParameterPanel` to `Query Parameter Panel View`.

When `/search?...&filter=general` returns `query_parameters`, this panel shows the search text parameter profile. It clears on each new search.


## Parameter Rank Bar Display

ParameterScoresPanelView now supports a horizontal bar chart style with D-S rank display. The raw numeric value remains in ThoughtMapParameterScore.value; only the visible label is converted to rank.

Rank thresholds:

- S: 40 or higher
- A: 30-39.99
- B: 20-29.99
- C: 10-19.99
- D: 0-9.99

Recommended hierarchy:

```text
ParameterScoresPanel
  BarContainer
    ParameterScoreBar instances
  ParameterScoresText optional fallback
```

Create ParameterScoreBar prefab:

```text
ParameterScoreBar
  LabelText
  BarBackground
    BarFill
  ValueText
```

Inspector wiring:

1. Add ParameterScoreBarView to the ParameterScoreBar row root.
2. Assign LabelText to Label Text.
3. Assign BarFill RectTransform to Bar Fill.
4. Assign ValueText to Value Text. This displays S/A/B/C/D, not the raw number.
5. Optional: assign the BarFill Image to Bar Fill Image for rank colors.
6. On ParameterScoresPanelView, assign BarContainer to Bar Container.
7. Assign the ParameterScoreBar prefab to Bar Prefab.
8. Optionally assign ParameterScoresText to Output Text as fallback.

If Bar Container or Bar Prefab is not assigned, ParameterScoresPanelView falls back to rank text:

```text
Philosophy   A
Psychology   B
Science   C
```

Use the same ParameterScoresPanelView and ParameterScoreBar prefab for both query_parameters and results[].parameters.


## Parameter Radar Chart Display

ParameterRadarChartView visualizes the same numeric parameter scores as a radar chart. Axis count is dynamic: it uses the number and order of the received scores. `general` can render 10 axes, while filters such as `basic_thought`, `basic_literature`, or `jinn_os` can render 8 axes. The radar chart treats 40 as the outer radius because 40 or higher is S rank. Values above 40 are still preserved as raw scores, but visually clamp to the outer edge.

- philosophy
- psychology
- science
- economics
- karma
- emotion
- morality
- ideal
- individual
- community

Other filters can use fewer axes, for example:

- basic_thought
- basic_literature
- jinn_os

The D-S rank list remains available through ParameterScoresPanelView. The radar chart is an additional visual layer.

Recommended hierarchy:

```text
DetailPanel
  ParameterVisualizationRow
    RankListColumn
      ParameterScoresPanel
    RadarColumn
      ResultRadarChart

QueryParameterPanel
  QueryVisualizationRow
    QueryRankListColumn
      ParameterScoresPanel
    QueryRadarColumn
      QueryRadarChart
```

Recommended layout:

- Rank list: left
- Radar chart: right
- Keep both under the same horizontal row so they do not overlap.

Create a result radar chart:

1. Under DetailPanel/Content, create a UI object named ResultRadarChart.
2. Place it in the right RadarColumn, separate from the rank list. Give it a RectTransform size such as 220 x 220.
3. Add ParameterRadarChartView to ResultRadarChart.
4. Optional: create a child LabelContainer and assign it to Label Container.
5. Optional: create a TMP label prefab and assign it to Label Prefab.
6. On DetailPanelView, assign ResultRadarChart to Radar Chart View.

Create a query radar chart:

1. Under QueryParameterPanel, create a UI object named QueryRadarChart.
2. Place it in the right QueryRadarColumn, separate from the query rank list. Give it a RectTransform size such as 220 x 220.
3. Add ParameterRadarChartView to QueryRadarChart.
4. Optional: assign Label Container and Label Prefab.
5. On QueryParameterPanelView, assign QueryRadarChart to Radar Chart View.

Inspector note:

- Radar max value defaults to 40. Keep this aligned with the D-S rank threshold where S starts at 40.
- Increase Max Value only if the rank system changes later.

Runtime behavior:

- QueryRadarChart renders query_parameters after search.
- ResultRadarChart renders results[].parameters when a result item is clicked.
- Axis count equals the received score count.
- Axis labels are generated from scores[i].key.
- Axis order follows the received score order.
- Scores that are null or empty clear the chart.
- Values are normalized as value / 40 by default. 40 or higher is S rank and reaches the outer radius.
- The chart uses UI mesh drawing, so no FastAPI or API schema changes are required.

For the MVP, query and selected result charts are separate. A future overlay chart can reuse ParameterRadarChartView or extend it to accept two score sets.

## Wire ThoughtMapSearchManager

Select the GameObject with `ThoughtMapSearchManager` and assign:

- `Api Client`: existing `ThoughtMapApiClient`
- `Search Input`: existing search TMP InputField
- `Mode Dropdown`: existing mode TMP Dropdown
- `Source Dropdown`: existing source TMP Dropdown
- `Filter Selector View`: new `FilterSelector`
- `Search Button`: existing search Button
- `Results List View`: existing `SearchResultsListView`
- `Detail Panel View`: new or existing `DetailPanel`
- `Query Parameter Panel View`: new `QueryParameterPanel`
- `Top Results`: keep current value, usually `10`
- `DetailPanelView.Radar Chart View`: optional `ResultRadarChart`
- `QueryParameterPanelView.Radar Chart View`: optional `QueryRadarChart`

## Wire Result Selection

The current script flow is:

```text
ResultItemView click
  -> SearchResultsListView.ResultSelected
  -> ThoughtMapSearchManager.OnResultSelected
  -> DetailPanelView.ShowResult
  -> ParameterScoresPanelView.ShowScores
```

Make sure each `ResultItem` has:

- `ResultItemView`
- `TitleText` assigned
- `AuthorText` assigned
- `SelectButton` assigned, or a Button on the same GameObject



## Detail URL Link

DetailPanelView can show the selected result URL and open it in the system browser.

Unity wiring:

1. Add a TMP Text under DetailPanel/Content named UrlText.
2. Add a Button named OpenLinkButton.
3. On DetailPanelView, assign UrlText to Url Text.
4. On DetailPanelView, assign OpenLinkButton to Open Link Button.

Runtime behavior:

- If result.url is present, UrlText and OpenLinkButton are shown.
- If result.url is empty, both are hidden or disabled.
- Pressing OpenLinkButton calls Application.OpenURL(url).
- Gutendex results can receive inferred Gutenberg URLs from the API.

## Save Selected Result

The DetailPanel can save the selected search result to the backend default user library.

Backend endpoint:

```text
POST /users/default/save
```

Unity wiring:

1. Add a Button under DetailPanel/Content named SaveButton.
2. Add a TMP Text near it named SaveStatusText.
3. On DetailPanelView, assign SaveButton to Save Button.
4. On DetailPanelView, assign SaveStatusText to Save Status Text.
5. Keep ThoughtMapSearchManager.Api Client assigned.

Runtime behavior:

- Selecting a result enables the Save button.
- Pressing Save sends the selected result doc_id and current result parameters.
- On success the status text shows Saved.
- Duplicate saves are skipped by the API and the status text shows Already saved.
- The API writes documents.csv, embeddings.csv, and favorites.json under data/thoughtmap_db/users/default.


## Neon UI Layout Stage 2

This stage improves spacing and hierarchy without changing FastAPI, API schemas, or existing event wiring.

### Add Layout Helper

1. Create an empty GameObject under Canvas named `NeonLayout`.
2. Add `ThoughtMapNeonLayout`.
3. Assign the following RectTransforms where available:
   - `Results Panel` -> the panel containing the results Scroll View
   - `Detail Panel` -> DetailPanel root
   - `Query Parameter Panel` -> QueryParameterPanel root
   - `Result Item Prefab Root` -> ResultItem prefab root
   - `Result Visualization Row` -> horizontal row that contains result rank list and result radar
   - `Result Rank List Column` -> left column containing `ParameterScoresPanel`
   - `Result Radar Column` -> right column containing heading + `ResultRadarChart`
   - `Result Radar Chart` -> selected-result radar chart
   - `Result Radar Heading` -> selected-result radar heading text
   - `Query Visualization Row` -> horizontal row that contains query rank list and query radar
   - `Query Rank List Column` -> left column containing query `ParameterScoresPanel`
   - `Query Radar Column` -> right column containing heading + `QueryRadarChart`
   - `Query Radar Chart` -> query radar chart
   - `Query Radar Heading` -> query radar heading text
   - `Save Button` -> SaveButton RectTransform
   - `Open Link Button` -> OpenLinkButton RectTransform
   - `Url Text` -> UrlText RectTransform
4. Use the component menu `Apply Neon Layout`.

### Recommended DetailPanel Hierarchy

Keep the existing DetailPanel, but group the parameter area like this:

```text
DetailPanel
  HeaderRow
    Title/Author/Source/DocId/Score
    SaveButton
  LinkRow
    UrlText              (shows Source Link, not full URL)
    OpenLinkButton       (Open Link)
  BodyText
  ResultVisualizationRow
    RankListColumn
      ParameterScoresPanel
    RadarColumn
      RadarHeadingText   (Selected Document Profile)
      ResultRadarChart
```

For query parameters:

```text
QueryParameterPanel
  QueryVisualizationRow
    QueryRankListColumn
      ParameterScoresPanel
    QueryRadarColumn
      QueryRadarHeadingText (Search Query Profile)
      QueryRadarChart
```

### Layout Rules

- Rank list goes left.
- Radar chart goes right.
- Radar heading must be above the radar chart inside the radar column.
- Do not place heading under the chart.
- Keep SaveButton and OpenLinkButton as horizontal buttons with LayoutElement sizes from `ThoughtMapNeonLayout`.
- `DetailPanelView` displays URL text as `Source Link`; the full URL is still stored internally and used by `Application.OpenURL`.
- Selected result item uses a stronger cyan outline; non-selected items keep a dim outline.

### Button Labels

- SaveButton label is set by script to `☆ Save to My Library`.
- OpenLinkButton label is set by script to `Open Link`.

If the Save button still looks like a checkbox, check that the GameObject assigned to `DetailPanelView.Save Button` is a Button root with a normal Image background, not a Toggle or small child graphic.

## FastAPI Request Behavior

Current Unity request shape:

```text
/search?q=...&top=...&mode=...&source=...&filter=...
```

Rules:

- `source=all` is omitted by `ThoughtMapApiClient`.
- `filter=all` is omitted by `ThoughtMapApiClient`.
- `filter=general` requests parameter scores from FastAPI.
- Existing search results continue to display only title/author in the result list.

## Smoke Test

1. Start FastAPI with the desired backend.
2. Open `ThoughtMapMain` in Unity.
3. Press Play.
4. Search `Plato` with:
   - Mode: `keyword` or `semantic`
   - Source: `all` or `gutendex`
   - Filter: `general`
5. Confirm the result list still populates.
6. Click one result.
7. Confirm the right Detail Panel updates.
8. Confirm Query Parameter Panel shows D-S rank rows or bars when the API returns `query_parameters`.
9. Confirm QueryRadarChart draws when `query_parameters` are present.
10. Confirm selected-result Parameter Scores show D-S rank rows or bars when the API returns `results[].parameters`.
11. Confirm ResultRadarChart draws after clicking a result with `results[].parameters`.

## Troubleshooting

- If search still works but DetailPanel does not update, check `ThoughtMapSearchManager.Detail Panel View`.
- If clicking a result does nothing, check `ResultItemView.Select Button` and the Button component.
- If filter is always `all`, check `ThoughtMapSearchManager.Filter Selector View` and `FilterSelectorView.Filter Dropdown`.
- If parameter rows are missing, test the API URL directly with `filter=general` and check that `parameters` is included in the JSON.
- If Unity shows script references as missing, reimport the `Assets/Scripts` folder.
## Neon Layout Recovery / Safe Layout

If applying the old `ThoughtMapNeonLayout` caused invisible result items or overlapping radar/rank text, the likely cause is that LayoutGroup components were added to objects that already had hand-authored RectTransforms.

The safe layout helper no longer changes panel roots automatically. `Apply On Enable` is off by default.

### Cleanup after the old layout helper

1. Select the `NeonLayout` object.
2. In `Unsafe Layout Roots To Clean`, temporarily assign objects that were affected by the previous helper, for example:
   - `DetailPanel`
   - `QueryParameterPanel`
   - `Scroll View` root, if it received a LayoutGroup
   - `ResultVisualizationRow`, if it was not intentionally a layout container
   - `QueryVisualizationRow`, if it was not intentionally a layout container
   - `ParameterScoresText`, if it received a VerticalLayoutGroup
   - `ResultRadarChart`, if it received a VerticalLayoutGroup
   - `QueryRadarChart`, if it received a VerticalLayoutGroup
3. Run the component menu `Remove Unsafe Layout From Assigned Roots`.
4. Remove those temporary cleanup references when the scene looks normal again.

### Safe assignments

Use only these fields for normal operation:

- `Result List Content`: assign `Scroll View/Viewport/Content`, not the Scroll View root.
- `Save Button`: assign the SaveButton root RectTransform.
- `Open Link Button`: assign the OpenLinkButton root RectTransform.
- `Url Text`: assign UrlText RectTransform.
- `Result Radar Chart`: assign ResultRadarChart RectTransform.
- `Query Radar Chart`: assign QueryRadarChart RectTransform.

Then run `Apply Safe Neon Layout` manually from the component menu.

### What this safe helper does not do

- It does not add LayoutGroup to `DetailPanel`.
- It does not add LayoutGroup to `Scroll View` root or `Viewport`.
- It does not move anchors, pivots, positions, or sizes of main panels.
- It does not arrange the whole scene automatically.
- It does not touch FastAPI, API schema, Repository, SQLite, or CSV behavior.

### Result list visibility check

For the result list, the only object that should normally have `VerticalLayoutGroup` and `ContentSizeFitter` is:

```text
Scroll View
  Viewport
    Content   <-- VerticalLayoutGroup + ContentSizeFitter
      ResultItem(Clone)
```

Each `ResultItem(Clone)` should have a `LayoutElement` with a preferred height around 74.
## Stable Prefab / Panel Layout Structure

The Unity UI should no longer rely on manually nudging Pos Y values after every change. Use dedicated containers with LayoutGroup components instead.

`ThoughtMapNeonTheme` is responsible for colors. `ThoughtMapNeonLayout` is responsible only for safe container setup and recovery. Keep them separate.

### Important rule

Do not add LayoutGroup components directly to hand-positioned roots such as `DetailPanel`, `Scroll View`, `Viewport`, `ResultRadarChart`, `QueryRadarChart`, `SaveButton`, or `OpenLinkButton`.

LayoutGroup should be used only on dedicated containers such as:

```text
DetailPanel
  DetailContent
    HeaderBlock
    ResultProfileBlock
    SaveBlock
    LinkBlock
    QueryProfileBlock
```

### ThoughtMapNeonLayout context menus

- `Apply Safe Neon Layout`: configures only `Scroll View/Viewport/Content` so generated result items stack correctly.
- `Remove Unsafe Layout From Assigned Roots`: removes old unsafe LayoutGroup, LayoutElement, and ContentSizeFitter components from assigned cleanup targets.
- `Rebuild Detail Panel Layout`: creates `DetailContent` and the five stable blocks under `DetailPanel`, then reparents assigned UI elements into those blocks.

`ThoughtMapNeonLayout` does not run automatically on enable. Apply layout actions manually from the component menu.

### Recommended Inspector wiring

On `NeonLayout`, assign:

- `Result List Content`: `Scroll View/Viewport/Content` only
- `Detail Panel`: `DetailPanel` root
- `Detail Content Parent`: optional existing `DetailPanelView.ContentRoot`; use this if your DetailPanel has a Content object that is toggled by script
- `Header Block Items`: `TitleText`, `AuthorText`, `SourceText`, `DocIdText`, `SimilarityText`, `BodyText` if you want them stacked at the top
- `Result Profile Items`: selected-result rank panel/text, selected-result heading, selected-result radar chart
- `Save Block Items`: `SaveButton`, `SaveStatusText`
- `Link Block Items`: `UrlText`, `OpenLinkButton`
- `Query Profile Items`: query heading, query rank panel/text, query radar chart
- `Known Controls`: assign `SaveButton`, `OpenLinkButton`, `UrlText`, `ResultRadarChart`, and `QueryRadarChart` so cleanup can remove old unsafe components from them

Then run:

1. `Remove Unsafe Layout From Assigned Roots`
2. `Rebuild Detail Panel Layout`
3. `Apply Safe Neon Layout`

### Cleanup targets after the old layout helper

If the scene still overlaps, add these to `Unsafe Layout Roots To Clean` and run cleanup again:

- `DetailPanel`
- `Scroll View` root
- `Viewport`
- `ResultVisualizationRow`
- `QueryVisualizationRow`
- `ParameterScoresText`
- `ResultRadarChart`
- `QueryRadarChart`
- `SaveButton`
- `OpenLinkButton`

After cleanup, only `Scroll View/Viewport/Content` should normally have `VerticalLayoutGroup` and `ContentSizeFitter` for the result list.

### Result list structure

```text
Scroll View
  Viewport
    Content
      ResultItem(Clone)
      ResultItem(Clone)
```

`Apply Safe Neon Layout` may add `VerticalLayoutGroup` and `ContentSizeFitter` only to `Content`. It may add `LayoutElement` only to generated result item children, not to buttons or radar charts.

### DetailPanel structure

```text
DetailPanel
  DetailContent
    HeaderBlock
      TitleText
      AuthorText
      SourceText
      DocIdText
      SimilarityText
      BodyText
    ResultProfileBlock
      ParameterScoresPanel or ParameterScoresText
      ResultRadarHeading
      ResultRadarChart
    SaveBlock
      SaveButton
      SaveStatusText
    LinkBlock
      UrlText
      OpenLinkButton
    QueryProfileBlock
      QueryRadarHeading
      QueryParameterScoresText or panel
      QueryRadarChart
```

This keeps future UI changes manageable by editing spacing and padding on containers rather than fixed coordinates.
## Non-Destructive Detail Layout Rebuild

`Rebuild Detail Panel Layout` is intentionally conservative. It creates only empty containers:

```text
DetailContent
  HeaderBlock
  ResultProfileBlock
  SaveBlock
  LinkBlock
  QueryProfileBlock
```

It does not move existing TextMeshPro, Button, RadarChart, ParameterScores, or other UI objects. This prevents the current scene from being broken by partial reparenting or mismatched preferred sizes.

Recommended recovery flow:

1. Run `Remove Unsafe Layout From Assigned Roots` to remove old unsafe layout components.
2. Run `Rebuild Detail Panel Layout` to create empty stable containers only.
3. Confirm the existing UI still appears as before.
4. Move UI objects into the new blocks manually, one small group at a time, only after adding proper LayoutElement or wrapper objects where needed.

For radar charts, create a wrapper object first:

```text
ResultRadarSlot
  ResultRadarChart
```

Put `LayoutElement` on `ResultRadarSlot`, not directly on the chart object. Do the same for query radar charts. For long TMP text, prefer a wrapper or an explicit `LayoutElement` with a stable preferred height.
## Neon Animation Pass

This pass adds visual motion without changing the existing UI layout. It does not modify FastAPI, API schemas, Repository code, RectTransform anchors, or parent/child scene structure.

### Added animation components

- `NeonUIFade`: fades a UI object in with CanvasGroup.
- `NeonSlideIn`: temporarily slides a panel from an offset and returns it to its original anchored position.
- `NeonHoverGlow`: adds neon hover/press glow to Button-like UI objects using Image and Outline.
- `NeonPanelPulse`: adds a subtle cyber-style pulsing outline to panel frames.
- `LoadingIndicatorView`: shows a fading loading overlay and optional rotating spinner while search is running.

### Automatic hooks

- Search result items fade in when `SearchResultsListView.ShowResults()` creates them.
- DetailPanel slides in when `DetailPanelView.ShowResult()` displays a selected result.
- Radar chart values animate from 0 to their score when `ParameterRadarChartView.ShowScores()` is called.
- Search, Save, and Open Link buttons receive `NeonHoverGlow` at runtime if it is missing.
- `ThoughtMapSearchManager` can show/hide `LoadingIndicatorView` during API search if assigned.

### Optional Unity Editor setup

For loading:

1. Create a small overlay object, for example `SearchLoadingIndicator`.
2. Add `CanvasGroup` and `LoadingIndicatorView`.
3. Optional: add a child image as `Spinner`.
4. Optional: add TMP text as `Status Text`.
5. Assign it to `ThoughtMapSearchManager.Loading Indicator View`.

For panel glow:

1. Add `NeonPanelPulse` to `DetailPanel`, result list panel, or other card-like panel roots.
2. Make sure the object has an `Outline`, or let the component add one at runtime.

For button glow:

- Search, Save, and Open Link are wired automatically.
- Add `NeonHoverGlow` manually to dropdowns or other buttons if needed.

### Safety notes

- These animation scripts do not rebuild layout.
- They do not add LayoutGroup to existing objects.
- `NeonSlideIn` stores the original anchored position and only offsets it temporarily during Play mode.
- `NeonUIFade` may add CanvasGroup to the target object.
- `NeonHoverGlow` may add Outline to the target object.
## ThoughtMapDetailPanelV2 Prefab

`ThoughtMapDetailPanelV2.prefab` is a new standalone detail panel. It does not modify the existing scene DetailPanel, RectTransforms, or hierarchy.

Files:

- `Assets/Prefabs/ThoughtMapDetailPanelV2.prefab`
- `Assets/Scripts/UI/ThoughtMapDetailPanelV2View.cs`

Purpose:

- Receive the same `ThoughtMapSearchResult` data used by the current DetailPanel.
- Display title, author, source, doc_id, similarity, URL label, parameter ranks, and radar chart.
- Provide Save and Open Link buttons inside the prefab.
- Build its own internal `DetailContent` UI at runtime, so existing scene UI is not rearranged.

Usage:

1. Drag `ThoughtMapDetailPanelV2.prefab` into the Canvas.
2. Position the prefab root manually where the right detail panel should appear.
3. Do not run `ThoughtMapNeonLayout` on the existing DetailPanel for this prefab workflow.
4. To test data binding, call `ThoughtMapDetailPanelV2View.ShowResult(result)` from the same place that currently calls `DetailPanelView.ShowResult(result)`.

Notes:

- This prefab is intentionally isolated from the existing DetailPanel.
- It does not require old UI text fields to be assigned in the Inspector.
- It creates its child UI under its own root at runtime.
- It does not change FastAPI, API schema, Repository, SQLite, or CSV behavior.
- It is safe to keep the old DetailPanel in the scene while testing V2 separately.
## ThoughtMapDemoUI + DetailPanelV2 Wiring

Current scene flow may use `ThoughtMapDemoUI` directly instead of `ThoughtMapSearchManager`:

```text
SearchButton -> ThoughtMapDemoUI.OnSearchClicked()
```

The repository copy used by Codex did not include `ThoughtMapDemoUI.cs`, so the existing scene script was not modified directly. Use the following minimal patch in the local `ThoughtMapDemoUI` script.

### Add fields

Keep the old `DetailPanelView` field. Add V2 and a switch:

```csharp
[SerializeField] private DetailPanelView detailPanelView;
[SerializeField] private ThoughtMapDetailPanelV2View detailPanelV2;
[SerializeField] private bool useDetailPanelV2 = true;
```

### On result click

Where `ThoughtMapDemoUI` currently handles a clicked result, call V2 when enabled:

```csharp
private void OnResultClicked(ThoughtMapSearchResult result)
{
    if (useDetailPanelV2 && detailPanelV2 != null)
    {
        detailPanelV2.ShowResult(result);
        return;
    }

    if (detailPanelView != null)
    {
        detailPanelView.ShowResult(result);
    }
}
```

If the local method has a different name, add the same block at the point where the old detail panel currently receives the selected result.

### Optional router component

`ThoughtMapDetailPanelRouter` was added as a small helper. It can sit on the same GameObject as `ThoughtMapDemoUI` and hold:

- `Legacy Detail Panel`
- `Detail Panel V2`
- `Use Detail Panel V2`

Then `ThoughtMapDemoUI` can call:

```csharp
[SerializeField] private ThoughtMapDetailPanelRouter detailPanelRouter;

// On result click:
detailPanelRouter?.ShowResult(result);
```

### Inspector steps

1. Drag `ThoughtMapDetailPanelV2.prefab` into the Canvas.
2. Select the GameObject with `ThoughtMapDemoUI`.
3. Drag the V2 prefab instance into `Detail Panel V2`.
4. Keep the old `DetailPanelView` assignment in place.
5. Toggle `Use Detail Panel V2` to switch between old and new detail panels.

FastAPI, API schema, Repository, SQLite, and CSV behavior are unchanged.
## ThoughtMapRuntimeController Wiring

Use `ThoughtMapRuntimeController` when the scene has a missing or hidden `ThoughtMapDemoUI` reference. This controller does not depend on `ThoughtMapDemoUI` and does not modify the old DetailPanel.

### Scene setup

1. Create an empty GameObject under Canvas named `ThoughtMapRuntimeController`.
2. Add the `ThoughtMapRuntimeController` component.
3. Assign Inspector fields:
   - `Api Client`: existing `ThoughtMapApiClient`
   - `Search Button`: existing Search button
   - `Search Input`: existing TMP input field
   - `Mode Dropdown`: existing mode dropdown
   - `Source Dropdown`: existing source dropdown
   - `Filter Dropdown`: existing filter dropdown
   - `Search Results List View`: existing result list view
   - `Detail Panel V2`: `ThoughtMapDetailPanelV2` prefab instance
   - `Loading Indicator View`: optional
   - `Query Parameter Panel View`: optional

### Replace SearchButton OnClick

1. Select `SearchButton`.
2. In the Button OnClick list, remove the old `ThoughtMapDemoUI.OnSearchClicked` entry.
3. Add a new OnClick entry.
4. Drag the GameObject with `ThoughtMapRuntimeController` into the target slot.
5. Select `ThoughtMapRuntimeController.OnSearchClicked()`.

### Runtime behavior

```text
SearchButton
  -> ThoughtMapRuntimeController.OnSearchClicked()
  -> ThoughtMapApiClient.Search()
  -> SearchResultsListView.ShowResults()
  -> SearchResultsListView.ResultSelected
  -> ThoughtMapDetailPanelV2View.ShowResult(result)
```

### Notes

- Existing `ThoughtMapDemoUI` and `DetailPanelView` are not touched.
- FastAPI, API schema, Repository, SQLite, and CSV behavior are unchanged.
- The old scene can remain intact while V2 is tested by switching only the SearchButton OnClick target.
## DetailPanelV2 Japanese Font Setup

If Japanese titles render as squares in `ThoughtMapDetailPanelV2`, assign the same TMP Font Asset used by the existing scene text that already displays Japanese correctly.

Recommended setup:

1. Select the `ThoughtMapDetailPanelV2` prefab instance in the scene.
2. In `ThoughtMapDetailPanelV2View`, assign `Japanese Font Asset` to the TMP Font Asset used by the working Japanese scene text.
3. Alternatively, drag an existing TMP text object that already displays Japanese correctly into `Font Reference Text`. V2 copies that text component font at runtime.
4. If the prefab has already generated child texts, use the component menu `Apply Font To Generated Texts`.

V2 now applies the chosen font to all generated text objects, including title, author, metadata, parameter scores, URL label, save status, and button labels.

V2 visual tuning:

- Wider root default size: 620 x 760
- Larger header and profile spacing
- Larger radar slot: 270 x 270
- Larger parameter text area: 250 x 240
- Parameter text uses larger font and wider line spacing
- Save button: 220 x 44
- Open Link button: 150 x 42
- Text uses wrapping/ellipsis to avoid crushing Japanese strings

Existing scene RectTransforms are not modified by these changes.
## DetailPanelV2 Design Tuning

`ThoughtMapDetailPanelV2View` now exposes visual tuning values in the Inspector so the V2 prefab can be adjusted without editing code or touching the old scene UI.

Inspector fields:

- `Radar Size`: default `330 x 330`
- `Title Font Size`: default `22`
- `Body Font Size`: default `14`
- `Block Spacing`: default `16`
- `Block Padding`: default `18`
- `Parameter Scores Size`: default `260 x 330`
- `Open Button Size`: default `150 x 42`
- `Save Button Size`: default `230 x 42`

Profile layout:

```text
ResultProfileBlock
  ProfileHeadingText
  ProfileRow
    ParameterScoresText   // left
    RadarSlot
      ResultRadarChart    // right, large
```

Action layout:

```text
ActionBlock
  Source Link
  Open Link
  ☆ Save to My Library
  SaveStatusText
```

If you already generated V2 child UI in Play Mode, stop Play and run again. Runtime-generated children are not intended to be edited as the source of truth; tune the serialized values on the prefab root instead.

Existing scene RectTransforms and the old DetailPanel are not modified by these V2 tuning fields.
## DetailPanelV2 Design Adjustment Phase

This phase keeps the runtime build approach and exposes more layout values in the Inspector. Existing scene RectTransforms, the old DetailPanel, FastAPI, API schema, and Repository code are not changed.

Primary Inspector controls:

- `Radar Size`: default `420 x 420`
- `Title Font Size`: default `28`
- `Body Font Size`: default `16`
- `Block Spacing`: default `18`
- `Block Padding`: default `22`
- `Header Height`: default `150`
- `Profile Height`: default `500`
- `Action Height`: default `74`
- `Footer Height`: default `64`
- `Parameter Width Ratio`: default `0.4`
- `Radar Width Ratio`: default `0.6`
- `Open Button Size`: default `170 x 52`
- `Save Button Size`: default `250 x 52`

The selected profile area is designed as:

```text
ResultProfileBlock
  Selected Document Profile
  ProfileRow
    ParameterScoresText  // left, 40%
    RadarSlot            // right, 60%
      ResultRadarChart
```

The action area is:

```text
ActionBlock
  Source Link
  Open Link
  ☆ Save to My Library
  SaveStatusText
```

When changing the panel root size in Unity, adjust `Header Height`, `Profile Height`, `Action Height`, and `Footer Height` first. Then tune `Parameter Width Ratio` and `Radar Width Ratio` if the score list and chart need a different split.
## V2 Prefab Window UI Direction

Future ThoughtMap UI work should prefer prefab windows instead of modifying existing scene-placed UI directly.

New left-side V2 prefabs:

- `Assets/Prefabs/SearchHeaderV2.prefab`
- `Assets/Prefabs/ResultListV2.prefab`
- `Assets/Prefabs/ResultItemV2.prefab`

Runtime scripts:

- `SearchHeaderV2View`
- `ResultListV2View`
- `ResultItemV2View`

Each V2 prefab is built around a future window structure:

```text
WindowRoot
  TitleBar
  ContentArea
  ActionArea
```

This structure is intended to support later add-on components such as:

- `DraggableWindow`
- `NeonUIFade`
- `NeonSlideIn`
- `NeonHoverGlow`
- `NeonPanelPulse`

### RuntimeController V2 assignment

`ThoughtMapRuntimeController` now supports V2 window assignments while keeping the old scene UI fields intact.

Assign:

- `Search Header V2`: instance of `SearchHeaderV2.prefab`
- `Result List V2`: instance of `ResultListV2.prefab`
- `Detail Panel V2`: instance of `ThoughtMapDetailPanelV2.prefab`
- `Api Client`: existing `ThoughtMapApiClient`

When V2 fields are assigned:

```text
SearchHeaderV2.SearchRequested
  -> ThoughtMapRuntimeController.OnSearchClicked()
  -> ThoughtMapApiClient.Search()
  -> ResultListV2.ShowResults()
  -> ResultListV2.ResultSelected
  -> ThoughtMapDetailPanelV2.ShowResult(result)
```

Old scene fields can remain assigned as fallback. If both old and V2 result lists are assigned, V2 is preferred for displaying results.

### Japanese font

All V2 view scripts expose:

- `Japanese Font Asset`
- `Font Reference Text`

Assign the same TMP Font Asset or reference text used by the existing Japanese-capable scene UI.

### Notes

- Existing scene RectTransforms are not modified.
- Existing `ThoughtMapDemoUI` and old `DetailPanelView` are not required for the V2 flow.
- FastAPI, API schema, Repository, SQLite, and CSV behavior are unchanged.
