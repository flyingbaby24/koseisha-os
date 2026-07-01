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
```

## Responsibilities

- `ThoughtMapApiClient`: HTTP only.
- `ThoughtMapSearchManager`: connects input/button to API and result list.
- `SearchResultsListView`: owns ScrollView content creation/clearing.
- `ResultItemView`: binds one search result to prefab text fields.
- `SearchModels`: JSON response models.

## Scene wiring

1. Add `ThoughtMapApiClient` to a scene object.
2. Add `SearchResultsListView` to the ScrollView or another UI object.
3. Add `ThoughtMapSearchManager` to a scene object.
4. Assign:
   - API Client
   - Search Input: `TMP_InputField`
   - Search Button: `Button`
   - Results List View
5. In `SearchResultsListView`, assign:
   - Results Content: ScrollView Content transform
   - Result Item Prefab: prefab with `ResultItemView`
6. On the prefab, assign title and author TMP text fields.

## Local API URL

Default API URL is:

```text
http://127.0.0.1:8000
```

For a device or WebGL build, replace it with a reachable host URL.
Unity should not know whether the backend uses CSV or SQLite.
