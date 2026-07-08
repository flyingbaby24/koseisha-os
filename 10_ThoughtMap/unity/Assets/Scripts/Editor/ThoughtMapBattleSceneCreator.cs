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
    private const string SpriteFolder = "Assets/Sprites";
    private const string CardSpriteFolder = "Assets/Sprites/Cards";
    private const string IconSpriteFolder = "Assets/Sprites/Icons";

    private const string BattlePrepScenePath = "Assets/Scenes/BattlePrepScene.unity";
    private const string BattleScenePath = "Assets/Scenes/BattleScene.unity";

    private const string CardViewPrefabPath = "Assets/Prefabs/ProductBattleCardPrefab.prefab";
    private const string GridCellPrefabPath = "Assets/Prefabs/ProductBattleGridCellPrefab.prefab";
    private const string AttributeIconPrefabPath = "Assets/Prefabs/AttributeIconPrefab.prefab";
    private const string SkillIconPrefabPath = "Assets/Prefabs/SkillIconPrefab.prefab";
    private const string CardDetailPanelPrefabPath = "Assets/Prefabs/CardDetailPanel.prefab";
    private const string DeckListPanelPrefabPath = "Assets/Prefabs/DeckListPanel.prefab";
    private const string FormationGridPrefabPath = "Assets/Prefabs/FormationGrid.prefab";
    private const string BattleFieldPrefabPath = "Assets/Prefabs/BattleField.prefab";
    private const string BattleUnitCardPrefabPath = "Assets/Prefabs/BattleUnitCard.prefab";
    private const string BattleLogPanelPrefabPath = "Assets/Prefabs/BattleLogPanel.prefab";
    private const string ProductBattlePrepCanvasPrefabPath = "Assets/Prefabs/ProductBattlePrepCanvas.prefab";
    private const string ProductBattleCanvasPrefabPath = "Assets/Prefabs/ProductBattleCanvas.prefab";

    [MenuItem("Tools/Source of Thought/Create Product Battle UI Prefabs")]
    public static void CreateProductBattleUiPrefabs()
    {
        EnsureFolders();
        ProductBattleCardView cardPrefab = CreateCardViewPrefab();
        ProductBattleGridCellView cellPrefab = CreateGridCellPrefab();
        CreateSimpleImagePrefab("AttributeIconPrefab", AttributeIconPrefabPath, new Color(0.0f, 0.45f, 0.8f, 1f), new Vector2(48f, 48f));
        CreateSimpleImagePrefab("SkillIconPrefab", SkillIconPrefabPath, new Color(0.55f, 0.15f, 0.85f, 1f), new Vector2(48f, 48f));
        ProductBattleCardDetailPanelView detailPanel = CreateCardDetailPanelPrefab();
        CreateDeckListPanelPrefab();
        CreateFormationGridPrefab(cellPrefab);
        ProductBattleUnitCardView unitCard = CreateBattleUnitCardPrefab();
        ProductBattleLogPanelView logPanel = CreateBattleLogPanelPrefab();
        CreateBattleFieldPrefab(unitCard);
        CreateProductBattlePrepCanvasPrefab(cardPrefab, cellPrefab, detailPanel, logPanel);
        CreateProductBattleCanvasPrefab(unitCard, logPanel);
        AssetDatabase.Refresh();
        Debug.Log("[SourceOfThoughtBattleScene] Product Battle UI prefabs created. They are editable assets, not runtime-only UI.");
    }

    [MenuItem("Tools/Source of Thought/Create BattlePrepScene")]
    public static void CreateBattlePrepScene()
    {
        EnsureFolders();
        CreateProductBattleUiPrefabs();

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        scene.name = "BattlePrepScene";
        CreateCamera();
        CreateEventSystem();

        GameObject canvasPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(ProductBattlePrepCanvasPrefabPath);
        PrefabUtility.InstantiatePrefab(canvasPrefab);

        EditorSceneManager.SaveScene(scene, BattlePrepScenePath);
        AssetDatabase.Refresh();
        Debug.Log($"[SourceOfThoughtBattleScene] Created editable BattlePrepScene at {BattlePrepScenePath}.");
    }

    [MenuItem("Tools/Source of Thought/Create BattleScene")]
    public static void CreateBattleScene()
    {
        EnsureFolders();
        CreateProductBattleUiPrefabs();

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        scene.name = "BattleScene";
        CreateCamera();
        CreateEventSystem();

        GameObject canvasPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(ProductBattleCanvasPrefabPath);
        PrefabUtility.InstantiatePrefab(canvasPrefab);

        EditorSceneManager.SaveScene(scene, BattleScenePath);
        AssetDatabase.Refresh();
        Debug.Log($"[SourceOfThoughtBattleScene] Created editable BattleScene at {BattleScenePath}.");
    }

    [MenuItem("Tools/Source of Thought/Create DebugBattlePrepScene")]
    public static void CreateDebugBattlePrepScene()
    {
        EnsureFolders();
        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        scene.name = "DebugBattlePrepScene";
        CreateCamera();
        Canvas canvas = CreateCanvas("DebugBattlePrepCanvas");
        CreateEventSystem();
        GameObject root = new GameObject("DebugBattlePrep", typeof(RectTransform), typeof(ThoughtMapBattleMvpController), typeof(ThoughtMapBattleMvpPanelView));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.SetParent(canvas.transform, false);
        Stretch(rect);
        EditorSceneManager.SaveScene(scene, "Assets/Scenes/DebugBattlePrepScene.unity");
        AssetDatabase.Refresh();
    }

    [MenuItem("Tools/Source of Thought/Clean Battle UI From Current Search Scene")]
    public static void CleanBattleUiFromCurrentSearchScene()
    {
        Scene scene = SceneManager.GetActiveScene();
        if (!scene.IsValid() || scene.name == "BattleScene" || scene.name == "BattlePrepScene")
        {
            Debug.LogWarning("[SourceOfThoughtBattleScene] Cleanup skipped for Battle scenes.");
            return;
        }

        int removed = 0;
        foreach (GameObject root in scene.GetRootGameObjects())
        {
            removed += RemoveBattleObjectsRecursive(root);
        }
        EditorSceneManager.MarkSceneDirty(scene);
        Debug.Log($"[SourceOfThoughtBattleScene] Removed {removed} Battle UI object(s) from {scene.name}.");
    }

    private static ProductBattleCardView CreateCardViewPrefab()
    {
        GameObject root = UiObject("ProductBattleCardPrefab", typeof(Image), typeof(Button), typeof(ProductBattleCardView), typeof(LayoutElement));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(210f, 320f);
        root.GetComponent<Image>().color = new Color(0.025f, 0.035f, 0.045f, 0.98f);
        LayoutElement layout = root.GetComponent<LayoutElement>();
        layout.preferredWidth = 210f;
        layout.preferredHeight = 320f;

        Image selection = ChildImage(rect, "SelectionGlow", new Vector2(0f, 0f), new Vector2(1f, 1f), new Color(0.1f, 0.9f, 1f, 0.28f));
        Image art = ChildImage(rect, "ArtImage", new Vector2(0.08f, 0.36f), new Vector2(0.92f, 0.88f), new Color(0.12f, 0.14f, 0.16f, 1f));
        Image icon = ChildImage(rect, "AttributeIconImage", new Vector2(0.76f, 0.78f), new Vector2(0.94f, 0.94f), new Color(0.0f, 0.45f, 0.8f, 1f));
        TMP_Text unit = ChildText(rect, "UnitIdText", new Vector2(0.05f, 0.88f), new Vector2(0.28f, 0.98f), "P1", 18, TextAlignmentOptions.Left);
        TMP_Text rarity = ChildText(rect, "RarityText", new Vector2(0.68f, 0.88f), new Vector2(0.94f, 0.98f), "★4", 18, TextAlignmentOptions.Right);
        TMP_Text name = ChildText(rect, "NameText", new Vector2(0.08f, 0.25f), new Vector2(0.92f, 0.35f), "Card Name", 17, TextAlignmentOptions.Center);
        TMP_Text attr = ChildText(rect, "AttributeText", new Vector2(0.08f, 0.18f), new Vector2(0.92f, 0.25f), "Attribute", 14, TextAlignmentOptions.Center);
        TMP_Text hp = ChildText(rect, "HpText", new Vector2(0.08f, 0.10f), new Vector2(0.42f, 0.17f), "HP 120", 14, TextAlignmentOptions.Left);
        TMP_Text atk = ChildText(rect, "AtkText", new Vector2(0.46f, 0.10f), new Vector2(0.92f, 0.17f), "ATK 85", 14, TextAlignmentOptions.Right);
        TMP_Text skill = ChildText(rect, "SkillText", new Vector2(0.08f, 0.04f), new Vector2(0.58f, 0.10f), "Skill 01", 12, TextAlignmentOptions.Left);
        TMP_Text status = ChildText(rect, "StatusText", new Vector2(0.60f, 0.04f), new Vector2(0.92f, 0.10f), "Ready", 12, TextAlignmentOptions.Right);

        ProductBattleCardView view = root.GetComponent<ProductBattleCardView>();
        SerializedObject so = new SerializedObject(view);
        SetObject(so, "frameImage", root.GetComponent<Image>());
        SetObject(so, "artImage", art);
        SetObject(so, "attributeIconImage", icon);
        SetObject(so, "selectionImage", selection);
        SetObject(so, "unitIdText", unit);
        SetObject(so, "cardNameText", name);
        SetObject(so, "attributeText", attr);
        SetObject(so, "hpText", hp);
        SetObject(so, "atkText", atk);
        SetObject(so, "skillText", skill);
        SetObject(so, "rarityText", rarity);
        SetObject(so, "statusText", status);
        SetObject(so, "button", root.GetComponent<Button>());
        so.ApplyModifiedPropertiesWithoutUndo();

        SavePrefab(root, CardViewPrefabPath);
        return AssetDatabase.LoadAssetAtPath<ProductBattleCardView>(CardViewPrefabPath);
    }

    private static ProductBattleGridCellView CreateGridCellPrefab()
    {
        GameObject root = UiObject("ProductBattleGridCellPrefab", typeof(Image), typeof(Button), typeof(ProductBattleGridCellView));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(132f, 112f);
        root.GetComponent<Image>().color = new Color(0.025f, 0.032f, 0.04f, 0.96f);

        Image cardFrame = ChildImage(rect, "CardFrameImage", new Vector2(0.12f, 0.18f), new Vector2(0.88f, 0.72f), new Color(0.07f, 0.09f, 0.11f, 0.9f));
        Image glow = ChildImage(rect, "PlacedGlowImage", new Vector2(0f, 0f), new Vector2(1f, 1f), new Color(0.1f, 0.85f, 1f, 0.2f));
        TMP_Text coordinate = ChildText(rect, "CoordinateText", new Vector2(0.04f, 0.76f), new Vector2(0.96f, 0.98f), "1,1", 11, TextAlignmentOptions.Left);
        TMP_Text unit = ChildText(rect, "UnitIdText", new Vector2(0.04f, 0.48f), new Vector2(0.96f, 0.70f), "P1", 16, TextAlignmentOptions.Center);
        TMP_Text name = ChildText(rect, "CardNameText", new Vector2(0.04f, 0.25f), new Vector2(0.96f, 0.46f), "Card", 12, TextAlignmentOptions.Center);
        TMP_Text attr = ChildText(rect, "AttributeText", new Vector2(0.04f, 0.04f), new Vector2(0.96f, 0.22f), "Attr", 11, TextAlignmentOptions.Center);

        ProductBattleGridCellView view = root.GetComponent<ProductBattleGridCellView>();
        SerializedObject so = new SerializedObject(view);
        SetObject(so, "backgroundImage", root.GetComponent<Image>());
        SetObject(so, "cardFrameImage", cardFrame);
        SetObject(so, "placedGlowImage", glow);
        SetObject(so, "coordinateText", coordinate);
        SetObject(so, "unitIdText", unit);
        SetObject(so, "cardNameText", name);
        SetObject(so, "attributeText", attr);
        SetObject(so, "button", root.GetComponent<Button>());
        so.ApplyModifiedPropertiesWithoutUndo();

        SavePrefab(root, GridCellPrefabPath);
        return AssetDatabase.LoadAssetAtPath<ProductBattleGridCellView>(GridCellPrefabPath);
    }

    private static ProductBattleCardDetailPanelView CreateCardDetailPanelPrefab()
    {
        GameObject root = UiObject("CardDetailPanel", typeof(Image), typeof(ProductBattleCardDetailPanelView));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(760f, 320f);
        root.GetComponent<Image>().color = new Color(0.02f, 0.03f, 0.045f, 0.96f);
        Image art = ChildImage(rect, "ArtImage", new Vector2(0.02f, 0.08f), new Vector2(0.34f, 0.92f), new Color(0.08f, 0.10f, 0.12f, 1f));
        Image icon = ChildImage(rect, "AttributeIconImage", new Vector2(0.36f, 0.70f), new Vector2(0.43f, 0.88f), new Color(0f, 0.45f, 0.8f, 1f));
        TMP_Text title = ChildText(rect, "TitleText", new Vector2(0.45f, 0.78f), new Vector2(0.96f, 0.94f), "Card Name", 24, TextAlignmentOptions.Left);
        TMP_Text desc = ChildText(rect, "DescriptionText", new Vector2(0.45f, 0.52f), new Vector2(0.96f, 0.76f), "Description", 14, TextAlignmentOptions.TopLeft);
        TMP_Text attr = ChildText(rect, "AttributeText", new Vector2(0.45f, 0.44f), new Vector2(0.96f, 0.52f), "Attribute", 15, TextAlignmentOptions.Left);
        TMP_Text hp = ChildText(rect, "HpText", new Vector2(0.45f, 0.34f), new Vector2(0.58f, 0.42f), "HP", 18, TextAlignmentOptions.Left);
        TMP_Text atk = ChildText(rect, "AtkText", new Vector2(0.60f, 0.34f), new Vector2(0.73f, 0.42f), "ATK", 18, TextAlignmentOptions.Left);
        TMP_Text def = ChildText(rect, "DefenseText", new Vector2(0.75f, 0.34f), new Vector2(0.90f, 0.42f), "DEF", 18, TextAlignmentOptions.Left);
        TMP_Text skill = ChildText(rect, "SkillText", new Vector2(0.45f, 0.18f), new Vector2(0.96f, 0.30f), "Skill", 15, TextAlignmentOptions.Left);
        TMP_Text rarity = ChildText(rect, "RarityText", new Vector2(0.86f, 0.80f), new Vector2(0.96f, 0.94f), "★", 20, TextAlignmentOptions.Right);

        SerializedObject so = new SerializedObject(root.GetComponent<ProductBattleCardDetailPanelView>());
        SetObject(so, "artImage", art);
        SetObject(so, "attributeIconImage", icon);
        SetObject(so, "titleText", title);
        SetObject(so, "descriptionText", desc);
        SetObject(so, "attributeText", attr);
        SetObject(so, "hpText", hp);
        SetObject(so, "atkText", atk);
        SetObject(so, "defenseText", def);
        SetObject(so, "skillText", skill);
        SetObject(so, "rarityText", rarity);
        so.ApplyModifiedPropertiesWithoutUndo();

        SavePrefab(root, CardDetailPanelPrefabPath);
        return AssetDatabase.LoadAssetAtPath<ProductBattleCardDetailPanelView>(CardDetailPanelPrefabPath);
    }

    private static void CreateDeckListPanelPrefab()
    {
        GameObject root = UiObject("DeckListPanel", typeof(Image));
        root.GetComponent<Image>().color = new Color(0.015f, 0.025f, 0.035f, 0.95f);
        RectTransform content = CreateScrollContent(root.GetComponent<RectTransform>(), "Content", 2, new Vector2(210f, 320f));
        content.gameObject.name = "CardContent";
        SavePrefab(root, DeckListPanelPrefabPath);
    }

    private static void CreateFormationGridPrefab(ProductBattleGridCellView cellPrefab)
    {
        GameObject root = UiObject("FormationGrid", typeof(GridLayoutGroup));
        GridLayoutGroup grid = root.GetComponent<GridLayoutGroup>();
        grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        grid.constraintCount = 5;
        grid.cellSize = new Vector2(132f, 112f);
        grid.spacing = new Vector2(8f, 8f);
        grid.childAlignment = TextAnchor.MiddleCenter;
        for (int i = 0; i < 25; i++)
        {
            GameObject cellObject = PrefabUtility.InstantiatePrefab(cellPrefab.gameObject, root.transform) as GameObject;
            if (cellObject != null)
            {
                cellObject.name = $"Cell_{i:00}";
            }
        }
        SavePrefab(root, FormationGridPrefabPath);
    }

    private static ProductBattleUnitCardView CreateBattleUnitCardPrefab()
    {
        GameObject root = UiObject("BattleUnitCard", typeof(Image), typeof(ProductBattleUnitCardView));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(180f, 260f);
        root.GetComponent<Image>().color = new Color(0.025f, 0.035f, 0.045f, 0.98f);
        Image art = ChildImage(rect, "ArtImage", new Vector2(0.08f, 0.36f), new Vector2(0.92f, 0.88f), new Color(0.08f, 0.1f, 0.12f, 1f));
        Image icon = ChildImage(rect, "AttributeIconImage", new Vector2(0.76f, 0.78f), new Vector2(0.94f, 0.94f), new Color(0f, 0.45f, 0.8f, 1f));
        TMP_Text unit = ChildText(rect, "UnitIdText", new Vector2(0.05f, 0.88f), new Vector2(0.32f, 0.98f), "P1", 18, TextAlignmentOptions.Left);
        TMP_Text name = ChildText(rect, "CardNameText", new Vector2(0.08f, 0.22f), new Vector2(0.92f, 0.34f), "Card Name", 15, TextAlignmentOptions.Center);
        TMP_Text hp = ChildText(rect, "HpText", new Vector2(0.08f, 0.12f), new Vector2(0.92f, 0.20f), "120/120", 13, TextAlignmentOptions.Center);
        TMP_Text attr = ChildText(rect, "AttributeText", new Vector2(0.08f, 0.04f), new Vector2(0.92f, 0.11f), "Attribute", 12, TextAlignmentOptions.Center);
        Slider slider = CreateSlider(rect, "HpSlider", new Vector2(0.08f, 0.20f), new Vector2(0.92f, 0.24f));

        SerializedObject so = new SerializedObject(root.GetComponent<ProductBattleUnitCardView>());
        SetObject(so, "frameImage", root.GetComponent<Image>());
        SetObject(so, "artImage", art);
        SetObject(so, "attributeIconImage", icon);
        SetObject(so, "hpSlider", slider);
        SetObject(so, "unitIdText", unit);
        SetObject(so, "cardNameText", name);
        SetObject(so, "hpText", hp);
        SetObject(so, "attributeText", attr);
        so.ApplyModifiedPropertiesWithoutUndo();
        SavePrefab(root, BattleUnitCardPrefabPath);
        return AssetDatabase.LoadAssetAtPath<ProductBattleUnitCardView>(BattleUnitCardPrefabPath);
    }

    private static ProductBattleLogPanelView CreateBattleLogPanelPrefab()
    {
        GameObject root = UiObject("BattleLogPanel", typeof(Image), typeof(ProductBattleLogPanelView));
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(620f, 220f);
        root.GetComponent<Image>().color = new Color(0.0f, 0.015f, 0.025f, 0.92f);
        Button toggle = CreateButton(rect, "ToggleButton", "Show Debug", new Vector2(0.02f, 0.80f), new Vector2(0.24f, 0.96f));
        TMP_Text toggleText = toggle.GetComponentInChildren<TMP_Text>();
        GameObject content = UiChild(rect, "ContentRoot", typeof(RectTransform));
        RectTransform contentRect = content.GetComponent<RectTransform>();
        Anchor(contentRect, new Vector2(0.02f, 0.06f), new Vector2(0.98f, 0.76f));
        ScrollRect scroll = content.AddComponent<ScrollRect>();
        Image contentImage = content.AddComponent<Image>();
        contentImage.color = new Color(0f, 0f, 0f, 0.2f);
        TMP_Text log = ChildText(contentRect, "LogText", Vector2.zero, Vector2.one, "", 13, TextAlignmentOptions.TopLeft);
        scroll.content = log.rectTransform;
        scroll.viewport = contentRect;

        SerializedObject so = new SerializedObject(root.GetComponent<ProductBattleLogPanelView>());
        SetObject(so, "contentRoot", content);
        SetObject(so, "logText", log);
        SetObject(so, "scrollRect", scroll);
        SetObject(so, "toggleButton", toggle);
        SetObject(so, "toggleButtonText", toggleText);
        so.ApplyModifiedPropertiesWithoutUndo();
        SavePrefab(root, BattleLogPanelPrefabPath);
        return AssetDatabase.LoadAssetAtPath<ProductBattleLogPanelView>(BattleLogPanelPrefabPath);
    }

    private static void CreateBattleFieldPrefab(ProductBattleUnitCardView unitCardPrefab)
    {
        GameObject root = UiObject("BattleField", typeof(Image));
        root.GetComponent<Image>().color = new Color(0.02f, 0.02f, 0.035f, 0.96f);
        RectTransform rect = root.GetComponent<RectTransform>();
        RectTransform enemy = UiChild(rect, "EnemyBoardRoot", typeof(RectTransform), typeof(HorizontalLayoutGroup)).GetComponent<RectTransform>();
        Anchor(enemy, new Vector2(0.12f, 0.58f), new Vector2(0.88f, 0.92f));
        enemy.GetComponent<HorizontalLayoutGroup>().spacing = 22f;
        RectTransform player = UiChild(rect, "PlayerBoardRoot", typeof(RectTransform), typeof(HorizontalLayoutGroup)).GetComponent<RectTransform>();
        Anchor(player, new Vector2(0.12f, 0.12f), new Vector2(0.88f, 0.46f));
        player.GetComponent<HorizontalLayoutGroup>().spacing = 22f;
        SavePrefab(root, BattleFieldPrefabPath);
    }

    private static void CreateProductBattlePrepCanvasPrefab(
        ProductBattleCardView cardPrefab,
        ProductBattleGridCellView cellPrefab,
        ProductBattleCardDetailPanelView detailPrefab,
        ProductBattleLogPanelView logPrefab
    )
    {
        Canvas canvas = CreateCanvas("ProductBattlePrepCanvas");
        RectTransform canvasRect = canvas.GetComponent<RectTransform>();

        GameObject panel = UiChild(canvasRect, "ProductBattlePrepPanel", typeof(RectTransform), typeof(Image), typeof(ProductBattlePrepPanelView));
        RectTransform panelRect = panel.GetComponent<RectTransform>();
        Anchor(panelRect, new Vector2(0.02f, 0.04f), new Vector2(0.98f, 0.96f));
        panel.GetComponent<Image>().color = new Color(0.005f, 0.012f, 0.02f, 0.98f);

        TMP_Text title = ChildText(panelRect, "TitleText", new Vector2(0.02f, 0.92f), new Vector2(0.38f, 0.99f), "Source of Thought - Battle Prep", 30, TextAlignmentOptions.Left);
        Button loadButton = CreateButton(panelRect, "LoadCardsButton", "Load Cards", new Vector2(0.58f, 0.93f), new Vector2(0.68f, 0.985f));
        Button saveButton = CreateButton(panelRect, "SaveDeckButton", "Save", new Vector2(0.70f, 0.93f), new Vector2(0.78f, 0.985f));
        Button simulateButton = CreateButton(panelRect, "SimulateButton", "Simulate Battle", new Vector2(0.80f, 0.93f), new Vector2(0.90f, 0.985f));
        Button startButton = CreateButton(panelRect, "StartBattleButton", "Start Battle", new Vector2(0.91f, 0.93f), new Vector2(0.985f, 0.985f));
        Button clearButton = CreateButton(panelRect, "ClearButton", "Clear", new Vector2(0.02f, 0.01f), new Vector2(0.10f, 0.07f));
        TMP_Text status = ChildText(panelRect, "StatusText", new Vector2(0.18f, 0.01f), new Vector2(0.70f, 0.07f), "Ready", 16, TextAlignmentOptions.Left);

        RectTransform cardList = CreatePanel(panelRect, "CardListPanel", new Vector2(0.02f, 0.10f), new Vector2(0.24f, 0.90f), "Card List", out Transform cardListContent);
        GameObject detailObject = PrefabUtility.InstantiatePrefab(detailPrefab.gameObject, panelRect) as GameObject;
        RectTransform detail = detailObject.GetComponent<RectTransform>();
        detail.name = "CardDetailPanel";
        Anchor(detail, new Vector2(0.26f, 0.66f), new Vector2(0.76f, 0.90f));
        RectTransform deck = CreatePanel(panelRect, "DeckListPanel", new Vector2(0.78f, 0.42f), new Vector2(0.985f, 0.90f), "Deck 10", out Transform deckContent);
        RectTransform formation = CreatePanel(panelRect, "FormationGridPanel", new Vector2(0.26f, 0.10f), new Vector2(0.76f, 0.64f), "5x5 Formation", out Transform formationContent);
        GridLayoutGroup formationGrid = formationContent.gameObject.AddComponent<GridLayoutGroup>();
        formationGrid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        formationGrid.constraintCount = 5;
        formationGrid.cellSize = new Vector2(132f, 112f);
        formationGrid.spacing = new Vector2(8f, 8f);
        formationGrid.childAlignment = TextAnchor.MiddleCenter;
        GameObject logObject = PrefabUtility.InstantiatePrefab(logPrefab.gameObject, panelRect) as GameObject;
        RectTransform log = logObject.GetComponent<RectTransform>();
        log.name = "DebugLogPanel";
        Anchor(log, new Vector2(0.78f, 0.10f), new Vector2(0.985f, 0.40f));

        ProductBattlePrepPanelView view = panel.GetComponent<ProductBattlePrepPanelView>();
        SerializedObject so = new SerializedObject(view);
        SetObject(so, "cardViewPrefab", cardPrefab);
        SetObject(so, "gridCellPrefab", cellPrefab);
        SetObject(so, "cardListContent", cardListContent);
        SetObject(so, "deckListContent", deckContent);
        SetObject(so, "formationGridContent", formationContent);
        SetObject(so, "cardDetailPanel", detailObject.GetComponent<ProductBattleCardDetailPanelView>());
        SetObject(so, "debugLogPanel", logObject.GetComponent<ProductBattleLogPanelView>());
        SetObject(so, "statusText", status);
        SetObject(so, "loadCardsButton", loadButton);
        SetObject(so, "saveDeckButton", saveButton);
        SetObject(so, "startBattleButton", startButton);
        SetObject(so, "simulateButton", simulateButton);
        SetObject(so, "clearButton", clearButton);
        so.ApplyModifiedPropertiesWithoutUndo();

        SavePrefab(canvas.gameObject, ProductBattlePrepCanvasPrefabPath);
    }

    private static void CreateProductBattleCanvasPrefab(ProductBattleUnitCardView unitCardPrefab, ProductBattleLogPanelView logPrefab)
    {
        Canvas canvas = CreateCanvas("ProductBattleCanvas");
        RectTransform canvasRect = canvas.GetComponent<RectTransform>();

        GameObject root = UiChild(canvasRect, "ProductBattleSceneRoot", typeof(RectTransform), typeof(Image), typeof(ProductBattleSceneView));
        RectTransform rootRect = root.GetComponent<RectTransform>();
        Anchor(rootRect, Vector2.zero, Vector2.one);
        root.GetComponent<Image>().color = new Color(0.005f, 0.01f, 0.025f, 1f);

        TMP_Text title = ChildText(rootRect, "TitleText", new Vector2(0.02f, 0.92f), new Vector2(0.42f, 0.99f), "Source of Thought - Battle", 32, TextAlignmentOptions.Left);
        TMP_Text status = ChildText(rootRect, "StatusText", new Vector2(0.45f, 0.93f), new Vector2(0.78f, 0.985f), "Loading deck...", 16, TextAlignmentOptions.Left);
        GameObject fieldPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(BattleFieldPrefabPath);
        GameObject fieldObject = PrefabUtility.InstantiatePrefab(fieldPrefab, rootRect) as GameObject;
        RectTransform fieldInstance = fieldObject.GetComponent<RectTransform>();
        fieldInstance.name = "BattleField";
        Anchor(fieldInstance, new Vector2(0.10f, 0.12f), new Vector2(0.78f, 0.88f));
        GameObject logObject = PrefabUtility.InstantiatePrefab(logPrefab.gameObject, rootRect) as GameObject;
        RectTransform log = logObject.GetComponent<RectTransform>();
        log.name = "BattleLogPanel";
        Anchor(log, new Vector2(0.80f, 0.12f), new Vector2(0.98f, 0.88f));

        ProductBattleSceneView view = root.GetComponent<ProductBattleSceneView>();
        SerializedObject so = new SerializedObject(view);
        SetObject(so, "battleUnitCardPrefab", unitCardPrefab);
        SetObject(so, "playerBoardRoot", fieldInstance.Find("PlayerBoardRoot"));
        SetObject(so, "enemyBoardRoot", fieldInstance.Find("EnemyBoardRoot"));
        SetObject(so, "statusText", status);
        SetObject(so, "battleLogPanel", logObject.GetComponent<ProductBattleLogPanelView>());
        so.ApplyModifiedPropertiesWithoutUndo();

        SavePrefab(canvas.gameObject, ProductBattleCanvasPrefabPath);
    }

    private static RectTransform CreatePanel(RectTransform parent, string name, Vector2 min, Vector2 max, string title, out Transform content)
    {
        GameObject panel = UiChild(parent, name, typeof(RectTransform), typeof(Image));
        RectTransform rect = panel.GetComponent<RectTransform>();
        Anchor(rect, min, max);
        panel.GetComponent<Image>().color = new Color(0.015f, 0.025f, 0.035f, 0.94f);
        ChildText(rect, "HeadingText", new Vector2(0.03f, 0.92f), new Vector2(0.98f, 0.99f), title, 18, TextAlignmentOptions.Left);
        GameObject contentObject = UiChild(rect, "Content", typeof(RectTransform));
        RectTransform contentRect = contentObject.GetComponent<RectTransform>();
        Anchor(contentRect, new Vector2(0.03f, 0.03f), new Vector2(0.97f, 0.90f));
        content = contentRect;
        return rect;
    }

    private static RectTransform CreateScrollContent(RectTransform parent, string name, int columns, Vector2 cellSize)
    {
        GameObject viewport = UiChild(parent, "Viewport", typeof(RectTransform), typeof(Image), typeof(Mask));
        RectTransform viewportRect = viewport.GetComponent<RectTransform>();
        Anchor(viewportRect, Vector2.zero, Vector2.one);
        viewport.GetComponent<Image>().color = new Color(0f, 0f, 0f, 0.08f);
        viewport.GetComponent<Mask>().showMaskGraphic = false;
        GameObject content = UiChild(viewportRect, name, typeof(RectTransform), typeof(GridLayoutGroup), typeof(ContentSizeFitter));
        RectTransform contentRect = content.GetComponent<RectTransform>();
        contentRect.anchorMin = new Vector2(0f, 1f);
        contentRect.anchorMax = new Vector2(1f, 1f);
        contentRect.pivot = new Vector2(0.5f, 1f);
        GridLayoutGroup grid = content.GetComponent<GridLayoutGroup>();
        grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        grid.constraintCount = columns;
        grid.cellSize = cellSize;
        grid.spacing = new Vector2(10f, 10f);
        content.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        ScrollRect scroll = parent.gameObject.AddComponent<ScrollRect>();
        scroll.viewport = viewportRect;
        scroll.content = contentRect;
        scroll.horizontal = false;
        return contentRect;
    }

    private static void CreateSimpleImagePrefab(string name, string path, Color color, Vector2 size)
    {
        GameObject root = UiObject(name, typeof(Image));
        root.GetComponent<RectTransform>().sizeDelta = size;
        root.GetComponent<Image>().color = color;
        SavePrefab(root, path);
    }

    private static Button CreateButton(RectTransform parent, string name, string label, Vector2 min, Vector2 max)
    {
        GameObject buttonObject = UiChild(parent, name, typeof(RectTransform), typeof(Image), typeof(Button));
        RectTransform rect = buttonObject.GetComponent<RectTransform>();
        Anchor(rect, min, max);
        buttonObject.GetComponent<Image>().color = new Color(0.06f, 0.08f, 0.09f, 0.98f);
        ChildText(rect, "Label", Vector2.zero, Vector2.one, label, 15, TextAlignmentOptions.Center);
        return buttonObject.GetComponent<Button>();
    }

    private static Slider CreateSlider(RectTransform parent, string name, Vector2 min, Vector2 max)
    {
        GameObject sliderObject = UiChild(parent, name, typeof(RectTransform), typeof(Slider));
        RectTransform rect = sliderObject.GetComponent<RectTransform>();
        Anchor(rect, min, max);
        return sliderObject.GetComponent<Slider>();
    }

    private static Image ChildImage(RectTransform parent, string name, Vector2 min, Vector2 max, Color color)
    {
        GameObject child = UiChild(parent, name, typeof(RectTransform), typeof(Image));
        RectTransform rect = child.GetComponent<RectTransform>();
        Anchor(rect, min, max);
        Image image = child.GetComponent<Image>();
        image.color = color;
        return image;
    }

    private static TMP_Text ChildText(RectTransform parent, string name, Vector2 min, Vector2 max, string value, int size, TextAlignmentOptions alignment)
    {
        GameObject child = UiChild(parent, name, typeof(RectTransform), typeof(TextMeshProUGUI));
        RectTransform rect = child.GetComponent<RectTransform>();
        Anchor(rect, min, max);
        TMP_Text text = child.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = size;
        text.color = new Color(0.9f, 0.96f, 1f, 1f);
        text.alignment = alignment;
        text.enableWordWrapping = true;
        text.overflowMode = TextOverflowModes.Ellipsis;
        return text;
    }

    private static GameObject UiObject(string name, params System.Type[] components)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer));
        foreach (System.Type component in components)
        {
            if (obj.GetComponent(component) == null)
            {
                obj.AddComponent(component);
            }
        }
        return obj;
    }

    private static GameObject UiChild(RectTransform parent, string name, params System.Type[] components)
    {
        GameObject child = UiObject(name, components);
        child.GetComponent<RectTransform>().SetParent(parent, false);
        return child;
    }

    private static void Anchor(RectTransform rect, Vector2 min, Vector2 max)
    {
        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
    }

    private static void Stretch(RectTransform rect)
    {
        Anchor(rect, Vector2.zero, Vector2.one);
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

    private static void CreateEventSystem()
    {
        if (Object.FindObjectOfType<EventSystem>() == null)
        {
            new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
        }
    }

    private static void SavePrefab(GameObject root, string path)
    {
        PrefabUtility.SaveAsPrefabAsset(root, path);
        Object.DestroyImmediate(root);
    }

    private static void EnsureFolders()
    {
        EnsureFolder("Assets", "Scenes");
        EnsureFolder("Assets", "Prefabs");
        EnsureFolder("Assets", "Sprites");
        EnsureFolder("Assets/Sprites", "Cards");
        EnsureFolder("Assets/Sprites", "Icons");
    }

    private static void EnsureFolder(string parent, string child)
    {
        string path = parent + "/" + child;
        if (!AssetDatabase.IsValidFolder(path))
        {
            AssetDatabase.CreateFolder(parent, child);
        }
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
            removed += RemoveBattleObjectsRecursive(gameObject.transform.GetChild(index).gameObject);
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
            objectName.Contains("BattleMVP") ||
            objectName.Contains("ProductBattlePrep"))
        {
            return true;
        }

        return gameObject.GetComponent<ThoughtMapBattleMvpController>() != null ||
            gameObject.GetComponent<ThoughtMapBattleMvpPanelView>() != null ||
            gameObject.GetComponent<ProductBattlePrepPanelView>() != null ||
            gameObject.GetComponent<ProductBattleSceneView>() != null ||
            gameObject.GetComponent<ThoughtMapScreenModeController>() != null;
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
