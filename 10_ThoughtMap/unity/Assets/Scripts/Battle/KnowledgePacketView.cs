using System;
using System.Collections.Generic;
using UnityEngine;

public enum KnowledgeIntent { EnemyAttack, Support, Resonance, Debuff, SelfEnhance }
public enum ThoughtPacketPattern { Philosophy, Psychology, Science, Economics, Karma, Emotion, Moral, Ideology, Individual, Community, Generic }

/// <summary>One pooled, parameter-driven optical data transfer shared by all knowledge effects.</summary>
public sealed class KnowledgePacketView : MonoBehaviour
{
    private sealed class Ripple
    {
        public LineRenderer line;
        public float delay;
    }

    private Transform source;
    private Transform target;
    private KnowledgeIntent intent;
    private ThoughtPacketPattern pattern;
    private LineRenderer core;
    private LineRenderer spiralA;
    private LineRenderer spiralB;
    private readonly List<Transform> packets = new List<Transform>();
    private readonly List<Ripple> ripples = new List<Ripple>();
    private Material lineMaterial;
    private Material packetMaterial;
    private Light packetLight;
    private float width;
    private float radius;
    private float speed;
    private float elapsed;
    private float duration;
    private float power01;
    private bool critical;
    private bool persistent;
    private bool impactCreated;
    private float resonanceBoost;
    private Color color;
    private Action<KnowledgePacketView> release;

    public Transform Source => source;
    public Transform Target => target;
    public bool Persistent => persistent;

    public void Configure(Transform from, Transform to, KnowledgeIntent packetIntent, ThoughtPacketPattern thoughtPattern, int power, bool isCritical, float travelDuration, bool keepAlive=false, Action<KnowledgePacketView> releaseAction=null)
    {
        CleanupVisuals();
        source=from; target=to; intent=packetIntent; pattern=thoughtPattern; critical=isCritical; persistent=keepAlive; release=releaseAction;
        elapsed=0f; impactCreated=false; resonanceBoost=0f; power01=Mathf.InverseLerp(1f,120f,power);
        duration=Mathf.Max(.18f,travelDuration*(.88f-power01*.18f)); speed=1f/duration;
        color=IntentColor(intent);
        width=Mathf.Clamp((.012f+power*.00052f)*.64f,.012f,.065f);
        radius=Mathf.Clamp(.045f+power*.00085f,.055f,.18f);
        BuildRenderers(power);
        UpdateGeometry();
        gameObject.SetActive(true);
    }

    public void PulseResonance() { if(persistent) resonanceBoost=1f; }

    private void BuildRenderers(int power)
    {
        Shader lineShader=Shader.Find("ThoughtMap/KnowledgeLine")??Shader.Find("Universal Render Pipeline/Unlit")??Shader.Find("Sprites/Default");
        lineMaterial=new Material(lineShader){name="KnowledgeLine_Runtime"};
        lineMaterial.SetColor("_BaseColor",color); lineMaterial.SetColor("_Color",color);
        if(lineMaterial.HasProperty("_Glow")) lineMaterial.SetFloat("_Glow",persistent?1.15f:1.45f);
        if(lineMaterial.HasProperty("_FlowSpeed")) lineMaterial.SetFloat("_FlowSpeed",persistent?.35f:2.4f+power01*2f);
        packetMaterial=new Material(Shader.Find("Universal Render Pipeline/Unlit")??Shader.Find("Sprites/Default")){name="KnowledgePacket_Runtime"};
        Color packetColor=color*(3.6f+power01*2.4f); packetMaterial.SetColor("_BaseColor",packetColor); packetMaterial.SetColor("_Color",packetColor);
        core=Line("Core",width,color); spiralA=Line("SpiralA",width*.34f,color*.8f); spiralB=Line("SpiralB",width*.22f,color*.62f);
        int packetCount=persistent?0:Mathf.Clamp(2+Mathf.RoundToInt(power01*7f),2,9);
        for(int i=0;i<packetCount;i++)
        {
            GameObject packet=GameObject.CreatePrimitive(PrimitiveType.Sphere); packet.name="DataPacket"; Destroy(packet.GetComponent<Collider>()); packet.transform.SetParent(transform,false);
            packet.transform.localScale=Vector3.one*Mathf.Lerp(.075f,.18f,power01); packet.GetComponent<Renderer>().sharedMaterial=packetMaterial;
            TrailRenderer trail=packet.AddComponent<TrailRenderer>(); trail.sharedMaterial=lineMaterial; trail.time=.12f+power01*.12f; trail.startWidth=width*2.2f; trail.endWidth=0f; trail.startColor=color; trail.endColor=new Color(color.r,color.g,color.b,0f); trail.minVertexDistance=.03f;
            packets.Add(packet.transform);
        }
        if(packetCount>0)
        {
            GameObject lightObject=new GameObject("PacketGlow"); lightObject.transform.SetParent(transform,false); packetLight=lightObject.AddComponent<Light>(); packetLight.type=LightType.Point; packetLight.color=color; packetLight.range=Mathf.Lerp(.55f,1.15f,power01); packetLight.intensity=Mathf.Lerp(.45f,1.2f,power01);
        }
    }

    private LineRenderer Line(string name,float lineWidth,Color lineColor)
    {
        GameObject go=new GameObject(name,typeof(LineRenderer)); go.transform.SetParent(transform,false); LineRenderer line=go.GetComponent<LineRenderer>();
        line.sharedMaterial=lineMaterial; line.useWorldSpace=true; line.textureMode=LineTextureMode.Tile; line.startWidth=line.endWidth=lineWidth; line.startColor=line.endColor=lineColor; line.numCapVertices=3; line.numCornerVertices=3; return line;
    }

    private void Update()
    {
        if(source==null||target==null){Release();return;}
        elapsed+=Time.unscaledDeltaTime; resonanceBoost=Mathf.MoveTowards(resonanceBoost,0f,Time.unscaledDeltaTime*2.6f); UpdateGeometry();
        if(persistent)return;
        float normalized=MotionProgress(elapsed*speed);
        for(int i=0;i<packets.Count;i++){float t=Mathf.Repeat(normalized-i/(float)Mathf.Max(1,packets.Count),1f);packets[i].position=SpiralPoint(t,i*.9f,true);}
        if(packetLight!=null&&packets.Count>0)packetLight.transform.position=packets[0].position;
        if(elapsed>=duration&&!impactCreated){impactCreated=true;CreateImpact();}
        UpdateRipples(); if(elapsed>duration+1.35f)Release();
    }

    private float MotionProgress(float t)
    {
        t=Mathf.Clamp01(t);
        if(pattern==ThoughtPacketPattern.Economics)return t*t;
        if(pattern==ThoughtPacketPattern.Karma)return Mathf.SmoothStep(0f,1f,t);
        if(pattern==ThoughtPacketPattern.Ideology)return Mathf.Pow(t,.82f);
        return t;
    }

    private void UpdateGeometry()
    {
        Vector3 a=source.position,b=target.position; core.positionCount=2;core.SetPosition(0,a);core.SetPosition(1,b);
        int points=54;spiralA.positionCount=points;spiralB.positionCount=points;
        for(int i=0;i<points;i++){float t=i/(float)(points-1);spiralA.SetPosition(i,SpiralPoint(t,0,false));spiralB.SetPosition(i,SpiralPoint(t,Mathf.PI,false));}
        float pulse=persistent?.68f+Mathf.Sin(Time.unscaledTime*1.8f)*.12f+resonanceBoost*.85f:1f;
        core.startWidth=core.endWidth=width*pulse; if(lineMaterial!=null&&lineMaterial.HasProperty("_Glow"))lineMaterial.SetFloat("_Glow",(persistent?1.05f:1.45f)+resonanceBoost*3f);
    }

    private Vector3 SpiralPoint(float t,float phase,bool packetMotion)
    {
        Vector3 a=source.position,b=target.position,axis=(b-a).normalized; Vector3 side=Vector3.Cross(axis,Vector3.up);if(side.sqrMagnitude<.01f)side=Vector3.Cross(axis,Vector3.right);side.Normalize();Vector3 up=Vector3.Cross(side,axis).normalized;
        float turns=3.5f+PatternFrequency(pattern); float angularSpeed=pattern==ThoughtPacketPattern.Karma?.35f:pattern==ThoughtPacketPattern.Ideology?1.35f:1f;
        float angle=t*turns*Mathf.PI*2f+phase+Time.unscaledTime*(persistent?.55f:2.8f)*angularSpeed;
        float envelope=Mathf.Lerp(.3f,1f,Mathf.Sin(t*Mathf.PI)); float shaped=PatternRadius(pattern,t,angle)*envelope;
        float jitter=packetMotion?PatternJitter(pattern,t):0f; return Vector3.Lerp(a,b,t)+(side*Mathf.Cos(angle)+up*Mathf.Sin(angle))*radius*shaped+up*jitter;
    }

    private static float PatternJitter(ThoughtPacketPattern value,float t)
    {
        if(value==ThoughtPacketPattern.Psychology)return (Mathf.PerlinNoise(t*9f,Time.unscaledTime*2f)-.5f)*.13f;
        if(value==ThoughtPacketPattern.Emotion)return Mathf.Sin(t*24f+Time.unscaledTime*8f)*.09f;
        if(value==ThoughtPacketPattern.Individual)return Mathf.Sin(t*55f+Time.unscaledTime*15f)*.055f;
        return 0f;
    }

    private static float PatternFrequency(ThoughtPacketPattern value){switch(value){case ThoughtPacketPattern.Science:return .25f;case ThoughtPacketPattern.Philosophy:return 1f;case ThoughtPacketPattern.Economics:return 2f;case ThoughtPacketPattern.Karma:return 1.4f;case ThoughtPacketPattern.Ideology:return 3f;case ThoughtPacketPattern.Community:return .8f;default:return 1.5f;}}
    private static float PatternRadius(ThoughtPacketPattern value,float t,float angle){switch(value){case ThoughtPacketPattern.Philosophy:return 1f;case ThoughtPacketPattern.Psychology:return .72f+Mathf.PerlinNoise(t*6f,angle*.08f)*.5f;case ThoughtPacketPattern.Science:return .28f;case ThoughtPacketPattern.Economics:return .72f+Mathf.Floor(t*8f)%2*.25f;case ThoughtPacketPattern.Karma:return .82f;case ThoughtPacketPattern.Emotion:return .7f+Mathf.Abs(Mathf.Sin(angle*1.4f))*.42f;case ThoughtPacketPattern.Moral:return .72f;case ThoughtPacketPattern.Ideology:return 1.18f;case ThoughtPacketPattern.Individual:return .55f+Mathf.PerlinNoise(t*13f,3f)*.55f;case ThoughtPacketPattern.Community:return 1.28f;default:return 1f;}}

    private void CreateImpact()
    {
        int count=critical?4:3; for(int i=0;i<count;i++){LineRenderer ring=Line("ArrivalRipple_"+(i+1),width*(1.05f+i*.16f),color);ring.loop=true;ring.positionCount=40;ring.enabled=false;ripples.Add(new Ripple{line=ring,delay=i*.14f});}
    }

    private void UpdateRipples()
    {
        for(int r=0;r<ripples.Count;r++){Ripple ripple=ripples[r];float localAge=(elapsed-duration-ripple.delay)/.82f;if(localAge<0f)continue;ripple.line.enabled=true;float age=Mathf.Clamp01(localAge);float rr=.1f+age*(critical&&r==ripples.Count-1?1.35f:.82f+r*.12f);Color faded=new Color(color.r,color.g,color.b,1f-age);ripple.line.startColor=ripple.line.endColor=faded;for(int i=0;i<ripple.line.positionCount;i++){float a=i/(float)ripple.line.positionCount*Mathf.PI*2;ripple.line.SetPosition(i,target.position+new Vector3(Mathf.Cos(a)*rr,.02f,Mathf.Sin(a)*rr));}}
    }

    private void Release(){if(release!=null){Action<KnowledgePacketView> callback=release;release=null;callback(this);}else Destroy(gameObject);}
    private void CleanupVisuals(){for(int i=transform.childCount-1;i>=0;i--){GameObject child=transform.GetChild(i).gameObject;child.SetActive(false);Destroy(child);}packets.Clear();ripples.Clear();core=null;spiralA=null;spiralB=null;packetLight=null;if(lineMaterial!=null)Destroy(lineMaterial);if(packetMaterial!=null)Destroy(packetMaterial);}
    private static Color IntentColor(KnowledgeIntent value){switch(value){case KnowledgeIntent.EnemyAttack:return new Color(1f,.08f,.045f);case KnowledgeIntent.Support:return new Color(.1f,1f,.22f);case KnowledgeIntent.Resonance:return new Color(.05f,.48f,1f);case KnowledgeIntent.Debuff:return new Color(.65f,.08f,1f);case KnowledgeIntent.SelfEnhance:return new Color(1f,.72f,.05f);default:return Color.white;}}
    private void OnDestroy(){if(lineMaterial!=null)Destroy(lineMaterial);if(packetMaterial!=null)Destroy(packetMaterial);}
}
