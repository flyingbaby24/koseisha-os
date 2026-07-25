using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleResultPanelView : MonoBehaviour
{
    private RectTransform panelRoot;
    private TMP_FontAsset fontAsset;

    public string Show(
        BattleResultData data,
        TMP_FontAsset font,
        UnityAction returnToPrep,
        UnityAction retryBattle)
    {
        fontAsset = font;
        BuildResultUi(data, returnToPrep, retryBattle);
        string path = Path.Combine(Application.persistentDataPath, "battle_log.json");
        File.WriteAllText(path, JsonUtility.ToJson(data, true), new UTF8Encoding(false));
        Debug.Log($"[BattleResult] Saved BattleResultData JSON: {path}", this);
        return path;
    }

    private void BuildResultUi(BattleResultData data, UnityAction returnToPrep, UnityAction retryBattle)
    {
        RectTransform root = transform as RectTransform;
        root.anchorMin = Vector2.zero;
        root.anchorMax = Vector2.one;
        root.offsetMin = Vector2.zero;
        root.offsetMax = Vector2.zero;
        transform.SetAsLastSibling();

        Image dim = GetComponent<Image>() ?? gameObject.AddComponent<Image>();
        dim.color = new Color(0.01f, 0.02f, 0.04f, 0.9f);
        dim.raycastTarget = true;

        GameObject panel = CreateObject("ResultPanel", transform, typeof(Image), typeof(VerticalLayoutGroup));
        panelRoot = panel.GetComponent<RectTransform>();
        panelRoot.anchorMin = panelRoot.anchorMax = new Vector2(0.5f, 0.5f);
        panelRoot.pivot = new Vector2(0.5f, 0.5f);
        panelRoot.sizeDelta = new Vector2(1180f, 900f);
        panel.GetComponent<Image>().color = new Color(0.015f, 0.07f, 0.11f, 0.98f);
        VerticalLayoutGroup layout = panel.GetComponent<VerticalLayoutGroup>();
        layout.padding = new RectOffset(36, 36, 26, 26);
        layout.spacing = 9f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandHeight = false;

        TMP_Text title = CreateText(panelRoot, "OutcomeText", data != null && data.victory ? "Victory" : "Defeat", 44, TextAlignmentOptions.Center);
        title.color = data != null && data.victory ? new Color(1f, 0.84f, 0.25f) : new Color(1f, 0.34f, 0.28f);
        SetPreferredHeight(title.gameObject, 56f);
        TMP_Text turn = CreateText(panelRoot, "TurnText", $"Turn {(data == null ? 0 : data.turnCount)}", 24, TextAlignmentOptions.Center);
        SetPreferredHeight(turn.gameObject, 34f);

        UnitBattleResult mvp = data == null
            ? null
            : data.playerResults.Concat(data.enemyResults).FirstOrDefault(unit => unit.unitId == data.mvpUnitId);
        string mvpLabel = mvp == null
            ? "MVP\n-"
            : $"MVP  {mvp.cardName}   Damage {mvp.damageDealt}   Kills {mvp.kills}   Skills {mvp.skillCount}";
        TMP_Text mvpText = CreateText(panelRoot, "MvpText", mvpLabel, 25, TextAlignmentOptions.Center);
        mvpText.color = new Color(1f, 0.72f, 0.18f);
        SetPreferredHeight(mvpText.gameObject, 48f);

        GameObject scrollObject = CreateObject("ResultsScroll", panelRoot, typeof(Image), typeof(ScrollRect), typeof(LayoutElement));
        scrollObject.GetComponent<Image>().color = new Color(0f, 0.02f, 0.04f, 0.55f);
        LayoutElement scrollElement = scrollObject.GetComponent<LayoutElement>();
        scrollElement.preferredHeight = 560f;
        scrollElement.flexibleHeight = 1f;
        GameObject viewport = CreateObject("Viewport", scrollObject.transform, typeof(Image), typeof(Mask));
        RectTransform viewportRect = viewport.GetComponent<RectTransform>();
        viewportRect.anchorMin = Vector2.zero;
        viewportRect.anchorMax = Vector2.one;
        viewportRect.offsetMin = new Vector2(10f, 8f);
        viewportRect.offsetMax = new Vector2(-10f, -8f);
        viewport.GetComponent<Image>().color = new Color(0f, 0f, 0f, 0.01f);
        viewport.GetComponent<Mask>().showMaskGraphic = false;

        GameObject content = CreateObject("Content", viewport.transform, typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
        RectTransform contentRect = content.GetComponent<RectTransform>();
        contentRect.anchorMin = new Vector2(0f, 1f);
        contentRect.anchorMax = new Vector2(1f, 1f);
        contentRect.pivot = new Vector2(0.5f, 1f);
        contentRect.anchoredPosition = Vector2.zero;
        contentRect.sizeDelta = Vector2.zero;
        VerticalLayoutGroup contentLayout = content.GetComponent<VerticalLayoutGroup>();
        contentLayout.spacing = 4f;
        contentLayout.childControlWidth = true;
        contentLayout.childControlHeight = true;
        contentLayout.childForceExpandHeight = false;
        content.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        ScrollRect scroll = scrollObject.GetComponent<ScrollRect>();
        scroll.viewport = viewportRect;
        scroll.content = contentRect;
        scroll.horizontal = false;
        scroll.vertical = true;

        CreateResultSection(contentRect, "Player Results", data == null ? null : data.playerResults, new Color(0.55f, 0.9f, 1f));
        CreateResultSection(contentRect, "Enemy Results", data == null ? null : data.enemyResults, new Color(1f, 0.62f, 0.58f));

        GameObject buttons = CreateObject("Buttons", panelRoot, typeof(HorizontalLayoutGroup), typeof(LayoutElement));
        HorizontalLayoutGroup buttonLayout = buttons.GetComponent<HorizontalLayoutGroup>();
        buttonLayout.spacing = 24f;
        buttonLayout.childAlignment = TextAnchor.MiddleCenter;
        buttonLayout.childControlWidth = false;
        buttonLayout.childControlHeight = false;
        SetPreferredHeight(buttons, 64f);
        CreateButton(buttons.transform, "OpenRewardsButton", "報酬を確認", returnToPrep);
        CreateButton(buttons.transform, "RetryBattleButton", "Retry Battle", retryBattle);
    }

    private void CreateResultSection(Transform parent, string title, List<UnitBattleResult> units, Color color)
    {
        TMP_Text section = CreateText(parent, title.Replace(" ", "") + "Title", title, 24, TextAlignmentOptions.Left);
        section.color = color;
        SetPreferredHeight(section.gameObject, 34f);
        TMP_Text header = CreateText(parent, "Header", "Card                         Damage    Taken    Kills    Skills    Alive", 18, TextAlignmentOptions.Left);
        header.color = new Color(0.62f, 0.78f, 0.86f);
        SetPreferredHeight(header.gameObject, 28f);
        foreach (UnitBattleResult unit in units ?? new List<UnitBattleResult>())
        {
            TMP_Text row = CreateText(
                parent,
                "Result_" + unit.unitId,
                $"{Trim(unit.cardName, 27),-29} {unit.damageDealt,7}  {unit.damageTaken,7}  {unit.kills,7}  {unit.skillCount,8}    {(unit.survived ? "Yes" : "No")}",
                18,
                TextAlignmentOptions.Left);
            row.color = color;
            SetPreferredHeight(row.gameObject, 27f);
        }
    }









    private Button CreateButton(Transform parent, string name, string label, UnityAction callback)
    {
        GameObject buttonObject = CreateObject(name, parent, typeof(Image), typeof(Button), typeof(LayoutElement));
        RectTransform rect = buttonObject.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(300f, 58f);
        LayoutElement element = buttonObject.GetComponent<LayoutElement>();
        element.preferredWidth = 300f;
        element.preferredHeight = 58f;
        Image image = buttonObject.GetComponent<Image>();
        image.color = new Color(0.04f, 0.35f, 0.5f, 0.98f);
        Button button = buttonObject.GetComponent<Button>();
        button.targetGraphic = image;
        if (callback != null)
        {
            button.onClick.AddListener(callback);
        }
        TMP_Text text = CreateText(rect, "Label", label, 22, TextAlignmentOptions.Center);
        text.rectTransform.anchorMin = Vector2.zero;
        text.rectTransform.anchorMax = Vector2.one;
        text.rectTransform.offsetMin = Vector2.zero;
        text.rectTransform.offsetMax = Vector2.zero;
        text.raycastTarget = false;
        return button;
    }

    private TMP_Text CreateText(Transform parent, string name, string value, float size, TextAlignmentOptions alignment)
    {
        GameObject textObject = CreateObject(name, parent, typeof(CanvasRenderer), typeof(TextMeshProUGUI), typeof(LayoutElement));
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = size;
        text.font = fontAsset;
        text.color = Color.white;
        text.alignment = alignment;
        text.enableWordWrapping = false;
        text.overflowMode = TextOverflowModes.Ellipsis;
        text.raycastTarget = false;
        return text;
    }

    private static GameObject CreateObject(string name, Transform parent, params Type[] components)
    {
        List<Type> types = new List<Type> { typeof(RectTransform) };
        types.AddRange(components);
        GameObject target = new GameObject(name, types.ToArray());
        target.transform.SetParent(parent, false);
        return target;
    }

    private static void SetPreferredHeight(GameObject target, float height)
    {
        LayoutElement element = target.GetComponent<LayoutElement>() ?? target.AddComponent<LayoutElement>();
        element.preferredHeight = height;
    }

    private static string Trim(string value, int maxLength)
    {
        if (string.IsNullOrEmpty(value) || value.Length <= maxLength)
        {
            return value ?? string.Empty;
        }
        return value.Substring(0, maxLength - 3) + "...";
    }
}
