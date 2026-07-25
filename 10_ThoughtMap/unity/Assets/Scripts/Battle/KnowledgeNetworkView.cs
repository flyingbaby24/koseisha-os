using System;
using System.Collections.Generic;
using UnityEngine;

public sealed class KnowledgeNetworkView : MonoBehaviour
{
    [SerializeField] private GameObject packetPrefab;
    private readonly Dictionary<string,BattleUnitView> nodes=new Dictionary<string,BattleUnitView>();
    private readonly List<GameObject> resonanceLinks=new List<GameObject>();
    private readonly Stack<KnowledgePacketView> pool=new Stack<KnowledgePacketView>();

    public void Initialize(IReadOnlyDictionary<string,BattleUnitView> unitViews)
    {
        if(packetPrefab==null)packetPrefab=Resources.Load<GameObject>("Effects/KnowledgePacket");
        nodes.Clear();foreach(var pair in unitViews)if(pair.Value!=null&&pair.Value.KnowledgeCore!=null)nodes[pair.Key]=pair.Value;
        BuildResonanceLinks();
    }

    public void PlayAttack(BattlePhase1Event battleEvent)
    {
        if(battleEvent?.attacker==null||battleEvent.target==null)return;
        bool critical=battleEvent.damage>=Mathf.Max(30,Mathf.RoundToInt(battleEvent.target.maxHp*.28f));
        Spawn(battleEvent.attacker.battleId,battleEvent.target.battleId,KnowledgeIntent.EnemyAttack,battleEvent.damage,Pattern(battleEvent.attacker.card),critical,.52f,false);
    }

    public void PlaySupport(string sourceId,string targetId,int power,string attribute) => Spawn(sourceId,targetId,KnowledgeIntent.Support,power,Pattern(attribute),false,.72f,false);
    public void PlayDebuff(string sourceId,string targetId,int power,string attribute) => Spawn(sourceId,targetId,KnowledgeIntent.Debuff,power,Pattern(attribute),false,.72f,false);
    public void PlaySelfEnhance(string unitId,int power,string attribute)
    {
        if(!nodes.TryGetValue(unitId,out BattleUnitView node))return;
        GameObject endpoint=new GameObject("SelfEnhanceEndpoint");endpoint.transform.SetParent(node.EffectRoot,false);endpoint.transform.localPosition=Vector3.up*.55f;
        GameObject effect=Spawn(node.KnowledgeCore,endpoint.transform,node.EffectRoot,KnowledgeIntent.SelfEnhance,power,Pattern(attribute),false,.55f,false);Destroy(endpoint,1.2f);
    }

    private void BuildResonanceLinks()
    {
        foreach(GameObject link in resonanceLinks)if(link!=null){KnowledgePacketView view=link.GetComponent<KnowledgePacketView>();if(view!=null)Release(view);else Destroy(link);}resonanceLinks.Clear();
        var list=new List<KeyValuePair<string,BattleUnitView>>(nodes);int created=0;
        for(int i=0;i<list.Count&&created<6;i++)for(int j=i+1;j<list.Count&&created<6;j++)
        {
            BattlePresentationUnitData a=list[i].Value.PresentationData,b=list[j].Value.PresentationData;if(a==null||b==null||a.EnemySide!=b.EnemySide)continue;
            string aa=a.Card?.primaryAttribute,bb=b.Card?.primaryAttribute;if(string.IsNullOrWhiteSpace(aa)||!string.Equals(aa,bb,StringComparison.OrdinalIgnoreCase))continue;
            GameObject link=Spawn(list[i].Value.KnowledgeCore,list[j].Value.KnowledgeCore,list[i].Value.EffectRoot,KnowledgeIntent.Resonance,5,Pattern(aa),false,2f,true);if(link!=null){resonanceLinks.Add(link);created++;}
        }
    }

    private GameObject Spawn(string from,string to,KnowledgeIntent intent,int power,ThoughtPacketPattern pattern,bool critical,float duration,bool persistent)
    {
        return nodes.TryGetValue(from,out BattleUnitView a)&&nodes.TryGetValue(to,out BattleUnitView b)?Spawn(a.KnowledgeCore,b.KnowledgeCore,a.EffectRoot,intent,power,pattern,critical,duration,persistent):null;
    }

    private GameObject Spawn(Transform from,Transform to,Transform effectRoot,KnowledgeIntent intent,int power,ThoughtPacketPattern pattern,bool critical,float duration,bool persistent)
    {
        if(packetPrefab==null)packetPrefab=Resources.Load<GameObject>("Effects/KnowledgePacket");if(packetPrefab==null)return null;
        KnowledgePacketView view=pool.Count>0?pool.Pop():Instantiate(packetPrefab).GetComponent<KnowledgePacketView>();
        GameObject effect=view.gameObject;effect.transform.SetParent(effectRoot,false);effect.name=persistent?"ResonanceLink":"KnowledgePacket";
        view.Configure(from,to,intent,pattern,power,critical,duration,persistent,Release);return effect;
    }

    private void Release(KnowledgePacketView view)
    {
        if(view==null)return;view.gameObject.SetActive(false);view.transform.SetParent(transform,false);pool.Push(view);
    }

    private static ThoughtPacketPattern Pattern(ThoughtMapBattleCardData card) => Pattern(card==null?string.Empty:(!string.IsNullOrWhiteSpace(card.category)?card.category:card.primaryAttribute));
    private static ThoughtPacketPattern Pattern(string value)
    {
        string key=(value??string.Empty).ToLowerInvariant();
        if(key.Contains("philos")||key.Contains("哲"))return ThoughtPacketPattern.Philosophy;if(key.Contains("psych")||key.Contains("心"))return ThoughtPacketPattern.Psychology;if(key.Contains("scien")||key.Contains("科学"))return ThoughtPacketPattern.Science;if(key.Contains("econom")||key.Contains("経済"))return ThoughtPacketPattern.Economics;if(key.Contains("karma")||key.Contains("カルマ"))return ThoughtPacketPattern.Karma;if(key.Contains("emotion")||key.Contains("感情"))return ThoughtPacketPattern.Emotion;if(key.Contains("moral")||key.Contains("モラル"))return ThoughtPacketPattern.Moral;if(key.Contains("ideol")||key.Contains("理念"))return ThoughtPacketPattern.Ideology;if(key.Contains("individual")||key.Contains("個人"))return ThoughtPacketPattern.Individual;if(key.Contains("community")||key.Contains("共同"))return ThoughtPacketPattern.Community;return ThoughtPacketPattern.Generic;
    }
}
