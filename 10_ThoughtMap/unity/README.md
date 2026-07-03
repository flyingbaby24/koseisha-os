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
