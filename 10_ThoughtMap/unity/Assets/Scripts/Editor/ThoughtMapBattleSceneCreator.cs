#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public static class ThoughtMapBattleSceneCreator
{
    private const string SceneFolder = "Assets/Scenes";
    private const string PrefabFolder = "Assets/Prefabs";
    private const string BattleScenePath = "Assets/Scenes/BattleScene.unity";
    private const string BattlePrepScenePath = "Assets/Scenes/BattlePrepScene.unity";
    private const string ProductBattlePrepScenePath = "Assets/Scenes/ProductBattlePrepScene.unity";
    private const string ProductBattleCardPrefabPath = "Assets/Prefabs/ProductBattleCardPrefab.prefab";
    private const string ProductBattleGridCellPrefabPath = "Assets/Prefabs/ProductBattleGridCellPrefab.prefab";
    private const string PlaceholderCardArtPath = "Assets/Sprites/placeholder_card_art.png";
    private const string PlaceholderAttributeIconPath = "Assets/Sprites/placeholder_attribute_icon.png";

    [MenuItem("Tools/Source of Thought/Create BattleScene")]
    public static void CreateBattleScene()
    {
        EnsureSceneFolder();

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        scene.name = "BattleScene";

        CreateCamera();
        Canvas canvas = CreateCanvas("BattleCanvas");
        CreateEventSystem();
        CreateBattlePlaceholderRoot(canvas.transform);

        EditorSceneManager.SaveScene(scene, BattleScenePath);
        AssetDatabase.Refresh();
        Debug.Log($"[SourceOfThoughtBattleScene] Created {BattleScenePath}. This is a placeholder for the future production Battle scene.");
    }

    [MenuItem("Tools/Source of Thought/Create BattlePrepScene")]
    public static void CreateBattlePrepScene()
    {
        EnsureSceneFolder();

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        scene.name = "BattlePrepScene";

        CreateCamera();
        Canvas canvas = CreateCanvas("BattlePrepCanvas");
        CreateEventSystem();
        CreateDebugBattlePrepRoot(canvas.transform);

        EditorSceneManager.SaveScene(scene, BattlePrepScenePath);
        AssetDatabase.Refresh();
        Debug.Log($"[SourceOfThoughtBattleScene] Created {BattlePrepScenePath}. Open it and press Play to show the Debug Battle Prep screen.");
    }

    [MenuItem("Tools/Source of Thought/Create ProductBattlePrepScene")]
    public static void CreateProductBattlePrepScene()
    {
        EnsureSceneFolder();
        CreateProductBattlePrepPrefabs();

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        scene.name = "ProductBattlePrepScene";

        CreateCamera();
        Canvas canvas = CreateCanvas("ProductBattlePrepCanvas");
        CreateEventSystem();
        CreateProductBattlePrepRoot(canvas.transform);

        EditorSceneManager.SaveScene(scene, ProductBattlePrepScenePath);
        AssetDatabase.Refresh();
        Debug.Log($"[SourceOfThoughtBattleScene] Created {ProductBattlePrepScenePath}. Open it and press Play to show the Product Battle Prep mock UI.");
    }

    [MenuItem("Tools/Source of Thought/Create Product Battle Prep Prefabs")]
    public static void CreateProductBattlePrepPrefabs()
    {
        EnsurePrefabFolder();

        GameObject cardObject = new GameObject("ProductBattleCardPrefab", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ProductBattleCardView));
        cardObject.GetComponent<ProductBattleCardView>().BuildIfNeeded();
        PrefabUtility.SaveAsPrefabAsset(cardObject, ProductBattleCardPrefabPath);
        Object.DestroyImmediate(cardObject);

        GameObject cellObject = new GameObject("ProductBattleGridCellPrefab", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ProductBattleGridCellView));
        cellObject.GetComponent<ProductBattleGridCellView>().BuildIfNeeded();
        PrefabUtility.SaveAsPrefabAsset(cellObject, ProductBattleGridCellPrefabPath);
        Object.DestroyImmediate(cellObject);

        AssetDatabase.Refresh();
        Debug.Log("[SourceOfThoughtBattleScene] Created Product Battle Prep prefabs.");
    }

    [MenuItem("Tools/Source of Thought/Clean Battle UI From Current Search Scene")]
    public static void CleanBattleUiFromCurrentSearchScene()
    {
        Scene scene = SceneManager.GetActiveScene();
        if (!scene.IsValid())
        {
            Debug.LogWarning("[SourceOfThoughtBattleScene] No valid active scene. Nothing was cleaned.");
            return;
        }

        if (scene.name == "BattleScene")
        {
            Debug.LogWarning("[SourceOfThoughtBattleScene] Active scene is BattleScene. Cleanup skipped so the standalone Battle UI is not removed.");
            return;
        }

        int removed = 0;
        GameObject[] roots = scene.GetRootGameObjects();
        for (int index = roots.Length - 1; index >= 0; index--)
        {
            removed += RemoveBattleObjectsRecursive(roots[index]);
        }

        EditorSceneManager.MarkSceneDirty(scene);
        Debug.Log($"[SourceOfThoughtBattleScene] Removed {removed} Battle UI object(s) from {scene.name}. Search UI should now be Battle-free.");
    }

    private static void EnsureSceneFolder()
    {
        if (!AssetDatabase.IsValidFolder(SceneFolder))
        {
            AssetDatabase.CreateFolder("Assets", "Scenes");
        }
    }

    private static void EnsurePrefabFolder()
    {
        if (!AssetDatabase.IsValidFolder(PrefabFolder))
        {
            AssetDatabase.CreateFolder("Assets", "Prefabs");
        }
    }

    private static Camera CreateCamera()
    {
        GameObject cameraObject = new GameObject("Main Camera", typeof(Camera));
        Camera camera = cameraObject.GetComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.005f, 0.018f, 0.05f, 1f);
        camera.orthographic = true;
        cameraObject.tag = "MainCamera";
        cameraObject.transform.position = new Vector3(0f, 0f, -10f);
        return camera;
    }

    private static Canvas CreateCanvas(string canvasName)
    {
        GameObject canvasObject = new GameObject(canvasName, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
        Canvas canvas = canvasObject.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;

        CanvasScaler scaler = canvasObject.GetComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);
        scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
        scaler.matchWidthOrHeight = 0.5f;
        return canvas;
    }

    private static void CreateEventSystem()
    {
        if (Object.FindObjectOfType<EventSystem>() != null)
        {
            return;
        }

        new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
    }

    private static void CreateBattlePlaceholderRoot(Transform parent)
    {
        GameObject root = new GameObject("SourceOfThoughtBattleScenePlaceholder", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
        root.GetComponent<Image>().color = new Color(0.005f, 0.018f, 0.05f, 1f);

        GameObject textObject = new GameObject("Title", typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform textRect = textObject.GetComponent<RectTransform>();
        textRect.SetParent(rect, false);
        textRect.anchorMin = new Vector2(0.5f, 0.5f);
        textRect.anchorMax = new Vector2(0.5f, 0.5f);
        textRect.pivot = new Vector2(0.5f, 0.5f);
        textRect.sizeDelta = new Vector2(980f, 180f);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.text = "Source of Thought - Battle Scene\nFuture production battle display only.\nDeck editing and placement live in BattlePrepScene.";
        text.fontSize = 28;
        text.color = new Color(0.76f, 0.98f, 1f, 1f);
        text.alignment = TextAlignmentOptions.Center;
        EditorUtility.SetDirty(root);
    }

    private static void CreateDebugBattlePrepRoot(Transform parent)
    {
        GameObject root = new GameObject(
            "DebugBattlePrep",
            typeof(RectTransform),
            typeof(ThoughtMapBattleMvpController),
            typeof(ThoughtMapBattleMvpPanelView)
        );
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;

        ThoughtMapBattleMvpController controller = root.GetComponent<ThoughtMapBattleMvpController>();
        ThoughtMapBattleMvpPanelView panel = root.GetComponent<ThoughtMapBattleMvpPanelView>();

        SerializedObject controllerObject = new SerializedObject(controller);
        SetBool(controllerObject, "runOnStart", false);
        SetString(controllerObject, "streamingAssetsCsvPath", "cards.csv");
        SetBool(controllerObject, "useStreamingAssetsFallback", true);
        controllerObject.ApplyModifiedPropertiesWithoutUndo();

        SerializedObject panelObject = new SerializedObject(panel);
        SetObject(panelObject, "controller", controller);
        SetBool(panelObject, "buildOnAwake", true);
        SetBool(panelObject, "showOnStart", true);
        SetVector2(panelObject, "defaultSize", new Vector2(1680f, 1000f));
        SetVector2(panelObject, "defaultPosition", Vector2.zero);
        panelObject.ApplyModifiedPropertiesWithoutUndo();

        EditorUtility.SetDirty(root);
    }

    private static void CreateBattlePrepRoot(Transform parent)
    {
        GameObject root = new GameObject(
            "SourceOfThoughtBattlePrep",
            typeof(RectTransform),
            typeof(ThoughtMapBattlePrepController),
            typeof(ThoughtMapBattlePrepPanelView)
        );
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;

        ThoughtMapBattlePrepController controller = root.GetComponent<ThoughtMapBattlePrepController>();
        ThoughtMapBattlePrepPanelView panel = root.GetComponent<ThoughtMapBattlePrepPanelView>();

        SerializedObject controllerObject = new SerializedObject(controller);
        SetString(controllerObject, "streamingAssetsCsvPath", "cards.csv");
        SetString(controllerObject, "deckFileName", "deck.json");
        SetString(controllerObject, "battleSceneName", "BattleScene");
        controllerObject.ApplyModifiedPropertiesWithoutUndo();

        SerializedObject panelObject = new SerializedObject(panel);
        SetObject(panelObject, "controller", controller);
        SetBool(panelObject, "buildOnAwake", true);
        SetVector2(panelObject, "defaultSize", new Vector2(1180f, 900f));
        SetVector2(panelObject, "defaultPosition", Vector2.zero);
        panelObject.ApplyModifiedPropertiesWithoutUndo();

        EditorUtility.SetDirty(root);
    }

    private static void CreateProductBattlePrepRoot(Transform parent)
    {
        GameObject root = new GameObject(
            "ProductBattlePrepPanel",
            typeof(RectTransform),
            typeof(ProductBattlePrepPanelView)
        );
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        rect.anchorMin = new Vector2(0.5f, 0.5f);
        rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.sizeDelta = new Vector2(1760f, 980f);
        rect.anchoredPosition = Vector2.zero;

        ProductBattlePrepPanelView panel = root.GetComponent<ProductBattlePrepPanelView>();
        SerializedObject panelObject = new SerializedObject(panel);
        SetObject(panelObject, "panelRoot", rect);
        SetString(panelObject, "streamingAssetsCsvPath", "cards.csv");
        SetString(panelObject, "battleSceneName", "BattleScene");
        SetBool(panelObject, "buildOnAwake", true);
        SetVector2(panelObject, "defaultSize", new Vector2(1760f, 980f));
        SetVector2(panelObject, "defaultPosition", Vector2.zero);
        SetObject(panelObject, "placeholderCardArt", AssetDatabase.LoadAssetAtPath<Sprite>(PlaceholderCardArtPath));
        SetObject(panelObject, "placeholderAttributeIcon", AssetDatabase.LoadAssetAtPath<Sprite>(PlaceholderAttributeIconPath));
        panelObject.ApplyModifiedPropertiesWithoutUndo();

        EditorUtility.SetDirty(root);
    }

    private static int RemoveBattleObjectsRecursive(GameObject gameObject)
    {
        if (gameObject == null)
        {
            return 0;
        }

        if (IsBattleUiObject(gameObject))
        {
            Object.DestroyImmediate(gameObject);
            return 1;
        }

        int removed = 0;
        for (int index = gameObject.transform.childCount - 1; index >= 0; index--)
        {
            Transform child = gameObject.transform.GetChild(index);
            removed += RemoveBattleObjectsRecursive(child.gameObject);
        }

        return removed;
    }

    private static bool IsBattleUiObject(GameObject gameObject)
    {
        string objectName = gameObject.name;
        if (objectName.Contains("SourceOfThoughtBattle") ||
            objectName.Contains("ThoughtMapBattleMVP") ||
            objectName.Contains("ThoughtMapBattleMvp") ||
            objectName.Contains("Battle MVP") ||
            objectName.Contains("BattleMVP"))
        {
            return true;
        }

        return gameObject.GetComponent<ThoughtMapBattleMvpController>() != null ||
            gameObject.GetComponent<ThoughtMapBattleMvpPanelView>() != null ||
            gameObject.GetComponent<ThoughtMapScreenModeController>() != null;
    }

    private static void SetBool(SerializedObject serializedObject, string propertyName, bool value)
    {
        SerializedProperty property = serializedObject.FindProperty(propertyName);
        if (property != null)
        {
            property.boolValue = value;
        }
    }

    private static void SetString(SerializedObject serializedObject, string propertyName, string value)
    {
        SerializedProperty property = serializedObject.FindProperty(propertyName);
        if (property != null)
        {
            property.stringValue = value;
        }
    }

    private static void SetVector2(SerializedObject serializedObject, string propertyName, Vector2 value)
    {
        SerializedProperty property = serializedObject.FindProperty(propertyName);
        if (property != null)
        {
            property.vector2Value = value;
        }
    }

    private static void SetObject(SerializedObject serializedObject, string propertyName, Object value)
    {
        SerializedProperty property = serializedObject.FindProperty(propertyName);
        if (property != null)
        {
            property.objectReferenceValue = value;
        }
    }
}
#endif
