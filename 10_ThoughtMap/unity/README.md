# ThoughtMap Unity HTTP integration

These scripts keep Unity as a frontend and the Python/FastAPI service as the
ThoughtMap search engine.

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
```

## Scene wiring

1. Add `ThoughtMapApiClient` to a scene object.
2. Add `ThoughtMapSearchManager` to a scene object.
3. Assign:
   - Search Input: `TMP_InputField`
   - Search Button: `Button`
   - Results Content: ScrollView Content transform
   - Result Item Prefab: prefab with `ResultItemView`
4. On the prefab, assign title and author TMP text fields.

## Local API URL

Default API URL is:

```text
http://127.0.0.1:8000
```

For a device or WebGL build, replace it with a reachable host URL.
