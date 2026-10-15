@echo off
rem Run DeepNoise from source (dev). First time: see README "Build from source".
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app.py" %*
