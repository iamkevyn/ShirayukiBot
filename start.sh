#!/bin/bash

set -e  # Faz o script parar ao primeiro erro

pip install --upgrade pip setuptools
pip install -r requirements.txt

python main.py
