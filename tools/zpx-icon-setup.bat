@echo off
REM ZPX File Icon Association Setup
REM Run this script to register .zpx files with the ZPX icon in Windows Explorer

setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "ICON_PATH=%SCRIPT_DIR%zpx.ico"

REM Register the .zpx extension
reg add "HKCU\Software\Classes\.zpx" /ve /t REG_SZ /d "zpx-file" /f >nul
reg add "HKCU\Software\Classes\.zpx\DefaultIcon" /ve /t REG_SZ /d "%ICON_PATH%" /f >nul

REM Create file type and associate icon
reg add "HKCU\Software\Classes\zpx-file" /ve /t REG_SZ /d "Zpx Source File" /f >nul
reg add "HKCU\Software\Classes\zpx-file\DefaultIcon" /ve /t REG_SZ /d "%ICON_PATH%" /f >nul

REM Clear icon cache and restart Explorer
del /f /q "%LOCALAPPDATA%\IconCache.db" >nul 2>&1
del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache*" >nul 2>&1
taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

echo.
echo ========================================
echo   ZPX File Association Set Up!
echo ========================================
echo   .zpx files will now show the ZPX icon.
echo   (You may need to log off/on to see the
echo    change if icon cache doesn't refresh.)
echo.
pause
