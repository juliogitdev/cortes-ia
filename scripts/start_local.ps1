param([ValidateSet('cpu','cuda')][string]$Device, [string]$Model)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install the local environment first. See docs/INSTALL.md.' }
$localSettings = Join-Path $projectRoot 'runtime/local-settings.json'
$configured = $null
if (Test-Path -LiteralPath $localSettings) {
    $configured = Get-Content -Raw -Encoding UTF8 -LiteralPath $localSettings | ConvertFrom-Json
}
if (-not $PSBoundParameters.ContainsKey('Device')) {
    $Device = 'cpu'
    if ($configured -and $configured.device -in @('cpu','cuda')) { $Device = $configured.device }
}
if (-not $PSBoundParameters.ContainsKey('Model')) {
    $Model = 'models/whisper-tiny'
    if ($configured -and $configured.model) { $Model = [string]$configured.model }
}
$workerPython = $pythonPath
if ($Device -eq 'cuda') {
    $workerPython = Join-Path $projectRoot '.venv-gpu/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $workerPython)) { throw 'GPU environment missing. See docs/INSTALL.md.' }
}
$modelPath = if ([IO.Path]::IsPathRooted($Model)) { [IO.Path]::GetFullPath($Model) } else { [IO.Path]::GetFullPath((Join-Path $projectRoot $Model)) }
if (-not (Test-Path -LiteralPath (Join-Path $modelPath 'model.bin'))) { throw 'Prepare a local speech model first. See docs/INSTALL.md.' }
$nodePath = (Get-Command node -ErrorAction SilentlyContinue).Source
$frontendPath = Join-Path $projectRoot 'frontend'
if (-not $nodePath -or -not (Test-Path -LiteralPath (Join-Path $frontendPath 'node_modules/vite/bin/vite.js'))) {
    throw 'Frontend dependencies missing. Run npm ci in frontend.'
}
foreach ($port in @(8000,8501)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port already in use; preserve existing processes." }
}
$runtimePath = Join-Path $projectRoot 'runtime'
New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null
$manifestPath = Join-Path $runtimePath 'local-processes.json'
if (Test-Path -LiteralPath $manifestPath) { throw 'Existing process manifest; run stop_local.ps1 first.' }
$processes = @()
$env:CLIP_STORAGE = Join-Path $projectRoot 'storage'
$definitions = @(
    @{name='api'; args=@('-m','uvicorn','clip_platform.api.app:create_app','--factory','--host','127.0.0.1','--port','8000','--no-access-log'); workdir=$projectRoot},
    @{name='scheduler'; args=@('-m','clip_platform.learning.tiktok_scheduler','--storage',('"'+$env:CLIP_STORAGE+'"')); workdir=$projectRoot},
    @{name='worker'; args=@('-m','clip_platform.worker.runner','--model',('"'+$modelPath+'"'),'--device',$Device); workdir=$projectRoot},
    @{name='panel'; args=@('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','8501','--strictPort'); workdir=$frontendPath}
)
try {
    foreach ($definition in $definitions) {
        $executable = if ($definition.name -eq 'worker') { $workerPython } elseif ($definition.name -eq 'panel') { $nodePath } else { $pythonPath }
        $process = Start-Process -FilePath $executable -ArgumentList $definition.args -WorkingDirectory $definition.workdir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath ($definition.name+'.log')) -RedirectStandardError (Join-Path $runtimePath ($definition.name+'.err.log'))
        $processes += @{name=$definition.name; pid=$process.Id; executable=$executable}
    }
    @{root=$projectRoot; processes=$processes} | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -LiteralPath $manifestPath
    Write-Output 'Panel: http://127.0.0.1:8501 | API: http://127.0.0.1:8000/docs'
    Write-Output "Logs in runtime. Stop with scripts/stop_local.ps1. Worker device: $Device; visual CUDA benchmark remains pending."
} catch {
    foreach ($process in $processes) { Stop-Process -Id $process.pid -ErrorAction SilentlyContinue }
    throw
}
