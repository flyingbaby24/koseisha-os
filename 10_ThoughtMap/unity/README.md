# ThoughtMap Unity Setup

This guide explains how to wire the current Unity scene to the FastAPI ThoughtMap backend and the new filter/detail/parameter UI placeholders.

The current repository copy contains Unity scripts, but no editable scene or prefab asset is present here. Update `ThoughtMapMain` in the Unity Editor using the steps below.

## Goal

Add these UI pieces to the existing `ThoughtMapMain` scene without breaking the current search flow:

- Filter Dropdown for `filters/*.json` selection
- Right-side Detail Panel
- Parameter Scores Panel inside the Detail Panel
- Inspector references for `ThoughtMapSearchManager`, `DetailPanelView`, and `FilterSelectorView`

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
8. Confirm Query Parameter Panel shows key/value rows when the API returns `query_parameters`.
9. Confirm selected-result Parameter Scores show key/value rows when the API returns `results[].parameters`.

## Troubleshooting

- If search still works but DetailPanel does not update, check `ThoughtMapSearchManager.Detail Panel View`.
- If clicking a result does nothing, check `ResultItemView.Select Button` and the Button component.
- If filter is always `all`, check `ThoughtMapSearchManager.Filter Selector View` and `FilterSelectorView.Filter Dropdown`.
- If parameter rows are missing, test the API URL directly with `filter=general` and check that `parameters` is included in the JSON.
- If Unity shows script references as missing, reimport the `Assets/Scripts` folder.
