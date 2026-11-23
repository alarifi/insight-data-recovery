@echo off
title Build and Package Insight Data Recovery Studio Pro
chcp 65001 >nul
cd /d "%~dp0"

echo ===============================================================================
echo     Insight Data Recovery Studio Pro - Build and Package Pipeline
echo ===============================================================================
echo.

echo [1/3] Cleaning temporary build folders...
if exist "build" rd /s /q "build"
if not exist "Output" mkdir "Output"
echo Done.
echo.

echo [2/3] Compiling lightweight bundle with PyInstaller...
python -m PyInstaller --noconfirm "InsightRecovery.spec"

if not exist "dist\InsightRecovery\InsightRecovery.exe" (
    echo [ERROR] PyInstaller build failed! Please check errors above.
    pause
    exit /b 1
)

echo.
echo [2/3] Successfully generated dist\InsightRecovery\
echo.

echo [3/3] Running Inno Setup 6 Compiler...
set "INNO_COMPILER=E:\PortableApps\Inno\Inno Setup 6\ISCC.exe"

if not exist "%INNO_COMPILER%" (
    echo [WARNING] Inno Setup compiler not found at: %INNO_COMPILER%
    echo Please compile installer.iss manually using Inno Setup GUI.
    pause
    exit /b 0
)

"%INNO_COMPILER%" "installer.iss"

if exist "Output\Setup_InsightRecovery_Pro_v2.0.0.exe" (
    echo.
    echo ===============================================================================
    echo   SUCCESS! Final Installer Built Successfully:
    echo   %~dp0Output\Setup_InsightRecovery_Pro_v2.0.0.exe
    echo ===============================================================================
) else (
    echo [INFO] Build completed. Please check Output directory.
)

echo.
pause
