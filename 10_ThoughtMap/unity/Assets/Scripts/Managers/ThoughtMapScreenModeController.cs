using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public enum SourceOfThoughtScreenMode
{
    Menu,
    Search,
    Battle
}

// Compatibility helper for older same-scene prototypes.
// Current Source of Thought architecture uses separate scenes:
// Input/Register, Search/Collect, Battle Prep, and Battle.
// Do not use this controller to merge Battle UI into the Search/Collect scene.
public class ThoughtMapScreenModeController : MonoBehaviour
{
    [Header("Startup")]
    [SerializeField] private SourceOfThoughtScreenMode initialMode = SourceOfThoughtScreenMode.Menu;
    [SerializeField] private bool buildMenuOnAwake = true;
    [SerializeField] private bool autoResolveV2Roots = true;

    [Header("Menu")]
    [SerializeField] private RectTransform menuRoot;
    [SerializeField] private Vector2 menuSize = new Vector2(720f, 420f);
    [SerializeField] private Vector2 menuPosition = Vector2.zero;
    [SerializeField] private string titleText = "Source of Thought";
    [SerializeField] private string subtitleText = "Select a mode";

    [Header("Screen Roots")]
    [SerializeField] private GameObject[] searchUiRoots;
    [SerializeField] private GameObject[] battleUiRoots;
    [SerializeField] private ThoughtMapBattleMvpPanelView battlePanelView;

    [Header("Style")]
    [SerializeField] private Color backgroundColor = new Color(0.005f, 0.018f, 0.05f, 0.95f);
    [SerializeField] private Color panelColor = new Color(0.012f, 0.045f, 0.10f, 0.92f);
    [SerializeField] private Color buttonColor = new Color(0.0f, 0.24f, 0.36f, 0.95f);
    [SerializeField] private Color textPrimary = new Color(0.90f, 0.97f, 1f, 1f);
    [SerializeField] private Color textSecondary = new Color(0.58f, 0.76f, 0.90f, 1f);
    [SerializeField] private Color cyan = new Color(0.05f, 0.82f, 1f, 0.8f);

    private Button searchButton;
    private Button battleButton;
    private SourceOfThoughtScreenMode currentMode;

    private void Awake()
    {
        if (autoResolveV2Roots)
        {
            ResolveScreenRoots();
        }

        if (buildMenuOnAwake)
        {
            BuildMenu();
        }

        Show(initialMode);
    }

    [ContextMenu("Build Source of Thought Menu")]
    public void BuildMenu()
    {
        if (menuRoot == null)
        {
            menuRoot = CreateMenuRoot();
        }

        ClearChildren(menuRoot);
        Image panel = EnsureImage(menuRoot.gameObject, panelColor);
        panel.raycastTarget = true;
        Outline outline = menuRoot.GetComponent<Outline>();
        if (outline == null)
        {
            outline = menuRoot.gameObject.AddComponent<Outline>();
        }
        outline.effectColor = cyan;
        outline.effectDistance = new Vector2(1.4f, -1.4f);

        VerticalLayoutGroup layout = EnsureVerticalLayout(menuRoot.gameObject, 22f, 34, 34, 34, 34);
        layout.childAlignment = TextAnchor.MiddleCenter;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        TMP_Text title = CreateText(menuRoot, "TitleText", titleText, 42, FontStyles.Bold, textPrimary);
        title.alignment = TextAlignmentOptions.Center;
        AddLayout(title.gameObject, 0f, 70f, true);

        TMP_Text subtitle = CreateText(menuRoot, "SubtitleText", subtitleText, 18, FontStyles.Normal, textSecondary);
        subtitle.alignment = TextAlignmentOptions.Center;
        AddLayout(subtitle.gameObject, 0f, 36f, true);

        RectTransform buttonRow = CreateContainer(menuRoot, "ModeButtons");
        HorizontalLayoutGroup rowLayout = EnsureHorizontalLayout(buttonRow.gameObject, 20f, 0, 0, 0, 0);
        rowLayout.childAlignment = TextAnchor.MiddleCenter;
        rowLayout.childForceExpandWidth = false;
        rowLayout.childForceExpandHeight = false;
        AddLayout(buttonRow.gameObject, 0f, 78f, true);

        searchButton = CreateButton(buttonRow, "SearchButton", "Search", new Vector2(220f, 58f));
        searchButton.onClick.AddListener(ShowSearch);

        battleButton = CreateButton(buttonRow, "BattleButton", "Battle", new Vector2(220f, 58f));
        battleButton.onClick.AddListener(ShowBattle);
    }

    public void ShowMenu()
    {
        Show(SourceOfThoughtScreenMode.Menu);
    }

    public void ShowSearch()
    {
        Show(SourceOfThoughtScreenMode.Search);
    }

    public void ShowBattle()
    {
        Show(SourceOfThoughtScreenMode.Battle);
    }

    public void Show(SourceOfThoughtScreenMode mode)
    {
        currentMode = mode;
        SetMenuVisible(mode == SourceOfThoughtScreenMode.Menu);
        SetRootsActive(searchUiRoots, mode == SourceOfThoughtScreenMode.Search);
        SetRootsActive(battleUiRoots, mode == SourceOfThoughtScreenMode.Battle);
        if (battlePanelView != null)
        {
            battlePanelView.SetVisible(mode == SourceOfThoughtScreenMode.Battle);
        }

        Debug.Log($"[ThoughtMapScreenMode] Showing {mode}", this);
    }

    [ContextMenu("Show Menu")]
    private void ContextShowMenu()
    {
        ShowMenu();
    }

    [ContextMenu("Show Search")]
    private void ContextShowSearch()
    {
        ShowSearch();
    }

    [ContextMenu("Show Battle")]
    private void ContextShowBattle()
    {
        ShowBattle();
    }

    private void ResolveScreenRoots()
    {
        if (searchUiRoots == null || searchUiRoots.Length == 0)
        {
            List<GameObject> searchRoots = new List<GameObject>();
            AddRoot(searchRoots, FindSceneObject<SearchHeaderV2View>());
            AddRoot(searchRoots, FindSceneObject<ResultListV2View>());
            AddRoot(searchRoots, FindSceneObject<ThoughtMapDetailPanelV2View>());
            searchUiRoots = searchRoots.ToArray();
        }

        if (battlePanelView == null)
        {
            battlePanelView = FindSceneObject<ThoughtMapBattleMvpPanelView>();
        }

        if ((battleUiRoots == null || battleUiRoots.Length == 0) && battlePanelView != null)
        {
            battleUiRoots = new[] { battlePanelView.gameObject };
        }
    }

    private void AddRoot<T>(List<GameObject> roots, T component) where T : Component
    {
        if (component == null || component.gameObject == gameObject)
        {
            return;
        }

        if (!roots.Contains(component.gameObject))
        {
            roots.Add(component.gameObject);
        }
    }

    private T FindSceneObject<T>() where T : Component
    {
        T[] components = Resources.FindObjectsOfTypeAll<T>();
        foreach (T component in components)
        {
            if (component == null || component.gameObject == null)
            {
                continue;
            }

            if (!component.gameObject.scene.IsValid())
            {
                continue;
            }

            return component;
        }

        return null;
    }

    private void SetMenuVisible(bool visible)
    {
        if (menuRoot != null)
        {
            menuRoot.gameObject.SetActive(visible);
        }
    }

    private void SetRootsActive(GameObject[] roots, bool active)
    {
        if (roots == null)
        {
            return;
        }

        foreach (GameObject root in roots)
        {
            if (root != null && root != gameObject)
            {
                root.SetActive(active);
            }
        }
    }

    private RectTransform CreateMenuRoot()
    {
        GameObject menuObject = new GameObject("SourceOfThoughtMenu", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        RectTransform rect = menuObject.GetComponent<RectTransform>();
        Transform parent = transform;
        Canvas canvas = GetComponentInParent<Canvas>();
        if (canvas != null)
        {
            parent = canvas.transform;
        }
        rect.SetParent(parent, false);
        rect.anchorMin = new Vector2(0.5f, 0.5f);
        rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.sizeDelta = menuSize;
        rect.anchoredPosition = menuPosition;
        return rect;
    }

    private RectTransform CreateContainer(RectTransform parent, string name)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform));
        RectTransform rect = obj.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        return rect;
    }

    private Button CreateButton(RectTransform parent, string name, string label, Vector2 size)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button));
        RectTransform rect = obj.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        rect.sizeDelta = size;
        Image image = obj.GetComponent<Image>();
        image.color = buttonColor;
        Outline outline = obj.AddComponent<Outline>();
        outline.effectColor = cyan;
        outline.effectDistance = new Vector2(1.2f, -1.2f);

        Button button = obj.GetComponent<Button>();
        ColorBlock colors = button.colors;
        colors.normalColor = buttonColor;
        colors.highlightedColor = new Color(0.02f, 0.42f, 0.62f, 1f);
        colors.pressedColor = new Color(0.04f, 0.62f, 0.82f, 1f);
        button.colors = colors;
        AddLayout(obj, size.x, size.y, false);

        TMP_Text text = CreateText(rect, "Label", label, 20, FontStyles.Bold, textPrimary);
        text.alignment = TextAlignmentOptions.Center;
        Stretch(text.rectTransform, 0f);
        return button;
    }

    private TMP_Text CreateText(RectTransform parent, string name, string value, int size, FontStyles style, Color color)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = obj.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        TMP_Text text = obj.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = size;
        text.fontStyle = style;
        text.color = color;
        text.enableWordWrapping = true;
        return text;
    }

    private Image EnsureImage(GameObject target, Color color)
    {
        Image image = target.GetComponent<Image>();
        if (image == null)
        {
            image = target.AddComponent<Image>();
        }
        image.color = color;
        return image;
    }

    private VerticalLayoutGroup EnsureVerticalLayout(GameObject target, float spacing, int left, int right, int top, int bottom)
    {
        VerticalLayoutGroup layout = target.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = target.AddComponent<VerticalLayoutGroup>();
        }
        layout.spacing = spacing;
        layout.padding = new RectOffset(left, right, top, bottom);
        return layout;
    }

    private HorizontalLayoutGroup EnsureHorizontalLayout(GameObject target, float spacing, int left, int right, int top, int bottom)
    {
        HorizontalLayoutGroup layout = target.GetComponent<HorizontalLayoutGroup>();
        if (layout == null)
        {
            layout = target.AddComponent<HorizontalLayoutGroup>();
        }
        layout.spacing = spacing;
        layout.padding = new RectOffset(left, right, top, bottom);
        return layout;
    }

    private void AddLayout(GameObject target, float width, float height, bool flexibleWidth)
    {
        LayoutElement layout = target.GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = target.AddComponent<LayoutElement>();
        }
        layout.preferredWidth = width;
        layout.preferredHeight = height;
        layout.flexibleWidth = flexibleWidth ? 1f : 0f;
    }

    private void Stretch(RectTransform rect, float inset)
    {
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = new Vector2(inset, inset);
        rect.offsetMax = new Vector2(-inset, -inset);
    }

    private void ClearChildren(RectTransform root)
    {
        for (int i = root.childCount - 1; i >= 0; i--)
        {
            GameObject child = root.GetChild(i).gameObject;
            if (Application.isPlaying)
            {
                Destroy(child);
            }
            else
            {
                DestroyImmediate(child);
            }
        }
    }
}
