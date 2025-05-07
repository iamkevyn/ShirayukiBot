# Use uma imagem base oficial do Python. 
# python:3.12-slim é uma boa escolha por ser menor e compatível com Nextcord 3.x.
FROM python:3.12-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala as dependências de sistema necessárias
# build-essential, python3-dev, pkg-config e cargo são para compilar pacotes Python que não têm wheels para ARM ou certas versões de Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ffmpeg \
        libopus-dev \
        libsodium-dev \
        build-essential \
        python3-dev \
        pkg-config \
        cargo \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências Python para o diretório de trabalho
# Primeiro o pyproject.toml e poetry.lock para aproveitar o cache do Docker se não mudarem
COPY pyproject.toml poetry.lock* .

# Instala o Poetry
RUN pip install poetry

# Configura o Poetry para não criar virtualenvs dentro do projeto, o que é melhor para Docker
RUN poetry config virtualenvs.create false

# Instala as dependências do projeto usando Poetry
# --no-root para não instalar o projeto em si como editável, apenas as dependências
# --no-interaction para não pedir inputs
RUN poetry install --no-root --no-interaction --no-ansi

# Copia o restante do código da aplicação para o diretório de trabalho
COPY . .

# Define o comando padrão para executar a aplicação quando o contêiner iniciar
# Usando poetry run para garantir que executa no ambiente correto
CMD ["poetry", "run", "python", "main.py"]
