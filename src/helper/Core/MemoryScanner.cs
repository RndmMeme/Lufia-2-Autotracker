using System;
using System.Diagnostics;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using Lufia2AutoTracker.Helper.Utils;

namespace Lufia2AutoTracker.Helper.Core
{
    public class WramCandidate
    {
        public IntPtr Address { get; set; }
        public int Gold { get; set; }
        public int Score { get; set; }
        public bool IsStrong => Gold > 0;
    }

    public class MemoryScanner
    {
        public static List<IntPtr> ScanForSignature(Process process, byte[] signature, string mask, long minRegionSize = 0)
        {
            List<IntPtr> matches = new List<IntPtr>();
            if (process == null || process.HasExited) return matches;

            long start = 0;
            long end = 0x7FFFFFFFFFFF; 

            IntPtr currentAddr = (IntPtr)start;
            NativeMethods.MEMORY_BASIC_INFORMATION memInfo = new NativeMethods.MEMORY_BASIC_INFORMATION();

            while ((long)currentAddr < end && NativeMethods.VirtualQueryEx(process.Handle, currentAddr, out memInfo, (uint)Marshal.SizeOf(memInfo)) != 0)
            {
                if (memInfo.State == NativeMethods.MEM_COMMIT && 
                   (memInfo.Protect == NativeMethods.PAGE_READWRITE || memInfo.Protect == NativeMethods.PAGE_EXECUTE_READWRITE ||
                    memInfo.Protect == 0x02 /* PAGE_READONLY */ || memInfo.Protect == 0x20 /* PAGE_EXECUTE_READ */))
                {
                    // Check Min Region Size
                    if ((long)memInfo.RegionSize >= signature.Length && (long)memInfo.RegionSize >= minRegionSize)
                    {
                        byte[] buffer = new byte[(int)memInfo.RegionSize];
                        IntPtr bytesRead;
                        
                        if (NativeMethods.ReadProcessMemory(process.Handle, memInfo.BaseAddress, buffer, buffer.Length, out bytesRead))
                        {
                            int matchIndex = FindPattern(buffer, signature, mask);
                            if (matchIndex != -1)
                            {
                                matches.Add((IntPtr)((long)memInfo.BaseAddress + matchIndex));
                            }
                        }
                    }
                }
                
                long nextAddress = (long)memInfo.BaseAddress + (long)memInfo.RegionSize;
                // Safely advance
                if (nextAddress <= (long)currentAddr) break; 
                currentAddr = (IntPtr)nextAddress;
            }

            return matches;
        }

        public static List<WramCandidate> ScanForWram(Process process)
        {
            var candidates = new List<WramCandidate>();
            if (process == null || process.HasExited) return candidates;

            // 1. Precise Signature Scans (Names are static in Randomizer)
            // SSelan (0x2F7E), AArty (0x30FE), LLexis (0x3326)
            var signatures = new List<(string, byte[], int)> {
                ("SSelan", new byte[]{0x53,0x53,0x65,0x6C,0x61,0x6E}, 0x2F7E),
                ("AArty",  new byte[]{0x41,0x41,0x72,0x74,0x79},      0x30FE),
                ("LLexis", new byte[]{0x4C,0x4C,0x65,0x78,0x69,0x73}, 0x3326)
            };

            foreach (var sig in signatures)
            {
                try 
                {
                    Console.WriteLine($"[Scanner] Scanning for Signature '{sig.Item1}'...");
                    var matches = ScanForSignature(process, sig.Item2, new string('x', sig.Item2.Length));
                    IntPtr? addr = matches.Count > 0 ? (IntPtr?)matches[0] : null;
                    
                    if (addr.HasValue)
                    {
                        IntPtr wramBase = (IntPtr)((long)addr.Value - sig.Item3);
                        
                        // Verify Gold
                        byte[] gBuf = new byte[4];
                        IntPtr read;
                        IntPtr goldAddr = (IntPtr)((long)wramBase + 0x2D9E);
                        
                        if (NativeMethods.ReadProcessMemory(process.Handle, goldAddr, gBuf, 4, out read))
                        {
                            int gold = gBuf[0] | (gBuf[1] << 8) | (gBuf[2] << 16);
                            
                            Console.WriteLine($"[Scanner] FOUND Signature '{sig.Item1}' at 0x{addr.Value.ToString("X")}");
                            // Console.WriteLine($"[Scanner] Derived WRAM Base: 0x{wramBase.ToString("X")} (Gold: {gold})");
                            
                            if (gold >= 0 && gold < 10000000)
                            {
                                 return new List<WramCandidate> { new WramCandidate { Address = wramBase, Gold = gold, Score = 100 } };
                            }
                        }
                    }
                } 
                catch (Exception ex)
                {
                    Console.WriteLine($"[Scanner] Signature Scan Error: {ex.Message}");
                }
            }

            IntPtr currentAddress = IntPtr.Zero;
            long maxAddress = 0x7FFFFFFFFFFF; 
            
            // Relative Offsets from GOLD
            // Gold = 0
            // Party = -15 (0xF)
            // Transport = -169 (0xA9)
            
            Console.WriteLine("[Scanner] Starting Cluster Scan for WRAM...");

            while (true)
            {
                // Query
                NativeMethods.MEMORY_BASIC_INFORMATION memInfo = new NativeMethods.MEMORY_BASIC_INFORMATION();
                int result = NativeMethods.VirtualQueryEx(process.Handle, currentAddress, out memInfo, (uint)Marshal.SizeOf(memInfo));
                if (result == 0) break;

                // Check Region
                if (memInfo.State == NativeMethods.MEM_COMMIT && 
                   (memInfo.Protect == NativeMethods.PAGE_READWRITE || memInfo.Protect == NativeMethods.PAGE_EXECUTE_READWRITE) &&
                    memInfo.RegionSize >= 0x100) // 256 bytes min to contain the cluster
                {
                    byte[] buffer = new byte[(int)memInfo.RegionSize];
                    IntPtr bytesRead;

                    if (NativeMethods.ReadProcessMemory(process.Handle, memInfo.BaseAddress, buffer, buffer.Length, out bytesRead))
                    {
                        // Scan for Gold (i) - Scan EVERY BYTE to handle unaligned memory
                        // Snes9x NWA Gold Address (e.g. E2CF52) is 2-byte aligned, not 4-byte.
                        // Scanning every byte ensures we don't miss it.
                        for (int i = 0xA9; i < buffer.Length - 4; i++)
                        {
                            // 1. Check Gold Value (i)
                            int gold = buffer[i] | (buffer[i + 1] << 8) | (buffer[i + 2] << 16);
                            if (gold > 9999999) continue; 

                            // 2. Check Party (i - 15)
                            int pOffset = i - 15;
                            // Fast Filter
                            if (buffer[pOffset] > 6) continue;

                            bool partyValid = true;
                            bool[] seenIds = new bool[7]; 
                            int validMembers = 0;
                            string partyDebug = "";

                            for (int p = 0; p < 4; p++)
                            {
                                byte id = buffer[pOffset + p];
                                partyDebug += $"{id:X2} ";
                                if (id == 0xFF) continue; 
                                if (id > 6) { partyValid = false; break; }
                                if (seenIds[id]) { partyValid = false; break; }
                                seenIds[id] = true;
                                validMembers++;
                            }

                            if (!partyValid) continue;
                            if (validMembers == 0) continue;

                            // 3. Check Transport (i - 169)
                            int tOffset = i - 169;
                            byte transport = buffer[tOffset];
                            if (!(transport <= 0x05 || transport == 0xFF)) continue;
                            
                            // FOUND CANDIDATE (Gold Address)
                            // Calculate WRAM Base
                            IntPtr goldAddr = (IntPtr)((long)memInfo.BaseAddress + i);
                            IntPtr wramBase = (IntPtr)((long)goldAddr - 0x2D9E); 
                            
                            // 4. Structure Check (Inventory Zeros)
                            // Real inventory (at i+3) has many 0x00 bytes. Random memory does not.
                            int invOffset = i + 3;
                            int zeroCount = 0;
                            if (invOffset < buffer.Length)
                            {
                                int checkLen = Math.Min(100, buffer.Length - invOffset);
                                for (int z = 0; z < checkLen; z++) 
                                {
                                    if (buffer[invOffset + z] == 0) zeroCount++;
                                }
                            }

                            // Scoring
                            int score = 0;
                            if (zeroCount >= 20) score += 50; // High Structure
                            else if (zeroCount >= 5) score += 10;
                            
                            if (gold > 0) score += 20;
                            
                            // Penalize "Round Numbers" (e.g. 0x980000 = 9961472)
                            // These are very common in memory (pointers/indices) but extremely rare for real Gold.
                            // Real gold (e.g. 9648386 = 0x933902) is noisy.
                            if ((gold & 0xFFFF) == 0 && gold > 0) 
                            { 
                                score -= 50; 
                            }
                            
                            // Console.WriteLine($"[Candidate] 0x{wramBase.ToString("X")} G:{gold} Score:{score}");
                            
                            candidates.Add(new WramCandidate { Address = wramBase, Gold = gold, Score = score });
                        }
                    }
                }

                long nextAddress = (long)memInfo.BaseAddress + (long)memInfo.RegionSize;
                if (nextAddress >= maxAddress || nextAddress <= (long)currentAddress) break;
                currentAddress = (IntPtr)nextAddress;
            }

            if (candidates.Count > 0)
            {
               // Prioritize Score (Structure), then Gold
               var best = candidates.OrderByDescending(c => c.Score).ThenByDescending(c => c.Gold).First();
               Console.WriteLine($"[Scanner] Selected BEST candidate 0x{best.Address.ToString("X")} (Gold: {best.Gold}, Score: {best.Score})");
               return new List<WramCandidate> { best };
            }

            Console.WriteLine($"[Scanner] Scan Complete. No candidates found.");
            return candidates;
        }

        public static IntPtr? ScanForSpoilerLog(Process process)
        {
            string marker = "ITEM LOCATIONS";
            byte[] signature = System.Text.Encoding.ASCII.GetBytes(marker);
            string mask = new string('x', signature.Length);
            var matches = ScanForSignature(process, signature, mask);
            return matches.Count > 0 ? (IntPtr?)matches[0] : null;
        }

        public static IntPtr? ScanForRom(Process process, IntPtr? wramHint = null)
        {
            var candidates = new List<IntPtr>();

            // Signatures (Standard & Randomized)
            var romSigs = new List<(string, byte[], int)> {
                ("LUFIA",    new byte[]{0x4C,0x55,0x46,0x49,0x41}, 0xFFC0),
                ("L2-R",     new byte[]{0x4C,0x32,0x2D,0x52},      0xFFC0), 
                ("L2-",      new byte[]{0x4C,0x32,0x2D},           0xFFC0), 
                ("ESTPOLIS", new byte[]{0x45,0x53,0x54,0x50,0x4F,0x4C,0x49,0x53}, 0xFFC0),
                ("Lufia II", new byte[]{0x4C,0x75,0x66,0x69,0x61,0x20,0x49,0x49}, 0xFFC0),
                ("Lufia",    new byte[]{0x4C,0x75,0x66,0x69,0x61}, 0xFFC0)
            };

            foreach (var sig in romSigs)
            {
                 string mask = new string('x', sig.Item2.Length);
                 var locs = ScanForSignature(process, sig.Item2, mask, 0); 
                 foreach(var loc in locs)
                 {
                     IntPtr candidate = (IntPtr)((long)loc - sig.Item3);
                     Console.WriteLine($"[Scanner] FOUND ROM Signature '{sig.Item1}' at 0x{loc.ToString("X")} (Base: 0x{candidate.ToString("X")})");
                     candidates.Add(candidate);
                 }
            }

            // Fallback
            if (candidates.Count == 0 && wramHint.HasValue)
            {
                IntPtr fallback = (IntPtr)((long)wramHint.Value + 0x22330);
                byte[] temp = new byte[1];
                if (NativeMethods.ReadProcessMemory(process.Handle, fallback, temp, 1, out _))
                     candidates.Add(fallback);
            }
            
            if (candidates.Count == 0) return null;

            // Sort by WRAM Proximity
            List<IntPtr> sorted = candidates;
            if (wramHint.HasValue)
            {
                 long wramVal = (long)wramHint.Value;
                 sorted = candidates.OrderBy(c => Math.Abs((long)c - wramVal)).Distinct().ToList();
            }

            Console.WriteLine($"[Scanner] Verifying {sorted.Count} ROM Candidates...");
            
            foreach(var cand in sorted)
            {
                // CorrectRomBase will return IntPtr.Zero if verification fails
                IntPtr result = CorrectRomBase(process, cand);
                if (result != IntPtr.Zero) 
                {
                    Console.WriteLine($"[Scanner] Selected Verified ROM: 0x{result.ToString("X")}");
                    return result;
                }
            }

            Console.WriteLine("[Scanner] ALL ROM Candidates failed Sprite Table verification. Using Best Guess.");
            return sorted.FirstOrDefault(); 
        }

        private static IntPtr CorrectRomBase(Process process, IntPtr romBase)
        {
             // Expected Sprite IDs
             var validIds = new HashSet<ushort> { 
                 0x4600, 0x0046,
                 0xA502, 0x02A5,
                 0x4305, 0x0543,
                 0xAF07, 0x07AF,
                 0x580A, 0x0A58,
                 0x0B0D, 0x0D0B,
                 0x880F, 0x0F88,
                 0x0E15, 0x150E 
             };

             // Scan Window: Base + BDCB8 +/- 0x40000 (256KB)
             int range = 0x40000;
             long expectedTable = (long)romBase + 0xBDCB8;
             long startOffset = -range;
             
             IntPtr startAddr = (IntPtr)(expectedTable + startOffset);
             byte[] buffer = new byte[range * 2]; 
             IntPtr read;
             
             // Console.WriteLine($"[Scanner] Probing Sprite Table near 0x{expectedTable.ToString("X")}...");
             
             if (NativeMethods.ReadProcessMemory(process.Handle, startAddr, buffer, buffer.Length, out read))
             {
                 for (int i = 0; i < buffer.Length - 14; i += 2)
                 {
                     ushort val = (ushort)(buffer[i] | (buffer[i + 1] << 8));
                     
                     if (validIds.Contains(val))
                     {
                         // Basic verification: Check if it's not just a random 0x0000 match (Wait, 0xA502 is robust)
                         // User said "Starts with ANY ONE".
                         
                         long foundAddr = (long)startAddr + i;
                         long correctedBase = foundAddr - 0xBDCB8;
                         long diff = correctedBase - (long)romBase;
                         
                         // Console.WriteLine($"[Scanner] Sprite Table matched at 0x{foundAddr.ToString("X")}. Correcting Base by {diff:X}");
                         return (IntPtr)correctedBase;
                     }
                 }
             }
             
             // Console.WriteLine("[Scanner] Sprite Table Scan failed for this candidate.");
             return IntPtr.Zero; // INDICATE FAILURE
        }

        private static bool IsValidRom(Process process, IntPtr romBase)
        {
             try {
                long addrCk = (long)romBase + 0xFFDC;
                byte[] buf = new byte[4];
                IntPtr read;
                if (NativeMethods.ReadProcessMemory(process.Handle, (IntPtr)addrCk, buf, 4, out read))
                {
                    ushort ck = (ushort)(buf[0] | (buf[1] << 8)); 
                    ushort cm = (ushort)(buf[2] | (buf[3] << 8)); 
                    return (ck + cm) == 0xFFFF;
                }
             } catch {}
             return false;
        }

        private static int FindPattern(byte[] buffer, byte[] signature, string mask)
        {
            for (int i = 0; i < buffer.Length - signature.Length; i++)
            {
                bool found = true;
                for (int j = 0; j < signature.Length; j++)
                {
                    if (mask[j] == 'x' && buffer[i + j] != signature[j])
                    {
                        found = false;
                        break;
                    }
                }
                if (found) return i;
            }
            return -1;
        }
    }
}
