# ThoughtMap Unity HTTP integration

Unity is the frontend. FastAPI/Python is the search engine.

## Unity folders

```text
Assets/Scripts/
  API/
    ThoughtMapApiClient.cs
  Managers/
    ThoughtMapSearchManager.cs
  Models/
    SearchModels.cs
  UI/
    ResultItemView.cs
    SearchResultsListView.cs
    DetailPanelView.cs
```

## Responsibilities

- `ThoughtMapApiClient`: HTTP only.
- `ThoughtMapSearchManager`: connects input/button to API and result list.
- `SearchResultsListView`: owns ScrollView content creation/clearing and result selection events.
- `ResultItemView`: binds one search result to prefab text fields and emits click selection.
- `DetailPanelView`: owns the right-side detail panel display.
- `SearchModels`: JSON response models.

## Scene wiring

1. Add `ThoughtMapApiClient` to a scene object.
2. Add `SearchResultsListView` to the ScrollView or another UI object.
3. Add `ThoughtMapSearchManager` to a scene object.
4. Assign:
   - API Client
   - Search Input: `TMP_InputField`
   - Search Button: `Button`
   - Mode Dropdown: `TMP_Dropdown` with `semantic`, `keyword`, `hybrid`
   - Source Dropdown: `TMP_Dropdown` with `all`, `gutendex`, `user_suno`
   - Results List View
   - Detail Panel View
5. In `SearchResultsListView`, assign:
   - Results Content: ScrollView Content transform
   - Result Item Prefab: prefab with `ResultItemView`
6. On the prefab, assign title and author TMP text fields. Add or assign a `Button` for click selection.
7. Create a right-side ScrollView or panel for details and add `DetailPanelView`. Assign:
   - Empty State Root, optional
   - Content Root, optional
   - Title Text
   - Author Text
   - Source Text
   - Doc ID Text
   - Similarity Text
   - Body Text

Selecting a result currently shows placeholder detail data from the search result. A future `GET /document/{doc_id}` call should be triggered from `ThoughtMapSearchManager.OnResultSelected`.

## Local API URL

Default API URL is:

```text
http://127.0.0.1:8000
```

For a device or WebGL build, replace it with a reachable host URL.
Unity should not know whether the backend uses CSV or SQLite.

## Search Modes

The Search Manager sends mode and source query parameters to FastAPI:

```text
/search?q=Plato&top=10&mode=keyword
/search?q=Plato&top=10&mode=keyword&source=gutendex
/search?q=Plato&top=10&mode=hybrid
/search?q=Burn&top=10&mode=semantic&source=user_suno
```

When Source Dropdown is `all`, the `source` query parameter is omitted.
