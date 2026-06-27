# Logging and diagnostics

Starting with v1.4.9, logs are stored outside the installation and PyInstaller extraction directories:

```text
%LOCALAPPDATA%\Lufia2AutoTracker\logs\tracker.log
%LOCALAPPDATA%\Lufia2AutoTracker\logs\error.log
```

Use **Help > Open Log Folder** to open this directory.

- `tracker.log` records session, UI, synchronization, helper, discovery, and recovery events at information level and above.
- `error.log` records errors and critical failures with tracebacks where available.
- Both logs rotate at 5 MiB. Three tracker backups and five error backups are retained.
- Helper messages identify the operation, canonical field or section, WRAM/ROM address, process/profile, native error code, and failure reason when available.

Each startup records the tracker version, packaged/source mode, Python version, and Windows version. Logs do not contain ROM data or process-memory dumps.

For emulator-attachment reports, reproduce the problem once and provide both current log files together with the emulator name and version.
