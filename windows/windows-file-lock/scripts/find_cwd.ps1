param([string]$PathPrefix = '')
# Lists every accessible process whose current working directory starts with PathPrefix.
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File find_cwd.ps1 -PathPrefix 'E:\work\tree'
#   powershell -NoProfile -ExecutionPolicy Bypass -File find_cwd.ps1   # dump all readable CWDs
# Keep this file pure ASCII: Windows PowerShell 5.1 parses non-BOM UTF-8 as GBK.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$sig = @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public class ProcCwd {
    [DllImport("ntdll.dll")]
    public static extern int NtQueryInformationProcess(IntPtr hProcess, int pic, ref PROCESS_BASIC_INFORMATION pbi, int cb, out int pSize);

    [DllImport("kernel32.dll")]
    public static extern IntPtr OpenProcess(int access, bool inherit, int pid);

    [DllImport("kernel32.dll")]
    public static extern bool ReadProcessMemory(IntPtr hProcess, IntPtr addr, byte[] buffer, int size, out IntPtr read);

    [DllImport("kernel32.dll")]
    public static extern bool CloseHandle(IntPtr h);

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_BASIC_INFORMATION {
        public IntPtr Reserved1;
        public IntPtr PebBaseAddress;
        public IntPtr Reserved2_0;
        public IntPtr Reserved2_1;
        public IntPtr UniqueProcessId;
        public IntPtr InheritedFromUniqueProcessId;
    }

    // x64 only. RTL_USER_PROCESS_PARAMETERS.CurrentDirectory.DosPath:
    //   UNICODE_STRING Length  @ pp+0x38, Buffer pointer @ pp+0x40
    public static string GetCwd(int pid) {
        IntPtr h = OpenProcess(0x0410, false, pid); // QUERY_INFORMATION | VM_READ
        if (h == IntPtr.Zero) return null;
        try {
            PROCESS_BASIC_INFORMATION pbi = new PROCESS_BASIC_INFORMATION();
            int sz;
            int st = NtQueryInformationProcess(h, 0, ref pbi, Marshal.SizeOf(pbi), out sz);
            if (st != 0) return null;

            byte[] buf = new byte[8];
            IntPtr read;
            if (!ReadProcessMemory(h, (IntPtr)((long)pbi.PebBaseAddress + 0x20), buf, 8, out read)) return null; // PEB->ProcessParameters
            long ppAddr = BitConverter.ToInt64(buf, 0);
            if (ppAddr == 0) return null;

            byte[] us = new byte[16];
            if (!ReadProcessMemory(h, (IntPtr)(ppAddr + 0x38), us, 16, out read)) return null;
            ushort len = BitConverter.ToUInt16(us, 0);
            long strPtr = BitConverter.ToInt64(us, 8);
            if (len == 0 || strPtr == 0 || len > 1024) return null;

            byte[] strBuf = new byte[len];
            if (!ReadProcessMemory(h, (IntPtr)strPtr, strBuf, len, out read)) return null;
            return Encoding.Unicode.GetString(strBuf);
        } catch { return null; }
        finally { CloseHandle(h); }
    }
}
'@
Add-Type -TypeDefinition $sig

$results = foreach ($p in (Get-Process)) {
    $cwd = [ProcCwd]::GetCwd($p.Id)
    if ($cwd) {
        [PSCustomObject]@{ PID = $p.Id; Name = $p.Name; StartTime = $(try { $p.StartTime } catch { $null }); CWD = $cwd }
    }
}

if ($PathPrefix) {
    Write-Output ("=== CWD under '" + $PathPrefix + "' ===")
    $hits = $results | Where-Object { $_.CWD -like ($PathPrefix + '*') }
} else {
    Write-Output '=== all readable CWDs ==='
    $hits = $results
}
if ($hits) { $hits | Format-Table -AutoSize -Wrap } else { Write-Output '(none)' }
