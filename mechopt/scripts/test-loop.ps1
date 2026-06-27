param(
    [string[]]$PytestArgs = @("-q"),
    [int]$MaxRuns = 0,
    [int]$DelaySeconds = 2,
    [switch]$Watch
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

function Test-CommandExists {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-TestRun {
    $env:UV_CACHE_DIR = Join-Path $ProjectRoot ".uv-cache"
    $script:TestExitCode = 0

    if (Test-CommandExists "uv") {
        & uv run --with-requirements requirements.txt pytest @PytestArgs
        $script:TestExitCode = $LASTEXITCODE
        return
    }

    if (Test-CommandExists "python") {
        & python -m pytest @PytestArgs
        $script:TestExitCode = $LASTEXITCODE
        return
    }

    if (Test-CommandExists "py") {
        & py -m pytest @PytestArgs
        $script:TestExitCode = $LASTEXITCODE
        return
    }

    Write-Host "No Python runner found. Install Python or uv, then rerun this script." -ForegroundColor Red
    $script:TestExitCode = 127
}

function Get-SourceFingerprint {
    $paths = @("mechopt", "tests", "app.py", "requirements.txt", "pytest.ini")
    $items = foreach ($path in $paths) {
        if (Test-Path $path) {
            Get-ChildItem $path -Recurse -File |
                Where-Object { $_.FullName -notmatch "\\(__pycache__|\.pytest_cache|\.uv-cache)\\" }
        }
    }

    ($items | Sort-Object FullName | ForEach-Object {
        "$($_.FullName)|$($_.LastWriteTimeUtc.Ticks)|$($_.Length)"
    }) -join "`n"
}

$run = 0
$lastFingerprint = $null

while ($true) {
    if ($Watch) {
        $fingerprint = Get-SourceFingerprint
        if ($fingerprint -eq $lastFingerprint) {
            Start-Sleep -Seconds $DelaySeconds
            continue
        }
        $lastFingerprint = $fingerprint
    }

    $run += 1
    Write-Host ""
    Write-Host "== MechOpt test loop run #$run ==" -ForegroundColor Cyan
    Invoke-TestRun
    $exitCode = $script:TestExitCode

    if ($exitCode -eq 0) {
        Write-Host "Tests are green." -ForegroundColor Green
        if (-not $Watch) {
            exit 0
        }
    } else {
        Write-Host "Tests failed with exit code $exitCode. Fix the implementation, then the loop will rerun." -ForegroundColor Yellow
        if (-not $Watch) {
            exit $exitCode
        }
    }

    if ($MaxRuns -gt 0 -and $run -ge $MaxRuns) {
        exit $exitCode
    }

    Start-Sleep -Seconds $DelaySeconds
}
