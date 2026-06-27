using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Lufia2AutoTracker.Helper.Utils;

namespace Lufia2AutoTracker.Helper.Core
{
    public class DataReaders
    {
        private readonly IntPtr _processHandle;
        private readonly MemoryProfile _profile;
        private int _requiredReadFailures;

        public bool LastRequiredReadSucceeded { get; private set; } = true;

        public DataReaders(IntPtr processHandle, MemoryProfile profile)
        {
            _processHandle = processHandle;
            _profile = profile;
        }

        private byte[] ReadWram(int offset, int size, bool required = true)
        {
            IntPtr address = _profile.ResolveWram(offset);
            byte[] buffer = new byte[size];
            IntPtr bytesRead;
            if (NativeMethods.ReadProcessMemory(_processHandle, address, buffer, size, out bytesRead) &&
                bytesRead.ToInt64() == size)
            {
                return buffer;
            }
            else
            {
                if (required) _requiredReadFailures++;
                int err = System.Runtime.InteropServices.Marshal.GetLastWin32Error();
                Console.WriteLine($"[DEBUG] ReadMemory FAILED at 0x{address.ToString("X")} (Size: {size}) - Win32 Error: {err}");
            }
            return new byte[size]; // Return empty on failure
        }
        
        private byte ReadByte(int offset) => ReadWram(offset, 1)[0];

        public GameState ReadGameState()
        {
            _requiredReadFailures = 0;
            var state = new GameState();
            try { state.Inventory = ReadInventory(); } catch {}
            try { state.ScenarioItems = ReadScenario(); } catch {}
            try { state.Capsules = ReadCapsules(); } catch {}
            try { state.CapsuleSpriteValues = ReadCapsuleSpriteValues(); } catch {}
            try { state.Characters = ReadCharacters(); } catch {}
            try { state.ClearedLocations = ReadDungeonFlags(); } catch {}
            
            var pos = ReadPosition();
            state.PlayerX = pos.X;
            state.PlayerY = pos.Y;
            state.TransportMode = pos.Mode;

            LastRequiredReadSucceeded = _requiredReadFailures == 0;

            return state;
        }

        // --- Inventory Logic ---
        private List<string> ReadInventory()
        {
            var obtained = new List<string>();
            var invData = ReadWram(Lufia2MemoryMap.Wram.InventoryStart, Lufia2MemoryMap.Wram.InventoryLength);
            
            // Read Scenario Block (used for Special items bitmask)
            var scenarioData = ReadWram(Lufia2MemoryMap.Wram.ScenarioStart, Lufia2MemoryMap.Wram.ScenarioLength);
            // v1.3: reversed_memory_value = memory_value[::-1]
            Array.Reverse(scenarioData); 
            string binaryString = string.Join("", scenarioData.Select(b => Convert.ToString(b, 2).PadLeft(8, '0')));

            foreach (var item in GameData.Tools)
            {
                if (item.Type == "normal")
                {
                    // "0xAABB" -> byte string check
                    ushort val = Convert.ToUInt16(item.ObtainedValue, 16);
                    byte sub = (byte)(val & 0xFF);
                    byte main = (byte)((val >> 8) & 0xFF);
                    
                    // Python: item_bytes in inventory_data
                    // Simple distinct check OK? Python checks if SUBSEQUENCE exists.
                    if (ContainsSequence(invData, new byte[] { sub, main }))
                    {
                        obtained.Add(item.Name);
                    }
                }
                else if (item.Type == "special")
                {
                    // "0001 0000 ..."
                    CheckBitmask(item.Name, item.ObtainedValue, binaryString, obtained);
                }
            }
            return obtained;
        }

        private bool ContainsSequence(byte[] haystack, byte[] needle)
        {
            for (int i = 0; i <= haystack.Length - needle.Length; i++)
            {
                if (haystack[i] == needle[0] && haystack[i+1] == needle[1]) return true;
            }
            return false;
        }

        // --- Scenario Logic ---
        private List<string> ReadScenario()
        {
            var obtained = new List<string>();
            var scenarioData = ReadWram(Lufia2MemoryMap.Wram.ScenarioStart, Lufia2MemoryMap.Wram.ScenarioLength);
            Array.Reverse(scenarioData);
            string binaryString = string.Join("", scenarioData.Select(b => Convert.ToString(b, 2).PadLeft(8, '0')));

            foreach (var item in GameData.ScenarioItems)
            {
                 CheckBitmask(item.Name, item.ObtainedValue, binaryString, obtained);
            }
            return obtained;
        }

        private void CheckBitmask(string name, string maskPattern, string binaryString, List<string> list)
        {
            string cleanMask = maskPattern.Replace(" ", "");
            // v1.3 Logic: if bit_value == '1': check index
            // It iterates "binary_string". If it finds a '1', calculates index.
            // Simplified: We just check if the Mask aligns with the Data?
            // "if obtained_value_bin[-obtained_index] == '1'"
            // This implies: For every '1' in the *game memory*, check if the Item's mask has a '1' at that same index (from right).
            // Actually v1.3 says:
            // "for bit_position, bit_value in enumerate(binary_string):
            //    if bit_value == '1': ... obtained_index = len - pos ... if item_mask[-idx] == '1': FOUND"
            
            // Replicating:
            for (int i = 0; i < binaryString.Length; i++)
            {
                if (binaryString[i] == '1')
                {
                    int obtainedIndex = binaryString.Length - i; // 1-based index from end
                    if (cleanMask.Length >= obtainedIndex)
                    {
                        // Check N-th char from end
                        char maskBit = cleanMask[cleanMask.Length - obtainedIndex];
                         if (maskBit == '1')
                         {
                             list.Add(name);
                             break;
                         }
                    }
                }
            }
        }

        // --- Character Logic ---
        private List<string> ReadCharacters()
        {
            var chars = new List<string>();
            for (int slot = 0; slot < Lufia2MemoryMap.Wram.PartyCount; slot++)
            {
                byte id = ReadByte(Lufia2MemoryMap.Wram.PartyStart + slot);
                string name = GameData.GetCharacterName(id);
                if (name != "Empty" && name != "Unknown") chars.Add(name);
            }
            return chars;
        }

        public List<string> ReadCapsules()
        {
            var capsules = new List<string>();
            int start = Lufia2MemoryMap.Wram.CapsuleStart;
            int end = start + Lufia2MemoryMap.Wram.CapsuleCount - 1;
            List<string> capsuleNames = GetCapsuleNames(); 
            
            for (int addr = start; addr <= end; addr++)
            {
                byte val = ReadByte(addr);
                if (val != 0x00)
                {
                    int idx = addr - start;
                    if (idx < capsuleNames.Count) capsules.Add(capsuleNames[idx]);
                }
            }
            return capsules;
        }

        public List<string> ReadCapsuleSpriteValues()
        {
            var values = new List<string>();
            if (!_profile.HasRom)
            {
                return values;
            }

            for (int i = 0; i < Lufia2MemoryMap.Rom.CapsuleSpriteCount; i++)
            {
                IntPtr address = _profile.ResolveRom(
                    Lufia2MemoryMap.Rom.CapsuleSpriteTable +
                    i * Lufia2MemoryMap.Rom.CapsuleSpriteStride);
                byte[] bytes = new byte[2];
                IntPtr bytesRead;
                NativeMethods.ReadProcessMemory(_processHandle, address, bytes, 2, out bytesRead);

                // Hex format "A502" upper case
                string hex = $"{bytes[0]:X2}{bytes[1]:X2}";
                values.Add(hex);
            }
            return values;
        }

        private List<string> GetCapsuleNames()
        {
             return new List<string> { "Jelze", "Flash", "Gusto", "Zeppy", "Darbi", "Sully", "Blaze" };
        }

        // --- Position Logic ---
        private (int X, int Y, string Mode) ReadPosition()
        {
            byte mode = ReadByte(Lufia2MemoryMap.Wram.Transport);
            int xFast, xSlow, yFast, ySlow;
            string modeStr = "walk";

            if (mode == 0xFF) // Ship / Airship
            {
                modeStr = "ship";
                xFast = Lufia2MemoryMap.Wram.ShipXLow; xSlow = Lufia2MemoryMap.Wram.ShipXHigh;
                yFast = Lufia2MemoryMap.Wram.ShipYLow; ySlow = Lufia2MemoryMap.Wram.ShipYHigh;
            }
            else // Walk (0x00) or other
            {
                xFast = Lufia2MemoryMap.Wram.WalkXLow; xSlow = Lufia2MemoryMap.Wram.WalkXHigh;
                yFast = Lufia2MemoryMap.Wram.WalkYLow; ySlow = Lufia2MemoryMap.Wram.WalkYHigh;
            }

            int x = (ReadByte(xSlow) << 8) | ReadByte(xFast);
            int y = (ReadByte(ySlow) << 8) | ReadByte(yFast);
            return (x, y, modeStr);
        }

        // --- Dungeon Flags ---
        private List<string> ReadDungeonFlags()
        {
            var cleared = new List<string>();
            int start = Lufia2MemoryMap.Wram.DungeonFlagsStart;
            int size = Lufia2MemoryMap.Wram.DungeonFlagsLength;
            byte[] flags = ReadWram(start, size);

            foreach (var d in GameData.Dungeons)
            {
                // Logic: d.Address is now Normalized (0, 1, 2...)
                int relativeOffset = d.Address;
                if (relativeOffset >= 0 && relativeOffset < size)
                {
                     byte val = flags[relativeOffset];
                     // "flag" in JSON is hex string like "0x80"
                     byte mask = Convert.ToByte(d.Flag, 16);
                     if ((val & mask) != 0)
                     {
                         cleared.Add(d.Location);
                     }
                }
            }
            return cleared;
        }

        private IntPtr _overrideSpoilerLogAddress = IntPtr.Zero;

        public void SetSpoilerLogAddress(IntPtr address)
        {
             _overrideSpoilerLogAddress = address;
        }

        // --- Spoiler Log ---
        public List<Dictionary<string, string>> ReadSpoilerLog()
        {
            var logs = new List<Dictionary<string, string>>();
            try
            {
                long start;
                int size;
                
                if (_overrideSpoilerLogAddress != IntPtr.Zero)
                {
                    // If override is set, we assume it POINTS to the "ITEM LOCATIONS" string start.
                    // We want to read enough buffer around/after it.
                    // Let's assume a reasonable size, e.g. 50KB.
                    start = (long)_overrideSpoilerLogAddress;
                    size = 50000;
                }
                else return logs;
                
                if (size <= 0 || size > 500000) 
                {
                    return logs; 
                }

                IntPtr address = (IntPtr)(long)start; // Absolute
                byte[] buffer = new byte[size];
                IntPtr read;
                if (!NativeMethods.ReadProcessMemory(_processHandle, address, buffer, size, out read))
                {
                     return logs;
                }

                string text = Encoding.ASCII.GetString(buffer);

                int idx = text.IndexOf("ITEM LOCATIONS");
                if (idx == -1) 
                {
                    return logs;
                }
                
                string content = text.Substring(idx + "ITEM LOCATIONS".Length);
                string niceText = Regex.Replace(content, "([a-z])([A-Z])", "$1 $2");
                var matches = Regex.Matches(niceText, @"[A-Za-z\s]+");
                var words = matches.Cast<Match>()
                                   .Select(m => m.Value.Trim())
                                   .Where(s => !string.IsNullOrWhiteSpace(s))
                                   .ToList();

                 for (int i = 0; i < words.Count - 2; i += 3)
                 {
                     logs.Add(new Dictionary<string, string> {
                         { "item", words[i] },
                         { "location", words[i+1] },
                         { "boss", words[i+2] }
                     });
                 }
            }
            catch (Exception)
            {
                // Silent catch
            }
            return logs;
        }

    }
}
