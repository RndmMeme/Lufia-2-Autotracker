# Tracker data files

- `emulator_root_hints.json`: optional process-relative anchors used to reconstruct and validate a WRAM root when dynamic scanning fails.
- `emulator_addresses.json`: legacy curated host-address table retained for reference; v1.4.7 does not load it.
- `dungeon_flags_*.json`: dungeon flag descriptions. Their original host-address keys are normalized to offsets when loaded.
- Remaining JSON files describe tracker items, locations, layouts, shops, and sprites.

New game-memory fields belong in `src/helper/Core/Lufia2MemoryMap.cs` as canonical WRAM or ROM offsets, not in an emulator-specific address table.
