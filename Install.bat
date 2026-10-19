@echo off
setlocal
echo ============================================
echo  FF4 TAY - Chinese Patch v1.0.3
echo ============================================
echo.

set "GAME_DIR=%~dp0.."
if exist "%~dp0FF4A.exe" set "GAME_DIR=%~dp0."
for %%I in ("%GAME_DIR%") do set "GAME_DIR=%%~fI"
if not exist "%GAME_DIR%\FF4A.exe" (
    echo ERROR: FF4A.exe not found in the game directory.
    goto :failed
)
"%SystemRoot%\System32\tasklist.exe" /FI "IMAGENAME eq FF4A.exe" /NH | "%SystemRoot%\System32\find.exe" /I "FF4A.exe" >nul
if not errorlevel 1 (
    echo ERROR: Close FF4A.exe before installing.
    goto :failed
)
if not exist "%SystemRoot%\Fonts\simhei.ttf" (
    echo ERROR: SimHei ^(simhei.ttf^) is required. Install it first.
    goto :failed
)
if not exist "%~dp0Resources\en.lproj\menu.msd" (
    echo ERROR: Chinese resource files are missing.
    goto :failed
)
if not exist "%~dp0menu.txt" (
    echo ERROR: Chinese menu.txt is missing.
    goto :failed
)

echo Installing Chinese game files...
if /I not "%~dp0"=="%GAME_DIR%\" (
    xcopy /E /I /Y "%~dp0Resources\en.lproj\*" "%GAME_DIR%\Resources\en.lproj\" >nul
    if errorlevel 1 goto :failed
    copy /Y "%~dp0menu.txt" "%GAME_DIR%\menu.txt" >nul
    if errorlevel 1 goto :failed
)

echo Installing SimHei for old and updated game builds...
call :install_font arial.ttf
if errorlevel 1 goto :failed
call :install_font Arimo.ttf
if errorlevel 1 goto :failed

echo.
echo Installation complete! Run FF4A.exe to play.
echo Uninstall: Steam verify game files.
if not defined FF4TAY_PATCH_NO_PAUSE pause
exit /b 0

:install_font
if exist "%GAME_DIR%\%~1" if not exist "%GAME_DIR%\%~1.chinese-patch.bak" (
    copy /Y "%GAME_DIR%\%~1" "%GAME_DIR%\%~1.chinese-patch.bak" >nul
    if errorlevel 1 exit /b 1
)
copy /Y "%SystemRoot%\Fonts\simhei.ttf" "%GAME_DIR%\%~1" >nul
exit /b %errorlevel%

:failed
echo Installation failed. Check the error above.
if not defined FF4TAY_PATCH_NO_PAUSE pause
exit /b 1
