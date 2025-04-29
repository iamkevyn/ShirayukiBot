# /home/ubuntu/jsbot/main.py (MODIFICADO - IGNORA COGS COM ERRO)
import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
import traceback # Importar o módulo traceback
import sys # Para sys.exit em caso de erro crítico
import asyncio # Para wavelink
import wavelink # Para Lavalink
from wavelink.ext import spotify # Para integração Spotify

print("--- Iniciando Bot (Modo Tolerante a Falhas) ---")

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

class MusicBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só tenta conectar ao Lavalink se as credenciais existirem
        if lava_uri and lava_pass:
            self.loop.create_task(self.connect_nodes())
        else:
            print("-> Conexão com Lavalink pulada (credenciais ausentes).")

    async def connect_nodes(self):
        """Conecta aos nós Lavalink."""
        await self.wait_until_ready() # Espera o bot estar pronto
        if not lava_uri or not lava_pass:
            print("❌ Erro: Credenciais do Lavalink não configuradas. Não é possível conectar ao nó.")
            return

        print("-> Tentando conectar ao nó Lavalink...")
        # Configurar cliente Spotify para wavelink se as credenciais estiverem disponíveis
        spotify_client = None
        if spotify_client_id and spotify_client_secret:
            spotify_client = spotify.SpotifyClient(
                client_id=spotify_client_id,
                client_secret=spotify_client_secret
            )
            print("-> Cliente Spotify para Wavelink configurado.")
        else:
            print("-> Cliente Spotify para Wavelink não configurado (credenciais ausentes).")

        try:
            node: wavelink.Node = wavelink.Node(
                uri=lava_uri,
                password=lava_pass,
                spotify_client=spotify_client
            )
            await wavelink.NodePool.connect(client=self, nodes=[node])
            print(f"✅ Conectado ao nó Lavalink em {lava_uri}")
        except Exception as e:
            print(f"❌ Erro ao conectar ao nó Lavalink:")
            traceback.print_exc()
            print("⚠️ O bot continuará funcionando, mas sem recursos de música.")

bot = MusicBot(command_prefix="!", intents=intents)
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
        else:
            print("⚠️ A sincronização retornou None. Verifique se há comandos para sincronizar.")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos slash:")
        traceback.print_exc()
        print("⚠️ O bot continuará funcionando, mas os comandos slash podem não estar disponíveis.")
    print("-> Sincronização de comandos concluída (ou falhou).")

# Evento Wavelink para status do nó
@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f"✅ Nó Lavalink '{node.identifier}' está pronto!")

# Carrega os COGs da pasta 'cogs' com tratamento de erros aprimorado
print("\n--- Carregando COGs (Modo Tolerante a Falhas) ---")
cogs_dir = "./cogs"
if not os.path.isdir(cogs_dir):
    print(f"❌ Erro: Diretório de COGs '{cogs_dir}' não encontrado.")
else:
    try:
        all_files = os.listdir(cogs_dir)
        print(f"-> Arquivos encontrados em '{cogs_dir}': {all_files}")
        cog_files = [f for f in all_files if f.endswith(".py") and not f.startswith("__")]
        print(f"-> Arquivos .py a serem carregados: {cog_files}")
    except Exception as e:
        print(f"❌ Erro ao listar arquivos em '{cogs_dir}':")
        traceback.print_exc()
        cog_files = []

    # Listas para acompanhar o status do carregamento
    cogs_loaded = []
    cogs_failed = []

    for filename in cog_files:
        cog_path = f"cogs.{filename[:-3]}"
        print(f"--> Tentando carregar: {cog_path}")
        try:
            bot.load_extension(cog_path)
            print(f"✅ COG carregado com sucesso: {filename}")
            cogs_loaded.append(filename)
        except commands.errors.NoEntryPointError:
            print(f"⚠️ Aviso: {filename} não possui a função setup() e não pode ser carregado como cog.")
            cogs_failed.append(f"{filename} (sem setup)")
        except commands.errors.ExtensionAlreadyLoaded:
            print(f"⚠️ Aviso: {filename} já estava carregado.")
            cogs_loaded.append(filename)  # Consideramos como carregado
        except Exception as e:
            print(f"❌ Erro ao carregar {filename}:")
            traceback.print_exc()
            cogs_failed.append(f"{filename} ({type(e).__name__})")
            print(f"⚠️ Ignorando erro e continuando com os próximos cogs...")

    # Resumo do carregamento
    loaded_extensions = list(bot.extensions.keys())
    print(f"\n=== RESUMO DO CARREGAMENTO DE COGS ===")
    print(f"-> Total de cogs encontrados: {len(cog_files)}")
    print(f"-> Cogs carregados com sucesso ({len(cogs_loaded)}): {', '.join(cogs_loaded) if cogs_loaded else 'Nenhum'}")
    print(f"-> Cogs que falharam ({len(cogs_failed)}): {', '.join(cogs_failed) if cogs_failed else 'Nenhum'}")
    print(f"-> Extensões ativas ({len(loaded_extensions)}): {', '.join(loaded_extensions) if loaded_extensions else 'Nenhuma'}")
    print("=== FIM DO RESUMO ===\n")

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
