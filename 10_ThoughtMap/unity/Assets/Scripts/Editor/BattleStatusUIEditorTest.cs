using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class BattleStatusUIEditorTest
{
    [MenuItem("Tools/Source of Thought/Verify Battle Status UI Phase 1")]
    public static void Run()
    {
        ThoughtMapBattleCardData card = new ThoughtMapBattleCardData { cardId = "status-test", cardName = "Status Test", statPhysicalAttack = 50, statSkillAttack = 44, statPhysicalDefense = 40, statSkillDefense = 36, statHp = 60 };
        ThoughtMapBattleUnit unit = new ThoughtMapBattleUnit(card, "Player", new ThoughtMapGridPosition(2, 1)) { battleId = "P1", physicalAttack = 50, skillAttack = 44, physicalDefense = 40, skillDefense = 36 };
        FakeStatusReadModel source = new FakeStatusReadModel(unit);
        List<BattleStatusDisplayModel> models = BattleStatusPresenter.Build(unit, source);
        Require(models.Count == 6, "Expected all six status types.");
        Require(models[0].EffectType == BattleSkillEffectType.Stun, "Stun must have highest priority.");
        Require(models[1].EffectType == BattleSkillEffectType.Taunt, "Taunt priority mismatch.");
        Require(models[2].EffectType == BattleSkillEffectType.Shield, "Shield priority mismatch.");
        Require(models[3].EffectType == BattleSkillEffectType.DamageOverTime, "DOT priority mismatch.");
        Require(models.Count - BattleStatusPresenter.MaxVisible == 2, "Overflow must display +2.");
        string detail = BattleStatusPresenter.BuildDetail(unit, source);
        Require(detail.Contains("Shield 24 / 2 turns"), "Shield detail mismatch.");
        Require(detail.Contains("P.ATK +12 / 2 turns"), "Attack detail mismatch.");
        Require(detail.Contains("P.DEF -8 / 1 turn"), "Defense detail mismatch.");
        Require(detail.Contains("Stun / next action"), "Stun detail mismatch.");
        unit.hp = 0;
        Require(BattleStatusPresenter.Build(unit, source).Count == 0, "Defeated unit must hide statuses.");
        Require(BattleStatusPresenter.BuildDetail(unit, source) == "DEFEATED", "Defeated detail mismatch.");
        Debug.Log("[BattleStatusUI] PASS effects=6 visible=4 overflow=+2 priority=Stun>Taunt>Shield>DOT>DefenseDebuff>AttackBuff detail-effective-values=true defeated-clears=true");
    }

    private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException("[BattleStatusUI] " + message); }

    private sealed class FakeStatusReadModel : IBattleStatusReadModel
    {
        private readonly List<ActiveStatusEffect> effects;
        public FakeStatusReadModel(ThoughtMapBattleUnit unit)
        {
            effects = new List<ActiveStatusEffect>
            {
                Effect(BattleSkillEffectType.AttackBuff, "physical_attack", 12, 2),
                Effect(BattleSkillEffectType.DefenseDebuff, "physical_defense", 8, 1),
                Effect(BattleSkillEffectType.DamageOverTime, "hp", 6, 3),
                Effect(BattleSkillEffectType.Shield, "hp", 24, 2),
                Effect(BattleSkillEffectType.Taunt, "hate", 1, 2),
                Effect(BattleSkillEffectType.Stun, "action", 1, 1),
            };
            foreach (ActiveStatusEffect effect in effects) effect.targetUnitId = unit.battleId;
        }
        public IReadOnlyList<ActiveStatusEffect> GetActiveEffects(string unitId) => effects;
        public int GetShield(ThoughtMapBattleUnit unit) => 24;
        public int GetEffectiveAttack(ThoughtMapBattleUnit unit, bool magic) => magic ? unit.skillAttack : unit.physicalAttack + 12;
        public int GetEffectiveDefense(ThoughtMapBattleUnit unit, bool magic) => magic ? unit.skillDefense : unit.physicalDefense - 8;
        public float GetTauntMultiplier(ThoughtMapBattleUnit unit) => 2f;
        private static ActiveStatusEffect Effect(BattleSkillEffectType type, string parameter, float value, int turns) => new ActiveStatusEffect { effectType = type, sourceUnitId = "E1", parameter = parameter, value = value, remainingTurns = turns, stackCount = 1 };
    }
}
