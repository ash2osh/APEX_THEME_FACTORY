# Windows PowerShell version of install-all-themes.sh. Preview by default; add --apply to install.
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $root 'installer/theme-factory-python.ps1') $root (Join-Path $root 'scripts/install_all_themes.py') @args
exit $LASTEXITCODE
