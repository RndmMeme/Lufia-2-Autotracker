using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Lufia2AutoTracker.Helper.Core
{
    public class GameState
    {
        [JsonPropertyName("inventory")]
        public List<string> Inventory { get; set; } = new List<string>();

        [JsonPropertyName("characters")]
        public List<string> Characters { get; set; } = new List<string>();

        [JsonPropertyName("capsules")]
        public List<string> Capsules { get; set; } = new List<string>();

        [JsonPropertyName("capsule_sprite_values")]
        public List<string> CapsuleSpriteValues { get; set; } = new List<string>();

        [JsonPropertyName("player_x")]
        public int PlayerX { get; set; }

        [JsonPropertyName("player_y")]
        public int PlayerY { get; set; }

        [JsonPropertyName("transport_mode")]
        public string TransportMode { get; set; }

        [JsonPropertyName("cleared_locations")]
        public List<string> ClearedLocations { get; set; } = new List<string>();

        [JsonPropertyName("scenario")]
        public List<string> ScenarioItems { get; set; } = new List<string>();

        [JsonPropertyName("maidens")]
        public Dictionary<string, bool> Maidens { get; set; } = new Dictionary<string, bool>();

        [JsonPropertyName("spoiler_log")]
        public List<Dictionary<string, string>> SpoilerLog { get; set; } = new List<Dictionary<string, string>>();
    }
}
