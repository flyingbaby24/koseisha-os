using System.Collections.Generic;
using UnityEngine;

/// <summary>Ambient-only Cyber Archive motion. It never reads or changes battle state.</summary>
public sealed class CyberArchiveEnvironmentView : MonoBehaviour
{
    [SerializeField] private float pageDriftSpeed = 0.32f;
    [SerializeField] private float shelfFloatHeight = 0.06f;
    [SerializeField] private float dataPulseSpeed = 1.4f;
    [SerializeField] private float archiveInwardOffset = 0.7f;

    private readonly List<Transform> pages = new List<Transform>();
    private readonly List<Vector3> pageOrigins = new List<Vector3>();
    private readonly List<Transform> towers = new List<Transform>();
    private readonly List<Vector3> towerOrigins = new List<Vector3>();
    private readonly List<Transform> halos = new List<Transform>();
    private readonly List<Renderer> holograms = new List<Renderer>();
    private MaterialPropertyBlock block;

    private void Awake()
    {
        block = new MaterialPropertyBlock();
        foreach (Transform child in GetComponentsInChildren<Transform>(true))
        {
            if (child.name.StartsWith("FloatingPage")) { pages.Add(child); pageOrigins.Add(child.localPosition); }
            else if (child.name.StartsWith("ArchiveTower")) { Vector3 position=child.localPosition;position.x+=child.name.Contains("_L_")?archiveInwardOffset:-archiveInwardOffset;child.localPosition=position;towers.Add(child);towerOrigins.Add(position); }
            else if (child.name.StartsWith("NodeHalo") || child.name.StartsWith("KnowledgeNexusRing")) halos.Add(child);
            if (child.name.StartsWith("HologramPanel"))
            {
                Renderer renderer = child.GetComponent<Renderer>(); if (renderer != null) holograms.Add(renderer);
            }
        }
    }

    private void Update()
    {
        float time = Time.unscaledTime;
        for (int i=0;i<pages.Count;i++)
        {
            Transform page=pages[i]; float phase=i*.73f;
            page.localPosition=pageOrigins[i]+new Vector3(Mathf.Sin(time*.37f+phase)*.08f,Mathf.Sin(time*pageDriftSpeed+phase)*.24f,Mathf.Cos(time*.29f+phase)*.06f);
            page.Rotate(5f*Time.unscaledDeltaTime,11f*Time.unscaledDeltaTime,3f*Time.unscaledDeltaTime,Space.Self);
        }
        for(int i=0;i<towers.Count;i++) towers[i].localPosition=towerOrigins[i]+Vector3.up*(Mathf.Sin(time*.24f+i*1.7f)*shelfFloatHeight);
        for(int i=0;i<halos.Count;i++) halos[i].Rotate(0f,(i%2==0?1f:-1f)*(4f+i%3)*Time.unscaledDeltaTime,0f,Space.Self);
        Color pulse=new Color(.02f,.45f,1f)*(2.6f+Mathf.Sin(time*dataPulseSpeed)*1.2f);
        foreach(Renderer renderer in holograms){renderer.GetPropertyBlock(block);block.SetColor("_EmissionColor",pulse);renderer.SetPropertyBlock(block);}
    }
}
