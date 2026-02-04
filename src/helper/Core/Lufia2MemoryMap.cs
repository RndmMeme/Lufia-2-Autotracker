using System.Collections.Generic;

namespace Lufia2AutoTracker.Helper.Core
{
    public static class Lufia2MemoryMap
    {
        // Offsets relative to WRAM Start (7E00000)
        // Derived from v1.3: Gold is at 0x2D9E relative to base 0xA30000
        
        public const int Offset_Gold = 0x2D9E; 
        
        // Character Slots (0x2D8F, 0x2D90, 0x2D91, 0x2D92) - 1 byte each?
        // Actually v1.3 "character_slots": ["0xA32D8F", "0xA32D90", "0xA32D91", "0xA32D92"]
        public const int Offset_PartySlot1 = 0x2D8F;
        public const int Offset_PartySlot2 = 0x2D90;
        public const int Offset_PartySlot3 = 0x2D91;
        public const int Offset_PartySlot4 = 0x2D92;

        public const int Offset_Inventory_Start = 0x2DA1;
        public const int Offset_Inventory_End = 0x2E60;

        // Dungeon Flags (Scenario) - need to check logic more deeply, but sticking to basics
        public const int Offset_DungeonFlags_Start = 0x2A96; // Derived from v1.3 if matching

        // Pointer Base Address (for Spoiler Log) - specific to Snes9x implementation in v1.3? 
        // In v1.3 it says "pointer_base_address" is used to calculated spoiler log.
        // If we scan process memory, the spoiler log is in the ROM area usually? Or RAM?
        // v1.3 says: "scan_spoiler_log" reads from "shop_table_pointer".
        
    }
}
