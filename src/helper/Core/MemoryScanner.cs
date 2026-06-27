using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using Lufia2AutoTracker.Helper.Utils;

namespace Lufia2AutoTracker.Helper.Core
{
    public sealed class WramCandidate
    {
        public IntPtr Address { get; set; }
        public int Gold { get; set; }
        public int Score { get; set; }
        public string Evidence { get; set; } = string.Empty;
        public bool IsStrong => Score >= 80;
    }

    public static class MemoryScanner
    {
        private const int ScanChunkSize = 4 * 1024 * 1024;
        private const int MaxSignatureMatches = 128;
        private const int WramSnapshotSize = Lufia2MemoryMap.Wram.ShipYHigh + 1;

        private static readonly (string Name, byte[] Bytes, int Offset)[] WramSignatures = {
            ("SSelan", new byte[]{0x53,0x53,0x65,0x6C,0x61,0x6E}, Lufia2MemoryMap.Wram.SelanAnchor),
            ("AArty",  new byte[]{0x41,0x41,0x72,0x74,0x79},      Lufia2MemoryMap.Wram.ArtyAnchor),
            ("LLexis", new byte[]{0x4C,0x4C,0x65,0x78,0x69,0x73}, Lufia2MemoryMap.Wram.LexisAnchor)
        };

        public static List<IntPtr> ScanForSignature(
            Process process,
            byte[] signature,
            string mask,
            long minRegionSize = 0,
            int maxMatches = MaxSignatureMatches,
            bool writableOnly = false)
        {
            var matches = new HashSet<long>();
            if (process == null || process.HasExited || signature.Length == 0) return new List<IntPtr>();

            IntPtr currentAddress = IntPtr.Zero;
            long maxAddress = Environment.Is64BitProcess ? 0x7FFFFFFFFFFF : 0x7FFFFFFF;

            while ((long)currentAddress < maxAddress &&
                   NativeMethods.VirtualQueryEx(process.Handle, currentAddress, out var memInfo,
                       (uint)Marshal.SizeOf<NativeMethods.MEMORY_BASIC_INFORMATION>()) != 0)
            {
                long regionSize = memInfo.RegionSize.ToInt64();
                if (memInfo.State == NativeMethods.MEM_COMMIT &&
                    (writableOnly ? IsWritable(memInfo.Protect) : IsReadable(memInfo.Protect)) &&
                    regionSize >= Math.Max(signature.Length, minRegionSize))
                {
                    int overlap = Math.Max(0, signature.Length - 1);
                    long regionOffset = 0;

                    while (regionOffset < regionSize && matches.Count < maxMatches)
                    {
                        int requested = (int)Math.Min(ScanChunkSize, regionSize - regionOffset);
                        byte[] buffer = new byte[requested];
                        IntPtr chunkAddress = (IntPtr)((long)memInfo.BaseAddress + regionOffset);

                        if (NativeMethods.ReadProcessMemory(process.Handle, chunkAddress, buffer, requested, out var bytesRead))
                        {
                            int available = (int)Math.Min(requested, bytesRead.ToInt64());
                            foreach (int index in FindPatterns(buffer, available, signature, mask))
                            {
                                matches.Add((long)chunkAddress + index);
                                if (matches.Count >= maxMatches) break;
                            }
                        }

                        if (requested <= overlap) break;
                        regionOffset += requested - overlap;
                    }
                }

                long nextAddress = (long)memInfo.BaseAddress + regionSize;
                if (nextAddress <= (long)currentAddress || nextAddress >= maxAddress) break;
                currentAddress = (IntPtr)nextAddress;
            }

            return matches.OrderBy(value => value).Select(value => (IntPtr)value).ToList();
        }

        public static List<WramCandidate> ScanForWram(Process process)
        {
            var anchorCounts = new Dictionary<long, HashSet<string>>();

            foreach (var signature in WramSignatures)
            {
                Console.WriteLine($"[Scanner] Scanning for WRAM anchor '{signature.Name}'...");
                var locations = ScanForSignature(
                    process,
                    signature.Bytes,
                    new string('x', signature.Bytes.Length),
                    maxMatches: 64,
                    writableOnly: true);

                foreach (IntPtr location in locations)
                {
                    long baseAddress = (long)location - signature.Offset;
                    if (!anchorCounts.TryGetValue(baseAddress, out var anchors))
                    {
                        anchors = new HashSet<string>(StringComparer.Ordinal);
                        anchorCounts[baseAddress] = anchors;
                    }
                    anchors.Add(signature.Name);
                }
            }

            var candidates = new List<WramCandidate>();
            foreach (var pair in anchorCounts)
            {
                if (TryEvaluateWramCandidate(process, (IntPtr)pair.Key, pair.Value.Count, out var candidate))
                {
                    candidates.Add(candidate);
                }
            }

            if (!candidates.Any(candidate => candidate.IsStrong))
            {
                Console.WriteLine("[Scanner] No strong anchor candidate; starting bounded cluster scan...");
                candidates.AddRange(ScanWramClusters(process));
            }

            var result = candidates
                .GroupBy(candidate => (long)candidate.Address)
                .Select(group => group.OrderByDescending(candidate => candidate.Score).First())
                .OrderByDescending(candidate => candidate.Score)
                .ThenByDescending(candidate => candidate.Gold)
                .Take(20)
                .ToList();

            foreach (var candidate in result.Take(5))
            {
                Console.WriteLine($"[Scanner] WRAM candidate 0x{candidate.Address:X}: score={candidate.Score}, gold={candidate.Gold}, {candidate.Evidence}");
            }

            return result;
        }

        public static bool ValidateProfile(Process process, MemoryProfile profile, out string reason)
        {
            if (!profile.HasWram ||
                !TryRead(process, profile.ResolveWram(Lufia2MemoryMap.Wram.Gold), 3, out var goldBytes) ||
                !TryRead(process, profile.ResolveWram(Lufia2MemoryMap.Wram.PartyStart), Lufia2MemoryMap.Wram.PartyCount, out var party) ||
                !TryRead(process, profile.ResolveWram(Lufia2MemoryMap.Wram.Transport), 1, out var transport))
            {
                reason = "one or more required addresses were unreadable";
                return false;
            }

            int gold = ReadUInt24(goldBytes, 0);
            bool validParty = IsValidParty(party, 0, out int memberCount);
            bool validTransport = IsValidTransport(transport[0]);
            bool validGold = gold <= 9_999_999;

            reason = $"gold={gold}, partyMembers={memberCount}, transport=0x{transport[0]:X2}";
            return validGold && validParty && validTransport;
        }

        public static int ScoreWramSnapshot(byte[] snapshot, out int gold)
        {
            gold = 0;
            if (snapshot.Length < WramSnapshotSize) return 0;

            gold = ReadUInt24(snapshot, Lufia2MemoryMap.Wram.Gold);
            bool validGold = gold <= 9_999_999;
            bool validParty = IsValidParty(snapshot, Lufia2MemoryMap.Wram.PartyStart, out int memberCount);
            bool validTransport = IsValidTransport(snapshot[Lufia2MemoryMap.Wram.Transport]);
            int zeroCount = CountZeros(snapshot, Lufia2MemoryMap.Wram.InventoryStart, 100);

            return ScoreWramValues(validGold, validParty, memberCount, validTransport, zeroCount, 0);
        }

        public static IntPtr? ScanForSpoilerLog(Process process)
        {
            byte[] signature = System.Text.Encoding.ASCII.GetBytes("ITEM LOCATIONS");
            var matches = ScanForSignature(process, signature, new string('x', signature.Length), maxMatches: 8);
            return matches.Count > 0 ? matches[0] : null;
        }

        public static IntPtr? ScanForRom(Process process, IntPtr? wramHint = null)
        {
            var candidates = new HashSet<long>();
            var romSignatures = new (string Name, byte[] Bytes, int HeaderOffset)[] {
                ("LUFIA",    new byte[]{0x4C,0x55,0x46,0x49,0x41}, Lufia2MemoryMap.Rom.InternalHeader),
                ("L2-R",     new byte[]{0x4C,0x32,0x2D,0x52},      Lufia2MemoryMap.Rom.InternalHeader),
                ("L2-",      new byte[]{0x4C,0x32,0x2D},           Lufia2MemoryMap.Rom.InternalHeader),
                ("ESTPOLIS", new byte[]{0x45,0x53,0x54,0x50,0x4F,0x4C,0x49,0x53}, Lufia2MemoryMap.Rom.InternalHeader),
                ("Lufia II", new byte[]{0x4C,0x75,0x66,0x69,0x61,0x20,0x49,0x49}, Lufia2MemoryMap.Rom.InternalHeader)
            };

            foreach (var signature in romSignatures)
            {
                foreach (IntPtr location in ScanForSignature(
                    process,
                    signature.Bytes,
                    new string('x', signature.Bytes.Length),
                    maxMatches: 32))
                {
                    candidates.Add((long)location - signature.HeaderOffset);
                }
            }

            var sorted = wramHint.HasValue
                ? candidates.OrderBy(candidate => Math.Abs(candidate - (long)wramHint.Value))
                : candidates.OrderBy(candidate => candidate);

            foreach (long candidate in sorted)
            {
                IntPtr corrected = CorrectRomBase(process, (IntPtr)candidate);
                if (corrected != IntPtr.Zero)
                {
                    Console.WriteLine($"[Scanner] Verified ROM base 0x{corrected:X}");
                    return corrected;
                }
            }

            Console.WriteLine("[Scanner] No ROM candidate passed sprite-table validation; continuing with WRAM only.");
            return null;
        }

        private static bool TryEvaluateWramCandidate(
            Process process,
            IntPtr wramBase,
            int anchorCount,
            out WramCandidate candidate)
        {
            candidate = new WramCandidate { Address = wramBase };

            if (!TryRead(process, (IntPtr)((long)wramBase + Lufia2MemoryMap.Wram.Gold), 3, out var goldBytes) ||
                !TryRead(process, (IntPtr)((long)wramBase + Lufia2MemoryMap.Wram.PartyStart), Lufia2MemoryMap.Wram.PartyCount, out var party) ||
                !TryRead(process, (IntPtr)((long)wramBase + Lufia2MemoryMap.Wram.Transport), 1, out var transport) ||
                !TryRead(process, (IntPtr)((long)wramBase + Lufia2MemoryMap.Wram.InventoryStart), 100, out var inventory))
            {
                return false;
            }

            int gold = ReadUInt24(goldBytes, 0);
            bool validGold = gold <= 9_999_999;
            bool validParty = IsValidParty(party, 0, out int memberCount);
            bool validTransport = IsValidTransport(transport[0]);
            int zeroCount = CountZeros(inventory, 0, inventory.Length);
            int score = ScoreWramValues(validGold, validParty, memberCount, validTransport, zeroCount, anchorCount);

            if (!validGold || !validParty || !validTransport || score < 60) return false;

            candidate.Gold = gold;
            candidate.Score = score;
            candidate.Evidence = $"anchors={anchorCount}, partyMembers={memberCount}, inventoryZeros={zeroCount}, transport=0x{transport[0]:X2}";
            return true;
        }

        private static IEnumerable<WramCandidate> ScanWramClusters(Process process)
        {
            var candidates = new List<WramCandidate>();
            IntPtr currentAddress = IntPtr.Zero;
            long maxAddress = Environment.Is64BitProcess ? 0x7FFFFFFFFFFF : 0x7FFFFFFF;

            while ((long)currentAddress < maxAddress && candidates.Count < 200 &&
                   NativeMethods.VirtualQueryEx(process.Handle, currentAddress, out var memInfo,
                       (uint)Marshal.SizeOf<NativeMethods.MEMORY_BASIC_INFORMATION>()) != 0)
            {
                long regionSize = memInfo.RegionSize.ToInt64();
                if (memInfo.State == NativeMethods.MEM_COMMIT && IsWritable(memInfo.Protect) && regionSize >= 0x100)
                {
                    long regionOffset = 0;
                    const int overlap = 0x200;
                    while (regionOffset < regionSize && candidates.Count < 200)
                    {
                        int requested = (int)Math.Min(ScanChunkSize, regionSize - regionOffset);
                        byte[] buffer = new byte[requested];
                        IntPtr chunkAddress = (IntPtr)((long)memInfo.BaseAddress + regionOffset);

                        if (NativeMethods.ReadProcessMemory(process.Handle, chunkAddress, buffer, requested, out var bytesRead))
                        {
                            int available = (int)Math.Min(requested, bytesRead.ToInt64());
                            int transportDistance = Lufia2MemoryMap.Wram.Gold - Lufia2MemoryMap.Wram.Transport;
                            int partyDistance = Lufia2MemoryMap.Wram.Gold - Lufia2MemoryMap.Wram.PartyStart;
                            int inventoryDistance = Lufia2MemoryMap.Wram.InventoryStart - Lufia2MemoryMap.Wram.Gold;
                            for (int i = transportDistance; i < available - 103; i++)
                            {
                                int gold = ReadUInt24(buffer, i);
                                if (gold > 9_999_999) continue;

                                int partyOffset = i - partyDistance;
                                if (!IsValidParty(buffer, partyOffset, out int memberCount)) continue;

                                byte transport = buffer[i - transportDistance];
                                if (!IsValidTransport(transport)) continue;

                                int inventoryOffset = i + inventoryDistance;
                                int zeroCount = CountZeros(buffer, inventoryOffset, Math.Min(100, available - inventoryOffset));
                                int score = ScoreWramValues(true, true, memberCount, true, zeroCount, 0);
                                if (score < 70) continue;

                                IntPtr wramBase = (IntPtr)((long)chunkAddress + i - Lufia2MemoryMap.Wram.Gold);
                                candidates.Add(new WramCandidate {
                                    Address = wramBase,
                                    Gold = gold,
                                    Score = score,
                                    Evidence = $"cluster, partyMembers={memberCount}, inventoryZeros={zeroCount}, transport=0x{transport:X2}"
                                });
                            }
                        }

                        if (requested <= overlap) break;
                        regionOffset += requested - overlap;
                    }
                }

                long nextAddress = (long)memInfo.BaseAddress + regionSize;
                if (nextAddress <= (long)currentAddress || nextAddress >= maxAddress) break;
                currentAddress = (IntPtr)nextAddress;
            }

            return candidates;
        }

        private static IntPtr CorrectRomBase(Process process, IntPtr romBase)
        {
            const int capsuleSpriteOffset = Lufia2MemoryMap.Rom.CapsuleSpriteTable;
            long expectedTable = (long)romBase + capsuleSpriteOffset;

            if (ScoreSpriteTable(process, (IntPtr)expectedTable) >= 5) return romBase;

            const int range = 0x40000;
            IntPtr startAddress = (IntPtr)(expectedTable - range);
            byte[] buffer = new byte[range * 2];
            if (!NativeMethods.ReadProcessMemory(process.Handle, startAddress, buffer, buffer.Length, out var bytesRead))
            {
                return IntPtr.Zero;
            }

            int available = (int)Math.Min(buffer.Length, bytesRead.ToInt64());
            int bestScore = 0;
            int bestIndex = -1;
            for (int index = 0; index + 62 < available; index += 2)
            {
                int score = ScoreSpriteTable(buffer, index);
                if (score > bestScore)
                {
                    bestScore = score;
                    bestIndex = index;
                }
            }

            if (bestScore < 5 || bestIndex < 0) return IntPtr.Zero;
            long tableAddress = (long)startAddress + bestIndex;
            return (IntPtr)(tableAddress - capsuleSpriteOffset);
        }

        private static int ScoreSpriteTable(Process process, IntPtr address)
        {
            int tableLength =
                (Lufia2MemoryMap.Rom.CapsuleSpriteCount - 1) * Lufia2MemoryMap.Rom.CapsuleSpriteStride + 2;
            if (!TryRead(process, address, tableLength, out var bytes)) return 0;
            return ScoreSpriteTable(bytes, 0);
        }

        private static int ScoreSpriteTable(byte[] bytes, int start)
        {
            var validIds = new HashSet<ushort> {
                0x4600, 0x0046, 0xA502, 0x02A5, 0x4305, 0x0543, 0xAF07, 0x07AF,
                0x580A, 0x0A58, 0x0B0D, 0x0D0B, 0x880F, 0x0F88, 0x0E15, 0x150E
            };

            int score = 0;
            for (int slot = 0; slot < Lufia2MemoryMap.Rom.CapsuleSpriteCount; slot++)
            {
                int index = start + slot * Lufia2MemoryMap.Rom.CapsuleSpriteStride;
                if (index + 1 >= bytes.Length) break;
                ushort value = (ushort)(bytes[index] | (bytes[index + 1] << 8));
                if (validIds.Contains(value)) score++;
            }
            return score;
        }

        private static int ScoreWramValues(
            bool validGold,
            bool validParty,
            int memberCount,
            bool validTransport,
            int zeroCount,
            int anchorCount)
        {
            int score = 0;
            if (validGold) score += 20;
            if (validParty && memberCount > 0) score += 40;
            if (validTransport) score += 20;
            if (zeroCount >= 20) score += 30;
            else if (zeroCount >= 5) score += 10;
            score += Math.Min(anchorCount, WramSignatures.Length) * 25;
            return score;
        }

        private static bool IsValidParty(byte[] bytes, int offset, out int memberCount)
        {
            memberCount = 0;
            if (offset < 0 || offset + 4 > bytes.Length) return false;

            var seen = new HashSet<byte>();
            for (int index = 0; index < 4; index++)
            {
                byte id = bytes[offset + index];
                if (id == 0xFF) continue;
                if (id > 6 || !seen.Add(id)) return false;
                memberCount++;
            }
            return memberCount > 0;
        }

        private static bool IsValidTransport(byte value) => value <= 0x05 || value == 0xFF;

        private static int CountZeros(byte[] bytes, int offset, int count)
        {
            int end = Math.Min(bytes.Length, offset + Math.Max(0, count));
            int zeros = 0;
            for (int index = Math.Max(0, offset); index < end; index++)
            {
                if (bytes[index] == 0) zeros++;
            }
            return zeros;
        }

        private static int ReadUInt24(byte[] bytes, int offset) =>
            bytes[offset] | (bytes[offset + 1] << 8) | (bytes[offset + 2] << 16);

        private static bool TryRead(Process process, IntPtr address, int size, out byte[] bytes)
        {
            bytes = new byte[size];
            return NativeMethods.ReadProcessMemory(process.Handle, address, bytes, size, out var bytesRead) &&
                   bytesRead.ToInt64() == size;
        }

        private static bool IsReadable(uint protection)
        {
            if ((protection & NativeMethods.PAGE_GUARD) != 0 || (protection & NativeMethods.PAGE_NOACCESS) != 0) return false;
            uint baseProtection = protection & 0xFF;
            return baseProtection == NativeMethods.PAGE_READONLY ||
                   baseProtection == NativeMethods.PAGE_READWRITE ||
                   baseProtection == NativeMethods.PAGE_WRITECOPY ||
                   baseProtection == NativeMethods.PAGE_EXECUTE_READ ||
                   baseProtection == NativeMethods.PAGE_EXECUTE_READWRITE ||
                   baseProtection == NativeMethods.PAGE_EXECUTE_WRITECOPY;
        }

        private static bool IsWritable(uint protection)
        {
            if ((protection & NativeMethods.PAGE_GUARD) != 0 || (protection & NativeMethods.PAGE_NOACCESS) != 0) return false;
            uint baseProtection = protection & 0xFF;
            return baseProtection == NativeMethods.PAGE_READWRITE ||
                   baseProtection == NativeMethods.PAGE_WRITECOPY ||
                   baseProtection == NativeMethods.PAGE_EXECUTE_READWRITE ||
                   baseProtection == NativeMethods.PAGE_EXECUTE_WRITECOPY;
        }

        private static IEnumerable<int> FindPatterns(
            byte[] buffer,
            int available,
            byte[] signature,
            string mask)
        {
            int lastStart = available - signature.Length;
            for (int index = 0; index <= lastStart; index++)
            {
                bool found = true;
                for (int signatureIndex = 0; signatureIndex < signature.Length; signatureIndex++)
                {
                    if (mask[signatureIndex] == 'x' && buffer[index + signatureIndex] != signature[signatureIndex])
                    {
                        found = false;
                        break;
                    }
                }
                if (found) yield return index;
            }
        }
    }
}
