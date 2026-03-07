using System;
using System.Diagnostics;
using System.Threading;
using System.Linq;
using System.Collections.Generic;
using Lufia2AutoTracker.Helper.Core;
using Lufia2AutoTracker.Helper.Utils;
using System.IO;
using System.Text.Json;

namespace Lufia2AutoTracker.Helper
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Lufia 2 Auto Tracker Helper v1.4");
            
            var client = new TrackerClient();
            client.Connect();
            client.StartListening();
            
            var scanner = new ProcessScanner();
            DataReaders reader = null;
            GameState lastState = null;
            Process process = null;
            MemoryProfile currentProfile = null;
            
            // Spoiler Log Cache (only read once per session usually)
            List<Dictionary<string, string>> cachedSpoilerLog = null;
            int _spoilerAttemptCount = 0;

            client.CommandReceived += (cmd) => {
                if (cmd.Contains("RESCAN")) {
                    Console.WriteLine("RESCAN Requested: Resetting process and cache...");
                    cachedSpoilerLog = null;
                    _spoilerAttemptCount = 0;
                    process = null; // Forces re-scanning for emulator and WRAM offset
                }
            };

            while (true)
            {
                try
                {
                    if (process == null || process.HasExited)
                    {
                        process = ProcessScanner.FindEmulatorProcess();
                        if (process != null)
                        {
                            Console.WriteLine($"Found Emulator: {process.ProcessName} (PID: {process.Id})");
                            
                            // Initialize Variables
                            IntPtr baseAddress = IntPtr.Zero;
                            IntPtr spoilerAddress = IntPtr.Zero;

                            // 1. Scan WRAM First (Anchors: SSelan, AArty, etc.)
                            Console.WriteLine("Initiating Dual Scan (ROM + WRAM)...");
                            
                            List<WramCandidate> wramCandidates = MemoryScanner.ScanForWram(process);
                            IntPtr? wramPtr = null;

                            // Filter Strong Candidates (Gold > 0)
                            var strongCandidates = wramCandidates.Where(c => c.IsStrong).ToList();
                            Console.WriteLine($"Found {strongCandidates.Count} STRONG candidates (Gold > 0).");

                            if (strongCandidates.Count > 0)
                            {
                                // Log the candidates for debugging
                                foreach (var c in strongCandidates.Take(20))
                                {
                                    // Console.WriteLine($"  - Addr: 0x{c.Address.ToString("X")}\tGold: {c.Gold}\tScore: {c.Score}");
                                }
                                
                                // Best candidate is already first (sorted by Scanner), but lets be safe
                                var best = strongCandidates.OrderByDescending(c => c.Score).ThenByDescending(c => c.Gold).FirstOrDefault();
                                
                                wramPtr = best.Address;
                                Console.WriteLine($"Selected BEST candidate 0x{wramPtr.Value.ToString("X")} (Gold: {best.Gold})");
                            }
                            else if (wramCandidates.Count > 0)
                            {
                                // Fallback to first weak candidate
                                wramPtr = wramCandidates[0].Address;
                                Console.WriteLine($"WARNING: Only WEAK candidates found. Using first: 0x{wramPtr.Value.ToString("X")}");
                            }
                            
                            // 2. Scan ROM (Pass WRAM Hint)
                            // We use the WRAM pointer as a hint to find a nearby ROM (Snes9x layout)
                            IntPtr? romPtr = MemoryScanner.ScanForRom(process, wramPtr);
                            
                            if (romPtr.HasValue)
                            {
                                Console.WriteLine($"Lufia 2 ROM Base found at 0x{romPtr.Value.ToString("X")}");
                            }

                            IntPtr? logPtr = MemoryScanner.ScanForSpoilerLog(process); 
                            
                            if (romPtr.HasValue && wramPtr.HasValue)
                            {
                                Console.WriteLine($"SUCCESS: Dual Scan Complete.");
                                Console.WriteLine($"  - WRAM Found: 0x{wramPtr.Value.ToString("X")}");
                                Console.WriteLine($"  - ROM Found:  0x{romPtr.Value.ToString("X")}");
                                
                                baseAddress = process.MainModule.BaseAddress; 
                                long wramOffsetLong = (long)wramPtr.Value - (long)baseAddress;
                                
                                // Detect NWA based on Gold alignment. 
                                // Verification showed NWA Base ends in A1B4.
                                bool isNwa = ((long)wramPtr.Value & 0xFFFF) == 0xA1B4;

                                Console.WriteLine($"[Layout] Detected {(isNwa ? "NWA (Moved)" : "Standard x64")}");

                                if (isNwa)
                                {
                                     LoadDungeons("dungeon_flags_snes9x-nwa.json");
                                }
                                else
                                {
                                     // Ensure we load Standard if not NWA (since list is cleared)
                                     LoadDungeons("dungeon_flags_snes9x.json");
                                }

                                IntPtr romBasePtr = romPtr.HasValue ? romPtr.Value : IntPtr.Zero;
                                // Pass isNwa=false because Relative Offsets are consistent across versions (Diff is 308 for both)
                                // My previous MemoryProfile edit was based on incorrect math (302), so we Force False here.
                                currentProfile = MemoryProfile.CreateFromOffsets(wramPtr.Value, romBasePtr, false);
                                
                                if (isNwa) currentProfile.Name += " [NWA Adjusted]";
                                
                                if (logPtr.HasValue)
                                {
                                    spoilerAddress = logPtr.Value;
                                    Console.WriteLine($"  - Spoiler Log: 0x{spoilerAddress.ToString("X")}");
                                }
                            }
                            else
                            {
                                Console.WriteLine("Dual Scan failed (missing WRAM or ROM). Checking known profiles...");
                                
                                // Load Profiles from Config (emulator_addresses.json)
                                var configProfiles = new List<MemoryProfile>();
                                try 
                                {
                                    var loadedConfig = ConfigLoader.Load("config_dummy_path_checked_internally"); 
                                    if (loadedConfig != null)
                                    {
                                        foreach (var kvp in loadedConfig)
                                        {
                                            foreach (var cfg in kvp.Value)
                                            {
                                                try 
                                                {
                                                    var p = new MemoryProfile
                                                    {
                                                        Name = cfg.name,
                                                        ProcessName = kvp.Key.Replace(".exe", ""),
                                                        PointerBaseAddress = string.IsNullOrEmpty(cfg.pointer_base_address) ? 0 : Convert.ToInt32(cfg.pointer_base_address, 16),
                                                        Gold = string.IsNullOrEmpty(cfg.gold_address) ? 0 : Convert.ToInt32(cfg.gold_address, 16),
                                                        InventoryStart = cfg.inventory_range?.Count > 0 ? Convert.ToInt32(cfg.inventory_range[0], 16) : 0,
                                                        InventoryEnd = cfg.inventory_range?.Count > 1 ? Convert.ToInt32(cfg.inventory_range[1], 16) : 0,
                                                        ScenarioStart = cfg.scenario_range?.Count > 0 ? Convert.ToInt32(cfg.scenario_range[0], 16) : 0,
                                                        ScenarioEnd = cfg.scenario_range?.Count > 1 ? Convert.ToInt32(cfg.scenario_range[1], 16) : 0,
                                                        CharacterSlots = cfg.character_slots?.Select(s => Convert.ToInt32(s, 16)).ToArray() ?? new int[0],
                                                        CapsuleSlotsStart = cfg.capsule_slots_start?.Count > 0 ? Convert.ToInt32(cfg.capsule_slots_start[0], 16) : 0,
                                                        CapsuleSlotsEnd = cfg.capsule_slots_end?.Count > 0 ? Convert.ToInt32(cfg.capsule_slots_end[0], 16) : 0,
                                                        SpoilerLogOffsetStart = string.IsNullOrEmpty(cfg.spoiler_log_offset_start) ? 0 : Convert.ToInt32(cfg.spoiler_log_offset_start, 16),
                                                        SpoilerLogOffsetEnd = string.IsNullOrEmpty(cfg.spoiler_log_offset_end) ? 0 : Convert.ToInt32(cfg.spoiler_log_offset_end, 16),
                                                        DungeonFlagStart = string.IsNullOrEmpty(cfg.dungeon_flag_start) ? 0 : Convert.ToInt32(cfg.dungeon_flag_start, 16),
                                                        DungeonFlagEnd = string.IsNullOrEmpty(cfg.dungeon_flag_end) ? 0 : Convert.ToInt32(cfg.dungeon_flag_end, 16),
                                                        TransportFlag = string.IsNullOrEmpty(cfg.transport_flag) ? 0 : Convert.ToInt32(cfg.transport_flag, 16),
                                                        ShipXFast = string.IsNullOrEmpty(cfg.ship_x_fast_address) ? 0 : Convert.ToInt32(cfg.ship_x_fast_address, 16),
                                                        ShipXSlow = string.IsNullOrEmpty(cfg.ship_x_slow_address) ? 0 : Convert.ToInt32(cfg.ship_x_slow_address, 16),
                                                        ShipYFast = string.IsNullOrEmpty(cfg.ship_y_fast_address) ? 0 : Convert.ToInt32(cfg.ship_y_fast_address, 16),
                                                        ShipYSlow = string.IsNullOrEmpty(cfg.ship_y_slow_address) ? 0 : Convert.ToInt32(cfg.ship_y_slow_address, 16),
                                                        WalkXFast = string.IsNullOrEmpty(cfg.walk_x_fast_address) ? 0 : Convert.ToInt32(cfg.walk_x_fast_address, 16),
                                                        WalkXSlow = string.IsNullOrEmpty(cfg.walk_x_slow_address) ? 0 : Convert.ToInt32(cfg.walk_x_slow_address, 16),
                                                        WalkYFast = string.IsNullOrEmpty(cfg.walk_y_fast_address) ? 0 : Convert.ToInt32(cfg.walk_y_fast_address, 16),
                                                        WalkYSlow = string.IsNullOrEmpty(cfg.walk_y_slow_address) ? 0 : Convert.ToInt32(cfg.walk_y_slow_address, 16),
                                                        CapsuleSpriteOffset = string.IsNullOrEmpty(cfg.capsule_sprite_offset) ? 0 : Convert.ToInt32(cfg.capsule_sprite_offset, 16),
                                                        MapAddress = string.IsNullOrEmpty(cfg.map_address) && cfg.map_address != "0x" ? Convert.ToInt32(cfg.map_address, 16) : 0
                                                    };
                                                    configProfiles.Add(p);
                                                }
                                                catch {}
                                            }
                                        }
                                    }
                                } catch {}

                                var allProfiles = configProfiles.Concat(MemoryProfile.KnownProfiles);

                                foreach (var p in allProfiles)
                                {
                                    if (process.ProcessName.StartsWith(p.ProcessName, StringComparison.OrdinalIgnoreCase))
                                    {
                                        try 
                                        {
                                            currentProfile = p;
                                            baseAddress = process.MainModule.BaseAddress; 
                                            break;
                                        } 
                                        catch {}
                                    }
                                }
                            }

                            if (currentProfile != null)
                            {
                                Console.WriteLine($"SUCCESS: Attached to Emulator!");
                                Console.WriteLine($"  - Process: {process.ProcessName} (PID: {process.Id})");
                                Console.WriteLine($"  - Profile: {currentProfile.Name}");
                                Console.WriteLine($"  - Base Address: 0x{baseAddress.ToString("X")}");
                                
                                reader = new DataReaders(process.Handle, baseAddress, currentProfile);
                                if (spoilerAddress != IntPtr.Zero)
                                {
                                    reader.SetSpoilerLogAddress(spoilerAddress);
                                }

                                cachedSpoilerLog = null; // Reset cache on new process
                            }
                            else
                            {
                                Console.WriteLine($"WARNING: Found process '{process.ProcessName}' but no matching profile in MemoryProfile.KnownProfiles.");
                                Console.WriteLine($"  - Please ensure you are running a supported version of Snes9x.");
                                process = null;
                            }
                        }
                    }

                    if (process != null && reader != null)
                    {
                        var state = reader.ReadGameState();
                        
                        // Read Spoiler Log only if empty/null and we have a valid state (game running)
                        if ((cachedSpoilerLog == null || cachedSpoilerLog.Count == 0) && _spoilerAttemptCount < 10)
                        {
                             _spoilerAttemptCount++;
                             var logs = reader.ReadSpoilerLog();
                             if (logs.Count > 0)
                             {
                                 cachedSpoilerLog = logs;
                                 Console.WriteLine($"Parsed Spoiler Log: {logs.Count} entries.");
                             }
                        }
                        state.SpoilerLog = cachedSpoilerLog;

                        var currentPosStr = $"{state.PlayerX},{state.PlayerY},{state.TransportMode}";
                        var lastPosStr = lastState != null ? $"{lastState.PlayerX},{lastState.PlayerY},{lastState.TransportMode}" : "";

                        var coreStateCurrent = new {
                            inventory = state.Inventory,
                            characters = state.Characters,
                            capsules = state.Capsules,
                            capsule_sprite_values = state.CapsuleSpriteValues,
                            cleared_locations = state.ClearedLocations,
                            scenario = state.ScenarioItems,
                            maidens = state.Maidens
                        };
                        var coreStateLast = lastState != null ? new {
                            inventory = lastState.Inventory,
                            characters = lastState.Characters,
                            capsules = lastState.Capsules,
                            capsule_sprite_values = lastState.CapsuleSpriteValues,
                            cleared_locations = lastState.ClearedLocations,
                            scenario = lastState.ScenarioItems,
                            maidens = lastState.Maidens
                        } : null;

                        string jsonCoreCurrent = System.Text.Json.JsonSerializer.Serialize(coreStateCurrent);
                        string jsonCoreLast = coreStateLast != null ? System.Text.Json.JsonSerializer.Serialize(coreStateLast) : "";

                        bool posChanged = currentPosStr != lastPosStr;
                        bool coreChanged = jsonCoreCurrent != jsonCoreLast;

                        if (coreChanged)
                        {
                            client.SendState(state);
                            lastState = state;
                        }
                        else if (posChanged)
                        {
                            var minimalState = new GameState {
                                PlayerX = state.PlayerX,
                                PlayerY = state.PlayerY,
                                TransportMode = state.TransportMode,
                                Inventory = null,
                                Characters = null,
                                Capsules = null,
                                CapsuleSpriteValues = null,
                                ClearedLocations = null,
                                ScenarioItems = null,
                                Maidens = null,
                                SpoilerLog = null
                            };
                            client.SendState(minimalState);
                            
                            if (lastState != null) {
                                lastState.PlayerX = state.PlayerX;
                                lastState.PlayerY = state.PlayerY;
                                lastState.TransportMode = state.TransportMode;
                            }
                        }
                    }
                }

                catch (Exception ex)
                {
                    Console.WriteLine($"Loop Error: {ex.Message}");
                    process = null; // Retry
                    lastSentJson = ""; // Reset on error
                }

                Thread.Sleep(100);
            }
        }

        private static bool IsInWramBlock(IntPtr processBase, IntPtr candidate, long minSize)
        {
            // Simple check: Snes9x usually maps WRAM at > baseAddress. 
            // Better to rely on Gold scanning.
            return (long)candidate > (long)processBase;
        }

        private static string lastSentJson = "";

        private static void LoadDungeons(string filename)
        {
            try 
            {
                // Traverse up to find 'src/data' or 'data'
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string targetPath = null;
                
                for (int i = 0; i < 12; i++)
                {
                   string tryPath = Path.Combine(baseDir, "data", filename);
                   if (File.Exists(tryPath)) { targetPath = tryPath; break; }
                   
                   tryPath = Path.Combine(baseDir, "src", "data", filename);
                   if (File.Exists(tryPath)) { targetPath = tryPath; break; }

                   var parent = Directory.GetParent(baseDir);
                   if (parent == null) break;
                   baseDir = parent.FullName;
                }

                if (targetPath != null && File.Exists(targetPath))
                {
                    string json = File.ReadAllText(targetPath);
                    using var doc = JsonDocument.Parse(json);
                    var list = new List<GameData.DungeonDef>();
                    
                    int minAddr = int.MaxValue;
                    var tempItems = new List<(int addr, JsonElement val)>();

                    // First pass: Find Min and Collect
                    foreach (var prop in doc.RootElement.EnumerateObject())
                    {
                        int addr = Convert.ToInt32(prop.Name, 16);
                        if (addr < minAddr) minAddr = addr;
                        tempItems.Add((addr, prop.Value));
                    }
                    
                    // Second pass: Add with Normalized Offset
                    foreach (var item in tempItems)
                    {
                        int normalizedOffset = item.addr - minAddr;
                        foreach (var subEntry in item.val.EnumerateArray())
                        {
                            list.Add(new GameData.DungeonDef {
                                Address = normalizedOffset, // Store 0, 1, 2...
                                Location = subEntry.GetProperty("location").GetString(),
                                Flag = subEntry.GetProperty("flag").GetString()
                            });
                        }
                    }
                    GameData.LoadDungeons(list);
                    Console.WriteLine($"[Config] Loaded Dungeons from {targetPath} (Base: 0x{minAddr:X})");
                }
                else
                {
                    Console.WriteLine($"[Config] Warning: {filename} not found (Searched up from {AppDomain.CurrentDomain.BaseDirectory}).");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Config] Error loading dungeons: {ex.Message}");
            }
        }
    }
}
