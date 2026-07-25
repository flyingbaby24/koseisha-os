using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// <summary>Battlefield-only visual dressing. It never reads or changes battle state.</summary>
public sealed class BattlefieldVisualPolishView : MonoBehaviour
{
    [Header("Digital Thought Battlefield")]
    [SerializeField] private Color playerAmbient = new Color(.04f, .30f, .72f);
    [SerializeField] private Color enemyAmbient = new Color(.58f, .055f, .045f);
    [SerializeField] private Color neutralAmbient = new Color(.14f, .34f, .46f);
    [SerializeField, Range(0f, 1f)] private float particleOpacity = .18f;
    [SerializeField] private bool logVisualAudit;

    private readonly List<GameObject> generated = new List<GameObject>();
    private readonly List<Material> runtimeMaterials = new List<Material>();
    private readonly List<Mesh> runtimeMeshes = new List<Mesh>();
    private Volume volume;
    private VolumeProfile volumeProfile;
    private bool built;

    public void Build(float floorY, Vector2 playerCenter, Vector2 enemyCenter)
    {
        if (built) return;
        built = true;
        SoftenLegacyStructures();
        BuildFloorCircuits(floorY, playerCenter, enemyCenter);
        BuildKnowledgeArtifacts(floorY);
        BuildLighting();
        BuildParticles(floorY);
        BuildPostProcessing();
        if(logVisualAudit)AuditRuntimeVisuals();
    }

    private void SoftenLegacyStructures()
    {
        foreach (Renderer renderer in GetComponentsInChildren<Renderer>(true))
        {
            if (renderer == null || renderer is ParticleSystemRenderer) continue;
            bool prohibitedDarkShape = false;
            string materialNames = string.Empty;
            foreach (Material material in renderer.sharedMaterials)
            {
                if(material==null)continue;
                if(materialNames.Length>0)materialNames+=",";
                materialNames+=material.name;
                if (material.name.Contains("DarkStructure") || material.name.Contains("ArchiveMetal") ||
                    material.name.Contains("DataPage") || material.name.Contains("ArchiveBook")) prohibitedDarkShape = true;
            }
            if (!prohibitedDarkShape) continue;
            MeshFilter filter=renderer.GetComponent<MeshFilter>();
            string meshName=filter!=null&&filter.sharedMesh!=null?filter.sharedMesh.name:"<none>";
            if(logVisualAudit)Debug.Log($"[BattlefieldVisualAudit] DISABLE path={Path(renderer.transform)} mesh={meshName} bounds={renderer.bounds.size} materials={materialNames}");
            renderer.enabled = false;
        }
    }

    private void BuildFloorCircuits(float y, Vector2 player, Vector2 enemy)
    {
        Material neutral = MakeLineMaterial("BattlefieldNeutralCircuit", new Color(.20f, .66f, .82f, .38f), .44f);
        for (int ring = 0; ring < 3; ring++)
            CreateRing("ThoughtNexusRing_" + ring, new Vector3(0f, y + .008f, 1.5f), 1.4f + ring * 1.10f, .010f, neutral, 72);

        CreateCircuitBranch(new Vector3(player.x + 2.5f, y + .01f, player.y), new Vector3(-1.2f, y + .01f, 0f), playerAmbient, "PlayerKnowledgeCircuit");
        CreateCircuitBranch(new Vector3(enemy.x - 2.5f, y + .01f, enemy.y), new Vector3(1.2f, y + .01f, 0f), enemyAmbient, "EnemyKnowledgeCircuit");
        CreateRing("NexusCore", new Vector3(0f, y + .012f, 1.5f), .46f, .016f, neutral, 48);
    }

    private void BuildKnowledgeArtifacts(float floorY)
    {
        Material crystalBlue = MakeLitMaterial("KnowledgeCrystalBlue", new Color(.035f, .16f, .23f), .48f, .74f, playerAmbient * .46f);
        Material crystalRed = MakeLitMaterial("KnowledgeCrystalRed", new Color(.20f, .055f, .045f), .46f, .72f, enemyAmbient * .42f);
        Material rune = MakeLineMaterial("AncientDataRune", new Color(.24f, .70f, .84f, .44f), .48f);
        Material book = MakeLitMaterial("LuminousArchiveBook", new Color(.055f, .11f, .14f), .12f, .44f, new Color(.018f, .055f, .072f));

        CreateCrystalCluster("PlayerKnowledgeMonument", new Vector3(-8.25f, floorY + .28f, 7.6f), crystalBlue, -12f);
        CreateCrystalCluster("EnemyKnowledgeMonument", new Vector3(8.25f, floorY + .28f, 7.6f), crystalRed, 12f);
        CreateNexusMonument("ArchiveNexusMonument",new Vector3(0f,floorY+.025f,8.7f),rune);
        CreateOpenBook("FloatingArchiveBook_L", new Vector3(-7.15f, floorY + 1.05f, 5.2f), new Vector3(5f, 20f, -5f), book);
        CreateOpenBook("FloatingArchiveBook_R", new Vector3(7.15f, floorY + 1.05f, 5.2f), new Vector3(-5f, -20f, 5f), book);
        CreateRing("AncientRune_L", new Vector3(-8.25f, floorY + .025f, 7.6f), .82f, .014f, rune, 48);
        CreateRing("AncientRune_R", new Vector3(8.25f, floorY + .025f, 7.6f), .82f, .014f, rune, 48);
    }

    private void BuildLighting()
    {
        foreach (Light existing in GetComponentsInChildren<Light>(true))
            if (existing.type != LightType.Directional) existing.enabled = false;

        GameObject root = NewGenerated("PolishLights", transform);
        Light center = NewLight(root.transform, "ThoughtNexusSpot", LightType.Spot, neutralAmbient, 1.25f, 28f, new Vector3(0f, 13f, -1.5f));
        center.spotAngle = 62f;
        center.innerSpotAngle = 32f;
        center.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
        center.shadows = LightShadows.Soft;
        center.shadowStrength = .34f;

        Light player = NewLight(root.transform, "PlayerArchiveFill", LightType.Point, playerAmbient, .42f, 13f, new Vector3(-5.5f, 4.2f, -1f));
        Light enemy = NewLight(root.transform, "EnemyArchiveFill", LightType.Point, enemyAmbient, .34f, 13f, new Vector3(5.5f, 4.2f, -1f));
        player.shadows = LightShadows.None;
        enemy.shadows = LightShadows.None;
    }

    private void BuildParticles(float floorY)
    {
        Material particle = MakeParticleMaterial("ThoughtDust", new Color(.22f, .58f, .78f, particleOpacity));
        CreateParticles("ThoughtDust", new Vector3(0f, floorY + .2f, 2f), new Vector3(23f, 5f, 24f), particle, 11f, 70, .024f, .16f, 7f);
        Material mist = MakeParticleMaterial("DataMist", new Color(.08f, .20f, .28f, particleOpacity * .18f));
        CreateParticles("DataMist", new Vector3(0f, floorY + .05f, 3f), new Vector3(20f, .25f, 20f), mist, .4f, 22, 1.25f, .035f, 8f);
    }

    private void BuildPostProcessing()
    {
        GameObject go = NewGenerated("BattlefieldPostProcess", transform);
        volume = go.AddComponent<Volume>();
        volume.isGlobal = true;
        volume.priority = -5f;
        volume.weight = 1f;
        volumeProfile = ScriptableObject.CreateInstance<VolumeProfile>();
        volume.profile = volumeProfile;

        Bloom bloom = volumeProfile.Add<Bloom>();
        bloom.active = true; bloom.intensity.Override(.16f); bloom.threshold.Override(1.15f); bloom.scatter.Override(.42f);
        Vignette vignette = volumeProfile.Add<Vignette>();
        vignette.active = true; vignette.color.Override(new Color(.002f, .006f, .012f)); vignette.intensity.Override(.17f); vignette.smoothness.Override(.72f); vignette.rounded.Override(false);
        ColorAdjustments color = volumeProfile.Add<ColorAdjustments>();
        color.active = true; color.postExposure.Override(-.04f); color.contrast.Override(4f); color.saturation.Override(-7f); color.colorFilter.Override(new Color(.94f, .98f, 1f));
        Tonemapping tone = volumeProfile.Add<Tonemapping>();
        tone.active = true; tone.mode.Override(TonemappingMode.Neutral);
    }

    private void CreateCrystalCluster(string name, Vector3 position, Material material, float yaw)
    {
        GameObject root = NewGenerated(name, transform);
        root.transform.localPosition = position;
        root.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);
        CreateCrystal(root.transform, new Vector3(0f, .36f, 0f), new Vector3(.32f, .72f, .32f), material);
        CreateCrystal(root.transform, new Vector3(-.34f, .19f, .18f), new Vector3(.20f, .38f, .20f), material);
        CreateCrystal(root.transform, new Vector3(.34f, .16f, -.12f), new Vector3(.18f, .31f, .18f), material);
    }

    private void CreateNexusMonument(string name,Vector3 position,Material material)
    {
        GameObject root=NewGenerated(name,transform);root.transform.localPosition=position;
        GameObject outer=CreateRing(name+"_Outer",position,.92f,.018f,material,64);
        GameObject inner=CreateRing(name+"_Inner",position+new Vector3(0f,.006f,0f),.48f,.014f,material,48);
        outer.transform.SetParent(root.transform,true);inner.transform.SetParent(root.transform,true);
    }

    private void CreateCrystal(Transform parent, Vector3 localPosition, Vector3 scale, Material material)
    {
        GameObject go = new GameObject("KnowledgeCrystal", typeof(MeshFilter), typeof(MeshRenderer));
        go.transform.SetParent(parent, false); go.transform.localPosition = localPosition; go.transform.localScale = scale;
        Mesh mesh = CreateOctahedron(); go.GetComponent<MeshFilter>().sharedMesh = mesh; go.GetComponent<MeshRenderer>().sharedMaterial = material;
        go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.On; go.GetComponent<MeshRenderer>().receiveShadows = true;
    }

    private Mesh CreateOctahedron()
    {
        Mesh mesh = new Mesh { name = "KnowledgeCrystalMesh_Runtime" };
        mesh.vertices = new[] { new Vector3(0,1,0),new Vector3(1,0,0),new Vector3(0,0,1),new Vector3(-1,0,0),new Vector3(0,0,-1),new Vector3(0,-1,0) };
        mesh.triangles = new[] { 0,2,1,0,3,2,0,4,3,0,1,4,5,1,2,5,2,3,5,3,4,5,4,1 };
        mesh.RecalculateNormals(); mesh.RecalculateBounds(); runtimeMeshes.Add(mesh); return mesh;
    }

    private void CreateOpenBook(string name, Vector3 position, Vector3 rotation, Material material)
    {
        GameObject root = NewGenerated(name, transform); root.transform.localPosition = position; root.transform.localEulerAngles = rotation;
        Mesh mesh = new Mesh { name = "OpenKnowledgeBook_Runtime" };
        mesh.vertices = new[] { new Vector3(-.85f,0,0),new Vector3(0,.12f,0),new Vector3(0,.12f,1.15f),new Vector3(-.85f,0,1.15f),new Vector3(0,.12f,0),new Vector3(.85f,0,0),new Vector3(.85f,0,1.15f),new Vector3(0,.12f,1.15f) };
        mesh.triangles = new[] { 0,1,2,0,2,3,4,5,6,4,6,7 }; mesh.RecalculateNormals(); mesh.RecalculateBounds(); runtimeMeshes.Add(mesh);
        MeshFilter filter = root.AddComponent<MeshFilter>(); filter.sharedMesh = mesh; MeshRenderer renderer = root.AddComponent<MeshRenderer>(); renderer.sharedMaterial = material; renderer.shadowCastingMode = ShadowCastingMode.On;
    }

    private void CreateCircuitBranch(Vector3 from, Vector3 to, Color color, string name)
    {
        Material material = MakeLineMaterial(name, new Color(color.r, color.g, color.b, .28f), .34f);
        Vector3 middle = Vector3.Lerp(from, to, .55f); middle.z += from.x < 0 ? .8f : -.8f;
        CreateLine(name, new[] { from, middle, to }, .008f, material, transform);
    }

    private GameObject CreateRing(string name, Vector3 center, float radius, float width, Material material, int segments)
    {
        Vector3[] points = new Vector3[segments];
        for (int i=0;i<segments;i++){float angle=i/(float)segments*Mathf.PI*2f;points[i]=center+new Vector3(Mathf.Cos(angle)*radius,0f,Mathf.Sin(angle)*radius);}
        GameObject go = CreateLine(name, points, width, material, transform); go.GetComponent<LineRenderer>().loop = true;return go;
    }

    private GameObject CreateLine(string name, Vector3[] points, float width, Material material, Transform parent)
    {
        GameObject go = NewGenerated(name, parent); LineRenderer line = go.AddComponent<LineRenderer>(); line.sharedMaterial=material; line.useWorldSpace=true; line.positionCount=points.Length; line.SetPositions(points); line.startWidth=line.endWidth=width; line.startColor=line.endColor=Color.white; line.shadowCastingMode=ShadowCastingMode.Off; line.receiveShadows=false; return go;
    }

    private void CreateParticles(string name, Vector3 position, Vector3 box, Material material, float rate, int max, float size, float speed, float lifetime)
    {
        GameObject go=NewGenerated(name,transform);go.transform.localPosition=position;ParticleSystem ps=go.AddComponent<ParticleSystem>();var main=ps.main;main.loop=true;main.playOnAwake=true;main.startLifetime=lifetime;main.startSpeed=speed;main.startSize=size;main.startColor=Color.white;main.maxParticles=max;main.simulationSpace=ParticleSystemSimulationSpace.Local;var emission=ps.emission;emission.rateOverTime=rate;var shape=ps.shape;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=box;var velocity=ps.velocityOverLifetime;velocity.enabled=true;velocity.y=.08f;ParticleSystemRenderer renderer=go.GetComponent<ParticleSystemRenderer>();renderer.renderMode=ParticleSystemRenderMode.Billboard;renderer.sharedMaterial=material;renderer.shadowCastingMode=ShadowCastingMode.Off;
    }

    private Light NewLight(Transform parent,string name,LightType type,Color color,float intensity,float range,Vector3 position){GameObject go=new GameObject(name,typeof(Light));go.transform.SetParent(parent,false);go.transform.localPosition=position;Light light=go.GetComponent<Light>();light.type=type;light.color=color;light.intensity=intensity;light.range=range;return light;}
    private Material MakeLineMaterial(string name,Color color,float glow){Shader shader=Shader.Find("ThoughtMap/KnowledgeLine")??Shader.Find("Sprites/Default");Material material=new Material(shader){name=name+"_Runtime"};material.SetColor("_BaseColor",color);material.SetColor("_Color",color);if(material.HasProperty("_Glow"))material.SetFloat("_Glow",glow);if(material.HasProperty("_FlowSpeed"))material.SetFloat("_FlowSpeed",.035f);runtimeMaterials.Add(material);return material;}
    private Material MakeLitMaterial(string name,Color color,float metallic,float smoothness,Color emission){Shader shader=Shader.Find("Universal Render Pipeline/Lit")??Shader.Find("Standard");Material material=new Material(shader){name=name+"_Runtime"};material.SetColor("_BaseColor",color);material.SetColor("_Color",color);material.SetFloat("_Metallic",metallic);material.SetFloat("_Smoothness",smoothness);if(material.HasProperty("_Cull"))material.SetFloat("_Cull",0f);material.EnableKeyword("_EMISSION");material.SetColor("_EmissionColor",emission);runtimeMaterials.Add(material);return material;}
    private Material MakeParticleMaterial(string name,Color color)
    {
        Shader shader=Shader.Find("Universal Render Pipeline/Particles/Unlit")??Shader.Find("Sprites/Default");
        Material material=new Material(shader){name=name+"_Runtime"};
        material.SetColor("_BaseColor",color);material.SetColor("_Color",color);
        if(material.HasProperty("_Surface"))
        {
            material.SetFloat("_Surface",1f);material.SetFloat("_Blend",0f);
            material.SetFloat("_SrcBlend",5f);material.SetFloat("_DstBlend",10f);material.SetFloat("_ZWrite",0f);
            material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");material.renderQueue=3000;
        }
        runtimeMaterials.Add(material);return material;
    }
    private GameObject NewGenerated(string name,Transform parent){GameObject go=new GameObject(name);go.transform.SetParent(parent,false);generated.Add(go);return go;}

    private void AuditRuntimeVisuals()
    {
        string[] names={"ArchiveUplink_L","ArchiveUplink_R","PlayerKnowledgeMonument","EnemyKnowledgeMonument","ArchiveNexusMonument","IntegratedArchiveFloor","FloatingArchiveBook_L","FloatingArchiveBook_R","AncientRune_L","AncientRune_R","ThoughtNexusRing_0","ThoughtNexusRing_1","ThoughtNexusRing_2","PlayerKnowledgeCircuit","EnemyKnowledgeCircuit","NexusCore"};
        foreach(string targetName in names)
        {
            Transform target=FindDeep(transform,targetName);
            if(target==null){Debug.LogWarning($"[BattlefieldVisualAudit] MISSING name={targetName}");continue;}
            Renderer[] renderers=target.GetComponentsInChildren<Renderer>(true);
            string renderInfo=renderers.Length==0?"<none>":string.Join(" | ",System.Array.ConvertAll(renderers,r=>$"{r.GetType().Name}:{r.sharedMaterial?.name ?? "<none>"}:bounds={r.bounds.size}:enabled={r.enabled}"));
            MeshFilter filter=target.GetComponent<MeshFilter>();
            string mesh=filter!=null&&filter.sharedMesh!=null?filter.sharedMesh.name:"<none>";
            Debug.Log($"[BattlefieldVisualAudit] name={targetName} path={Path(target)} mesh={mesh} localPos={target.localPosition} localRot={target.localEulerAngles} localScale={target.localScale} worldPos={target.position} renderers={renderInfo}");
        }
    }

    private static Transform FindDeep(Transform root,string name)
    {
        foreach(Transform child in root){if(child.name==name)return child;Transform found=FindDeep(child,name);if(found!=null)return found;}return null;
    }

    private static string Path(Transform target)
    {
        string value=target.name;while(target.parent!=null){target=target.parent;value=target.name+"/"+value;}return value;
    }

    private void OnDestroy()
    {
        Release(volumeProfile);
        foreach(Material material in runtimeMaterials)Release(material);
        foreach(Mesh mesh in runtimeMeshes)Release(mesh);
    }

    private static void Release(Object value)
    {
        if(value==null)return;
        if(Application.isPlaying)Destroy(value);else DestroyImmediate(value);
    }
}
