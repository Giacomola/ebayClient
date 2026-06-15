# Legt eine Desktop-Verknuepfung "Buch-Anzeigen-Helfer" mit Logo an.
# Die Verknuepfung startet das Programm OHNE Terminalfenster (ueber Start-leise.vbs).
$dir = $PSScriptRoot
$ws = New-Object -ComObject WScript.Shell
$desktop = $ws.SpecialFolders('Desktop')
$lnk = Join-Path $desktop 'Buch-Anzeigen-Helfer.lnk'

$s = $ws.CreateShortcut($lnk)
$s.TargetPath = 'wscript.exe'
$s.Arguments = '"' + (Join-Path $dir 'Start-leise.vbs') + '"'
$s.WorkingDirectory = $dir
$s.IconLocation = (Join-Path $dir 'app.ico')
$s.Description = 'Buch-Anzeigen-Helfer starten (ohne Terminal)'
$s.Save()

Write-Host ''
Write-Host 'Fertig: Die Verknuepfung "Buch-Anzeigen-Helfer" liegt jetzt auf dem Desktop.'
Write-Host 'Doppelklick darauf startet das Programm ohne schwarzes Fenster.'
