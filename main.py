import nextcord
import os
import asyncio
import traceback
import mafic
import logging
from nextcord import Interaction # <--- ADICIONADO: Interaction para o comando de teste
from nextcord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive

# Configuração básica do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('discord_bot')

logger.info("--- Iniciando Bot (com Mafic, Logging Detalhado e Teste de Comando no Main) ---")

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
        logger.info("--- [DIAGNÓSTICO MAFIC] __init__ da classe MusicBot concluído ---")

    async def setup_hook(self) -> None:
        logger.info("--- [DIAGNÓSTICO MAFIC] Iniciando setup_hook ---")
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
            logger.info("--- [DIAGNÓSTICO MAFIC] Chamada para create_node concluída. Aguardando on_mafic_node_ready na cog. ---")

            logger.info("--- [DIAGNÓSTICO MAFIC] Iniciando carregamento de cogs em setup_hook ---")
            await self.load_cogs()
            logger.info("--- [DIAGNÓSTICO MAFIC] Carregamento de cogs concluído em setup_hook ---")

        except Exception as e:
            logger.critical(f"❌ CRÍTICO: Erro durante o setup_hook (Mafic ou Cogs): {e}", exc_info=True)
            logger.warning("⚠️ O bot pode não funcionar corretamente devido ao erro no setup_hook.")
        logger.info("--- [DIAGNÓSTICO MAFIC] setup_hook concluído (ou falhou) ---")

    async def load_cogs(self):
        logger.info("--- Carregando COGs (via setup_hook com Mafic) ---")
        cogs_dir = "cogs"
        cogs_loaded = []
        cogs_failed = []
        cog_files = []

        if not os.path.isdir(cogs_dir):
            logger.warning(f"⚠️ Diretório 		'{cogs_dir}'		 não encontrado. Nenhum cog será carregado.")
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

                except commands.errors.NoEntryPointError:
                    logger.warning(f"⚠️ Aviso: Cog {filename} não possui uma função 'setup'. Pulando.")
                    cogs_failed.append(f"{filename} (sem setup)")
                except commands.errors.ExtensionAlreadyLoaded:
                    logger.warning(f"⚠️ Aviso: Cog {filename} já estava carregado.")
                    cogs_loaded.append(filename)
                except Exception as e:
                    logger.error(f"❌ Erro ao carregar cog {filename}: {e}", exc_info=True)
                    cogs_failed.append(f"{filename} ({type(e).__name__})")
                    logger.warning(f"⚠️ Ignorando erro e continuando com os próximos cogs...")

        loaded_extensions = list(self.extensions.keys())
        logger.info(f"\n=== RESUMO DO CARREGAMENTO DE COGS (MAFIC) ===")
        logger.info(f"-> Total de cogs encontrados: {len(cog_files)}")
        logger.info(f"-> Cogs carregados com sucesso ({len(cogs_loaded)}): {', '.join(cogs_loaded) if cogs_loaded else 'Nenhum'}")
        logger.info(f"-> Cogs que falharam ({len(cogs_failed)}): {', '.join(cogs_failed) if cogs_failed else 'Nenhum'}")
        logger.info(f"-> Extensões ativas ({len(loaded_extensions)}): {', '.join(loaded_extensions) if loaded_extensions else 'Nenhuma'}")
        
        if loaded_extensions:
            logger.info("--- [DIAGNÓSTICO COMANDOS] Verificando comandos de aplicação carregados APÓS load_cogs ---")
            all_app_cmds_after_cogs = self.get_application_commands()
            if all_app_cmds_after_cogs:
                logger.info(f"Total de comandos de aplicação detectados globalmente no bot APÓS carregar cogs: {len(all_app_cmds_after_cogs)}")
                for cmd in all_app_cmds_after_cogs:
                    logger.info(f"  -> Comando (pós-cogs): '{cmd.qualified_name}', Tipo: {type(cmd)}, Guild IDs: {cmd.guild_ids}")
            else:
                logger.warning("Nenhum comando de aplicação detectado globalmente no bot após carregar cogs.")
        logger.info("=== FIM DO RESUMO ===\n")

bot = MusicBot(command_prefix="!", intents=intents)
logger.info("-> Bot (Mafic) instanciado.")

# --- COMANDO DE TESTE DIRETO NO MAIN.PY ---
@bot.slash_command(name="testemainslash", description="Um comando de teste simples no main.py")
async def teste_main_slash(interaction: Interaction):
    logger.info(f"--- [TESTE MAIN SLASH] Comando /testemainslash executado por {interaction.user} ---")
    await interaction.response.send_message("Olá! Este é um comando de teste do main.py!", ephemeral=True)
    logger.info("--- [TESTE MAIN SLASH] Resposta enviada. ---")
# --- FIM DO COMANDO DE TESTE ---

@bot.event
async def on_ready():
    logger.info(f"\n✅ {bot.user.name} (Mafic) está online e pronto! ID: {bot.user.id}")
    logger.info("--- [DIAGNÓSTICO COMANDOS] Verificando comandos de aplicação ANTES da sincronização em on_ready ---")
    all_app_cmds = bot.get_application_commands()
    if all_app_cmds:
        logger.info(f"Total de comandos de aplicação detectados globalmente no bot: {len(all_app_cmds)}")
        for cmd in all_app_cmds:
            logger.info(f"  -> Comando: '{cmd.qualified_name}', Tipo: {type(cmd)}, Guild IDs: {cmd.guild_ids}, Descrição: {cmd.description}")
    else:
        logger.warning("Nenhum comando de aplicação detectado globalmente no bot antes da sincronização.")

    logger.info("-> Tentando sincronizar comandos slash globalmente em on_ready...")
    try:
        synced = await bot.sync_application_commands()
        if synced is not None:
            logger.info(f"🔄 Comandos slash sincronizados/enviados para registro global: {len(synced)} comandos.")
            for s_cmd in synced:
                logger.info(f"    Synced: '{s_cmd.name}', ID: {s_cmd.id}, Guild ID: {s_cmd.guild_id}")
        else:
            logger.warning("⚠️ A sincronização global retornou None. Verifique se há comandos para sincronizar ou se já estão sincronizados.")
    except nextcord.errors.ApplicationInvokeError as e:
        logger.error(f"❌ Erro de Invocação de Aplicação durante sincronização global: {e.original if e.original else e}", exc_info=True)
    except nextcord.errors.HTTPException as e:
        logger.error(f"❌ Erro HTTP durante sincronização global: Status {e.status}, Código {e.code}, Texto: {e.text}", exc_info=True)
    except Exception as e:
        logger.error(f"❌ Erro genérico ao sincronizar comandos slash globalmente: {e}", exc_info=True)
    logger.info("-> Sincronização de comandos global concluída (ou falhou).")

keep_alive()

logger.info("-> Iniciando execução do bot (Mafic) com o token...")
logger.info("--- [DIAGNÓSTICO MAFIC] Antes de bot.run() ---")
try:
    bot.run(token)
except nextcord.errors.LoginFailure:
    logger.critical("❌ CRÍTICO: Falha no login - Token inválido. Verifique seu token.", exc_info=True)
except Exception as e:
    logger.critical(f"❌ Erro crítico durante a execução do bot (Mafic): {e}", exc_info=True)
finally:
    logger.info("--- [DIAGNÓSTICO MAFIC] Após bot.run() (no finally) ---")
    logger.info("--- Bot (Mafic) encerrado ---")
