# Find and update PC Rotation Manager IP address
# Updates only advertised_ip + server_port, preserving admin_token,
# discord_bot_token, and discord_guild_id already in config.json.

$configPath = "C:\PCRotationManagerPro\config.json"
$configDir = Split-Path -Parent $configPath

if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# Load existing config (if any) so we never wipe secrets/tokens
$config = @{}
if (Test-Path $configPath) {
    try {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json -AsHashtable
    } catch {
        Write-Host "Existing config could not be parsed — starting fresh." -ForegroundColor Yellow
    }
}

# Get local IP (excluding loopback)
$ip = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1
).IPAddress

if ($ip) {
    Write-Host "Found local IP: $ip" -ForegroundColor Green

    # Update only the network fields
    $config["server_port"] = 6969
    $config["advertised_ip"] = $ip

    $config | ConvertTo-Json -Depth 5 | Out-File $configPath -Encoding UTF8

    Write-Host ""
    Write-Host "Config updated!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Mobile dashboard URL:" -ForegroundColor Cyan
    Write-Host "http://$ip`:6969/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Restart PC Rotation Manager for changes to take effect."
} else {
    Write-Host "Could not find local IP address" -ForegroundColor Red
}

Read-Host "Press Enter to close"