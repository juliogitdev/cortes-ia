param([string]$OutputPath = 'storage/demo/demo.mp4')
$ErrorActionPreference = 'Stop'
# Amostra artificial local; não é benchmark editorial de lives.
Add-Type -AssemblyName System.Speech
$destination = [IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $destination) { throw 'Destino já existe; preserve-o ou escolha outro OutputPath.' }
New-Item -ItemType Directory -Force ([IO.Path]::GetDirectoryName($destination)) | Out-Null
$audioPath = [IO.Path]::ChangeExtension($destination, '.wav')
if (Test-Path -LiteralPath $audioPath) { throw 'Áudio já existe; escolha outro destino.' }
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voice = $synth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | Select-Object -First 1
    if (-not $voice) { throw 'Voz portuguesa local ausente. Use um vídeo de teste autorizado.' }
    $synth.SelectVoice($voice.VoiceInfo.Name)
    $synth.Rate = -1
    $synth.SetOutputToWaveFile($audioPath)
    $synth.Speak('Este teste da plataforma de cortes usa um computador local. Vamos analisar este material, escolher um trecho, ajustar os limites e baixar o resultado final.')
} finally { $synth.Dispose() }
$pythonPath = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
$ffmpegPath = & $pythonPath -c "from clip_platform.media.tools import find_tool; print(find_tool('ffmpeg'))"
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg indisponível. Execute bootstrap_media.ps1.' }
& $ffmpegPath -hide_banner -loglevel error -nostdin -f lavfi -i 'testsrc2=size=320x240:rate=25' -i $audioPath -t 30 -af apad -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac -movflags +faststart $destination
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar a amostra.' }
Write-Output "Amostra sintética criada: $destination"
