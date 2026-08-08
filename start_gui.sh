#!/bin/bash

# Ativa o ambiente virtual e inicia a interface gráfica
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python gui/main.py
