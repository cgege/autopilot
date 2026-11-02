$ErrorActionPreference = "Stop"
$python = ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
  py -3.11 -m venv .venv
}
& $python -m pip install -r requirements.txt pyinstaller
& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name DeltaScreenBot `
  --paths src `
  --add-data "config;config" `
  --add-data "imgtest;imgtest" `
  launcher.py
Write-Host "Built dist\DeltaScreenBot.exe"
