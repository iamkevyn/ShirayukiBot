import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

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
        print(f"🔄 Comandos slash sincronizados: {len(synced)} comandos")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos slash: {e}")

# Carrega os COGs da pasta 'cogs'
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        cog_path = f"cogs.{filename[:-3]}"
        try:
            bot.load_extension(cog_path)
            print(f"✅ COG carregado: {filename}")
        except Exception as e:
            print(f"❌ Erro ao carregar {filename}: {e}")

# Executa o bot
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token do bot não encontrado! Verifique seu arquivo .env.")
