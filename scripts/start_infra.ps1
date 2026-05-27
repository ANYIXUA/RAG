param(
    [switch]$Pull,
    [switch]$BuildApp,
    [switch]$RefreshKnowledge,
    [switch]$WithApi
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$DotEnvValues = @{}
$DotEnvPath = Join-Path $ProjectRoot ".env"
if (Test-Path $DotEnvPath) {
    foreach ($line in Get-Content -Path $DotEnvPath -Encoding utf8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }

        $parts = $trimmed.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if ($name) {
            $DotEnvValues[$name] = $value
        }
    }
}

function Get-EffectiveSetting {
    param(
        [string]$Name,
        [string]$DefaultValue
    )

    $processValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ($null -ne $processValue -and $processValue -ne "") {
        return $processValue
    }
    if ($DotEnvValues.ContainsKey($Name) -and $DotEnvValues[$Name] -ne "") {
        return $DotEnvValues[$Name]
    }
    return $DefaultValue
}

if ($Pull) {
    Write-Host "Pulling PostgreSQL/pgvector image..."
    docker compose pull postgres
}

if ($BuildApp) {
    Write-Host "Building RAG application images..."
    docker compose build rag-api rag-refresh
}

Write-Host "Starting PostgreSQL/pgvector..."
docker compose up -d postgres

if ($RefreshKnowledge) {
    if (-not $BuildApp) {
        docker compose build rag-refresh
    }
    Write-Host "Refreshing knowledge base into PostgreSQL/pgvector..."
    docker compose --profile tools run --rm rag-refresh
}

if ($WithApi) {
    if (-not $BuildApp) {
        docker compose build rag-api
    }
    Write-Host "Starting RAG API..."
    docker compose up -d rag-api
}

$postgresPort = Get-EffectiveSetting "POSTGRES_PORT" "5432"
$postgresUser = Get-EffectiveSetting "POSTGRES_USER" "rag"
$postgresPassword = Get-EffectiveSetting "POSTGRES_PASSWORD" "rag_password"
$postgresDb = Get-EffectiveSetting "POSTGRES_DB" "rag"
$apiPort = Get-EffectiveSetting "RAG_API_PORT" "8000"

docker compose ps

Write-Host ""
Write-Host "PostgreSQL DSN: postgresql://$postgresUser`:$postgresPassword@127.0.0.1:$postgresPort/$postgresDb"
Write-Host "RAG API: http://127.0.0.1:$apiPort"
