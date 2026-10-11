$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pidFile = Join-Path $root 'runtime\remote-tunnel.pid'
if (Test-Path -LiteralPath $pidFile) {
    $tunnelPid = [int](Get-Content -LiteralPath $pidFile)
    $process = Get-Process -Id $tunnelPid -ErrorAction SilentlyContinue
    if ($process -and $process.Path -like '*cloudflared.exe') { Stop-Process -Id $tunnelPid -Force }
    Remove-Item -LiteralPath $pidFile
}
$apiPidFile = Join-Path $root 'runtime\remote-api.pid'
if (Test-Path -LiteralPath $apiPidFile) {
    $apiPid = [int](Get-Content -LiteralPath $apiPidFile)
    $process = Get-Process -Id $apiPid -ErrorAction SilentlyContinue
    if ($process -and $process.Path -like '*python.exe') { Stop-Process -Id $apiPid -Force }
    Remove-Item -LiteralPath $apiPidFile
}
Write-Output 'Túnel remoto encerrado.'
