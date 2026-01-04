@echo off
chcp 65001 >nul
color 0A
title Cài đặt FFmpeg cho DouyinVoice Pro

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║          CÀI ĐẶT FFMPEG CHO DOUYINVOICE PRO                  ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 📦 Đang chuẩn bị cài đặt FFmpeg...
echo.

:: Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  LƯU Ý: Script cần quyền Administrator để thêm PATH
    echo.
    echo 👉 Nhấn phải chuột vào file này và chọn "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo ✅ Đang chạy với quyền Administrator
echo.

:: Create installation directory
set INSTALL_DIR=C:\ffmpeg
echo 📁 Tạo thư mục cài đặt: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Download FFmpeg
echo.
echo 📥 Bước 1/4: Đang tải FFmpeg từ GitHub...
echo    (Dung lượng khoảng 100MB, cần 1-3 phút tùy tốc độ mạng)
echo.

set DOWNLOAD_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip
set DOWNLOAD_FILE=%TEMP%\ffmpeg.zip

:: Use PowerShell to download
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%DOWNLOAD_FILE%'; if ($?) {Write-Host 'Download thanh cong!'} else {Write-Host 'Download that bai!'; exit 1}}"

if %errorLevel% neq 0 (
    echo.
    echo ❌ LỖI: Không tải được FFmpeg!
    echo.
    echo 🔧 Thử cách thủ công:
    echo    1. Mở: https://github.com/BtbN/FFmpeg-Builds/releases
    echo    2. Tải file: ffmpeg-master-latest-win64-gpl.zip
    echo    3. Giải nén vào: C:\ffmpeg
    echo    4. Chạy lại script này
    echo.
    pause
    exit /b 1
)

echo ✅ Tải xong!
echo.

:: Extract FFmpeg
echo 📦 Bước 2/4: Đang giải nén FFmpeg...
echo.

powershell -Command "& {$ProgressPreference = 'SilentlyContinue'; Expand-Archive -Path '%DOWNLOAD_FILE%' -DestinationPath '%TEMP%\ffmpeg_extracted' -Force}"

if %errorLevel% neq 0 (
    echo ❌ LỖI: Không giải nén được!
    pause
    exit /b 1
)

:: Find the extracted folder (it has version in name)
for /d %%i in ("%TEMP%\ffmpeg_extracted\ffmpeg-*") do set EXTRACTED_DIR=%%i

:: Copy files to installation directory
echo 📂 Đang sao chép files...
xcopy "%EXTRACTED_DIR%\bin\*" "%INSTALL_DIR%\bin\" /E /I /Y >nul
xcopy "%EXTRACTED_DIR%\doc\*" "%INSTALL_DIR%\doc\" /E /I /Y >nul
xcopy "%EXTRACTED_DIR%\LICENSE.txt" "%INSTALL_DIR%\" /Y >nul

echo ✅ Sao chép xong!
echo.

:: Add to PATH
echo ⚙️  Bước 3/4: Đang thêm FFmpeg vào PATH...
echo.

:: Get current PATH
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "CURRENT_PATH=%%b"

:: Check if already in PATH
echo %CURRENT_PATH% | findstr /C:"%INSTALL_DIR%\bin" >nul
if %errorLevel% equ 0 (
    echo ℹ️  FFmpeg đã có trong PATH rồi
) else (
    :: Add to PATH
    setx PATH "%CURRENT_PATH%;%INSTALL_DIR%\bin" /M >nul
    if %errorLevel% equ 0 (
        echo ✅ Đã thêm vào PATH!
    ) else (
        echo ⚠️  Không thể thêm vào PATH tự động
        echo    Vui lòng thêm thủ công: %INSTALL_DIR%\bin
    )
)
echo.

:: Clean up
echo 🧹 Bước 4/4: Đang dọn dẹp...
del "%DOWNLOAD_FILE%" >nul 2>&1
rmdir /S /Q "%TEMP%\ffmpeg_extracted" >nul 2>&1
echo ✅ Dọn dẹp xong!
echo.

:: Verify installation
echo 🔍 Kiểm tra cài đặt...
"%INSTALL_DIR%\bin\ffmpeg.exe" -version >nul 2>&1
if %errorLevel% equ 0 (
    echo.
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║              ✅ CÀI ĐẶT THÀNH CÔNG!                          ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo 📍 FFmpeg đã được cài tại: %INSTALL_DIR%
    echo 📍 PATH đã được cập nhật
    echo.
    echo ⚠️  QUAN TRỌNG:
    echo    Khởi động lại máy tính để PATH có hiệu lực!
    echo    Hoặc đóng hết CMD/PowerShell đang mở và mở lại
    echo.
    echo 🎉 Bây giờ bạn có thể chạy DouyinVoice Pro!
    echo.
) else (
    echo.
    echo ❌ LỖI: Cài đặt không thành công!
    echo    Vui lòng thử cài thủ công hoặc liên hệ hỗ trợ
    echo    Zalo: 0366468477
    echo.
)

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo Nhấn phím bất kỳ để đóng cửa sổ này...
pause >nul
