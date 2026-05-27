param(
    [string]$Source = "data",
    [switch]$Reset,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$ArgsList = @("offline-refresh", "--source", $Source)
if ($Reset) {
    $ArgsList += "--reset"
}
if ($Force) {
    $ArgsList += "--force"
}

Write-Host "Refreshing PostgreSQL/pgvector knowledge base. Source: $Source"
python -m rag_app.cli @ArgsList
Write-Host "Knowledge refresh completed."
