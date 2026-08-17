Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
BatPath = FSO.BuildPath(ScriptDir, "edit_timers.bat")

WshShell.Run Chr(34) & BatPath & Chr(34), 0, False