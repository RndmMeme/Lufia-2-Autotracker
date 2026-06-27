using System.Collections.Generic;

namespace Lufia2AutoTracker.Helper.Core
{
    public static class GameData
    {
        public class ItemDef
        {
            public string Name { get; set; } = string.Empty;
            public string Type { get; set; } = string.Empty;
            public string ObtainedValue { get; set; } = string.Empty; // Hex string ("0x03A9") or Binary mask
        }
        
        public class DungeonDef
        {
            public string Location { get; set; } = string.Empty;
            public string Flag { get; set; } = string.Empty; // "0x80"
            public int Address { get; set; } // Offset from canonical DungeonFlagsStart.
        }

        public static string GetCharacterName(byte id)
        {
            return id switch
            {
                0x00 => "Maxim", 0x01 => "Selan", 0x02 => "Guy", 0x03 => "Artea",
                0x04 => "Tia", 0x05 => "Dekar", 0x06 => "Lexis", 0xFF => "Empty",
                _ => "Unknown"
            };
        }

        public static List<ItemDef> Tools = new List<ItemDef>
        {
            new ItemDef { Name="Arrow", Type="normal", ObtainedValue="0x03A9" },
            new ItemDef { Name="Bomb", Type="normal", ObtainedValue="0x03A8" },
            new ItemDef { Name="Hammer", Type="normal", ObtainedValue="0x03AB" },
            new ItemDef { Name="Hook", Type="normal", ObtainedValue="0x03A7" },
            new ItemDef { Name="Fire", Type="normal", ObtainedValue="0x03AA" },
            new ItemDef { Name="Jade", Type="special", ObtainedValue="0001 0000 0000 0000 0000 0000" },
            new ItemDef { Name="Engine", Type="special", ObtainedValue="0010 0000 0000 0000 0000 0000" }
        };

        public static List<ItemDef> ScenarioItems = new List<ItemDef>
        {
             new ItemDef { Name="Door key", ObtainedValue="0000 0000 0000 0000 0000 0010" },
             new ItemDef { Name="Shrine", ObtainedValue="0000 0000 0000 0000 0000 0100" },
             new ItemDef { Name="Basement", ObtainedValue="0000 0010 0000 0000 0000 0000" },
             new ItemDef { Name="Cloud", ObtainedValue="0000 0000 0000 0000 1000 0000" },
             new ItemDef { Name="Dankirk", ObtainedValue="0000 0001 0000 0000 0000 0000" },
             new ItemDef { Name="Flower", ObtainedValue="0000 0000 0000 1000 0000 0000" },
             new ItemDef { Name="Ghost", ObtainedValue="0000 0000 0100 0000 0000 0000" },
             new ItemDef { Name="Heart", ObtainedValue="0000 0000 0010 0000 0000 0000" },
             new ItemDef { Name="Lake", ObtainedValue="0000 0000 0000 0000 0001 0000" },
             new ItemDef { Name="Light", ObtainedValue="0000 0000 0000 0001 0000 0000" },
             new ItemDef { Name="Magma", ObtainedValue="0000 0000 0001 0000 0000 0000" },
             new ItemDef { Name="Narcysus", ObtainedValue="0000 0100 0000 0000 0000 0000" },
             new ItemDef { Name="Ruby", ObtainedValue="0000 0000 0000 0000 0010 0000" },
             new ItemDef { Name="Sky", ObtainedValue="0000 0000 0000 0000 0000 1000" },
             new ItemDef { Name="Sword", ObtainedValue="0000 0000 0000 0010 0000 0000" },
             new ItemDef { Name="Tree", ObtainedValue="0000 0000 0000 0100 0000 0000" },
             new ItemDef { Name="Trial", ObtainedValue="0000 0000 1000 0000 0000 0000" },
             new ItemDef { Name="Truth", ObtainedValue="0000 1000 0000 0000 0000 0000" },
             new ItemDef { Name="Wind", ObtainedValue="0000 0000 0000 0000 0100 0000" }
        };

        // Loaded from the dungeon flag mapping at helper startup.
        public static List<DungeonDef> Dungeons = new List<DungeonDef>();

        public static void LoadDungeons(List<DungeonDef> dungeons)
        {
            Dungeons = dungeons;
        }
    }
}
