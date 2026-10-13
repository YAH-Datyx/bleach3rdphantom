@echo off
rem Startet den iCloud-Sync-Watcher unsichtbar im Hintergrund.
rem Spiegelt "Bleach3P modded.nds" und den Battery-Save in die iCloud,
rem sobald sie sich aendern (fuer die iPhone-Shortcuts).
start "" pythonw "%~dp0tools\icloud_sync.pyw"
