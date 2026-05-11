$ErrorActionPreference = "Stop"

$kaggleDir = Join-Path $env:USERPROFILE ".kaggle"
$tokenPath = Join-Path $kaggleDir "access_token"

New-Item -ItemType Directory -Force -Path $kaggleDir | Out-Null
$token = Read-Host "Paste Kaggle KGAT token"

if ([string]::IsNullOrWhiteSpace($token) -or -not $token.StartsWith("KGAT_")) {
    throw "That does not look like a KGAT access token."
}

Set-Content -LiteralPath $tokenPath -Value $token.Trim() -NoNewline -Encoding ascii
Write-Host "Saved Kaggle access token to $tokenPath"
Write-Host "Now test with: .\kaggle.ps1 competitions files orbit-wars"
