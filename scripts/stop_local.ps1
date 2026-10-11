$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$manifestPath = Join-Path $projectRoot 'runtime/local-processes.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { Write-Output 'No local process manifest.'; exit 0 }
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
if ($manifest.root -ne $projectRoot) { throw 'Manifest belongs to another workspace; preserving it.' }
foreach ($process in $manifest.processes) {
    $current = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.pid)" -ErrorAction SilentlyContinue
    if ($current -and $current.ExecutablePath -eq $process.executable -and $current.CommandLine -match 'clip_platform|vite') {
        & taskkill /PID $process.pid /T /F 2>&1 | Out-Null
    } elseif ($current) { throw 'PID reused by another process; preserving it.' }
}
Remove-Item -LiteralPath $manifestPath
Write-Output 'Local processes stopped. Media and database preserved.'
