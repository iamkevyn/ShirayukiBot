import nextcord
import os
from nextcord.ext import commands
from dotenv import load_dotenv

print("--- Iniciando Bot Simplificado ---")
load_dotenv()
token = os.getenv("DISCORD_TOKEN") # Ou coloque o token direto: token = "SEU_TOKEN_AQUI"

if not token:
    print("Token não encontrado!")
    exit()

intents = nextcord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"\n✅ {bot.user.name} (SIMPLIFICADO) está online!")
    print("-> Tentando sincronizar comandos slash...")
    try:
        synced = await bot.sync_application_commands()
        print(f"Comandos sincronizados: {len(synced) if synced else 0}")
    except Exception as e:
        print(f"Erro ao sincronizar: {e}")

@nextcord.slash_command(name="ping", description="Testa se o bot está respondendo.")
async def ping(interaction: nextcord.Interaction):
    print("--- Comando /ping recebido ---")
    await interaction.response.send_message("Pong!", ephemeral=True)
    print("--- Resposta Pong enviada ---")

print("-> Iniciando execução do bot...")
try:
    bot.run(token)
except Exception as e:
    print(f"Erro crítico: {e}")
finally:
    print("--- Bot Simplificado Encerrado ---")
