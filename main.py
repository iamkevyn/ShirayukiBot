import nextcord
import os
import asyncio
import traceback
import mafic # <--- MUDANÇA: Wavelink para Mafic
from nextcord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive

print("--- Iniciando Bot (com Mafic) ---")

print("-> Carregando variáveis de ambiente...")
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
lavalink_host = os.getenv("LAVALINK_HOST", "lavalink.jirayu.net") # Usar LAVALINK_HOST
lavalink_port = int(os.getenv("LAVALINK_PORT", "13592")) # Usar LAVALINK_PORT, converter para int
lavalink_password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
lavalink_label = os.getenv("LAVALINK_LABEL", "LAVALINK_JIRAYU") # Label para o nó Mafic

if not token:
    print("❌ CRÍTICO: Token do Discord não encontrado nas variáveis de ambiente.")
    exit()

print("-> Variáveis de ambiente carregadas.")

print("-> Configurando Intents...")
intents = nextcord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
print("-> Intents configuradas.")

print("-> Inicializando o Bot (com Mafic)...")
class MusicBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        print("--- [DIAGNÓSTICO MAFIC] Iniciando __init__ da classe MusicBot ---")
        super().__init__(*args, **kwargs)
        # O NodePool do Mafic será inicializado no setup_hook
        self.mafic_pool: mafic.NodePool | None = None
        print("--- [DIAGNÓSTICO MAFIC] __init__ da classe MusicBot concluído ---")

    async def setup_hook(self) -> None:
        print("--- [DIAGNÓSTICO MAFIC] Iniciando setup_hook ---")
        try:
            print(f"--- [DIAGNÓSTICO MAFIC] Verificando Mafic: Versão {mafic.__version__}")
            print(f"--- [DIAGNÓSTICO MAFIC] Inicializando Mafic NodePool ---")
            self.mafic_pool = mafic.NodePool(self) # Inicializa o NodePool do Mafic
            
            print(f"--- [DIAGNÓSTICO MAFIC] Tentando conectar ao Lavalink (Mafic) em {lavalink_host}:{lavalink_port} ---")
            await self.mafic_pool.create_node(
                host=lavalink_host,
                port=lavalink_port,
                label=lavalink_label,
                password=lavalink_password,
                # secure=False # Adicionar se o Lavalink não usar SSL
            )
            # O evento on_mafic_node_ready na cog Musica confirmará a conexão

            print("--- [DIAGNÓSTICO MAFIC] Iniciando carregamento de cogs em setup_hook ---")
            await self.load_cogs()
            print("--- [DIAGNÓSTICO MAFIC] Carregamento de cogs concluído em setup_hook ---")

        except Exception as e:
            print(f"❌ CRÍTICO: Erro durante o setup_hook (Mafic ou Cogs):")
            traceback.print_exc()
            print("⚠️ O bot pode não funcionar corretamente devido ao erro no setup_hook.")
        print("--- [DIAGNÓSTICO MAFIC] setup_hook concluído (ou falhou) ---")

    async def load_cogs(self):
        print("--- Carregando COGs (via setup_hook com Mafic) ---")
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
        print(f"\n=== RESUMO DO CARREGAMENTO DE COGS (MAFIC) ===")
        print(f"-> Total de cogs encontrados: {len(cog_files)}")
        print(f"-> Cogs carregados com sucesso ({len(cogs_loaded)}): {', '.join(cogs_loaded) if cogs_loaded else 'Nenhum'}")
        print(f"-> Cogs que falharam ({len(cogs_failed)}): {', '.join(cogs_failed) if cogs_failed else 'Nenhum'}")
        print(f"-> Extensões ativas ({len(loaded_extensions)}): {', '.join(loaded_extensions) if loaded_extensions else 'Nenhuma'}")
        print("=== FIM DO RESUMO ===\n")

bot = MusicBot(command_prefix="!", intents=intents)
print("-> Bot (Mafic) instanciado.")

@bot.event
async def on_ready():
    print(f"\n✅ {bot.user.name} (Mafic) está online e pronto!")
    print("-> Tentando sincronizar comandos slash em on_ready (global + guild-specific)...")
    try:
        synced = await bot.sync_application_commands()
        if synced is not None:
            print(f"🔄 Comandos slash sincronizados/enviados para registro: {len(synced)} comandos")
        else:
            print("⚠️ A sincronização retornou None. Verifique se há comandos para sincronizar.")
    except nextcord.errors.NotFound as e:
        print(f"⚠️ Erro 404 durante sincronização (Comando desconhecido ignorado): {e}")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos slash:")
        traceback.print_exc()
    print("-> Sincronização de comandos concluída (ou falhou).")

# O evento on_mafic_node_ready é tratado na cog Musica.py
# Não é mais necessário um listener on_wavelink_node_ready aqui.

keep_alive()

print("-> Iniciando execução do bot (Mafic) com o token...")
print("--- [DIAGNÓSTICO MAFIC] Antes de bot.run() ---")
try:
    bot.run(token)
except nextcord.errors.LoginFailure:
    print("❌ CRÍTICO: Falha no login - Token inválido. Verifique seu token.")
except Exception as e:
    print("❌ Erro crítico durante a execução do bot (Mafic):")
    traceback.print_exc()
finally:
    print("--- [DIAGNÓSTICO MAFIC] Após bot.run() (no finally) ---")
    print("--- Bot (Mafic) encerrado ---")
