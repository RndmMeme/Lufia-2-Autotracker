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
        private IntPtr _processHandle;
        private IntPtr _baseAddress;
        private MemoryProfile _profile;

        public DataReaders(IntPtr processHandle, IntPtr baseAddress, MemoryProfile profile)
        {
            _processHandle = processHandle;
            _baseAddress = baseAddress;
            _profile = profile;
        }

        private byte[] ReadMemory(int offset, int size)
        {
            IntPtr address = (IntPtr)((long)_baseAddress + offset);
            byte[] buffer = new byte[size];
            IntPtr bytesRead;
            if (NativeMethods.ReadProcessMemory(_processHandle, address, buffer, size, out bytesRead))
            {
                return buffer;
            }
            return new byte[size]; // Return empty on failure
        }
        
        private byte ReadByte(int offset) => ReadMemory(offset, 1)[0];
        private ushort ReadUShort(int offset) => BitConverter.ToUInt16(ReadMemory(offset, 2), 0);
        private uint ReadUInt(int offset) => BitConverter.ToUInt32(ReadMemory(offset, 4), 0);

        public GameState ReadGameState()
        {
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

            return state;
        }

        // --- Inventory Logic ---
        private List<string> ReadInventory()
        {
            var obtained = new List<string>();
            var invData = ReadMemory(_profile.InventoryStart, _profile.InventoryEnd - _profile.InventoryStart);
            
            // Read Scenario Block (used for Special items bitmask)
            var scenarioData = ReadMemory(_profile.ScenarioStart, _profile.ScenarioEnd - _profile.ScenarioStart + 1);
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
            var scenarioData = ReadMemory(_profile.ScenarioStart, _profile.ScenarioEnd - _profile.ScenarioStart + 1);
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
            foreach (var offset in _profile.CharacterSlots)
            {
                byte id = ReadByte(offset);
                string name = GameData.GetCharacterName(id);
                if (name != "Empty" && name != "Unknown") chars.Add(name);
            }
            return chars;
        }

        public List<string> ReadCapsules()
        {
            var capsules = new List<string>();
            int start = _profile.CapsuleSlotsStart;
            int end = _profile.CapsuleSlotsEnd;
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
            long baseOffset;

            if (_profile.ScannedRomBase != IntPtr.Zero)
            {
                // Use Scanned Absolute Address
                baseOffset = (long)_profile.ScannedRomBase + _profile.CapsuleSpriteOffset;
            }
            else
            {
                // Fallback to Pointer Logic (Relative to Base)
                // 1:1 logic: Add ROM Start + Offset (User request)
                uint romStart = ReadUInt(_profile.PointerBaseAddress);
                baseOffset = romStart + _profile.CapsuleSpriteOffset;
            }

            for (int i = 0; i < 7; i++)
            {
                // Each sprite definition is 10 bytes apart (Confirmed by Debug Log: A502 at 0, 0B0D at 10)
                long addr = baseOffset + (i * 10);
                byte[] bytes = new byte[2];
                IntPtr bytesRead;
                NativeMethods.ReadProcessMemory(_processHandle, (IntPtr)addr, bytes, 2, out bytesRead);

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
            byte mode = ReadByte(_profile.TransportFlag);
            int xFast, xSlow, yFast, ySlow;
            string modeStr = "walk";

            if (mode == 0xFF) // Ship / Airship
            {
                modeStr = "ship";
                xFast = _profile.ShipXFast; xSlow = _profile.ShipXSlow;
                yFast = _profile.ShipYFast; ySlow = _profile.ShipYSlow;
            }
            else // Walk (0x00) or other
            {
                xFast = _profile.WalkXFast; xSlow = _profile.WalkXSlow;
                yFast = _profile.WalkYFast; ySlow = _profile.WalkYSlow;
            }

            int x = (ReadByte(xSlow) << 8) | ReadByte(xFast);
            int y = (ReadByte(ySlow) << 8) | ReadByte(yFast);
            return (x, y, modeStr);
        }

        // --- Dungeon Flags ---
        private List<string> ReadDungeonFlags()
        {
            var cleared = new List<string>();
            int start = _profile.DungeonFlagStart;
            int size = _profile.DungeonFlagEnd - start + 1;
            byte[] flags = ReadMemory(start, size);

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
                long start, end;
                int size;
                
                if (_overrideSpoilerLogAddress != IntPtr.Zero)
                {
                    // If override is set, we assume it POINTS to the "ITEM LOCATIONS" string start.
                    // We want to read enough buffer around/after it.
                    // Let's assume a reasonable size, e.g. 50KB.
                    start = (long)_overrideSpoilerLogAddress;
                    size = 50000;
                    end = start + size;
                }
                else
                {
                    uint ptrVal = ReadUInt(_profile.PointerBaseAddress);
                    if (ptrVal == 0) return logs; // Pointer logic failed or disabled

                    start = ptrVal + _profile.SpoilerLogOffsetStart;
                    end = ptrVal + _profile.SpoilerLogOffsetEnd;
                    size = (int)(end - start);
                }
                
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
