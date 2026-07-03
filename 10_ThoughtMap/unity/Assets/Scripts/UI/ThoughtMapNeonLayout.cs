using UnityEngine;
using UnityEngine.Serialization;
using UnityEngine.UI;

[ExecuteAlways]
public class ThoughtMapNeonLayout : MonoBehaviour
{
    [Header("ScrollView")]
    [Tooltip("Assign Scroll View/Viewport/Content, not the Scroll View root. Only this object receives list layout components.")]
    [FormerlySerializedAs("resultItemPrefabRoot")]
    [SerializeField] private RectTransform resultListContent;

    [Header("Detail Root")]
    [Tooltip("Assign DetailPanel root. Layout components are not added to this object; a child DetailContent container is created instead.")]
    [SerializeField] private RectTransform detailPanel;
    [Tooltip("Optional. Assign DetailPanelView ContentRoot here if the scene uses one. DetailContent will be created under this object instead of the panel root.")]
    [SerializeField] private RectTransform detailContentParent;

    [Header("Existing Detail Elements")]
    [SerializeField] private RectTransform[] headerBlockItems;
    [SerializeField] private RectTransform[] resultProfileItems;
    [SerializeField] private RectTransform[] saveBlockItems;
    [SerializeField] private RectTransform[] linkBlockItems;
    [SerializeField] private RectTransform[] queryProfileItems;

    [Header("Known Controls")]
    [SerializeField] private RectTransform saveButton;
    [SerializeField] private RectTransform openLinkButton;
    [SerializeField] private RectTransform urlText;
    [SerializeField] private RectTransform resultRadarChart;
    [SerializeField] private RectTransform queryRadarChart;

    [Header("Recovery Cleanup")]
    [Tooltip("Optional: assign objects that received unsafe layout components from the old layout helper, then run the cleanup context menu.")]
    [SerializeField] private RectTransform[] unsafeLayoutRootsToClean;

    [Header("Spacing")]
    [SerializeField] private int detailPadding = 18;
    [SerializeField] private int detailBlockSpacing = 12;
    [SerializeField] private int blockPadding = 8;
    [SerializeField] private int blockSpacing = 8;
    [SerializeField] private int resultItemHeight = 74;
    [SerializeField] private int resultItemSpacing = 8;
    [SerializeField] private int resultListPadding = 10;

    private const string DetailContentName = "DetailContent";
    private const string HeaderBlockName = "HeaderBlock";
    private const string ResultProfileBlockName = "ResultProfileBlock";
    private const string SaveBlockName = "SaveBlock";
    private const string LinkBlockName = "LinkBlock";
    private const string QueryProfileBlockName = "QueryProfileBlock";

    private void OnEnable()
    {
        // Intentionally empty. Layout changes must be applied manually from the context menu.
    }

    [ContextMenu("Apply Safe Neon Layout")]
    public void ApplySafeNeonLayout()
    {
        ConfigureResultListContent();
    }

    [ContextMenu("Remove Unsafe Layout From Assigned Roots")]
    public void RemoveUnsafeLayoutFromAssignedRoots()
    {
        RemoveUnsafeLayout(saveButton, true);
        RemoveUnsafeLayout(openLinkButton, true);
        RemoveUnsafeLayout(urlText, true);
        RemoveUnsafeLayout(resultRadarChart, true);
        RemoveUnsafeLayout(queryRadarChart, true);

        if (unsafeLayoutRootsToClean == null)
        {
            return;
        }

        foreach (RectTransform target in unsafeLayoutRootsToClean)
        {
            bool keepListContentLayout = target == resultListContent;
            RemoveUnsafeLayout(target, keepListContentLayout);
        }
    }

    [ContextMenu("Rebuild Detail Panel Layout")]
    public void RebuildDetailPanelLayout()
    {
        if (detailPanel == null)
        {
            Debug.LogWarning("ThoughtMapNeonLayout needs Detail Panel assigned before rebuilding the detail layout.", this);
            return;
        }

        RemoveUnsafeLayout(detailPanel, true);

        RectTransform parent = detailContentParent == null ? detailPanel : detailContentParent;
        RemoveUnsafeLayout(parent, true);

        RectTransform detailContent = GetOrCreateContainer(parent, DetailContentName);
        StretchToParent(detailContent);
        ConfigureVerticalGroup(detailContent, detailPadding, detailBlockSpacing, true);

        RectTransform headerBlock = GetOrCreateContainer(detailContent, HeaderBlockName);
        RectTransform resultProfileBlock = GetOrCreateContainer(detailContent, ResultProfileBlockName);
        RectTransform saveBlock = GetOrCreateContainer(detailContent, SaveBlockName);
        RectTransform linkBlock = GetOrCreateContainer(detailContent, LinkBlockName);
        RectTransform queryProfileBlock = GetOrCreateContainer(detailContent, QueryProfileBlockName);

        ConfigureVerticalGroup(headerBlock, blockPadding, blockSpacing, false);
        ConfigureHorizontalGroup(resultProfileBlock, blockPadding, blockSpacing);
        ConfigureHorizontalGroup(saveBlock, blockPadding, blockSpacing);
        ConfigureHorizontalGroup(linkBlock, blockPadding, blockSpacing);
        ConfigureHorizontalGroup(queryProfileBlock, blockPadding, blockSpacing);

        ReparentItems(headerBlock, headerBlockItems);
        ReparentItems(resultProfileBlock, resultProfileItems);
        ReparentItems(saveBlock, saveBlockItems);
        ReparentItems(linkBlock, linkBlockItems);
        ReparentItems(queryProfileBlock, queryProfileItems);

        ReparentIfAssigned(saveBlock, saveButton);
        ReparentIfAssigned(linkBlock, urlText);
        ReparentIfAssigned(linkBlock, openLinkButton);
        ReparentIfAssigned(resultProfileBlock, resultRadarChart);
        ReparentIfAssigned(queryProfileBlock, queryRadarChart);

        RemoveUnsafeLayout(saveButton, true);
        RemoveUnsafeLayout(openLinkButton, true);
        RemoveUnsafeLayout(urlText, true);
        RemoveUnsafeLayout(resultRadarChart, true);
        RemoveUnsafeLayout(queryRadarChart, true);
    }

    private void ConfigureResultListContent()
    {
        if (resultListContent == null)
        {
            return;
        }

        VerticalLayoutGroup layout = Ensure<VerticalLayoutGroup>(resultListContent.gameObject);
        layout.padding = new RectOffset(resultListPadding, resultListPadding, resultListPadding, resultListPadding);
        layout.spacing = resultItemSpacing;
        layout.childAlignment = TextAnchor.UpperLeft;
        layout.childControlWidth = true;
        layout.childControlHeight = false;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        ContentSizeFitter fitter = Ensure<ContentSizeFitter>(resultListContent.gameObject);
        fitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        foreach (Transform child in resultListContent)
        {
            RectTransform item = child as RectTransform;
            if (item != null)
            {
                LayoutElement element = Ensure<LayoutElement>(item.gameObject);
                element.minHeight = resultItemHeight;
                element.preferredHeight = resultItemHeight;
                element.flexibleWidth = 1f;
            }
        }
    }

    private void ConfigureVerticalGroup(RectTransform target, int padding, int spacing, bool forceExpandWidth)
    {
        VerticalLayoutGroup layout = Ensure<VerticalLayoutGroup>(target.gameObject);
        layout.padding = new RectOffset(padding, padding, padding, padding);
        layout.spacing = spacing;
        layout.childAlignment = TextAnchor.UpperLeft;
        layout.childControlWidth = true;
        layout.childControlHeight = false;
        layout.childForceExpandWidth = forceExpandWidth;
        layout.childForceExpandHeight = false;
    }

    private void ConfigureHorizontalGroup(RectTransform target, int padding, int spacing)
    {
        HorizontalLayoutGroup layout = Ensure<HorizontalLayoutGroup>(target.gameObject);
        layout.padding = new RectOffset(padding, padding, padding, padding);
        layout.spacing = spacing;
        layout.childAlignment = TextAnchor.MiddleLeft;
        layout.childControlWidth = false;
        layout.childControlHeight = false;
        layout.childForceExpandWidth = false;
        layout.childForceExpandHeight = false;
    }

    private RectTransform GetOrCreateContainer(RectTransform parent, string childName)
    {
        Transform existing = parent.Find(childName);
        if (existing != null && existing is RectTransform existingRect)
        {
            return existingRect;
        }

        GameObject child = new GameObject(childName, typeof(RectTransform));
        RectTransform rect = child.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        return rect;
    }

    private void StretchToParent(RectTransform target)
    {
        target.anchorMin = Vector2.zero;
        target.anchorMax = Vector2.one;
        target.offsetMin = Vector2.zero;
        target.offsetMax = Vector2.zero;
        target.localScale = Vector3.one;
    }

    private void ReparentItems(RectTransform parent, RectTransform[] items)
    {
        if (items == null)
        {
            return;
        }

        foreach (RectTransform item in items)
        {
            ReparentIfAssigned(parent, item);
        }
    }

    private void ReparentIfAssigned(RectTransform parent, RectTransform item)
    {
        if (parent == null || item == null || item == parent || item == detailPanel)
        {
            return;
        }

        item.SetParent(parent, false);
        item.localScale = Vector3.one;
    }

    private void RemoveUnsafeLayout(RectTransform target, bool removeLayoutElement)
    {
        if (target == null)
        {
            return;
        }

        HorizontalLayoutGroup horizontal = target.GetComponent<HorizontalLayoutGroup>();
        if (horizontal != null && target != resultListContent)
        {
            DestroyComponent(horizontal);
        }

        VerticalLayoutGroup vertical = target.GetComponent<VerticalLayoutGroup>();
        if (vertical != null && target != resultListContent)
        {
            DestroyComponent(vertical);
        }

        ContentSizeFitter fitter = target.GetComponent<ContentSizeFitter>();
        if (fitter != null && target != resultListContent)
        {
            DestroyComponent(fitter);
        }

        LayoutElement element = target.GetComponent<LayoutElement>();
        if (removeLayoutElement && element != null)
        {
            DestroyComponent(element);
        }
    }

    private void DestroyComponent(Component component)
    {
        if (Application.isPlaying)
        {
            Destroy(component);
        }
        else
        {
            DestroyImmediate(component);
        }
    }

    private T Ensure<T>(GameObject target) where T : Component
    {
        T component = target.GetComponent<T>();
        if (component == null)
        {
            component = target.AddComponent<T>();
        }

        return component;
    }
}
