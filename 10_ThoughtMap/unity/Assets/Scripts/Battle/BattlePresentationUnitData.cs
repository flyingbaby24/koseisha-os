using System.Collections.Generic;
using UnityEngine;

/// <summary>Display-only data for one BattleUnit. It is not a scene object and owns no battle logic.</summary>
public sealed class BattlePresentationUnitData
{
    public string UnitId { get; }
    public ThoughtMapBattleCardData Card { get; }
    public Sprite CardSprite { get; }
    public bool EnemySide { get; }
    public int CurrentHp { get; private set; }
    public int MaxHp { get; private set; }
    public int CurrentSp { get; private set; }
    public int PhysicalAttack { get; private set; }
    public int SkillAttack { get; private set; }
    public int PhysicalDefense { get; private set; }
    public int SkillDefense { get; private set; }
    public int Speed { get; private set; }
    public GeneratedSkillDto EquippedSkill { get; private set; }

    public BattlePresentationUnitData(string unitId, ThoughtMapBattleCardData card, Sprite sprite, bool enemySide,
        ThoughtMapBattlePreparedUnitData prepared, IReadOnlyList<GeneratedSkillDto> skills)
    {
        UnitId=unitId; Card=card; CardSprite=sprite; EnemySide=enemySide;
        CurrentHp=MaxHp=prepared==null?(card==null?1:card.MaxHp):prepared.maxHp;
        CurrentSp=card==null?0:card.MaxSp;
        PhysicalAttack=prepared==null?(card==null?0:card.statPhysicalAttack):prepared.physicalAttack;
        SkillAttack=prepared==null?(card==null?0:card.statSkillAttack):prepared.skillAttack;
        PhysicalDefense=prepared==null?(card==null?0:card.statPhysicalDefense):prepared.physicalDefense;
        SkillDefense=prepared==null?(card==null?0:card.statSkillDefense):prepared.skillDefense;
        Speed=prepared==null?(card==null?0:card.statSpeed):prepared.speed;
        EquippedSkill=skills!=null&&skills.Count>0?skills[0]:null;
    }

    public void ApplyRuntime(ThoughtMapBattleUnit unit)
    {
        if(unit==null)return;CurrentHp=unit.hp;MaxHp=unit.maxHp;CurrentSp=unit.sp;
        PhysicalAttack=unit.physicalAttack;SkillAttack=unit.skillAttack;PhysicalDefense=unit.physicalDefense;SkillDefense=unit.skillDefense;Speed=unit.speed;
        if(unit.assignedGeneratedSkills.Count>0)EquippedSkill=unit.assignedGeneratedSkills[0];
    }
}
