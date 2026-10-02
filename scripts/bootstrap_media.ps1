# Portable build linked by https://ffmpeg.org/download.html; not an FFmpeg.org binary.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $projectRoot 'storage/tools'
$version = '9.0.2'
$archiveName = "ffmpeg-$version-essentials_build.zip"
$url = "https://www.gyan.dev/ffmpeg/builds/packages/$archiveName"
$expectedHash = '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba'
New-Item -ItemType Directory -Force -Path $toolsRoot | Out-Null
$archive = Join-Path $toolsRoot $archiveName
if (-not (Test-Path -LiteralPath $archive)) {
    $partial = "$archive.partial"
    & curl.exe --fail --location --retry 2 --max-time 300 --output $partial $url
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg download failed; rerun to retry.' }
    $actual = (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expectedHash) { throw "Archive checksum mismatch: $actual" }
    Move-Item -LiteralPath $partial -Destination $archive
}
$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expectedHash) { throw "Existing archive checksum mismatch: $actual" }
$distribution = Join-Path $toolsRoot "ffmpeg-$version-essentials_build"
$expanded = $false
if (-not (Test-Path -LiteralPath $distribution)) {
    Expand-Archive -LiteralPath $archive -DestinationPath $toolsRoot
    $expanded = $true
}
$ffmpeg = Join-Path $distribution 'bin/ffmpeg.exe'
$ffprobe = Join-Path $distribution 'bin/ffprobe.exe'
if (-not (Test-Path -LiteralPath $ffmpeg) -or -not (Test-Path -LiteralPath $ffprobe)) { throw 'Incomplete portable distribution; preserve and inspect storage/tools.' }
$manifestPath = Join-Path $toolsRoot 'ffmpeg-manifest.json'
if (-not $expanded) {
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Existing distribution has no provenance manifest; preserve and inspect it before execution.' }
    $previous = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($previous.archive_sha256 -ne $expectedHash -or $previous.ffmpeg_sha256 -ne (Get-FileHash $ffmpeg).Hash -or $previous.ffprobe_sha256 -ne (Get-FileHash $ffprobe).Hash) { throw 'Existing distribution differs from recorded hashes; preserving files for inspection.' }
}
$manifest = @{source_page='https://ffmpeg.org/download.html'; provider='https://www.gyan.dev/ffmpeg/builds/'; archive_url=$url; archive_sha256=$actual; version=$version; observed_at_utc=[DateTime]::UtcNow.ToString('o'); ffmpeg_sha256=(Get-FileHash $ffmpeg).Hash; ffprobe_sha256=(Get-FileHash $ffprobe).Hash}
$manifest | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath $manifestPath
& $ffmpeg -version | Select-Object -First 1
& $ffprobe -version | Select-Object -First 1
Write-Output 'Portable tools ready. No global install or PATH changes.'
