param([ValidateSet('cpu','cuda')][string]$Device = 'cpu', [string]$Model = 'models/whisper-tiny')
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install the local environment first. See docs/INSTALL.md.' }
$modelPath = if ([IO.Path]::IsPathRooted($Model)) { [IO.Path]::GetFullPath($Model) } else { [IO.Path]::GetFullPath((Join-Path $projectRoot $Model)) }
if (-not (Test-Path -LiteralPath (Join-Path $modelPath 'model.bin'))) { throw 'Prepare a local speech model first. See docs/INSTALL.md.' }
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
    @{name='api'; args=@('-m','uvicorn','clip_platform.api.app:create_app','--factory','--host','127.0.0.1','--port','8000')},
    @{name='worker'; args=@('-m','clip_platform.worker.runner','--model',('"'+$modelPath+'"'),'--device',$Device)},
    @{name='panel'; args=@('-m','streamlit','run',('"'+(Join-Path $projectRoot 'src/clip_platform/ui/app.py')+'"'),'--server.address','127.0.0.1','--server.port','8501','--server.headless','true','--browser.gatherUsageStats','false')}
)
try {
    foreach ($definition in $definitions) {
        $process = Start-Process -FilePath $pythonPath -ArgumentList $definition.args -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath ($definition.name+'.log')) -RedirectStandardError (Join-Path $runtimePath ($definition.name+'.err.log'))
        $processes += @{name=$definition.name; pid=$process.Id; executable=$pythonPath}
    }
    @{root=$projectRoot; processes=$processes} | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -LiteralPath $manifestPath
    Write-Output 'Panel: http://127.0.0.1:8501 | API: http://127.0.0.1:8000/docs'
    Write-Output 'Logs in runtime. Stop with scripts/stop_local.ps1. GPU mode still requires the PC benchmark.'
} catch {
    foreach ($process in $processes) { Stop-Process -Id $process.pid -ErrorAction SilentlyContinue }
    throw
}
