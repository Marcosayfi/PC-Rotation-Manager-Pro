# Find and update PC Rotation Manager IP address

$configPath = "C:\ProgramData\PCRotationManager\config.json"

# Get local IP (excluding loopback)
$ip = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1
).IPAddress

if ($ip) {
    Write-Host "Found local IP: $ip" -ForegroundColor Green
    
    # Update config
    $config = @{
        server_port = 8765
        advertised_ip = $ip
        admin_token = $null
    }
    
    $config | ConvertTo-Json | Out-File $configPath -Encoding UTF8
    
    Write-Host ""
    Write-Host "Config updated!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Mobile dashboard URL:" -ForegroundColor Cyan
    Write-Host "http://$ip`:8765/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Restart PC Rotation Manager for changes to take effect."
} else {
    Write-Host "Could not find local IP address" -ForegroundColor Red
}

Read-Host "Press Enter to close"
