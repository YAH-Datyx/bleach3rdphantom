@echo off
cd /d "%~dp0"
python stat_editor.py
if errorlevel 1 pause
