# Emulator Compatibility

Compatibility in v1.4.7 is determined by validated memory content, not by the executable name alone. Process names are used only to find candidates. Every successful attachment uses the same canonical Lufia II memory map.

## Live verification matrix

| Emulator | Process observed | WRAM | ROM features | State payload | Verified |
|---|---|---:|---:|---:|---|
| Snes9x 1.62.3 | `snes9x-x64` | Yes | Yes | Yes | 2026-06-27 |
| Snes9x 1.62.3-nwa | `snes9x-x64` | Yes | Yes | Yes | 2026-06-27 |
| bsnes-plus v05 | `bsnes` | Yes | Yes | Yes | 2026-06-27 |

The bsnes executable name can vary by build. `snes9x`, `snes9x-x64`, and `bsnes` are all treated as candidate names, but attachment still requires the same WRAM validation.

## Compatibility levels

- **WRAM validated:** inventory, characters, capsules, scenario items, cleared locations, and player position are available.
- **WRAM + ROM validated:** capsule sprite metadata is additionally available. Spoiler-log discovery is a separate signature scan and does not depend on the ROM root.
- **Candidate only:** the executable is recognized, but that emulator/version has not yet passed a live state-payload test.

Current candidate-only names include RetroArch, Mesen/Mesen-S, higan, ares, and BizHawk/EmuHawk.

## Reproducing a live check

Start the emulator, load Lufia II into gameplay, and run:

```powershell
python tools/verify_emulator.py
```

If several emulators are running, isolate one process:

```powershell
python tools/verify_emulator.py --pid <PID>
```

A successful check ends with an `attached` status and a state summary. The harness performs read-only process-memory access.

Use `--root-hints-only` with standard or NWA Snes9x to verify that the single-anchor fallback reconstructs the canonical WRAM root without dynamic scanning.
