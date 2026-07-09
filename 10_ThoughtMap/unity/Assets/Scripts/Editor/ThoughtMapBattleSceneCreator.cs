#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public static class ThoughtMapBattleSceneCreator
{
    private static readonly Vector2 ProductCardSize = new Vector2(176f, 272f);
    private static readonly Vector2 ProductCardGridSpacing = new Vector2(14f, 14f);
    private const float ProductListRowSpacing = 4f;

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
        EnsurePlaceholderSpriteAssets();
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

    [MenuItem("Tools/Source of Thought/Repair Product Battle Prep ScrollViews")]
    public static void RepairProductBattlePrepScrollViews()
    {
        EnsureFolders();
        EnsurePlaceholderSpriteAssets();
        Sprite[] cardSprites = LoadSpritesFromFolder(CardSpriteFolder);
        Sprite[] iconSprites = LoadSpritesFromFolder(IconSpriteFolder);
        int repaired = 0;
        Scene scene = SceneManager.GetActiveScene();
        if (scene.IsValid())
        {
            foreach (GameObject root in scene.GetRootGameObjects())
            {
                ProductBattlePrepPanelView[] views = root.GetComponentsInChildren<ProductBattlePrepPanelView>(true);
                foreach (ProductBattlePrepPanelView view in views)
                {
                    RepairProductBattlePrepPanel(view);
                    RepairProductBattlePrepControls(view);
                    RepairProductBattlePrepSpriteBindings(view, cardSprites, iconSprites);
                    repaired++;
                }
            }
        }

        foreach (GameObject selected in Selection.gameObjects)
        {
            ProductBattlePrepPanelView[] views = selected.GetComponentsInChildren<ProductBattlePrepPanelView>(true);
            foreach (ProductBattlePrepPanelView view in views)
            {
                RepairProductBattlePrepPanel(view);
                RepairProductBattlePrepControls(view);
                RepairProductBattlePrepSpriteBindings(view, cardSprites, iconSprites);
                repaired++;
            }
        }

        if (repaired > 0)
        {
            EditorSceneManager.MarkSceneDirty(scene);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        Debug.Log($"[SourceOfThoughtBattleScene] Repaired {repaired} Product Battle Prep scroll view binding(s).");
    }

    [MenuItem("Tools/Source of Thought/Repair Product Battle Prep Controls")]
    public static void RepairProductBattlePrepControlsMenu()
    {
        int repaired = 0;
        Scene scene = SceneManager.GetActiveScene();
        if (scene.IsValid())
        {
            foreach (GameObject root in scene.GetRootGameObjects())
            {
                ProductBattlePrepPanelView[] views = root.GetComponentsInChildren<ProductBattlePrepPanelView>(true);
                foreach (ProductBattlePrepPanelView view in views)
                {
                    RepairProductBattlePrepControls(view);
                    repaired++;
                }
            }
        }

        foreach (GameObject selected in Selection.gameObjects)
        {
            ProductBattlePrepPanelView[] views = selected.GetComponentsInChildren<ProductBattlePrepPanelView>(true);
            foreach (ProductBattlePrepPanelView view in views)
            {
                RepairProductBattlePrepControls(view);
                repaired++;
            }
        }

        if (repaired > 0)
        {
            EditorSceneManager.MarkSceneDirty(scene);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        Debug.Log($"[SourceOfThoughtBattleScene] Repaired Product Battle Prep controls on {repaired} component(s).");
    }

    [MenuItem("Tools/Source of Thought/Repair Product Battle Prep Sprites")]
    public static void RepairProductBattlePrepSprites()
    {
        EnsureFolders();
        EnsurePlaceholderSpriteAssets();
        Sprite[] cardSprites = LoadSpritesFromFolder(CardSpriteFolder);
        Sprite[] iconSprites = LoadSpritesFromFolder(IconSpriteFolder);

        int repaired = 0;
        Scene scene = SceneManager.GetActiveScene();
        if (scene.IsValid())
        {
            foreach (GameObject root in scene.GetRootGameObjects())
            {
                ProductBattlePrepPanelView[] views = root.GetComponentsInChildren<ProductBattlePrepPanelView>(true);
                foreach (ProductBattlePrepPanelView view in views)
                {
                    RepairProductBattlePrepSpriteBindings(view, cardSprites, iconSprites);
                    repaired++;
                }
            }
        }

        foreach (GameObject selected in Selection.gameObjects)
        {
            ProductBattlePrepPanelView[] views = selected.GetComponentsInChildren<ProductBattlePrepPanelView>(true);
            foreach (ProductBattlePrepPanelView view in views)
            {
                RepairProductBattlePrepSpriteBindings(view, cardSprites, iconSprites);
                repaired++;
            }
        }

        if (repaired > 0)
        {
            EditorSceneManager.MarkSceneDirty(scene);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        Debug.Log($"[SourceOfThoughtBattleScene] Repaired sprite bindings on {repaired} ProductBattlePrepPanelView component(s). Card Art Pool Size={cardSprites.Length}, Attribute Sprites Size={iconSprites.Length}.");
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
        rect.sizeDelta = ProductCardSize;
        Image rootImage = root.GetComponent<Image>();
        rootImage.color = new Color(0.025f, 0.035f, 0.045f, 0.98f);
        rootImage.raycastTarget = true;
        LayoutElement layout = root.GetComponent<LayoutElement>();
        layout.preferredWidth = ProductCardSize.x;
        layout.preferredHeight = ProductCardSize.y;
        layout.minWidth = ProductCardSize.x;
        layout.minHeight = ProductCardSize.y;
        layout.flexibleWidth = 0f;
        layout.flexibleHeight = 0f;

        Image selection = ChildImage(rect, "SelectionGlow", new Vector2(0f, 0f), new Vector2(1f, 1f), new Color(0.1f, 0.9f, 1f, 0.28f));
        ChildImage(rect, "ArtFrame", new Vector2(0.02f, 0.08f), new Vector2(0.34f, 0.92f), new Color(0.72f, 0.52f, 0.24f, 0.70f));
        Image art = ChildImage(rect, "ArtImage", new Vector2(0.035f, 0.105f), new Vector2(0.325f, 0.895f), new Color(0.08f, 0.10f, 0.12f, 1f));
        Image icon = ChildImage(rect, "AttributeIconImage", new Vector2(0.76f, 0.78f), new Vector2(0.94f, 0.94f), new Color(0.0f, 0.45f, 0.8f, 1f));
        TMP_Text unit = ChildText(rect, "UnitIdText", new Vector2(0.05f, 0.88f), new Vector2(0.28f, 0.98f), "P1", 18, TextAlignmentOptions.Left);
        TMP_Text rarity = ChildText(rect, "RarityText", new Vector2(0.68f, 0.88f), new Vector2(0.94f, 0.98f), "R4", 18, TextAlignmentOptions.Right);
        TMP_Text name = ChildText(rect, "NameText", new Vector2(0.08f, 0.29f), new Vector2(0.92f, 0.38f), "Card Name", 17, TextAlignmentOptions.Center);
        TMP_Text attr = ChildText(rect, "AttributeText", new Vector2(0.08f, 0.235f), new Vector2(0.92f, 0.29f), "Attribute", 13, TextAlignmentOptions.Center);
        TMP_Text hp = ChildText(rect, "HpText", new Vector2(0.08f, 0.16f), new Vector2(0.42f, 0.22f), "HP 120", 13, TextAlignmentOptions.Left);
        TMP_Text atk = ChildText(rect, "AtkText", new Vector2(0.48f, 0.16f), new Vector2(0.92f, 0.22f), "ATK 85", 13, TextAlignmentOptions.Right);
        TMP_Text def = ChildText(rect, "DefText", new Vector2(0.08f, 0.10f), new Vector2(0.42f, 0.155f), "DEF 70", 13, TextAlignmentOptions.Left);
        TMP_Text en = ChildText(rect, "EnText", new Vector2(0.48f, 0.10f), new Vector2(0.92f, 0.155f), "EN 30", 13, TextAlignmentOptions.Right);
        TMP_Text skill = ChildText(rect, "SkillText", new Vector2(0.08f, 0.045f), new Vector2(0.58f, 0.095f), "Skill 01", 12, TextAlignmentOptions.Left);
        TMP_Text status = ChildText(rect, "StatusText", new Vector2(0.60f, 0.045f), new Vector2(0.92f, 0.095f), "Ready", 12, TextAlignmentOptions.Right);

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
        SetObject(so, "defText", def);
        SetObject(so, "enText", en);
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
        Image art = ChildImage(rect, "ArtImage", new Vector2(0.18f, 0.26f), new Vector2(0.82f, 0.70f), new Color(0.10f, 0.11f, 0.13f, 1f));
        Image icon = ChildImage(rect, "AttributeIconImage", new Vector2(0.68f, 0.58f), new Vector2(0.86f, 0.76f), new Color(0.0f, 0.45f, 0.8f, 1f));
        Image glow = ChildImage(rect, "PlacedGlowImage", new Vector2(0f, 0f), new Vector2(1f, 1f), new Color(0.1f, 0.85f, 1f, 0.2f));
        TMP_Text coordinate = ChildText(rect, "CoordinateText", new Vector2(0.04f, 0.76f), new Vector2(0.96f, 0.98f), "1,1", 11, TextAlignmentOptions.Left);
        TMP_Text unit = ChildText(rect, "UnitIdText", new Vector2(0.04f, 0.48f), new Vector2(0.96f, 0.70f), "P1", 16, TextAlignmentOptions.Center);
        TMP_Text name = ChildText(rect, "CardNameText", new Vector2(0.04f, 0.25f), new Vector2(0.96f, 0.46f), "Card", 12, TextAlignmentOptions.Center);
        TMP_Text attr = ChildText(rect, "AttributeText", new Vector2(0.08f, 0.235f), new Vector2(0.92f, 0.29f), "Attribute", 13, TextAlignmentOptions.Center);

        ProductBattleGridCellView view = root.GetComponent<ProductBattleGridCellView>();
        SerializedObject so = new SerializedObject(view);
        SetObject(so, "backgroundImage", root.GetComponent<Image>());
        SetObject(so, "cardFrameImage", cardFrame);
        SetObject(so, "artImage", art);
        SetObject(so, "attributeIconImage", icon);
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
        ChildImage(rect, "ArtFrame", new Vector2(0.02f, 0.08f), new Vector2(0.38f, 0.92f), new Color(0.72f, 0.52f, 0.24f, 0.70f));
        Image art = ChildImage(rect, "ArtImage", new Vector2(0.04f, 0.11f), new Vector2(0.36f, 0.89f), new Color(0.12f, 0.14f, 0.16f, 1f));
        Image icon = ChildImage(rect, "AttributeIconImage", new Vector2(0.36f, 0.70f), new Vector2(0.43f, 0.88f), new Color(0f, 0.45f, 0.8f, 1f));
        TMP_Text title = ChildText(rect, "TitleText", new Vector2(0.45f, 0.78f), new Vector2(0.96f, 0.94f), "Card Name", 24, TextAlignmentOptions.Left);
        TMP_Text desc = ChildText(rect, "DescriptionText", new Vector2(0.45f, 0.52f), new Vector2(0.96f, 0.76f), "Description", 14, TextAlignmentOptions.TopLeft);
        TMP_Text attr = ChildText(rect, "AttributeText", new Vector2(0.45f, 0.44f), new Vector2(0.96f, 0.52f), "Attribute", 15, TextAlignmentOptions.Left);
        TMP_Text hp = ChildText(rect, "HpText", new Vector2(0.45f, 0.34f), new Vector2(0.58f, 0.42f), "HP", 18, TextAlignmentOptions.Left);
        TMP_Text atk = ChildText(rect, "AtkText", new Vector2(0.60f, 0.34f), new Vector2(0.73f, 0.42f), "ATK", 18, TextAlignmentOptions.Left);
        TMP_Text def = ChildText(rect, "DefenseText", new Vector2(0.75f, 0.34f), new Vector2(0.88f, 0.42f), "DEF", 18, TextAlignmentOptions.Left);
        TMP_Text en = ChildText(rect, "EnText", new Vector2(0.89f, 0.34f), new Vector2(0.98f, 0.42f), "EN", 18, TextAlignmentOptions.Left);
        TMP_Text skill = ChildText(rect, "SkillText", new Vector2(0.45f, 0.18f), new Vector2(0.96f, 0.30f), "Skill", 15, TextAlignmentOptions.Left);
        TMP_Text rarity = ChildText(rect, "RarityText", new Vector2(0.68f, 0.88f), new Vector2(0.94f, 0.98f), "R4", 18, TextAlignmentOptions.Right);

        SerializedObject so = new SerializedObject(root.GetComponent<ProductBattleCardDetailPanelView>());
        SetObject(so, "artImage", art);
        SetObject(so, "attributeIconImage", icon);
        SetObject(so, "titleText", title);
        SetObject(so, "descriptionText", desc);
        SetObject(so, "attributeText", attr);
        SetObject(so, "hpText", hp);
        SetObject(so, "atkText", atk);
        SetObject(so, "defenseText", def);
        SetObject(so, "enText", en);
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
        RectTransform content = CreateScrollContent(root.GetComponent<RectTransform>(), "Content", 2, ProductCardSize);
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
        ChildImage(rect, "ArtFrame", new Vector2(0.07f, 0.39f), new Vector2(0.93f, 0.88f), new Color(0.72f, 0.52f, 0.24f, 0.70f));
        Image art = ChildImage(rect, "ArtImage", new Vector2(0.09f, 0.41f), new Vector2(0.91f, 0.86f), new Color(0.12f, 0.14f, 0.16f, 1f));
        Image icon = ChildImage(rect, "AttributeIconImage", new Vector2(0.76f, 0.78f), new Vector2(0.94f, 0.94f), new Color(0f, 0.45f, 0.8f, 1f));
        TMP_Text unit = ChildText(rect, "UnitIdText", new Vector2(0.05f, 0.88f), new Vector2(0.32f, 0.98f), "P1", 18, TextAlignmentOptions.Left);
        TMP_Text name = ChildText(rect, "CardNameText", new Vector2(0.08f, 0.22f), new Vector2(0.92f, 0.34f), "Card Name", 15, TextAlignmentOptions.Center);
        TMP_Text hp = ChildText(rect, "HpText", new Vector2(0.08f, 0.16f), new Vector2(0.42f, 0.22f), "HP 120", 13, TextAlignmentOptions.Left);
        TMP_Text attr = ChildText(rect, "AttributeText", new Vector2(0.08f, 0.235f), new Vector2(0.92f, 0.29f), "Attribute", 13, TextAlignmentOptions.Center);
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
        Button loadButton = CreateButton(panelRect, "LoadCardsButton", "Load Cards", new Vector2(0.54f, 0.93f), new Vector2(0.63f, 0.985f));
        Button addToDeckButton = CreateButton(panelRect, "AddToDeckButton", "Add to Deck", new Vector2(0.64f, 0.93f), new Vector2(0.735f, 0.985f));
        Button saveButton = CreateButton(panelRect, "SaveDeckButton", "Save", new Vector2(0.745f, 0.93f), new Vector2(0.815f, 0.985f));
        Button simulateButton = CreateButton(panelRect, "SimulateButton", "Simulate", new Vector2(0.825f, 0.93f), new Vector2(0.905f, 0.985f));
        Button startButton = CreateButton(panelRect, "StartBattleButton", "Start", new Vector2(0.915f, 0.93f), new Vector2(0.985f, 0.985f));
        Button clearButton = CreateButton(panelRect, "ClearButton", "Clear", new Vector2(0.02f, 0.01f), new Vector2(0.10f, 0.07f));
        TMP_Text status = ChildText(panelRect, "StatusText", new Vector2(0.18f, 0.01f), new Vector2(0.70f, 0.07f), "Ready", 16, TextAlignmentOptions.Left);

        RectTransform cardList = CreateLightweightListPanel(panelRect, "CardListPanel", new Vector2(0.02f, 0.10f), new Vector2(0.24f, 0.90f), "Card List", out Transform cardListContent);
        GameObject detailObject = PrefabUtility.InstantiatePrefab(detailPrefab.gameObject, panelRect) as GameObject;
        RectTransform detail = detailObject.GetComponent<RectTransform>();
        detail.name = "CardDetailPanel";
        Anchor(detail, new Vector2(0.26f, 0.66f), new Vector2(0.76f, 0.90f));
        RectTransform deck = CreateLightweightListPanel(panelRect, "DeckListPanel", new Vector2(0.78f, 0.42f), new Vector2(0.985f, 0.90f), "Deck 10", out Transform deckContent);
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
        SetObject(so, "gridCellPrefab", cellPrefab);
        SetObject(so, "cardListContent", cardListContent);
        SetObject(so, "deckListContent", deckContent);
        SetObject(so, "formationGridContent", formationContent);
        SetObject(so, "cardDetailPanel", detailObject.GetComponent<ProductBattleCardDetailPanelView>());
        SetObject(so, "debugLogPanel", logObject.GetComponent<ProductBattleLogPanelView>());
        SetObject(so, "statusText", status);
        SetObject(so, "loadCardsButton", loadButton);
        SetObject(so, "addToDeckButton", addToDeckButton);
        SetObject(so, "saveDeckButton", saveButton);
        SetObject(so, "startBattleButton", startButton);
        SetObject(so, "simulateButton", simulateButton);
        SetObject(so, "clearButton", clearButton);
        Sprite[] cardSprites = LoadSpritesFromFolder(CardSpriteFolder);
        Sprite[] iconSprites = LoadSpritesFromFolder(IconSpriteFolder);
        SetObject(so, "defaultCardArt", FirstOrNull(cardSprites));
        SetObject(so, "defaultAttributeIcon", FirstOrNull(iconSprites));
        SetSpriteArray(so, "cardArtPool", cardSprites);
        SetAttributeSpriteArray(so, "attributeSprites", iconSprites);
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
        Sprite[] cardSprites = LoadSpritesFromFolder(CardSpriteFolder);
        Sprite[] iconSprites = LoadSpritesFromFolder(IconSpriteFolder);
        SetObject(so, "defaultCardArt", FirstOrNull(cardSprites));
        SetObject(so, "defaultAttributeIcon", FirstOrNull(iconSprites));
        SetSpriteArray(so, "cardArtPool", cardSprites);
        SetAttributeSpriteArray(so, "attributeSprites", iconSprites);
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

    private static RectTransform CreateScrollablePanel(RectTransform parent, string name, Vector2 min, Vector2 max, string title, int columns, Vector2 cellSize, out Transform content)
    {
        GameObject panel = UiChild(parent, name, typeof(RectTransform), typeof(Image));
        RectTransform rect = panel.GetComponent<RectTransform>();
        Anchor(rect, min, max);
        panel.GetComponent<Image>().color = new Color(0.015f, 0.025f, 0.035f, 0.94f);
        ChildText(rect, "HeadingText", new Vector2(0.03f, 0.92f), new Vector2(0.98f, 0.99f), title, 18, TextAlignmentOptions.Left);
        RectTransform contentRect = EnsureScrollablePanelStructure(rect, columns, cellSize);
        content = contentRect;
        return rect;
    }

    private static RectTransform CreateLightweightListPanel(RectTransform parent, string name, Vector2 min, Vector2 max, string title, out Transform content)
    {
        GameObject panel = UiChild(parent, name, typeof(RectTransform), typeof(Image));
        RectTransform rect = panel.GetComponent<RectTransform>();
        Anchor(rect, min, max);
        panel.GetComponent<Image>().color = new Color(0.015f, 0.025f, 0.035f, 0.94f);
        ChildText(rect, "HeadingText", new Vector2(0.03f, 0.92f), new Vector2(0.98f, 0.99f), title, 18, TextAlignmentOptions.Left);
        RectTransform contentRect = EnsureLightweightListPanelStructure(rect);
        content = contentRect;
        return rect;
    }

    private static RectTransform CreateScrollContent(RectTransform parent, string name, int columns, Vector2 cellSize)
    {
        RectTransform contentRect = EnsureScrollablePanelStructure(parent, columns, cellSize);
        contentRect.gameObject.name = name;
        return contentRect;
    }

    private static bool RepairProductBattlePrepPanel(ProductBattlePrepPanelView view)
    {
        if (view == null)
        {
            return false;
        }

        RectTransform cardListPanel = FindDescendant(view.transform, "CardListPanel") as RectTransform;
        RectTransform deckListPanel = FindDescendant(view.transform, "DeckListPanel") as RectTransform;
        if (cardListPanel == null && deckListPanel == null)
        {
            Debug.LogWarning($"[SourceOfThoughtBattleScene] No CardListPanel or DeckListPanel found under {view.name}.");
            return false;
        }

        Undo.RecordObject(view, "Repair Product Battle Prep ScrollViews");
        RectTransform cardContent = cardListPanel == null ? null : EnsureLightweightListPanelStructure(cardListPanel);
        RectTransform deckContent = deckListPanel == null ? null : EnsureLightweightListPanelStructure(deckListPanel);

        SerializedObject so = new SerializedObject(view);
        if (cardContent != null)
        {
            SetObject(so, "cardListContent", cardContent);
            EditorUtility.SetDirty(cardContent.gameObject);
        }
        if (deckContent != null)
        {
            SetObject(so, "deckListContent", deckContent);
            EditorUtility.SetDirty(deckContent.gameObject);
        }
        so.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(view);
        Debug.Log($"[SourceOfThoughtBattleScene] ScrollView repaired for {view.name}: cardContent={cardContent?.name ?? "missing"}, deckContent={deckContent?.name ?? "missing"}.");
        return true;
    }

    private static void RepairProductBattlePrepControls(ProductBattlePrepPanelView view)
    {
        if (view == null)
        {
            return;
        }

        RectTransform root = view.transform as RectTransform;
        if (root == null)
        {
            Debug.LogWarning($"[SourceOfThoughtBattleScene] ProductBattlePrepPanelView root is not a RectTransform: {view.name}.");
            return;
        }

        Undo.RecordObject(view, "Repair Product Battle Prep Controls");
        Button addToDeckButton = EnsurePrepButton(root, "AddToDeckButton", "Add to Deck", new Vector2(0.64f, 0.93f), new Vector2(0.735f, 0.985f));
        NormalizeProductCardViews(root);
        SerializedObject so = new SerializedObject(view);
        SetObject(so, "addToDeckButton", addToDeckButton);
        so.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(view);
        Debug.Log($"[SourceOfThoughtBattleScene] AddToDeckButton repaired for {view.name}: {(addToDeckButton == null ? "missing" : addToDeckButton.name)}.");
    }

    private static void NormalizeProductCardViews(RectTransform root)
    {
        if (root == null)
        {
            return;
        }

        ProductBattleCardView[] cardViews = root.GetComponentsInChildren<ProductBattleCardView>(true);
        foreach (ProductBattleCardView cardView in cardViews)
        {
            RectTransform rect = cardView.GetComponent<RectTransform>();
            if (rect != null)
            {
                rect.sizeDelta = ProductCardSize;
                EditorUtility.SetDirty(rect);
            }

            LayoutElement layout = cardView.GetComponent<LayoutElement>();
            if (layout == null)
            {
                layout = Undo.AddComponent<LayoutElement>(cardView.gameObject);
            }
            layout.preferredWidth = ProductCardSize.x;
            layout.preferredHeight = ProductCardSize.y;
            layout.minWidth = ProductCardSize.x;
            layout.minHeight = ProductCardSize.y;
            layout.flexibleWidth = 0f;
            layout.flexibleHeight = 0f;

            Image[] images = cardView.GetComponentsInChildren<Image>(true);
            foreach (Image image in images)
            {
                bool isRootImage = image.gameObject == cardView.gameObject;
                bool isFrame = image.gameObject.name.ToLowerInvariant().Contains("frame");
                image.raycastTarget = isRootImage || isFrame;
            }

            EditorUtility.SetDirty(cardView);
        }
    }

    private static Button EnsurePrepButton(RectTransform parent, string name, string label, Vector2 min, Vector2 max)
    {
        if (parent == null)
        {
            return null;
        }

        Transform existing = FindDirectChild(parent, name);
        RectTransform rect;
        GameObject buttonObject;
        if (existing != null)
        {
            buttonObject = existing.gameObject;
            rect = buttonObject.GetComponent<RectTransform>();
        }
        else
        {
            buttonObject = UiChild(parent, name, typeof(RectTransform), typeof(Image), typeof(Button));
            rect = buttonObject.GetComponent<RectTransform>();
            Undo.RegisterCreatedObjectUndo(buttonObject, "Create Add To Deck Button");
        }

        buttonObject.name = name;
        buttonObject.SetActive(true);
        Anchor(rect, min, max);
        rect.SetAsLastSibling();

        Image image = buttonObject.GetComponent<Image>();
        if (image == null)
        {
            image = Undo.AddComponent<Image>(buttonObject);
        }
        image.color = new Color(0.06f, 0.08f, 0.09f, 0.98f);
        image.raycastTarget = true;

        Button button = buttonObject.GetComponent<Button>();
        if (button == null)
        {
            button = Undo.AddComponent<Button>(buttonObject);
        }

        TMP_Text labelText = buttonObject.GetComponentInChildren<TMP_Text>(true);
        if (labelText == null)
        {
            labelText = ChildText(rect, "Label", Vector2.zero, Vector2.one, label, 15, TextAlignmentOptions.Center);
        }
        labelText.text = label;
        labelText.gameObject.SetActive(true);

        EditorUtility.SetDirty(button.gameObject);
        return button;
    }

    private static void RepairProductBattlePrepSpriteBindings(ProductBattlePrepPanelView view, Sprite[] cardSprites, Sprite[] iconSprites)
    {
        if (view == null)
        {
            return;
        }

        Undo.RecordObject(view, "Repair Product Battle Prep Sprites");
        SerializedObject so = new SerializedObject(view);
        SetObject(so, "defaultCardArt", FirstOrNull(cardSprites));
        SetObject(so, "defaultAttributeIcon", FirstOrNull(iconSprites));
        SetSpriteArray(so, "cardArtPool", cardSprites);
        SetAttributeSpriteArray(so, "attributeSprites", iconSprites);
        so.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(view);
    }

    private static RectTransform EnsureScrollablePanelStructure(RectTransform panel, int columns, Vector2 cellSize)
    {
        Image panelImage = panel.GetComponent<Image>();
        if (panelImage == null)
        {
            panelImage = Undo.AddComponent<Image>(panel.gameObject);
            panelImage.color = new Color(0.015f, 0.025f, 0.035f, 0.94f);
        }

        RectTransform viewportRect = FindDirectChild(panel, "Viewport") as RectTransform;
        if (viewportRect == null)
        {
            GameObject viewport = UiChild(panel, "Viewport", typeof(RectTransform), typeof(Image), typeof(Mask));
            viewportRect = viewport.GetComponent<RectTransform>();
        }
        Anchor(viewportRect, new Vector2(0.03f, 0.03f), new Vector2(0.97f, 0.90f));
        viewportRect.SetSiblingIndex(Mathf.Min(1, panel.childCount - 1));

        Image viewportImage = viewportRect.GetComponent<Image>();
        if (viewportImage == null)
        {
            viewportImage = Undo.AddComponent<Image>(viewportRect.gameObject);
        }
        viewportImage.color = new Color(0f, 0f, 0f, 0.08f);
        viewportImage.raycastTarget = true;

        Mask mask = viewportRect.GetComponent<Mask>();
        if (mask == null)
        {
            mask = Undo.AddComponent<Mask>(viewportRect.gameObject);
        }
        mask.showMaskGraphic = false;

        RectTransform contentRect = FindDirectChild(viewportRect, "Content") as RectTransform;
        if (contentRect == null)
        {
            contentRect = FindDirectChild(viewportRect, "CardContent") as RectTransform;
        }
        if (contentRect == null)
        {
            contentRect = FindDirectChild(panel, "Content") as RectTransform;
            if (contentRect == null)
            {
                contentRect = FindDirectChild(panel, "CardContent") as RectTransform;
            }
            if (contentRect != null)
            {
                Undo.SetTransformParent(contentRect, viewportRect, "Move Content Under Viewport");
                contentRect.SetParent(viewportRect, false);
            }
        }
        if (contentRect == null)
        {
            GameObject content = UiChild(viewportRect, "Content", typeof(RectTransform));
            contentRect = content.GetComponent<RectTransform>();
        }
        contentRect.gameObject.name = "Content";
        contentRect.anchorMin = new Vector2(0f, 1f);
        contentRect.anchorMax = new Vector2(1f, 1f);
        contentRect.pivot = new Vector2(0.5f, 1f);
        contentRect.anchoredPosition = Vector2.zero;
        contentRect.sizeDelta = Vector2.zero;
        contentRect.offsetMin = Vector2.zero;
        contentRect.offsetMax = Vector2.zero;

        GridLayoutGroup grid = contentRect.GetComponent<GridLayoutGroup>();
        if (grid == null)
        {
            grid = Undo.AddComponent<GridLayoutGroup>(contentRect.gameObject);
        }
        grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        grid.constraintCount = columns;
        grid.cellSize = cellSize;
        grid.spacing = ProductCardGridSpacing;
        grid.padding = new RectOffset(8, 8, 8, 8);
        grid.childAlignment = TextAnchor.UpperCenter;

        ContentSizeFitter fitter = contentRect.GetComponent<ContentSizeFitter>();
        if (fitter == null)
        {
            fitter = Undo.AddComponent<ContentSizeFitter>(contentRect.gameObject);
        }
        fitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        ScrollRect scroll = panel.GetComponent<ScrollRect>();
        if (scroll == null)
        {
            scroll = Undo.AddComponent<ScrollRect>(panel.gameObject);
        }
        scroll.viewport = viewportRect;
        scroll.content = contentRect;
        scroll.horizontal = false;
        scroll.vertical = true;
        scroll.movementType = ScrollRect.MovementType.Clamped;
        scroll.inertia = true;

        EditorUtility.SetDirty(panel.gameObject);
        EditorUtility.SetDirty(viewportRect.gameObject);
        EditorUtility.SetDirty(contentRect.gameObject);
        return contentRect;
    }

    private static RectTransform EnsureLightweightListPanelStructure(RectTransform panel)
    {
        if (panel == null)
        {
            return null;
        }

        Image panelImage = panel.GetComponent<Image>();
        if (panelImage == null)
        {
            panelImage = Undo.AddComponent<Image>(panel.gameObject);
        }
        panelImage.color = new Color(0.015f, 0.025f, 0.035f, 0.94f);

        RectTransform viewportRect = FindDirectChild(panel, "Viewport") as RectTransform;
        if (viewportRect == null)
        {
            GameObject viewport = UiChild(panel, "Viewport", typeof(RectTransform), typeof(Image), typeof(Mask));
            viewportRect = viewport.GetComponent<RectTransform>();
            Undo.RegisterCreatedObjectUndo(viewport, "Create Product Battle Prep Viewport");
        }
        Anchor(viewportRect, new Vector2(0.03f, 0.03f), new Vector2(0.97f, 0.90f));
        viewportRect.SetSiblingIndex(Mathf.Min(1, panel.childCount - 1));

        Image viewportImage = viewportRect.GetComponent<Image>();
        if (viewportImage == null)
        {
            viewportImage = Undo.AddComponent<Image>(viewportRect.gameObject);
        }
        viewportImage.color = new Color(0f, 0f, 0f, 0.08f);
        viewportImage.raycastTarget = true;

        Mask mask = viewportRect.GetComponent<Mask>();
        if (mask == null)
        {
            mask = Undo.AddComponent<Mask>(viewportRect.gameObject);
        }
        mask.showMaskGraphic = false;

        RectTransform contentRect = FindDirectChild(viewportRect, "Content") as RectTransform;
        if (contentRect == null)
        {
            contentRect = FindDirectChild(viewportRect, "CardContent") as RectTransform;
        }
        if (contentRect == null)
        {
            contentRect = FindDirectChild(panel, "Content") as RectTransform;
            if (contentRect == null)
            {
                contentRect = FindDirectChild(panel, "CardContent") as RectTransform;
            }
            if (contentRect != null)
            {
                Undo.SetTransformParent(contentRect, viewportRect, "Move Content Under Viewport");
                contentRect.SetParent(viewportRect, false);
            }
        }
        if (contentRect == null)
        {
            GameObject content = UiChild(viewportRect, "Content", typeof(RectTransform));
            contentRect = content.GetComponent<RectTransform>();
            Undo.RegisterCreatedObjectUndo(content, "Create Product Battle Prep Content");
        }

        contentRect.gameObject.name = "Content";
        contentRect.anchorMin = new Vector2(0f, 1f);
        contentRect.anchorMax = new Vector2(1f, 1f);
        contentRect.pivot = new Vector2(0.5f, 1f);
        contentRect.anchoredPosition = Vector2.zero;
        contentRect.sizeDelta = Vector2.zero;
        contentRect.offsetMin = Vector2.zero;
        contentRect.offsetMax = Vector2.zero;

        GridLayoutGroup grid = contentRect.GetComponent<GridLayoutGroup>();
        if (grid != null)
        {
            Undo.DestroyObjectImmediate(grid);
        }

        VerticalLayoutGroup vertical = contentRect.GetComponent<VerticalLayoutGroup>();
        if (vertical == null)
        {
            vertical = Undo.AddComponent<VerticalLayoutGroup>(contentRect.gameObject);
        }
        vertical.padding = new RectOffset(6, 6, 6, 6);
        vertical.spacing = ProductListRowSpacing;
        vertical.childAlignment = TextAnchor.UpperCenter;
        vertical.childControlWidth = true;
        vertical.childControlHeight = true;
        vertical.childForceExpandWidth = true;
        vertical.childForceExpandHeight = false;

        ContentSizeFitter fitter = contentRect.GetComponent<ContentSizeFitter>();
        if (fitter == null)
        {
            fitter = Undo.AddComponent<ContentSizeFitter>(contentRect.gameObject);
        }
        fitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        ScrollRect scroll = panel.GetComponent<ScrollRect>();
        if (scroll == null)
        {
            scroll = Undo.AddComponent<ScrollRect>(panel.gameObject);
        }
        scroll.viewport = viewportRect;
        scroll.content = contentRect;
        scroll.horizontal = false;
        scroll.vertical = true;
        scroll.movementType = ScrollRect.MovementType.Clamped;
        scroll.inertia = true;

        EditorUtility.SetDirty(panel.gameObject);
        EditorUtility.SetDirty(viewportRect.gameObject);
        EditorUtility.SetDirty(contentRect.gameObject);
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

    private static Transform FindDirectChild(Transform parent, string childName)
    {
        if (parent == null)
        {
            return null;
        }

        for (int i = 0; i < parent.childCount; i++)
        {
            Transform child = parent.GetChild(i);
            if (child.name == childName)
            {
                return child;
            }
        }

        return null;
    }

    private static Transform FindDescendant(Transform parent, string descendantName)
    {
        if (parent == null)
        {
            return null;
        }

        if (parent.name == descendantName)
        {
            return parent;
        }

        for (int i = 0; i < parent.childCount; i++)
        {
            Transform found = FindDescendant(parent.GetChild(i), descendantName);
            if (found != null)
            {
                return found;
            }
        }

        return null;
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

    private static void EnsurePlaceholderSpriteAssets()
    {
        EnsurePlaceholderPngAsset("Assets/Sprites/Cards/placeholder_card_art.png", new Color(0.08f, 0.16f, 0.24f, 1f), new Color(0.75f, 0.55f, 0.25f, 1f));
        EnsurePlaceholderPngAsset("Assets/Sprites/Icons/placeholder_attribute_icon.png", new Color(0.02f, 0.22f, 0.34f, 1f), new Color(0.1f, 0.85f, 1f, 1f));
        EnsureSpritesImportedFromFolder(CardSpriteFolder);
        EnsureSpritesImportedFromFolder(IconSpriteFolder);
        AssetDatabase.Refresh();
    }

    private static void EnsurePlaceholderPngAsset(string assetPath, Color background, Color foreground)
    {
        if (!File.Exists(assetPath))
        {
            Texture2D texture = new Texture2D(128, 128, TextureFormat.RGBA32, false);
            for (int y = 0; y < texture.height; y++)
            {
                for (int x = 0; x < texture.width; x++)
                {
                    bool border = x < 6 || y < 6 || x >= texture.width - 6 || y >= texture.height - 6;
                    bool diagonal = Mathf.Abs(x - y) < 3 || Mathf.Abs((texture.width - x) - y) < 3;
                    texture.SetPixel(x, y, border || diagonal ? foreground : background);
                }
            }
            texture.Apply();
            File.WriteAllBytes(assetPath, texture.EncodeToPNG());
            Object.DestroyImmediate(texture);
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
        }

        EnsureSpriteImportSettings(assetPath);
    }

    private static void EnsureSpritesImportedFromFolder(string folderPath)
    {
        if (!AssetDatabase.IsValidFolder(folderPath))
        {
            return;
        }

        string[] guids = AssetDatabase.FindAssets("t:Texture2D", new[] { folderPath });
        foreach (string guid in guids)
        {
            EnsureSpriteImportSettings(AssetDatabase.GUIDToAssetPath(guid));
        }
    }

    private static void EnsureSpriteImportSettings(string assetPath)
    {
        TextureImporter importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
        if (importer == null)
        {
            return;
        }

        bool changed = false;
        if (importer.textureType != TextureImporterType.Sprite)
        {
            importer.textureType = TextureImporterType.Sprite;
            changed = true;
        }
        if (importer.spriteImportMode != SpriteImportMode.Single)
        {
            importer.spriteImportMode = SpriteImportMode.Single;
            changed = true;
        }

        if (changed)
        {
            importer.SaveAndReimport();
        }
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

    private static Sprite[] LoadSpritesFromFolder(string folderPath)
    {
        List<Sprite> sprites = new List<Sprite>();
        if (!AssetDatabase.IsValidFolder(folderPath))
        {
            return sprites.ToArray();
        }

        EnsureSpritesImportedFromFolder(folderPath);
        string[] guids = AssetDatabase.FindAssets("t:Sprite", new[] { folderPath });
        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            Sprite sprite = AssetDatabase.LoadAssetAtPath<Sprite>(path);
            if (sprite != null)
            {
                sprites.Add(sprite);
            }
        }
        return sprites.ToArray();
    }

    private static Sprite FirstOrNull(Sprite[] sprites)
    {
        return sprites != null && sprites.Length > 0 ? sprites[0] : null;
    }

    private static void SetSpriteArray(SerializedObject serializedObject, string propertyName, Sprite[] sprites)
    {
        SerializedProperty property = serializedObject.FindProperty(propertyName);
        if (property == null || sprites == null)
        {
            return;
        }

        property.arraySize = sprites.Length;
        for (int i = 0; i < sprites.Length; i++)
        {
            property.GetArrayElementAtIndex(i).objectReferenceValue = sprites[i];
        }
    }

    private static void SetAttributeSpriteArray(SerializedObject serializedObject, string propertyName, Sprite[] sprites)
    {
        SerializedProperty property = serializedObject.FindProperty(propertyName);
        if (property == null || sprites == null)
        {
            return;
        }

        property.arraySize = sprites.Length;
        for (int i = 0; i < sprites.Length; i++)
        {
            SerializedProperty element = property.GetArrayElementAtIndex(i);
            SerializedProperty attribute = element.FindPropertyRelative("attribute");
            SerializedProperty sprite = element.FindPropertyRelative("sprite");
            string label = sprites[i] == null ? "" : sprites[i].name;
            if (attribute != null)
            {
                attribute.stringValue = label;
            }
            if (sprite != null)
            {
                sprite.objectReferenceValue = sprites[i];
            }
        }
    }
}
#endif
