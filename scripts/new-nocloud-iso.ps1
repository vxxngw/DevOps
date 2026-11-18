<# Build a NoCloud ISO with Windows IMAPI2; no additional package is required. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourceDirectory,
    [Parameter(Mandatory)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
foreach ($name in @('user-data', 'meta-data')) {
    if (-not (Test-Path -LiteralPath (Join-Path $SourceDirectory $name) -PathType Leaf)) {
        throw "Missing NoCloud file: $name"
    }
}
if (Test-Path -LiteralPath $OutputPath) { throw "Refusing to overwrite ISO: $OutputPath" }
if (-not ('ClinicIsoWriter' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class ClinicIsoWriter {
    public static void Write(object imageStream, string path) {
        IStream stream = (IStream)imageStream;
        byte[] buffer = new byte[1024 * 1024];
        IntPtr count = Marshal.AllocHGlobal(4);
        try {
            using (FileStream output = new FileStream(path, FileMode.CreateNew, FileAccess.Write)) {
                while (true) {
                    Marshal.WriteInt32(count, 0);
                    stream.Read(buffer, buffer.Length, count);
                    int read = Marshal.ReadInt32(count);
                    if (read == 0) break;
                    output.Write(buffer, 0, read);
                }
            }
        } finally { Marshal.FreeHGlobal(count); }
    }
}
'@
}
$image = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
$image.FileSystemsToCreate = 3 # ISO9660 + Joliet (preserves user-data/meta-data names)
$image.VolumeName = 'cidata'
$image.Root.AddTree([IO.Path]::GetFullPath($SourceDirectory), $false)
$result = $image.CreateResultImage()
[ClinicIsoWriter]::Write($result.ImageStream, [IO.Path]::GetFullPath($OutputPath))
Get-Item -LiteralPath $OutputPath | Select-Object FullName, Length