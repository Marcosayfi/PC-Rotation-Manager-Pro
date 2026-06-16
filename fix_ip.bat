@echo off
REM Find local IP address and update PC Rotation Manager config

echo Finding your local IP address...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| find "IPv4 Address"') do (
    set IP=%%a
    goto :found
)

:found
if defined IP (
    echo Your IP address is: %IP%
    echo.
    echo Updating config.json...
    
    REM Create a new config.json with the correct IP
    (
        echo {
        echo   "server_port": 8765,
        echo   "advertised_ip": "%IP%",
        echo   "admin_token": null
        echo }
    ) > "C:\ProgramData\PCRotationManager\config.json"
    
    echo Config updated!
    echo.
    echo You can now access the mobile dashboard at:
    echo http://%IP%:8765/
    echo.
    pause
) else (
    echo Could not find IP address.
    pause
)
