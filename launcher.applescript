-- Startet den Buch-Anzeigen-Helfer unsichtbar im Hintergrund (ohne Terminal)
-- und öffnet den Browser. Beim ersten Mal wird alles eingerichtet.
on run
	-- Ordner finden, in dem diese App liegt (= Projektordner).
	set appPosix to POSIX path of (path to me)
	set appDir to do shell script "cd " & quoted form of appPosix & "/.. && pwd"

	-- Erste Einrichtung, falls die Umgebung noch fehlt.
	try
		do shell script "test -d " & quoted form of (appDir & "/.venv")
	on error
		display dialog "Erste Einrichtung des Buch-Anzeigen-Helfers. Das dauert einmalig ein bis zwei Minuten." buttons {"OK"} default button "OK" with icon note
		do shell script "cd " & quoted form of appDir & " && python3 -m venv .venv && ./.venv/bin/pip install --quiet --upgrade pip && ./.venv/bin/pip install --quiet -r requirements.txt"
	end try

	-- Läuft der Server schon? Dann nur den Browser öffnen.
	set isRunning to true
	try
		do shell script "curl -s -o /dev/null --max-time 2 http://127.0.0.1:5050"
	on error
		set isRunning to false
	end try

	if isRunning is false then
		do shell script "cd " & quoted form of appDir & " && nohup ./.venv/bin/python app.py > /tmp/buchhelfer.log 2>&1 &"
		delay 2
	end if

	do shell script "open http://127.0.0.1:5050"
end run
