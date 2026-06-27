using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

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
                snapshot[Lufia2MemoryMap.Wram.PartyStart + 1] =
                    snapshot[Lufia2MemoryMap.Wram.PartyStart];
                int score = MemoryScanner.ScoreWramSnapshot(snapshot, out _);
                return score < 80;
            });

            failures += Check("memory profile resolves canonical roots", () =>
            {
                IntPtr wram = (IntPtr)0x12345000;
                MemoryProfile profile = MemoryProfile.CreateFromRoots(wram, IntPtr.Zero);
                return profile.WramBase == wram &&
                       profile.ResolveWram(Lufia2MemoryMap.Wram.Gold) ==
                           (IntPtr)((long)wram + Lufia2MemoryMap.Wram.Gold) &&
                       !profile.HasRom;
            });

            failures += Check("legacy hints reconstruct the same canonical WRAM root", () =>
            {
                IntPtr processBase = new IntPtr(0x140000000L);
                var standard = new MemoryRootHint { GoldProcessOffset = 0xA32D9E };
                var nwa = new MemoryRootHint { GoldProcessOffset = 0xE2CF52 };
                IntPtr standardRoot = standard.ResolveWramRoot(processBase);
                IntPtr nwaRoot = nwa.ResolveWramRoot(processBase);
                return standardRoot == (IntPtr)((long)processBase + 0xA30000) &&
                       nwaRoot == (IntPtr)((long)processBase + 0xE2A1B4) &&
                       (long)standardRoot + Lufia2MemoryMap.Wram.Gold == (long)processBase + 0xA32D9E &&
                       (long)nwaRoot + Lufia2MemoryMap.Wram.Gold == (long)processBase + 0xE2CF52;
            });

            failures += Check("SNES WRAM addresses round-trip through canonical offsets", () =>
            {
                int busAddress = 0x7E2D9E;
                int offset = Lufia2MemoryMap.Wram.FromSnesAddress(busAddress);
                return offset == Lufia2MemoryMap.Wram.Gold &&
                       Lufia2MemoryMap.Wram.ToSnesAddress(offset) == busAddress;
            });

            failures += Check("emulator discovery aliases are registered", () =>
                ProcessScanner.IsKnownEmulatorName("snes9x") &&
                ProcessScanner.IsKnownEmulatorName("bsnes") &&
                ProcessScanner.IsKnownEmulatorName("ares") &&
                ProcessScanner.IsKnownEmulatorName("EmuHawk"));

            failures += Check("configured emulator root hints resolve", () =>
            {
                string? path = ConfigLoader.ResolveConfigPath(dataDirectory);
                var config = ConfigLoader.Load(dataDirectory);
                return path != null && File.Exists(path) && config != null && config.root_hints.Count >= 2;
            });

            failures += Check("source-generated JSON preserves tracker protocol", () =>
            {
                string stateJson = TrackerClient.SerializeState(new GameState {
                    Inventory = new List<string> { "Arrow" },
                    PlayerX = 123,
                    TransportMode = "walk"
                });
                using JsonDocument state = JsonDocument.Parse(stateJson);

                string statusJson = TrackerClient.SerializeStatus(new TrackerStatusEnvelope {
                    Status = new TrackerStatus {
                        State = "attached",
                        Message = "ready",
                        Process = "snes9x-x64"
                    }
                });
                using JsonDocument status = JsonDocument.Parse(statusJson);
                JsonElement statusBody = status.RootElement.GetProperty("tracker_status");

                return state.RootElement.GetProperty("inventory")[0].GetString() == "Arrow" &&
                       state.RootElement.GetProperty("player_x").GetInt32() == 123 &&
                       statusBody.GetProperty("state").GetString() == "attached" &&
                       statusBody.GetProperty("process").GetString() == "snes9x-x64";
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
            byte[] snapshot = new byte[Lufia2MemoryMap.Wram.ShipYHigh + 1];
            snapshot[Lufia2MemoryMap.Wram.Gold] = 0x39;
            snapshot[Lufia2MemoryMap.Wram.Gold + 1] = 0x30;
            snapshot[Lufia2MemoryMap.Wram.Gold + 2] = 0x00;
            snapshot[Lufia2MemoryMap.Wram.PartyStart] = 0x00;
            snapshot[Lufia2MemoryMap.Wram.PartyStart + 1] = 0x01;
            snapshot[Lufia2MemoryMap.Wram.PartyStart + 2] = 0xFF;
            snapshot[Lufia2MemoryMap.Wram.PartyStart + 3] = 0xFF;
            snapshot[Lufia2MemoryMap.Wram.Transport] = 0x00;
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
