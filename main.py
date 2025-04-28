# /home/ubuntu/jsbot/main.py
import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
import traceback  # Importar o módulo traceback

# Se estiver usando Replit ou Railway com webserver opcional:
try:
    from keep_alive import keep_alive
    keep_alive()
except ImportError:
    print("🔁 Módulo 'keep_alive' não encontrado, ignorando...")

# Carregar variáveis de ambiente do .env
load_dotenv()

# Intents recomendadas
intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

# Inicializa o bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} está online!")
    try:
        synced = await bot.sync_application_commands()
        print(f"🔄 Comandos slash sincronizados: {len(synced) if synced else 0} comandos") # Adicionado verificação se synced é None
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos slash:")
        traceback.print_exc() # Imprimir traceback completo do erro de sincronização

# Carrega os COGs da pasta 'cogs'
print("\n--- Carregando COGs ---")
cogs_dir = "./cogs"
if not os.path.isdir(cogs_dir):
    print(f"❌ Erro: Diretório de COGs '{cogs_dir}' não encontrado.")
else:
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            cog_path = f"cogs.{filename[:-3]}"
            try:
                bot.load_extension(cog_path)
                print(f"✅ COG carregado: {filename}")
            except commands.errors.NoEntryPointError:
                 print(f"⚠️  Aviso: {filename} não possui a função setup() e não pode ser carregado como cog.")
            except Exception as e:
                print(f"❌ Erro ao carregar {filename}:")
                traceback.print_exc() # Imprimir traceback completo do erro
print("--- Fim do carregamento de COGs ---\n")

# Executa o bot
token = os.getenv("DISCORD_TOKEN")
if token:
    try:
        bot.run(token)
    except Exception as e:
        print("❌ Erro crítico ao executar o bot:")
        traceback.print_exc()
else:
    print("❌ Token do bot não encontrado! Verifique seu arquivo .env ou as variáveis de ambiente no Railway.")
