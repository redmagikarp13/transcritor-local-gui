@echo off
echo ============================================
echo   Build do Transcritor Local (Windows)
echo ============================================
echo.

REM Instala as dependencias
echo Instalando dependencias...
pip install -r src\transcritor\core\requirements.txt
pip install -r gui_requirements.txt
pip install pyinstaller
echo.

REM Baixa o FFmpeg se ainda nao existir
if not exist ffmpeg.exe (
    echo Baixando FFmpeg...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile ffmpeg.zip"
    echo Extraindo FFmpeg...
    powershell -Command "Expand-Archive ffmpeg.zip -DestinationPath ffmpeg_tmp"
    for /d %%d in (ffmpeg_tmp\*) do (
        copy "%%d\bin\ffmpeg.exe" ffmpeg.exe
    )
    rmdir /s /q ffmpeg_tmp
    del ffmpeg.zip
    echo FFmpeg baixado com sucesso!
    echo.
) else (
    echo FFmpeg ja existe, pulando download.
    echo.
)

REM Limpa builds anteriores
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Gera o executavel
echo Gerando executavel com PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
    --name "TranscritorLocal" ^
    --hidden-import faster_whisper ^
    --hidden-import ctranslate2 ^
    --hidden-import tokenizers ^
    --hidden-import transcritor.gui.transcribe_runner ^
    --collect-all customtkinter ^
    --collect-all faster_whisper ^
    --collect-all huggingface_hub ^
    --add-data "src\transcritor\core;transcritor\core" ^
    --add-data "src\transcritor\gui;transcritor\gui" ^
    --add-binary "ffmpeg.exe;." ^
    src\transcritor\gui\main.py

echo.
echo ============================================
echo   Build concluido!
echo   Executavel em: dist\TranscritorLocal.exe
echo ============================================
pause
