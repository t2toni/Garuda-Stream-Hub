@echo off
REM ==============================================================================
REM Garuda Stream Hub - Windows Executable (.exe) Builder
REM Run this script on Windows (x64) with Python 3.10+ installed
REM ==============================================================================

echo === [1/3] Installing Windows Dependencies ===
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo === [2/3] Building Standalone Windows Executable via PyInstaller ===
set QT_API=pyqt6
pyinstaller --clean -y garuda_stream_hub.spec

echo === [3/3] Creating Windows Distribution Archive ===
if not exist "dist\release" mkdir dist\release
copy "dist\garuda-stream-hub.exe" "dist\release\GarudaStreamHub-windows-x64.exe"
copy "README.md" "dist\release\"
xcopy /E /I "assets" "dist\release\assets"

powershell -Command "Compress-Archive -Path dist\release\* -DestinationPath dist\GarudaStreamHub-windows-x64.zip -Force"

echo ==============================================================================
echo [SUCCESS] Windows packaging complete!
echo Executable: dist\garuda-stream-hub.exe
echo ZIP Bundle:  dist\GarudaStreamHub-windows-x64.zip
echo ==============================================================================
pause
