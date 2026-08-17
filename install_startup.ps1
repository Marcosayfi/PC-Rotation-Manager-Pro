# Install PC Rotation Manager Pro to run at Windows startup
# Run once in PowerShell (as the user who shares the PC):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
#   .\install_startup.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($PyCmd) {
    $Python = $PyCmd.Source
} else {
    $PyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PyCmd) { $Python = $PyCmd.Source }
}
if (-not $Python) {
    Write-Error "Python not found in PATH. Install Python 3.11+ and retry."
}

$VenvPythonw = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPythonw)) {
    # Create venv if it doesn't exist
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating virtual environment..."
        & py -m venv (Join-Path $ProjectRoot ".venv")
        & $VenvPython -m pip install --upgrade pip
        & $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
    }
}

$SilentRunScript = Join-Path $ProjectRoot "run_silent.vbs"
$StartupFolder = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupFolder "PC Rotation Manager Pro.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "cscript.exe"
$Shortcut.Arguments = "`"$SilentRunScript`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.WindowStyle = 1
$Shortcut.Description = "PC Rotation Manager Pro — shared PC time referee"
$Shortcut.Save()

# Grant all local users write permission to the shared data directory so that
# non-admin users can write state / config files without errors.
$DataDir = "C:\PCRotationManagerPro"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}
# Grant Modify permission to the Users group — this covers all standard users.
icacls $DataDir /grant "Users:(OI)(CI)M" /q

Write-Host "Startup shortcut created:"
Write-Host "  $ShortcutPath"
Write-Host ""
Write-Host "Data stored in: $DataDir"
Write-Host "Mobile dashboard: http://<YOUR_IP>:6969/ (edit config.json to change IP/port)"
