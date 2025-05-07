# Use uma imagem base oficial do Python. 
# python:3.12-slim é uma boa escolha por ser menor e compatível com Nextcord 3.x.
FROM python:3.12-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala as dependências de sistema necessárias para PyNaCl, ffmpeg, opus e git
# Atualiza a lista de pacotes, instala os pacotes e depois limpa o cache do apt
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ffmpeg \
        libopus-dev \
        libsodium-dev \
        # Adicione quaisquer outras dependências de sistema aqui, se necessário
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências Python para o diretório de trabalho
COPY requirements.txt .

# Instala as dependências Python
# --no-cache-dir economiza espaço na imagem
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação para o diretório de trabalho
COPY . .

# Define o comando padrão para executar a aplicação quando o contêiner iniciar
CMD ["python", "main.py"]
