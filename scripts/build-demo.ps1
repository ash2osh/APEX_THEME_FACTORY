# Windows PowerShell version of build-demo.sh.
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $root 'installer/theme-factory-python.ps1') $root (Join-Path $root 'tools/build_demo.py') @args
exit $LASTEXITCODE
