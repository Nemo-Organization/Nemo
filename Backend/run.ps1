$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot

try {
    $pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw 'Install dependencies once with: uv sync --locked'
    }

    if (-not (Test-Path -LiteralPath '.env')) {
        Copy-Item -LiteralPath '.env.example' -Destination '.env'
    }

    & $pythonPath -m app
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
