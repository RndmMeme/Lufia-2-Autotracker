using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace Lufia2AutoTracker.Helper.Core
{
    public static class ConfigLoader
    {
        private const string ConfigFileName = "emulator_root_hints.json";

        public static RootHintDocument? Load(string? dataDirectory = null)
        {
            string? path = ResolveConfigPath(dataDirectory);
            if (path == null)
            {
                Console.WriteLine($"[Config] {ConfigFileName} was not found; using built-in root hints.");
                return null;
            }

            try
            {
                string json = File.ReadAllText(path);
                var result = JsonSerializer.Deserialize<RootHintDocument>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                Console.WriteLine($"[Config] Loaded emulator root hints from {path}");
                return result;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Config] Failed to load {path}: {ex.Message}");
                return null;
            }
        }

        public static string? ResolveConfigPath(string? dataDirectory = null)
        {
            var candidates = new List<string>();

            if (!string.IsNullOrWhiteSpace(dataDirectory))
            {
                candidates.Add(Path.Combine(dataDirectory, ConfigFileName));
            }

            string appBase = AppContext.BaseDirectory;
            string current = Directory.GetCurrentDirectory();
            candidates.Add(Path.Combine(appBase, "src", "data", ConfigFileName));
            candidates.Add(Path.Combine(appBase, "data", ConfigFileName));
            candidates.Add(Path.Combine(current, "src", "data", ConfigFileName));
            candidates.Add(Path.Combine(current, "data", ConfigFileName));

            foreach (string candidate in candidates)
            {
                try
                {
                    string fullPath = Path.GetFullPath(candidate);
                    if (File.Exists(fullPath)) return fullPath;
                }
                catch
                {
                    // Continue to the next deterministic candidate.
                }
            }

            return null;
        }
    }

    public sealed class RootHintDocument
    {
        public List<RootHintConfig> root_hints { get; set; } = new();
    }

    public sealed class RootHintConfig
    {
        public string name { get; set; } = "Unnamed root hint";
        public List<string> process_names { get; set; } = new();
        public string gold_process_offset { get; set; } = "0x0";
    }
}
