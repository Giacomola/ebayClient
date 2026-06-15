#!/bin/bash
# Entfernt den INBOX-Daemon-LaunchAgent wieder (stoppt + löscht die .plist).
LABEL="com.buch-anzeigen.inbox-daemon"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
rm -f "$PLIST"
echo "✅ INBOX-Daemon-LaunchAgent entfernt. (Manueller Start über start-inbox-daemon.command bleibt möglich.)"
