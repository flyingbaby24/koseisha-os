#if UNITY_EDITOR
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public static class BattleSceneInitialBuilder
{
    private const string ScenePath = "Assets/Scenes/BattleScene.unity";
    private const string PrefabFolder = "Assets/Prefabs/Battle";
    private const string BattleCardPrefabPath = PrefabFolder + "/BattleCardPrefab.prefab";
    private const string BattleLogRowPrefabPath = PrefabFolder + "/BattleLogRowPrefab.prefab";
    private const string TurnIconPrefabPath = PrefabFolder + "/TurnIconPrefab.prefab";
    private const string BackgroundPath = "Assets/Art/Backgrounds/battle_prep_bg.png";

    [MenuItem("Tools/Source of Thought/Create BattleScene Initial")]
    public static void CreateBattleSceneInitial()
    {
        EnsureFolders();

        BattleCardView cardPrefab = CreateBattleCardPrefab();
        TMP_Text logRowPrefab = CreateBattleLogRowPrefab();
        GameObject turnIconPrefab = CreateTurnIconPrefab();

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        scene.name = "BattleScene";

        GameObject sceneRoot = new GameObject("BattleScene");
        CreateCamera(sceneRoot.transform);
        CreateDirectionalLight(sceneRoot.transform);
        CreateBackground(sceneRoot.transform);
        CreateBattleRoot(sceneRoot.transform, cardPrefab);
        CreateEffects(sceneRoot.transform);
        CreateBattleCanvas(sceneRoot.transform, logRowPrefab, turnIconPrefab);
        CreateEventSystem(sceneRoot.transform);

        EditorSceneManager.SaveScene(scene, ScenePath);
        AddSceneToBuildSettings(ScenePath);
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();

        Debug.Log("[BattleSceneInitial] BattleScene created at " + ScenePath);
    }

    private static void CreateBattleCanvas(Transform parent, TMP_Text logRowPrefab, GameObject turnIconPrefab)
    {
        Canvas canvas = CreateOverlayCanvas("BattleCanvas", 10);
        canvas.transform.SetParent(parent, false);
        RectTransform canvasRect = canvas.GetComponent<RectTransform>();

        RectTransform topBar = CreatePanel(canvasRect, "TopBar", new Vector2(0.02f, 0.93f), new Vector2(0.98f, 0.99f), new Color(0.02f, 0.05f, 0.08f, 0.86f));
        BattleHudView hud = topBar.gameObject.AddComponent<BattleHudView>();

        TMP_Text roundText = CreateText(topBar, "RoundText", "Round 1", new Vector2(0.02f, 0.1f), new Vector2(0.16f, 0.9f), 18, TextAlignmentOptions.Left);
        TMP_Text speedText = CreateText(topBar, "BattleSpeedText", "Speed x1", new Vector2(0.78f, 0.1f), new Vector2(0.88f, 0.9f), 16, TextAlignmentOptions.Center);
        Button pauseButton = CreateButton(topBar, "PauseButton", "Pause", new Vector2(0.89f, 0.12f), new Vector2(0.98f, 0.88f));

        TMP_Text turnText = CreateText(canvasRect, "TurnText", "Turn 1", new Vector2(0.44f, 0.88f), new Vector2(0.56f, 0.93f), 24, TextAlignmentOptions.Center);

        SerializedObject hudSo = new SerializedObject(hud);
        SetObject(hudSo, "roundText", roundText);
        SetObject(hudSo, "turnText", turnText);
        SetObject(hudSo, "battleSpeedText", speedText);
        SetObject(hudSo, "pauseButton", pauseButton);
        hudSo.ApplyModifiedPropertiesWithoutUndo();

        RectTransform log = CreateBattleLog(canvasRect, logRowPrefab);
        RectTransform speedOrder = CreateSpeedOrder(canvasRect, turnIconPrefab);

        BattleSceneController controller = canvas.gameObject.AddComponent<BattleSceneController>();
        BattleFieldView fieldView = Object.FindObjectOfType<BattleFieldView>();
        SerializedObject controllerSo = new SerializedObject(controller);
        SetObject(controllerSo, "hudView", hud);
        SetObject(controllerSo, "fieldView", fieldView);
        SetObject(controllerSo, "battleLogView", log.GetComponent<BattleLogView>());
        SetObject(controllerSo, "speedOrderView", speedOrder.GetComponent<SpeedOrderView>());
        controllerSo.ApplyModifiedPropertiesWithoutUndo();
    }

    private static RectTransform CreateBattleLog(RectTransform parent, TMP_Text logRowPrefab)
    {
        RectTransform root = CreatePanel(parent, "BattleLog", new Vector2(0.02f, 0.04f), new Vector2(0.34f, 0.26f), new Color(0.01f, 0.03f, 0.05f, 0.82f));
        ScrollRect scrollRect = root.gameObject.AddComponent<ScrollRect>();
        BattleLogView view = root.gameObject.AddComponent<BattleLogView>();

        TMP_Text title = CreateText(root, "TitleText", "Battle Log", new Vector2(0.04f, 0.82f), new Vector2(0.96f, 0.96f), 16, TextAlignmentOptions.Left);
        title.fontStyle = FontStyles.Bold;

        RectTransform viewport = CreatePanel(root, "Viewport", new Vector2(0.04f, 0.08f), new Vector2(0.96f, 0.78f), new Color(0f, 0f, 0f, 0.12f));
        viewport.gameObject.AddComponent<Mask>().showMaskGraphic = false;

        GameObject contentObject = new GameObject("Content", typeof(RectTransform), typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
        RectTransform content = contentObject.GetComponent<RectTransform>();
        content.SetParent(viewport, false);
        content.anchorMin = new Vector2(0f, 1f);
        content.anchorMax = new Vector2(1f, 1f);
        content.pivot = new Vector2(0.5f, 1f);
        content.offsetMin = Vector2.zero;
        content.offsetMax = Vector2.zero;

        VerticalLayoutGroup layout = contentObject.GetComponent<VerticalLayoutGroup>();
        layout.padding = new RectOffset(8, 8, 8, 8);
        layout.spacing = 4f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        ContentSizeFitter fitter = contentObject.GetComponent<ContentSizeFitter>();
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        scrollRect.viewport = viewport;
        scrollRect.content = content;
        scrollRect.horizontal = false;

        SerializedObject so = new SerializedObject(view);
        SetObject(so, "scrollRect", scrollRect);
        SetObject(so, "contentRoot", content);
        SetObject(so, "rowPrefab", logRowPrefab);
        so.ApplyModifiedPropertiesWithoutUndo();

        return root;
    }

    private static RectTransform CreateSpeedOrder(RectTransform parent, GameObject turnIconPrefab)
    {
        RectTransform root = CreatePanel(parent, "SpeedOrder", new Vector2(0.36f, 0.04f), new Vector2(0.72f, 0.16f), new Color(0.01f, 0.03f, 0.05f, 0.78f));
        SpeedOrderView view = root.gameObject.AddComponent<SpeedOrderView>();
        HorizontalLayoutGroup layout = root.gameObject.AddComponent<HorizontalLayoutGroup>();
        layout.padding = new RectOffset(12, 12, 12, 12);
        layout.spacing = 8f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = false;
        layout.childForceExpandHeight = true;

        TMP_Text title = CreateText(root, "TitleText", "Speed Order", new Vector2(0.02f, 0.72f), new Vector2(0.98f, 0.98f), 14, TextAlignmentOptions.Left);
        title.raycastTarget = false;

        SerializedObject so = new SerializedObject(view);
        SetObject(so, "contentRoot", root);
        SetObject(so, "turnIconPrefab", turnIconPrefab);
        so.ApplyModifiedPropertiesWithoutUndo();

        return root;
    }

    private static void CreateBattleRoot(Transform parent, BattleCardView cardPrefab)
    {
        Canvas canvas = CreateOverlayCanvas("BattleRoot", 5);
        canvas.transform.SetParent(parent, false);
        BattleFieldView fieldView = canvas.gameObject.AddComponent<BattleFieldView>();
        RectTransform rootRect = canvas.GetComponent<RectTransform>();

        RectTransform playerTeam = CreateTeamRoot(rootRect, "PlayerTeam", new Vector2(0.20f, 0.24f), new Vector2(0.80f, 0.44f), new Color(0.0f, 0.25f, 0.45f, 0.24f));
        RectTransform enemyTeam = CreateTeamRoot(rootRect, "EnemyTeam", new Vector2(0.20f, 0.56f), new Vector2(0.80f, 0.76f), new Color(0.45f, 0.05f, 0.05f, 0.24f));

        SerializedObject so = new SerializedObject(fieldView);
        SetObject(so, "playerTeamRoot", playerTeam);
        SetObject(so, "enemyTeamRoot", enemyTeam);
        SetObject(so, "battleCardPrefab", cardPrefab);
        so.ApplyModifiedPropertiesWithoutUndo();

        BattleSceneController controller = Object.FindObjectOfType<BattleSceneController>();
        if (controller != null)
        {
            SerializedObject controllerSo = new SerializedObject(controller);
            SetObject(controllerSo, "fieldView", fieldView);
            controllerSo.ApplyModifiedPropertiesWithoutUndo();
        }
    }

    private static RectTransform CreateTeamRoot(RectTransform parent, string name, Vector2 min, Vector2 max, Color color)
    {
        RectTransform root = CreatePanel(parent, name, min, max, color);
        HorizontalLayoutGroup layout = root.gameObject.AddComponent<HorizontalLayoutGroup>();
        layout.padding = new RectOffset(20, 20, 16, 16);
        layout.spacing = 18f;
        layout.childAlignment = TextAnchor.MiddleCenter;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = false;
        layout.childForceExpandHeight = true;
        return root;
    }

    private static void CreateBackground(Transform parent)
    {
        Canvas canvas = CreateOverlayCanvas("Background", 0);
        canvas.transform.SetParent(parent, false);
        Image image = canvas.gameObject.AddComponent<Image>();
        image.color = new Color(1f, 1f, 1f, 0.95f);
        image.sprite = AssetDatabase.LoadAssetAtPath<Sprite>(BackgroundPath);
        image.preserveAspect = false;
    }

    private static void CreateEffects(Transform parent)
    {
        GameObject effects = new GameObject("Effects");
        effects.transform.SetParent(parent, false);
    }

    private static void CreateCamera(Transform parent)
    {
        GameObject cameraObject = new GameObject("Main Camera", typeof(Camera));
        cameraObject.transform.SetParent(parent, false);
        cameraObject.tag = "MainCamera";
        Camera camera = cameraObject.GetComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.005f, 0.008f, 0.018f, 1f);
        camera.orthographic = true;
        camera.orthographicSize = 5f;
        cameraObject.transform.position = new Vector3(0f, 0f, -10f);
    }

    private static void CreateDirectionalLight(Transform parent)
    {
        GameObject lightObject = new GameObject("Directional Light", typeof(Light));
        lightObject.transform.SetParent(parent, false);
        Light light = lightObject.GetComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 0.9f;
        lightObject.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
    }

    private static void CreateEventSystem(Transform parent)
    {
        GameObject eventSystem = new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
        eventSystem.transform.SetParent(parent, false);
    }

    private static Canvas CreateOverlayCanvas(string name, int sortingOrder)
    {
        GameObject canvasObject = new GameObject(name, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
        Canvas canvas = canvasObject.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = sortingOrder;

        CanvasScaler scaler = canvasObject.GetComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);
        scaler.matchWidthOrHeight = 0.5f;

        return canvas;
    }

    private static BattleCardView CreateBattleCardPrefab()
    {
        GameObject root = new GameObject("BattleCardPrefab", typeof(RectTransform), typeof(Image), typeof(BattleCardView), typeof(LayoutElement));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(180f, 240f);
        root.GetComponent<Image>().color = new Color(0.02f, 0.08f, 0.12f, 0.92f);
        LayoutElement layout = root.GetComponent<LayoutElement>();
        layout.preferredWidth = 180f;
        layout.preferredHeight = 240f;

        Image cardImage = CreateImage(rect, "Card Image", new Vector2(0.08f, 0.34f), new Vector2(0.92f, 0.92f), new Color(0.05f, 0.16f, 0.24f, 1f));
        TMP_Text name = CreateText(rect, "Name", "Unit", new Vector2(0.08f, 0.22f), new Vector2(0.92f, 0.32f), 15, TextAlignmentOptions.Center);
        Image hp = CreateBar(rect, "HP Bar", new Vector2(0.08f, 0.13f), new Vector2(0.92f, 0.18f), new Color(0.1f, 0.8f, 0.35f, 1f));
        Image sp = CreateBar(rect, "SP Bar", new Vector2(0.08f, 0.06f), new Vector2(0.92f, 0.11f), new Color(0.1f, 0.45f, 0.95f, 1f));

        GameObject status = new GameObject("Status Icons", typeof(RectTransform), typeof(HorizontalLayoutGroup));
        RectTransform statusRect = status.GetComponent<RectTransform>();
        statusRect.SetParent(rect, false);
        Anchor(statusRect, new Vector2(0.08f, 0.935f), new Vector2(0.92f, 0.99f));

        Image target = CreateImage(rect, "Target Marker", new Vector2(0f, 0f), Vector2.one, new Color(1f, 0.1f, 0.1f, 0.28f));
        target.raycastTarget = false;
        target.gameObject.SetActive(false);

        SerializedObject so = new SerializedObject(root.GetComponent<BattleCardView>());
        SetObject(so, "cardImage", cardImage);
        SetObject(so, "nameText", name);
        SetObject(so, "hpFillImage", hp);
        SetObject(so, "spFillImage", sp);
        SetObject(so, "statusIconRoot", statusRect);
        SetObject(so, "targetMarker", target.gameObject);
        so.ApplyModifiedPropertiesWithoutUndo();

        SavePrefab(root, BattleCardPrefabPath);
        return AssetDatabase.LoadAssetAtPath<BattleCardView>(BattleCardPrefabPath);
    }

    private static TMP_Text CreateBattleLogRowPrefab()
    {
        GameObject root = new GameObject("BattleLogRowPrefab", typeof(RectTransform), typeof(TextMeshProUGUI), typeof(LayoutElement));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(520f, 28f);
        TMP_Text text = root.GetComponent<TMP_Text>();
        text.text = "Battle log row";
        text.fontSize = 14f;
        text.color = new Color(0.86f, 0.95f, 1f, 1f);
        text.alignment = TextAlignmentOptions.Left;
        LayoutElement layout = root.GetComponent<LayoutElement>();
        layout.minHeight = 24f;
        layout.preferredHeight = 28f;
        SavePrefab(root, BattleLogRowPrefabPath);
        return AssetDatabase.LoadAssetAtPath<TMP_Text>(BattleLogRowPrefabPath);
    }

    private static GameObject CreateTurnIconPrefab()
    {
        GameObject root = new GameObject("TurnIconPrefab", typeof(RectTransform), typeof(Image), typeof(LayoutElement));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(64f, 54f);
        root.GetComponent<Image>().color = new Color(0.04f, 0.14f, 0.22f, 0.95f);
        LayoutElement layout = root.GetComponent<LayoutElement>();
        layout.preferredWidth = 64f;
        layout.preferredHeight = 54f;
        CreateText(rect, "Label", "P1", Vector2.zero, Vector2.one, 16, TextAlignmentOptions.Center);
        SavePrefab(root, TurnIconPrefabPath);
        return AssetDatabase.LoadAssetAtPath<GameObject>(TurnIconPrefabPath);
    }

    private static RectTransform CreatePanel(RectTransform parent, string name, Vector2 min, Vector2 max, Color color)
    {
        GameObject panel = new GameObject(name, typeof(RectTransform), typeof(Image));
        RectTransform rect = panel.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        Anchor(rect, min, max);
        Image image = panel.GetComponent<Image>();
        image.color = color;
        return rect;
    }

    private static TMP_Text CreateText(RectTransform parent, string name, string value, Vector2 min, Vector2 max, float fontSize, TextAlignmentOptions alignment)
    {
        GameObject textObject = new GameObject(name, typeof(RectTransform), typeof(TextMeshProUGUI));
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        Anchor(rect, min, max);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = fontSize;
        text.alignment = alignment;
        text.color = new Color(0.90f, 0.98f, 1f, 1f);
        text.raycastTarget = false;
        return text;
    }

    private static Button CreateButton(RectTransform parent, string name, string label, Vector2 min, Vector2 max)
    {
        RectTransform rect = CreatePanel(parent, name, min, max, new Color(0.02f, 0.08f, 0.14f, 0.95f));
        Button button = rect.gameObject.AddComponent<Button>();
        CreateText(rect, "Text", label, Vector2.zero, Vector2.one, 14, TextAlignmentOptions.Center);
        return button;
    }

    private static Image CreateImage(RectTransform parent, string name, Vector2 min, Vector2 max, Color color)
    {
        RectTransform rect = CreatePanel(parent, name, min, max, color);
        return rect.GetComponent<Image>();
    }

    private static Image CreateBar(RectTransform parent, string name, Vector2 min, Vector2 max, Color fillColor)
    {
        RectTransform container = CreatePanel(parent, name, min, max, new Color(0f, 0f, 0f, 0.65f));
        Image fill = CreateImage(container, "Fill", Vector2.zero, Vector2.one, fillColor);
        fill.type = Image.Type.Filled;
        fill.fillMethod = Image.FillMethod.Horizontal;
        fill.fillOrigin = 0;
        fill.fillAmount = 1f;
        return fill;
    }

    private static void Anchor(RectTransform rect, Vector2 min, Vector2 max)
    {
        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
        rect.localScale = Vector3.one;
    }

    private static void SavePrefab(GameObject root, string path)
    {
        GameObject prefab = PrefabUtility.SaveAsPrefabAsset(root, path);
        Object.DestroyImmediate(root);
        if (prefab == null)
        {
            Debug.LogError("[BattleSceneInitial] Failed to save prefab: " + path);
        }
    }

    private static void EnsureFolders()
    {
        EnsureFolder("Assets/Prefabs");
        EnsureFolder(PrefabFolder);
        EnsureFolder("Assets/Scenes");
    }

    private static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path))
        {
            return;
        }

        string parent = System.IO.Path.GetDirectoryName(path)?.Replace("\\", "/");
        string name = System.IO.Path.GetFileName(path);
        if (!string.IsNullOrEmpty(parent) && !AssetDatabase.IsValidFolder(parent))
        {
            EnsureFolder(parent);
        }
        AssetDatabase.CreateFolder(parent, name);
    }

    private static void SetObject(SerializedObject serializedObject, string propertyName, Object value)
    {
        SerializedProperty property = serializedObject.FindProperty(propertyName);
        if (property != null)
        {
            property.objectReferenceValue = value;
        }
    }

    private static void AddSceneToBuildSettings(string scenePath)
    {
        List<EditorBuildSettingsScene> scenes = EditorBuildSettings.scenes.ToList();
        if (scenes.Any(scene => scene.path == scenePath))
        {
            return;
        }

        scenes.Add(new EditorBuildSettingsScene(scenePath, true));
        EditorBuildSettings.scenes = scenes.ToArray();
    }
}
#endif
