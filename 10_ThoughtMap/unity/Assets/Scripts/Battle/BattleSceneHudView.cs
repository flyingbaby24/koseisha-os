using System;
using System.Text;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public sealed class BattleSceneHudView : MonoBehaviour
{
    private TMP_FontAsset font;
    private TMP_Text turnText;
    private TMP_Text phaseText;
    private TMP_Text speedText;
    private TMP_Text playerDetail;
    private TMP_Text enemyDetail;
    private Image playerDetailImage;
    private Image enemyDetailImage;
    private TMP_Text logText;
    private ScrollRect logScroll;
    private BattleTargetLineGraphic targetLine;
    private readonly StringBuilder log = new StringBuilder();
    private float activeSpeed = 1f;
    private IBattleStatusReadModel statusSource;
    private readonly Dictionary<string, ThoughtMapBattleUnit> runtimeUnits = new Dictionary<string, ThoughtMapBattleUnit>();
    private string selectedPlayerId;
    private string selectedEnemyId;
    public RectTransform BattleField { get; private set; }

    public void Build(TMP_FontAsset sourceFont, Transform playerRoot, Transform enemyRoot)
    {
        font = sourceFont;
        RectTransform root = transform as RectTransform;
        root.anchorMin = Vector2.zero; root.anchorMax = Vector2.one; root.offsetMin = root.offsetMax = Vector2.zero;
        root.SetAsLastSibling();

        BattleField = Panel(root, "BattleField", new Vector2(0.16f, 0.12f), new Vector2(0.84f, 0.88f), new Color(0f, 0.001f, 0.003f, 0.025f));
        BattleField.GetComponent<Image>().enabled=false;
        BattleField.SetAsFirstSibling();
        StretchBoard(playerRoot, BattleField);
        StretchBoard(enemyRoot, BattleField);

        RectTransform left = Panel(root, "PlayerDetailPanel", new Vector2(.0125f, .1667f), new Vector2(.1517f, .8796f), new Color(0f, 0.002f, 0.006f, 0.94f));
        AddTitle(left, "PLAYER DETAIL", new Color(0.35f, 0.8f, 1f));
        playerDetailImage = AddDetailImage(left);
        playerDetail = AddBody(left);

        RectTransform right = Panel(root, "EnemyDetailPanel", new Vector2(.8483f, .1667f), new Vector2(.9875f, .8796f), new Color(0.007f, 0f, 0f, 0.94f));
        AddTitle(right, "ENEMY DETAIL", new Color(1f, 0.42f, 0.35f));
        enemyDetailImage = AddDetailImage(right);
        enemyDetail = AddBody(right);

        BuildLog(root);
        BuildHeader(root);
        BuildControls(root);
        BuildTargetLine(root);
        SetEmptyDetails();
    }

    public void SelectUnit(ProductBattleUnitCardView view)
    {
        if (view == null) return;
        TMP_Text target = view.EnemySide ? enemyDetail : playerDetail;
        target.text = FormatUnit(view);
        Image image = view.EnemySide ? enemyDetailImage : playerDetailImage;
        if (image != null) { image.sprite = view.CardSprite; image.enabled = view.CardSprite != null; }
    }

    public void UpdateUnit(ThoughtMapBattleUnit unit, ProductBattleUnitCardView view)
    {
        if (unit == null || view == null) return;
        view.SetRuntimeUnit(unit);
        SelectUnit(view);
    }

    public void SelectUnit(BattleUnitView view)
    {
        BattlePresentationUnitData data=view==null?null:view.PresentationData;if(data==null)return;
        if(data.EnemySide)selectedEnemyId=data.UnitId;else selectedPlayerId=data.UnitId;
        runtimeUnits.TryGetValue(data.UnitId,out ThoughtMapBattleUnit unit);
        TMP_Text target=data.EnemySide?enemyDetail:playerDetail;target.text=FormatUnit(data,unit);
        Image image=data.EnemySide?enemyDetailImage:playerDetailImage;if(image!=null){image.sprite=data.CardSprite;image.enabled=data.CardSprite!=null;}
    }

    public void UpdateUnit(ThoughtMapBattleUnit unit,BattleUnitView view)
    {
        if(view==null||unit==null)return;runtimeUnits[unit.battleId]=unit;view.PresentationData?.ApplyRuntime(unit);SelectUnit(view);
    }

    public void SetStatusSource(IBattleStatusReadModel source) { statusSource=source; }
    public void RefreshStatus(ThoughtMapBattleUnit unit,BattleUnitView view)
    {
        if(unit==null||view==null)return;
        runtimeUnits[unit.battleId]=unit;
        view.PresentationData?.ApplyRuntime(unit);
        bool selected=view.PresentationData!=null&&(view.PresentationData.EnemySide?selectedEnemyId==unit.battleId:selectedPlayerId==unit.battleId);
        if(selected)SelectUnit(view);
    }

    public void SetTurn(int turn) { if (turnText != null) turnText.text = $"TURN {turn}"; }
    public void SetPhase(string team)
    {
        if (phaseText == null) return;
        bool enemy = string.Equals(team, "Enemy", StringComparison.OrdinalIgnoreCase);
        phaseText.text = enemy ? "ENEMY PHASE" : "PLAYER PHASE";
        phaseText.color = enemy ? new Color(1f, 0.35f, 0.28f) : new Color(0.25f, 0.72f, 1f);
    }
    public void AppendLog(string value)
    {
        if (string.IsNullOrWhiteSpace(value)) return;
        log.AppendLine(value);
        if (logText != null) logText.text = log.ToString();
        if (logScroll != null) { Canvas.ForceUpdateCanvases(); logScroll.verticalNormalizedPosition = 0f; }
    }
    public void ShowTarget(ProductBattleUnitCardView attacker, ProductBattleUnitCardView target)
    {
        Color color = attacker != null && attacker.EnemySide ? new Color(1f, 0.12f, 0.08f, 0.9f) : new Color(0.1f, 0.58f, 1f, 0.9f);
        targetLine?.Show(attacker == null ? null : attacker.RectTransform, target == null ? null : target.RectTransform, color);
    }
    public void HideTarget() => targetLine?.Hide();

    private string FormatUnit(ProductBattleUnitCardView view)
    {
        StringBuilder b = new StringBuilder();
        b.AppendLine($"{view.UnitId}  {view.Card?.cardName}");
        b.AppendLine();
        b.AppendLine($"HP  {view.CurrentHp} / {view.MaxHp}");
        b.AppendLine($"SP  {view.CurrentSp}");
        b.AppendLine();
        b.AppendLine("FINAL PARAMETERS");
        b.AppendLine($"P.ATK  {view.PhysicalAttack}");
        b.AppendLine($"S.ATK  {view.SkillAttack}");
        b.AppendLine($"P.DEF  {view.PhysicalDefense}");
        b.AppendLine($"S.DEF  {view.SkillDefense}");
        b.AppendLine($"SPD    {view.Speed}");
        b.AppendLine();
        b.AppendLine("EQUIPPED SKILL");
        if (view.EquippedSkill == null) b.AppendLine("No Skill");
        else
        {
            b.AppendLine(view.EquippedSkill.DisplayName);
            b.AppendLine($"Trigger: {view.EquippedSkill.trigger}");
            b.AppendLine(GeneratedSkillLibrary.EffectSummary(view.EquippedSkill));
        }
        return b.ToString();
    }

    private string FormatUnit(BattlePresentationUnitData view,ThoughtMapBattleUnit unit)
    {
        StringBuilder b=new StringBuilder();b.AppendLine($"{view.UnitId}  {view.Card?.cardName}");b.AppendLine();
        if(unit!=null&&!unit.IsAlive){b.AppendLine("DEFEATED");return b.ToString();}
        b.AppendLine($"HP  {view.CurrentHp} / {view.MaxHp}");
        int shield=unit==null||statusSource==null?0:statusSource.GetShield(unit);if(shield>0)b.AppendLine($"Shield  {shield}");
        b.AppendLine($"SP  {view.CurrentSp}");b.AppendLine();b.AppendLine("FINAL PARAMETERS");
        b.AppendLine(EffectiveLine("P.ATK",view.PhysicalAttack,unit==null||statusSource==null?view.PhysicalAttack:statusSource.GetEffectiveAttack(unit,false)));
        b.AppendLine(EffectiveLine("S.ATK",view.SkillAttack,unit==null||statusSource==null?view.SkillAttack:statusSource.GetEffectiveAttack(unit,true)));
        b.AppendLine(EffectiveLine("P.DEF",view.PhysicalDefense,unit==null||statusSource==null?view.PhysicalDefense:statusSource.GetEffectiveDefense(unit,false)));
        b.AppendLine(EffectiveLine("S.DEF",view.SkillDefense,unit==null||statusSource==null?view.SkillDefense:statusSource.GetEffectiveDefense(unit,true)));
        b.AppendLine($"SPD    {view.Speed}");b.AppendLine();b.AppendLine("ACTIVE EFFECTS");b.AppendLine(BattleStatusPresenter.BuildDetail(unit,statusSource));b.AppendLine();b.AppendLine("EQUIPPED SKILL");if(view.EquippedSkill==null)b.AppendLine("No Skill");else{b.AppendLine(view.EquippedSkill.DisplayName);b.AppendLine($"Trigger: {view.EquippedSkill.trigger}");b.AppendLine(GeneratedSkillLibrary.EffectSummary(view.EquippedSkill));}return b.ToString();
    }

    private static string EffectiveLine(string label,int baseValue,int effective){int delta=effective-baseValue;return delta==0?$"{label}  {effective}":$"{label}  {effective} ({(delta>0?"+":"")}{delta})";}

    private void BuildHeader(RectTransform root)
    {
        RectTransform header = Panel(root, "BattleHeader", new Vector2(.35f, .8963f), new Vector2(.65f, .9778f), new Color(0f, 0.001f, 0.004f, 0.92f));
        turnText = Text(header, "TurnText", "TURN 1", 28, TextAlignmentOptions.Center, new Vector2(0f, 0.48f), Vector2.one);
        phaseText = Text(header, "PhaseText", "PLAYER PHASE", 18, TextAlignmentOptions.Center, Vector2.zero, new Vector2(1f, 0.52f));
    }
    private void BuildControls(RectTransform root)
    {
        RectTransform controls = Panel(root, "BattleControls", new Vector2(.69f, .9037f), new Vector2(.9875f, .9778f), new Color(0f, 0.001f, 0.004f, 0.92f));
        speedText = Text(controls, "SpeedText", "SPEED x1", 16, TextAlignmentOptions.Center, new Vector2(0f, 0f), new Vector2(0.23f, 1f));
        Button x1 = Button(controls, "Speed1", "x1", new Vector2(0.24f, 0.08f), new Vector2(0.40f, 0.92f)); x1.onClick.AddListener(() => SetSpeed(1f));
        Button x2 = Button(controls, "Speed2", "x2", new Vector2(0.41f, 0.08f), new Vector2(0.57f, 0.92f)); x2.onClick.AddListener(() => SetSpeed(2f));
        Button pause = Button(controls, "Pause", "Pause", new Vector2(0.58f, 0.08f), new Vector2(0.78f, 0.92f)); pause.onClick.AddListener(TogglePause);
        Button menu = Button(controls, "Menu", "Menu", new Vector2(0.79f, 0.08f), new Vector2(0.99f, 0.92f)); menu.onClick.AddListener(TogglePause);
    }
    private void BuildLog(RectTransform root)
    {
        RectTransform panel = Panel(root, "BattleLog", Vector2.zero, Vector2.zero, new Color(0f, 0.001f, 0.003f, 0.20f));
        panel.anchorMin=panel.anchorMax=Vector2.zero;panel.pivot=Vector2.zero;panel.anchoredPosition=new Vector2(24f,24f);panel.sizeDelta=new Vector2(614.4f,140f);
        AddTitle(panel, "BATTLE LOG", new Color(0.85f, 0.9f, 0.95f));
        GameObject scrollObject = New("Scroll", panel, typeof(ScrollRect)); RectTransform scrollRect = scrollObject.GetComponent<RectTransform>(); Stretch(scrollRect, new Vector2(0.03f, 0.05f), new Vector2(0.97f, 0.84f));
        GameObject viewportObject = New("Viewport", scrollRect, typeof(Image), typeof(Mask)); RectTransform viewport = viewportObject.GetComponent<RectTransform>(); Stretch(viewport, Vector2.zero, Vector2.one); viewportObject.GetComponent<Image>().color = new Color(0, 0, 0, 0.01f); viewportObject.GetComponent<Mask>().showMaskGraphic = false;
        GameObject contentObject = New("Content", viewport, typeof(VerticalLayoutGroup), typeof(ContentSizeFitter)); RectTransform content = contentObject.GetComponent<RectTransform>(); content.anchorMin = new Vector2(0, 1); content.anchorMax = new Vector2(1, 1); content.pivot = new Vector2(.5f, 1); content.sizeDelta = Vector2.zero; VerticalLayoutGroup layout = contentObject.GetComponent<VerticalLayoutGroup>(); layout.childControlWidth = true; layout.childControlHeight = true; layout.childForceExpandHeight = false; contentObject.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        logText = Text(content, "LogText", "", 13, TextAlignmentOptions.TopLeft, Vector2.zero, Vector2.one); logText.enableWordWrapping = true; logText.lineSpacing=-6f; LayoutElement le = logText.gameObject.AddComponent<LayoutElement>(); le.flexibleWidth = 1;
        logScroll = scrollObject.GetComponent<ScrollRect>(); logScroll.viewport = viewport; logScroll.content = content; logScroll.horizontal = false;
    }
    private void BuildTargetLine(RectTransform root)
    {
        GameObject go = New("TargetLine", root, typeof(BattleTargetLineGraphic)); RectTransform rect = go.GetComponent<RectTransform>(); Stretch(rect, Vector2.zero, Vector2.one); targetLine = go.GetComponent<BattleTargetLineGraphic>(); targetLine.raycastTarget = false; targetLine.Hide();
    }
    private void SetSpeed(float speed) { activeSpeed = speed; Time.timeScale = speed; speedText.text = $"SPEED x{speed:0}"; }
    private void TogglePause() { Time.timeScale = Time.timeScale <= 0f ? activeSpeed : 0f; speedText.text = Time.timeScale <= 0f ? "PAUSED" : $"SPEED x{activeSpeed:0}"; }
    private void SetEmptyDetails() { playerDetail.text = "Select a Player card"; enemyDetail.text = "Select an Enemy card"; }
    private void StretchBoard(Transform board, RectTransform parent) { if (board == null) return; board.SetParent(parent, false); RectTransform rect = board as RectTransform; if (rect != null) Stretch(rect, Vector2.zero, Vector2.one); Graphic graphic = board.GetComponent<Graphic>(); if (graphic != null) graphic.enabled = false; }
    private void AddTitle(RectTransform parent, string value, Color color) { TMP_Text t = Text(parent, "Title", value, 17, TextAlignmentOptions.Center, new Vector2(0, .86f), Vector2.one); t.color = color; }
    private Image AddDetailImage(RectTransform parent) { GameObject go = New("CardImage", parent, typeof(Image)); RectTransform rect = go.GetComponent<RectTransform>(); Stretch(rect, new Vector2(.14f, .56f), new Vector2(.86f, .84f)); Image image = go.GetComponent<Image>(); image.preserveAspect = true; image.raycastTarget = false; image.enabled = false; return image; }
    private TMP_Text AddBody(RectTransform parent) { TMP_Text t = Text(parent, "Detail", "", 14, TextAlignmentOptions.TopLeft, new Vector2(.06f, .035f), new Vector2(.94f, .54f)); t.enableWordWrapping = true; return t; }
    private RectTransform Panel(Transform parent, string name, Vector2 min, Vector2 max, Color color) { GameObject go = New(name, parent, typeof(Image),typeof(Outline)); RectTransform rect = go.GetComponent<RectTransform>(); Stretch(rect, min, max); go.GetComponent<Image>().color = color;Outline outline=go.GetComponent<Outline>();outline.effectColor=new Color(color.r<color.b?.05f:.45f,.32f,color.b>color.r?.75f:.12f,.62f);outline.effectDistance=new Vector2(1f,-1f);return rect; }
    private TMP_Text Text(Transform parent, string name, string value, float size, TextAlignmentOptions alignment, Vector2 min, Vector2 max) { GameObject go = New(name, parent, typeof(CanvasRenderer), typeof(TextMeshProUGUI)); RectTransform rect = go.GetComponent<RectTransform>(); Stretch(rect, min, max); TMP_Text t = go.GetComponent<TMP_Text>(); t.text = value; t.font = font; t.fontSize = size; t.color = Color.white; t.alignment = alignment; t.raycastTarget = false; return t; }
    private Button Button(Transform parent, string name, string label, Vector2 min, Vector2 max) { GameObject go = New(name, parent, typeof(Image), typeof(Button)); RectTransform rect = go.GetComponent<RectTransform>(); Stretch(rect, min, max); go.GetComponent<Image>().color = new Color(.12f, .09f, .05f, .95f); Text(go.transform, "Label", label, 14, TextAlignmentOptions.Center, Vector2.zero, Vector2.one); return go.GetComponent<Button>(); }
    private static GameObject New(string name, Transform parent, params Type[] types) { Type[] all = new Type[types.Length + 1]; all[0] = typeof(RectTransform); Array.Copy(types, 0, all, 1, types.Length); GameObject go = new GameObject(name, all); go.transform.SetParent(parent, false); return go; }
    private static void Stretch(RectTransform rect, Vector2 min, Vector2 max) { rect.anchorMin = min; rect.anchorMax = max; rect.offsetMin = rect.offsetMax = Vector2.zero; }
}
