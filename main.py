# /home/ubuntu/jsbot/main.py (MODIFICADO COM setup_hook)
import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
import traceback # Importar o módulo traceback
import sys # Para sys.exit em caso de erro crítico
import asyncio # Para wavelink
import wavelink # Para Lavalink

print("--- Iniciando Bot  ---")

# Tentar importar a extensão Spotify, mas não falhar se não encontrar
try:
    from wavelink.ext import spotify
    spotify_ext_available = True
    print("-> Extensão wavelink.ext.spotify importada com sucesso.")
except ModuleNotFoundError:
    print("⚠️ AVISO: Módulo 'wavelink.ext' não encontrado. A integração com Spotify estará desativada.")
    spotify = None # Definir como None para verificações posteriores
    spotify_ext_available = False
except Exception as e:
    print("❌ Erro inesperado ao importar wavelink.ext.spotify:")
    traceback.print_exc()
    spotify = None
    spotify_ext_available = False

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
        # A conexão com Lavalink agora é feita no setup_hook

    async def setup_hook(self) -> None:
        """Hook executado após o login, ideal para conexões assíncronas."""
        print("--- [DIAGNÓSTICO] Entrando em setup_hook ---") # ADDED
        try: # ADDED try/except block
            print("--- [DIAGNÓSTICO] Dentro do try do setup_hook ---") # ADDED
            print("-> Executando setup_hook...") # Keep original print
            if lava_uri and lava_pass:
                print("--- [DIAGNÓSTICO] Tentando chamar connect_nodes... ---") # ADDED
                await self.connect_nodes()
                print("--- [DIAGNÓSTICO] connect_nodes chamado (ou pulado se erro). ---") # ADDED
            else:
                print("-> Conexão com Lavalink pulada em setup_hook (credenciais ausentes).") # Keep original print

            print("--- [DIAGNÓSTICO] Tentando chamar load_cogs... ---") # ADDED
            await self.load_cogs()
            print("--- [DIAGNÓSTICO] load_cogs chamado (ou pulado se erro). ---") # ADDED

        except Exception as e: # ADDED except block
            print(f"❌ [DIAGNÓSTICO] Erro DENTRO do setup_hook:") # ADDED
            traceback.print_exc() # ADDED
        print("--- [DIAGNÓSTICO] Saindo de setup_hook ---") # ADDED

    async def connect_nodes(self):
        """Conecta aos nós Lavalink."""
        # await self.wait_until_ready() # Não é mais necessário aqui, setup_hook roda após login
        if not lava_uri or not lava_pass:
            print("❌ Erro: Credenciais do Lavalink não configuradas. Não é possível conectar ao nó.")
            return

        print("-> Tentando conectar ao nó Lavalink em connect_nodes...")
        # REMOVIDO: Configuração manual do SpotifyClient. Assumindo Lavalink com LavaSrc.

        try:
            node: wavelink.Node = wavelink.Node(
                uri=lava_uri,
                password=lava_pass,
                # Se você estiver usando LavaSrc ou similar que suporte Spotify diretamente no Lavalink,
                # você NÃO precisa passar spotify_client aqui.
                # Se você REALMENTE precisar do wavelink.ext.spotify (menos comum agora),
                # o parâmetro seria passado para NodePool.connect, não Node().
                # Vamos manter simples por enquanto.
            )
            # Passar o spotify_client para o Pool.connect se aplicável (verificar documentação do Wavelink v3+)
            # Para LavaSrc, geralmente não é necessário passar nada aqui.
            await wavelink.NodePool.connect(client=self, nodes=[node])
            print(f"✅ Conexão com o nó Lavalink iniciada via NodePool.connect.")
        except Exception as e:
            print(f"❌ Erro ao iniciar conexão com o nó Lavalink:")
            traceback.print_exc()
            print("⚠️ O bot continuará funcionando, mas sem recursos de música.")

    async def load_cogs(self):
        """Carrega os COGs da pasta 'cogs'."""
        print("\n--- Carregando COGs (via setup_hook) ---")
        cogs_dir = "./cogs"
        if not os.path.isdir(cogs_dir):
            print(f"❌ Erro: Diretório de COGs '{cogs_dir}' não encontrado.")
            return

        try:
            all_files = os.listdir(cogs_dir)
            print(f"-> Arquivos encontrados em '{cogs_dir}': {all_files}")
            cog_files = [f for f in all_files if f.endswith(".py") and not f.startswith("__")]
            print(f"-> Arquivos .py a serem carregados: {cog_files}")
        except Exception as e:
            print(f"❌ Erro ao listar arquivos em '{cogs_dir}':")
            traceback.print_exc()
            cog_files = []

        cogs_loaded = []
        cogs_failed = []

        for filename in cog_files:
            cog_path = f"cogs.{filename[:-3]}"
            print(f"--> Tentando carregar: {cog_path}")
            try:
                self.load_extension(cog_path)
                print(f"✅ COG carregado com sucesso: {filename}")
                cogs_loaded.append(filename)
            except commands.errors.NoEntryPointError:
                print(f"⚠️ Aviso: {filename} não possui a função setup() e não pode ser carregado como cog.")
                cogs_failed.append(f"{filename} (sem setup)")
            except commands.errors.ExtensionAlreadyLoaded:
                print(f"⚠️ Aviso: {filename} já estava carregado.")
                cogs_loaded.append(filename)
            except Exception as e:
                print(f"❌ Erro ao carregar {filename}:")
                traceback.print_exc()
                cogs_failed.append(f"{filename} ({type(e).__name__})")
                print(f"⚠️ Ignorando erro e continuando com os próximos cogs...")

        loaded_extensions = list(self.extensions.keys())
        print(f"\n=== RESUMO DO CARREGAMENTO DE COGS ===")
        print(f"-> Total de cogs encontrados: {len(cog_files)}")
        print(f"-> Cogs carregados com sucesso ({len(cogs_loaded)}): {', '.join(cogs_loaded) if cogs_loaded else 'Nenhum'}")
        print(f"-> Cogs que falharam ({len(cogs_failed)}): {', '.join(cogs_failed) if cogs_failed else 'Nenhum'}")
        print(f"-> Extensões ativas ({len(loaded_extensions)}): {', '.join(loaded_extensions) if loaded_extensions else 'Nenhuma'}")
        print("=== FIM DO RESUMO ===\n")

bot = MusicBot(command_prefix="!", intents=intents)
print("-> Bot instanciado.")

@bot.event
async def on_ready():
    print(f"\n✅ {bot.user.name} está online e pronto!")
    # A sincronização de comandos pode ser movida para setup_hook também, mas on_ready ainda funciona.
    print("-> Tentando sincronizar comandos slash em on_ready...")
    try:
        synced = await bot.sync_application_commands()
        if synced is not None:
            print(f"🔄 Comandos slash sincronizados: {len(synced)} comandos")
        else:
            print("⚠️ A sincronização retornou None. Verifique se há comandos para sincronizar.")
    # Adicionar tratamento específico para NotFound (Unknown application command)
    except nextcord.errors.NotFound as e:
        print(f"⚠️ Erro 404 durante sincronização (Comando desconhecido ignorado): {e}")
        print("⚠️ O bot continuará funcionando, mas pode haver comandos antigos não removidos.")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos slash:")
        traceback.print_exc()
        print("⚠️ O bot continuará funcionando, mas os comandos slash podem não estar disponíveis.")
    print("-> Sincronização de comandos concluída (ou falhou).")

# Evento Wavelink para status do nó
@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    # Este evento é crucial para saber quando o nó está realmente pronto.
    node = payload.node
    session_id = payload.session_id
    print(f"✅ Nó Lavalink '{node.identifier}' (Sessão: {session_id}) está pronto e conectado!")
# REMOVIDO: Evento on_wavelink_node_disconnected (causando AttributeError)
# O carregamento de COGs foi movido para setup_hook

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
