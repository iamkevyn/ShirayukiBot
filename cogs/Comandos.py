# /home/ubuntu/ShirayukiBot/cogs/Comandos.py
# Cog principal para comandos gerais, moderação básica e o sistema de ajuda.

import nextcord
from nextcord import Interaction, Embed, SlashOption, Color, Member, User, Role, TextChannel, Permissions, AuditLogAction, Forbidden, HTTPException, ButtonStyle, NotFound
from nextcord.ext import commands, application_checks
from nextcord.ui import View, Button, Select, Modal, TextInput
import time
import psutil # Para info do bot
import platform
import os
from datetime import datetime, timedelta, timezone
import asyncio
import random
import traceback # Para log de erros

# Importar helper de emojis
from utils.emojis import get_emoji

# ID do servidor fornecido pelo usuário para carregamento rápido de comandos
SERVER_ID = 1367345048458498219
# ID do Desenvolvedor (Kevyn) para receber DMs
DEVELOPER_ID = 1278842453159444582

# IDs de canais (Mantidos caso sejam usados para outras coisas, mas não para sugestões/bugs)
MOD_LOG_CHANNEL_ID = None    # Canal para logs de moderação

# --- Views e Modals --- 

# Modal para Sugestões
class SuggestionModal(Modal):
    def __init__(self, bot):
        super().__init__("💡 Enviar Sugestão")
        self.bot = bot

        self.suggestion_title = TextInput(
            label="Título da Sugestão",
            placeholder="Ex: Novo comando de música",
            min_length=5,
            max_length=100,
            required=True,
            style=nextcord.TextInputStyle.short
        )
        self.add_item(self.suggestion_title)

        self.suggestion_details = TextInput(
            label="Detalhes da Sugestão",
            placeholder="Descreva sua ideia em detalhes...",
            min_length=20,
            max_length=1000,
            required=True,
            style=nextcord.TextInputStyle.paragraph
        )
        self.add_item(self.suggestion_details)

    async def callback(self, interaction: Interaction):
        developer = await self.bot.fetch_user(DEVELOPER_ID)
        if not developer:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não foi possível encontrar o desenvolvedor para enviar a sugestão.", ephemeral=True)
            print(f"[ERRO SUGESTAO] Desenvolvedor com ID {DEVELOPER_ID} não encontrado.")
            return

        embed = Embed(
            title=f"💡 Nova Sugestão: {self.suggestion_title.value}",
            description=self.suggestion_details.value,
            color=Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=f"{interaction.user.display_name} ({interaction.user.id})", icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Enviado do servidor: {interaction.guild.name} ({interaction.guild.id})" if interaction.guild else "Enviado de DM")

        try:
            await developer.send(embed=embed)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Sua sugestão foi enviada com sucesso para o desenvolvedor!", ephemeral=True)
        except Forbidden:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não consegui enviar a DM para o desenvolvedor. Ele pode ter desativado DMs ou me bloqueado.", ephemeral=True)
            print(f"[ERRO SUGESTAO] Forbidden ao tentar enviar DM para {DEVELOPER_ID}")
        except Exception as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro inesperado ao enviar sua sugestão: {e}", ephemeral=True)
            print(f"[ERRO SUGESTAO] Erro inesperado: {e}")
            traceback.print_exc()

# Modal para Reportar Bugs
class BugReportModal(Modal):
    def __init__(self, bot):
        super().__init__("🐞 Reportar Bug")
        self.bot = bot

        self.bug_command = TextInput(
            label="Comando/Funcionalidade com Bug",
            placeholder="Ex: /apostar, Sistema de loja",
            max_length=100,
            required=True,
            style=nextcord.TextInputStyle.short
        )
        self.add_item(self.bug_command)

        self.bug_description = TextInput(
            label="Descrição do Bug",
            placeholder="Descreva o problema que você encontrou...",
            min_length=20,
            max_length=1000,
            required=True,
            style=nextcord.TextInputStyle.paragraph
        )
        self.add_item(self.bug_description)

        self.bug_reproduce = TextInput(
            label="Passos para Reproduzir (Opcional)",
            placeholder="Como posso fazer o bug acontecer?",
            max_length=500,
            required=False,
            style=nextcord.TextInputStyle.paragraph
        )
        self.add_item(self.bug_reproduce)

    async def callback(self, interaction: Interaction):
        developer = await self.bot.fetch_user(DEVELOPER_ID)
        if not developer:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não foi possível encontrar o desenvolvedor para enviar o report.", ephemeral=True)
            print(f"[ERRO BUGREPORT] Desenvolvedor com ID {DEVELOPER_ID} não encontrado.")
            return

        embed = Embed(
            title=f"🐞 Novo Report de Bug: {self.bug_command.value}",
            color=Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=f"{interaction.user.display_name} ({interaction.user.id})", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Descrição", value=self.bug_description.value, inline=False)
        if self.bug_reproduce.value:
            embed.add_field(name="Passos para Reproduzir", value=self.bug_reproduce.value, inline=False)
        embed.set_footer(text=f"Enviado do servidor: {interaction.guild.name} ({interaction.guild.id})" if interaction.guild else "Enviado de DM")

        try:
            await developer.send(embed=embed)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Seu report de bug foi enviado com sucesso para o desenvolvedor! Obrigado por ajudar a melhorar a Shirayuki!", ephemeral=True)
        except Forbidden:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não consegui enviar a DM para o desenvolvedor. Ele pode ter desativado DMs ou me bloqueado.", ephemeral=True)
            print(f"[ERRO BUGREPORT] Forbidden ao tentar enviar DM para {DEVELOPER_ID}")
        except Exception as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro inesperado ao enviar seu report: {e}", ephemeral=True)
            print(f"[ERRO BUGREPORT] Erro inesperado: {e}")
            traceback.print_exc()

# View para Confirmação de Moderação
class ConfirmModerationView(View):
    def __init__(self, bot, action: str, target: Member, moderator: Member, reason: str | None):
        super().__init__(timeout=60.0)
        self.bot = bot
        self.action = action # "kick", "ban", "mute", "unmute"
        self.target = target
        self.moderator = moderator
        self.reason = reason or "Motivo não especificado"
        self.confirmed = False

        # Adapta o label do botão
        action_labels = {
            "kick": "Confirmar Kick",
            "ban": "Confirmar Ban",
            "mute": "Confirmar Mute",
            "unmute": "Confirmar Unmute"
        }
        confirm_button = nextcord.utils.get(self.children, custom_id="confirm_mod_action")
        if confirm_button:
            confirm_button.label = action_labels.get(action, "Confirmar")

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Só o moderador que iniciou pode confirmar/cancelar
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')}{interaction.user.mention}, apenas {self.moderator.mention} pode confirmar esta ação.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if not self.confirmed:
            for item in self.children:
                item.disabled = True
            timeout_embed = Embed(title=f"Ação de Moderação Cancelada ({self.action.capitalize()})", description="Você demorou muito para confirmar.", color=Color.red())
            try:
                await self.message.edit(embed=timeout_embed, view=self)
            except (NotFound, AttributeError):
                pass

    @nextcord.ui.button(label="Confirmar", style=ButtonStyle.danger, custom_id="confirm_mod_action") # Label será alterado no __init__
    async def confirm_button(self, button: Button, interaction: Interaction):
        self.confirmed = True
        for item in self.children:
            item.disabled = True
        # Não edita a mensagem aqui ainda, espera a ação ser concluída

        # Executa a ação de moderação
        success = False
        error_message = None
        log_embed = None

        try:
            mod_reason = f"{self.reason} (Moderador: {self.moderator.name}#{self.moderator.discriminator} [{self.moderator.id}])"
            if self.action == "kick":
                await self.target.kick(reason=mod_reason)
                success = True
            elif self.action == "ban":
                # TODO: Adicionar opção de dias para deletar mensagens (days_to_delete_messages)
                await self.target.ban(reason=mod_reason)
                success = True
            # TODO: Implementar Mute/Unmute (requer gerenciamento de cargo ou timeout do Discord)
            # elif self.action == "mute":
            #     # Lógica para adicionar cargo de mute ou usar timeout
            #     success = True
            # elif self.action == "unmute":
            #     # Lógica para remover cargo de mute ou timeout
            #     success = True
            else:
                 error_message = "Ação de moderação desconhecida."

        except Forbidden:
            error_message = f"Não tenho permissão para {self.action} {self.target.mention}. Verifique minhas permissões e a hierarquia de cargos."
        except HTTPException as e:
            error_message = f"Ocorreu um erro de API ao tentar {self.action} {self.target.mention}: {e}"
        except Exception as e:
            error_message = f"Ocorreu um erro inesperado ao tentar {self.action} {self.target.mention}: {e}"
            print(f"[ERRO MOD] Erro ao {self.action} {self.target.id}: {e}")
            traceback.print_exc()

        # Prepara o embed de resultado/log
        if success:
            result_embed = Embed(
                title=f"{get_emoji(self.bot, 'hammer')} Ação Concluída: {self.action.capitalize()} de {self.target.name}",
                description=f"**Usuário:** {self.target.mention} (`{self.target.id}`)\n**Moderador:** {self.moderator.mention}\n**Motivo:** {self.reason}",
                color=Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed = result_embed # Usa o mesmo embed para o log
        else:
            result_embed = Embed(
                title=f"{get_emoji(self.bot, 'sad')}{self.action.capitalize()} Falhou",
                description=error_message or "Erro desconhecido.",
                color=Color.red()
            )

        # Edita a mensagem de confirmação com o resultado
        # Usar followup.edit_message se a resposta inicial foi deferida, senão edit_original_message
        try:
            await interaction.response.edit_message(embed=result_embed, view=None)
        except Exception as e:
             print(f"[WARN MOD] Falha ao editar mensagem de confirmação: {e}")
             # Tenta enviar como nova mensagem se a edição falhar
             try:
                 await interaction.followup.send(embed=result_embed, ephemeral=True)
             except Exception as e2:
                 print(f"[ERRO MOD] Falha ao enviar followup após falha na edição: {e2}")

        # Envia o log se a ação foi bem-sucedida e o canal de log está configurado
        if success and MOD_LOG_CHANNEL_ID:
            log_channel = interaction.guild.get_channel(MOD_LOG_CHANNEL_ID)
            if log_channel and isinstance(log_channel, TextChannel):
                try:
                    await log_channel.send(embed=log_embed)
                except Forbidden:
                    print(f"[ERRO MODLOG] Sem permissão para enviar log no canal {MOD_LOG_CHANNEL_ID}")
                except Exception as e:
                    print(f"[ERRO MODLOG] Erro ao enviar log: {e}")
            else:
                print(f"[AVISO MODLOG] Canal de log {MOD_LOG_CHANNEL_ID} não encontrado ou inválido.")

        self.stop()

    @nextcord.ui.button(label="Cancelar", style=ButtonStyle.grey, custom_id="cancel_mod_action")
    async def cancel_button(self, button: Button, interaction: Interaction):
        self.confirmed = False
        for item in self.children:
            item.disabled = True
        cancel_embed = Embed(title=f"Ação Cancelada ({self.action.capitalize()})", description=f"A ação de {self.action} em {self.target.mention} foi cancelada.", color=Color.light_grey())
        await interaction.response.edit_message(embed=cancel_embed, view=self)
        self.stop()

# --- View para o Comando Help --- 
class HelpView(View):
    def __init__(self, bot: commands.Bot, initial_interaction: Interaction):
        super().__init__(timeout=180) # Timeout de 3 minutos
        self.bot = bot
        self.initial_interaction = initial_interaction # Usuário que chamou o /ajuda
        self.current_cog = "help_home" # Começa na home
        self._update_buttons()

    def _update_buttons(self):
        """Atualiza a aparência dos botões (desabilita o botão da categoria atual)."""
        for child in self.children:
            if isinstance(child, Button):
                # Re-habilita todos primeiro
                child.disabled = False
                # Define estilo padrão
                if child.custom_id == "help_home":
                    child.style = ButtonStyle.primary
                elif child.custom_id == "help_musica":
                     child.style = ButtonStyle.secondary # Música desativada, estilo secundário
                elif child.custom_id in ["help_economia", "help_jogos"]:
                     child.style = ButtonStyle.green
                else:
                     child.style = ButtonStyle.secondary

                # Desabilita e muda estilo do botão atual
                if child.custom_id == self.current_cog:
                    child.disabled = True
                    child.style = ButtonStyle.primary # Destaca o botão ativo

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Apenas o usuário que iniciou o comando pode interagir
        if interaction.user.id != self.initial_interaction.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')}{interaction.user.mention}, apenas {self.initial_interaction.user.mention} pode usar estes botões.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            # Tenta editar a mensagem original para indicar que expirou
            await self.initial_interaction.edit_original_message(content="*Esta sessão de ajuda expirou.*", view=self)
        except (NotFound, HTTPException):
            pass # Mensagem pode ter sido deletada

    async def _get_cog_help_embed(self, cog_name: str) -> Embed:
        """Cria o Embed de ajuda para uma cog específica."""
        cog = self.bot.get_cog(cog_name)

        # Mapeamento de Nomes Amigáveis e Emojis
        cog_display_info = {
            "Comandos": {"emoji": get_emoji(self.bot, 'gear'), "color": Color.blue()},
            "Economia": {"emoji": get_emoji(self.bot, 'money'), "color": Color.gold()},
            "Informacoes": {"emoji": get_emoji(self.bot, 'info'), "color": Color.teal()},
            "Interacoes": {"emoji": get_emoji(self.bot, 'happy_flower'), "color": Color.magenta()},
            "Jogos": {"emoji": get_emoji(self.bot, 'dice'), "color": Color.green()},
            "Utilitarios": {"emoji": get_emoji(self.bot, 'tool'), "color": Color.orange()},
            "Musica": {"emoji": get_emoji(self.bot, 'music'), "color": Color.red()}
        }
        display_info = cog_display_info.get(cog_name, {"emoji": "❓", "color": Color.default()})
        friendly_name = cog_name.replace("Informacoes", "Informações").replace("Interacoes", "Interações")

        embed = Embed(title=f"{display_info['emoji']} Ajuda - {friendly_name}", color=display_info['color'])

        if not cog and cog_name != "Musica": # Permite mostrar ajuda da música mesmo desativada
            embed.description = f"{get_emoji(self.bot, 'sad')} Categoria não encontrada ou desativada."
            return embed

        commands_list = []
        # Prioriza application_commands (slash commands)
        if hasattr(cog, 'get_application_commands'):
            app_commands = cog.get_application_commands()
            for cmd in sorted(app_commands, key=lambda c: c.name):
                # Ignora subcomandos aqui, eles são parte do comando pai
                if cmd.parent_command:
                    continue
                desc = cmd.description or "Sem descrição."
                commands_list.append(f"</{cmd.qualified_name}:{cmd.command_ids[SERVER_ID] if SERVER_ID in cmd.command_ids else list(cmd.command_ids.values())[0]}> - {desc}")

        # Adiciona comandos de texto se existirem (menos comum com slash)
        if hasattr(cog, 'get_commands'):
            text_commands = cog.get_commands()
            for cmd in sorted(text_commands, key=lambda c: c.name):
                if cmd.hidden:
                    continue
                desc = cmd.short_doc or cmd.help or "Sem descrição."
                aliases = f" (Aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                commands_list.append(f"`{self.bot.command_prefix}{cmd.name}{aliases}` - {desc}")

        if cog_name == "Musica":
             embed.description = (f"{get_emoji(self.bot, 'warn')} A categoria de música está temporariamente desativada.\n\n"
                                f"Quando ativa, os comandos disponíveis seriam:\n"
                                f"</play:0> - Toca uma música.\n"
                                f"</pause:0> - Pausa a música atual.\n"
                                f"</resume:0> - Retoma a música pausada.\n"
                                f"</skip:0> - Pula para a próxima música.\n"
                                f"</queue:0> - Mostra a fila de músicas.\n"
                                f"</stop:0> - Para a música e limpa a fila.")
        elif commands_list:
            embed.description = "\n".join(commands_list)
        else:
            embed.description = f"{get_emoji(self.bot, 'thinking')} Nenhum comando encontrado nesta categoria."

        return embed

    async def _get_home_embed(self) -> Embed:
        """Cria o Embed inicial de ajuda (home)."""
        embed = Embed(
            title=f"{get_emoji(self.bot, 'book', default='📖')} Central de Ajuda da Shirayuki",
            description=f"Olá! Sou a Shirayuki {get_emoji(self.bot, 'happy_flower')}. Use os botões abaixo para navegar pelas categorias de comandos.",
            color=Color.purple()
        )
        # Adiciona informações gerais ou links úteis se desejar
        # embed.add_field(name="Links Úteis", value="[Convite](URL_CONVITE) | [Suporte](URL_SUPORTE)", inline=False)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        return embed

    async def _update_help(self, interaction: Interaction, cog_id: str):
        """Atualiza a mensagem de ajuda com o embed da categoria selecionada."""
        self.current_cog = cog_id
        self._update_buttons()

        if cog_id == "help_home":
            embed = await self._get_home_embed()
        else:
            cog_name = cog_id.replace("help_", "").capitalize()
            # Ajustes para nomes de cogs específicos
            if cog_name == "Informacoes": cog_name = "Informacoes"
            if cog_name == "Interacoes": cog_name = "Interacoes"
            embed = await self._get_cog_help_embed(cog_name)

        await interaction.response.edit_message(embed=embed, view=self)

    # --- Botões --- 
    @nextcord.ui.button(label="Início", style=ButtonStyle.primary, custom_id="help_home")
    async def home_button(self, button: Button, interaction: Interaction):
        await self._update_help(interaction, "help_home")

    @nextcord.ui.button(label="Comandos", style=ButtonStyle.secondary, custom_id="help_comandos")
    async def commands_button(self, button: Button, interaction: Interaction):
        await self._update_help(interaction, "help_comandos")

    @nextcord.ui.button(label="Economia", style=ButtonStyle.green, custom_id="help_economia")
    async def economy_button(self, button: Button, interaction: Interaction):
        await self._update_help(interaction, "help_economia")

    @nextcord.ui.button(label="Informações", style=ButtonStyle.secondary, custom_id="help_informacoes")
    async def info_button(self, button: Button, interaction: Interaction):
        await self._update_help(interaction, "help_informacoes")

    @nextcord.ui.button(label="Interações", style=ButtonStyle.secondary, custom_id="help_interacoes")
    async def interactions_button(self, button: Button, interaction: Interaction):
        await self._update_help(interaction, "help_interacoes")

    # Nova linha de botões
    @nextcord.ui.button(label="Jogos", style=ButtonStyle.green, custom_id="help_jogos", row=1)
    async def games_button(self, button: Button, interaction: Interaction):
        await self._update_help(interaction, "help_jogos")

    @nextcord.ui.button(label="Utilitários", style=ButtonStyle.secondary, custom_id="help_utilitarios", row=1)
    async def utils_button(self, button: Button, interaction: Interaction):
        await self._update_help(interaction, "help_utilitarios")

    @nextcord.ui.button(label="Música", style=ButtonStyle.red, custom_id="help_musica", row=1)
    async def music_button(self, button: Button, interaction: Interaction):
        await self._update_help(interaction, "help_musica")

# --- Cog Principal --- 
class Comandos(commands.Cog):
    """Comandos gerais, moderação básica e o sistema de ajuda interativo."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] Cog Comandos carregada.')

    # --- Comandos Slash --- 

    @nextcord.slash_command(name="ajuda", description="Mostra a central de ajuda interativa da Shirayuki.", guild_ids=[SERVER_ID])
    async def help_command(self, interaction: Interaction):
        """Mostra a central de ajuda interativa da Shirayuki."""
        view = HelpView(self.bot, interaction)
        initial_embed = await view._get_home_embed()
        await interaction.response.send_message(embed=initial_embed, view=view, ephemeral=True)

    @nextcord.slash_command(name="ping", description="Verifica a latência da Shirayuki.", guild_ids=[SERVER_ID])
    async def ping(self, interaction: Interaction):
        """Verifica a latência da Shirayuki."""
        latency = self.bot.latency
        embed = Embed(title=f"{get_emoji(self.bot, 'ping_pong', default='🏓')} Pong!", description=f"Latência: `{latency * 1000:.2f}ms`", color=Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="botinfo", description="Mostra informações sobre a Shirayuki.", guild_ids=[SERVER_ID])
    async def botinfo(self, interaction: Interaction):
        """Mostra informações sobre a Shirayuki."""
        process = psutil.Process(os.getpid())
        mem_usage = process.memory_info().rss / (1024 * 1024) # Em MB
        cpu_usage = psutil.cpu_percent(interval=0.1)
        uptime_seconds = time.time() - self.start_time
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))

        embed = Embed(title=f"{get_emoji(self.bot, 'info', default='ℹ️')} Informações da Shirayuki", color=Color.purple())
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Desenvolvedor", value=f"<@{DEVELOPER_ID}>", inline=True)
        embed.add_field(name="Versão Nextcord", value=f"`{nextcord.__version__}`", inline=True)
        embed.add_field(name="Versão Python", value=f"`{platform.python_version()}`", inline=True)
        embed.add_field(name="Servidores", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="Usuários", value=f"`{len(self.bot.users)}`", inline=True)
        embed.add_field(name="Latência", value=f"`{self.bot.latency * 1000:.2f}ms`", inline=True)
        embed.add_field(name="Uso de CPU", value=f"`{cpu_usage:.1f}%`", inline=True)
        embed.add_field(name="Uso de RAM", value=f"`{mem_usage:.2f} MB`", inline=True)
        embed.add_field(name="Tempo Online", value=f"`{uptime_str}`", inline=True)
        embed.set_footer(text=f"ID: {self.bot.user.id} | Criada em: {self.bot.user.created_at.strftime('%d/%m/%Y')}")

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="sugestao", description="Envia uma sugestão para o desenvolvedor.", guild_ids=[SERVER_ID])
    async def suggest(self, interaction: Interaction):
        """Abre um formulário para enviar uma sugestão para o desenvolvedor.
        A sugestão será enviada por DM para o desenvolvedor (Kevyn).
        """
        modal = SuggestionModal(self.bot)
        await interaction.response.send_modal(modal)

    @nextcord.slash_command(name="bugreport", description="Reporta um bug encontrado na Shirayuki.", guild_ids=[SERVER_ID])
    async def bugreport(self, interaction: Interaction):
        """Abre um formulário para reportar um bug.
        O report será enviado por DM para o desenvolvedor (Kevyn).
        """
        modal = BugReportModal(self.bot)
        await interaction.response.send_modal(modal)

    # --- Comandos de Moderação (Básicos) ---
    # Estes comandos precisam de permissões adequadas

    @nextcord.slash_command(name="kick", description="Expulsa um membro do servidor.", guild_ids=[SERVER_ID])
    @application_checks.has_permissions(kick_members=True)
    @application_checks.bot_has_permissions(kick_members=True)
    async def kick_member(self, interaction: Interaction,
                        membro: Member = SlashOption(description="O membro a ser expulso.", required=True),
                        motivo: str = SlashOption(description="O motivo da expulsão.", required=False, default="Motivo não especificado.")):
        """Expulsa um membro do servidor (requer permissão)."""
        if membro == interaction.user:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode se expulsar.", ephemeral=True)
            return
        if membro.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode expulsar um membro com cargo igual ou superior ao seu.", ephemeral=True)
            return
        if membro.top_role >= interaction.guild.me.top_role:
             await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não posso expulsar um membro com cargo igual ou superior ao meu.", ephemeral=True)
             return

        embed = Embed(title=f"Confirmar Expulsão de {membro.name}",
                      description=f"Você tem certeza que deseja expulsar {membro.mention}?\n**Motivo:** {motivo}",
                      color=Color.orange())
        view = ConfirmModerationView(self.bot, "kick", membro, interaction.user, motivo)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_message()

    @nextcord.slash_command(name="ban", description="Bane um membro do servidor.", guild_ids=[SERVER_ID])
    @application_checks.has_permissions(ban_members=True)
    @application_checks.bot_has_permissions(ban_members=True)
    async def ban_member(self, interaction: Interaction,
                       membro: Member = SlashOption(description="O membro a ser banido.", required=True),
                       motivo: str = SlashOption(description="O motivo do banimento.", required=False, default="Motivo não especificado.")):
        """Bane um membro do servidor (requer permissão)."""
        if membro == interaction.user:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode se banir.", ephemeral=True)
            return
        if membro.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode banir um membro com cargo igual ou superior ao seu.", ephemeral=True)
            return
        if membro.top_role >= interaction.guild.me.top_role:
             await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não posso banir um membro com cargo igual ou superior ao meu.", ephemeral=True)
             return

        embed = Embed(title=f"Confirmar Banimento de {membro.name}",
                      description=f"Você tem certeza que deseja banir {membro.mention}?\n**Motivo:** {motivo}",
                      color=Color.red())
        view = ConfirmModerationView(self.bot, "ban", membro, interaction.user, motivo)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_message()

    # TODO: Adicionar comandos /mute e /unmute quando a funcionalidade for implementada
    # TODO: Adicionar comando /clear para limpar mensagens

    # --- Error Handling Específico da Cog ---
    @kick_member.error
    @ban_member.error
    async def moderation_error(self, interaction: Interaction, error):
        if isinstance(error, application_checks.ApplicationMissingPermissions):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'no_entry')} Você não tem permissão para usar este comando (`{', '.join(error.missing_permissions)}`).", ephemeral=True)
        elif isinstance(error, application_checks.ApplicationBotMissingPermissions):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Eu não tenho permissão para executar esta ação (`{', '.join(error.missing_permissions)}`). Peça a um administrador para verificar minhas permissões.", ephemeral=True)
        else:
            # Log genérico para outros erros
            print(f"Erro não tratado em comando de moderação: {error}")
            traceback.print_exc()
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro inesperado ao processar o comando.", ephemeral=True)

# Função setup para carregar a cog
def setup(bot: commands.Bot):
    bot.add_cog(Comandos(bot))
