@echo off
echo ============================================
echo  FF4 TAY - Chinese Patch v1.0.1
echo ============================================
echo.

echo [1/1] Installing Chinese game files...
xcopy /E /Y "Resources\en.lproj\*" "..\Resources\en.lproj\" >nul 2>nul
echo   121 files installed.

echo.
echo Selecting Chinese font...
set FONT_FOUND=0

if exist "%SystemRoot%\Fonts\simhei.ttf" (
    copy /Y "%SystemRoot%\Fonts\simhei.ttf" "..\arial.ttf" >nul 2>nul
    echo   SimHei ^(simhei.ttf^)
    set FONT_FOUND=1
)

if %FONT_FOUND%==0 (
    echo   No Chinese font found on system.
    echo   Install SimHei from Windows Settings.
    echo   Open-source CJK fonts are known to crash this game.
    echo   See README.md for details.
)

echo.
echo ============================================
echo  Installation complete!
if %FONT_FOUND%==1 echo  Font installed: see above.
if %FONT_FOUND%==0 echo  Font was NOT installed.
echo.
echo  Run FF4A.exe to play.
echo  Uninstall: Steam verify game files.
echo ============================================
pause
