$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$directory = Join-Path $root 'models'
$target = Join-Path $directory 'face_detection_yunet_2023mar.onnx'
$expected = '8F2383E4DD3CFBB4553EA8718107FC0423210DC964F9F4280604804ED2552FA4'
New-Item -ItemType Directory -Force -Path $directory | Out-Null
if (Test-Path -LiteralPath $target) {
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash -eq $expected) {
        Write-Output "Modelo de rostos pronto: $target"
        exit 0
    }
    throw 'Modelo de rostos existente com hash inesperado; preserve e inspecione o arquivo.'
}
$temporary = Join-Path $directory ('.face-model-' + [guid]::NewGuid().ToString('N') + '.onnx')
try {
    Invoke-WebRequest -Uri 'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx' -OutFile $temporary
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $temporary).Hash -ne $expected) {
        throw 'Hash do modelo de rostos não corresponde ao arquivo oficial esperado.'
    }
    Move-Item -LiteralPath $temporary -Destination $target
    Write-Output "Modelo de rostos instalado: $target"
} finally {
    Remove-Item -LiteralPath $temporary -ErrorAction SilentlyContinue
}
