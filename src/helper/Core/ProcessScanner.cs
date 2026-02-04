using System;
using System.Diagnostics;
using System.Linq;

namespace Lufia2AutoTracker.Helper.Core
{
    public class ProcessScanner
    {
        private static readonly string[] EmulatorNames = {
            "snes9x", "snes9x-x64", "retroarch", "mesen-s", "bsnes", "higan"
        };

        public static Process? FindEmulatorProcess()
        {
            var processes = Process.GetProcesses();
            foreach (var name in EmulatorNames)
            {
                var process = processes.FirstOrDefault(p => p.ProcessName.Equals(name, StringComparison.OrdinalIgnoreCase));
                if (process != null && !process.HasExited)
                {
                    return process;
                }
            }
            return null;
        }
    }
}
