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
- `DebugBattlePrep`

`DebugBattlePrep` contains:

- `ThoughtMapBattleMvpController`
- `ThoughtMapBattleMvpPanelView`

MVP behavior:

- The scene is a debug/verification preparation screen.
- `Simulate Battle` runs the current lightweight preview simulation.
- `Reset / Reposition` remains available for placement/debug checks.
- This scene is not the formal battle presentation scene.

Do not add `SearchHeaderV2`, `ResultListV2`, or `ThoughtMapDetailPanelV2` to `BattlePrepScene`.

## ProductBattlePrepScene

Create the product-facing preparation mock from Unity Editor:

```text
Tools > Source of Thought > Create Product Battle Prep Prefabs
Tools > Source of Thought > Create ProductBattlePrepScene
```

The generated scene should contain:

- `Main Camera`
- `ProductBattlePrepCanvas`
- `EventSystem`
- `ProductBattlePrepPanel`

Product mock behavior:

- `Load Cards` reads `Assets/StreamingAssets/cards.csv` or an assigned TextAsset.
- The deck shows up to ten large card views.
- The formation board accepts up to five deployed cards.
- `Simulate Battle` is only a formation/preview check.
- `Save Deck` writes `deck.json` to `Application.persistentDataPath`.
- `Start Battle` saves `deck.json`, then loads the future `BattleScene`.

Product mock assets:

- `Assets/Prefabs/ProductBattleCardPrefab.prefab`
- `Assets/Prefabs/ProductBattleGridCellPrefab.prefab`
- `Assets/Sprites/placeholder_card_art.png`
- `Assets/Sprites/placeholder_attribute_icon.png`

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
- a future battle presentation root

`BattleScene` is reserved for future battle execution only. It should load saved `deck.json` and show the battle presentation/result. Do not add card selection, deck-building, placement editing, Reset/Reposition, or simulation debug logs to `BattleScene`.

Current card selection, 5x5 placement, deck saving, and preview/simulation UI belongs in `BattlePrepScene` or `ProductBattlePrepScene`.

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
