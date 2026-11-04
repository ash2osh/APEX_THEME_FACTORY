# Runs Python 3.10+ with the Theme Factory code on its path. Works in Windows PowerShell 5.1 and PowerShell 7.
# Usage: theme-factory-python.ps1 <root folder> <python arguments...>
$root = $args[0]
$pythonArgs = @($args | Select-Object -Skip 1)

function Find-Python {
    foreach ($candidate in @(@('py', '-3'), @('python3'), @('python'))) {
        if (-not (Get-Command $candidate[0] -CommandType Application -ErrorAction SilentlyContinue)) { continue }
        $launcher = @($candidate | Select-Object -Skip 1)
        # The Microsoft Store placeholder is named python too, and it fails this check.
        $version = & $candidate[0] @launcher -c 'import sys; print("%d %d" % sys.version_info[:2])' 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $version) { continue }
        $parts = "$version".Trim() -split ' '
        if ([int]$parts[0] -gt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10)) { return ,@($candidate) }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    [Console]::Error.WriteLine('Python 3.10+ is required. Install it from https://www.python.org/downloads/')
    exit 2
}
$launcher = @($python | Select-Object -Skip 1)

$saved = @{}
$settings = @{ PYTHONPATH = "$root"; PYTHONDONTWRITEBYTECODE = '1'; PYTHONUTF8 = '1' }
foreach ($name in $settings.Keys) {
    $saved[$name] = [Environment]::GetEnvironmentVariable($name)
    [Environment]::SetEnvironmentVariable($name, $settings[$name])
}
try {
    & $python[0] @launcher @pythonArgs
    $code = $LASTEXITCODE
} finally {
    foreach ($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name, $saved[$name]) }
}
exit $code
