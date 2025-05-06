import nextcord
import os
import asyncio
import traceback
import wavelink # Re-adicionado Wavelink
from nextcord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive # Mantido import

print("--- Iniciando Bot ---")

# Removida verificação de wavelink.ext.spotify

print("-> Carregando variáveis de ambiente...")
# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
lavalink_uri = os.getenv("LAVALINK_URI", "http://localhost:2333") # Default to localhost if not set
lavalink_password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass") # Default password

# ID do servidor da Shira para registro imediato de comandos
SHIRA_GUILD_ID = 1367345048458498219

if not token:
    print("❌ CRÍTICO: Token do Discord não encontrado nas variáveis de ambiente.")
    exit()

print("-> Variáveis de ambiente carregadas (incluindo Lavalink defaults se não definidos).")

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
        """Carrega os cogs e tenta conectar ao Lavalink."""
        print("--- [DIAGNÓSTICO] Iniciando setup_hook ---")
        try:
            print(f"--- [DIAGNÓSTICO] Verificando Wavelink: Versão {wavelink.__version__}, Atributos: {dir(wavelink)}")
            print(f"--- [DIAGNÓSTICO] Tentando conectar ao Lavalink em {lavalink_uri} ---")
            node: wavelink.Node = wavelink.Node(uri=lavalink_uri, password=lavalink_password)
            await wavelink.Pool.connect(client=self, nodes=[node]) # Tenta usar Pool em vez de NodePool
            # O evento on_wavelink_node_ready confirmará a conexão

            print("--- [DIAGNÓSTICO] Iniciando carregamento de cogs em setup_hook ---")
            await self.load_cogs()
            print("--- [DIAGNÓSTICO] Carregamento de cogs concluído em setup_hook ---")

        except Exception as e:
            print(f"❌ CRÍTICO: Erro durante o setup_hook (Lavalink ou Cogs):")
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

# Inicializa o bot com o ID do servidor da Shira como debug_guild
# Isso garante registro imediato lá, mas mantém o registro global para outros servidores.
bot = MusicBot(command_prefix="!", intents=intents, debug_guilds=[SHIRA_GUILD_ID])
print(f"-> Bot instanciado com debug_guilds=[{SHIRA_GUILD_ID}].")

@bot.event
async def on_ready():
    print(f"\n✅ {bot.user.name} está online e pronto!")
    # A sincronização aqui ainda tentará o registro global, mas o debug_guild garante a disponibilidade imediata no servidor da Shira.
    print("-> Tentando sincronizar comandos slash em on_ready (global + debug guild)...")
    try:
        # Não passamos guild_ids aqui para permitir o registro global em paralelo.
        # O debug_guilds na inicialização já cuida do registro imediato.
        synced = await bot.sync_application_commands()
        if synced is not None:
            print(f"🔄 Comandos slash sincronizados/enviados para registro: {len(synced)} comandos")
        else:
            print("⚠️ A sincronização retornou None. Verifique se há comandos para sincronizar.")
    except nextcord.errors.NotFound as e:
        print(f"⚠️ Erro 404 durante sincronização (Comando desconhecido ignorado): {e}")
        print("⚠️ O bot continuará funcionando, mas pode haver comandos antigos não removidos.")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos slash:")
        traceback.print_exc()
        print("⚠️ O bot continuará funcionando, mas os comandos slash podem não estar disponíveis imediatamente em todos os servidores.")
    print("-> Sincronização de comandos concluída (ou falhou).")

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    """Evento chamado quando um nó Lavalink está pronto."""
    node = payload.node # Acessa o nó a partir do payload
    print(f"✅ Nó Lavalink '{node.identifier}' conectado e pronto!")

# Inicia o servidor keep alive em background
keep_alive() # Mantida chamada

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
