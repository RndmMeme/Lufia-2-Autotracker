using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace Lufia2AutoTracker.Helper.Core
{
    public static class ConfigLoader
    {
        private const string ConfigFileName = "emulator_addresses.json";

        public static Dictionary<string, List<EmulatorConfig>>? Load(string? dataDirectory = null)
        {
            string? path = ResolveConfigPath(dataDirectory);
            if (path == null)
            {
                Console.WriteLine("[Config] emulator_addresses.json was not found.");
                return null;
            }

            try
            {
                string json = File.ReadAllText(path);
                var result = JsonSerializer.Deserialize<Dictionary<string, List<EmulatorConfig>>>(json,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                Console.WriteLine($"[Config] Loaded emulator profiles from {path}");
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

    public sealed class EmulatorConfig
    {
        public string name { get; set; } = "Unnamed profile";
        public string pointer_base_address { get; set; } = "0x0";
        public string gold_address { get; set; } = "0x0";
        public List<string> character_slots { get; set; } = new();
        public List<string> capsule_slots_start { get; set; } = new();
        public List<string> capsule_slots_end { get; set; } = new();
        public List<string> inventory_range { get; set; } = new();
        public List<string> scenario_range { get; set; } = new();
        public string shop_offset { get; set; } = "0x0";
        public string capsule_sprite_offset { get; set; } = "0x0";
        public string map_address { get; set; } = "0x0";
        public string spoiler_log_offset_start { get; set; } = "0x0";
        public string spoiler_log_offset_end { get; set; } = "0x0";
        public string dungeon_flag_start { get; set; } = "0x0";
        public string dungeon_flag_end { get; set; } = "0x0";
        public string dungeon_flag_addresses { get; set; } = "dungeon_flags_snes9x.json";
        public string transport_flag { get; set; } = "0x0";
        public string ship_x_fast_address { get; set; } = "0x0";
        public string ship_x_slow_address { get; set; } = "0x0";
        public string ship_y_fast_address { get; set; } = "0x0";
        public string ship_y_slow_address { get; set; } = "0x0";
        public string walk_x_fast_address { get; set; } = "0x0";
        public string walk_x_slow_address { get; set; } = "0x0";
        public string walk_y_fast_address { get; set; } = "0x0";
        public string walk_y_slow_address { get; set; } = "0x0";
    }
}
