using System.Collections.Generic;
using UnityEngine;

/// <summary>Display-only 5x5 team grids aligned to BattleUnit presentation coordinates.</summary>
public sealed class BattlefieldGridPresentationView : MonoBehaviour
{
    private readonly List<GameObject> visuals=new List<GameObject>();
    private Material playerMaterial;
    private Material enemyMaterial;
    private Material dividerMaterial;
    private Material floorMaterial;
    private BattlefieldVisualPolishView polish;

    public void Build(float spacingX,float spacingZ,Vector2 playerCenter,Vector2 enemyCenter,float floorY)
    {
        Clear();
        playerMaterial=Material(new Color(.04f,.42f,.82f,.13f),"PlayerGrid");
        enemyMaterial=Material(new Color(.68f,.07f,.065f,.11f),"EnemyGrid");
        dividerMaterial=Material(new Color(.28f,.38f,.42f,.075f),"GridDivider");
        BuildArchiveFloor(spacingX,spacingZ,playerCenter,enemyCenter,floorY);
        BuildGrid("PlayerGrid",playerCenter,spacingX,spacingZ,floorY,playerMaterial);
        BuildGrid("EnemyGrid",enemyCenter,spacingX,spacingZ,floorY,enemyMaterial);
        CreateLine("TeamDivider",new Vector3(0f,floorY+.012f,-spacingZ*2.9f),new Vector3(0f,floorY+.012f,spacingZ*2.9f),.007f,dividerMaterial);
        CreateArchiveUplink("ArchiveUplink_L",new Vector3(playerCenter.x-spacingX*2.5f,floorY+.02f,playerCenter.y+spacingZ*2.5f),new Vector3(-6.8f,floorY+.05f,10.5f),playerMaterial,-1f);
        CreateArchiveUplink("ArchiveUplink_R",new Vector3(enemyCenter.x+spacingX*2.5f,floorY+.02f,enemyCenter.y+spacingZ*2.5f),new Vector3(6.8f,floorY+.05f,10.5f),enemyMaterial,1f);
        polish=GetComponent<BattlefieldVisualPolishView>()??gameObject.AddComponent<BattlefieldVisualPolishView>();
        polish.Build(floorY,playerCenter,enemyCenter);
    }

    private void BuildGrid(string name,Vector2 center,float sx,float sz,float y,Material material)
    {
        GameObject root=new GameObject(name);root.transform.SetParent(transform,false);visuals.Add(root);
        float minX=center.x-sx*2.5f,maxX=center.x+sx*2.5f,minZ=center.y-sz*2.5f,maxZ=center.y+sz*2.5f;
        for(int i=0;i<=5;i++){float x=minX+i*sx;CreateLine(name+"_V"+i,new Vector3(x,y,minZ),new Vector3(x,y,maxZ),.006f,material,root.transform);}
        for(int i=0;i<=5;i++){float z=minZ+i*sz;CreateLine(name+"_H"+i,new Vector3(minX,y,z),new Vector3(maxX,y,z),.006f,material,root.transform);}
        for(int row=0;row<5;row++)for(int col=0;col<5;col++)CreateMarker(name+"_Slot_"+col+"_"+row,new Vector3(center.x+(col-2)*sx,y+.018f,center.y+(row-2)*sz),material,root.transform);
    }

    private void CreateMarker(string name,Vector3 center,Material material,Transform parent)
    {
        bool occupied=false;foreach(BattleUnitView unit in GetComponentsInChildren<BattleUnitView>(true)){Vector3 p=unit.transform.position;if(new Vector2(p.x-center.x,p.z-center.z).sqrMagnitude<.12f){occupied=true;break;}}
        GameObject go=new GameObject(name,typeof(LineRenderer));go.transform.SetParent(parent,false);LineRenderer line=go.GetComponent<LineRenderer>();line.sharedMaterial=material;line.useWorldSpace=true;line.loop=true;line.positionCount=32;line.startWidth=line.endWidth=occupied?.011f:.0045f;Color tint=occupied?new Color(1f,1f,1f,.72f):new Color(1f,1f,1f,.22f);line.startColor=line.endColor=tint;
        float radius=.22f;for(int i=0;i<32;i++){float a=i/32f*Mathf.PI*2f;line.SetPosition(i,center+new Vector3(Mathf.Cos(a)*radius,0f,Mathf.Sin(a)*radius));}
    }

    private void BuildArchiveFloor(float sx,float sz,Vector2 player,Vector2 enemy,float gridY)
    {
        float minX=Mathf.Min(player.x,enemy.x)-sx*2.75f,maxX=Mathf.Max(player.x,enemy.x)+sx*2.75f;
        float minZ=Mathf.Min(player.y,enemy.y)-sz*2.75f,maxZ=Mathf.Max(player.y,enemy.y)+sz*2.75f;
        Shader shader=Shader.Find("Universal Render Pipeline/Lit")??Shader.Find("Standard");floorMaterial=new Material(shader){name="IntegratedArchiveFloor_Runtime"};Color color=new Color(.018f,.055f,.085f,.34f);floorMaterial.SetColor("_BaseColor",color);floorMaterial.SetColor("_Color",color);floorMaterial.SetFloat("_Metallic",.30f);floorMaterial.SetFloat("_Smoothness",.72f);
        if(floorMaterial.HasProperty("_Surface")){floorMaterial.SetFloat("_Surface",1f);floorMaterial.SetFloat("_SrcBlend",5f);floorMaterial.SetFloat("_DstBlend",10f);floorMaterial.SetFloat("_ZWrite",0f);floorMaterial.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");floorMaterial.renderQueue=3000;}
        GameObject floor=GameObject.CreatePrimitive(PrimitiveType.Cube);floor.name="IntegratedArchiveFloor";Destroy(floor.GetComponent<Collider>());floor.transform.SetParent(transform,false);floor.transform.localPosition=new Vector3((minX+maxX)*.5f,gridY-.055f,(minZ+maxZ)*.5f);floor.transform.localScale=new Vector3(maxX-minX,.045f,maxZ-minZ);Renderer renderer=floor.GetComponent<Renderer>();renderer.sharedMaterial=floorMaterial;renderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;renderer.receiveShadows=false;visuals.Add(floor);
    }

    private void CreateArchiveUplink(string name,Vector3 start,Vector3 end,Material material,float side)
    {
        GameObject go=new GameObject(name,typeof(LineRenderer));go.transform.SetParent(transform,false);visuals.Add(go);
        LineRenderer line=go.GetComponent<LineRenderer>();line.sharedMaterial=material;line.useWorldSpace=true;line.positionCount=24;line.startWidth=line.endWidth=.007f;line.startColor=line.endColor=new Color(1f,1f,1f,.48f);line.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;line.receiveShadows=false;
        Vector3 control=(start+end)*.5f+new Vector3(side*.55f,1.15f,-.25f);
        for(int i=0;i<line.positionCount;i++){float t=i/(float)(line.positionCount-1);float u=1f-t;line.SetPosition(i,u*u*start+2f*u*t*control+t*t*end);}
    }

    private void CreateLine(string name,Vector3 a,Vector3 b,float width,Material material,Transform parent=null)
    {
        GameObject go=new GameObject(name,typeof(LineRenderer));go.transform.SetParent(parent==null?transform:parent,false);if(parent==null)visuals.Add(go);LineRenderer line=go.GetComponent<LineRenderer>();line.sharedMaterial=material;line.useWorldSpace=true;line.positionCount=2;line.SetPosition(0,a);line.SetPosition(1,b);line.startWidth=line.endWidth=width;line.startColor=line.endColor=Color.white;
    }

    private static Material Material(Color color,string name)
    {
        Shader shader=Shader.Find("ThoughtMap/KnowledgeLine")??Shader.Find("Sprites/Default");Material material=new Material(shader){name=name};material.SetColor("_BaseColor",color);material.SetColor("_Color",color);if(material.HasProperty("_Glow"))material.SetFloat("_Glow",.38f);if(material.HasProperty("_FlowSpeed"))material.SetFloat("_FlowSpeed",.08f);return material;
    }

    private void Clear(){foreach(GameObject visual in visuals)if(visual!=null)Destroy(visual);visuals.Clear();if(playerMaterial!=null)Destroy(playerMaterial);if(enemyMaterial!=null)Destroy(enemyMaterial);if(dividerMaterial!=null)Destroy(dividerMaterial);if(floorMaterial!=null)Destroy(floorMaterial);}
    private void OnDestroy(){Clear();}
}
