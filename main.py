import os
import nextcord
from nextcord.ext import commands
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()
keep_alive()

# Carrega o Opus se necessário
if not nextcord.opus.is_loaded():
    try:
        nextcord.opus.load_opus('libopus.so')  # No Replit, talvez precise mudar pra "opus"
    except Exception as e:
        print(f"Erro ao carregar Opus: {e}")

intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user.name} está online!")

# Carrega todos os COGs da pasta cogs
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        try:
            bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"✅ COG carregado: {filename}")
        except Exception as e:
            print(f"❌ Erro ao carregar {filename}: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
