@echo off
REM ====================================================================
REM DouyinVoice Pro - Build Script
REM ====================================================================
REM This script packages the application as a single .exe file
REM
REM Requirements:
REM   - Python 3.8+ installed
REM   - PyInstaller installed (pip install pyinstaller)
REM
REM Output:
REM   - dist/DouyinVoicePro.exe (single file, ready to share)
REM ====================================================================

echo.
echo ====================================================================
echo DouyinVoice Pro - Build Script
echo ====================================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo [OK] Python installed:
python --version
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [WARNING] PyInstaller is not installed!
    echo.
    echo Installing PyInstaller...
    pip install pyinstaller>=6.0.0
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo [OK] PyInstaller is ready
echo.

echo [1/4] Checking dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [2/4] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist DouyinVoicePro.spec del /q DouyinVoicePro.spec

echo [3/4] Building executable...
echo       This may take 3-5 minutes...
echo.
pyinstaller build.spec
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [4/4] Copying customer files to dist folder...
echo.

REM Copy customer-friendly files to dist folder
if exist "HUONG_DAN_SU_DUNG.txt" (
    copy "HUONG_DAN_SU_DUNG.txt" "dist\" >nul
    echo [OK] Copied: HUONG_DAN_SU_DUNG.txt
)

if exist "CAI_DAT_FFMPEG.bat" (
    copy "CAI_DAT_FFMPEG.bat" "dist\" >nul
    echo [OK] Copied: CAI_DAT_FFMPEG.bat
)

echo.
echo [5/5] Build complete!
echo.

REM Check if .exe was created
if exist "dist\DouyinVoicePro.exe" (
    echo ====================================================================
    echo SUCCESS!
    echo ====================================================================
    echo.
    echo Output files in dist\ folder:
    echo   - DouyinVoicePro.exe (Main program)
    echo   - HUONG_DAN_SU_DUNG.txt (Vietnamese user guide)
    echo   - CAI_DAT_FFMPEG.bat (FFmpeg auto-installer)
    echo   - README.txt (Quick start guide)
    echo.
    for %%A in ("dist\DouyinVoicePro.exe") do echo .exe file size: %%~zA bytes
    echo.
    echo READY TO DISTRIBUTE!
    echo.
    echo Distribution package includes:
    echo   1. DouyinVoicePro.exe - Main program
    echo   2. CAI_DAT_FFMPEG.bat - FFmpeg installer (run this first)
    echo   3. HUONG_DAN_SU_DUNG.txt - Full user guide in Vietnamese
    echo   4. README.txt - Quick start guide
    echo.
    echo IMPORTANT:
    echo   - Source code (.py files) are NOT visible in the .exe
    echo   - The server/ folder is excluded (stays on your computer only)
    echo   - Customers get a complete package ready to use
    echo   - They just need to run CAI_DAT_FFMPEG.bat first, then DouyinVoicePro.exe
    echo.
    echo ====================================================================
) else (
    echo [ERROR] DouyinVoicePro.exe was not created!
    echo Please check the build log above for errors.
)

echo.
pause
