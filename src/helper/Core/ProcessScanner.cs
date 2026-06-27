using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;

namespace Lufia2AutoTracker.Helper.Core
{
    public static class ProcessScanner
    {
        // Names are discovery hints only. A process is never accepted until its
        // memory validates as a live Lufia II instance.
        private static readonly string[] EmulatorNames = {
            "snes9x-x64", "snes9x", "bsnes", "retroarch", "mesen-s", "mesen",
            "higan", "ares", "emuhawk"
        };

        public static IReadOnlyList<Process> FindEmulatorProcesses()
        {
            var priority = EmulatorNames
                .Select((name, index) => new { name, index })
                .ToDictionary(x => x.name, x => x.index, StringComparer.OrdinalIgnoreCase);

            var matches = new List<Process>();
            foreach (Process process in Process.GetProcesses())
            {
                bool keep = false;
                try
                {
                    keep = !process.HasExited && priority.ContainsKey(process.ProcessName);
                    if (keep) matches.Add(process);
                }
                catch
                {
                    keep = false;
                }
                finally
                {
                    if (!keep) process.Dispose();
                }
            }

            return matches
                .OrderBy(process => priority[process.ProcessName])
                .ThenBy(process => process.Id)
                .ToList();
        }

        public static Process? FindEmulatorProcess() => FindEmulatorProcesses().FirstOrDefault();

        public static bool IsKnownEmulatorName(string processName) =>
            EmulatorNames.Contains(processName, StringComparer.OrdinalIgnoreCase);
    }
}
