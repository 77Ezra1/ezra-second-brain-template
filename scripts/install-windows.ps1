#requires -Version 5.1
param(
    [string]$Target = $(if ($env:SECOND_BRAIN_HOME) { $env:SECOND_BRAIN_HOME } else { Join-Path $HOME 'second-brain' }),
    [switch]$Force,
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'

function Resolve-PythonCommand {
    $candidates = @(
        @{ File = 'py'; Args = @('-3') },
        @{ File = 'python'; Args = @() },
        @{ File = 'python3'; Args = @() }
    )
    foreach ($candidate in $candidates) {
        try {
            $versionArgs = @($candidate.Args) + @('-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)')
            & $candidate.File @versionArgs | Out-Null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            continue
        }
    }
    throw 'Python 3.11+ is required. Install it from https://www.python.org/downloads/windows/ and retry.'
}

$python = Resolve-PythonCommand
$installerCode = "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"
$installArgs = @($python.Args) + @('-c', $installerCode, '--', '--platform', 'windows', '--target', $Target)
if ($Force) { $installArgs += '--force' }
if ($SkipTests) { $installArgs += '--skip-tests' }

& $python.File @installArgs
exit $LASTEXITCODE
