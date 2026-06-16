' Run PC Rotation Manager Pro without console window
' To use: Right-click this file and select "Open" or create a shortcut to it

Set oShell = CreateObject("WScript.Shell")
strScriptPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
oShell.Run chr(34) & strScriptPath & "\run.bat" & chr(34), 0, False
