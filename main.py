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

print(f"--- VERSÃO DO NEXTCORD: {nextcord.__version__} ---") # Adicionado para imprimir a versão do Nextcord

# Configuração básica do logging
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
        logger.info("--- [DIAGNÓSTICO MAFIC] __init__ da classe MusicBot concluído ---")

    async def setup_hook(self) -> None:
        logger.critical("CRITICAL DEBUG: DENTRO DO SETUP_HOOK - LINHA INICIAL ANTES DE TUDO") # MODIFICADO DE PRINT PARA LOGGER.CRITICAL
        logger.info("--- [DIAGNÓSTICO] Iniciando setup_hook (Mafic temporariamente desativado para teste) ---") # Log ajustado
        try:
            # logger.info(f"--- [DIAGNÓSTICO MAFIC] Verificando Mafic: Versão {mafic.__version__}")
            # logger.info(f"--- [DIAGNÓSTICO MAFIC] Inicializando Mafic NodePool ---")
            # self.mafic_pool = mafic.NodePool(self)
            
            # logger.info(f"--- [DIAGNÓSTICO MAFIC] Tentando conectar ao Lavalink (Mafic) em {lavalink_host}:{lavalink_port} com label {lavalink_label} ---")
            # await self.mafic_pool.create_node(
            #     host=lavalink_host,
            #     port=lavalink_port,
            #     label=lavalink_label,
            #     password=lavalink_password,
            # )
            # logger.info("--- [DIAGNÓSTICO MAFIC] Chamada para create_node concluída. Aguardando on_mafic_node_ready na cog. ---")

            logger.info("--- [DIAGNÓSTICO] Iniciando carregamento de cogs em setup_hook (Mafic desativado) ---") # Log ajustado
            logger.info("--- [DEBUG] PRESTES A CHAMAR self.load_cogs() ---")
            await self.load_cogs()
            logger.info("--- [DIAGNÓSTICO] Carregamento de cogs concluído em setup_hook (Mafic desativado) ---") # Log ajustado

        except Exception as e:
            logger.critical(f"❌ CRÍTICO: Erro durante o setup_hook (Cogs): {e}", exc_info=True) # Log ajustado
            logger.warning("⚠️ O bot pode não funcionar corretamente devido ao erro no setup_hook.")
        logger.info("--- [DIAGNÓSTICO] setup_hook (Mafic desativado) concluído (ou falhou) ---") # Log ajustado

    async def load_cogs(self):
        logger.info("--- [DEBUG] DENTRO DE self.load_cogs() --- INÍCIO DA FUNÇÃO ---")
        logger.info("--- Carregando COGs (Mafic desativado para este teste) ---") # Log ajustado
        cogs_dir = "cogs"
        cogs_loaded = []
        cogs_failed = []
        cog_files = []

        if not os.path.isdir(cogs_dir):
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

                    cog_name_to_inspect = None
                    if filename == "Musica.py": 
                        cog_name_to_inspect = "Musica"
                    elif filename == "Comandos.py":
                        cog_name_to_inspect = "Comandos"
                    elif filename == "Economia.py":
                        cog_name_to_inspect = "Economia"
                    elif filename == "Informacoes.py":
                        cog_name_to_inspect = "Informacoes"
                    elif filename == "Interacoes.py":
                        cog_name_to_inspect = "Interacoes"
                    elif filename == "Jogos.py":
                        cog_name_to_inspect = "Jogos"
                    elif filename == "Utilitarios.py":
                        cog_name_to_inspect = "Utilitarios"
                    else:
                        cog_name_to_inspect = filename[:-3].capitalize()

                    if cog_name_to_inspect:
                        cog_instance = self.get_cog(cog_name_to_inspect)
                        if cog_instance:
                            logger.info(f"--- [INSPEÇÃO COG] Instância da cog '{cog_instance.qualified_name}' (Tipo: {type(cog_instance)}) obtida.")
                            
                            cog_app_commands_from_instance = []
                            if hasattr(cog_instance, 'get_application_commands'):
                                try:
                                    cog_app_commands_from_instance = cog_instance.get_application_commands()
                                except Exception as e_get_app_cmds:
                                     logger.error(f"    -- Erro ao chamar get_application_commands() na cog '{cog_instance.qualified_name}': {e_get_app_cmds}", exc_info=False)

                            if cog_app_commands_from_instance:
                                logger.info(f"  -> Comandos de aplicação (via get_application_commands) DENTRO da cog '{cog_instance.qualified_name}': {len(cog_app_commands_from_instance)}")
                                for app_cmd in cog_app_commands_from_instance:
                                    logger.info(f"    -- Cog App Cmd (instância): '{app_cmd.qualified_name}', Tipo: {type(app_cmd)}")
                            else:
                                logger.warning(f"  -> Nenhum comando de aplicação (via get_application_commands) encontrado DENTRO da cog '{cog_instance.qualified_name}'.")

                            cog_all_commands_from_instance = []
                            try:
                                cog_all_commands_from_instance = cog_instance.get_commands()
                            except Exception as e_get_cmds:
                                logger.error(f"    -- Erro ao chamar get_commands() na cog '{cog_instance.qualified_name}': {e_get_cmds}", exc_info=False)

                            if cog_all_commands_from_instance:
                                logger.info(f"  -> Comandos (gerais via get_commands) DENTRO da cog '{cog_instance.qualified_name}': {len(cog_all_commands_from_instance)}")
                                for cmd_obj in cog_all_commands_from_instance:
                                    logger.info(f"    -- Cog Cmd Geral (instância): '{cmd_obj.qualified_name}', Tipo: {type(cmd_obj)}")
                            else:
                                logger.warning(f"  -> Nenhum comando (geral via get_commands) encontrado DENTRO da cog '{cog_instance.qualified_name}'.")
                            
                            cog_slash_commands_internal = getattr(cog_instance, '__cog_slash_commands__', {})
                            if cog_slash_commands_internal and isinstance(cog_slash_commands_internal, dict) and cog_slash_commands_internal:
                                logger.info(f"  -> Atributo __cog_slash_commands__ DENTRO da cog '{cog_instance.qualified_name}': {len(cog_slash_commands_internal)} comandos.")
                                for cmd_name, cmd_obj_internal in cog_slash_commands_internal.items():
                                     logger.info(f"    -- Cog Slash Cmd Interno: '{cmd_name}' (Objeto: {cmd_obj_internal.name if hasattr(cmd_obj_internal, 'name') else type(cmd_obj_internal)}) - Tipo do objeto: {type(cmd_obj_internal)}")
                            else:
                                logger.warning(f"  -> Atributo __cog_slash_commands__ não encontrado, vazio ou não é um dict DENTRO da cog '{cog_instance.qualified_name}'. Valor: {cog_slash_commands_internal}")
                        else:
                            logger.warning(f"--- [INSPEÇÃO COG] Não foi possível obter a instância da cog '{cog_name_to_inspect}' usando self.get_cog().")

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
        logger.info(f"\n=== RESUMO DO CARREGAMENTO DE COGS (Mafic desativado) ===") # Log ajustado
        logger.info(f"-> Total de cogs encontrados: {len(cog_files)}")
        logger.info(f"-> Cogs carregados com sucesso ({len(cogs_loaded)}): {', '.join(cogs_loaded) if cogs_loaded else 'Nenhum'}")
        logger.info(f"-> Cogs que falharam ({len(cogs_failed)}): {', '.join(cogs_failed) if cogs_failed else 'Nenhum'}")
        logger.info(f"-> Extensões ativas ({len(loaded_extensions)}): {', '.join(loaded_extensions) if loaded_extensions else 'Nenhuma'}")
        
        logger.info("--- [DIAGNÓSTICO COMANDOS GLOBAIS] Verificando comandos de aplicação GLOBAIS DO BOT APÓS load_cogs ---")
        all_app_cmds_after_cogs = self.get_application_commands()
        if all_app_cmds_after_cogs:
            logger.info(f"Total de comandos de aplicação detectados GLOBALMENTE NO BOT APÓS carregar cogs: {len(all_app_cmds_after_cogs)}")
            for cmd in all_app_cmds_after_cogs:
                logger.info(f"  -> Comando Global (pós-cogs): '{cmd.qualified_name}', Tipo: {type(cmd)}, Guild IDs: {cmd.guild_ids}")
        else:
            logger.warning("Nenhum comando de aplicação detectado GLOBALMENTE NO BOT após carregar cogs.")
        logger.info("=== FIM DO RESUMO ===\n")

bot = MusicBot(command_prefix="!", intents=intents)
logger.info("-> Bot (Mafic) instanciado.")

@bot.slash_command(name="testemainslash", description="Um comando de teste simples no main.py")
async def teste_main_slash(interaction: Interaction):
    logger.info(f"--- [TESTE MAIN SLASH] Comando /testemainslash executado por {interaction.user} ---")
    await interaction.response.send_message("Olá! Este é um comando de teste do main.py!", ephemeral=True)
    logger.info("--- [TESTE MAIN SLASH] Resposta enviada. ---")

@bot.event
async def on_ready():
    logger.info(f"\n✅ {bot.user.name} (Mafic) está online e pronto! ID: {bot.user.id}")
    logger.info("--- [DIAGNÓSTICO COMANDOS GLOBAIS] Verificando comandos de aplicação GLOBAIS DO BOT ANTES da sincronização em on_ready ---")
    all_app_cmds_on_ready = bot.get_application_commands()
    if all_app_cmds_on_ready:
        logger.info(f"Total de comandos de aplicação detectados GLOBALMENTE NO BOT (on_ready): {len(all_app_cmds_on_ready)}")
        for cmd in all_app_cmds_on_ready:
            logger.info(f"  -> Comando Global (on_ready): '{cmd.qualified_name}', Tipo: {type(cmd)}, Guild IDs: {cmd.guild_ids}, Descrição: {cmd.description}")
    else:
        logger.warning("Nenhum comando de aplicação detectado GLOBALMENTE NO BOT (on_ready) antes da sincronização.")

    logger.info("-> Tentando sincronizar comandos slash globalmente em on_ready...")
    try:
        synced_global = await bot.sync_application_commands()
        if synced_global is not None:
            logger.info(f"🔄 Comandos slash sincronizados/enviados para registro GLOBAL: {len(synced_global)} comandos.")
            for s_cmd in synced_global:
                logger.info(f"    Synced Global: '{s_cmd.name}', ID: {s_cmd.id}, Guild ID: {s_cmd.guild_id}")
        else:
            logger.warning("⚠️ A sincronização GLOBAL retornou None.")

    except nextcord.errors.ApplicationInvokeError as e:
        logger.error(f"❌ Erro de Invocação de Aplicação durante sincronização: {e.original if e.original else e}", exc_info=True)
    except nextcord.errors.HTTPException as e:
        logger.error(f"❌ Erro HTTP durante sincronização: Status {e.status}, Código {e.code}, Texto: {e.text}", exc_info=True)
    except Exception as e:
        logger.error(f"❌ Erro genérico ao sincronizar comandos slash: {e}", exc_info=True)
    logger.info("-> Sincronização de comandos concluída (ou falhou).")

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
