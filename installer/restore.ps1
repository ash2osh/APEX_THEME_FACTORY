# Windows PowerShell version of restore.sh. Preview by default; add --apply to restore the backup.
& (Join-Path $PSScriptRoot 'theme-factory-python.ps1') $PSScriptRoot -m lib.theme_factory.cli restore @args
exit $LASTEXITCODE
