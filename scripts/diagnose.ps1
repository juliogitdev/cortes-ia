param([string]$OutputPath = 'runtime/diagnostics/environment.json')
$ErrorActionPreference = 'Stop'
function ToolInfo($Name, $Arguments) {
    $tool = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $tool) { return @{available=$false; path=$null; version=$null} }
    $version = (& $tool.Source @Arguments 2>&1 | Out-String).Trim()
    return @{available=$true; path=$tool.Source; version=$version}
}
$os = Get-CimInstance Win32_OperatingSystem
$system = Get-CimInstance Win32_ComputerSystem
$report = [ordered]@{
    observed_at_utc = [DateTime]::UtcNow.ToString('o')
    cwd = (Get-Location).Path
    os = @{caption=$os.Caption; version=$os.Version; architecture=$os.OSArchitecture}
    cpu = @(Get-CimInstance Win32_Processor | Select-Object Name)
    ram_bytes = $system.TotalPhysicalMemory
    disks = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,Size,FreeSpace)
    adapters = @(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM)
    tools = @{}
    gpu_validation = 'pending: adapter recognition is not CUDA inference validation'
}
foreach ($entry in @(@('python','--version'),@('git','--version'),@('uv','--version'),@('ffmpeg','-version'),@('ffprobe','-version'),@('nvidia-smi','--query-gpu=name,driver_version,memory.total,compute_cap','--format=csv,noheader'))) {
    $report.tools[$entry[0]] = ToolInfo $entry[0] $entry[1..($entry.Count-1)]
}
$parent = Split-Path -Parent $OutputPath
if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
$report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath $OutputPath
Write-Output "Diagnostic saved: $OutputPath"
