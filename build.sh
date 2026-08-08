#!/bin/bash
# Script para gerar o .app para macOS com PyInstaller

echo "Iniciando build do Transcritor Local GUI..."

# Instala as dependências de GUI (inclui pyinstaller)
pip install -r tools/requirements.txt
pip install -r gui_requirements.txt
pip install pyinstaller

# Limpa builds anteriores
rm -rf build/ dist/

# Gera o executável
# Usamos --windowed para não abrir o terminal no fundo (macOS .app)
# Incluímos a pasta tools/ para que o script runner a encontre
pyinstaller --noconfirm --log-level=WARN \
    --name "TranscritorLocal" \
    --windowed \
    --add-data "tools:tools" \
    --add-data "gui:gui" \
    gui/main.py

echo "Build concluído! Verifique a pasta 'dist/TranscritorLocal.app'."
