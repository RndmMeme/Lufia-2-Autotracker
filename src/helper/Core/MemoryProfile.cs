using System;
using System.Collections.Generic;

namespace Lufia2AutoTracker.Helper.Core
{
    public sealed class MemoryRootHint
    {
        public string Name { get; init; } = string.Empty;
        public string ProcessName { get; init; } = string.Empty;
        public int GoldProcessOffset { get; init; }

        public IntPtr ResolveWramRoot(IntPtr processBase) =>
            (IntPtr)((long)processBase + GoldProcessOffset - Lufia2MemoryMap.Wram.Gold);
    }

    /// <summary>
    /// Verified host roots for one running game instance. All consumers resolve
    /// canonical game offsets through these roots.
    /// </summary>
    public sealed class MemoryProfile
    {
        public string Name { get; init; } = string.Empty;
        public string ProcessName { get; init; } = string.Empty;
        public IntPtr WramBase { get; init; }
        public IntPtr RomBase { get; init; }

        public bool HasWram => WramBase != IntPtr.Zero;
        public bool HasRom => RomBase != IntPtr.Zero;

        public IntPtr ResolveWram(int offset)
        {
            if (!HasWram) throw new InvalidOperationException("WRAM root is unavailable.");
            if (offset < 0 || offset >= Lufia2MemoryMap.Wram.Size)
                throw new ArgumentOutOfRangeException(nameof(offset));
            return (IntPtr)((long)WramBase + offset);
        }

        public IntPtr ResolveRom(int offset)
        {
            if (!HasRom) throw new InvalidOperationException("ROM root is unavailable.");
            if (offset < 0) throw new ArgumentOutOfRangeException(nameof(offset));
            return (IntPtr)((long)RomBase + offset);
        }

        public static MemoryProfile CreateFromRoots(
            IntPtr wramBase,
            IntPtr romBase,
            string processName = "Scanned",
            string? name = null) => new MemoryProfile {
                Name = name ?? (romBase != IntPtr.Zero
                    ? "Canonical WRAM + ROM profile"
                    : "Canonical WRAM-only profile"),
                ProcessName = processName,
                WramBase = wramBase,
                RomBase = romBase
            };

        public static IReadOnlyList<MemoryRootHint> BuiltInRootHints { get; } = new[] {
            new MemoryRootHint {
                Name = "Snes9x 1.62.3 standard root hint",
                ProcessName = "snes9x-x64",
                GoldProcessOffset = 0xA32D9E
            },
            new MemoryRootHint {
                Name = "Snes9x 1.62.3 NWA root hint",
                ProcessName = "snes9x-x64",
                GoldProcessOffset = 0xE2CF52
            },
            new MemoryRootHint {
                Name = "Snes9x-compatible NWA root hint",
                ProcessName = "snes9x",
                GoldProcessOffset = 0xE2CF52
            }
        };
    }
}
