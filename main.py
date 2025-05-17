import nextcord
import os
import asyncio
import traceback
import mafic
import logging
from nextcord import Interaction
from nextcord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive

print(f"--- VERSÃO DO NEXTCORD: {nextcord.__version__} ---")

# CORREÇÃO: Removidas barras invertidas desnecessárias das aspas
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('discord_bot')

logger.info("--- Iniciando Bot (com Mafic, Logging Detalhado e Inspeção de Cog) ---")

logger.info("-> Carregando variáveis de ambiente...")
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
lavalink_host = os.getenv("LAVALINK_HOST", "lavalink.jirayu.net")
lavalink_port = int(os.getenv("LAVALINK_PORT", "13592"))
lavalink_password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
lavalink_label = os.getenv("LAVALINK_LABEL", "LAVALINK_JIRAYU")

if not token:
    logger.critical("❌ CRÍTICO: Token do Discord não encontrado nas variáveis de ambiente.")
    exit()

logger.info("-> Variáveis de ambiente carregadas.")

logger.info("-> Configurando Intents...")
intents = nextcord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
logger.info("-> Intents configuradas.")

logger.info("-> Inicializando o Bot (com Mafic)...")
class MusicBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        logger.info("--- [DIAGNÓSTICO MAFIC] Iniciando __init__ da classe MusicBot ---")
        super().__init__(*args, **kwargs)
        self.mafic_pool: mafic.NodePool | None = None
        self._setup_hook_done = False # Adicionando a flag para controlar a execução do setup_hook
        logger.info("--- [DIAGNÓSTICO MAFIC] __init__ da classe MusicBot concluído ---")

    async def setup_hook(self) -> None:
        logger.critical("CRITICAL DEBUG: DENTRO DO SETUP_HOOK - LINHA INICIAL ANTES DE TUDO")
        logger.info("--- [DIAGNÓSTICO] Iniciando setup_hook ---")
        try:
            logger.info(f"--- [DIAGNÓSTICO MAFIC] Verificando Mafic: Versão {mafic.__version__}")
            logger.info(f"--- [DIAGNÓSTICO MAFIC] Inicializando Mafic NodePool ---")
            self.mafic_pool = mafic.NodePool(self)
            
            logger.info(f"--- [DIAGNÓSTICO MAFIC] Tentando conectar ao Lavalink (Mafic) em {lavalink_host}:{lavalink_port} com label {lavalink_label} ---")
            await self.mafic_pool.create_node(
                host=lavalink_host,
                port=lavalink_port,
                label=lavalink_label,
                password=lavalink_password,
            )
            logger.info("--- [DIAGNÓSTICO MAFIC] Chamada para create_node concluída. Aguardando on_mafic_node_ready na cog.")

            logger.info("--- [DIAGNÓSTICO] Iniciando carregamento de cogs em setup_hook ---")
            logger.info("--- [DEBUG] PRESTES A CHAMAR self.load_cogs() ---")
            await self.load_cogs()
            logger.info("--- [DIAGNÓSTICO] Carregamento de cogs concluído em setup_hook ---")

        except Exception as e:
            logger.critical(f"❌ CRÍTICO: Erro durante o setup_hook (Cogs ou Mafic): {e}", exc_info=True)
            logger.warning("⚠️ O bot pode não funcionar corretamente devido ao erro no setup_hook.")
        logger.info("--- [DIAGNÓSTICO] setup_hook concluído (ou falhou) ---")

    async def load_cogs(self):
        logger.info("--- [DEBUG] DENTRO DE self.load_cogs() --- INÍCIO DA FUNÇÃO ---")
        logger.info("--- Carregando COGs ---")
        cogs_dir = "cogs"
        cogs_loaded = []
        cogs_failed = []
        cog_files = []

        if not os.path.isdir(cogs_dir):
            # CORREÇÃO: Removidas barras invertidas desnecessárias das aspas
            logger.warning(f"⚠️ Diretório '{cogs_dir}' não encontrado. Nenhum cog será carregado.")
            return

        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                cog_path = f"{cogs_dir}.{filename[:-3]}"
                cog_files.append(cog_path)

                logger.info(f"--> Tentando carregar cog: {cog_path}")
                try:
                    self.load_extension(cog_path)
                    logger.info(f"✅ Cog {filename} carregado com sucesso.")
                    cogs_loaded.append(filename)
                    # ... (código de inspeção de cog omitido para brevidade, mas deve ser mantido se estava no original)
                except Exception as e:
                    logger.error(f"❌ Erro ao carregar cog {filename}: {e}", exc_info=True)
                    cogs_failed.append(f"{filename} ({type(e).__name__})")
                    logger.warning("⚠️ Ignorando erro e continuando com os próximos cogs...")

        loaded_extensions = list(self.extensions.keys())
        logger.info(f"\n=== RESUMO DO CARREGAMENTO DE COGS ===")
        logger.info(f"-> Total de cogs encontrados: {len(cog_files)}")
        # CORREÇÃO: Removidas barras invertidas desnecessárias das aspas
        logger.info(f"-> Cogs carregados com sucesso ({len(cogs_loaded)}): {', '.join(cogs_loaded) if cogs_loaded else 'Nenhum'}")
        logger.info(f"-> Cogs que falharam ({len(cogs_failed)}): {', '.join(cogs_failed) if cogs_failed else 'Nenhum'}")
        logger.info(f"-> Extensões ativas ({len(loaded_extensions)}): {', '.join(loaded_extensions) if loaded_extensions else 'Nenhuma'}")
        logger.info("=== FIM DO RESUMO ===\n")

bot = MusicBot(command_prefix="!", intents=intents)
logger.info("-> Instância de MusicBot criada.")
@bot.event
async def on_ready():
    if not bot._setup_hook_done:
        logger.info("--- [DIAGNÓSTICO ON_READY] _setup_hook_done é False. Chamando setup_hook manualmente... ---")
        try:
            await bot.setup_hook()
            bot._setup_hook_done = True
            logger.info("--- [DIAGNÓSTICO ON_READY] Chamada manual de setup_hook concluída e _setup_hook_done definido como True. ---")
        except Exception as e_setup:
            logger.critical(f"❌ CRÍTICO: Erro ao chamar setup_hook manualmente de on_ready: {e_setup}", exc_info=True)
    else:
        logger.info("--- [DIAGNÓSTICO ON_READY] _setup_hook_done é True. Pulando chamada manual de setup_hook. ---")
    
    logger.info(f"\n✅ {bot.user.name} está online e pronto! ID: {bot.user.id}")
    logger.info("--- [DIAGNÓSTICO COMANDOS GLOBAIS] Verificando comandos de aplicação GLOBAIS DO BOT ANTES da sincronização em on_ready ---")
    all_app_cmds_on_ready = bot.get_application_commands()
    if all_app_cmds_on_ready:
        logger.info(f"Total de comandos de aplicação detectados GLOBALMENTE NO BOT (on_ready): {len(all_app_cmds_on_ready)}")
        for cmd in all_app_cmds_on_ready:
            # CORREÇÃO: Removidas barras invertidas desnecessárias das aspas
            logger.info(f"  -> Comando Global (on_ready): '{cmd.qualified_name}', Tipo: {type(cmd)}, Guild IDs: {cmd.guild_ids}, Descrição: {cmd.description}")
    else:
        logger.warning("Nenhum comando de aplicação detectado GLOBALMENTE NO BOT (on_ready) antes da sincronização.")

    logger.info("-> Tentando sincronizar comandos slash globalmente em on_ready...")
    try:
        synced_global = await bot.sync_application_commands()
        if synced_global is not None:
            logger.info(f"🔄 Comandos slash sincronizados/enviados para registro GLOBAL: {len(synced_global)} comandos.")
            for s_cmd in synced_global:
                # CORREÇÃO: Removidas barras invertidas desnecessárias das aspas
                logger.info(f"    Synced Global: '{s_cmd.name}', ID: {s_cmd.id}, Guild ID: {s_cmd.guild_id}")
        else:
            logger.warning("⚠️ A sincronização GLOBAL retornou None.")

    except Exception as e:
        logger.error(f"❌ Erro genérico ao sincronizar comandos slash: {e}", exc_info=True)
    logger.info("-> Sincronização de comandos concluída (ou falhou).")

keep_alive()

logger.info("-> Iniciando execução do bot com o token...")
logger.info("--- [DIAGNÓSTICO MAFIC] Antes de bot.run() ---")
try:
    bot.run(token)
except nextcord.errors.LoginFailure:
    logger.critical("❌ CRÍTICO: Falha no login - Token inválido. Verifique seu token.", exc_info=True)
except Exception as e:
    logger.critical(f"❌ Erro crítico durante a execução do bot: {e}", exc_info=True)
finally:
    logger.info("--- [DIAGNÓSTICO MAFIC] Após bot.run() (no finally) ---")
    logger.info("--- Bot encerrado ---")
