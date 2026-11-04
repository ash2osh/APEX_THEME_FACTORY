# Windows PowerShell version of install.sh. Preview by default; add --apply to install.
& (Join-Path $PSScriptRoot 'theme-factory-python.ps1') $PSScriptRoot -m lib.theme_factory.cli install --package-root $PSScriptRoot @args
exit $LASTEXITCODE
