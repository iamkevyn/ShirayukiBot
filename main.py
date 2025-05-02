import nextcord
import os
import asyncio
import traceback
import wavelink
from nextcord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive # <-- Adicionado import

print("--- Iniciando Bot ---")

# Verifica se wavelink.ext.spotify está disponível
try:
    # Tenta importar algo específico do módulo
    from wavelink.ext import spotify
    # Se chegou aqui, o módulo existe, mas não vamos usá-lo diretamente
    print("⚠️ AVISO: Módulo 'wavelink.ext.spotify' encontrado, mas a integração direta está desativada. Use LavaSrc no Lavalink.")
    # Definir spotify_client como None para evitar erros posteriores se o código antigo ainda o referenciar
    spotify_client = None
except ImportError:
    # Se falhar, o módulo não está instalado ou disponível
    print("⚠️ AVISO: Módulo 'wavelink.ext' não encontrado. A integração com Spotify estará desativada.")
    spotify_client = None # Garante que a variável exista como None
except Exception as e:
    print(f"❌ Erro inesperado ao verificar 'wavelink.ext.spotify': {e}")
    spotify_client = None

print("-> Carregando variáveis de ambiente...")
# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
uri = os.getenv("LAVALINK_URI")
password = os.getenv("LAVALINK_PASSWORD")

if not token:
    print("❌ CRÍTICO: Token do Discord não encontrado nas variáveis de ambiente.")
    exit()
if not uri:
    print("⚠️ AVISO: URI do Lavalink não encontrada. Funcionalidades de música podem não funcionar.")
if not password:
    print("⚠️ AVISO: Senha do Lavalink não encontrada. Funcionalidades de música podem não funcionar.")

print("-> Variáveis de ambiente carregadas.")

print("-> Configurando Intents...")
# Define as intents necessárias para o bot
intents = nextcord.Intents.default()
intents.message_content = True # Necessário para ler o conteúdo das mensagens (se aplicável)
intents.voice_states = True    # Necessário para gerenciar estados de voz
intents.guilds = True          # Necessário para informações da guilda
print("-> Intents configuradas.")

print("-> Inicializando o Bot...")
# Define a classe principal do bot, herdando de commands.Bot
class MusicBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        print("--- [DIAGNÓSTICO] Iniciando __init__ da classe MusicBot ---")
        super().__init__(*args, **kwargs)
        self.loop.create_task(self.setup_hook()) # Chama setup_hook na inicialização
        print("--- [DIAGNÓSTICO] __init__ da classe MusicBot concluído ---")

    async def setup_hook(self) -> None:
        """Inicializa o nó Lavalink e carrega os cogs."""
        print("--- [DIAGNÓSTICO] Iniciando setup_hook ---")
        try:
            if uri and password:
                print("--- [DIAGNÓSTICO] Tentando conectar nós Lavalink ---")
                node: wavelink.Node = wavelink.Node(uri=uri, password=password)
                # Não passamos mais spotify_client aqui
                await wavelink.Pool.connect(nodes=[node], client=self)
                print("--- [DIAGNÓSTICO] Conexão com Lavalink iniciada (aguardando on_wavelink_node_ready) ---")
            else:
                print("--- [DIAGNÓSTICO] URI ou senha do Lavalink ausentes. Pulando conexão com Lavalink. ---")

            print("--- [DIAGNÓSTICO] Iniciando carregamento de cogs em setup_hook ---")
            await self.load_cogs()
            print("--- [DIAGNÓSTICO] Carregamento de cogs concluído em setup_hook ---")

        except Exception as e:
            print(f"❌ CRÍTICO: Erro durante o setup_hook:")
            traceback.print_exc()
            print("⚠️ O bot pode não funcionar corretamente devido ao erro no setup_hook.")
        print("--- [DIAGNÓSTICO] setup_hook concluído (ou falhou) ---")

    async def load_cogs(self):
        print("--- Carregando COGs (via setup_hook) ---")
        cogs_dir = "cogs"
        cogs_loaded = []
        cogs_failed = []
        cog_files = []

        if not os.path.isdir(cogs_dir):
            print(f"⚠️ Diretório '{cogs_dir}' não encontrado. Nenhum cog será carregado.")
            return

        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                cog_path = f"{cogs_dir}.{filename[:-3]}"
                cog_files.append(cog_path)
                print(f"--> Tentando carregar: {cog_path}")
                try:
                    self.load_extension(cog_path)
                    # Verifica se a extensão realmente tem um comando setup
                    # (Nota: load_extension já faz isso implicitamente, mas podemos ser explícitos)
                    # ext = self.get_cog(cog_path.split('.')[-1]) # Pega o nome da classe
                    # if ext is None or not hasattr(ext, 'setup'):
                    #     print(f"⚠️ Aviso: {filename} carregado, mas não parece ter uma função 'setup'.")
                    #     cogs_failed.append(f"{filename} (sem setup)")
                    # else:
                    print(f"✅ {filename} carregado com sucesso.")
                    cogs_loaded.append(filename)

                except commands.errors.NoEntryPointError:
                    print(f"⚠️ Aviso: {filename} não possui uma função 'setup'. Pulando.")
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
    print("-> Sincronização de comandos slash TEMPORARIAMENTE DESATIVADA para teste.")
    # print("-> Tentando sincronizar comandos slash em on_ready...")
    # try:
    #     synced = await bot.sync_application_commands()
    #     if synced is not None:
    #         print(f"🔄 Comandos slash sincronizados: {len(synced)} comandos")
    #     else:
    #         print("⚠️ A sincronização retornou None. Verifique se há comandos para sincronizar.")
    # # Adicionar tratamento específico para NotFound (Unknown application command)
    # except nextcord.errors.NotFound as e:
    #     print(f"⚠️ Erro 404 durante sincronização (Comando desconhecido ignorado): {e}")
    #     print("⚠️ O bot continuará funcionando, mas pode haver comandos antigos não removidos.")
    # except Exception as e:
    #     print(f"❌ Erro ao sincronizar comandos slash:")
    #     traceback.print_exc()
    #     print("⚠️ O bot continuará funcionando, mas os comandos slash podem não estar disponíveis.")
    # print("-> Sincronização de comandos concluída (ou falhou).")

# Evento Wavelink para status do nó
@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    # Este evento é crucial para saber quando o nó está realmente pronto.
    node = payload.node
    session_id = payload.session_id
    print(f"✅ Nó Lavalink '{node.identifier}' (Sessão: {session_id}) está pronto e conectado!")

# REMOVIDO: Evento on_wavelink_node_disconnected (causando AttributeError)

# O carregamento de COGs foi movido para setup_hook

# Inicia o servidor keep alive em background
keep_alive() # <-- Adicionada chamada

# Executa o bot
print("-> Iniciando execução do bot com o token...")
print("--- [DIAGNÓSTICO] Antes de bot.run() ---")
try:
    bot.run(token)
except nextcord.errors.LoginFailure:
    print("❌ CRÍTICO: Falha no login - Token inválido. Verifique seu token.")
except Exception as e:
    print("❌ Erro crítico durante a execução do bot:")
    traceback.print_exc()
finally:
    print("--- [DIAGNÓSTICO] Após bot.run() (no finally) ---")
    print("--- Bot encerrado ---")
