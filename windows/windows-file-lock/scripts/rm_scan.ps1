param(
    [string]$Target,
    [string]$Parent,
    [string]$NameFilter
)
# Finds processes holding open DATA FILES under a target directory via the Restart Manager API
# (same mechanism Windows installers use). Limitation: it cannot see directory-handle-only or
# CWD-based locks -- an empty result does NOT mean nothing locks the folder.
# Usage (either form):
#   -Target 'E:\some\dir'                       # direct path, may garble if it contains Chinese via argv
#   -Parent 'E:\some' -NameFilter 'harness'     # discover child dir by ASCII substring (Chinese-path safe)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$sig = @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class RestMgr {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct RM_UNIQUE_PROCESS {
        public int dwProcessId;
        public System.Runtime.InteropServices.ComTypes.FILETIME ProcessStartTime;
    }

    const int CCH_RM_MAX_APP_NAME = 255;
    const int CCH_RM_MAX_SVC_NAME = 63;
    const int ERROR_MORE_DATA = 234;

    public enum RM_APP_TYPE { RmUnknownApp = 0, RmMainWindow = 1, RmOtherWindow = 2, RmService = 3, RmExplorer = 4, RmConsole = 5, RmCritical = 1000 }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct RM_PROCESS_INFO {
        public RM_UNIQUE_PROCESS Process;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = CCH_RM_MAX_APP_NAME + 1)]
        public string strAppName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = CCH_RM_MAX_SVC_NAME + 1)]
        public string strServiceShortName;
        public RM_APP_TYPE ApplicationType;
        public uint AppStatus;
        public uint TSSessionId;
        [MarshalAs(UnmanagedType.Bool)]
        public bool bRestartable;
    }

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    public static extern int RmRegisterResources(uint pSessionHandle, uint nFiles, string[] rgsFilenames,
        uint nApplications, [In] RM_UNIQUE_PROCESS[] rgApplications, uint nServices, string[] rgsServiceNames);

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    public static extern int RmStartSession(out uint pSessionHandle, int dwSessionFlags, string strSessionKey);

    [DllImport("rstrtmgr.dll")]
    public static extern int RmEndSession(uint pSessionHandle);

    [DllImport("rstrtmgr.dll")]
    public static extern int RmGetList(uint dwSessionHandle, out uint pnProcInfoNeeded, ref uint pnProcInfo,
        [In, Out] RM_PROCESS_INFO[] rgAffectedApps, ref uint lpdwRebootReasons);

    public static List<string> FindLockers(string[] paths) {
        var result = new List<string>();
        uint handle;
        string key = Guid.NewGuid().ToString();
        int res = RmStartSession(out handle, 0, key);
        if (res != 0) throw new Exception("RmStartSession failed: " + res);
        try {
            res = RmRegisterResources(handle, (uint)paths.Length, paths, 0, null, 0, null);
            if (res != 0) throw new Exception("RmRegisterResources failed: " + res);
            uint needed = 0, count = 10, reasons = 0;
            var info = new RM_PROCESS_INFO[count];
            res = RmGetList(handle, out needed, ref count, info, ref reasons);
            if (res == ERROR_MORE_DATA) {
                count = needed;
                info = new RM_PROCESS_INFO[count];
                res = RmGetList(handle, out needed, ref count, info, ref reasons);
            }
            if (res != 0) throw new Exception("RmGetList failed: " + res);
            for (int i = 0; i < count; i++) {
                result.Add(info[i].Process.dwProcessId + "\t" + info[i].strAppName + "\t" + info[i].ApplicationType);
            }
        } finally { RmEndSession(handle); }
        return result;
    }
}
'@
Add-Type -TypeDefinition $sig

if (-not $Target -and $Parent -and $NameFilter) {
    $found = Get-ChildItem -LiteralPath $Parent -Directory | Where-Object { $_.Name -like ($NameFilter + '*') } | Select-Object -First 1
    if (-not $found) { Write-Output 'target folder not found by filter'; exit 1 }
    $Target = $found.FullName
}
if (-not ($Target -and (Test-Path -LiteralPath $Target))) { Write-Output 'usage: -Target <dir>  or  -Parent <dir> -NameFilter <ascii-prefix>'; exit 1 }
Write-Output ("target: " + $Target)

$files = @()
$files += Get-ChildItem -LiteralPath $Target -File -Force -ErrorAction SilentlyContinue | Select-Object -First 30
foreach ($sub in (Get-ChildItem -LiteralPath $Target -Directory -Force -ErrorAction SilentlyContinue | Select-Object -First 12)) {
    $files += Get-ChildItem -LiteralPath $sub.FullName -File -Recurse -Force -ErrorAction SilentlyContinue | Select-Object -First 20
}
$paths = @($files | ForEach-Object { $_.FullName } | Select-Object -Unique)
Write-Output ("scanning " + $paths.Count + " sample files with Restart Manager...")

try { $lockers = [RestMgr]::FindLockers($paths) }
catch { Write-Output ("ERROR: " + $_.Exception.Message); exit 1 }

if ($lockers.Count -eq 0) {
    Write-Output '(no file-level locks found in sampled files; directory/CWD locks are invisible to this method)'
} else {
    Write-Output '=== locking processes ==='
    foreach ($l in $lockers) {
        $parts = $l -split "`t"
        try { $procName = (Get-Process -Id ([int]$parts[0]) -ErrorAction Stop).Name } catch { $procName = '?' }
        Write-Output ("PID=" + $parts[0] + "  App=" + $parts[1] + "  Type=" + $parts[2] + "  Process=" + $procName)
    }
}
