<#
.SYNOPSIS
    Generate a multi-resolution Windows .ico from a PNG (helper for #63).

.DESCRIPTION
    Inno Setup's SetupIconFile and Windows shortcuts want a real .ico holding
    several square sizes. This builds one from the app's icon.png using only
    System.Drawing (shipped with the .NET runtime on Windows) — no ImageMagick.

    The .ico is assembled by hand: an ICONDIR header, one ICONDIRENTRY per size,
    and each frame stored as an embedded PNG (the modern, Vista+ .ico form that
    Inno Setup and Explorer both read).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Source,
    [Parameter(Mandatory)] [string]$Destination,
    [int[]]$Sizes = @(16, 24, 32, 48, 64, 128, 256)
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Drawing

$src = [System.Drawing.Image]::FromFile((Resolve-Path $Source).Path)
try {
    # Render each size to an in-memory PNG.
    $frames = foreach ($size in $Sizes) {
        $bmp = New-Object System.Drawing.Bitmap $size, $size
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.DrawImage($src, 0, 0, $size, $size)
        $g.Dispose()
        $ms = New-Object System.IO.MemoryStream
        $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        $bmp.Dispose()
        [pscustomobject]@{ Size = $size; Bytes = $ms.ToArray() }
    }

    # Resolve $Destination against the current directory. [Path]::Combine (unlike
    # Join-Path) returns it unchanged when it is already absolute — which it is when
    # build_installer.ps1 passes a full path — and joins it to the cwd when relative.
    $destPath = [System.IO.Path]::Combine((Get-Location).Path, $Destination)
    $out = [System.IO.File]::Open($destPath, "Create")
    try {
        $w = New-Object System.IO.BinaryWriter $out
        # ICONDIR: reserved(0), type(1 = icon), image count.
        $w.Write([uint16]0); $w.Write([uint16]1); $w.Write([uint16]$frames.Count)
        # Image data starts after the directory (6-byte header + 16 bytes/entry).
        $offset = 6 + 16 * $frames.Count
        foreach ($f in $frames) {
            $dim = if ($f.Size -ge 256) { 0 } else { $f.Size }  # 0 means 256 in .ico
            $w.Write([byte]$dim)        # width
            $w.Write([byte]$dim)        # height
            $w.Write([byte]0)           # palette count
            $w.Write([byte]0)           # reserved
            $w.Write([uint16]1)         # color planes
            $w.Write([uint16]32)        # bits per pixel
            $w.Write([uint32]$f.Bytes.Length)
            $w.Write([uint32]$offset)
            $offset += $f.Bytes.Length
        }
        foreach ($f in $frames) { $w.Write($f.Bytes) }
        $w.Flush()
    } finally {
        $out.Dispose()
    }
    Write-Host ">> Wrote $Destination ($($frames.Count) sizes)"
} finally {
    $src.Dispose()
}
