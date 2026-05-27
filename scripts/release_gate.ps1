param(
    [Parameter(Mandatory=$true)]
    [string]$Dataset,
    [int]$TopK = 3,
    [string]$RerankProvider = "none",
    [string]$RerankModel = "",
    [switch]$SkipRefresh,
    [switch]$SkipUnitTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot"

if (-not $SkipRefresh) {
    Write-Host "Refreshing PostgreSQL/pgvector knowledge base..."
    python -m rag_app.cli offline-refresh --source data --reset
}

if (-not $SkipUnitTests) {
    Write-Host "Running unit tests..."
    python -m unittest discover
}

$evalArgs = @(
    "-m",
    "rag_app.cli",
    "evaluate-retrieval",
    "--dataset",
    $Dataset,
    "--top-k",
    "$TopK",
    "--with-rerank-provider",
    $RerankProvider,
    "--fail-on-gate"
)

if ($RerankModel -ne "") {
    $evalArgs += @("--with-rerank-model", $RerankModel)
}

Write-Host "Running retrieval release gate..."
python @evalArgs

Write-Host "Release gate completed."
