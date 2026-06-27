using System;
using System.IO;
using System.Linq;

namespace Lufia2AutoTracker.Helper.Core
{
    internal static class SelfTest
    {
        public static int Run(string? dataDirectory)
        {
            int failures = 0;

            failures += Check("valid WRAM fixture is strong", () =>
            {
                byte[] snapshot = CreateValidSnapshot();
                int score = MemoryScanner.ScoreWramSnapshot(snapshot, out int gold);
                return score >= 80 && gold == 12345;
            });

            failures += Check("duplicate party members weaken WRAM fixture", () =>
            {
                byte[] snapshot = CreateValidSnapshot();
                snapshot[0x2D90] = snapshot[0x2D8F];
                int score = MemoryScanner.ScoreWramSnapshot(snapshot, out _);
                return score < 80;
            });

            failures += Check("dynamic profile uses canonical WRAM offsets", () =>
            {
                IntPtr wram = (IntPtr)0x12345000;
                MemoryProfile profile = MemoryProfile.CreateFromOffsets(wram, IntPtr.Zero);
                return profile.ScannedWramBase == wram &&
                       profile.Gold == 0x2D9E &&
                       profile.InventoryStart == 0x2DA1 &&
                       profile.ScannedRomBase == IntPtr.Zero;
            });

            failures += Check("emulator discovery aliases are registered", () =>
                ProcessScanner.IsKnownEmulatorName("snes9x") &&
                ProcessScanner.IsKnownEmulatorName("bsnes") &&
                ProcessScanner.IsKnownEmulatorName("ares") &&
                ProcessScanner.IsKnownEmulatorName("EmuHawk"));

            failures += Check("configured emulator profiles resolve", () =>
            {
                string? path = ConfigLoader.ResolveConfigPath(dataDirectory);
                var config = ConfigLoader.Load(dataDirectory);
                return path != null && File.Exists(path) && config != null && config.Values.Sum(list => list.Count) >= 2;
            });

            failures += Check("dungeon mapping loads", () =>
                Program.LoadDungeons(dataDirectory, "dungeon_flags_snes9x.json") && GameData.Dungeons.Count > 0);

            Console.WriteLine(failures == 0
                ? "[SelfTest] All checks passed."
                : $"[SelfTest] {failures} check(s) failed.");
            return failures == 0 ? 0 : 1;
        }

        private static byte[] CreateValidSnapshot()
        {
            byte[] snapshot = new byte[0x3801];
            snapshot[0x2D9E] = 0x39;
            snapshot[0x2D9F] = 0x30;
            snapshot[0x2DA0] = 0x00;
            snapshot[0x2D8F] = 0x00;
            snapshot[0x2D90] = 0x01;
            snapshot[0x2D91] = 0xFF;
            snapshot[0x2D92] = 0xFF;
            snapshot[0x2CF5] = 0x00;
            return snapshot;
        }

        private static int Check(string name, Func<bool> test)
        {
            try
            {
                bool passed = test();
                Console.WriteLine($"[SelfTest] {(passed ? "PASS" : "FAIL")}: {name}");
                return passed ? 0 : 1;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[SelfTest] FAIL: {name}: {ex.Message}");
                return 1;
            }
        }
    }
}
