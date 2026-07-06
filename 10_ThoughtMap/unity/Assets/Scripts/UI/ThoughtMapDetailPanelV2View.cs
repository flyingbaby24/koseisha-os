using System;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class ThoughtMapDetailPanelV2View : MonoBehaviour
{
    [Header("Runtime Build")]
    [SerializeField] private bool buildOnAwake = true;
    [SerializeField] private bool debugSaveFlow = false;
    [SerializeField] private Vector2 defaultPosition = new Vector2(410f, -70f);
    [SerializeField] private Vector2 defaultSize = new Vector2(860f, 900f);

    [Header("Fonts")]
    [Tooltip("Assign the TMP Font Asset used by the existing scene for Japanese text.")]
    [SerializeField] private TMP_FontAsset japaneseFontAsset;
    [Tooltip("Optional: drag a TMP text from the existing scene that already displays Japanese correctly. V2 will copy its font asset.")]
    [SerializeField] private TMP_Text fontReferenceText;

    [Header("Palette")]
    [SerializeField] private Color panelColor = new Color(0.012f, 0.045f, 0.10f, 0.88f);
    [SerializeField] private Color blockColor = new Color(0.015f, 0.06f, 0.13f, 0.72f);
    [SerializeField] private Color textPrimary = new Color(0.92f, 0.98f, 1f, 1f);
    [SerializeField] private Color textSecondary = new Color(0.60f, 0.78f, 0.92f, 1f);
    [SerializeField] private Color cyan = new Color(0.05f, 0.82f, 1f, 0.88f);
    [SerializeField] private Color selectedRadarLine = new Color(0.08f, 0.85f, 1f, 0.96f);
    [SerializeField] private Color selectedRadarFill = new Color(0.08f, 0.85f, 1f, 0.34f);
    [SerializeField] private Color queryRadarLine = new Color(1f, 0.28f, 0.92f, 0.96f);
    [SerializeField] private Color queryRadarFill = new Color(1f, 0.28f, 0.92f, 0.32f);

    [Header("Layout Tuning")]
    [SerializeField] private Vector2 radarSize = new Vector2(420f, 420f);
    [SerializeField] private int titleFontSize = 28;
    [SerializeField] private int bodyFontSize = 16;
    [SerializeField] private int blockSpacing = 18;
    [SerializeField] private int blockPadding = 22;
    [SerializeField] private float headerHeight = 150f;
    [SerializeField] private float profileHeight = 500f;
    [SerializeField] private float actionHeight = 74f;
    [SerializeField] private float footerHeight = 64f;
    [Range(0.2f, 0.8f)]
    [SerializeField] private float parameterWidthRatio = 0.4f;
    [Range(0.2f, 0.8f)]
    [SerializeField] private float radarWidthRatio = 0.6f;
    [SerializeField] private Vector2 openButtonSize = new Vector2(170f, 52f);
    [SerializeField] private Vector2 saveButtonSize = new Vector2(250f, 52f);

    [Header("Window Interaction")]
    [SerializeField] private bool enableDragging = true;
    [Tooltip("Deprecated compatibility field. Detail blocks no longer move independently; the DetailPanelV2 root is the only movable window.")]
    [SerializeField] private bool enableDetailBlockDragging = false;
    [SerializeField] private bool enableWindowMotion = true;
    [SerializeField] private bool enableResizing = true;
    [Tooltip("Deprecated compatibility field. Detail blocks no longer resize independently; the DetailPanelV2 root owns resizing.")]
    [SerializeField] private bool enableDetailBlockResizing = false;
    [SerializeField] private Vector2 minWindowSize = new Vector2(520f, 520f);
    [SerializeField] private Vector2 minHeaderBlockSize = new Vector2(420f, 120f);
    [SerializeField] private Vector2 minProfileBlockSize = new Vector2(460f, 300f);
    [SerializeField] private Vector2 minSourceLinkBlockSize = new Vector2(360f, 70f);
    [SerializeField] private Vector2 minQueryProfileBlockSize = new Vector2(460f, 260f);
    [Tooltip("Compatibility switch for older scenes. Radar charts are always rendered as flat 2D; this only triggers legacy sanitize calls.")]
    [SerializeField] private bool enableRadar3DMotion = true;

    [Header("Diagnostics")]
    [SerializeField] private bool debugParameterFlow = false;
    [SerializeField] private bool debugBlockInteraction = false;

    private RectTransform contentRoot;
    private TMP_Text titleText;
    private TMP_Text authorText;
    private TMP_Text sourceText;
    private TMP_Text docIdText;
    private TMP_Text similarityText;
    private TMP_Text bodyText;
    private TMP_Text parameterText;
    private TMP_Text queryParameterText;
    private TMP_Text urlText;
    private TMP_Text saveStatusText;
    private Button saveButton;
    private Button openLinkButton;
    private ParameterRadarChartView radarChartView;
    private ParameterRadarChartView queryRadarChartView;
    private HologramRadarBaseView radarBaseView;
    private HologramRadarBaseView queryRadarBaseView;
    private ThoughtMapSearchResult currentResult;
    private string currentUrl = string.Empty;

    public event Action<ThoughtMapSearchResult> SaveRequested;

    private void Awake()
    {
        SanitizeDeprecatedInteractionFlags();

        if (buildOnAwake)
        {
            BuildIfNeeded();
        }

        Clear();
    }

    private void OnValidate()
    {
        SanitizeDeprecatedInteractionFlags();
    }

    public void BuildIfNeeded()
    {
        ApplyDefaultWindowRect();

        if (contentRoot != null || transform.Find("DetailContent") != null)
        {
            CacheBuiltReferences();
            EnsureQueryProfileBlock();
            EnsureWindowFeatures();
            return;
        }

        Image panelImage = GetComponent<Image>();
        if (panelImage == null)
        {
            panelImage = gameObject.AddComponent<Image>();
        }
        panelImage.color = new Color(panelColor.r, panelColor.g, panelColor.b, 0.10f);

        Outline outline = GetComponent<Outline>();
        if (outline == null)
        {
            outline = gameObject.AddComponent<Outline>();
        }
        outline.effectColor = new Color(cyan.r, cyan.g, cyan.b, 0.20f);
        outline.effectDistance = new Vector2(0.6f, -0.6f);

        if (GetComponent<CanvasGroup>() == null)
        {
            gameObject.AddComponent<CanvasGroup>();
        }

        contentRoot = CreateContainer(transform, "DetailContent", true);
        ConfigureVertical(contentRoot, blockPadding, blockSpacing);

        RectTransform header = CreateBlock(contentRoot, "HeaderBlock");
        AddPreferredSize(header.gameObject, 0f, headerHeight, false);
        ConfigureVertical(header, blockPadding, 14);
        titleText = CreateText(header, "TitleText", "Select a result", titleFontSize, FontStyles.Bold, textPrimary);
        authorText = CreateText(header, "AuthorText", string.Empty, 18, FontStyles.Normal, textSecondary);
        sourceText = CreateText(header, "SourceText", string.Empty, 16, FontStyles.Normal, textSecondary);
        docIdText = CreateText(header, "DocIdText", string.Empty, 16, FontStyles.Normal, textSecondary);
        similarityText = CreateText(header, "SimilarityText", string.Empty, 16, FontStyles.Normal, textSecondary);

        RectTransform profile = CreateBlock(contentRoot, "ResultProfileBlock");
        AddPreferredSize(profile.gameObject, 0f, profileHeight, false);
        ConfigureVertical(profile, blockPadding, 16);
        TMP_Text profileHeading = CreateText(profile, "ProfileHeadingText", "Selected Document Profile", Mathf.Max(18, titleFontSize - 2), FontStyles.Bold, textPrimary);
        profileHeading.color = textPrimary;
        RectTransform profileRow = CreateContainer(profile, "ProfileRow", false);
        AddPreferredSize(profileRow.gameObject, 0f, Mathf.Max(120f, profileHeight - 90f), false);
        ConfigureHorizontal(profileRow, blockPadding, blockSpacing);
        parameterText = CreateText(profileRow, "ParameterScoresText", "Parameter scores are not available yet.", Mathf.Max(18, bodyFontSize + 2), FontStyles.Normal, textSecondary);
        parameterText.lineSpacing = 24f;
        parameterText.enableWordWrapping = false;
        AddRatioSize(parameterText.gameObject, parameterWidthRatio, Mathf.Max(120f, profileHeight - 120f));
        RectTransform radarSlot = CreateContainer(profileRow, "RadarSlot", false);
        AddRatioSize(radarSlot.gameObject, radarWidthRatio, Mathf.Min(radarSize.y, Mathf.Max(160f, profileHeight - 120f)));
        radarBaseView = CreateHologramBase(radarSlot, "ResultRadarHologramBase", selectedRadarLine, selectedRadarFill);
        GameObject radarObject = new GameObject("ResultRadarChart", typeof(RectTransform), typeof(CanvasRenderer), typeof(ParameterRadarChartView));
        RectTransform radarRect = radarObject.GetComponent<RectTransform>();
        radarRect.SetParent(radarSlot, false);
        radarRect.anchorMin = Vector2.zero;
        radarRect.anchorMax = Vector2.one;
        radarRect.offsetMin = Vector2.zero;
        radarRect.offsetMax = Vector2.zero;
        radarChartView = radarObject.GetComponent<ParameterRadarChartView>();
        radarChartView.SetHologramStyleEnabled(enableRadar3DMotion);
        radarChartView.SetChartColors(selectedRadarLine, selectedRadarFill);

        CreateQueryProfileBlock();

        RectTransform body = CreateBlock(contentRoot, "FooterBlock");
        AddPreferredSize(body.gameObject, 0f, footerHeight, false);
        ConfigureVertical(body, blockPadding, 12);
        bodyText = CreateText(body, "BodyText", "Document detail API is not connected yet. This panel is showing the selected search result.", bodyFontSize, FontStyles.Normal, textSecondary);

        RectTransform action = CreateBlock(contentRoot, "ActionBlock");
        AddPreferredSize(action.gameObject, 0f, actionHeight, false);
        ConfigureHorizontal(action, blockPadding, blockSpacing);
        urlText = CreateText(action, "UrlText", string.Empty, Mathf.Max(13, bodyFontSize), FontStyles.Normal, textSecondary);
        AddPreferredSize(urlText.gameObject, 180, actionHeight - blockPadding, true);
        openLinkButton = CreateButton(action, "OpenLinkButton", "Open Link", openButtonSize);
        openLinkButton.onClick.AddListener(HandleOpenLinkClicked);
        saveButton = CreateButton(action, "SaveButton", "\u2606 Save to My Library", saveButtonSize);
        saveButton.onClick.AddListener(HandleSaveClicked);
        saveStatusText = CreateText(action, "SaveStatusText", string.Empty, Mathf.Max(12, bodyFontSize - 1), FontStyles.Normal, textSecondary);
        AddPreferredSize(saveStatusText.gameObject, 150, actionHeight - blockPadding, true);

        EnsureWindowFeatures();
        Clear();
    }

    public void Clear()
    {
        currentResult = null;
        currentUrl = string.Empty;
        SetText(titleText, "Select a result");
        SetText(authorText, string.Empty);
        SetText(sourceText, string.Empty);
        SetText(docIdText, string.Empty);
        SetText(similarityText, string.Empty);
        SetText(bodyText, "Select a search result to preview document details.");
        SetText(parameterText, "Parameter scores are not available yet.");
        SetText(queryParameterText, "Search query parameters are not available yet.");
        SetText(urlText, string.Empty);
        SetText(saveStatusText, string.Empty);
        if (saveButton != null) saveButton.interactable = false;
        if (openLinkButton != null) openLinkButton.gameObject.SetActive(false);
        radarChartView?.Clear();
        queryRadarChartView?.Clear();
    }

    public void ShowResult(ThoughtMapSearchResult result)
    {
        BuildIfNeeded();
        if (result == null)
        {
            Clear();
            return;
        }

        currentResult = result;
        PlayWindowShow(gameObject);
        int parameterCount = result.parameters == null ? 0 : result.parameters.Length;
        LogParameterFlow($"ShowResult doc_id={result.doc_id} parameter count={parameterCount}");
        EnsureDynamicReferences();
        EnsureWindowFeatures();
        PlayWindowShow((transform.Find("DetailContent/ResultProfileBlock") as RectTransform)?.gameObject);
        PlayWindowShow((transform.Find("DetailContent/ActionBlock") as RectTransform)?.gameObject);
        currentUrl = string.IsNullOrWhiteSpace(result.url) ? string.Empty : result.url.Trim();
        SetText(titleText, string.IsNullOrWhiteSpace(result.title) ? "Untitled" : result.title);
        SetText(authorText, string.IsNullOrWhiteSpace(result.author) ? "Unknown" : result.author);
        SetText(sourceText, string.IsNullOrWhiteSpace(result.source) ? "Source: Unknown" : $"Source: {result.source}");
        SetText(docIdText, string.IsNullOrWhiteSpace(result.doc_id) ? "Doc ID: Unknown" : $"Doc ID: {result.doc_id}");
        SetText(similarityText, $"Score: {result.similarity:0.0000}");
        SetText(bodyText, "Document detail API is not connected yet. This panel is showing the selected search result.");
        ApplyParameterScores(result.parameters);
        SetText(urlText, string.IsNullOrWhiteSpace(currentUrl) ? string.Empty : "Source Link");
        if (openLinkButton != null) openLinkButton.gameObject.SetActive(!string.IsNullOrWhiteSpace(currentUrl));
        if (saveButton != null) saveButton.interactable = !string.IsNullOrWhiteSpace(result.doc_id);
        SetText(saveStatusText, string.Empty);
        if (radarChartView != null)
        {
            radarChartView.SetHologramStyleEnabled(enableRadar3DMotion);
            radarChartView.SetChartColors(selectedRadarLine, selectedRadarFill);
            radarChartView.ShowScores(result.parameters);
        }
        else
        {
            Debug.LogWarning("[ThoughtMapDetailPanelV2] ResultRadarChart reference is missing. Parameters were shown as text only.", this);
        }

        LogDetailWindowState("ShowResult");
    }

    public void ShowQueryParameters(string queryText, ThoughtMapParameterScore[] queryParameters)
    {
        BuildIfNeeded();
        PlayWindowShow(gameObject);
        EnsureDynamicReferences();
        EnsureWindowFeatures();
        PlayWindowShow((transform.Find("DetailContent/QueryProfileBlock") as RectTransform)?.gameObject);
        int parameterCount = queryParameters == null ? 0 : queryParameters.Length;
        LogParameterFlow($"ShowQueryParameters query={queryText} parameter count={parameterCount}");
        ApplyQueryParameterScores(queryParameters);
        if (queryRadarChartView != null)
        {
            queryRadarChartView.SetHologramStyleEnabled(enableRadar3DMotion);
            queryRadarChartView.SetChartColors(queryRadarLine, queryRadarFill);
            queryRadarChartView.ShowScores(queryParameters);
        }
        else
        {
            Debug.LogWarning("[ThoughtMapDetailPanelV2] QueryRadarChart reference is missing. Query parameters were shown as text only.", this);
        }

        LogDetailWindowState("ShowQueryParameters");
    }

    public void SetSaving()
    {
        SetText(saveStatusText, "Saving...");
        if (saveButton != null) saveButton.interactable = false;
    }

    public void SetSaved(bool duplicate)
    {
        SetText(saveStatusText, duplicate ? "Already saved" : "Saved");
        if (saveButton != null) saveButton.interactable = false;
    }

    public void SetSaveError(string message)
    {
        SetText(saveStatusText, string.IsNullOrWhiteSpace(message) ? "Save failed" : $"Save failed: {message}");
        if (saveButton != null) saveButton.interactable = currentResult != null && !string.IsNullOrWhiteSpace(currentResult.doc_id);
    }

    private void HandleSaveClicked()
    {
        if (currentResult == null)
        {
            SetSaveError("No selected result.");
            return;
        }

        if (debugSaveFlow)
        {
            Debug.Log($"[ThoughtMapDetailPanelV2] Save requested doc_id={currentResult.doc_id}", this);
        }

        SaveRequested?.Invoke(currentResult);
    }

    private void HandleOpenLinkClicked()
    {
        if (!string.IsNullOrWhiteSpace(currentUrl))
        {
            Application.OpenURL(currentUrl);
        }
    }

    private string FormatRank(float value)
    {
        if (value >= 40f) return "S";
        if (value >= 30f) return "A";
        if (value >= 20f) return "B";
        if (value >= 10f) return "C";
        return "D";
    }

    private string FormatParameters(ThoughtMapParameterScore[] scores)
    {
        if (scores == null || scores.Length == 0)
        {
            return "Parameter scores are not available yet.";
        }

        StringBuilder builder = new StringBuilder();
        foreach (ThoughtMapParameterScore score in scores)
        {
            if (score == null || string.IsNullOrWhiteSpace(score.key))
            {
                continue;
            }
            builder.Append(ParameterScoreBarView.FormatLabel(score.key));
            builder.Append("   ");
            builder.Append(FormatRank(score.value));
            builder.AppendLine();
        }
        return builder.Length == 0 ? "Parameter scores are not available yet." : builder.ToString();
    }

    private void CacheBuiltReferences()
    {
        contentRoot = transform.Find("DetailContent") as RectTransform;
        EnsureDynamicReferences();
    }

    private void EnsureDynamicReferences()
    {
        titleText = titleText == null ? FindText("TitleText") : titleText;
        authorText = authorText == null ? FindText("AuthorText") : authorText;
        sourceText = sourceText == null ? FindText("SourceText") : sourceText;
        docIdText = docIdText == null ? FindText("DocIdText") : docIdText;
        similarityText = similarityText == null ? FindText("SimilarityText") : similarityText;
        bodyText = bodyText == null ? FindText("BodyText") : bodyText;
        parameterText = parameterText == null ? FindText("ParameterScoresText") : parameterText;
        queryParameterText = queryParameterText == null ? FindText("QueryParameterScoresText") : queryParameterText;
        urlText = urlText == null ? FindText("UrlText") : urlText;
        saveStatusText = saveStatusText == null ? FindText("SaveStatusText") : saveStatusText;
        saveButton = saveButton == null ? FindComponentByName<Button>("SaveButton") : saveButton;
        openLinkButton = openLinkButton == null ? FindComponentByName<Button>("OpenLinkButton") : openLinkButton;
        radarChartView = radarChartView == null ? FindComponentByName<ParameterRadarChartView>("ResultRadarChart") : radarChartView;
        queryRadarChartView = queryRadarChartView == null ? FindComponentByName<ParameterRadarChartView>("QueryRadarChart") : queryRadarChartView;
        radarBaseView = radarBaseView == null ? FindComponentByName<HologramRadarBaseView>("ResultRadarHologramBase") : radarBaseView;
        queryRadarBaseView = queryRadarBaseView == null ? FindComponentByName<HologramRadarBaseView>("QueryRadarHologramBase") : queryRadarBaseView;
        if (radarChartView != null) radarChartView.SetHologramStyleEnabled(enableRadar3DMotion);
        if (queryRadarChartView != null) queryRadarChartView.SetHologramStyleEnabled(enableRadar3DMotion);
        if (radarChartView != null) radarChartView.SetChartColors(selectedRadarLine, selectedRadarFill);
        if (queryRadarChartView != null) queryRadarChartView.SetChartColors(queryRadarLine, queryRadarFill);
        if (radarBaseView != null) radarBaseView.SetColors(selectedRadarLine, selectedRadarFill);
        if (queryRadarBaseView != null) queryRadarBaseView.SetColors(queryRadarLine, queryRadarFill);
        EnsureRadarBaseSibling(radarChartView, ref radarBaseView, "ResultRadarHologramBase", selectedRadarLine, selectedRadarFill);
        EnsureRadarBaseSibling(queryRadarChartView, ref queryRadarBaseView, "QueryRadarHologramBase", queryRadarLine, queryRadarFill);
    }

    private void ApplyParameterScores(ThoughtMapParameterScore[] scores)
    {
        int parameterCount = scores == null ? 0 : scores.Length;
        LogParameterFlow($"ApplyParameterScores count={parameterCount} parameterText={(parameterText == null ? "null" : parameterText.name)} radar={(radarChartView == null ? "null" : radarChartView.name)}");

        if (parameterText == null)
        {
            Debug.LogWarning("[ThoughtMapDetailPanelV2] ParameterScoresText reference is missing. Cannot display parameters.", this);
            return;
        }

        if (scores != null && scores.Length > 0)
        {
            parameterText.gameObject.SetActive(true);
            SetText(parameterText, FormatParameters(scores));
            return;
        }

        SetText(parameterText, "Parameter scores are not available yet.");
    }

    private void ApplyQueryParameterScores(ThoughtMapParameterScore[] scores)
    {
        int parameterCount = scores == null ? 0 : scores.Length;
        LogParameterFlow($"ApplyQueryParameterScores count={parameterCount} queryParameterText={(queryParameterText == null ? "null" : queryParameterText.name)} queryRadar={(queryRadarChartView == null ? "null" : queryRadarChartView.name)}");

        if (queryParameterText == null)
        {
            Debug.LogWarning("[ThoughtMapDetailPanelV2] QueryParameterScoresText reference is missing. Cannot display query parameters.", this);
            return;
        }

        if (scores != null && scores.Length > 0)
        {
            queryParameterText.gameObject.SetActive(true);
            SetText(queryParameterText, FormatParameters(scores));
            return;
        }

        SetText(queryParameterText, "Search query parameters are not available yet.");
    }

    private void EnsureQueryProfileBlock()
    {
        if (contentRoot == null)
        {
            contentRoot = transform.Find("DetailContent") as RectTransform;
        }

        if (contentRoot == null || transform.Find("DetailContent/QueryProfileBlock") != null)
        {
            EnsureDynamicReferences();
            return;
        }

        CreateQueryProfileBlock();
        EnsureDynamicReferences();
    }

    private void CreateQueryProfileBlock()
    {
        if (contentRoot == null)
        {
            return;
        }

        RectTransform queryProfile = CreateBlock(contentRoot, "QueryProfileBlock");
        float queryProfileHeight = Mathf.Max(280f, profileHeight * 0.72f);
        AddPreferredSize(queryProfile.gameObject, 0f, queryProfileHeight, false);
        ConfigureVertical(queryProfile, blockPadding, 16);
        TMP_Text queryHeading = CreateText(queryProfile, "QueryProfileHeadingText", "Search Query Profile", Mathf.Max(18, titleFontSize - 2), FontStyles.Bold, textPrimary);
        queryHeading.color = textPrimary;

        RectTransform queryRow = CreateContainer(queryProfile, "QueryProfileRow", false);
        AddPreferredSize(queryRow.gameObject, 0f, Mathf.Max(120f, queryProfileHeight - 90f), false);
        ConfigureHorizontal(queryRow, blockPadding, blockSpacing);

        queryParameterText = CreateText(queryRow, "QueryParameterScoresText", "Search query parameters are not available yet.", Mathf.Max(18, bodyFontSize + 2), FontStyles.Normal, textSecondary);
        queryParameterText.lineSpacing = 24f;
        queryParameterText.enableWordWrapping = false;
        AddRatioSize(queryParameterText.gameObject, parameterWidthRatio, Mathf.Max(120f, queryProfileHeight - 120f));

        RectTransform queryRadarSlot = CreateContainer(queryRow, "QueryRadarSlot", false);
        AddRatioSize(queryRadarSlot.gameObject, radarWidthRatio, Mathf.Min(radarSize.y, Mathf.Max(160f, queryProfileHeight - 120f)));
        queryRadarBaseView = CreateHologramBase(queryRadarSlot, "QueryRadarHologramBase", queryRadarLine, queryRadarFill);
        GameObject queryRadarObject = new GameObject("QueryRadarChart", typeof(RectTransform), typeof(CanvasRenderer), typeof(ParameterRadarChartView));
        RectTransform queryRadarRect = queryRadarObject.GetComponent<RectTransform>();
        queryRadarRect.SetParent(queryRadarSlot, false);
        queryRadarRect.anchorMin = Vector2.zero;
        queryRadarRect.anchorMax = Vector2.one;
        queryRadarRect.offsetMin = Vector2.zero;
        queryRadarRect.offsetMax = Vector2.zero;
        queryRadarChartView = queryRadarObject.GetComponent<ParameterRadarChartView>();
        queryRadarChartView.SetHologramStyleEnabled(enableRadar3DMotion);
        queryRadarChartView.SetChartColors(queryRadarLine, queryRadarFill);
        EnsureMotion(queryProfile.gameObject, false);
    }

    private HologramRadarBaseView CreateHologramBase(RectTransform parent, string name, Color line, Color fill)
    {
        GameObject baseObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(HologramRadarBaseView));
        RectTransform baseRect = baseObject.GetComponent<RectTransform>();
        baseRect.SetParent(parent, false);
        baseRect.anchorMin = Vector2.zero;
        baseRect.anchorMax = Vector2.one;
        baseRect.offsetMin = Vector2.zero;
        baseRect.offsetMax = Vector2.zero;
        HologramRadarBaseView baseView = baseObject.GetComponent<HologramRadarBaseView>();
        baseView.SetColors(line, fill);
        return baseView;
    }

    private void EnsureRadarBaseSibling(ParameterRadarChartView chart, ref HologramRadarBaseView baseView, string name, Color line, Color fill)
    {
        if (chart == null)
        {
            return;
        }

        RectTransform chartRect = chart.transform as RectTransform;
        RectTransform parent = chartRect == null ? null : chartRect.parent as RectTransform;
        if (parent == null)
        {
            return;
        }

        if (baseView == null)
        {
            Transform existing = parent.Find(name);
            baseView = existing == null ? null : existing.GetComponent<HologramRadarBaseView>();
        }

        if (baseView == null)
        {
            baseView = CreateHologramBase(parent, name, line, fill);
        }

        baseView.SetColors(line, fill);
        RectTransform baseRect = baseView.transform as RectTransform;
        if (baseRect != null)
        {
            baseRect.SetAsFirstSibling();
        }

        chartRect.SetAsLastSibling();
    }

    private void EnsureWindowFeatures()
    {
        SanitizeDeprecatedInteractionFlags();
        ApplyRootFrameStyle();
        RepairDetailContentHierarchy();
        EnsureMotion(gameObject, true);

        RectTransform rootRect = transform as RectTransform;
        EnsureRootDragTarget(rootRect);
        EnsureRootResizeHandle(rootRect);
        LogDetailWindowState("EnsureWindowFeatures");
    }

    private void ApplyRootFrameStyle()
    {
        Image panelImage = GetComponent<Image>();
        if (panelImage != null)
        {
            panelImage.color = new Color(panelColor.r, panelColor.g, panelColor.b, 0.10f);
            panelImage.raycastTarget = true;
        }

        Outline outline = GetComponent<Outline>();
        if (outline != null)
        {
            outline.effectColor = new Color(cyan.r, cyan.g, cyan.b, 0.20f);
            outline.effectDistance = new Vector2(0.6f, -0.6f);
        }
    }

    private void RepairDetailContentHierarchy()
    {
        RectTransform detailContent = transform.Find("DetailContent") as RectTransform;
        if (detailContent == null)
        {
            return;
        }

        StretchToParent(detailContent);

        ThoughtMapDraggableWindow[] staleDrags = detailContent.GetComponentsInChildren<ThoughtMapDraggableWindow>(true);
        foreach (ThoughtMapDraggableWindow staleDrag in staleDrags)
        {
            RemoveComponentIfExists<ThoughtMapDraggableWindow>(staleDrag.gameObject);
        }

        ThoughtMapResizableWindow[] staleResizers = detailContent.GetComponentsInChildren<ThoughtMapResizableWindow>(true);
        foreach (ThoughtMapResizableWindow staleResize in staleResizers)
        {
            RemoveComponentIfExists<ThoughtMapResizableWindow>(staleResize.gameObject);
        }

        foreach (RectTransform block in GetDetailBlocks())
        {
            if (block == null)
            {
                continue;
            }

            LayoutElement layout = block.GetComponent<LayoutElement>();
            if (layout != null)
            {
                layout.ignoreLayout = false;
            }

            block.localRotation = Quaternion.identity;
            block.localScale = Vector3.one;
            ConfigureBlockAsLayoutOnly(block);
            RemoveBlockResizeHandle(block);
            RemoveComponentIfExists<ThoughtMapDraggableWindow>(block.gameObject);
            RemoveComponentIfExists<ThoughtMapResizableWindow>(block.gameObject);
            RemoveComponentIfExists<ThoughtMapWindowMotion>(block.gameObject);
        }

        RestoreDetailBlockOrder();
    }

    private void SanitizeDeprecatedInteractionFlags()
    {
        enableDetailBlockDragging = false;
        enableDetailBlockResizing = false;
    }

    private void ConfigureBlockAsLayoutOnly(RectTransform block)
    {
        if (block == null)
        {
            return;
        }

        LayoutElement layout = block.GetComponent<LayoutElement>();
        if (layout != null)
        {
            layout.ignoreLayout = false;
        }

        Graphic[] graphics = block.GetComponentsInChildren<Graphic>(true);
        foreach (Graphic graphic in graphics)
        {
            if (graphic == null)
            {
                continue;
            }

            Button button = graphic.GetComponent<Button>();
            if (button != null)
            {
                graphic.raycastTarget = true;
                continue;
            }

            graphic.raycastTarget = false;
        }
    }

    private RectTransform[] GetDetailBlocks()
    {
        return new[]
        {
            transform.Find("DetailContent/HeaderBlock") as RectTransform,
            transform.Find("DetailContent/ResultProfileBlock") as RectTransform,
            transform.Find("DetailContent/FooterBlock") as RectTransform,
            transform.Find("DetailContent/ActionBlock") as RectTransform,
            transform.Find("DetailContent/QueryProfileBlock") as RectTransform
        };
    }

    private void RestoreDetailBlockOrder()
    {
        SetDetailBlockSibling("HeaderBlock", 0);
        SetDetailBlockSibling("ResultProfileBlock", 1);
        SetDetailBlockSibling("FooterBlock", 2);
        SetDetailBlockSibling("ActionBlock", 3);
        SetDetailBlockSibling("QueryProfileBlock", 4);
    }

    private void SetDetailBlockSibling(string blockName, int index)
    {
        Transform block = transform.Find($"DetailContent/{blockName}");
        if (block != null)
        {
            block.SetSiblingIndex(index);
        }
    }

    private void RemoveBlockResizeHandle(RectTransform block)
    {
        if (block == null)
        {
            return;
        }

        Transform handle = block.Find("ResizeHandle");
        if (handle != null)
        {
            DestroyRuntimeObject(handle.gameObject);
        }
    }

    private void StretchToParent(RectTransform rect)
    {
        if (rect == null)
        {
            return;
        }

        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
        rect.localScale = Vector3.one;
        rect.localRotation = Quaternion.identity;
    }

    private void RemoveComponentIfExists<T>(GameObject target) where T : Component
    {
        if (target == null)
        {
            return;
        }

        T component = target.GetComponent<T>();
        if (component != null)
        {
            DestroyRuntimeObject(component);
        }
    }

    private void DestroyRuntimeObject(UnityEngine.Object target)
    {
        if (target == null)
        {
            return;
        }

        if (Application.isPlaying)
        {
            Destroy(target);
        }
        else
        {
            DestroyImmediate(target);
        }
    }

    private void EnsureRootDragTarget(RectTransform root)
    {
        if (!enableDragging || root == null)
        {
            return;
        }

        Image panelImage = root.GetComponent<Image>();
        if (panelImage == null)
        {
            panelImage = root.gameObject.AddComponent<Image>();
            panelImage.color = new Color(panelColor.r, panelColor.g, panelColor.b, 0.10f);
        }

        panelImage.raycastTarget = true;

        ThoughtMapDraggableWindow drag = root.GetComponent<ThoughtMapDraggableWindow>();
        if (drag == null)
        {
            drag = root.gameObject.AddComponent<ThoughtMapDraggableWindow>();
        }

        drag.Configure(root, false, false);
        LogBlockInteraction($"Prepared root-only drag target={root.name}");
    }

    private void EnsureRootResizeHandle(RectTransform root)
    {
        if (!enableResizing || root == null)
        {
            return;
        }

        RectTransform handle = transform.Find("ResizeHandle") as RectTransform;
        if (handle == null)
        {
            GameObject handleObject = new GameObject("ResizeHandle", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
            handle = handleObject.GetComponent<RectTransform>();
            handle.SetParent(transform, false);
            handle.anchorMin = new Vector2(1f, 0f);
            handle.anchorMax = new Vector2(1f, 0f);
            handle.pivot = new Vector2(1f, 0f);
            handle.anchoredPosition = new Vector2(-8f, 8f);
            handle.sizeDelta = new Vector2(28f, 28f);
            Image image = handleObject.GetComponent<Image>();
            image.color = new Color(cyan.r, cyan.g, cyan.b, 0.35f);
            image.raycastTarget = true;
            Outline outline = handleObject.AddComponent<Outline>();
            outline.effectColor = new Color(cyan.r, cyan.g, cyan.b, 0.85f);
            outline.effectDistance = new Vector2(1f, -1f);
            LayoutElement layout = handleObject.AddComponent<LayoutElement>();
            layout.ignoreLayout = true;
        }

        handle.SetAsLastSibling();

        ThoughtMapResizableWindow resize = handle.GetComponent<ThoughtMapResizableWindow>();
        if (resize == null)
        {
            resize = handle.gameObject.AddComponent<ThoughtMapResizableWindow>();
        }

        resize.Configure(root, minWindowSize);
        LogBlockInteraction($"Prepared root resize handle={handle.name} target={root.name}");
    }

    private void LogDetailWindowState(string reason)
    {
        if (!debugBlockInteraction)
        {
            return;
        }

        RectTransform detailContent = transform.Find("DetailContent") as RectTransform;
        int illegalDragCount = detailContent == null ? 0 : detailContent.GetComponentsInChildren<ThoughtMapDraggableWindow>(true).Length;
        int illegalResizeCount = detailContent == null ? 0 : detailContent.GetComponentsInChildren<ThoughtMapResizableWindow>(true).Length;
        bool hasRootDrag = GetComponent<ThoughtMapDraggableWindow>() != null;
        bool hasRootResize = (transform.Find("ResizeHandle") as RectTransform)?.GetComponent<ThoughtMapResizableWindow>() != null;
        LayoutElement rootLayout = GetComponent<LayoutElement>();
        string rootLayoutState = rootLayout == null ? "none" : rootLayout.ignoreLayout.ToString();

        Debug.Log(
            $"[ThoughtMapDetailPanelV2] WindowState reason={reason} rootDrag={hasRootDrag} rootResize={hasRootResize} rootIgnoreLayout={rootLayoutState} illegalBlockDrag={illegalDragCount} illegalBlockResize={illegalResizeCount}",
            this
        );

        foreach (RectTransform block in GetDetailBlocks())
        {
            if (block == null)
            {
                continue;
            }

            LayoutElement layout = block.GetComponent<LayoutElement>();
            string ignoreLayout = layout == null ? "none" : layout.ignoreLayout.ToString();
            Debug.Log($"[ThoughtMapDetailPanelV2] BlockState name={block.name} ignoreLayout={ignoreLayout}", block);
        }
    }

    private ThoughtMapWindowMotion EnsureMotion(GameObject target, bool playNow)
    {
        if (!enableWindowMotion || target == null)
        {
            return null;
        }

        ThoughtMapWindowMotion motion = target.GetComponent<ThoughtMapWindowMotion>();
        if (motion == null)
        {
            motion = target.AddComponent<ThoughtMapWindowMotion>();
        }

        if (playNow)
        {
            motion.Show();
        }

        return motion;
    }

    private void PlayWindowShow(GameObject target)
    {
        if (!enableWindowMotion || target == null)
        {
            return;
        }

        ThoughtMapWindowMotion motion = target.GetComponent<ThoughtMapWindowMotion>();
        if (motion != null)
        {
            motion.Show();
        }
    }

    private TMP_Text FindText(string objectName)
    {
        TMP_Text[] texts = GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            if (text != null && text.name == objectName)
            {
                return text;
            }
        }
        return null;
    }

    private T FindComponentByName<T>(string objectName) where T : Component
    {
        T[] components = GetComponentsInChildren<T>(true);
        foreach (T component in components)
        {
            if (component != null && component.name == objectName)
            {
                return component;
            }
        }
        return null;
    }

    private RectTransform CreateBlock(RectTransform parent, string name)
    {
        RectTransform block = CreateContainer(parent, name, false);
        Image image = block.gameObject.AddComponent<Image>();
        image.color = blockColor;
        Outline outline = block.gameObject.AddComponent<Outline>();
        outline.effectColor = new Color(cyan.r, cyan.g, cyan.b, 0.35f);
        outline.effectDistance = new Vector2(0.8f, -0.8f);
        ContentSizeFitter fitter = block.gameObject.AddComponent<ContentSizeFitter>();
        fitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        return block;
    }

    private RectTransform CreateContainer(Transform parent, string name, bool stretch)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform));
        RectTransform rect = obj.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        if (stretch)
        {
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }
        return rect;
    }

    private TMP_Text CreateText(Transform parent, string name, string value, int size, FontStyles style, Color color)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = obj.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        TMP_Text text = obj.GetComponent<TMP_Text>();
        ApplyFont(text);
        text.text = value;
        text.fontSize = size;
        text.fontStyle = style;
        text.color = color;
        text.enableWordWrapping = true;
        text.wordWrappingRatios = 0.4f;
        text.overflowMode = TextOverflowModes.Ellipsis;
        text.raycastTarget = false;
        ContentSizeFitter fitter = obj.AddComponent<ContentSizeFitter>();
        fitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        return text;
    }

    private void ApplyFont(TMP_Text text)
    {
        if (text == null)
        {
            return;
        }

        TMP_FontAsset font = japaneseFontAsset;
        if (font == null && fontReferenceText != null)
        {
            font = fontReferenceText.font;
        }

        if (font != null)
        {
            text.font = font;
        }
    }

    [ContextMenu("Apply Font To Generated Texts")]
    public void ApplyFontToGeneratedTexts()
    {
        TMP_Text[] texts = GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            ApplyFont(text);
        }
    }

    private Button CreateButton(Transform parent, string name, string label, Vector2 size)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button), typeof(NeonHoverGlow));
        RectTransform rect = obj.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        AddPreferredSize(obj, size.x, size.y);
        Image image = obj.GetComponent<Image>();
        image.color = new Color(0.018f, 0.05f, 0.11f, 0.96f);
        Button button = obj.GetComponent<Button>();
        TMP_Text text = CreateText(obj.transform, "Label", label, 15, FontStyles.Normal, textPrimary);
        RectTransform textRect = text.rectTransform;
        textRect.anchorMin = Vector2.zero;
        textRect.anchorMax = Vector2.one;
        textRect.offsetMin = Vector2.zero;
        textRect.offsetMax = Vector2.zero;
        text.alignment = TextAlignmentOptions.Center;
        ContentSizeFitter labelFitter = text.GetComponent<ContentSizeFitter>();
        if (labelFitter != null)
        {
            Destroy(labelFitter);
        }
        return button;
    }

    private void ConfigureVertical(RectTransform target, int padding, int spacing)
    {
        VerticalLayoutGroup layout = target.gameObject.AddComponent<VerticalLayoutGroup>();
        layout.padding = new RectOffset(padding, padding, padding, padding);
        layout.spacing = spacing;
        layout.childAlignment = TextAnchor.MiddleCenter;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;
    }

    private void ConfigureHorizontal(RectTransform target, int padding, int spacing)
    {
        HorizontalLayoutGroup existingVertical = target.GetComponent<HorizontalLayoutGroup>();
        if (existingVertical == null)
        {
            HorizontalLayoutGroup layout = target.gameObject.AddComponent<HorizontalLayoutGroup>();
            layout.padding = new RectOffset(padding, padding, padding, padding);
            layout.spacing = spacing;
            layout.childAlignment = TextAnchor.UpperLeft;
            layout.childControlWidth = true;
            layout.childControlHeight = true;
            layout.childForceExpandWidth = true;
            layout.childForceExpandHeight = false;
        }
    }

    private void AddRatioSize(GameObject target, float widthRatio, float height)
    {
        LayoutElement element = EnsureLayoutElement(target);
        element.flexibleWidth = Mathf.Max(0.01f, widthRatio);
        element.preferredHeight = height;
        element.minHeight = height;
    }

    private void AddPreferredSize(GameObject target, float width, float height)
    {
        AddPreferredSize(target, width, height, true);
    }

    private void AddPreferredSize(GameObject target, float width, float height, bool setWidth)
    {
        LayoutElement element = EnsureLayoutElement(target);
        if (setWidth)
        {
            element.preferredWidth = width;
            element.minWidth = width;
        }
        else
        {
            element.flexibleWidth = 1f;
        }
        element.preferredHeight = height;
        element.minHeight = height;
    }

    private LayoutElement EnsureLayoutElement(GameObject target)
    {
        LayoutElement element = target.GetComponent<LayoutElement>();
        if (element == null)
        {
            element = target.AddComponent<LayoutElement>();
        }
        return element;
    }

    private RectTransform EnsureRectTransform(GameObject target)
    {
        RectTransform rect = target.transform as RectTransform;
        if (rect == null)
        {
            Debug.LogWarning("ThoughtMapDetailPanelV2View should be placed under a Canvas so its root has a RectTransform.", this);
        }
        return rect;
    }

    private void ApplyDefaultWindowRect()
    {
        RectTransform rect = EnsureRectTransform(gameObject);
        if (rect == null) return;

        rect.anchorMin = new Vector2(0.5f, 0.5f);
        rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.anchoredPosition = defaultPosition;
        rect.sizeDelta = defaultSize;
    }

    private void SetText(TMP_Text target, string value)
    {
        if (target != null)
        {
            target.text = value;
        }
    }

    private void LogParameterFlow(string message)
    {
        if (debugParameterFlow)
        {
            Debug.Log($"[ThoughtMapDetailPanelV2] {message}", this);
        }
    }

    private void LogBlockInteraction(string message)
    {
        if (debugBlockInteraction)
        {
            Debug.Log($"[ThoughtMapDetailPanelV2][BlockInteraction] {message}", this);
        }
    }
}
