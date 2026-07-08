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

Create the product battle-preparation scene from Unity Editor:

```text
Tools > Source of Thought > Create Product Battle UI Prefabs
Tools > Source of Thought > Create BattlePrepScene
```

The generated scene should contain:

- `Main Camera`
- `ProductBattlePrepCanvas`
- `EventSystem`
- `ProductBattlePrepPanel`

`ProductBattlePrepPanel` contains:

- `ProductBattlePrepPanelView`
- editable Card List, Deck, Card Detail, Formation Grid, and Debug Log panels

Behavior:

- Card list/deck/grid visuals are Prefab/Scene based.
- `Load Cards` reads `Assets/StreamingAssets/cards.csv` or an assigned TextAsset.
- Select a deck card and place up to five cards on the 5x5 formation board.
- `Simulate Battle` is only a preparation preview.
- `Save Deck` writes `deck.json` to `Application.persistentDataPath`.
- `Start Battle` saves `deck.json`, then loads `BattleScene`.

Do not add `SearchHeaderV2`, `ResultListV2`, or `ThoughtMapDetailPanelV2` to `BattlePrepScene`.

## DebugBattlePrepScene

The old verification UI is kept as DebugBattlePrep, outside the product route:

```text
Tools > Source of Thought > Create DebugBattlePrepScene
```

This scene may use `ThoughtMapBattleMvpPanelView` and runtime debug UI. It is not the production Battle Prep screen.

## Product Prefabs

Create or refresh editable product prefabs:

```text
Tools > Source of Thought > Create Product Battle UI Prefabs
```

Expected product prefabs:

- `CardView prefab`: `Assets/Prefabs/ProductBattleCardPrefab.prefab`
- `GridCell prefab`: `Assets/Prefabs/ProductBattleGridCellPrefab.prefab`
- `AttributeIcon prefab`: `Assets/Prefabs/AttributeIconPrefab.prefab`
- `SkillIcon prefab`: `Assets/Prefabs/SkillIconPrefab.prefab`
- `CardDetailPanel prefab`: `Assets/Prefabs/CardDetailPanel.prefab`
- `DeckListPanel prefab`: `Assets/Prefabs/DeckListPanel.prefab`
- `FormationGrid prefab`: `Assets/Prefabs/FormationGrid.prefab`
- `BattleField prefab`: `Assets/Prefabs/BattleField.prefab`
- `BattleUnitCard prefab`: `Assets/Prefabs/BattleUnitCard.prefab`
- `BattleLogPanel prefab`: `Assets/Prefabs/BattleLogPanel.prefab`
- `ProductBattlePrepCanvas.prefab`
- `ProductBattleCanvas.prefab`

Product C# components update text/images and handle clicks. Adjust layout, image assignment, margins, and card frame design in the Prefab/Scene Inspector.

Image setup:

- Put card illustrations in `Assets/Sprites/Cards`.
- Put attribute icons in `Assets/Sprites/Icons`.
- Set imported PNGs to `Texture Type = Sprite (2D and UI)`.
- Regenerate product prefabs, or assign images manually in `Card Art Pool` and `Attribute Sprites`.

Display responsibilities:

- `ProductBattleCardPrefab` shows art, attribute icon, card name, attribute, HP, ATK, DEF, EN, skill, rarity, and placed/selected state.
- `ProductBattleGridCellPrefab` shows placed cards as compact card visuals, not plain text only.
- `CardDetailPanel.prefab` shows the selected card with a large art image and parameter texts.

## BattleScene

Create the formal battle-display scene from Unity Editor:

```text
Tools > Source of Thought > Create BattleScene
```

The generated scene should contain only the Battle UI:

- `Main Camera`
- `BattleCanvas`
- `EventSystem`
- `ProductBattleCanvas`
- `ProductBattleSceneRoot`

`BattleScene` loads saved `deck.json` and displays Player cards in the near board area and Enemy cards in the far board area. Do not add card selection, deck-building, placement editing, Reset/Reposition, or simulation debug logs to `BattleScene`.

Current card selection, 5x5 placement, deck saving, and preview/simulation UI belongs in `BattlePrepScene`.

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
