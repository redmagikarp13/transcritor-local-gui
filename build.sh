#!/bin/bash
# Script para gerar o executável com PyInstaller

echo "============================================"
echo "  Build do Transcritor Local"
echo "============================================"
echo

# Instala as dependências
echo "Instalando dependências..."
pip install -r src/transcritor/core/requirements.txt
pip install -r gui_requirements.txt
pip install pyinstaller
echo

# Detecta o sistema operacional
OS="$(uname -s)"
if [[ "$OS" == "Darwin" ]]; then
    FFMPEG_BIN="ffmpeg"
else
    FFMPEG_BIN="ffmpeg"
fi

# Baixa o FFmpeg se ainda não existir
if [ ! -f "$FFMPEG_BIN" ]; then
    echo "Baixando FFmpeg..."
    if [[ "$OS" == "Darwin" ]]; then
        # macOS - usa Homebrew
        if ! command -v brew &> /dev/null; then
            echo "Erro: Homebrew não encontrado. Instale em: https://brew.sh"
            exit 1
        fi
        brew install ffmpeg
        cp $(which ffmpeg) ffmpeg
    else
        # Linux - baixa binário estático
        curl -L https://johnvansickle.com/builds/ffmpeg-release-amd64-build.tar.xz -o ffmpeg.tar.xz
        tar -xf ffmpeg.tar.xz
        cp ffmpeg-*-amd64/ffmpeg ffmpeg
        rm -rf ffmpeg.tar.xz ffmpeg-*-amd64
    fi
    echo "FFmpeg baixado com sucesso!"
    echo
else
    echo "FFmpeg já existe, pulando download."
    echo
fi

# Limpa builds anteriores
rm -rf build/ dist/

# Gera o executável
echo "Gerando executável com PyInstaller..."
pyinstaller --noconfirm --onefile --windowed \
    --name "TranscritorLocal" \
    --hidden-import faster_whisper \
    --hidden-import ctranslate2 \
    --hidden-import tokenizers \
    --hidden-import transcritor.gui.transcribe_runner \
    --collect-all customtkinter \
    --collect-all faster_whisper \
    --collect-all huggingface_hub \
    --add-data "src/transcritor/core:transcritor/core" \
    --add-data "src/transcritor/gui:transcritor/gui" \
    --add-binary "ffmpeg:." \
    src/transcritor/gui/main.py

echo
echo "============================================"
echo "  Build concluído!"
echo "  Executável em: dist/TranscritorLocal"
echo "============================================"
