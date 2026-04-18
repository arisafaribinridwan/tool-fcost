param(
    [string]$PythonExe = ".\\.venv\\Scripts\\python.exe"
)

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$SpecPath = Join-Path $PSScriptRoot "ExcelAutoTool.spec"

if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Push-Location $ProjectRoot
try {
    & $PythonExe -m PyInstaller --clean --noconfirm $SpecPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $DistRoot = Join-Path $ProjectRoot "dist\\ExcelAutoTool"
    Copy-Item -Force (Join-Path $ProjectRoot "run.bat") (Join-Path $DistRoot "run.bat")

    foreach ($RuntimeDir in @("configs", "masters", "uploads", "outputs")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $DistRoot $RuntimeDir) | Out-Null
    }

    Write-Host "Build selesai di $DistRoot"
} finally {
    Pop-Location
}
