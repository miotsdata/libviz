# packaging/windows/build.ps1 — builds the Windows installer.
#
# Run from anywhere, on Windows, in a checkout with `pdm install -G:all -d` done:
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
# Output: dist\libviz-gui\ (the app) and dist\LibViz-setup-<version>.exe
#
# Needs Inno Setup 6 (https://jrsoftware.org/isdl.php) for the last step;
# without it you still get the runnable dist\libviz-gui\ folder.
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")

# PowerShell 5.1 (Windows 10's default) doesn't stop on a failing native
# command, only on cmdlet errors — check every exit code by hand.
function Run([string]$what, [scriptblock]$cmd) {
    Write-Host "== $what"
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" }
}

Run "Running PyInstaller" { pdm run pyinstaller packaging/pyinstaller/libviz-gui.spec --noconfirm }

$version = pdm run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Warning "Inno Setup 6 not found; skipping installer. The app is in dist\libviz-gui\"
    exit 0
}
Run "Building installer" { & $iscc "/DAppVersion=$version" packaging\windows\libviz.iss }
Write-Host "Built dist\LibViz-setup-$version.exe"
