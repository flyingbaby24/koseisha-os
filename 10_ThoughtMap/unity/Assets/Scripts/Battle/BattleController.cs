using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public sealed class BattleController : IBattleStatusReadModel
{
    private readonly ThoughtMapHateCalculator hateCalculator;
    private readonly System.Random random;
    private readonly BattleResultScoreSettings resultScoreSettings;
    private BattleStatusEffectController statusEffects;
    private BattleSkillResolver skillResolver;

    public BattleController(
        ThoughtMapBattleResonanceConfig hateConfig = null,
        int? randomSeed = null,
        BattleResultScoreSettings scoreSettings = null)
    {
        hateCalculator = new ThoughtMapHateCalculator(hateConfig);
        random = randomSeed.HasValue ? new System.Random(randomSeed.Value) : new System.Random();
        resultScoreSettings = scoreSettings ?? new BattleResultScoreSettings();
    }

    public BattlePhase1Result Run(
        IReadOnlyList<ThoughtMapBattleCardData> playerCards,
        IReadOnlyList<ThoughtMapBattleCardData> enemyCards,
        IReadOnlyList<ThoughtMapGridPosition> playerPositions = null,
        IReadOnlyList<ThoughtMapGridPosition> enemyPositions = null,
        Action<BattlePhase1Event> onEvent = null,
        IReadOnlyList<ThoughtMapBattlePreparedUnitData> playerPreparedUnits = null,
        IReadOnlyDictionary<string, List<GeneratedSkillDto>> assignedSkills = null,
        IReadOnlyDictionary<string, List<GeneratedSkillDto>> enemyAssignedSkills = null)
    {
        statusEffects = new BattleStatusEffectController();
        skillResolver = new BattleSkillResolver(statusEffects, random);
        BattlePhase1Result result = new BattlePhase1Result();
        result.playerUnits.AddRange(BuildTeam(playerCards, "Player", "P", playerPositions, 0));
        result.enemyUnits.AddRange(BuildTeam(enemyCards, "Enemy", "E", enemyPositions, 4));

        if (result.playerUnits.Count != 5 || result.enemyUnits.Count != 5)
        {
            result.logLines.Add("Battle aborted: Phase1 requires exactly 5 Player and 5 Enemy units.");
            return result;
        }

        if (!ApplyPreparedPlayerData(result.playerUnits, playerPreparedUnits, assignedSkills))
        {
            result.logLines.Add("Battle aborted: Battle Prep final status data is missing or incomplete.");
            return result;
        }
        ApplyAssignedSkills(result.enemyUnits, enemyAssignedSkills);
        BindStatusNotifications(result, onEvent);

        result.logLines.Add("Battle Started");
        TriggerAssignedSkills(result.playerUnits, "battle_start", result, onEvent);
        const int safetyTurnLimit = 10000;
        while (result.turn < safetyTurnLimit)
        {
            result.turn++;
            AddLog(result, onEvent, $"Turn {result.turn}");
            TriggerAssignedSkills(result.playerUnits.Concat(result.enemyUnits).Where(unit => unit.IsAlive), "turn_start", result, onEvent);

            List<ThoughtMapBattleUnit> order = BuildTurnOrder(result.playerUnits, result.enemyUnits);
            foreach (ThoughtMapBattleUnit attacker in order)
            {
                if (!attacker.IsAlive)
                {
                    continue;
                }

                foreach (BattlePhase1Event statusEvent in skillResolver.ProcessTurnStart(attacker, result.playerUnits.Concat(result.enemyUnits), result.turn, line => AddLog(result, onEvent, line)))
                {
                    result.events.Add(statusEvent); onEvent?.Invoke(statusEvent);
                }
                if (!attacker.IsAlive) { AddLog(result, onEvent, $"{attacker.battleId} defeated"); statusEffects.RemoveForDead(attacker); continue; }
                if (statusEffects.ConsumeStun(attacker))
                {
                    AddLog(result, onEvent, $"{attacker.battleId} is stunned and skips the action");
                    onEvent?.Invoke(new BattlePhase1Event { phase = BattlePresentationPhase.SkillEffectApplied, turn = result.turn, target = attacker, skillEffectType = BattleSkillEffectType.Stun });
                    statusEffects.EndUnitTurn(attacker, result.turn, line => AddLog(result, onEvent, line));
                    continue;
                }

                List<ThoughtMapBattleUnit> enemies = attacker.team == "Player"
                    ? result.enemyUnits
                    : result.playerUnits;
                if (!enemies.Any(unit => unit.IsAlive))
                {
                    break;
                }

                ThoughtMapBattleUnit target = SelectWeightedTarget(attacker, enemies, result.turn);
                if (target == null)
                {
                    continue;
                }

                TriggerAssignedSkills(new[] { attacker }, "low_hp", result, onEvent);
                if (!target.IsAlive)
                {
                    target = SelectWeightedTarget(attacker, enemies, result.turn);
                    if (target == null) break;
                }
                GeneratedSkillDto actionSkill = FindActionSkill(attacker);
                if (actionSkill != null)
                {
                    BattleSkillResolution resolution = ResolveSkill(actionSkill, attacker, target, result, onEvent);
                    if (resolution.supported && resolution.events.Count > 0)
                    {
                        foreach (BattlePhase1Event skillEvent in resolution.events) { result.events.Add(skillEvent); onEvent?.Invoke(skillEvent); }
                        if (!target.IsAlive) { AddLog(result, onEvent, $"{target.battleId} defeated"); statusEffects.RemoveForDead(target); }
                        statusEffects.EndUnitTurn(attacker, result.turn, line => AddLog(result, onEvent, line));
                        if (!result.playerUnits.Any(unit => unit.IsAlive) || !result.enemyUnits.Any(unit => unit.IsAlive)) break;
                        continue;
                    }
                }
                bool magic = attacker.skillAttack > attacker.physicalAttack;
                int attack = statusEffects.EffectiveAttack(attacker, magic);
                int defense = statusEffects.EffectiveDefense(target, magic);
                int damage = statusEffects.AbsorbShield(target, Mathf.Max(1, attack - defense), line => AddLog(result, onEvent, line));

                AddLog(result, onEvent, $"{attacker.battleId} attacks {target.battleId}");
                target.hp = Mathf.Max(0, target.hp - damage);
                attacker.damageDone += damage;
                target.damageTaken += damage;
                target.hate += Mathf.Max(0.1f, damage / 30f);
                AddLog(result, onEvent, $"{target.battleId} takes {damage} damage");

                BattlePhase1Event battleEvent = new BattlePhase1Event
                {
                    turn = result.turn,
                    attacker = attacker,
                    target = target,
                    damage = damage,
                    magicAttack = magic,
                    defeated = !target.IsAlive,
                    logLine = string.Empty,
                };
                result.events.Add(battleEvent);
                onEvent?.Invoke(battleEvent);

                if (!target.IsAlive)
                {
                    AddLog(result, onEvent, $"{target.battleId} defeated");
                    statusEffects.RemoveForDead(target);
                }

                statusEffects.EndUnitTurn(attacker, result.turn, line => AddLog(result, onEvent, line));

                if (!result.playerUnits.Any(unit => unit.IsAlive) || !result.enemyUnits.Any(unit => unit.IsAlive))
                {
                    break;
                }
            }

            bool playerAlive = result.playerUnits.Any(unit => unit.IsAlive);
            bool enemyAlive = result.enemyUnits.Any(unit => unit.IsAlive);
            if (!playerAlive || !enemyAlive)
            {
                result.finished = true;
                result.playerWon = playerAlive && !enemyAlive;
                AddLog(result, onEvent, result.playerWon ? "Win" : "Lose");
                AddLog(result, onEvent, "Battle Finished");
                result.battleResultData = BuildBattleResultData(result);
                return result;
            }
        }

        AddLog(result, onEvent, "Battle stopped by safety limit");
        return result;
    }

    public IEnumerator RunCoroutine(
        IReadOnlyList<ThoughtMapBattleCardData> playerCards,
        IReadOnlyList<ThoughtMapBattleCardData> enemyCards,
        IReadOnlyList<ThoughtMapGridPosition> playerPositions,
        IReadOnlyList<ThoughtMapGridPosition> enemyPositions,
        Func<BattlePhase1Event, IEnumerator> presentEvent,
        Action<BattlePhase1Event> onLogEvent,
        Action<BattlePhase1Result> onComplete,
        IReadOnlyList<ThoughtMapBattlePreparedUnitData> playerPreparedUnits = null,
        IReadOnlyDictionary<string, List<GeneratedSkillDto>> assignedSkills = null,
        IReadOnlyDictionary<string, List<GeneratedSkillDto>> enemyAssignedSkills = null)
    {
        statusEffects = new BattleStatusEffectController();
        skillResolver = new BattleSkillResolver(statusEffects, random);
        BattlePhase1Result result = new BattlePhase1Result();
        result.playerUnits.AddRange(BuildTeam(playerCards, "Player", "P", playerPositions, 0));
        result.enemyUnits.AddRange(BuildTeam(enemyCards, "Enemy", "E", enemyPositions, 4));

        if (result.playerUnits.Count != 5 || result.enemyUnits.Count != 5)
        {
            AddLog(result, onLogEvent, "Battle aborted: Phase1 requires exactly 5 Player and 5 Enemy units.");
            onComplete?.Invoke(result);
            yield break;
        }
        if (!ApplyPreparedPlayerData(result.playerUnits, playerPreparedUnits, assignedSkills))
        {
            AddLog(result, onLogEvent, "Battle aborted: Battle Prep final status data is missing or incomplete.");
            onComplete?.Invoke(result);
            yield break;
        }
        ApplyAssignedSkills(result.enemyUnits, enemyAssignedSkills);
        BindStatusNotifications(result, onLogEvent);

        AddLog(result, onLogEvent, "Battle Started");
        int triggerEventStart = result.events.Count;
        TriggerAssignedSkills(result.playerUnits, "battle_start", result, onLogEvent);
        for (int index = triggerEventStart; index < result.events.Count; index++) yield return Present(presentEvent, result.events[index]);
        const int safetyTurnLimit = 10000;
        while (result.turn < safetyTurnLimit)
        {
            result.turn++;
            AddLog(result, onLogEvent, $"Turn {result.turn}");
            yield return Present(presentEvent, new BattlePhase1Event
            {
                phase = BattlePresentationPhase.TurnStarted,
                turn = result.turn,
                logLine = $"Turn {result.turn}",
            });
            triggerEventStart = result.events.Count;
            TriggerAssignedSkills(result.playerUnits.Concat(result.enemyUnits).Where(unit => unit.IsAlive), "turn_start", result, onLogEvent);
            for (int index = triggerEventStart; index < result.events.Count; index++) yield return Present(presentEvent, result.events[index]);

            List<ThoughtMapBattleUnit> order = BuildTurnOrder(result.playerUnits, result.enemyUnits);
            foreach (ThoughtMapBattleUnit attacker in order)
            {
                if (!attacker.IsAlive)
                {
                    continue;
                }
                foreach (BattlePhase1Event statusEvent in skillResolver.ProcessTurnStart(attacker, result.playerUnits.Concat(result.enemyUnits), result.turn, line => AddLog(result, onLogEvent, line)))
                {
                    result.events.Add(statusEvent); yield return Present(presentEvent, statusEvent);
                }
                if (!attacker.IsAlive)
                {
                    AddLog(result, onLogEvent, $"{attacker.battleId} defeated"); statusEffects.RemoveForDead(attacker);
                    yield return Present(presentEvent, new BattlePhase1Event { phase = BattlePresentationPhase.ActionFinished, turn = result.turn, target = attacker });
                    continue;
                }
                if (statusEffects.ConsumeStun(attacker))
                {
                    AddLog(result, onLogEvent, $"{attacker.battleId} is stunned and skips the action");
                    yield return Present(presentEvent, new BattlePhase1Event { phase = BattlePresentationPhase.SkillEffectApplied, turn = result.turn, target = attacker, skillEffectType = BattleSkillEffectType.Stun });
                    statusEffects.EndUnitTurn(attacker, result.turn, line => AddLog(result, onLogEvent, line));
                    continue;
                }
                List<ThoughtMapBattleUnit> enemies = attacker.team == "Player" ? result.enemyUnits : result.playerUnits;
                if (!enemies.Any(unit => unit.IsAlive))
                {
                    break;
                }

                ThoughtMapBattleUnit target = SelectWeightedTarget(attacker, enemies, result.turn);
                if (target == null)
                {
                    continue;
                }
                yield return Present(presentEvent, new BattlePhase1Event
                {
                    phase = BattlePresentationPhase.TargetSelected,
                    turn = result.turn,
                    attacker = attacker,
                    target = target,
                });

                triggerEventStart = result.events.Count;
                TriggerAssignedSkills(new[] { attacker }, "low_hp", result, onLogEvent);
                for (int index = triggerEventStart; index < result.events.Count; index++) yield return Present(presentEvent, result.events[index]);
                if (!target.IsAlive)
                {
                    target = SelectWeightedTarget(attacker, enemies, result.turn);
                    if (target == null) break;
                }
                GeneratedSkillDto actionSkill = FindActionSkill(attacker);
                if (actionSkill != null)
                {
                    BattleSkillResolution resolution = ResolveSkill(actionSkill, attacker, target, result, onLogEvent);
                    if (resolution.supported && resolution.events.Count > 0)
                    {
                        yield return Present(presentEvent, new BattlePhase1Event { phase = BattlePresentationPhase.SkillActivated, turn = result.turn, attacker = attacker, target = target, skillName = resolution.skillName });
                        foreach (BattlePhase1Event skillEvent in resolution.events) { result.events.Add(skillEvent); yield return Present(presentEvent, skillEvent); }
                        yield return Present(presentEvent, new BattlePhase1Event { phase = BattlePresentationPhase.HpUpdated, turn = result.turn, target = target, remainingHp = target.hp, maxHp = target.maxHp, defeated = !target.IsAlive });
                        if (!target.IsAlive) { AddLog(result, onLogEvent, $"{target.battleId} defeated"); statusEffects.RemoveForDead(target); }
                        yield return Present(presentEvent, new BattlePhase1Event { phase = BattlePresentationPhase.ActionFinished, turn = result.turn, attacker = attacker, target = target });
                        statusEffects.EndUnitTurn(attacker, result.turn, line => AddLog(result, onLogEvent, line));
                        if (!result.playerUnits.Any(unit => unit.IsAlive) || !result.enemyUnits.Any(unit => unit.IsAlive)) break;
                        continue;
                    }
                }
                bool magic = attacker.skillAttack > attacker.physicalAttack;
                int attack = statusEffects.EffectiveAttack(attacker, magic);
                int defense = statusEffects.EffectiveDefense(target, magic);
                int damage = statusEffects.AbsorbShield(target, Mathf.Max(1, attack - defense), line => AddLog(result, onLogEvent, line));

                AddLog(result, onLogEvent, $"{attacker.battleId} attacks {target.battleId}");
                yield return Present(presentEvent, new BattlePhase1Event
                {
                    phase = BattlePresentationPhase.AttackStarted,
                    turn = result.turn,
                    attacker = attacker,
                    target = target,
                    damage = damage,
                    magicAttack = magic,
                });

                target.hp = Mathf.Max(0, target.hp - damage);
                attacker.damageDone += damage;
                target.damageTaken += damage;
                target.hate += Mathf.Max(0.1f, damage / 30f);
                AddLog(result, onLogEvent, $"{target.battleId} takes {damage} damage");
                BattlePhase1Event battleEvent = new BattlePhase1Event
                {
                    phase = BattlePresentationPhase.DamageApplied,
                    turn = result.turn,
                    attacker = attacker,
                    target = target,
                    damage = damage,
                    remainingHp = target.hp,
                    maxHp = target.maxHp,
                    magicAttack = magic,
                    defeated = !target.IsAlive,
                    logLine = string.Empty,
                };
                result.events.Add(battleEvent);
                yield return Present(presentEvent, battleEvent);
                yield return Present(presentEvent, new BattlePhase1Event
                {
                    phase = BattlePresentationPhase.HpUpdated,
                    turn = result.turn,
                    attacker = attacker,
                    target = target,
                    damage = damage,
                    remainingHp = target.hp,
                    maxHp = target.maxHp,
                    defeated = !target.IsAlive,
                });

                if (!target.IsAlive)
                {
                    AddLog(result, onLogEvent, $"{target.battleId} defeated");
                    statusEffects.RemoveForDead(target);
                }
                yield return Present(presentEvent, new BattlePhase1Event
                {
                    phase = BattlePresentationPhase.ActionFinished,
                    turn = result.turn,
                    attacker = attacker,
                    target = target,
                });

                statusEffects.EndUnitTurn(attacker, result.turn, line => AddLog(result, onLogEvent, line));

                if (!result.playerUnits.Any(unit => unit.IsAlive) || !result.enemyUnits.Any(unit => unit.IsAlive))
                {
                    break;
                }
            }

            bool playerAlive = result.playerUnits.Any(unit => unit.IsAlive);
            bool enemyAlive = result.enemyUnits.Any(unit => unit.IsAlive);
            if (!playerAlive || !enemyAlive)
            {
                result.finished = true;
                result.playerWon = playerAlive && !enemyAlive;
                AddLog(result, onLogEvent, result.playerWon ? "Win" : "Lose");
                AddLog(result, onLogEvent, "Battle Finished");
                result.battleResultData = BuildBattleResultData(result);
                yield return Present(presentEvent, new BattlePhase1Event
                {
                    phase = BattlePresentationPhase.BattleFinished,
                    turn = result.turn,
                    playerWon = result.playerWon,
                    logLine = "Battle Finished",
                });
                onComplete?.Invoke(result);
                yield break;
            }
        }

        AddLog(result, onLogEvent, "Battle stopped by safety limit");
        onComplete?.Invoke(result);
    }

    private BattleResultData BuildBattleResultData(BattlePhase1Result result)
    {
        Dictionary<string, int> kills = result.events
            .Where(evt => evt != null && evt.defeated && evt.attacker != null)
            .GroupBy(evt => evt.attacker.battleId)
            .ToDictionary(group => group.Key, group => group.Count());
        Dictionary<string, int> skills = result.skillTriggers
            .Where(trigger => trigger != null && !string.IsNullOrWhiteSpace(trigger.unitId))
            .GroupBy(trigger => trigger.unitId)
            .ToDictionary(group => group.Key, group => group.Count());

        UnitBattleResult Convert(ThoughtMapBattleUnit unit)
        {
            int killCount = kills.TryGetValue(unit.battleId, out int foundKills) ? foundKills : 0;
            int skillCount = skills.TryGetValue(unit.battleId, out int foundSkills) ? foundSkills : 0;
            return new UnitBattleResult
            {
                unitId = unit.battleId,
                cardId = GetCardId(unit.card),
                cardName = unit.card == null ? "Unknown" : unit.card.cardName,
                damageDealt = unit.damageDone,
                damageTaken = unit.damageTaken,
                kills = killCount,
                skillCount = skillCount,
                survived = unit.IsAlive,
                mvpScore = unit.damageDone * resultScoreSettings.damageWeight
                    + killCount * resultScoreSettings.killWeight
                    + skillCount * resultScoreSettings.skillWeight,
            };
        }

        BattleResultData data = new BattleResultData
        {
            victory = result.playerWon,
            turnCount = result.turn,
            playerResults = result.playerUnits.Where(unit => unit != null).Select(Convert).ToList(),
            enemyResults = result.enemyUnits.Where(unit => unit != null).Select(Convert).ToList(),
            battleLog = new List<string>(result.logLines),
        };
        List<UnitBattleResult> all = data.playerResults.Concat(data.enemyResults).ToList();
        UnitBattleResult mvp = all.OrderByDescending(unit => unit.mvpScore).FirstOrDefault();
        data.mvpCardId = mvp == null ? string.Empty : mvp.cardId;
        data.mvpUnitId = mvp == null ? string.Empty : mvp.unitId;
        data.mvpScore = mvp == null ? 0f : mvp.mvpScore;
        data.statistics = new BattleStatistics
        {
            totalDamage = all.Sum(unit => unit.damageDealt),
            totalTurns = result.turn,
            totalSkills = all.Sum(unit => unit.skillCount),
            totalKills = all.Sum(unit => unit.kills),
        };
        return data;
    }

    private static IEnumerator Present(Func<BattlePhase1Event, IEnumerator> presenter, BattlePhase1Event battleEvent)
    {
        if (presenter != null)
        {
            yield return presenter(battleEvent);
        }
    }

    private List<ThoughtMapBattleUnit> BuildTeam(
        IReadOnlyList<ThoughtMapBattleCardData> cards,
        string team,
        string idPrefix,
        IReadOnlyList<ThoughtMapGridPosition> positions,
        int defaultY)
    {
        List<ThoughtMapBattleUnit> units = new List<ThoughtMapBattleUnit>();
        if (cards == null)
        {
            return units;
        }

        for (int index = 0; index < cards.Count && index < 5; index++)
        {
            ThoughtMapBattleCardData card = cards[index];
            if (card == null)
            {
                continue;
            }

            ThoughtMapGridPosition position = positions != null && index < positions.Count
                ? positions[index]
                : new ThoughtMapGridPosition(index, defaultY);
            ThoughtMapBattleUnit unit = new ThoughtMapBattleUnit(card, team, position)
            {
                battleId = $"{idPrefix}{index + 1}",
            };
            units.Add(unit);
        }
        return units;
    }

    private List<ThoughtMapBattleUnit> BuildTurnOrder(
        IEnumerable<ThoughtMapBattleUnit> playerUnits,
        IEnumerable<ThoughtMapBattleUnit> enemyUnits)
    {
        return playerUnits
            .Concat(enemyUnits)
            .Where(unit => unit != null && unit.IsAlive)
            .Select(unit => new { unit, tie = random.Next() })
            .OrderByDescending(entry => entry.unit.speed)
            .ThenBy(entry => entry.tie)
            .Select(entry => entry.unit)
            .ToList();
    }

    private ThoughtMapBattleUnit SelectWeightedTarget(
        ThoughtMapBattleUnit attacker,
        List<ThoughtMapBattleUnit> enemies,
        int turn)
    {
        List<ThoughtMapBattleUnit> living = enemies.Where(unit => unit != null && unit.IsAlive).ToList();
        if (living.Count == 0)
        {
            return null;
        }

        List<float> weights = living
            .Select(unit => Mathf.Max(0.0001f, hateCalculator.CalculateHate(attacker, unit, turn)))
            .ToList();
        double roll = random.NextDouble() * weights.Sum();
        for (int index = 0; index < living.Count; index++)
        {
            roll -= weights[index];
            if (roll <= 0d)
            {
                return living[index];
            }
        }
        return living[living.Count - 1];
    }

    private bool ApplyPreparedPlayerData(
        List<ThoughtMapBattleUnit> playerUnits,
        IReadOnlyList<ThoughtMapBattlePreparedUnitData> preparedUnits,
        IReadOnlyDictionary<string, List<GeneratedSkillDto>> assignedSkills)
    {
        if (preparedUnits == null || preparedUnits.Count != 5)
        {
            return false;
        }

        Dictionary<string, ThoughtMapBattlePreparedUnitData> byCardId = preparedUnits
            .Where(data => data != null && !string.IsNullOrWhiteSpace(data.cardId))
            .ToDictionary(data => data.cardId, data => data);
        foreach (ThoughtMapBattleUnit unit in playerUnits)
        {
            string cardId = GetCardId(unit.card);
            if (!byCardId.TryGetValue(cardId, out ThoughtMapBattlePreparedUnitData data))
            {
                return false;
            }

            unit.position = new ThoughtMapGridPosition(data.x, data.y);
            unit.maxHp = Mathf.Max(1, data.maxHp);
            unit.hp = unit.maxHp;
            unit.physicalAttack = Mathf.Max(0, data.physicalAttack);
            unit.skillAttack = Mathf.Max(0, data.skillAttack);
            unit.physicalDefense = Mathf.Max(0, data.physicalDefense);
            unit.skillDefense = Mathf.Max(0, data.skillDefense);
            unit.speed = Mathf.Max(0, data.speed);
            unit.preparedResonanceModifier = data.resonanceModifier;
            unit.preparedHateMultiplier = Mathf.Max(0f, data.hateMultiplier);
            unit.skillHateModifier = unit.preparedHateMultiplier;
            if (assignedSkills != null && assignedSkills.TryGetValue(cardId, out List<GeneratedSkillDto> skills))
            {
                unit.assignedGeneratedSkills.AddRange(skills.Where(skill => skill != null));
            }
        }
        return true;
    }

    private static void ApplyAssignedSkills(
        IEnumerable<ThoughtMapBattleUnit> units,
        IReadOnlyDictionary<string, List<GeneratedSkillDto>> assignedSkills)
    {
        if (units == null || assignedSkills == null) return;
        foreach (ThoughtMapBattleUnit unit in units.Where(unit => unit != null))
        {
            string cardId = GetCardId(unit.card);
            if (assignedSkills.TryGetValue(cardId, out List<GeneratedSkillDto> skills) && skills != null)
                unit.assignedGeneratedSkills.AddRange(skills.Where(skill => skill != null));
        }
    }

    private void BindStatusNotifications(BattlePhase1Result result, Action<BattlePhase1Event> onEvent)
    {
        statusEffects.Changed += unitId =>
        {
            ThoughtMapBattleUnit unit = result.playerUnits.Concat(result.enemyUnits).FirstOrDefault(candidate => candidate.battleId == unitId);
            onEvent?.Invoke(new BattlePhase1Event { phase = BattlePresentationPhase.StatusChanged, turn = result.turn, target = unit });
        };
        foreach (ThoughtMapBattleUnit unit in result.playerUnits.Concat(result.enemyUnits))
            onEvent?.Invoke(new BattlePhase1Event { phase = BattlePresentationPhase.StatusChanged, turn = result.turn, target = unit });
    }

    public IReadOnlyList<ActiveStatusEffect> GetActiveEffects(string unitId) => statusEffects == null
        ? Array.Empty<ActiveStatusEffect>()
        : statusEffects.ActiveEffects.Where(effect => effect.targetUnitId == unitId).ToList();
    public int GetShield(ThoughtMapBattleUnit unit) => statusEffects == null ? 0 : statusEffects.Shield(unit);
    public int GetEffectiveAttack(ThoughtMapBattleUnit unit, bool magic) => statusEffects == null ? (magic ? unit.skillAttack : unit.physicalAttack) : statusEffects.EffectiveAttack(unit, magic);
    public int GetEffectiveDefense(ThoughtMapBattleUnit unit, bool magic) => statusEffects == null ? (magic ? unit.skillDefense : unit.physicalDefense) : statusEffects.EffectiveDefense(unit, magic);
    public float GetTauntMultiplier(ThoughtMapBattleUnit unit) => statusEffects == null ? 1f : statusEffects.TauntMultiplier(unit);

    private void TriggerAssignedSkills(
        IEnumerable<ThoughtMapBattleUnit> units,
        string trigger,
        BattlePhase1Result result,
        Action<BattlePhase1Event> onEvent)
    {
        foreach (ThoughtMapBattleUnit unit in units)
        {
            if (unit == null || !unit.IsAlive)
            {
                continue;
            }
            if (trigger == "low_hp" && unit.hp > Mathf.CeilToInt(unit.maxHp * 0.3f))
            {
                continue;
            }
            foreach (GeneratedSkillDto skill in unit.assignedGeneratedSkills.Where(skill => skill.trigger == trigger))
            {
                AddLog(result, onEvent, $"{unit.battleId} skill trigger: {skill.skill_id} ({trigger})");
                BattlePhase1Event activationEvent = new BattlePhase1Event
                {
                    phase = BattlePresentationPhase.SkillActivated,
                    turn = result.turn,
                    attacker = unit,
                    skillName = skill.DisplayName,
                };
                result.events.Add(activationEvent);
                onEvent?.Invoke(activationEvent);
                List<ThoughtMapBattleUnit> opponents = unit.team == "Player" ? result.enemyUnits : result.playerUnits;
                ThoughtMapBattleUnit target = SelectWeightedTarget(unit, opponents, result.turn);
                BattleSkillResolution resolution = ResolveSkill(skill, unit, target, result, onEvent);
                foreach (BattlePhase1Event skillEvent in resolution.events)
                {
                    result.events.Add(skillEvent);
                    onEvent?.Invoke(skillEvent);
                }
            }
        }
    }

    private GeneratedSkillDto FindActionSkill(ThoughtMapBattleUnit unit)
    {
        if (unit == null) return null;
        return unit.assignedGeneratedSkills.FirstOrDefault(skill =>
            skill != null && (skill.trigger == "manual" || skill.trigger == "on_attack" || skill.trigger == "attack"));
    }

    private BattleSkillResolution ResolveSkill(
        GeneratedSkillDto skill,
        ThoughtMapBattleUnit source,
        ThoughtMapBattleUnit preferredTarget,
        BattlePhase1Result result,
        Action<BattlePhase1Event> onEvent)
    {
        List<ThoughtMapBattleUnit> allies = source.team == "Player" ? result.playerUnits : result.enemyUnits;
        List<ThoughtMapBattleUnit> enemies = source.team == "Player" ? result.enemyUnits : result.playerUnits;
        BattleSkillResolution resolution = skillResolver.Resolve(
            skill, source, preferredTarget, allies, enemies, result.turn,
            line => AddLog(result, onEvent, line));
        if (resolution.used)
        {
            result.skillTriggers.Add(new BattleGeneratedSkillTrigger
            {
                turn = result.turn,
                unitId = source.battleId,
                skillId = skill.skill_id,
                trigger = skill.trigger,
            });
        }
        return resolution;
    }

    private static string GetCardId(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return string.Empty;
        }
        return !string.IsNullOrWhiteSpace(card.cardId) ? card.cardId : card.docId;
    }

    private static void AddLog(BattlePhase1Result result, Action<BattlePhase1Event> onEvent, string line)
    {
        result.logLines.Add(line);
        onEvent?.Invoke(new BattlePhase1Event { turn = result.turn, logLine = line });
    }
}

public sealed class BattlePhase1Result
{
    public readonly List<ThoughtMapBattleUnit> playerUnits = new List<ThoughtMapBattleUnit>();
    public readonly List<ThoughtMapBattleUnit> enemyUnits = new List<ThoughtMapBattleUnit>();
    public readonly List<BattlePhase1Event> events = new List<BattlePhase1Event>();
    public readonly List<BattleGeneratedSkillTrigger> skillTriggers = new List<BattleGeneratedSkillTrigger>();
    public readonly List<string> logLines = new List<string>();
    public int turn;
    public bool finished;
    public bool playerWon;
    public BattleResultData battleResultData;
}

public sealed class BattleGeneratedSkillTrigger
{
    public int turn;
    public string unitId;
    public string skillId;
    public string trigger;
}

public sealed class BattlePhase1Event
{
    public BattlePresentationPhase phase;
    public int turn;
    public ThoughtMapBattleUnit attacker;
    public ThoughtMapBattleUnit target;
    public int damage;
    public bool magicAttack;
    public bool defeated;
    public bool playerWon;
    public int remainingHp;
    public int maxHp;
    public string skillName;
    public BattleSkillEffectType skillEffectType;
    public string logLine;
}

public enum BattlePresentationPhase
{
    None,
    TurnStarted,
    TargetSelected,
    AttackStarted,
    DamageApplied,
    HpUpdated,
    ActionFinished,
    BattleFinished,
    SkillActivated,
    SkillEffectApplied,
    StatusChanged,
}
