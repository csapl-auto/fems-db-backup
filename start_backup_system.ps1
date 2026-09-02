# ==============================================================================
# FEMS Backup & Disaster Recovery Manager - Windows Development Launcher
# ==============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Starting FEMS Dual-Environment Backup & DR Manager" -ForegroundColor Green
Write-Host " Dashboard Port: 5050" -ForegroundColor Yellow
Write-Host " Backup Storage: ./FEMS_Backup" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check Python
if (Get-Command python -ErrorAction SilentlyContinue) {
    python app.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 app.py
} else {
    Write-Host "[ERROR] Python was not found in your PATH." -ForegroundColor Red
}
