param(
  [switch]$Clean
)

$ErrorActionPreference = 'Stop'

if ($Clean) {
  Write-Host "Cleaning build artifacts..."
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, .build, *.spec
}

# Ensure venv
if (-not (Test-Path .venv\Scripts\python.exe)) {
  Write-Host "Creating virtual environment..."
  python -m venv .venv
}

$py = ".venv\Scripts\python.exe"
$pip = ".venv\Scripts\pip.exe"
$pyinstaller = ".venv\Scripts\pyinstaller.exe"

& $pip install -U pip
& $pip install -e .[dev]

Write-Host "Running tests..."
& $py -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Building standalone exe..."
& $pyinstaller TacviewLogAnalyzer.spec

Write-Host "Testing executable..."
& .\dist\TacviewLogAnalyzer.exe --help
if ($LASTEXITCODE -eq 0) {
  $size = (Get-Item ".\dist\TacviewLogAnalyzer.exe").Length
  $sizeMB = [Math]::Round($size / 1MB, 1)
  Write-Host "✅ Build successful! Size: $sizeMB MB" -ForegroundColor Green
}
else {
  Write-Host "❌ Executable test failed!" -ForegroundColor Red
  exit 1
}

Write-Host "Done. See dist/ folder."
