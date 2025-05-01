# /home/ubuntu/jsbot/main.py (VERSÃO SIMPLIFICADA PARA DIAGNÓSTICO)
import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
import sys
import traceback

print("--- [DIAGNÓSTICO] Iniciando main.py simplificado ---")

# Carregar variáveis de ambiente do .env
print("--- [DIAGNÓSTICO] Carregando variáveis de ambiente...")
try:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    print("--- [DIAGNÓSTICO] Variáveis de ambiente carregadas.")
except Exception as e:
    print("❌ [DIAGNÓSTICO] Erro ao carregar .env:")
    traceback.print_exc()
    token = None

if not token:
    print("❌ [DIAGNÓSTICO] CRÍTICO: Token do bot não encontrado! Verifique .env ou variáveis no Railway.")
    sys.exit(1)
else:
    print("--- [DIAGNÓSTICO] Token encontrado.")

# Intents mínimas
print("--- [DIAGNÓSTICO] Configurando Intents...")
intents = nextcord.Intents.default()
intents.message_content = True # Apenas para exemplo, pode não ser necessário
print("--- [DIAGNÓSTICO] Intents configuradas.")

# Inicializa o bot
print("--- [DIAGNÓSTICO] Inicializando o Bot...")
try:
    bot = commands.Bot(command_prefix="!", intents=intents)
    print("--- [DIAGNÓSTICO] Bot instanciado.")
except Exception as e:
    print("❌ [DIAGNÓSTICO] Erro ao instanciar o Bot:")
    traceback.print_exc()
    sys.exit(1)

@bot.event
async def on_ready():
    print(f"\n✅ --- [DIAGNÓSTICO] {bot.user.name} está online! --- ✅")
    # Sem sincronização de comandos ou carregamento de cogs por enquanto

# Executa o bot
print("--- [DIAGNÓSTICO] Iniciando execução do bot com o token...")
try:
    bot.run(token)
except nextcord.errors.LoginFailure:
    print("❌ [DIAGNÓSTICO] CRÍTICO: Falha no login - Token inválido.")
except Exception as e:
    print("❌ [DIAGNÓSTICO] Erro crítico durante a execução do bot:")
    traceback.print_exc()
finally:
    print("--- [DIAGNÓSTICO] Processo do bot encerrado. ---")
