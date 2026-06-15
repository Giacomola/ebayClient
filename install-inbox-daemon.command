#!/bin/bash
# Installiert den INBOX-Daemon als macOS-LaunchAgent: startet automatisch beim
# Login und wird von launchd am Leben gehalten (KeepAlive). Doppelklickbar.
#
# Wichtig: launchd startet mit minimalem PATH. Damit der Daemon `claude`, `git`
# und `osascript` findet, setzt die .plist einen expliziten PATH.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
PY="$REPO/.venv/bin/python"
DAEMON="$REPO/tools/inbox_daemon.py"
LABEL="com.buch-anzeigen.inbox-daemon"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ ! -x "$PY" ]; then
  echo "FEHLER: $PY nicht gefunden. Erst die App einmal über Start.command starten (legt .venv an)."
  exit 1
fi

# watchdog sicherstellen (der Daemon braucht es)
"$PY" -c "import watchdog" 2>/dev/null || "$PY" -m pip install watchdog

mkdir -p "$HOME/Library/LaunchAgents" "$REPO/logs"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$DAEMON</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$REPO/logs/inbox_daemon.out.log</string>
  <key>StandardErrorPath</key>
  <string>$REPO/logs/inbox_daemon.err.log</string>
</dict>
</plist>
PLIST

# Neu laden (falls schon installiert: erst raus, dann rein)
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl kickstart -k "gui/$UID/$LABEL"

echo "✅ INBOX-Daemon installiert und gestartet ($LABEL)."
echo "   Er läuft ab jetzt automatisch nach jedem Login."
echo "   Logs: $REPO/logs/inbox_daemon.log (und .out/.err.log)"
echo "   Deinstallieren: uninstall-inbox-daemon.command doppelklicken."
