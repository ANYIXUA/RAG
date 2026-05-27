param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload,
    [switch]$RefreshKnowledge,
    [switch]$Background
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:RAG_DATA_DIR = if ($env:RAG_DATA_DIR) { $env:RAG_DATA_DIR } else { "data" }
$env:RAG_STORAGE_DIR = if ($env:RAG_STORAGE_DIR) { $env:RAG_STORAGE_DIR } else { "storage" }
$env:RAG_COLLECTION_NAME = if ($env:RAG_COLLECTION_NAME) { $env:RAG_COLLECTION_NAME } else { "default" }
$env:RAG_LLM_PROVIDER = if ($env:RAG_LLM_PROVIDER) { $env:RAG_LLM_PROVIDER } else { "openai" }
$env:RAG_EMBEDDING_PROVIDER = if ($env:RAG_EMBEDDING_PROVIDER) { $env:RAG_EMBEDDING_PROVIDER } else { "openai" }
$env:RAG_EMBEDDING_DIMENSION = if ($env:RAG_EMBEDDING_DIMENSION) { $env:RAG_EMBEDDING_DIMENSION } else { "1024" }
$env:RAG_EMBEDDING_BATCH_SIZE = if ($env:RAG_EMBEDDING_BATCH_SIZE) { $env:RAG_EMBEDDING_BATCH_SIZE } else { "10" }
$env:OPENAI_BASE_URL = if ($env:OPENAI_BASE_URL) { $env:OPENAI_BASE_URL } else { "https://dashscope.aliyuncs.com/compatible-mode/v1" }
$env:OPENAI_CHAT_MODEL = if ($env:OPENAI_CHAT_MODEL) { $env:OPENAI_CHAT_MODEL } else { "qwen-plus" }
$env:OPENAI_MAX_TOKENS = if ($env:OPENAI_MAX_TOKENS) { $env:OPENAI_MAX_TOKENS } else { "800" }
$env:OPENAI_EMBEDDING_MODEL = if ($env:OPENAI_EMBEDDING_MODEL) { $env:OPENAI_EMBEDDING_MODEL } else { "text-embedding-v4" }
$env:RAG_OPS_STORE_PROVIDER = if ($env:RAG_OPS_STORE_PROVIDER) { $env:RAG_OPS_STORE_PROVIDER } else { "postgresql" }
$env:RAG_OPS_POSTGRES_DSN = if ($env:RAG_OPS_POSTGRES_DSN) { $env:RAG_OPS_POSTGRES_DSN } else { "postgresql://rag:rag_password@localhost:15432/rag" }
$env:RAG_ORDER_STATUS_POSTGRES_DSN = if ($env:RAG_ORDER_STATUS_POSTGRES_DSN) { $env:RAG_ORDER_STATUS_POSTGRES_DSN } else { $env:RAG_OPS_POSTGRES_DSN }
$env:RAG_VECTOR_STORE_PROVIDER = if ($env:RAG_VECTOR_STORE_PROVIDER) { $env:RAG_VECTOR_STORE_PROVIDER } else { "postgresql" }

if ($RefreshKnowledge) {
    Write-Host "Refresh requested. Running offline refresh against PostgreSQL/pgvector first."
    python -m rag_app.cli offline-refresh --source $env:RAG_DATA_DIR --reset
}

$PythonPath = (Get-Command python).Source
$UvicornArgs = @(
    "-m",
    "uvicorn",
    "rag_app.api:app",
    "--host",
    $HostName,
    "--port",
    "$Port"
)

if ($Reload) {
    $UvicornArgs += "--reload"
}

if ($Background) {
    $LogDir = Join-Path $ProjectRoot "logs"
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    $StdoutLog = Join-Path $LogDir "api_stdout.log"
    $StderrLog = Join-Path $LogDir "api_stderr.log"
    $PidFile = Join-Path $LogDir "api.pid"

    $Process = Start-Process `
        -FilePath $PythonPath `
        -ArgumentList $UvicornArgs `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -PassThru

    Set-Content -Path $PidFile -Value $Process.Id -Encoding utf8
    Write-Host "API server started in background."
    Write-Host "URL: http://$HostName`:$Port"
    Write-Host "PID: $($Process.Id)"
    Write-Host "Logs: $StdoutLog / $StderrLog"
    return
}

Write-Host "Starting API server at http://$HostName`:$Port"
python @UvicornArgs
