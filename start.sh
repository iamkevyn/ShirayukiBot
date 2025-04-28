#!/bin/bash

set -e  # Faz o script parar ao primeiro erro

# Instalar Poetry (geralmente já disponível no Railway, mas garante)
pip install --upgrade pip poetry

# Instalar dependências usando Poetry (sem instalar o próprio projeto como pacote e sem dependências de desenvolvimento)
poetry install --no-root --no-dev

# Executar o bot usando Poetry para garantir que ele use o ambiente virtual correto
poetry run python main.py
