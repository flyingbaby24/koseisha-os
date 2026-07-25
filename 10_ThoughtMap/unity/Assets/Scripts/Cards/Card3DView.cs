using System.Collections;
using UnityEngine;

/// <summary>Reusable 3D representation of a card for Battle, Collection, Reward and gallery views.</summary>
public sealed class Card3DView : MonoBehaviour
{
    [Header("Parts")]
    [SerializeField] private Renderer artworkRenderer;
    [SerializeField] private Renderer[] glowRenderers;
    [Header("Idle Presentation")]
    [SerializeField] private float floatHeight = 0.025f;
    [SerializeField] private float floatSpeed = 1.15f;
    [SerializeField] private float swayAngle = 1.6f;
    [SerializeField] private float rotationSpeed = 2.5f;
    [SerializeField] private float hoverLift = 0.12f;
    [SerializeField] private float hoverScale = 1.08f;
    [Header("Surface Presentation")]
    [SerializeField] private Color playerColor = new Color(.08f, .58f, 1f, 1f);
    [SerializeField] private Color enemyColor = new Color(1f, .16f, .08f, 1f);
    [SerializeField] private float idleEmission = .35f;
    [SerializeField] private float activeEmission = 2.6f;
    [SerializeField] private float groundGlowRadius = .78f;
    [SerializeField] private float cardThickness = .14f;

    private MaterialPropertyBlock artworkBlock;
    private Material runtimeArtworkMaterial;
    private Material originalArtworkMaterial;
    private static Material sharedArtworkPresentationMaterial;
    private static Material sharedCardBodyMaterial;
    private static Material sharedCardRimMaterial;
    private Renderer artworkDisplayRenderer;
    private SpriteRenderer artworkSpriteRenderer;
    private SpriteRenderer artworkRearRenderer;
    private Renderer cardBodyRenderer;
    private Vector3 restingPosition;
    private Quaternion restingRotation;
    private Vector3 restingScale;
    private float phase;
    private bool hovered;
    private bool selected;
    private Vector3 actionOffset;
    private Vector3 shakeOffset;
    private bool enemySide;
    private bool dead;
    private bool targeted;
    private bool acting;
    private bool artworkDepthAdjusted;
    private Coroutine attackRoutine;
    private Coroutine hitRoutine;
    private int externalEffectDepth;
    private float sequenceCharge;
    private Color sequenceColor = Color.white;
    private LineRenderer targetRing;
    private Material targetRingMaterial;
    private LineRenderer groundGlow;
    private Renderer contactShadow;
    private static Material sharedShadowMaterial;
    private Material groundGlowMaterial;
    private Transform centeredVisualRoot;
    private Transform presentationAnchor;

    public Sprite Artwork { get; private set; }

    private void Awake()
    {
        ResolveParts();
        restingPosition = transform.localPosition;
        restingRotation = transform.localRotation;
        restingScale = transform.localScale;
        phase = Mathf.Abs(GetInstanceID() * 0.137f) % (Mathf.PI * 2f);
        ApplyGlow(false);
        EnsurePointerCollider();
    }

    public void SetCardSprite(Sprite sprite)
    {
        Artwork = sprite;
        ResolveParts();
        if (artworkRenderer == null || sprite == null) return;
        EnsureArtworkPresentationMaterial();
        EnsureArtworkDisplaySurface();
        if(artworkSpriteRenderer!=null)
        {
            ConfigureArtworkSprite(artworkSpriteRenderer,sprite,false);
            ConfigureArtworkSprite(artworkRearRenderer,sprite,true);
            return;
        }
        Renderer display = cardBodyRenderer != null ? cardBodyRenderer : (artworkDisplayRenderer == null ? artworkRenderer : artworkDisplayRenderer);
        if (artworkBlock == null) artworkBlock = new MaterialPropertyBlock();
        display.GetPropertyBlock(artworkBlock);
        artworkBlock.SetTexture("_BaseMap", sprite.texture);
        artworkBlock.SetTexture("_MainTex", sprite.texture);
        Rect rect = sprite.textureRect;
        Vector2 scale = new Vector2(rect.width / sprite.texture.width, rect.height / sprite.texture.height);
        Vector2 offset = new Vector2(rect.x / sprite.texture.width, rect.y / sprite.texture.height);
        artworkBlock.SetVector("_BaseMap_ST", new Vector4(scale.x, scale.y, offset.x, offset.y));
        artworkBlock.SetVector("_MainTex_ST", new Vector4(scale.x, scale.y, offset.x, offset.y));
        artworkBlock.SetColor("_BaseColor", Color.white);
        artworkBlock.SetColor("_Color", Color.white);
        artworkBlock.SetColor("_RendererColor", Color.white);
        artworkBlock.SetColor("_EmissionColor", Color.white * .08f);
        display.SetPropertyBlock(artworkBlock);
        if(runtimeArtworkMaterial!=null)Destroy(runtimeArtworkMaterial);
        runtimeArtworkMaterial=new Material(originalArtworkMaterial==null?sharedArtworkPresentationMaterial:originalArtworkMaterial){name="CardArtwork_Instance"};
        runtimeArtworkMaterial.SetTexture("_MainTex",sprite.texture);runtimeArtworkMaterial.SetTexture("_BaseMap",sprite.texture);
        runtimeArtworkMaterial.SetTextureScale("_MainTex",scale);runtimeArtworkMaterial.SetTextureOffset("_MainTex",offset);
        runtimeArtworkMaterial.SetTextureScale("_BaseMap",scale);runtimeArtworkMaterial.SetTextureOffset("_BaseMap",offset);
        runtimeArtworkMaterial.SetColor("_BaseColor",Color.white);runtimeArtworkMaterial.SetColor("_Color",Color.white);
        runtimeArtworkMaterial.EnableKeyword("_EMISSION");runtimeArtworkMaterial.SetColor("_EmissionColor",Color.white*.32f);
        display.sharedMaterial=runtimeArtworkMaterial;
    }

    private static void ConfigureArtworkSprite(SpriteRenderer target,Sprite sprite,bool rear)
    {
        if(target==null)return;target.sprite=sprite;target.color=Color.white;target.enabled=true;
        Vector2 size=sprite.bounds.size;target.transform.localScale=new Vector3(1.18f/Mathf.Max(.001f,size.x),1.66f/Mathf.Max(.001f,size.y),1f);
        target.transform.localPosition=new Vector3(0f,0f,rear?-.076f:.076f);
        target.transform.localRotation=Quaternion.Euler(0f,rear?180f:0f,0f);
    }

    private void EnsureArtworkDisplaySurface()
    {
        if (artworkDisplayRenderer != null) return;
        foreach (Renderer original in GetComponentsInChildren<Renderer>(true)) original.enabled = false;
        EnsureCardPresentationMaterials();
        GameObject body = GameObject.CreatePrimitive(PrimitiveType.Cube);
        body.name = "CardBody"; Destroy(body.GetComponent<Collider>()); body.transform.SetParent(transform,false);
        body.transform.localPosition = Vector3.zero; body.transform.localScale = new Vector3(1.32f,1.80f,.14f);
        cardBodyRenderer=body.GetComponent<Renderer>();cardBodyRenderer.sharedMaterial = sharedCardBodyMaterial;
        GameObject surface = new GameObject("ArtworkDisplay",typeof(SpriteRenderer));
        surface.name = "ArtworkDisplay";
        surface.transform.SetParent(transform, false);
        surface.transform.localPosition = new Vector3(0f, 0f, .076f);
        surface.transform.localRotation = Quaternion.identity;
        surface.transform.localScale = new Vector3(1.18f, 1.66f, 1f);
        artworkSpriteRenderer = surface.GetComponent<SpriteRenderer>();
        artworkDisplayRenderer = artworkSpriteRenderer;
        artworkDisplayRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        artworkDisplayRenderer.receiveShadows = false;
        artworkDisplayRenderer.sortingOrder = 20;
        GameObject rear=new GameObject("ArtworkRear",typeof(SpriteRenderer));rear.transform.SetParent(transform,false);
        artworkRearRenderer=rear.GetComponent<SpriteRenderer>();artworkRearRenderer.sortingOrder=20;
        artworkRearRenderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;artworkRearRenderer.receiveShadows=false;
        var rims = new System.Collections.Generic.List<Renderer>();
        rims.Add(CreateRim("RimTop",new Vector3(0f,.91f,.085f),new Vector3(1.38f,.035f,.035f)));
        rims.Add(CreateRim("RimBottom",new Vector3(0f,-.91f,.085f),new Vector3(1.38f,.035f,.035f)));
        rims.Add(CreateRim("RimLeft",new Vector3(-.67f,0f,.085f),new Vector3(.035f,1.82f,.035f)));
        rims.Add(CreateRim("RimRight",new Vector3(.67f,0f,.085f),new Vector3(.035f,1.82f,.035f)));
        glowRenderers = rims.ToArray();
        ApplyGlow(false);
    }

    private void EnsureCardPresentationMaterials()
    {
        Shader lit=Shader.Find("Universal Render Pipeline/Lit")??Shader.Find("Standard");
        if(sharedCardBodyMaterial==null){sharedCardBodyMaterial=new Material(lit){name="CardBody_Shared"};sharedCardBodyMaterial.SetColor("_BaseColor",new Color(.025f,.035f,.055f));sharedCardBodyMaterial.SetColor("_Color",new Color(.025f,.035f,.055f));sharedCardBodyMaterial.SetFloat("_Metallic",.48f);sharedCardBodyMaterial.SetFloat("_Smoothness",.66f);sharedCardBodyMaterial.enableInstancing=true;}
        if(sharedCardRimMaterial==null){sharedCardRimMaterial=new Material(lit){name="CardRim_Shared"};sharedCardRimMaterial.EnableKeyword("_EMISSION");sharedCardRimMaterial.SetColor("_BaseColor",Color.white);sharedCardRimMaterial.SetFloat("_Metallic",.35f);sharedCardRimMaterial.SetFloat("_Smoothness",.72f);sharedCardRimMaterial.enableInstancing=true;}
    }

    private Renderer CreateRim(string name,Vector3 position,Vector3 scale)
    {
        GameObject rim=GameObject.CreatePrimitive(PrimitiveType.Cube);rim.name=name;Destroy(rim.GetComponent<Collider>());rim.transform.SetParent(transform,false);rim.transform.localPosition=position;rim.transform.localScale=scale;Renderer renderer=rim.GetComponent<Renderer>();renderer.sharedMaterial=sharedCardRimMaterial;return renderer;
    }

    private void EnsureArtworkPresentationMaterial()
    {
        if (artworkRenderer == null) return;
        if (sharedArtworkPresentationMaterial == null)
        {
            Shader shader = Shader.Find("Sprites/Default") ?? Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Texture");
            sharedArtworkPresentationMaterial = new Material(shader) { name = "CardArtwork_Unlit_Shared" };
            sharedArtworkPresentationMaterial.SetColor("_BaseColor", Color.white);
            sharedArtworkPresentationMaterial.SetColor("_Color", Color.white);
            sharedArtworkPresentationMaterial.enableInstancing = true;
        }
        artworkRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        artworkRenderer.receiveShadows = false;
        if (!artworkDepthAdjusted)
        {
            artworkRenderer.transform.localPosition += Vector3.forward * .025f;
            artworkDepthAdjusted = true;
        }
    }

    public void ConfigureTeam(bool isEnemy)
    {
        enemySide = isEnemy;
        EnsureGroundGlow();
        ApplyGlow(false);
    }

    public void SetDead(bool value)
    {
        if(dead&&!value)return;
        dead = value;
        if (targetRing != null) targetRing.gameObject.SetActive(false);
        if (groundGlow != null) groundGlow.gameObject.SetActive(!value);
        foreach (Renderer target in GetComponentsInChildren<Renderer>(true))
        {
            var block = new MaterialPropertyBlock(); target.GetPropertyBlock(block);
            block.SetColor("_BaseColor", value ? new Color(.18f,.2f,.24f,1f) : Color.white);
            block.SetColor("_Color", value ? new Color(.18f,.2f,.24f,1f) : Color.white);
            block.SetColor("_EmissionColor", value ? Color.black : TeamColor * idleEmission);
            target.SetPropertyBlock(block);
        }
        Color defeated=new Color(.32f,.34f,.38f,.48f);
        if(artworkSpriteRenderer!=null)artworkSpriteRenderer.color=value?defeated:Color.white;
        if(artworkRearRenderer!=null)artworkRearRenderer.color=value?defeated:Color.white;
        if(contactShadow!=null)contactShadow.gameObject.SetActive(!value);
    }

    public void SetHovered(bool value) { EnsurePointerCollider(); hovered = value; ApplyGlow(hovered || selected); }
    public void SetSelected(bool value) { selected = value; ApplyGlow(hovered || selected); }
    public void SetTargeted(bool value)
    {
        if(dead&&value)return;
        targeted=value;
        EnsureTargetRing();
        if (targetRing != null) targetRing.gameObject.SetActive(value);
        ApplyGlow(value || hovered || selected || acting);
    }

    public void CapturePresentationPose()
    {
        restingPosition = transform.localPosition;
        restingRotation = transform.localRotation;
        restingScale = transform.localScale;
    }

    public void AlignVisualCenterToAnchor()
    {
        if(centeredVisualRoot!=null)return;
        GameObject wrapper=new GameObject("CenteredVisual");centeredVisualRoot=wrapper.transform;centeredVisualRoot.SetParent(transform,false);
        var children=new System.Collections.Generic.List<Transform>();foreach(Transform child in transform)if(child!=centeredVisualRoot)children.Add(child);
        foreach(Transform child in children)child.SetParent(centeredVisualRoot,true);
        Renderer[] renderers=centeredVisualRoot.GetComponentsInChildren<Renderer>(true);if(renderers.Length==0)return;
        Bounds bounds=renderers[0].bounds;for(int i=1;i<renderers.Length;i++)bounds.Encapsulate(renderers[i].bounds);
        centeredVisualRoot.position+=transform.position-bounds.center;
        BoxCollider pointer=GetComponent<BoxCollider>();if(pointer!=null)pointer.center=Vector3.zero;
    }

    public void SetPresentationAnchor(Transform anchor) { presentationAnchor=anchor; }

    public void ConfigureBattleMotion(float height, float speed, float yawSpeed, float hoverAmount)
    {
        floatHeight = Mathf.Max(0f, height);
        floatSpeed = Mathf.Max(0f, speed);
        rotationSpeed = yawSpeed;
        swayAngle = Mathf.Max(0f, hoverAmount);
    }

    public void PlayAttackMotion(Vector3 localOffset, float duration)
    {
        if (attackRoutine != null) StopCoroutine(attackRoutine);
        attackRoutine = StartCoroutine(AttackMotion(localOffset, duration));
    }

    public void PlayHitMotion(float strength, float duration = 0.22f)
    {
        if (hitRoutine != null) StopCoroutine(hitRoutine);
        hitRoutine = StartCoroutine(HitMotion(Mathf.Max(0f, strength), duration));
    }

    public void BeginSequencedAction()
    {
        if (dead) return;
        acting = true;
        sequenceCharge = 0f;
        ApplyGlow(true);
    }

    public void SetSequenceCharge(float value, Color color)
    {
        if (dead) return;
        sequenceCharge = Mathf.Clamp01(value);
        sequenceColor = color;
        actionOffset = new Vector3(0f, .055f, .11f) * Mathf.SmoothStep(0f, 1f, sequenceCharge);
        ApplyFlash(color, Mathf.Lerp(.5f, 3f, sequenceCharge));
    }

    public void EndSequencedAction()
    {
        sequenceCharge = 0f;
        acting = false;
        actionOffset = Vector3.zero;
        ApplyGlow(targeted || hovered || selected);
    }

    public void BeginExternalEffect() { if (!dead) externalEffectDepth++; }
    public void EndExternalEffect() { externalEffectDepth = Mathf.Max(0, externalEffectDepth - 1); if (!dead) ApplyGlow(targeted || hovered || selected || acting); }

    public void PlayEffectImpact(BattleEffectType type, Color color, bool critical)
    {
        if (dead) return;
        if (type is BattleEffectType.Attack or BattleEffectType.Debuff or BattleEffectType.Dot)
            PlayHitMotion(critical ? .14f : .085f, critical ? .24f : .18f);
        else
            StartCoroutine(EffectPulse(color, type == BattleEffectType.Heal ? .42f : .3f));
    }

    private IEnumerator EffectPulse(Color color, float duration)
    {
        for (float t = 0f; t < duration; t += Time.deltaTime)
        {
            float pulse = Mathf.Sin(Mathf.Clamp01(t / duration) * Mathf.PI);
            ApplyFlash(color, .45f + pulse * 2.2f);
            yield return null;
        }
        if (!dead) ApplyGlow(targeted || hovered || selected || acting);
    }

    private void Update()
    {
        float wave = Mathf.Sin(Time.unscaledTime * floatSpeed + phase);
        float lift = (hovered || selected) ? hoverLift : 0f;
        transform.localPosition = restingPosition + Vector3.up * (wave * floatHeight + lift) + actionOffset + shakeOffset;
        float idleWeight = acting || externalEffectDepth > 0 ? .18f : 1f;
        Quaternion idleRotation=Quaternion.Euler(wave * swayAngle * .10f * idleWeight, wave * swayAngle*.55f * idleWeight, wave * swayAngle * .18f * idleWeight);
        transform.localRotation = restingRotation * idleRotation * (dead?Quaternion.Euler(0f,0f,8f):Quaternion.identity);
        float stateScale = dead ? .88f : ((hovered || selected) ? hoverScale : 1f);
        transform.localScale = Vector3.Lerp(transform.localScale, restingScale * stateScale, Time.unscaledDeltaTime * (dead ? 3.5f : 10f));
    }

    private IEnumerator AttackMotion(Vector3 offset, float duration)
    {
        if(dead)yield break;acting=true;ApplyGlow(true);
        float half = Mathf.Max(.04f, duration * .5f);
        for (float t=0f;t<half;t+=Time.unscaledDeltaTime){actionOffset=Vector3.Lerp(Vector3.zero,offset,Mathf.SmoothStep(0f,1f,t/half));yield return null;}
        for (float t=0f;t<half;t+=Time.unscaledDeltaTime){actionOffset=Vector3.Lerp(offset,Vector3.zero,Mathf.SmoothStep(0f,1f,t/half));yield return null;}
        actionOffset=Vector3.zero;acting=false;ApplyGlow(targeted||hovered||selected);attackRoutine=null;
    }

    private IEnumerator HitMotion(float strength, float duration)
    {
        float elapsed=0f;
        while(elapsed<duration){elapsed+=Time.unscaledDeltaTime;float fade=1f-Mathf.Clamp01(elapsed/duration);shakeOffset=new Vector3(Mathf.Sin(elapsed*78f),Mathf.Sin(elapsed*57f)*.25f,-.42f)*strength*fade;ApplyFlash(Color.Lerp(new Color(1f,.08f,.04f),Color.white,fade),.5f+fade*4f);yield return null;}
        shakeOffset=Vector3.zero;ApplyGlow(targeted||hovered||selected||acting);hitRoutine=null;
    }

    private void ResolveParts()
    {
        Transform legacyShadow = FindDeep(transform, "Shadow");
        if (legacyShadow != null)
            foreach (Renderer shadowRenderer in legacyShadow.GetComponentsInChildren<Renderer>(true)) shadowRenderer.enabled = false;
        Transform backFace = FindDeep(transform, "BackFace");
        if (backFace != null)
            foreach (Renderer backRenderer in backFace.GetComponentsInChildren<Renderer>(true)) backRenderer.enabled = false;
        if (artworkRenderer == null)
        {
            foreach (Renderer target in GetComponentsInChildren<Renderer>(true))
                if (target.gameObject.name == "Artwork") { artworkRenderer = target; break; }
        }
        if (artworkRenderer != null && originalArtworkMaterial == null) originalArtworkMaterial = artworkRenderer.sharedMaterial;
        if (glowRenderers == null || glowRenderers.Length == 0)
        {
            Transform glow = FindDeep(transform, "Glow");
            glowRenderers = glow == null ? new Renderer[0] : glow.GetComponentsInChildren<Renderer>(true);
        }
    }

    private void EnsurePointerCollider()
    {
        if (GetComponent<Collider>() != null) return;
        BoxCollider pointer = gameObject.AddComponent<BoxCollider>();
        pointer.center = Vector3.zero;
        pointer.size = new Vector3(1.45f, 2.05f, 0.18f);
        pointer.isTrigger = true;
    }

    private void EnsureTargetRing()
    {
        if (targetRing != null) return;
        GameObject ringObject = new GameObject("TargetRing", typeof(LineRenderer));
        ringObject.transform.SetParent(presentationAnchor==null?transform:presentationAnchor, false);
        targetRing = ringObject.GetComponent<LineRenderer>();
        targetRing.useWorldSpace = false;
        targetRing.loop = true;
        targetRing.positionCount = 48;
        targetRing.startWidth = targetRing.endWidth = 0.022f;
        targetRing.numCornerVertices = 3;
        targetRing.numCapVertices = 3;
        Shader shader = Shader.Find("ThoughtMap/KnowledgeLine") ?? Shader.Find("Sprites/Default");
        targetRingMaterial = new Material(shader) { name = "CardTargetRing_Runtime" };
        Color targetColor = new Color(1f, .12f, .06f, 1f);
        targetRingMaterial.SetColor("_BaseColor", targetColor);
        targetRingMaterial.SetColor("_Color", targetColor);
        if (targetRingMaterial.HasProperty("_Glow")) targetRingMaterial.SetFloat("_Glow", 2.4f);
        if (targetRingMaterial.HasProperty("_FlowSpeed")) targetRingMaterial.SetFloat("_FlowSpeed", 1.2f);
        targetRing.sharedMaterial = targetRingMaterial;
        targetRing.startColor = targetRing.endColor = targetColor;
        for (int i=0;i<targetRing.positionCount;i++)
        {
            float angle=i/(float)targetRing.positionCount*Mathf.PI*2f;
            targetRing.SetPosition(i,new Vector3(Mathf.Cos(angle)*.9f,.025f,Mathf.Sin(angle)*.62f));
        }
        ringObject.SetActive(false);
    }

    private void OnMouseEnter() { SetHovered(true); }
    private void OnMouseExit() { SetHovered(false); }

    private void ApplyGlow(bool strong)
    {
        if (glowRenderers == null) return;
        foreach (Renderer target in glowRenderers)
        {
            if (target == null) continue;
            var block = new MaterialPropertyBlock(); target.GetPropertyBlock(block);
            block.SetColor("_BaseColor", Color.Lerp(Color.black, TeamColor, .42f));
            block.SetColor("_Color", Color.Lerp(Color.black, TeamColor, .42f));
            block.SetColor("_EmissionColor", TeamColor * (strong ? activeEmission : idleEmission));
            target.SetPropertyBlock(block);
        }
        if (groundGlow != null)
        {
            Color c=TeamColor; c.a=strong ? .62f : .07f;
            groundGlow.startColor=groundGlow.endColor=c;
            groundGlow.startWidth=groundGlow.endWidth=strong ? .028f : .009f;
        }
    }

    private Color TeamColor => enemySide ? enemyColor : playerColor;

    private void ApplyFlash(Color color,float emission)
    {
        foreach(Renderer target in glowRenderers)
        {
            var block=new MaterialPropertyBlock();target.GetPropertyBlock(block);
            block.SetColor("_EmissionColor",color*emission);target.SetPropertyBlock(block);
        }
    }

    private void EnsureGroundGlow()
    {
        if(groundGlow!=null)return;
        GameObject go=new GameObject("GroundGlow",typeof(LineRenderer));
        go.transform.SetParent(presentationAnchor==null?transform:presentationAnchor,false);
        groundGlow=go.GetComponent<LineRenderer>();groundGlow.useWorldSpace=false;groundGlow.loop=true;groundGlow.positionCount=48;
        groundGlow.numCornerVertices=3;groundGlow.numCapVertices=3;
        Shader shader=Shader.Find("ThoughtMap/KnowledgeLine")??Shader.Find("Sprites/Default");
        groundGlowMaterial=new Material(shader){name="CardGroundGlow_Runtime"};
        groundGlowMaterial.SetColor("_BaseColor",TeamColor);groundGlowMaterial.SetColor("_Color",TeamColor);
        if(groundGlowMaterial.HasProperty("_Glow"))groundGlowMaterial.SetFloat("_Glow",1.4f);
        groundGlow.sharedMaterial=groundGlowMaterial;
        for(int i=0;i<48;i++){float a=i/48f*Mathf.PI*2f;groundGlow.SetPosition(i,new Vector3(Mathf.Cos(a)*groundGlowRadius,.02f,Mathf.Sin(a)*groundGlowRadius*.72f));}
        EnsureContactShadow();
    }

    private void EnsureContactShadow()
    {
        if(contactShadow!=null)return;
        if(sharedShadowMaterial==null){Shader shader=Shader.Find("Sprites/Default")??Shader.Find("Universal Render Pipeline/Unlit");sharedShadowMaterial=new Material(shader){name="CardContactShadow_Shared"};sharedShadowMaterial.SetColor("_Color",new Color(0f,0f,0f,.16f));sharedShadowMaterial.SetTexture("_MainTex",Texture2D.whiteTexture);}
        GameObject shadow=GameObject.CreatePrimitive(PrimitiveType.Cylinder);shadow.name="ContactShadow";Destroy(shadow.GetComponent<Collider>());shadow.transform.SetParent(presentationAnchor==null?transform:presentationAnchor,false);shadow.transform.localPosition=new Vector3(0f,.012f,0f);shadow.transform.localScale=new Vector3(.72f,.004f,.48f);contactShadow=shadow.GetComponent<Renderer>();contactShadow.sharedMaterial=sharedShadowMaterial;contactShadow.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;contactShadow.receiveShadows=false;
    }

    private static Transform FindDeep(Transform root, string name)
    {
        foreach (Transform child in root)
        {
            if (child.name == name) return child;
            Transform nested = FindDeep(child, name); if (nested != null) return nested;
        }
        return null;
    }

    private void OnDestroy()
    {
        if (targetRingMaterial != null) Destroy(targetRingMaterial);
        if (groundGlowMaterial != null) Destroy(groundGlowMaterial);
        if (runtimeArtworkMaterial != null) Destroy(runtimeArtworkMaterial);
    }
}
