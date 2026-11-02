# Pasang Vesper-Agent di Windows.
# Pemakaian (PowerShell, dari folder proyek):
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = "Stop"

$Src    = Split-Path -Parent $MyInvocation.MyCommand.Path
$Prefix = Join-Path $env:USERPROFILE ".vesper-agent"
$App    = Join-Path $Prefix "app"
$Venv   = Join-Path $Prefix "venv"
$BinDir = Join-Path $Prefix "bin"

Write-Host "==> Memeriksa Python"
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PyExe = "py"; $PyArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PyExe = "python"; $PyArgs = @()
} else {
    throw "Python belum ada. Pasang dari python.org dan centang 'Add python.exe to PATH'."
}

& $PyExe @PyArgs -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) { throw "Butuh Python 3.10 atau lebih baru." }

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Warning "ollama belum terpasang. Pasang dari https://ollama.com"
}

Write-Host "==> Menyalin aplikasi ke $App"
if (Test-Path $App) { Remove-Item -Recurse -Force $App }
New-Item -ItemType Directory -Force -Path $App, $BinDir | Out-Null
Get-ChildItem -Path $Src -Force |
    Where-Object { $_.Name -notin @(".git", ".venv", "__pycache__") } |
    Copy-Item -Destination $App -Recurse -Force

Write-Host "==> Membuat lingkungan Python (venv)"
if (Test-Path $Venv) { Remove-Item -Recurse -Force $Venv }
& $PyExe @PyArgs -m venv $Venv
$VenvPy = Join-Path $Venv "Scripts\python.exe"

Write-Host "==> Memasang paket"
& $VenvPy -m pip install -q --upgrade pip
& $VenvPy -m pip install -q -r (Join-Path $App "requirements.txt")

Write-Host "==> Membuat perintah vesper"
$Launcher = Join-Path $BinDir "vesper.cmd"
$AppMain  = Join-Path $App "main.py"
$content  = "@echo off`r`n`"$VenvPy`" `"$AppMain`" %*`r`n"
Set-Content -Path $Launcher -Value $content -Encoding ASCII

# tambahkan folder bin ke PATH pengguna (sekali saja)
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($null -eq $userPath) { $userPath = "" }
$pathAdded = $false
if (-not (($userPath -split ";") -contains $BinDir)) {
    $newPath = (($userPath.TrimEnd(";") + ";" + $BinDir)).TrimStart(";")
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $pathAdded = $true
}

$info = @{ os = "windows"; launcher = $Launcher; path_added = $pathAdded } | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $Prefix "install.json"), $info)

Write-Host ""
Write-Host "Selesai. Buka PowerShell atau CMD baru, lalu ketik: vesper"