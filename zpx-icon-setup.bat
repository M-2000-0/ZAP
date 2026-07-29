@echo off
REM ZPX File Icon Association Setup
REM Run as Administrator for system-wide, or as user for current user only

set ICON_PATH=%~dp0zpx.ico

REM Register the .zpx extension
reg add "HKCU\Software\Classes\.zpx" /ve /t REG_SZ /d "zpx-file" /f
reg add "HKCU\Software\Classes\.zpx\DefaultIcon" /ve /t REG_SZ /d "%ICON_PATH%" /f

REM Create file type
reg add "HKCU\Software\Classes\zpx-file" /ve /t REG_SZ /d "Zpx Source File" /f
reg add "HKCU\Software\Classes\zpx-file\DefaultIcon" /ve /t REG_SZ /d "%ICON_PATH%" /f

REM Refresh Windows Explorer
ie4uinit.exe -show
taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

echo.
echo ZPX file association set up!
echo .zpx files will now show the ZPX icon.
pause
