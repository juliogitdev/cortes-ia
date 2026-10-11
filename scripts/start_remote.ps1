$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$binary = Join-Path $env:LOCALAPPDATA 'CortesIA\tools\cloudflared.exe'
$runtime = Join-Path $root 'runtime'
$pidFile = Join-Path $runtime 'remote-tunnel.pid'
$apiPidFile = Join-Path $runtime 'remote-api.pid'
$authFile = Join-Path $runtime 'remote-auth.json'
$logFile = Join-Path $runtime 'remote-tunnel.log'
if (-not (Test-Path -LiteralPath $binary)) { throw 'cloudflared não está instalado neste PC.' }
if ((Test-Path -LiteralPath $pidFile) -and (Get-Process -Id ([int](Get-Content -LiteralPath $pidFile)) -ErrorAction SilentlyContinue)) {
    throw 'Já existe um túnel ativo. Encerre-o antes de criar outro.'
}
if ((Test-Path -LiteralPath $apiPidFile) -and (Get-Process -Id ([int](Get-Content -LiteralPath $apiPidFile)) -ErrorAction SilentlyContinue)) {
    throw 'Já existe uma API remota ativa. Encerre-a antes de criar outra.'
}
if (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Porta remota 8001 já está em uso.'
}
try {
    $response = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/' -TimeoutSec 5
    if ($response.StatusCode -ne 200) { throw 'Painel indisponível.' }
} catch { throw 'Inicie a aplicação local antes do túnel: scripts/start_local.ps1' }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
if (-not (Test-Path -LiteralPath $authFile)) {
    $bytes = New-Object byte[] 24
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    $password = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
    @{username='admin'; password=$password} | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath $authFile
}
$credentials = Get-Content -Raw -Encoding UTF8 -LiteralPath $authFile | ConvertFrom-Json
$python = Join-Path $root '.venv\Scripts\python.exe'
$env:CLIP_STORAGE = Join-Path $root 'storage'
$env:CLIP_REMOTE_AUTH_FILE = $authFile
$remoteApi = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','clip_platform.api.remote:create_remote_app','--factory','--host','127.0.0.1','--port','8001','--no-access-log') -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime 'remote-api.log') -RedirectStandardError (Join-Path $runtime 'remote-api.err.log')
Set-Content -LiteralPath $apiPidFile -Value $remoteApi.Id
$ready = $false
for ($attempt = 0; $attempt -lt 15; $attempt++) {
    Start-Sleep -Seconds 1
    if ($remoteApi.HasExited) { throw 'API remota não iniciou. Consulte runtime/remote-api.err.log.' }
    $status = & curl.exe -sS -o NUL -w '%{http_code}' --max-time 2 -u "admin:$($credentials.password)" 'http://127.0.0.1:8001/health' 2>$null
    if ($status -eq '200') { $ready = $true; break }
}
if (-not $ready) { throw 'API remota não respondeu em 15 segundos.' }
if (Test-Path -LiteralPath $logFile) { Remove-Item -LiteralPath $logFile }
$args = @('tunnel', '--protocol', 'http2', '--url', 'http://127.0.0.1:8001',
          '--loglevel', 'info', '--logfile', $logFile)
$process = Start-Process -FilePath $binary -ArgumentList $args -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $pidFile -Value $process.Id
$url = $null
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Seconds 1
    if ($process.HasExited) { throw 'O túnel encerrou antes de obter um endereço. Consulte runtime/remote-tunnel.log.' }
    if (Test-Path -LiteralPath $logFile) {
        $match = [regex]::Match((Get-Content -LiteralPath $logFile -Raw), 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($match.Success) { $url = $match.Value; break }
    }
}
if (-not $url) { throw 'Túnel iniciado, mas o endereço não apareceu no log em 30 segundos.' }
Write-Output "Acesso remoto: $url"
Write-Output "Usuário: $($credentials.username)"
Write-Output "Senha: $($credentials.password)"
Write-Output "Para encerrar: scripts/stop_remote.ps1"
