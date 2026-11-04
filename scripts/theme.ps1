# Windows PowerShell version of theme.sh.
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $root 'installer/theme-factory-python.ps1') $root -m lib.theme_factory.cli @args
exit $LASTEXITCODE
