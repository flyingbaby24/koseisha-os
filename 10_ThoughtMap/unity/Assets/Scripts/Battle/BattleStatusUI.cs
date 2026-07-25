using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public interface IBattleStatusReadModel
{
    IReadOnlyList<ActiveStatusEffect> GetActiveEffects(string unitId);
    int GetShield(ThoughtMapBattleUnit unit);
    int GetEffectiveAttack(ThoughtMapBattleUnit unit, bool magic);
    int GetEffectiveDefense(ThoughtMapBattleUnit unit, bool magic);
    float GetTauntMultiplier(ThoughtMapBattleUnit unit);
}

public sealed class BattleStatusDisplayModel
{
    public BattleSkillEffectType EffectType { get; set; }
    public string ShortText { get; set; }
    public string DetailText { get; set; }
    public Color Color { get; set; }
    public int Priority { get; set; }
}

public static class BattleStatusPresenter
{
    public const int MaxVisible = 4;

    public static List<BattleStatusDisplayModel> Build(ThoughtMapBattleUnit unit, IBattleStatusReadModel source)
    {
        if (unit == null || source == null || !unit.IsAlive) return new List<BattleStatusDisplayModel>();
        IReadOnlyList<ActiveStatusEffect> effects = source.GetActiveEffects(unit.battleId);
        return effects
            .GroupBy(effect => effect.effectType)
            .Select(group => Create(unit, source, group.Key, group.ToList()))
            .Where(model => model != null)
            .OrderBy(model => model.Priority)
            .ToList();
    }

    public static string BuildDetail(ThoughtMapBattleUnit unit, IBattleStatusReadModel source)
    {
        if (unit == null || source == null) return "No Active Effects";
        if (!unit.IsAlive) return "DEFEATED";
        List<BattleStatusDisplayModel> models = Build(unit, source);
        if (models.Count == 0) return "No Active Effects";
        StringBuilder builder = new StringBuilder();
        foreach (BattleStatusDisplayModel model in models) builder.AppendLine(model.DetailText);
        return builder.ToString().TrimEnd();
    }

    private static BattleStatusDisplayModel Create(ThoughtMapBattleUnit unit, IBattleStatusReadModel source, BattleSkillEffectType type, List<ActiveStatusEffect> effects)
    {
        int turns = effects.Max(effect => effect.remainingTurns);
        int stacks = effects.Sum(effect => effect.stackCount);
        int value = Mathf.RoundToInt(effects.Sum(effect => effect.value * effect.stackCount));
        return type switch
        {
            BattleSkillEffectType.Stun => Model(type, "STUN", "Stun / next action", new Color(.72f, .45f, 1f), 0),
            BattleSkillEffectType.Taunt => Model(type, $"T {turns}", $"Taunt x{source.GetTauntMultiplier(unit):0.0} / {Turns(turns)}", new Color(1f, .52f, .18f), 1),
            BattleSkillEffectType.Shield => Model(type, $"S {source.GetShield(unit)}", $"Shield {source.GetShield(unit)} / {Turns(turns)}", new Color(.55f, .88f, 1f), 2),
            BattleSkillEffectType.DamageOverTime => Model(type, $"DOT {turns}", $"DOT {value} / {turns} ticks", new Color(.85f, .25f, .55f), 3),
            BattleSkillEffectType.DefenseDebuff => Model(type, $"DEF↓ {turns}", $"{StatLabel(effects[0].parameter, false)} -{value} / {Turns(turns)}{StackSuffix(stacks)}", new Color(1f, .38f, .18f), 4),
            BattleSkillEffectType.AttackBuff => Model(type, $"ATK↑ {turns}", $"{StatLabel(effects[0].parameter, true)} +{value} / {Turns(turns)}{StackSuffix(stacks)}", new Color(1f, .82f, .2f), 5),
            _ => null,
        };
    }

    private static BattleStatusDisplayModel Model(BattleSkillEffectType type, string shortText, string detail, Color color, int priority) => new BattleStatusDisplayModel { EffectType = type, ShortText = shortText, DetailText = detail, Color = color, Priority = priority };
    private static string Turns(int value) => value == 1 ? "1 turn" : $"{value} turns";
    private static string StackSuffix(int stacks) => stacks > 1 ? $" / x{stacks}" : string.Empty;
    private static string StatLabel(string parameter, bool attack)
    {
        if (parameter == "physical_attack") return "P.ATK";
        if (parameter == "skill_attack") return "S.ATK";
        if (parameter == "physical_defense") return "P.DEF";
        if (parameter == "skill_defense") return "S.DEF";
        return attack ? "ATK" : "DEF";
    }
}

public sealed class BattleStatusIconView : MonoBehaviour
{
    private TMP_Text label;
    public void Initialize(TMP_FontAsset font)
    {
        label = GetComponent<TMP_Text>() ?? gameObject.AddComponent<TextMeshProUGUI>();
        label.font = ThoughtMapTmpFontResolver.Resolve(font);
        label.fontSize = 20f;
        label.fontStyle = FontStyles.Bold;
        label.alignment = TextAlignmentOptions.Center;
        label.raycastTarget = false;
        label.enableWordWrapping = false;
        label.outlineWidth = .16f;
        label.outlineColor = new Color(0f, 0f, 0f, .9f);
        RectTransform rect = label.rectTransform;
        rect.sizeDelta = new Vector2(108f, 23f);
    }
    public void Show(string text, Color color) { label.text = text; label.color = color; gameObject.SetActive(true); }
    public void Hide() { gameObject.SetActive(false); }
}

public sealed class BattleUnitStatusView : MonoBehaviour
{
    private readonly List<BattleStatusIconView> rows = new List<BattleStatusIconView>();
    private Canvas canvas;

    public void Initialize(TMP_FontAsset font)
    {
        if (canvas != null) return;
        GameObject canvasObject = new GameObject("StatusCanvas", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));
        canvasObject.transform.SetParent(transform, false);
        canvas = canvasObject.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.WorldSpace;
        canvas.sortingOrder = 40;
        RectTransform rect = canvasObject.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(230f, 110f);
        rect.localScale = Vector3.one * .0085f;
        rect.localPosition = Vector3.zero;
        for (int index = 0; index < BattleStatusPresenter.MaxVisible + 1; index++)
        {
            GameObject rowObject = new GameObject("StatusRow" + index, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI), typeof(BattleStatusIconView));
            rowObject.transform.SetParent(rect, false);
            RectTransform rowRect = rowObject.GetComponent<RectTransform>();
            rowRect.anchorMin = rowRect.anchorMax = new Vector2(1f, 1f);
            rowRect.pivot = new Vector2(1f, 1f);
            rowRect.anchoredPosition = new Vector2(0f, -index * 22f);
            BattleStatusIconView row = rowObject.GetComponent<BattleStatusIconView>();
            row.Initialize(font);
            row.Hide();
            rows.Add(row);
        }
    }

    public void Refresh(IReadOnlyList<BattleStatusDisplayModel> models, bool defeated)
    {
        int count = defeated || models == null ? 0 : Mathf.Min(BattleStatusPresenter.MaxVisible, models.Count);
        for (int index = 0; index < BattleStatusPresenter.MaxVisible; index++)
        {
            if (index < count) rows[index].Show(models[index].ShortText, models[index].Color);
            else rows[index].Hide();
        }
        int overflow = defeated || models == null ? 0 : models.Count - BattleStatusPresenter.MaxVisible;
        if (overflow > 0) rows[BattleStatusPresenter.MaxVisible].Show($"+{overflow}", Color.white);
        else rows[BattleStatusPresenter.MaxVisible].Hide();
    }

    private void LateUpdate()
    {
        Camera camera = Camera.main;
        if (canvas != null && camera != null) canvas.transform.rotation = camera.transform.rotation;
    }
}
