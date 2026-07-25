using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public enum BattleEffectType { Attack, Heal, Shield, Buff, Debuff, Dot, Defeat }

public sealed class BattleEffectContext
{
    public BattleEffectType effectType;
    public BattleUnitView sourceUnit;
    public BattleUnitView targetUnit;
    public Vector3 sourceWorldPosition;
    public Vector3 targetWorldPosition;
    public int amount;
    public float duration;
    public Color teamColor;
    public Color attributeColor;
    public bool isCritical;
    public bool isDefeat;
}

[Serializable]
public sealed class BattleEffectProfile
{
    [Min(.1f)] public float attackDuration = 2.9f;
    [Min(.1f)] public float supportDuration = 2.8f;
    [Min(.1f)] public float dotTickDuration = .45f;
    [Range(1, 8)] public int maxConcurrentEffects = 4;
}

public enum BattleEffectAudioEvent
{
    Charge, PathTravel, Contact, Orbit, AttackImpact, HealContact, HealCleanse,
    ShieldApply, BuffApply, DebuffApply, DotTick, Defeat
}

public enum BattleEffectCameraEvent { MinorShake, HeavyShake, MicroZoom, HitStop, DefeatSlowMotion }

public sealed class BattleEffectAudioRouter : MonoBehaviour
{
    [Serializable] private struct Slot { public BattleEffectAudioEvent id; public AudioClip clip; }
    [SerializeField] private Slot[] slots;
    private AudioSource source;

    public void Play(BattleEffectAudioEvent id)
    {
        if (source == null) source = GetComponent<AudioSource>() ?? gameObject.AddComponent<AudioSource>();
        if (slots == null) return;
        foreach (Slot slot in slots) if (slot.id == id && slot.clip != null) { source.PlayOneShot(slot.clip); return; }
    }
}

public sealed class BattleEffectCameraRouter : MonoBehaviour
{
    private Coroutine routine;
    private Vector3 restingLocalPosition;

    private void Awake() { restingLocalPosition = transform.localPosition; }

    public void Play(BattleEffectCameraEvent id)
    {
        float strength = id == BattleEffectCameraEvent.HeavyShake ? .055f : .025f;
        float duration = id == BattleEffectCameraEvent.HeavyShake ? .18f : .1f;
        if (id is BattleEffectCameraEvent.MinorShake or BattleEffectCameraEvent.HeavyShake)
        {
            if (routine != null) StopCoroutine(routine);
            routine = StartCoroutine(Shake(strength, duration));
        }
    }

    private IEnumerator Shake(float strength, float duration)
    {
        for (float t = 0f; t < duration; t += Time.deltaTime)
        {
            float fade = 1f - Mathf.Clamp01(t / duration);
            transform.localPosition = restingLocalPosition + UnityEngine.Random.insideUnitSphere * strength * fade;
            yield return null;
        }
        transform.localPosition = restingLocalPosition;
        routine = null;
    }
}

public sealed class BattleEffectPathView : MonoBehaviour
{
    private LineRenderer path;
    private LineRenderer orbit;
    private Renderer endpoint;
    private Material material;
    private readonly Vector3[] points = new Vector3[40];

    public void Ensure()
    {
        if (path != null) return;
        Shader shader = Shader.Find("ThoughtMap/KnowledgeLine") ?? Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Sprites/Default");
        material = new Material(shader) { name = "BattleEffectPath_Pooled" };
        material.enableInstancing = true;
        path = CreateLine("GrowingPath", false);
        orbit = CreateLine("TargetOrbit", true);
        GameObject core = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        core.name = "EndpointCore"; Destroy(core.GetComponent<Collider>()); core.transform.SetParent(transform, false);
        endpoint = core.GetComponent<Renderer>(); endpoint.sharedMaterial = material;
    }

    public void RenderPath(Vector3 from, Vector3 to, float progress, Color color, float width)
    {
        Ensure(); ApplyColor(color, 1.55f);
        Vector3 delta = to - from;
        Vector3 side = Vector3.Cross(delta.normalized, Vector3.up);
        if (side.sqrMagnitude < .01f) side = Vector3.right;
        Vector3 control = (from + to) * .5f + Vector3.up * Mathf.Clamp(delta.magnitude * .12f, .18f, .7f) + side.normalized * .12f;
        int count = Mathf.Clamp(Mathf.CeilToInt(points.Length * Mathf.Clamp01(progress)), 2, points.Length);
        path.positionCount = count;
        for (int i = 0; i < count; i++)
        {
            float t = i / (float)(points.Length - 1);
            points[i] = Quadratic(from, control, to, t);
            path.SetPosition(i, points[i]);
        }
        path.startWidth = path.endWidth = width;
        endpoint.transform.position = points[count - 1];
        endpoint.transform.localScale = Vector3.one * Mathf.Lerp(.035f, .15f, progress);
        endpoint.gameObject.SetActive(true);
    }

    public void RenderOrbit(Transform target, float progress, Color color, float radius)
    {
        Ensure(); orbit.gameObject.SetActive(true); ApplyColor(color, 2f);
        orbit.positionCount = 48; orbit.startWidth = orbit.endWidth = .018f;
        float turns = Mathf.Lerp(.5f, 2.75f, progress);
        for (int i = 0; i < orbit.positionCount; i++)
        {
            float t = i / (float)(orbit.positionCount - 1);
            float angle = t * Mathf.PI * 2f * turns + progress * Mathf.PI * 3f;
            Vector3 local = new Vector3(Mathf.Cos(angle) * radius, Mathf.Sin(angle * .5f) * .34f, Mathf.Sin(angle) * radius * .42f);
            orbit.SetPosition(i, target.TransformPoint(local));
        }
    }

    public void Fade(float alpha)
    {
        if (path == null) return;
        Color c = path.startColor; c.a = alpha;
        path.startColor = path.endColor = c; orbit.startColor = orbit.endColor = c;
        endpoint.transform.localScale *= Mathf.Clamp01(alpha + .02f);
    }

    public void ResetView()
    {
        Ensure(); path.positionCount = 0; orbit.positionCount = 0; orbit.gameObject.SetActive(false); endpoint.gameObject.SetActive(false);
    }

    private LineRenderer CreateLine(string lineName, bool loop)
    {
        GameObject go = new GameObject(lineName, typeof(LineRenderer)); go.transform.SetParent(transform, false);
        LineRenderer line = go.GetComponent<LineRenderer>(); line.sharedMaterial = material; line.useWorldSpace = true;
        line.loop = loop; line.numCapVertices = 3; line.numCornerVertices = 3; return line;
    }

    private void ApplyColor(Color color, float glow)
    {
        material.SetColor("_BaseColor", color); material.SetColor("_Color", color);
        if (material.HasProperty("_Glow")) material.SetFloat("_Glow", glow);
        if (material.HasProperty("_FlowSpeed")) material.SetFloat("_FlowSpeed", 2.4f);
        path.startColor = path.endColor = color; orbit.startColor = orbit.endColor = color;
    }

    private static Vector3 Quadratic(Vector3 a, Vector3 b, Vector3 c, float t)
    {
        float u = 1f - t; return u * u * a + 2f * u * t * b + t * t * c;
    }

    private void OnDestroy() { if (material != null) Destroy(material); }
}

public sealed class BattleEffectSequenceController : MonoBehaviour
{
    [SerializeField] private BattleEffectProfile profile = new BattleEffectProfile();
    private readonly Stack<BattleEffectPathView> pool = new Stack<BattleEffectPathView>();
    private readonly HashSet<BattleEffectPathView> active = new HashSet<BattleEffectPathView>();
    private BattleEffectAudioRouter audioRouter;
    private BattleEffectCameraRouter cameraRouter;
    private readonly List<BattleUnitView> debugUnits = new List<BattleUnitView>();

    public void Initialize(IReadOnlyDictionary<string, BattleUnitView> units = null)
    {
        audioRouter = GetComponent<BattleEffectAudioRouter>() ?? gameObject.AddComponent<BattleEffectAudioRouter>();
        Camera camera = Camera.main;
        if (camera != null) cameraRouter = camera.GetComponent<BattleEffectCameraRouter>() ?? camera.gameObject.AddComponent<BattleEffectCameraRouter>();
        debugUnits.Clear();
        if (units != null) foreach (BattleUnitView unit in units.Values) if (unit != null) debugUnits.Add(unit);
    }

    [ContextMenu("Debug Replay/Attack")] private void DebugAttack() => DebugPlay(BattleEffectType.Attack);
    [ContextMenu("Debug Replay/Heal")] private void DebugHeal() => DebugPlay(BattleEffectType.Heal);
    [ContextMenu("Debug Replay/Shield")] private void DebugShield() => DebugPlay(BattleEffectType.Shield);
    [ContextMenu("Debug Replay/Buff")] private void DebugBuff() => DebugPlay(BattleEffectType.Buff);
    [ContextMenu("Debug Replay/Debuff")] private void DebugDebuff() => DebugPlay(BattleEffectType.Debuff);
    [ContextMenu("Debug Replay/DOT Tick")] private void DebugDot() => DebugPlay(BattleEffectType.Dot);
    [ContextMenu("Debug Replay/Defeat")] private void DebugDefeat() => DebugPlay(BattleEffectType.Defeat);

    private void DebugPlay(BattleEffectType type)
    {
        if (!Application.isPlaying || debugUnits.Count < 2) { Debug.LogWarning("[BattleEffect] Debug Replay requires Play Mode and two BattleUnits.", this); return; }
        BattleUnitView source = debugUnits[0], target = debugUnits[1];
        StartCoroutine(Play(new BattleEffectContext
        {
            effectType = type, sourceUnit = source, targetUnit = target, amount = 48,
            teamColor = new Color(.08f, .58f, 1f), attributeColor = Color.clear,
            isCritical = type == BattleEffectType.Attack, isDefeat = type == BattleEffectType.Defeat
        }));
    }

    public IEnumerator Play(BattleEffectContext context)
    {
        if (context == null || context.targetUnit == null) yield break;
        if (active.Count >= profile.maxConcurrentEffects) yield return null;
        BattleEffectPathView view = Rent();
        float duration = ResolveDuration(context);
        Color color = ResolveColor(context);
        Transform from = context.sourceUnit == null ? context.targetUnit.EffectTarget : context.sourceUnit.AttackOrigin;
        Transform to = context.targetUnit.EffectTarget;
        context.sourceWorldPosition = from.position; context.targetWorldPosition = to.position; context.duration = duration;
        context.sourceUnit?.Card3D?.BeginSequencedAction();
        context.targetUnit.Card3D?.BeginExternalEffect();
        audioRouter.Play(context.effectType == BattleEffectType.Attack ? BattleEffectAudioEvent.Charge : AudioFor(context.effectType));

        if (context.effectType == BattleEffectType.Dot)
        {
            yield return PulseTarget(context, color, duration);
            Release(view); yield break;
        }

        float chargeEnd = duration * .12f, pathEnd = duration * .56f, orbitEnd = duration * .82f, impactEnd = duration * .91f;
        for (float t = 0f; t < duration; t += Time.deltaTime)
        {
            if (t < chargeEnd)
            {
                context.sourceUnit?.Card3D?.SetSequenceCharge(t / chargeEnd, color);
            }
            else if (t < pathEnd)
            {
                float p = Mathf.SmoothStep(0f, 1f, (t - chargeEnd) / (pathEnd - chargeEnd));
                view.RenderPath(from.position, to.position, p, color, Mathf.Lerp(.012f, .035f, Mathf.Clamp01(context.amount / 100f)));
            }
            else if (t < orbitEnd)
            {
                view.RenderPath(from.position, to.position, 1f, color, .022f);
                view.RenderOrbit(to, (t - pathEnd) / (orbitEnd - pathEnd), color, .48f);
            }
            else if (t < impactEnd)
            {
                context.targetUnit.Card3D?.PlayEffectImpact(context.effectType, color, context.isCritical);
            }
            else view.Fade(1f - (t - impactEnd) / (duration - impactEnd));
            yield return null;
        }
        audioRouter.Play(context.effectType == BattleEffectType.Attack ? BattleEffectAudioEvent.AttackImpact : AudioFor(context.effectType));
        cameraRouter?.Play(context.isDefeat ? BattleEffectCameraEvent.HeavyShake : BattleEffectCameraEvent.MinorShake);
        context.sourceUnit?.Card3D?.EndSequencedAction();
        context.targetUnit.Card3D?.EndExternalEffect();
        if (context.isDefeat) context.targetUnit.Card3D?.SetDead(true);
        Release(view);
    }

    public void StopAndRecycleAll()
    {
        StopAllCoroutines();
        foreach (BattleEffectPathView view in new List<BattleEffectPathView>(active)) Release(view);
    }

    private void OnDisable() { StopAndRecycleAll(); }

    private IEnumerator PulseTarget(BattleEffectContext context, Color color, float duration)
    {
        audioRouter.Play(BattleEffectAudioEvent.DotTick);
        context.targetUnit.Card3D?.PlayEffectImpact(BattleEffectType.Dot, color, false);
        yield return new WaitForSeconds(duration);
        context.targetUnit.Card3D?.EndExternalEffect();
    }

    private BattleEffectPathView Rent()
    {
        BattleEffectPathView view;
        if (pool.Count > 0) view = pool.Pop();
        else { GameObject go = new GameObject("BattleEffectPath_Pooled"); go.transform.SetParent(transform, false); view = go.AddComponent<BattleEffectPathView>(); }
        view.gameObject.SetActive(true); view.ResetView(); active.Add(view); return view;
    }

    private void Release(BattleEffectPathView view)
    {
        if (view == null || !active.Remove(view)) return;
        view.ResetView(); view.gameObject.SetActive(false); view.transform.SetParent(transform, false); pool.Push(view);
    }

    private float ResolveDuration(BattleEffectContext context)
    {
        if (context.effectType == BattleEffectType.Dot) return profile.dotTickDuration;
        return context.effectType == BattleEffectType.Attack ? profile.attackDuration : profile.supportDuration;
    }

    private static Color ResolveColor(BattleEffectContext context)
    {
        if (context.attributeColor.maxColorComponent > .01f) return context.attributeColor;
        return context.effectType switch
        {
            BattleEffectType.Heal => new Color(.16f, 1f, .55f),
            BattleEffectType.Shield => new Color(.45f, .86f, 1f),
            BattleEffectType.Buff => new Color(1f, .78f, .15f),
            BattleEffectType.Debuff or BattleEffectType.Dot => new Color(.72f, .12f, .88f),
            BattleEffectType.Defeat => new Color(.78f, .16f, .2f),
            _ => context.teamColor.maxColorComponent > .01f ? context.teamColor : new Color(1f, .18f, .08f),
        };
    }

    private static BattleEffectAudioEvent AudioFor(BattleEffectType type) => type switch
    {
        BattleEffectType.Heal => BattleEffectAudioEvent.HealContact,
        BattleEffectType.Shield => BattleEffectAudioEvent.ShieldApply,
        BattleEffectType.Buff => BattleEffectAudioEvent.BuffApply,
        BattleEffectType.Debuff => BattleEffectAudioEvent.DebuffApply,
        BattleEffectType.Dot => BattleEffectAudioEvent.DotTick,
        BattleEffectType.Defeat => BattleEffectAudioEvent.Defeat,
        _ => BattleEffectAudioEvent.Contact,
    };
}
