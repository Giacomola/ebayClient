' Startet den Buch-Anzeigen-Helfer OHNE sichtbares Terminalfenster.
' Hierher zeigt die Desktop-Verknuepfung mit dem Logo.
Option Explicit
Dim sh, fso, projektordner, pyw
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Ordner, in dem diese Datei liegt (= Projektordner).
projektordner = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = projektordner
pyw = projektordner & "\.venv\Scripts\pythonw.exe"

If fso.FileExists(pyw) Then
    ' Umgebung ist eingerichtet -> leise im Hintergrund starten.
    ' 0 = kein Fenster, pythonw.exe hat ohnehin keine Konsole.
    ' app.py oeffnet den Browser selbst auf http://127.0.0.1:5050.
    sh.Run """" & pyw & """ app.py", 0, False
Else
    ' Noch nicht eingerichtet -> den sichtbaren Einrichter (Start.bat) starten,
    ' damit man den Fortschritt der einmaligen Erstinstallation sieht.
    sh.Run """" & projektordner & "\Start.bat""", 1, False
End If
