# Execute locally on the original Windows 5800X computer (not in ChatGPT).
# Shows only the NEW website Basic Auth credentials to the user in their own
# terminal. Never reads or prints the ForecastEngine/Workers API bearer token.
$ErrorActionPreference = 'Stop'
$keyPath = Join-Path $HOME '.ssh\oracle_amd_ed25519'
if (!(Test-Path -LiteralPath $keyPath)) {
    throw "Authorized Oracle SSH key not found on this Windows computer."
}
Write-Host 'Open: https://161.33.19.220/web/'
Write-Host 'Your separate website login (do not paste credentials into chat):'
& ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -i $keyPath ubuntu@161.33.19.220 'sudo cat /etc/tw01-forecastengine/web-login.txt'
if ($LASTEXITCODE -ne 0) {
    throw "Unable to display website credentials. Check Windows COS SSH connectivity."
}
