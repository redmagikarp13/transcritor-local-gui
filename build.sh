#!/bin/bash
# Script para gerar o executável com PyInstaller

echo "Iniciando build do Transcritor Local GUI..."

# Instala as dependências
pip install -r src/transcritor/core/requirements.txt
pip install -r gui_requirements.txt
pip install pyinstaller

# Limpa builds anteriores
rm -rf build/ dist/

# Gera o executável
pyinstaller --noconfirm --log-level=WARN \
    --name "TranscritorLocal" \
    --windowed \
    --hidden-import faster_whisper \
    --hidden-import ctranslate2 \
    --hidden-import tokenizers \
    --collect-data faster_whisper \
    --add-data "src/transcritor/core:transcritor/core" \
    --add-data "src/transcritor/gui:transcritor/gui" \
    src/transcritor/gui/main.py

echo "Build concluído! Verifique a pasta 'dist/'."
