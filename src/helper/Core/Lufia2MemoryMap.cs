namespace Lufia2AutoTracker.Helper.Core
{
    /// <summary>
    /// Canonical Lufia II addresses. WRAM values are offsets from the start of
    /// the emulator's linear 128 KiB WRAM image; ROM values are offsets from a
    /// verified, headerless ROM image. No host-process addresses belong here.
    /// </summary>
    public static class Lufia2MemoryMap
    {
        public static class Wram
        {
            public const int SnesBusBase = 0x7E0000;
            public const int Size = 0x20000;

            public static int FromSnesAddress(int address)
            {
                int offset = address - SnesBusBase;
                if (offset < 0 || offset >= Size)
                    throw new System.ArgumentOutOfRangeException(nameof(address));
                return offset;
            }

            public static int ToSnesAddress(int offset)
            {
                if (offset < 0 || offset >= Size)
                    throw new System.ArgumentOutOfRangeException(nameof(offset));
                return SnesBusBase + offset;
            }

            public const int Gold = 0x2D9E;

            public const int PartyStart = 0x2D8F;
            public const int PartyCount = 4;

            public const int InventoryStart = 0x2DA1;
            public const int InventoryLength = 0xBF;

            public const int ScenarioStart = 0x2C32;
            public const int ScenarioLength = 3;

            public const int CapsuleStart = 0x34CF;
            public const int CapsuleCount = 7;

            public const int DungeonFlagsStart = 0x2A96;
            public const int DungeonFlagsLength = 10;

            public const int Transport = 0x2CF5;

            public const int ShipXLow = 0x379C;
            public const int ShipXHigh = 0x379D;
            public const int ShipYLow = 0x379F;
            public const int ShipYHigh = 0x37A0;

            public const int WalkXLow = 0x377F;
            public const int WalkXHigh = 0x3780;
            public const int WalkYLow = 0x3782;
            public const int WalkYHigh = 0x3783;

            public const int Map = 0x351E;

            // Static randomizer strings used only to discover a candidate root.
            public const int SelanAnchor = 0x2F7E;
            public const int ArtyAnchor = 0x30FE;
            public const int LexisAnchor = 0x3326;
        }

        public static class Rom
        {
            public const int InternalHeader = 0xFFC0;
            public const int CapsuleSpriteTable = 0xBDCB8;
            public const int CapsuleSpriteStride = 10;
            public const int CapsuleSpriteCount = 7;
        }
    }
}
