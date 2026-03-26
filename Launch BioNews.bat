@echo off
REM Launch BioNews.bat
REM Double-click this file from Windows Explorer to start the app.
REM The browser will open automatically. Keep this window open while using the app.

REM %~dp0 = the folder containing this .bat file, guaranteed correct
REM regardless of shortcuts, taskbar pins, or "Run as Administrator".
cd /d "%~dp0"

echo.
echo  Starting BioNews...
echo  The browser will open automatically in a few seconds.
echo  Keep this window open while using the app.
echo  Close this window (or press Ctrl+C) to stop the server.
echo.

.venv\Scripts\python.exe launch.py

echo.
echo  BioNews has stopped.
pause
