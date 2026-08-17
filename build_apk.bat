@echo off
echo ============================================
echo   Building PC Rotation Manager Pro APK...
echo ============================================
echo.

cd /d "%~dp0mobile port\PCRotationManagerPro"

echo [1/3] Running Gradle assembleDebug...
call gradlew.bat assembleDebug
if %ERRORLEVEL% neq 0 (
    echo.
    echo BUILD FAILED! Check errors above.
    pause
    exit /b 1
)

echo.
echo [2/3] Removing old APK...
del /f "%~dp0apk\PC Rotation Manager Pro.apk" 2>nul

echo [3/3] Copying new APK...
copy /y "app\build\outputs\apk\debug\app-debug.apk" "%~dp0apk\PC Rotation Manager Pro.apk"
if %ERRORLEVEL% neq 0 (
    echo.
    echo COPY FAILED! Check the build output path.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Done! APK is at:
echo   %~dp0apk\PC Rotation Manager Pro.apk
echo ============================================
pause