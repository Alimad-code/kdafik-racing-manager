[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$tlsDirectory = Join-Path $PSScriptRoot "..\tls\local"

$opensslCommand = Get-Command openssl -ErrorAction SilentlyContinue
$opensslPath = if ($opensslCommand) {
    $opensslCommand.Source
} else {
    @(
        "C:\Program Files\OpenSSL-Win64\bin\openssl.exe",
        "C:\Program Files\Git\usr\bin\openssl.exe"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $opensslPath) {
    throw "openssl is required to generate the local kdafik.localhost certificate."
}

$opensslDirectory = Split-Path -Parent $opensslPath
$configCandidates = @(
    $env:OPENSSL_CONF,
    (Join-Path $opensslDirectory "..\ssl\openssl.cnf"),
    (Join-Path $opensslDirectory "openssl.cnf"),
    "C:\Program Files\Common Files\SSL\openssl.cnf"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$configPath = $configCandidates | Select-Object -First 1
if (-not $configPath) {
    throw "openssl.cnf was not found. Set OPENSSL_CONF to a valid OpenSSL configuration file."
}

New-Item -ItemType Directory -Path $tlsDirectory -Force | Out-Null

$keyPath = Join-Path $tlsDirectory "privkey.pem"
$certificatePath = Join-Path $tlsDirectory "fullchain.pem"

& $opensslPath req -config $configPath -x509 -newkey rsa:2048 -sha256 -nodes -days 30 `
    -keyout $keyPath `
    -out $certificatePath `
    -subj "/CN=kdafik.localhost" `
    -addext "subjectAltName=DNS:kdafik.localhost"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $keyPath) -or -not (Test-Path -LiteralPath $certificatePath)) {
    throw "OpenSSL failed to create the local kdafik.localhost certificate."
}

Write-Host "Created local-only TLS assets in $tlsDirectory. They are ignored by Git."
