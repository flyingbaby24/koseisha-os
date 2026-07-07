#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public static class ThoughtMapV2SceneInstaller
{
    private const string SearchHeaderPrefabPath = "Assets/Prefabs/SearchHeaderV2.prefab";
    private const string ResultListPrefabPath = "Assets/Prefabs/ResultListV2.prefab";
    private const string ResultItemPrefabPath = "Assets/Prefabs/ResultItemV2.prefab";
    private const string DetailPanelPrefabPath = "Assets/Prefabs/ThoughtMapDetailPanelV2.prefab";

    [MenuItem("Tools/ThoughtMap/Install V2 Prefabs In Current Scene")]
    public static void InstallV2PrefabsInCurrentScene()
    {
        Canvas canvas = Object.FindObjectOfType<Canvas>();
        if (canvas == null)
        {
            Debug.LogError("[ThoughtMapV2SceneInstaller] No Canvas found in the current scene.");
            return;
        }

        SearchHeaderV2View searchHeader = EnsurePrefabInstance<SearchHeaderV2View>(SearchHeaderPrefabPath, canvas.transform, "SearchHeaderV2");
        ResultListV2View resultList = EnsurePrefabInstance<ResultListV2View>(ResultListPrefabPath, canvas.transform, "ResultListV2");
        ThoughtMapDetailPanelV2View detailPanel = EnsurePrefabInstance<ThoughtMapDetailPanelV2View>(DetailPanelPrefabPath, canvas.transform, "ThoughtMapDetailPanelV2");
        ResultItemV2View resultItemPrefab = LoadPrefabComponent<ResultItemV2View>(ResultItemPrefabPath);

        if (resultList != null && resultItemPrefab != null)
        {
            SerializedObject resultListObject = new SerializedObject(resultList);
            resultListObject.FindProperty("resultItemPrefab").objectReferenceValue = resultItemPrefab;
            resultListObject.ApplyModifiedPropertiesWithoutUndo();
        }

        ThoughtMapRuntimeController controller = EnsureRuntimeController(canvas.transform);
        WireRuntimeController(controller, searchHeader, resultList, detailPanel);
        HideLegacyUi(canvas.transform);
        DisableLegacyManager();

        EditorUtility.SetDirty(canvas.gameObject);
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        Debug.Log("[ThoughtMapV2SceneInstaller] V2 prefabs installed under Canvas. Press Play and search to see [ResultListV2], [ResultItemV2], and [ThoughtMapDetailPanelV2] logs.");
    }

    private static T EnsurePrefabInstance<T>(string prefabPath, Transform parent, string instanceName) where T : Component
    {
        T existing = FindChildComponent<T>(parent, instanceName);
        if (existing != null)
        {
            existing.gameObject.SetActive(true);
            existing.SendMessage("BuildIfNeeded", SendMessageOptions.DontRequireReceiver);
            return existing;
        }

        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        if (prefab == null)
        {
            Debug.LogError($"[ThoughtMapV2SceneInstaller] Missing prefab: {prefabPath}");
            return null;
        }

        GameObject instance = PrefabUtility.InstantiatePrefab(prefab, parent) as GameObject;
        if (instance == null)
        {
            Debug.LogError($"[ThoughtMapV2SceneInstaller] Could not instantiate prefab: {prefabPath}");
            return null;
        }

        instance.name = instanceName;
        T component = instance.GetComponent<T>();
        if (component == null)
        {
            Debug.LogError($"[ThoughtMapV2SceneInstaller] Prefab does not contain component {typeof(T).Name}: {prefabPath}");
            return null;
        }

        component.SendMessage("BuildIfNeeded", SendMessageOptions.DontRequireReceiver);
        Undo.RegisterCreatedObjectUndo(instance, $"Create {instanceName}");
        return component;
    }

    private static T LoadPrefabComponent<T>(string prefabPath) where T : Component
    {
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        return prefab == null ? null : prefab.GetComponent<T>();
    }

    private static ThoughtMapRuntimeController EnsureRuntimeController(Transform parent)
    {
        ThoughtMapRuntimeController existing = Object.FindObjectOfType<ThoughtMapRuntimeController>();
        if (existing != null)
        {
            existing.gameObject.SetActive(true);
            return existing;
        }

        GameObject controllerObject = new GameObject("ThoughtMapRuntimeControllerV2", typeof(RectTransform), typeof(ThoughtMapRuntimeController));
        controllerObject.transform.SetParent(parent, false);
        Undo.RegisterCreatedObjectUndo(controllerObject, "Create ThoughtMapRuntimeControllerV2");
        return controllerObject.GetComponent<ThoughtMapRuntimeController>();
    }

    private static void WireRuntimeController(
        ThoughtMapRuntimeController controller,
        SearchHeaderV2View searchHeader,
        ResultListV2View resultList,
        ThoughtMapDetailPanelV2View detailPanel)
    {
        if (controller == null) return;

        SerializedObject controllerObject = new SerializedObject(controller);
        SetObject(controllerObject, "apiClient", Object.FindObjectOfType<ThoughtMapApiClient>());
        SetObject(controllerObject, "searchHeaderV2", searchHeader);
        SetObject(controllerObject, "resultListV2", resultList);
        SetObject(controllerObject, "detailPanelV2", detailPanel);
        // V2 input is owned by SearchHeaderV2. Keep legacy UI references empty to avoid duplicate button listeners.
        SetObject(controllerObject, "searchInput", null);
        SetObject(controllerObject, "searchButton", null);
        SetObject(controllerObject, "modeDropdown", null);
        SetObject(controllerObject, "sourceDropdown", null);
        SetObject(controllerObject, "filterDropdown", null);
        controllerObject.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(controller);
    }

    private static void SetObject(SerializedObject serializedObject, string propertyName, Object value)
    {
        SerializedProperty property = serializedObject.FindProperty(propertyName);
        if (property != null)
        {
            property.objectReferenceValue = value;
        }
    }

    private static TMP_Dropdown FindDropdownByName(string name)
    {
        TMP_Dropdown[] dropdowns = Resources.FindObjectsOfTypeAll<TMP_Dropdown>();
        foreach (TMP_Dropdown dropdown in dropdowns)
        {
            if (dropdown != null && !EditorUtility.IsPersistent(dropdown) && dropdown.name == name)
            {
                return dropdown;
            }
        }
        return null;
    }

    private static T FindChildComponent<T>(Transform parent, string childName) where T : Component
    {
        T[] components = parent.GetComponentsInChildren<T>(true);
        foreach (T component in components)
        {
            if (component != null && component.name == childName)
            {
                return component;
            }
        }
        return null;
    }

    private static void HideLegacyUi(Transform canvas)
    {
        string[] legacyNames =
        {
            "SearchInput",
            "SearchButton",
            "Scroll View",
            "ModeDropdown",
            "SourceDropdown",
            "FilterDropdown",
            "DetailPanel",
            "QueryParameterScoresText",
            "QueryRadarChart",
            "QueryRadarHeadingText"
        };

        foreach (string legacyName in legacyNames)
        {
            Transform target = FindDirectOrNested(canvas, legacyName);
            if (target != null && !IsV2Object(target))
            {
                target.gameObject.SetActive(false);
            }
        }
    }

    private static Transform FindDirectOrNested(Transform root, string name)
    {
        Transform[] children = root.GetComponentsInChildren<Transform>(true);
        foreach (Transform child in children)
        {
            if (child != null && child.name == name)
            {
                return child;
            }
        }
        return null;
    }

    private static bool IsV2Object(Transform target)
    {
        return target.GetComponentInParent<SearchHeaderV2View>(true) != null
            || target.GetComponentInParent<ResultListV2View>(true) != null
            || target.GetComponentInParent<ThoughtMapDetailPanelV2View>(true) != null;
    }

    private static void DisableLegacyManager()
    {
        ThoughtMapSearchManager legacyManager = Object.FindObjectOfType<ThoughtMapSearchManager>();
        if (legacyManager != null)
        {
            legacyManager.enabled = false;
            EditorUtility.SetDirty(legacyManager);
        }
    }
}
#endif


