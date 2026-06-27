using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading;
using Lufia2AutoTracker.Helper.Core;

namespace Lufia2AutoTracker.Helper
{
    internal static class Program
    {
        private sealed class Attachment
        {
            public required Process Process { get; init; }
            public required MemoryProfile Profile { get; init; }
            public IntPtr SpoilerAddress { get; init; }
        }

        private static int Main(string[] args)
        {
            string? dataDirectory = GetOption(args, "--data-dir");
            int? requestedProcessId = int.TryParse(GetOption(args, "--pid"), out int parsedProcessId)
                ? parsedProcessId
                : null;
            bool rootHintsOnly = args.Contains("--root-hints-only", StringComparer.OrdinalIgnoreCase);
            if (args.Contains("--self-test", StringComparer.OrdinalIgnoreCase))
            {
                return SelfTest.Run(dataDirectory);
            }

            Console.WriteLine("Lufia 2 Auto Tracker Helper v1.4.9");
            Console.WriteLine($"[Config] Data directory: {dataDirectory ?? "auto-detect"}");

            LoadDungeons(dataDirectory, "dungeon_flags_snes9x.json");
            List<MemoryRootHint> configuredRootHints = BuildConfiguredRootHints(ConfigLoader.Load(dataDirectory));

            var client = new TrackerClient();
            client.Connect();
            client.StartListening();

            DataReaders? reader = null;
            GameState? lastState = null;
            Process? process = null;
            MemoryProfile? currentProfile = null;
            List<Dictionary<string, string>>? cachedSpoilerLog = null;
            int spoilerAttemptCount = 0;
            int failedReadCycles = 0;
            int rescanRequested = 0;
            DateTime lastWaitingStatus = DateTime.MinValue;

            client.CommandReceived += command =>
            {
                if (command.Contains("RESCAN", StringComparison.OrdinalIgnoreCase))
                {
                    Interlocked.Exchange(ref rescanRequested, 1);
                }
            };

            while (true)
            {
                try
                {
                    if (Interlocked.Exchange(ref rescanRequested, 0) == 1)
                    {
                        Console.WriteLine("[Tracker] RESCAN requested.");
                        process?.Dispose();
                        process = null;
                        reader = null;
                        currentProfile = null;
                        lastState = null;
                        cachedSpoilerLog = null;
                        spoilerAttemptCount = 0;
                        failedReadCycles = 0;
                    }

                    if (process == null || HasExited(process) || reader == null)
                    {
                        if (process != null)
                        {
                            process.Dispose();
                            process = null;
                        }
                        client.SendStatus("scanning", "Searching for a running Lufia II emulator...");
                        Attachment? attachment = FindAttachment(
                            configuredRootHints,
                            client,
                            requestedProcessId,
                            rootHintsOnly);
                        if (attachment == null)
                        {
                            if ((DateTime.UtcNow - lastWaitingStatus).TotalSeconds >= 5)
                            {
                                client.SendStatus("waiting", "No validated Lufia II memory instance found.");
                                lastWaitingStatus = DateTime.UtcNow;
                            }
                            Thread.Sleep(1000);
                            continue;
                        }

                        process = attachment.Process;
                        currentProfile = attachment.Profile;
                        reader = new DataReaders(process.Handle, currentProfile);
                        if (attachment.SpoilerAddress != IntPtr.Zero)
                        {
                            reader.SetSpoilerLogAddress(attachment.SpoilerAddress);
                        }

                        cachedSpoilerLog = null;
                        spoilerAttemptCount = 0;
                        failedReadCycles = 0;
                        lastState = null;

                        Console.WriteLine($"[Tracker] Attached to {process.ProcessName} (PID {process.Id}) with {currentProfile.Name}");
                        client.SendStatus(
                            "attached",
                            currentProfile.HasRom
                                ? "Auto-tracker attached with WRAM and ROM support."
                                : "Auto-tracker attached with WRAM support; ROM-only features are unavailable.",
                            process.ProcessName,
                            currentProfile.Name);
                    }

                    if (process != null && reader != null)
                    {
                        GameState state = reader.ReadGameState();
                        if (!reader.LastRequiredReadSucceeded)
                        {
                            failedReadCycles++;
                            Console.WriteLine(
                                $"[Warning] [StateRead] rejected incomplete snapshot " +
                                $"cycle={failedReadCycles}/3 process={process.ProcessName} pid={process.Id} " +
                                $"profile={currentProfile?.Name}");
                            if (failedReadCycles >= 3)
                            {
                                Console.WriteLine("[Tracker] Required memory reads failed repeatedly; detaching for a fresh scan.");
                                client.SendStatus("lost", "Memory reads became invalid; rescanning.", process.ProcessName, currentProfile?.Name);
                                process.Dispose();
                                process = null;
                                reader = null;
                                currentProfile = null;
                                lastState = null;
                            }
                            continue;
                        }
                        else
                        {
                            failedReadCycles = 0;
                        }

                        if ((cachedSpoilerLog == null || cachedSpoilerLog.Count == 0) && spoilerAttemptCount < 10)
                        {
                            spoilerAttemptCount++;
                            var logs = reader.ReadSpoilerLog();
                            if (logs.Count > 0)
                            {
                                cachedSpoilerLog = logs;
                                Console.WriteLine($"[Tracker] Parsed spoiler log: {logs.Count} entries.");
                            }
                        }
                        state.SpoilerLog = cachedSpoilerLog;

                        string currentPosition = $"{state.PlayerX},{state.PlayerY},{state.TransportMode}";
                        string lastPosition = lastState != null
                            ? $"{lastState.PlayerX},{lastState.PlayerY},{lastState.TransportMode}"
                            : string.Empty;

                        bool positionChanged = currentPosition != lastPosition;
                        bool coreChanged = !CoreStateEquals(state, lastState);

                        if (coreChanged)
                        {
                            client.SendState(state);
                            lastState = state;
                        }
                        else if (positionChanged)
                        {
                            client.SendState(new GameState {
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
                            });

                            if (lastState != null)
                            {
                                lastState.PlayerX = state.PlayerX;
                                lastState.PlayerY = state.PlayerY;
                                lastState.TransportMode = state.TransportMode;
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[Tracker] Loop error: {ex}");
                    client.SendStatus("error", $"Tracker helper error: {ex.Message}");
                    process?.Dispose();
                    process = null;
                    reader = null;
                    currentProfile = null;
                    lastState = null;
                }

                Thread.Sleep(100);
            }
        }

        private static Attachment? FindAttachment(
            List<MemoryRootHint> configuredRootHints,
            TrackerClient client,
            int? requestedProcessId,
            bool rootHintsOnly)
        {
            IReadOnlyList<Process> processes;
            if (requestedProcessId.HasValue)
            {
                try
                {
                    processes = new[] { Process.GetProcessById(requestedProcessId.Value) };
                }
                catch
                {
                    return null;
                }
            }
            else
            {
                processes = ProcessScanner.FindEmulatorProcesses();
            }
            if (processes.Count == 0) return null;

            Console.WriteLine($"[Tracker] Found {processes.Count} emulator process candidate(s).");
            Process? attachedProcess = null;
            try
            {
                foreach (Process candidateProcess in processes)
                {
                    try
                    {
                        client.SendStatus("probing", $"Checking {candidateProcess.ProcessName} (PID {candidateProcess.Id})...", candidateProcess.ProcessName);
                        IntPtr processBase = candidateProcess.MainModule?.BaseAddress ?? IntPtr.Zero;

                        List<WramCandidate> wramCandidates = rootHintsOnly
                            ? new List<WramCandidate>()
                            : MemoryScanner.ScanForWram(candidateProcess);
                        foreach (WramCandidate wram in wramCandidates.OrderByDescending(item => item.Score))
                        {
                            IntPtr? romBase = MemoryScanner.ScanForRom(candidateProcess, wram.Address);
                            MemoryProfile profile = MemoryProfile.CreateFromRoots(
                                wram.Address,
                                romBase ?? IntPtr.Zero,
                                candidateProcess.ProcessName);

                            if (!MemoryScanner.ValidateProfile(candidateProcess, profile, out string validation))
                            {
                                Console.WriteLine($"[Tracker] Rejected scanned profile for PID {candidateProcess.Id}: {validation}");
                                continue;
                            }

                            IntPtr spoilerAddress = MemoryScanner.ScanForSpoilerLog(candidateProcess) ?? IntPtr.Zero;
                            attachedProcess = candidateProcess;
                            return new Attachment {
                                Process = candidateProcess,
                                Profile = profile,
                                SpoilerAddress = spoilerAddress
                            };
                        }

                        IEnumerable<MemoryRootHint> fallbackHints = configuredRootHints
                            .Concat(MemoryProfile.BuiltInRootHints)
                            .Where(hint => ProcessNameMatches(candidateProcess.ProcessName, hint.ProcessName));

                        foreach (MemoryRootHint hint in fallbackHints)
                        {
                            IntPtr wramRoot = hint.ResolveWramRoot(processBase);
                            MemoryProfile rootProfile = MemoryProfile.CreateFromRoots(
                                wramRoot,
                                IntPtr.Zero,
                                candidateProcess.ProcessName,
                                $"Canonical root from {hint.Name}");

                            if (!MemoryScanner.ValidateProfile(candidateProcess, rootProfile, out string validation))
                            {
                                Console.WriteLine($"[Tracker] Rejected root hint '{hint.Name}': {validation}");
                                continue;
                            }

                            IntPtr? romBase = MemoryScanner.ScanForRom(candidateProcess, wramRoot);
                            MemoryProfile profile = MemoryProfile.CreateFromRoots(
                                wramRoot,
                                romBase ?? IntPtr.Zero,
                                candidateProcess.ProcessName,
                                $"Canonical root from {hint.Name}");
                            IntPtr spoilerAddress = MemoryScanner.ScanForSpoilerLog(candidateProcess) ?? IntPtr.Zero;
                            attachedProcess = candidateProcess;
                            return new Attachment {
                                Process = candidateProcess,
                                Profile = profile,
                                SpoilerAddress = spoilerAddress
                            };
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[Tracker] Failed to inspect {candidateProcess.ProcessName} (PID {candidateProcess.Id}): {ex.Message}");
                    }
                }
            }
            finally
            {
                foreach (Process candidateProcess in processes)
                {
                    if (!ReferenceEquals(candidateProcess, attachedProcess)) candidateProcess.Dispose();
                }
            }

            return null;
        }

        private static List<MemoryRootHint> BuildConfiguredRootHints(RootHintDocument? document)
        {
            var hints = new List<MemoryRootHint>();
            if (document == null) return hints;

            foreach (RootHintConfig config in document.root_hints)
            {
                try
                {
                    int goldProcessOffset = ParseHex(config.gold_process_offset);
                    if (goldProcessOffset <= 0) throw new InvalidDataException("gold_process_offset must be positive");
                    foreach (string processName in config.process_names)
                    {
                        hints.Add(new MemoryRootHint {
                            Name = config.name,
                            ProcessName = Path.GetFileNameWithoutExtension(processName),
                            GoldProcessOffset = goldProcessOffset
                        });
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[Config] Ignoring invalid root hint '{config.name}': {ex.Message}");
                }
            }

            return hints;
        }

        private static int ParseHex(string? value)
        {
            if (string.IsNullOrWhiteSpace(value) || value.Equals("0x", StringComparison.OrdinalIgnoreCase)) return 0;
            string normalized = value.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? value[2..] : value;
            return Convert.ToInt32(normalized, 16);
        }

        private static bool ProcessNameMatches(string actualName, string profileName) =>
            actualName.Equals(profileName, StringComparison.OrdinalIgnoreCase) ||
            actualName.StartsWith(profileName + "-", StringComparison.OrdinalIgnoreCase);

        private static bool HasExited(Process process)
        {
            try { return process.HasExited; }
            catch (Exception ex)
            {
                Console.WriteLine(
                    $"[Warning] [Process] exit-state query failed " +
                    $"exception={ex.GetType().Name} message={ex.Message}");
                return true;
            }
        }

        private static bool CoreStateEquals(GameState current, GameState? previous)
        {
            if (previous == null) return false;
            return SequenceEqual(current.Inventory, previous.Inventory) &&
                   SequenceEqual(current.Characters, previous.Characters) &&
                   SequenceEqual(current.Capsules, previous.Capsules) &&
                   SequenceEqual(current.CapsuleSpriteValues, previous.CapsuleSpriteValues) &&
                   SequenceEqual(current.ClearedLocations, previous.ClearedLocations) &&
                   SequenceEqual(current.ScenarioItems, previous.ScenarioItems) &&
                   DictionariesEqual(current.Maidens, previous.Maidens);
        }

        private static bool SequenceEqual<T>(IEnumerable<T>? left, IEnumerable<T>? right) =>
            left == null ? right == null : right != null && left.SequenceEqual(right);

        private static bool DictionariesEqual<TKey, TValue>(
            IReadOnlyDictionary<TKey, TValue>? left,
            IReadOnlyDictionary<TKey, TValue>? right) where TKey : notnull
        {
            if (left == null) return right == null;
            if (right == null || left.Count != right.Count) return false;
            return left.All(pair =>
                right.TryGetValue(pair.Key, out TValue? value) &&
                EqualityComparer<TValue>.Default.Equals(pair.Value, value));
        }

        private static string? GetOption(string[] args, string option)
        {
            for (int index = 0; index < args.Length - 1; index++)
            {
                if (args[index].Equals(option, StringComparison.OrdinalIgnoreCase)) return args[index + 1];
            }
            return null;
        }

        internal static bool LoadDungeons(string? dataDirectory, string fileName)
        {
            try
            {
                string? configPath = ConfigLoader.ResolveConfigPath(dataDirectory);
                string? directory = !string.IsNullOrWhiteSpace(dataDirectory)
                    ? dataDirectory
                    : configPath == null ? null : Path.GetDirectoryName(configPath);
                if (directory == null) return false;

                string path = Path.Combine(directory, fileName);
                if (!File.Exists(path))
                {
                    Console.WriteLine($"[Config] Dungeon mapping not found: {path}");
                    return false;
                }

                using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path));
                var rawEntries = new List<(int Address, JsonElement Value)>();
                int minimumAddress = int.MaxValue;
                foreach (JsonProperty property in document.RootElement.EnumerateObject())
                {
                    int address = ParseHex(property.Name);
                    minimumAddress = Math.Min(minimumAddress, address);
                    rawEntries.Add((address, property.Value.Clone()));
                }

                var dungeons = new List<GameData.DungeonDef>();
                foreach (var entry in rawEntries)
                {
                    foreach (JsonElement item in entry.Value.EnumerateArray())
                    {
                        dungeons.Add(new GameData.DungeonDef {
                            Address = entry.Address - minimumAddress,
                            Location = item.GetProperty("location").GetString() ?? string.Empty,
                            Flag = item.GetProperty("flag").GetString() ?? "0"
                        });
                    }
                }

                GameData.LoadDungeons(dungeons);
                Console.WriteLine($"[Config] Loaded {dungeons.Count} dungeon flags from {path}");
                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Config] Failed to load dungeon mapping: {ex.Message}");
                return false;
            }
        }
    }
}
