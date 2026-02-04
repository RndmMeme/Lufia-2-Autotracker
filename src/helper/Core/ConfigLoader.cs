using System;
using System.IO;
using System.Text.Json;
using System.Collections.Generic;

namespace Lufia2AutoTracker.Helper.Core
{
    public class ConfigLoader
    {
        public static Dictionary<string, List<EmulatorConfig>> Load(string path)
        {
            if (!File.Exists(path))
            {
                // Try parent directories if not found (development vs production)
                 path = Path.Combine("..", "data", "emulator_addresses.json");
                 if (!File.Exists(path))
                 {
                     path = Path.Combine("..", "..", "src", "data", "emulator_addresses.json"); // Dev path
                 }
            }
            
            if (File.Exists(path))
            {
                string json = File.ReadAllText(path);
                try {
                    return JsonSerializer.Deserialize<Dictionary<string, List<EmulatorConfig>>>(json);
                } catch { return null; }
            }
            return null;
        }
    }

    public class EmulatorConfig
    {
        public string name { get; set; }
        public string pointer_base_address { get; set; }
        public string gold_address { get; set; }
        public List<string> character_slots { get; set; }
        
        public List<string> capsule_slots_start { get; set; }
        public List<string> capsule_slots_end { get; set; }
        public List<string> inventory_range { get; set; }
        public List<string> scenario_range { get; set; }
        public string shop_offset { get; set; }
        public string capsule_sprite_offset { get; set; }
        public string map_address { get; set; }
        public string spoiler_log_offset_start { get; set; }
        public string spoiler_log_offset_end { get; set; }
        public string dungeon_flag_start { get; set; }
        public string dungeon_flag_end { get; set; }
        public string dungeon_flag_addresses { get; set; }
        public string transport_flag { get; set; }
        public string ship_x_fast_address { get; set; }
        public string ship_x_slow_address { get; set; }
        public string ship_y_fast_address { get; set; }
        public string ship_y_slow_address { get; set; }
        public string walk_x_fast_address { get; set; }
        public string walk_x_slow_address { get; set; }
        public string walk_y_fast_address { get; set; }
        public string walk_y_slow_address { get; set; }
    }
}
