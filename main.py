# /home/ubuntu/jsbot/main.py
import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
import traceback  # Importar o módulo traceback
import sys # Para sys.exit em caso de erro crítico

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
if not token:
    print("❌ CRÍTICO: Token do bot não encontrado! Verifique seu arquivo .env ou as variáveis de ambiente no Railway.")
    sys.exit(1) # Parar execução se o token não for encontrado
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
bot = commands.Bot(command_prefix="!", intents=intents)
print("-> Bot inicializado.")

@bot.event
async def on_ready():
    print(f"\n✅ {bot.user.name} está online e pronto!")
    print("-> Tentando sincronizar comandos slash...")
    try:
        # Sincronizar comandos
        synced = await bot.sync_application_commands()
        if synced is not None:
            print(f"🔄 Comandos slash sincronizados: {len(synced)} comandos")
            # Opcional: Listar comandos sincronizados
            # for cmd in synced:
            #     print(f"    - {cmd.name} (ID: {cmd.id})")
        else:
            print("⚠️  A sincronização retornou None. Verifique se há comandos para sincronizar.")
    except Exception as e:
        print(f"❌ Erro CRÍTICO ao sincronizar comandos slash:")
        traceback.print_exc() # Imprimir traceback completo do erro de sincronização
    print("-> Sincronização de comandos concluída (ou falhou).")

# Carrega os COGs da pasta 'cogs'
print("\n--- Carregando COGs ---")
cogs_dir = "./cogs"
if not os.path.isdir(cogs_dir):
    print(f"❌ Erro: Diretório de COGs '{cogs_dir}' não encontrado.")
else:
    cog_files = [f for f in os.listdir(cogs_dir) if f.endswith(".py") and not f.startswith("__")]
    print(f"-> Encontrados {len(cog_files)} arquivos .py em '{cogs_dir}'")
    for filename in cog_files:
        cog_path = f"cogs.{filename[:-3]}"
        print(f"--> Tentando carregar: {cog_path}")
        try:
            bot.load_extension(cog_path)
            print(f"✅ COG carregado com sucesso: {filename}")
        except commands.errors.NoEntryPointError:
             print(f"⚠️  Aviso: {filename} não possui a função setup() e não pode ser carregado como cog.")
        except commands.errors.ExtensionAlreadyLoaded:
            print(f"⚠️  Aviso: {filename} já estava carregado.")
        except Exception as e:
            print(f"❌ Erro ao carregar {filename}:")
            traceback.print_exc() # Imprimir traceback completo do erro

# Verificar extensões carregadas
loaded_extensions = list(bot.extensions.keys())
print(f"\n-> Extensões carregadas ({len(loaded_extensions)}): {', '.join(loaded_extensions) if loaded_extensions else 'Nenhuma'}")
print("--- Fim do carregamento de COGs ---\n")

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
