param(
    [switch]$SkipDockerBuild,
    [switch]$SkipRefresh,
    [switch]$SkipUnitTests,
    [switch]$SkipEvaluation,
    [string]$Dataset = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot"
Write-Host "Checking version information..."
python -m rag_app.cli version

Write-Host "Compiling Python files..."
python -m compileall rag_app tests

if (-not $SkipUnitTests) {
    Write-Host "Running unit tests..."
    python -m unittest discover
}

if (-not $SkipRefresh) {
    Write-Host "Refreshing PostgreSQL/pgvector knowledge base..."
    python -m rag_app.cli offline-refresh --source data --reset
}

if (-not $SkipEvaluation) {
    if ($Dataset -eq "") {
        throw "Release evaluation requires -Dataset <path-to-production-eval-jsonl>."
    }
    Write-Host "Running retrieval release gate..."
    python -m rag_app.cli evaluate-retrieval `
        --dataset $Dataset `
        --top-k 3 `
        --with-rerank-provider none `
        --fail-on-gate
}

if (-not $SkipDockerBuild) {
    Write-Host "Running Docker build check..."
    docker compose build rag-api
}

Write-Host "Release check completed."
