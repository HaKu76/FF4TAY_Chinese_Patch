param(
    [switch]$UpdateInstalledGame,
    [switch]$SkipZip
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path $PSScriptRoot -Parent
$resourceDir = Join-Path $projectRoot 'Resources\en.lproj'
$menuPath = Join-Path $resourceDir 'menu.msd'
$scenarioPath = Join-Path $resourceDir 'scenario.msd'
$zipPath = Join-Path $projectRoot 'src\patch_data.zip'

function Read-Msd([string]$Path) {
    [byte[]]$data = [IO.File]::ReadAllBytes($Path)
    if ($data.Length -lt 16 -or [Text.Encoding]::ASCII.GetString($data, 0, 4) -ne 'MSDA') {
        throw "Invalid MSDA file: $Path"
    }

    $count = [BitConverter]::ToUInt32($data, 8)
    if (16 + $count * 12 -gt $data.Length) {
        throw "Invalid MSDA index: $Path"
    }

    $entries = @()
    for ($i = 0; $i -lt $count; $i++) {
        $entryOffset = 16 + $i * 12
        $dataOffset = [BitConverter]::ToUInt32($data, $entryOffset + 8)
        $nextOffset = if ($i + 1 -lt $count) {
            [BitConverter]::ToUInt32($data, $entryOffset + 20)
        } else {
            $data.Length
        }

        if ($dataOffset -gt $nextOffset -or $nextOffset -gt $data.Length) {
            throw "Invalid MSDA data offset at entry $i in $Path"
        }

        [byte[]]$raw = New-Object byte[] ($nextOffset - $dataOffset)
        [Array]::Copy($data, $dataOffset, $raw, 0, $raw.Length)
        $entries += [pscustomobject]@{
            Id = [BitConverter]::ToUInt32($data, $entryOffset)
            VariantCount = [BitConverter]::ToUInt16($data, $entryOffset + 4)
            Reserved = [BitConverter]::ToUInt16($data, $entryOffset + 6)
            Raw = $raw
        }
    }

    [byte[]]$header = New-Object byte[] 16
    [Array]::Copy($data, 0, $header, 0, 16)
    return [pscustomobject]@{ Header = $header; Entries = $entries }
}

function New-MsdTextData([string[]]$Texts) {
    $stream = New-Object IO.MemoryStream
    try {
        foreach ($text in $Texts) {
            [byte[]]$bytes = [Text.Encoding]::Unicode.GetBytes($text)
            $stream.Write($bytes, 0, $bytes.Length)
            $stream.WriteByte(0)
            $stream.WriteByte(0)
            $stream.WriteByte(0)
            $stream.WriteByte(0)
        }

        return $stream.ToArray()
    } finally {
        $stream.Dispose()
    }
}

function Set-MsdText($Document, [uint32]$Id, [string]$Text) {
    $entry = $Document.Entries | Where-Object { $_.Id -eq $Id } | Select-Object -First 1
    [byte[]]$raw = New-MsdTextData @($Text)

    if ($null -eq $entry) {
        $Document.Entries = @($Document.Entries) + [pscustomobject]@{
            Id = $Id
            VariantCount = [uint16]1
            Reserved = [uint16]0xCCCC
            Raw = $raw
        }
    } else {
        $entry.VariantCount = [uint16]1
        $entry.Raw = $raw
    }
}

function Write-Msd($Document, [string]$Path) {
    $entries = @($Document.Entries | Sort-Object { [uint64]$_.Id })
    $ids = [Collections.Generic.HashSet[uint32]]::new()
    foreach ($entry in $entries) {
        if (-not $ids.Add([uint32]$entry.Id)) {
            throw "Duplicate MSDA message ID: $($entry.Id)"
        }
    }

    $dataStart = 16 + $entries.Count * 12
    $totalLength = $dataStart
    foreach ($entry in $entries) {
        $totalLength += $entry.Raw.Length
    }

    [byte[]]$output = New-Object byte[] $totalLength
    [Array]::Copy($Document.Header, 0, $output, 0, 16)
    [Array]::Copy([BitConverter]::GetBytes([uint32]$entries.Count), 0, $output, 8, 4)

    $cursor = $dataStart
    for ($i = 0; $i -lt $entries.Count; $i++) {
        $indexOffset = 16 + $i * 12
        $entry = $entries[$i]
        [Array]::Copy([BitConverter]::GetBytes([uint32]$entry.Id), 0, $output, $indexOffset, 4)
        [Array]::Copy([BitConverter]::GetBytes([uint16]$entry.VariantCount), 0, $output, $indexOffset + 4, 2)
        [Array]::Copy([BitConverter]::GetBytes([uint16]$entry.Reserved), 0, $output, $indexOffset + 6, 2)
        [Array]::Copy([BitConverter]::GetBytes([uint32]$cursor), 0, $output, $indexOffset + 8, 4)
        [Array]::Copy($entry.Raw, 0, $output, $cursor, $entry.Raw.Length)
        $cursor += $entry.Raw.Length
    }

    [IO.File]::WriteAllBytes($Path, $output)
}

function Repair-ScenarioPointers([string]$Path) {
    [byte[]]$data = [IO.File]::ReadAllBytes($Path)
    foreach ($offset in @(0xA7D0, 0x187EC)) {
        if ($data[$offset + 1] -ne 0x21) {
            throw ('Unexpected scenario pointer bytes at 0x{0:X}' -f $offset)
        }

        if ($data[$offset] -eq 0x92) {
            $data[$offset] = 0xD2
        } elseif ($data[$offset] -ne 0xD2) {
            throw ('Unexpected scenario pointer bytes at 0x{0:X}' -f $offset)
        }
    }

    [IO.File]::WriteAllBytes($Path, $data)
}

function Add-FileToZip($Archive, [string]$SourcePath, [string]$EntryName) {
    $entry = $Archive.CreateEntry($EntryName, [IO.Compression.CompressionLevel]::Optimal)
    $entry.LastWriteTime = (Get-Item -LiteralPath $SourcePath).LastWriteTime
    $input = [IO.File]::OpenRead($SourcePath)
    $output = $entry.Open()
    try {
        $input.CopyTo($output)
    } finally {
        $output.Dispose()
        $input.Dispose()
    }
}

function Build-PatchDataZip([string]$Destination) {
    Add-Type -AssemblyName System.IO.Compression
    $tempPath = "$Destination.tmp"
    if (Test-Path -LiteralPath $tempPath) {
        Remove-Item -LiteralPath $tempPath -Force
    }

    $fileStream = [IO.File]::Open($tempPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $archive = New-Object IO.Compression.ZipArchive($fileStream, [IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        $resourceFiles = @(Get-ChildItem -LiteralPath $resourceDir -File | Sort-Object Name)
        if ($resourceFiles.Count -ne 121) {
            throw "Expected 121 localized resource files, found $($resourceFiles.Count)."
        }

        foreach ($file in $resourceFiles) {
            Add-FileToZip $archive $file.FullName $file.Name
        }
        Add-FileToZip $archive (Join-Path $projectRoot 'menu.txt') 'menu.txt'
    } finally {
        $archive.Dispose()
        $fileStream.Dispose()
    }

    [IO.File]::Copy($tempPath, $Destination, $true)
    Remove-Item -LiteralPath $tempPath -Force
}

$menu = Read-Msd $menuPath
$keyboardLabels = @(
    'Esc', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '退格', 'Tab',
    'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '回车', 'Ctrl',
    'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'", '`', 'Shift', '\',
    'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', '右 Shift', '小键盘 *', 'Alt',
    '空格', '大写锁定', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10',
    '数字锁定', 'Scroll Lock', '小键盘 7', '小键盘 8', '小键盘 9', '小键盘 -',
    '小键盘 4', '小键盘 5', '小键盘 6', '小键盘 +', '小键盘 1', '小键盘 2',
    '小键盘 3', '小键盘 0', '小键盘 .', '<', 'F11', 'F12', 'F13', 'F14', 'F15',
    'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU',
    '小键盘回车', '右 Ctrl',
    'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU',
    '小键盘 /', 'Print Screen', '右 Alt', 'Pause', 'Home', '上', 'Page Up', '左', '右',
    'End', '下', 'Page Down', 'Insert', 'Delete', '左 Windows', '右 Windows', '菜单键',
    'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU', 'DOTEMU'
)

if ($keyboardLabels.Count -ne 128) {
    throw "Expected 128 keyboard labels, found $($keyboardLabels.Count)."
}

Set-MsdText $menu 50101 '使用'
Set-MsdText $menu 50201 '装备'
Set-MsdText $menu 50505 '队伍编成'
for ($i = 0; $i -lt $keyboardLabels.Count; $i++) {
    Set-MsdText $menu ([uint32](60000 + $i)) $keyboardLabels[$i]
}
Set-MsdText $menu 61000 '十字键'
Set-MsdText $menu 61001 '方向键'
Write-Msd $menu $menuPath

Repair-ScenarioPointers $scenarioPath

if (-not $SkipZip) {
    Build-PatchDataZip $zipPath
}

if ($UpdateInstalledGame) {
    $gameRoot = Split-Path $projectRoot -Parent
    $gameResourceDir = Join-Path $gameRoot 'Resources\en.lproj'
    if (-not (Test-Path -LiteralPath (Join-Path $gameRoot 'FF4A.exe'))) {
        throw "FF4A.exe was not found in $gameRoot"
    }

    Copy-Item -LiteralPath $menuPath -Destination (Join-Path $gameResourceDir 'menu.msd') -Force
    Copy-Item -LiteralPath $scenarioPath -Destination (Join-Path $gameResourceDir 'scenario.msd') -Force
}

Write-Host "Updated menu.msd ($($menu.Entries.Count) entries)."
Write-Host 'Repaired scenario IDs 450508 and 680362.'
if (-not $SkipZip) {
    Write-Host 'Rebuilt src/patch_data.zip.'
}
if ($UpdateInstalledGame) {
    Write-Host 'Updated the installed game resources.'
}

