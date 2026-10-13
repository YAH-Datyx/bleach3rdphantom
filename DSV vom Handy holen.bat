@echo off
rem Holt den auf dem Handy gespeicherten DeSmuME-Spielstand (.dsv) aus der
rem iCloud in den PC-Battery-Ordner. Vorher das iPhone-Shortcut laufen lassen,
rem das die .dsv vom Handy in "iCloudDrive\Modded DSV files" legt.
rem TIPP: Diese .bat kannst du an eine Windows-Verknuepfung haengen und ihr im
rem Verknuepfungs-Dialog eine TASTENKOMBINATION (Eigenschaften -> Tastenkombi)
rem zuweisen -> dann per Tastendruck.
python "%~dp0tools\icloud_pull.py"
echo.
pause
