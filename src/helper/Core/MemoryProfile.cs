using System.Collections.Generic;

namespace Lufia2AutoTracker.Helper.Core
{
    public class MemoryProfile
    {
        public string Name { get; set; }
        public string ProcessName { get; set; }
        
        // Base Offsets
        public int Gold { get; set; }
        public int MapAddress { get; set; }
        public int PointerBaseAddress { get; set; }
        public System.IntPtr ScannedRomBase { get; set; }

        // Ranges
        public int InventoryStart { get; set; }
        public int InventoryEnd { get; set; }
        public int ScenarioStart { get; set; }
        public int ScenarioEnd { get; set; }
        
        // Flags
        public int TransportFlag { get; set; }
        public int DungeonFlagStart { get; set; }
        public int DungeonFlagEnd { get; set; }

        // Player Position
        public int ShipXFast { get; set; }
        public int ShipXSlow { get; set; }
        public int ShipYFast { get; set; }
        public int ShipYSlow { get; set; }
        public int WalkXFast { get; set; }
        public int WalkXSlow { get; set; }
        public int WalkYFast { get; set; }
        public int WalkYSlow { get; set; }

        // Spoiler Log
        public int SpoilerLogOffsetStart { get; set; }
        public int SpoilerLogOffsetEnd { get; set; }

        // Slots
        public int[] CharacterSlots { get; set; }
        public int CapsuleSlotsStart { get; set; }
        public int CapsuleSlotsEnd { get; set; }
        public int CapsuleSpriteOffset { get; set; }

        public static List<MemoryProfile> KnownProfiles => new List<MemoryProfile>
        {
            new MemoryProfile
            {
                Name = "Snes9x 1.62.3",
                ProcessName = "snes9x-x64",
                Gold = 0xA32D9E,
                CharacterSlots = new[] { 0xA32D8F, 0xA32D90, 0xA32D91, 0xA32D92 },
                CapsuleSlotsStart = 0xA334CF,
                CapsuleSlotsEnd = 0xA334D5,
                InventoryStart = 0xA32DA1,
                InventoryEnd = 0xA32E60,
                ScenarioStart = 0xA32C32,
                ScenarioEnd = 0xA32C34,
                PointerBaseAddress = 0xA52330,
                MapAddress = 0xA3351E,
                SpoilerLogOffsetStart = 0x3EE1E1,
                SpoilerLogOffsetEnd = 0x3EE8A5,
                DungeonFlagStart = 0xA32A96,
                DungeonFlagEnd = 0xA32A9F,
                TransportFlag = 0xA32CF5,
                ShipXFast = 0xA3379C,
                ShipXSlow = 0xA3379D,
                ShipYFast = 0xA3379F,
                ShipYSlow = 0xA337A0,
                WalkXFast = 0xA3377F,
                WalkXSlow = 0xA33780,
                WalkYFast = 0xA33782,
                WalkYSlow = 0xA33783,
                CapsuleSpriteOffset = 0xBDCB8
            },
            new MemoryProfile
            {
                Name = "Snes9x 1.62.3-nwa",
                ProcessName = "snes9x", // Usually just snes9x.exe for nwa? Assuming generic
                Gold = 0xE2CF52,
                CharacterSlots = new[] { 0xE2CF43, 0xE2CF44, 0xE2CF45, 0xE2CF46 },
                CapsuleSlotsStart = 0xE2D683,
                CapsuleSlotsEnd = 0xE2D689,
                InventoryStart = 0xE2CF55,
                InventoryEnd = 0xE2D014,
                ScenarioStart = 0xE2CDE6,
                ScenarioEnd = 0xE2CDE8,
                PointerBaseAddress = 0xBA0598,
                MapAddress = 0, // Missing in JSON
                SpoilerLogOffsetStart = 0x3EE1E1,
                SpoilerLogOffsetEnd = 0x3EE8A5,
                DungeonFlagStart = 0xE2CC4A,
                DungeonFlagEnd = 0xE2CC53,
                TransportFlag = 0xE2CEA9,
                ShipXFast = 0xE2D950,
                ShipXSlow = 0xE2D951,
                ShipYFast = 0xE2D953,
                ShipYSlow = 0xE2D954,
                WalkXFast = 0xE2D933,
                WalkXSlow = 0xE2D934,
                WalkYFast = 0xE2D936,
                WalkYSlow = 0xE2D937,
                CapsuleSpriteOffset = 0xBDCB8
            }
        };

        public static MemoryProfile CreateLufia2GenericProfile()
        {
            // Offsets relative to WRAM Start (SNES 7E0000)
            return new MemoryProfile
            {
                Name = "Generic Lufia 2 (WRAM Scan)",
                ProcessName = "Generic",
                Gold = 0x2D9E,
                CharacterSlots = new[] { 0x2D8F, 0x2D90, 0x2D91, 0x2D92 },
                CapsuleSlotsStart = 0x34CF,
                CapsuleSlotsEnd = 0x34D5,
                InventoryStart = 0x2DA1,
                InventoryEnd = 0x2E60,
                ScenarioStart = 0x2C32,
                ScenarioEnd = 0x2C34,
                PointerBaseAddress = 0, // Cannot use pointer logic with WRAM base
                MapAddress = 0x351E, // 0xA3351E - 0xA30000
                SpoilerLogOffsetStart = 0, // Handled separately
                SpoilerLogOffsetEnd = 0,
                DungeonFlagStart = 0x2A96,
                DungeonFlagEnd = 0x2A9F,
                TransportFlag = 0x2CF5,
                ShipXFast = 0x379C,
                ShipXSlow = 0x379D,
                ShipYFast = 0x379F,
                ShipYSlow = 0x37A0,
                WalkXFast = 0x377F,
                WalkXSlow = 0x3780,
                WalkYFast = 0x3782,
                WalkYSlow = 0x3783,
                CapsuleSpriteOffset = 0 // Needs ROM base
            };
        }
        public static MemoryProfile CreateFromOffsets(int wramOffset, System.IntPtr scanRomBase, bool isNwa = false)
        {
            // Standard Offsets (defaults for x64)
            int Wram_Gold = 0x2D9E;
            int Wram_Party = 0x2D8F;
            int Wram_Inv = 0x2DA1;
            int Wram_Scen = 0x2C32;
            int Wram_Caps = 0x34CF;
            int Wram_Flags = 0x2A96;
            int Wram_Trans = 0x2CF5;
            int Wram_ShipX = 0x379C; 
            int Wram_Map = 0x351E;
            
            // NWA Specific Adjustments
            // In NWA, the distance between Gold and DungeonFlags is 0x302.
            // In x64, the distance is 0x308.
            // Since wramOffset is derived from x64 Gold logic, we must adjust the Flags offset to match NWA.
            if (isNwa)
            {
                Wram_Flags = 0x2A9C; // 0x2A96 + 6
            }
            
            const int Rom_CapsuleSprite = 0xBDCB8;
            
            return new MemoryProfile
            {
                Name = $"Scanned Profile ({(isNwa ? "NWA" : "x64")})",
                ProcessName = "Scanned",
                
                PointerBaseAddress = 0, 
                ScannedRomBase = scanRomBase,
                
                Gold = wramOffset + Wram_Gold,
                CharacterSlots = new[] { wramOffset + Wram_Party, wramOffset + Wram_Party + 1, wramOffset + Wram_Party + 2, wramOffset + Wram_Party + 3 },
                
                CapsuleSlotsStart = wramOffset + Wram_Caps,
                CapsuleSlotsEnd = wramOffset + Wram_Caps + 6,
                
                InventoryStart = wramOffset + Wram_Inv,
                InventoryEnd = wramOffset + Wram_Inv + 0xBF, 
                
                ScenarioStart = wramOffset + Wram_Scen,
                ScenarioEnd = wramOffset + Wram_Scen + 2,

                DungeonFlagStart = wramOffset + Wram_Flags,
                DungeonFlagEnd = wramOffset + Wram_Flags + 9, 

                TransportFlag = wramOffset + Wram_Trans,
                
                // Map
                MapAddress = wramOffset + Wram_Map,

                // Position (Approx offsets from x64 profile)
                ShipXFast = wramOffset + 0x379C,
                ShipXSlow = wramOffset + 0x379D,
                ShipYFast = wramOffset + 0x379F,
                ShipYSlow = wramOffset + 0x37A0,
                
                WalkXFast = wramOffset + 0x377F,
                WalkXSlow = wramOffset + 0x3780,
                WalkYFast = wramOffset + 0x3782,
                WalkYSlow = wramOffset + 0x3783,
                
                // ROM Related
                CapsuleSpriteOffset = Rom_CapsuleSprite, 
                
                SpoilerLogOffsetStart = 0, 
                SpoilerLogOffsetEnd = 0
            };
        }
    }
}
