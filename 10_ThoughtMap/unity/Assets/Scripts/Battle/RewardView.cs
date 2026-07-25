using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public sealed class RewardView : MonoBehaviour
{
    public void Show(RewardData reward, PlayerProgressData currentProgress, TMP_FontAsset font, UnityAction claim)
    {
        RectTransform root = transform as RectTransform;
        root.anchorMin = Vector2.zero;
        root.anchorMax = Vector2.one;
        root.offsetMin = Vector2.zero;
        root.offsetMax = Vector2.zero;
        transform.SetAsLastSibling();

        Image dim = GetComponent<Image>() ?? gameObject.AddComponent<Image>();
        dim.color = new Color(0.005f, 0.015f, 0.03f, 0.94f);
        dim.raycastTarget = true;

        GameObject panel = CreateObject("RewardPanel", transform, typeof(Image), typeof(VerticalLayoutGroup));
        RectTransform panelRect = panel.GetComponent<RectTransform>();
        panelRect.anchorMin = panelRect.anchorMax = new Vector2(0.5f, 0.5f);
        panelRect.pivot = new Vector2(0.5f, 0.5f);
        panelRect.sizeDelta = new Vector2(820f, 700f);
        panel.GetComponent<Image>().color = new Color(0.02f, 0.09f, 0.14f, 0.99f);
        VerticalLayoutGroup layout = panel.GetComponent<VerticalLayoutGroup>();
        layout.padding = new RectOffset(50, 50, 38, 38);
        layout.spacing = 18f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandHeight = false;

        TMP_Text title = CreateText(panelRect, "Title", "Battle Rewards", 42, font, TextAlignmentOptions.Center);
        title.color = new Color(1f, 0.82f, 0.25f);
        SetHeight(title.gameObject, 62f);
        CreateRewardLine(panelRect, "Thought Fragment", $"+{reward.thoughtFragments}", new Color(0.4f, 0.95f, 1f), font);
        CreateRewardLine(panelRect, "Research Point", $"+{reward.researchPoints}", new Color(0.65f, 0.82f, 1f), font);
        CreateRewardLine(
            panelRect,
            "New Generated Skill",
            reward.hasGeneratedSkill ? reward.generatedSkillName : "No Drop",
            reward.hasGeneratedSkill ? new Color(1f, 0.62f, 0.2f) : new Color(0.55f, 0.6f, 0.65f),
            font);
        CreateRewardLine(
            panelRect,
            "Rare Card Drop",
            reward.hasRareCard ? reward.rareCardName : "No Drop",
            reward.hasRareCard ? new Color(1f, 0.35f, 0.75f) : new Color(0.55f, 0.6f, 0.65f),
            font);

        TMP_Text owned = CreateText(
            panelRect,
            "CurrentResources",
            $"Current Resources   Fragment {currentProgress.thoughtFragments}   RP {currentProgress.researchPoints}",
            20,
            font,
            TextAlignmentOptions.Center);
        owned.color = new Color(0.68f, 0.82f, 0.88f);
        SetHeight(owned.gameObject, 40f);

        GameObject spacer = CreateObject("Spacer", panelRect, typeof(LayoutElement));
        spacer.GetComponent<LayoutElement>().flexibleHeight = 1f;
        CreateButton(panelRect, "ClaimButton", "報酬を受け取り Battle Prepへ戻る", font, claim);
    }

    private void CreateRewardLine(Transform parent, string label, string value, Color color, TMP_FontAsset font)
    {
        GameObject row = CreateObject(label.Replace(" ", string.Empty), parent, typeof(HorizontalLayoutGroup), typeof(LayoutElement));
        HorizontalLayoutGroup layout = row.GetComponent<HorizontalLayoutGroup>();
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        SetHeight(row, 62f);
        TMP_Text labelText = CreateText(row.transform, "Label", label, 24, font, TextAlignmentOptions.Left);
        labelText.color = new Color(0.75f, 0.9f, 0.96f);
        TMP_Text valueText = CreateText(row.transform, "Value", value, 26, font, TextAlignmentOptions.Right);
        valueText.color = color;
    }

    private void CreateButton(Transform parent, string name, string label, TMP_FontAsset font, UnityAction callback)
    {
        GameObject target = CreateObject(name, parent, typeof(Image), typeof(Button), typeof(LayoutElement));
        SetHeight(target, 68f);
        Image image = target.GetComponent<Image>();
        image.color = new Color(0.06f, 0.42f, 0.58f, 1f);
        Button button = target.GetComponent<Button>();
        button.targetGraphic = image;
        button.onClick.AddListener(callback);
        TMP_Text text = CreateText(target.transform, "Label", label, 22, font, TextAlignmentOptions.Center);
        text.rectTransform.anchorMin = Vector2.zero;
        text.rectTransform.anchorMax = Vector2.one;
        text.rectTransform.offsetMin = Vector2.zero;
        text.rectTransform.offsetMax = Vector2.zero;
        text.raycastTarget = false;
    }

    private static TMP_Text CreateText(Transform parent, string name, string value, float size, TMP_FontAsset font, TextAlignmentOptions alignment)
    {
        GameObject target = CreateObject(name, parent, typeof(CanvasRenderer), typeof(TextMeshProUGUI), typeof(LayoutElement));
        TMP_Text text = target.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = size;
        text.font = font;
        text.alignment = alignment;
        text.color = Color.white;
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

    private static void SetHeight(GameObject target, float height)
    {
        LayoutElement element = target.GetComponent<LayoutElement>() ?? target.AddComponent<LayoutElement>();
        element.preferredHeight = height;
    }
}
