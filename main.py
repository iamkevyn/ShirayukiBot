# /home/ubuntu/jsbot/main.py (MODIFICADO SEM CARREGAR COGS)
import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
import traceback # Importar o módulo traceback
import sys # Para sys.exit em caso de erro crítico
import asyncio # Para wavelink
import wavelink # Para Lavalink
from wavelink.ext import spotify # Para integração Spotify

print("--- Iniciando Bot ---")

# Se estiver usando Replit ou Railway com webserver opcional:
try:
    from keep_alive import keep_alive
    print("-> Tentando iniciar keep_alive...")
    keep_alive()
    print("-> keep_alive iniciado (se aplicável).")
except ImportError:
    print("-> Módulo 'keep_alive' não encontrado, ignorando...")
except Exception as e:
    print("❌ Erro ao iniciar keep_alive:")
    traceback.print_exc()

# Carregar variáveis de ambiente do .env
print("-> Carregando variáveis de ambiente...")
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
lava_uri = os.getenv("LAVALINK_URI")
lava_pass = os.getenv("LAVALINK_PASSWORD")
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not token:
    print("❌ CRÍTICO: Token do bot não encontrado! Verifique seu arquivo .env ou as variáveis de ambiente no Railway.")
    sys.exit(1) # Parar execução se o token não for encontrado

# Aviso sobre Lavalink e Spotify, mas não impede a inicialização básica
if not lava_uri or not lava_pass:
    print("⚠️ AVISO: Credenciais do Lavalink (LAVALINK_URI, LAVALINK_PASSWORD) não encontradas. A funcionalidade de música não funcionará.")
if not spotify_client_id or not spotify_client_secret:
    print("⚠️ AVISO: Credenciais do Spotify (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET) não encontradas. A busca por links do Spotify pode não funcionar corretamente.")

print("-> Variáveis de ambiente carregadas.")

# Intents recomendadas
print("-> Configurando Intents...")
intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
print("-> Intents configuradas.")

# Inicializa o bot
print("-> Inicializando o Bot...")

class BasicBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removido self.loop.create_task(self.connect_nodes()) para simplificar
        # A conexão Lavalink não é necessária se as cogs não forem carregadas
        print("-> BasicBot inicializado (sem conexão Lavalink automática).")

    # Removida a função connect_nodes()

bot = BasicBot(command_prefix="!", intents=intents)
print("-> Bot inicializado.")

@bot.event
asyn...
