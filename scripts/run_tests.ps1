param(
    [switch]$SkipCompile
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot"

if (-not $SkipCompile) {
    Write-Host "Running Python compile check..."
    python -m compileall rag_app tests
}

Write-Host "Running unit tests..."
python -m unittest discover

Write-Host "Tests completed."
