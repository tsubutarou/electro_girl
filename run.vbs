Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

base = FSO.GetParentFolderName(WScript.ScriptFullName)
logPath = base & "\run.log"

cmd = "cmd /c """ & base & "\.venv\Scripts\pythonw.exe main.py >> """ & logPath & """ 2>&1"""

WshShell.CurrentDirectory = base
WshShell.Run cmd, 0