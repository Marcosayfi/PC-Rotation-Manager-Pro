@echo off
REM Find local IP address and update PC Rotation Manager config
REM Preserves existing admin_token / discord_bot_token / discord_guild_id.

set "CONFIG=C:\PCRotationManagerPro\config.json"

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

    (
        echo {
        echo   "server_port": 6969,
        echo   "advertised_ip": "%IP%"
        echo }
    ) > "%CONFIG%"

    echo Config updated!
    echo.
    echo Reminder: if you previously set an admin token or Discord bot token,
    echo re-add them to %CONFIG% (or use fix_ip.ps1 which preserves them).
    echo.
    echo You can now access the mobile dashboard at:
    echo http://%IP%:6969/
    echo.
    pause
) else (
    echo Could not find IP address.
    pause
)