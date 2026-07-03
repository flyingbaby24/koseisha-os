using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class DetailPanelView : MonoBehaviour
{
    [SerializeField] private GameObject emptyStateRoot;
    [SerializeField] private GameObject contentRoot;
    [SerializeField] private TMP_Text titleText;
    [SerializeField] private TMP_Text authorText;
    [SerializeField] private TMP_Text sourceText;
    [SerializeField] private TMP_Text docIdText;
    [SerializeField] private TMP_Text similarityText;
    [SerializeField] private TMP_Text bodyText;
    [SerializeField] private TMP_Text radarHeadingText;
    [SerializeField] private TMP_Text urlText;
    [SerializeField] private Button openLinkButton;
    [SerializeField] private TMP_Text saveStatusText;
    [SerializeField] private Button saveButton;
    [SerializeField] private ParameterScoresPanelView parameterScoresPanelView;
    [SerializeField] private ParameterRadarChartView radarChartView;
    [SerializeField] private NeonSlideIn slideInEffect;
    [SerializeField] private bool debugSaveFlow = true;

    private ThoughtMapSearchResult currentResult;
    private string currentUrl = string.Empty;
    private bool saveButtonListenerRegistered;

    public event Action<ThoughtMapSearchResult> SaveRequested;

    private void Awake()
    {
        LogSaveFlow($"Awake detailPanel={name} saveButton={(saveButton == null ? "null" : saveButton.name)}");
        if (openLinkButton != null)
        {
            openLinkButton.onClick.AddListener(HandleOpenLinkClicked);
        }
        if (slideInEffect == null)
        {
            slideInEffect = GetComponent<NeonSlideIn>();
        }

        if (slideInEffect == null)
        {
            slideInEffect = gameObject.AddComponent<NeonSlideIn>();
        }

        ConfigureActionButtonLabels();
        Clear();
    }

    private void OnEnable()
    {
        RegisterSaveButtonListener();
    }

    private void OnDisable()
    {
        UnregisterSaveButtonListener();
    }

    private void OnDestroy()
    {
        UnregisterSaveButtonListener();
        if (openLinkButton != null)
        {
            openLinkButton.onClick.RemoveListener(HandleOpenLinkClicked);
        }
    }

    public void Clear()
    {
        currentResult = null;
        currentUrl = string.Empty;
        SetVisible(false);
        SetText(titleText, "Select a result");
        SetText(authorText, "");
        SetText(sourceText, "");
        SetText(docIdText, "");
        SetText(similarityText, "");
        SetText(bodyText, "Select a search result to preview document details.");
        SetText(radarHeadingText, "Selected Document Profile");
        SetUrl("");
        SetSaveStatus("");
        SetSaveInteractable(false);
        parameterScoresPanelView?.Clear();
        radarChartView?.Clear();
        LogSaveFlow("Clear currentResult=null saveButtonInteractable=false");
    }

    public void ShowResult(ThoughtMapSearchResult result)
    {
        if (result == null)
        {
            LogSaveFlow("ShowResult received null result");
            Clear();
            return;
        }

        currentResult = result;
        currentUrl = string.IsNullOrWhiteSpace(result.url) ? string.Empty : result.url.Trim();
        SetVisible(true);
        SetText(titleText, string.IsNullOrWhiteSpace(result.title) ? "Untitled" : result.title);
        SetText(authorText, string.IsNullOrWhiteSpace(result.author) ? "Unknown" : result.author);
        SetText(sourceText, string.IsNullOrWhiteSpace(result.source) ? "Source: Unknown" : $"Source: {result.source}");
        SetText(docIdText, string.IsNullOrWhiteSpace(result.doc_id) ? "Doc ID: Unknown" : $"Doc ID: {result.doc_id}");
        SetText(similarityText, $"Score: {result.similarity:0.0000}");
        SetText(
            bodyText,
            "Document detail API is not connected yet. This panel is showing the selected search result."
        );
        SetText(radarHeadingText, "Selected Document Profile");
        SetUrl(currentUrl);
        SetSaveStatus("");
        bool canSave = !string.IsNullOrWhiteSpace(result.doc_id);
        SetSaveInteractable(canSave);
        parameterScoresPanelView?.ShowScores(result.parameters);
        radarChartView?.ShowScores(result.parameters);
        slideInEffect?.Play();
        LogSaveFlow($"ShowResult doc_id={result.doc_id} title={result.title} canSave={canSave} saveButton={(saveButton == null ? "null" : saveButton.name)}");
    }

    public void ShowPlaceholder(ThoughtMapSearchResult result)
    {
        ShowResult(result);
    }

    public void SetSaving()
    {
        SetSaveStatus("Saving...");
        SetSaveInteractable(false);
        LogSaveFlow($"SetSaving doc_id={CurrentDocIdForLog()}");
    }

    public void SetSaved(bool duplicate)
    {
        SetSaveStatus(duplicate ? "Already saved" : "Saved");
        SetSaveInteractable(false);
        LogSaveFlow($"SetSaved duplicate={duplicate} doc_id={CurrentDocIdForLog()}");
    }

    public void SetSaveError(string message)
    {
        SetSaveStatus(string.IsNullOrWhiteSpace(message) ? "Save failed" : $"Save failed: {message}");
        SetSaveInteractable(currentResult != null && !string.IsNullOrWhiteSpace(currentResult.doc_id));
        LogSaveFlow($"SetSaveError doc_id={CurrentDocIdForLog()} message={message}");
    }


    private void ConfigureActionButtonLabels()
    {
        SetButtonLabel(saveButton, "\u2606 Save to My Library");
        SetButtonLabel(openLinkButton, "Open Link");
        ConfigureButtonSize(saveButton, 190f, 40f);
        ConfigureButtonSize(openLinkButton, 132f, 36f);
        EnsureHoverGlow(saveButton);
        EnsureHoverGlow(openLinkButton);
    }

    private void EnsureHoverGlow(Button button)
    {
        if (button == null || button.GetComponent<NeonHoverGlow>() != null)
        {
            return;
        }

        button.gameObject.AddComponent<NeonHoverGlow>();
    }

    private void SetButtonLabel(Button button, string label)
    {
        if (button == null)
        {
            return;
        }

        TMP_Text text = button.GetComponentInChildren<TMP_Text>(true);
        if (text != null)
        {
            text.text = label;
        }
    }


    private void ConfigureButtonSize(Button button, float preferredWidth, float preferredHeight)
    {
        if (button == null)
        {
            return;
        }

        LayoutElement layout = button.GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = button.gameObject.AddComponent<LayoutElement>();
        }

        layout.minWidth = preferredWidth;
        layout.preferredWidth = preferredWidth;
        layout.minHeight = preferredHeight;
        layout.preferredHeight = preferredHeight;
    }

    private void HandleSaveClicked()
    {
        int subscriberCount = SaveRequested == null ? 0 : SaveRequested.GetInvocationList().Length;
        LogSaveFlow($"HandleSaveClicked currentResultNull={currentResult == null} doc_id={CurrentDocIdForLog()} subscribers={subscriberCount}");

        if (currentResult == null)
        {
            SetSaveError("No selected result on this DetailPanelView instance.");
            return;
        }

        if (subscriberCount == 0)
        {
            SetSaveError("Save event has no listener. Check ThoughtMapSearchManager Detail Panel View reference.");
            return;
        }

        SaveRequested?.Invoke(currentResult);
    }

    private void RegisterSaveButtonListener()
    {
        if (saveButton == null || saveButtonListenerRegistered)
        {
            LogSaveFlow($"RegisterSaveButtonListener skipped saveButtonNull={saveButton == null} alreadyRegistered={saveButtonListenerRegistered}");
            return;
        }

        saveButton.onClick.AddListener(HandleSaveClicked);
        saveButtonListenerRegistered = true;
        LogSaveFlow($"Registered SaveButton listener button={saveButton.name}");
    }

    private void UnregisterSaveButtonListener()
    {
        if (saveButton == null || !saveButtonListenerRegistered)
        {
            return;
        }

        saveButton.onClick.RemoveListener(HandleSaveClicked);
        saveButtonListenerRegistered = false;
        LogSaveFlow($"Unregistered SaveButton listener button={saveButton.name}");
    }


    private void HandleOpenLinkClicked()
    {
        if (string.IsNullOrWhiteSpace(currentUrl))
        {
            return;
        }

        Application.OpenURL(currentUrl);
    }

    private void SetUrl(string value)
    {
        currentUrl = string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim();
        SetText(urlText, string.IsNullOrWhiteSpace(currentUrl) ? string.Empty : "Source Link");

        if (urlText != null)
        {
            urlText.gameObject.SetActive(!string.IsNullOrWhiteSpace(currentUrl));
        }

        if (openLinkButton != null)
        {
            openLinkButton.gameObject.SetActive(!string.IsNullOrWhiteSpace(currentUrl));
            openLinkButton.interactable = !string.IsNullOrWhiteSpace(currentUrl);
        }
    }

    private void SetVisible(bool hasContent)
    {
        if (emptyStateRoot != null)
        {
            emptyStateRoot.SetActive(!hasContent);
        }

        if (contentRoot != null)
        {
            contentRoot.SetActive(hasContent);
        }
    }

    private void SetSaveInteractable(bool value)
    {
        if (saveButton != null)
        {
            saveButton.interactable = value;
        }
    }

    private void SetSaveStatus(string value)
    {
        SetText(saveStatusText, value);
    }

    private void SetText(TMP_Text target, string value)
    {
        if (target != null)
        {
            target.text = value;
        }
    }

    private string CurrentDocIdForLog()
    {
        return currentResult == null ? "null" : currentResult.doc_id;
    }

    private void LogSaveFlow(string message)
    {
        if (debugSaveFlow)
        {
            Debug.Log($"[ThoughtMap SaveFlow][DetailPanelView:{GetInstanceID()}] {message}", this);
        }
    }
}
