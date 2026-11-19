# Sets up EchoLocal on Windows: the voice-cloning TTS (Chatterbox), translation (NLLB-200) and
# speech to text / the check (faster-whisper).
# Run from this folder:  powershell -ExecutionPolicy Bypass -File .\setup.ps1
# Options: -Cpu forces the CPU build even if an NVIDIA GPU is present. -SkipWhisper skips speech to text
# and the check. -SkipTranslation skips the translation model. -SkipModels installs the packages only.
# Downloaded: uv (if missing), Python, the Python packages (about 3 GB with CUDA), then the models
# from Hugging Face (Chatterbox 4 GB, NLLB 2.4 GB, Whisper 1.6 GB). After that everything runs offline.
# Re-running it rebuilds the venvs; models already downloaded are kept.
param([switch]$Cpu, [switch]$SkipWhisper, [switch]$SkipTranslation, [switch]$SkipModels)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }

Step 'uv'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv not found, installing it (astral.sh)...'
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
uv --version

$gpu = $false
if (-not $Cpu -and (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    if ($LASTEXITCODE -eq 0) { $gpu = $true }
}
$torchIndex = if ($gpu) { 'https://download.pytorch.org/whl/cu124' } else { 'https://download.pytorch.org/whl/cpu' }
Write-Host ("Build: " + $(if ($gpu) { 'CUDA 12.4 (NVIDIA GPU)' } else { 'CPU only (slow: about 1 minute per sentence)' }))

Step 'Chatterbox venv'
$cb = Join-Path $root 'Chatterbox'
uv venv --clear --python 3.11 "$cb\venv"
$py = "$cb\venv\Scripts\python.exe"
# torch first from the PyTorch index: from PyPI on Windows torch 2.6.0 is the CPU build.
uv pip install --python $py torch==2.6.0 torchaudio==2.6.0 --index-url $torchIndex
# setuptools<81: resemble-perth needs pkg_resources, otherwise the model fails with "'NoneType' object is not callable".
# av (PyAV): decodes .m4a/.mp3 reference recordings, which librosa cannot read without ffmpeg.
uv pip install --python $py chatterbox-tts==0.1.7 "setuptools<81" av==18.1.0 -c "$cb\constraints.txt"
if ($LASTEXITCODE -ne 0) { throw 'Chatterbox install failed' }

if (-not $SkipWhisper) {
    Step 'Whisper venv'
    $wh = Join-Path $root 'Whisper'
    # 3.13: the pinned numpy 2.5.4 needs Python 3.12+.
    uv venv --clear --python 3.13 "$wh\venv"
    $wpy = "$wh\venv\Scripts\python.exe"
    $pkgs = @('faster-whisper==1.2.1')
    if ($gpu) { $pkgs += @('nvidia-cublas-cu12', 'nvidia-cudnn-cu12', 'nvidia-cuda-nvrtc-cu12') }
    uv pip install --python $wpy @pkgs -c "$wh\constraints.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Whisper install failed' }
}

if (-not $SkipModels) {
    Step 'Models (from Hugging Face)'
    $dl = @("$cb\download.py")
    if ($SkipTranslation) { $dl += '--skip-translation' }
    & $py @dl
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed (re-run setup to resume)' }
    if (-not $SkipWhisper) {
        & $wpy "$wh\transcribe.py" --download
        if ($LASTEXITCODE -ne 0) { throw 'Whisper model download failed (re-run setup to resume)' }
    }
}

New-Item -ItemType Directory -Force -Path (Join-Path $root 'voices'), (Join-Path $root 'outputs') | Out-Null

Step 'Check'
& $py -c "import torch; print('torch', torch.__version__, '| CUDA:', torch.cuda.is_available())"
Write-Host "`nDone. Put a 5-15 s recording of a voice in the voices folder, then run webui.bat." -ForegroundColor Green
