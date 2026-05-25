param(
  [int]$ApiPort = 8014,
  [string]$FrontendUrl = "http://127.0.0.1:3013"
)

$ErrorActionPreference = "Stop"

if ($env:RUN_FULL_STACK_SMOKE -ne "1") {
  Write-Host "SKIP: set RUN_FULL_STACK_SMOKE=1 to run the Docker-backed full-stack smoke."
  exit 0
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ApiDir = Join-Path $RepoRoot "services/api"
$LogDir = Join-Path $RepoRoot ".data/full-stack-smoke"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$ApiBaseUrl = "http://127.0.0.1:$ApiPort"
$SmokeId = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$QdrantCollection = "proofpilot_smoke_$SmokeId"

function Set-SmokeEnv {
  $env:PROOFPILOT_ENV = "development"
  $env:PROOFPILOT_API_CORS_ORIGINS = $FrontendUrl
  $env:DATABASE_URL = "postgresql+asyncpg://proofpilot:proofpilot@127.0.0.1:55432/proofpilot"
  $env:REDIS_URL = "redis://127.0.0.1:6379/0"
  $env:QDRANT_URL = "http://127.0.0.1:6333"
  $env:QDRANT_COLLECTION = $QdrantCollection
  $env:UPLOAD_INDEXING_ENABLED = "true"
  $env:GEMINI_GENERATION_MODEL = "gemini-2.5-flash-lite"
  $env:GEMINI_LIGHTWEIGHT_MODEL = "gemini-2.5-flash-lite"
  $env:GEMINI_FRESH_MODEL = "gemini-2.5-flash-lite"
  $env:GEMINI_SEARCH_GROUNDING_FALLBACK_MODEL = "gemini-2.5-flash-lite"
  $env:GEMINI_EMBEDDINGS_ENABLED = "false"
  $env:GEMINI_SEARCH_GROUNDING_ENABLED = "false"
  $env:PROOFPILOT_RATE_LIMITING_ENABLED = "false"
  $env:NEXT_PUBLIC_API_BASE_URL = $ApiBaseUrl
  $env:PROOFPILOT_E2E_FRONTEND_URL = $FrontendUrl
  if ($env:RUN_FULL_STACK_GEMINI_LIVE -ne "1") {
    $env:GEMINI_API_KEY = ""
    $env:GEMINI_PROVIDER_MODE = "mock"
  } else {
    $env:GEMINI_PROVIDER_MODE = "google"
  }
}

function Wait-HttpOk {
  param([string]$Url, [int]$TimeoutSeconds = 60)
  $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $Deadline) {
    try {
      $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 300) {
        return
      }
    } catch {
      Start-Sleep -Seconds 1
    }
  }
  throw "Timed out waiting for $Url"
}

function Assert-PortFree {
  param([int]$Port)
  $Listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($Listener) {
    throw "Port $Port is already in use. Stop the existing process or pass -ApiPort with a free port."
  }
}

function Start-SmokeProcess {
  param(
    [string]$Name,
    [string]$WorkingDirectory,
    [string]$Command
  )
  $OutFile = Join-Path $LogDir "$Name.out.log"
  $ErrFile = Join-Path $LogDir "$Name.err.log"
  $Encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
  Start-Process `
    -FilePath "powershell" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $Encoded) `
    -WorkingDirectory $WorkingDirectory `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutFile `
    -RedirectStandardError $ErrFile `
    -PassThru
}

Set-SmokeEnv
$Processes = @()
$FrontendPort = ([Uri]$FrontendUrl).Port
$PlaywrightExitCode = 0

try {
  Assert-PortFree -Port $ApiPort
  Assert-PortFree -Port $FrontendPort

  docker compose -f (Join-Path $RepoRoot "infra/docker-compose.yml") up -d
  Push-Location $ApiDir
  uv run alembic upgrade head
  Pop-Location

  $Processes += Start-SmokeProcess `
    -Name "api" `
    -WorkingDirectory $ApiDir `
    -Command "Set-Location '$ApiDir'; `$env:PROOFPILOT_ENV='$env:PROOFPILOT_ENV'; `$env:PROOFPILOT_API_CORS_ORIGINS='$env:PROOFPILOT_API_CORS_ORIGINS'; `$env:DATABASE_URL='$env:DATABASE_URL'; `$env:REDIS_URL='$env:REDIS_URL'; `$env:QDRANT_URL='$env:QDRANT_URL'; `$env:QDRANT_COLLECTION='$env:QDRANT_COLLECTION'; `$env:UPLOAD_INDEXING_ENABLED='$env:UPLOAD_INDEXING_ENABLED'; `$env:GEMINI_API_KEY='$env:GEMINI_API_KEY'; `$env:GEMINI_PROVIDER_MODE='$env:GEMINI_PROVIDER_MODE'; `$env:GEMINI_GENERATION_MODEL='$env:GEMINI_GENERATION_MODEL'; `$env:GEMINI_LIGHTWEIGHT_MODEL='$env:GEMINI_LIGHTWEIGHT_MODEL'; `$env:GEMINI_FRESH_MODEL='$env:GEMINI_FRESH_MODEL'; `$env:GEMINI_SEARCH_GROUNDING_FALLBACK_MODEL='$env:GEMINI_SEARCH_GROUNDING_FALLBACK_MODEL'; `$env:GEMINI_EMBEDDINGS_ENABLED='$env:GEMINI_EMBEDDINGS_ENABLED'; `$env:GEMINI_SEARCH_GROUNDING_ENABLED='$env:GEMINI_SEARCH_GROUNDING_ENABLED'; `$env:PROOFPILOT_RATE_LIMITING_ENABLED='$env:PROOFPILOT_RATE_LIMITING_ENABLED'; uv run uvicorn app.main:app --host 127.0.0.1 --port $ApiPort"

  Wait-HttpOk -Url "$ApiBaseUrl/api/v1/health" -TimeoutSeconds 90

  $Processes += Start-SmokeProcess `
    -Name "worker" `
    -WorkingDirectory $ApiDir `
    -Command "Set-Location '$ApiDir'; `$env:PROOFPILOT_ENV='$env:PROOFPILOT_ENV'; `$env:DATABASE_URL='$env:DATABASE_URL'; `$env:REDIS_URL='$env:REDIS_URL'; `$env:QDRANT_URL='$env:QDRANT_URL'; `$env:QDRANT_COLLECTION='$env:QDRANT_COLLECTION'; `$env:UPLOAD_INDEXING_ENABLED='$env:UPLOAD_INDEXING_ENABLED'; `$env:GEMINI_API_KEY='$env:GEMINI_API_KEY'; `$env:GEMINI_PROVIDER_MODE='$env:GEMINI_PROVIDER_MODE'; `$env:GEMINI_EMBEDDINGS_ENABLED='$env:GEMINI_EMBEDDINGS_ENABLED'; uv run python -m app.ingestion.worker"

  pnpm --filter "@proofpilot/web" e2e -- e2e/full-stack-smoke.spec.ts
  $PlaywrightExitCode = $LASTEXITCODE
  if ($PlaywrightExitCode -ne 0) {
    throw "Playwright full-stack smoke failed with exit code $PlaywrightExitCode."
  }
  Write-Host "PASS: Docker-backed full-stack smoke completed with collection $QdrantCollection"
} finally {
  foreach ($Process in $Processes) {
    if ($Process -and -not $Process.HasExited) {
      taskkill /PID $Process.Id /T /F 2>$null | Out-Null
    }
  }
  Pop-Location -ErrorAction SilentlyContinue
}
