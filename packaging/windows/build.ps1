param(
    [string]$PythonExe = ".\\.venv\\Scripts\\python.exe"
)

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$SpecPath = Join-Path $PSScriptRoot "ExcelAutoTool.spec"

$ResolvedPythonExe = $PythonExe
if (-not [System.IO.Path]::IsPathRooted($ResolvedPythonExe)) {
    $ResolvedPythonExe = Join-Path $ProjectRoot $ResolvedPythonExe
}

if (Test-Path $ResolvedPythonExe) {
    $PythonExe = $ResolvedPythonExe
} elseif (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Push-Location $ProjectRoot
try {
    & $PythonExe -c "import PIL, PyInstaller; print('Build Python:', __import__('sys').executable); print('Pillow:', PIL.__version__)"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Dependency build belum lengkap. Jalankan: .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
        exit $LASTEXITCODE
    }

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
