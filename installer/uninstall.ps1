# Windows PowerShell version of uninstall.sh. Preview by default; add --apply to remove the theme.
& (Join-Path $PSScriptRoot 'theme-factory-python.ps1') $PSScriptRoot -m lib.theme_factory.cli uninstall --package-root $PSScriptRoot @args
exit $LASTEXITCODE
