# Unity Scenes

This folder is reserved for Unity scene assets.

## Fixed Scene Roles

Keep Source of Thought screens separated by responsibility:

1. `InputRegisterScene`
   - User work input.
   - Embedding generation.
   - User-folder save.
   - DB registration request.
2. `SearchCollectScene` or the current `ThoughtMapMain`
   - Similarity search from embeddings or user-folder data.
   - Search result download.
   - Save collected results to the user folder.
   - Not a card-selection or deck-building screen.
3. `BattlePrepScene`
   - Select saved works.
   - Generate cards and skills.
   - Configure placement and skill allocation.
   - Save card, skill, and placement configurations.
4. `BattleScene`
   - Execute battle.
   - Display battle result.

Shared data across scenes is limited to saved-folder data, embeddings, and work metadata.

## BattlePrepScene

Create the standalone battle-preparation scene from Unity Editor:

```text
Tools > Source of Thought > Create BattlePrepScene
```

The generated scene should contain:

- `Main Camera`
- `BattlePrepCanvas`
- `EventSystem`
- `SourceOfThoughtBattlePrep`

`SourceOfThoughtBattlePrep` contains:

- `ThoughtMapBattlePrepController`
- `ThoughtMapBattlePrepPanelView`

MVP behavior:

- `Generate Cards` reads `Assets/StreamingAssets/cards.csv` or an assigned TextAsset.
- `Deck Slots 10` are auto-filled from the first ten cards.
- `Deploy Slots 5` are auto-filled from the first five deck cards.
- `5x5 Placement Preview` uses fixed MVP placement.
- `Save Deck` writes `deck.json` to `Application.persistentDataPath`.
- `Start Battle` saves `deck.json`, then loads `BattleScene`.

Do not add `SearchHeaderV2`, `ResultListV2`, or `ThoughtMapDetailPanelV2` to `BattlePrepScene`.

## BattleScene

Create the standalone battle scene from Unity Editor:

```text
Tools > Source of Thought > Create BattleScene
```

The generated scene should contain only the Battle UI:

- `Main Camera`
- `BattleCanvas`
- `EventSystem`
- `SourceOfThoughtBattle`

Battle UI is built from game-style view components:

- Player and Enemy deck cards use `ThoughtMapBattleCardView`.
- The 5x5 board uses `ThoughtMapBattleGridCellView`.
- Battle Log is the only scrolling text log.
- Battle Summary uses `ThoughtMapBattleSummaryView`.
- `ThoughtMapBattleMvpController` can use assigned card/cell prefabs, or create fallback runtime views if no prefabs are assigned.

BattleScene MVP controls:

- Click a Player Deck card to select it.
- Click a lower Player-side grid cell to place the selected card.
- Click an already placed Player cell to remove that placement.
- Press `Start Battle` to lock placement and run the simulation.
- Press `Reset / Reposition` to unlock and rebuild the default placement after a battle.

Do not add `SearchHeaderV2`, `ResultListV2`, or `ThoughtMapDetailPanelV2` to `BattleScene`.

Do not add card selection or deck-building UI to `SearchCollectScene`. Those belong in `BattlePrepScene`.

## Cleaning ThoughtMapMain

`ThoughtMapMain` should remain Search/Collect only.

If Battle objects were previously added to `ThoughtMapMain`, open that scene and run:

```text
Tools > Source of Thought > Clean Battle UI From Current Search Scene
```

The cleanup removes Battle-only objects and the old same-scene menu controller from the active non-Battle scene. It does not run when `BattleScene` is the active scene.

After cleanup, `ThoughtMapMain` should not contain:

- `SourceOfThoughtBattle`
- `ThoughtMapBattleMVP`
- `Battle MVP`
- `Start Battle`
- `Hide Battle UI`
- `ThoughtMapBattleMvpController`
- `ThoughtMapBattleMvpPanelView`
