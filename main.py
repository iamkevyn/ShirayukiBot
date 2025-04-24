import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

# Se estiver usando Replit ou similar:
try:
    from keep_alive import keep_alive
    keep_alive()
except ImportError:
    print("🔁 Módulo 'keep_alive' não encontrado, ignorando...")

# Carregar variáveis de ambiente
load_dotenv()

# Intents necessários
intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

# Usar InteractionBot para suportar comandos slash
bot = nextcord.InteractionBot(intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} está online!")

    try:
        synced = await bot.sync_all_application_commands()
        print(f"🔄 Comandos slash sincronizados: {len(synced)} comandos")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos slash: {e}")

# Carregamento dinâmico dos COGs
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        cog_path = f"cogs.{filename[:-3]}"
        try:
            bot.load_extension(cog_path)
            print(f"✅ COG carregado: {filename}")
        except Exception as e:
            print(f"❌ Erro ao carregar {filename}: {e}")

# Inicia o bot com o token da variável de ambiente
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Token do bot não encontrado! Verifique seu arquivo .env.")
