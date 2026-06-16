$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
$pyinstaller = Join-Path $projectDir ".venv\Scripts\pyinstaller.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Error: Virtual environment not found at $venvPython" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $pyinstaller)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    & $venvPython -m pip install pyinstaller
}

Write-Host "Building MeetTimer..." -ForegroundColor Green
& $pyinstaller --clean --noconfirm "gac_timer.spec"

$outputDir = Join-Path $projectDir "dist\会帮手"
if (Test-Path $outputDir) {
    Write-Host "Build successful! Output at: $outputDir" -ForegroundColor Green
    Write-Host "Run 会帮手.exe from the output directory." -ForegroundColor Cyan
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}