# Canonical Memory Architecture

Starting with v1.4.7, the tracker separates game addresses from emulator host addresses.

## Address model

The SNES exposes 128 KiB of WRAM at bus addresses `$7E0000-$7FFFFF`. The helper first locates the start of that linear WRAM image inside the emulator process. Every game read then uses:

```text
host address = detected WRAM root + canonical WRAM offset
```

For example, gold is always WRAM offset `0x2D9E`, equivalent to SNES bus address `$7E2D9E`:

| Live emulator layout | Detected WRAM root | Gold host address |
|---|---:|---:|
| Snes9x 1.62.3 | `0x140A30000` | root + `0x2D9E` |
| Snes9x 1.62.3-nwa | `0x140E2A1B4` | root + `0x2D9E` |
| bsnes-plus v05 | `0x645FA6C` | root + `0x2D9E` |

The host roots differ; the game offset does not.

## Sources of truth

- `src/helper/Core/Lufia2MemoryMap.cs` contains canonical WRAM and verified ROM offsets.
- `src/data/emulator_root_hints.json` contains optional historical host offsets used only to reconstruct a WRAM root if dynamic scanning fails.
- `src/data/emulator_addresses.json` is retained as archival reference and is not consumed by the v1.4.7 runtime.

No inventory, party, capsule, dungeon, scenario, transport, or position reader uses an emulator-specific host address.

## Root discovery

1. Find candidate emulator processes by executable alias.
2. Derive possible WRAM roots from game anchors or structural scanning.
3. Validate gold, party structure, transport state, and inventory shape.
4. Locate ROM candidates from internal game-title signatures.
5. Accept a ROM root only after validating the capsule sprite table.
6. If scanning fails, reconstruct a candidate WRAM root from one configured host anchor and validate it before use.

WRAM-only attachment remains valid. ROM-dependent features are disabled when no ROM root passes validation.

## Adding future addresses

Record either:

- a WRAM offset from the `$7E0000` WRAM base, or
- the canonical SNES bus address, converted with `Lufia2MemoryMap.Wram.FromSnesAddress`.

Do not add Cheat Engine host addresses to the canonical map. Host addresses belong only in optional root hints and must identify which canonical field they anchor.

ROM entries are stored as offsets from a verified headerless ROM root. ROM revisions or randomizer builds that relocate data should receive an explicit ROM-layout profile rather than emulator-specific addresses.
