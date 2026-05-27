param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot "logs\api.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "API pid file not found: $PidFile"
    return
}

$ProcessId = (Get-Content -Path $PidFile -Encoding utf8 | Select-Object -First 1).Trim()
if (-not $ProcessId) {
    Write-Host "API pid file is empty."
    return
}

$Process = Get-Process -Id ([int]$ProcessId) -ErrorAction SilentlyContinue
if ($null -eq $Process) {
    Write-Host "Process $ProcessId does not exist. Cleaning pid file."
    Remove-Item -Path $PidFile -Force
    return
}

Stop-Process -Id ([int]$ProcessId) -Force
Remove-Item -Path $PidFile -Force
Write-Host "API server stopped. PID: $ProcessId"
