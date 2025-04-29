# /home/ubuntu/jsbot/main.py (CORRIGIDO - SEM CARREGAR COGS)
import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
import traceback # Importar o módulo traceback
import sys # Para sys.exit em caso de erro crítico
# import asyncio # Não necessário sem Lavalink
# import wavelink # Não necessário sem Lavalink
# from wavelink.ext import spotify # Não necessário sem Lavalink

print("--- Iniciando Bot (Modo Diagnóstico - Sem Cogs) ---")

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
# lava_uri = os.getenv("LAVALINK_URI") # Não necessário
# lava_pass = os.getenv("LAVALINK_PASSWORD") # Não necessário
# spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID") # Não necessário
# spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET") # Não necessário

if not token:
    print("❌ CRÍTICO: Token do bot não encontrado! Verifique seu arquivo .env ou as variáveis de ambiente no Railway.")
    sys.exit(1) # Parar execução se o token não for encontrado

print("-> Variáveis de ambiente carregadas (apenas TOKEN necessário neste modo).")

# Intents recomendadas (mínimas para o bot ficar online)
print("-> Configurando Intents...")
intents = nextcord.Intents.default()
intents.guilds = True # Necessário para on_ready
# intents.message_content = True # Não necessário sem comandos de mensagem
# intents.members = True # Não necessário sem cogs
# intents.voice_states = True # Não necessário sem cogs de voz
print("-> Intents configuradas.")

# Inicializa o bot
print("-> Inicializando o Bot...")

# Usar commands.Bot normal, sem a classe customizada que tentava conectar Lavalink
bot = commands.Bot(command_prefix="!", intents=intents)
print("-> Bot inicializado.")

@bot.event
async def on_ready():
    print(f"\n✅ {bot.user.name} está online e pronto! (Modo Diagnóstico - Sem Cogs)")
    print("-> Sincronização de comandos slash PULADA neste modo.")
    # print("-> Tentando sincronizar comandos slash...")
    # try:
    #     # Sincronizar comandos
    #     synced = await bot.sync_application_commands()
    #     if synced is not None:
    #         print(f"🔄 Comandos slash sincronizados: {len(synced)} comandos")
    #     else:
    #         print("⚠️ A sincronização retornou None. Verifique se há comandos para sincronizar.")
    # except Exception as e:
    #     print(f"❌ Erro CRÍTICO ao sincronizar comandos slash:")
    #     traceback.print_exc()
    # print("-> Sincronização de comandos concluída (ou falhou).")

# Removido o listener on_wavelink_node_ready

# --- CARREGAMENTO DE COGS DESATIVADO --- #
print("\n--- Carregamento de COGs DESATIVADO para Diagnóstico --- ")
# cogs_dir = "./cogs"
# if not os.path.isdir(cogs_dir):
#     print(f"❌ Erro: Diretório de COGs '{cogs_dir}' não encontrado.")
# else:
#     try:
#         all_files = os.listdir(cogs_dir)
#         print(f"-> Arquivos encontrados em '{cogs_dir}': {all_files}")
#         cog_files = [f for f in all_files if f.endswith(".py") and not f.startswith("__")]
#         print(f"-> Arquivos .py a serem carregados: {cog_files}")
#     except Exception as e:
#         print(f"❌ Erro ao listar arquivos em '{cogs_dir}':")
#         traceback.print_exc()
#         cog_files = []
#
#     for filename in cog_files:
#         cog_path = f"cogs.{filename[:-3]}"
#         print(f"--> Tentando carregar: {cog_path}")
#         try:
#             bot.load_extension(cog_path)
#             print(f"✅ COG carregado com sucesso: {filename}")
#         except commands.errors.NoEntryPointError:
#             print(f"⚠️ Aviso: {filename} não possui a função setup() e não pode ser carregado como cog.")
#         except commands.errors.ExtensionAlreadyLoaded:
#             print(f"⚠️ Aviso: {filename} já estava carregado.")
#         except Exception as e:
#             print(f"❌ Erro ao carregar {filename}:")
#             traceback.print_exc()
#
# loaded_extensions = list(bot.extensions.keys())
# print(f"\n-> Extensões carregadas ({len(loaded_extensions)}): {', '.join(loaded_extensions) if loaded_extensions else 'Nenhuma'}")
# print("--- Fim do carregamento de COGs ---\n")
# --- FIM DO CARREGAMENTO DE COGS DESATIVADO ---

# Executa o bot
print("-> Iniciando execução do bot com o token...")
try:
    bot.run(token)
except nextcord.errors.LoginFailure:
    print("❌ CRÍTICO: Falha no login - Token inválido. Verifique seu token.")
except Exception as e:
    print("❌ Erro crítico durante a execução do bot:")
    traceback.print_exc()
finally:
    print("--- Bot encerrado ---")
