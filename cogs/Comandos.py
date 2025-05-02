# /home/ubuntu/ShirayukiBot/cogs/Comandos.py
# Cog principal para comandos gerais, moderação básica e o sistema de ajuda.

import nextcord
from nextcord import Interaction, Embed, SlashOption, Color, Member, User, Role, TextChannel, Permissions, AuditLogAction, Forbidden, HTTPException, ButtonStyle
from nextcord.ext import commands, application_checks
from nextcord.ui import View, Button, Select, Modal, TextInput
import time
import psutil # Para info do bot
import platform
import os
from datetime import datetime, timedelta, timezone
import asyncio
import random

# Importar helper de emojis
from utils.emojis import get_emoji

# ID do servidor fornecido pelo usuário para carregamento rápido de comandos
SERVER_ID = 1367345048458498219

# IDs de canais (Substituir pelos IDs reais, se aplicável)
SUGGESTION_CHANNEL_ID = None # Canal para enviar sugestões
BUG_REPORT_CHANNEL_ID = None # Canal para enviar reports de bugs
MOD_LOG_CHANNEL_ID = None    # Canal para logs de moderação

# --- Views e Modals --- 

# Modal para Sugestões
class SuggestionModal(Modal):
    def __init__(self, bot, suggestion_channel_id):
        super().__init__("💡 Enviar Sugestão")
        self.bot = bot
        self.suggestion_channel_id = suggestion_channel_id

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
        if not self.suggestion_channel_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} O canal de sugestões não foi configurado pelo administrador.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.suggestion_channel_id)
        if not channel or not isinstance(channel, TextChannel):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} O canal de sugestões configurado é inválido ou não encontrado.", ephemeral=True)
            return

        embed = Embed(
            title=f"💡 Nova Sugestão: {self.suggestion_title.value}",
            description=self.suggestion_details.value,
            color=Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"ID do Usuário: {interaction.user.id}")

        try:
            msg = await channel.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Sua sugestão foi enviada com sucesso para {channel.mention}!", ephemeral=True)
        except Forbidden:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não tenho permissão para enviar mensagens ou adicionar reações no canal {channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro ao enviar sua sugestão: {e}", ephemeral=True)

# Modal para Reportar Bugs
class BugReportModal(Modal):
    def __init__(self, bot, bug_report_channel_id):
        super().__init__("🐞 Reportar Bug")
        self.bot = bot
        self.bug_report_channel_id = bug_report_channel_id

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
        if not self.bug_report_channel_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} O canal de reports de bug não foi configurado.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.bug_report_channel_id)
        if not channel or not isinstance(channel, TextChannel):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} O canal de reports de bug configurado é inválido.", ephemeral=True)
            return

        embed = Embed(
            title=f"🐞 Novo Report de Bug: {self.bug_command.value}",
            color=Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Descrição", value=self.bug_description.value, inline=False)
        if self.bug_reproduce.value:
            embed.add_field(name="Passos para Reproduzir", value=self.bug_reproduce.value, inline=False)
        embed.set_footer(text=f"ID do Usuário: {interaction.user.id}")

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Seu report de bug foi enviado com sucesso para {channel.mention}! Obrigado por ajudar a melhorar a Shirayuki!", ephemeral=True)
        except Forbidden:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não tenho permissão para enviar mensagens no canal {channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro ao enviar seu report: {e}", ephemeral=True)

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
        self.confirm_button.label = action_labels.get(action, "Confirmar")

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Só o moderador que iniciou pode confirmar/cancelar
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Apenas {self.moderator.mention} pode confirmar esta ação.", ephemeral=True)
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

    @nextcord.ui.button(label="Confirmar", style=ButtonStyle.danger) # Label será alterado no __init__
    async def confirm_button(self, button: Button, interaction: Interaction):
        self.confirmed = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self) # Desabilita botões imediatamente

        # Executa a ação de moderação
        success = False
        error_message = None
        log_embed = None

        try:
            if self.action == "kick":
                await self.target.kick(reason=f"{self.reason} (Moderador: {self.moderator.name}#{self.moderator.discriminator})")
                success = True
            elif self.action == "ban":
                await self.target.ban(reason=f"{self.reason} (Moderador: {self.moderator.name}#{self.moderator.discriminator})")
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
                title=f"{get_emoji(self.bot, 'sad')} Falha na Ação: {self.action.capitalize()} de {self.target.name}",
                description=error_message or "Erro desconhecido.",
                color=Color.red()
            )

        # Edita a mensagem de confirmação com o resultado
        await interaction.edit_original_message(embed=result_embed, view=None)

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

    @ui.button(label="Cancelar", style=ButtonStyle.grey)
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
        self.current_cog = None # Para saber qual embed está sendo mostrado
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
                     child.style = ButtonStyle.red
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
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Apenas {self.initial_interaction.user.mention} pode usar estes botões.", ephemeral=True)
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
            "Comandos": {"emoji": get_emoji(self.bot, 'gear', default='⚙️'), "color": Color.blue()},
            "Economia": {"emoji": get_emoji(self.bot, 'money', default='💰'), "color": Color.gold()},
            "Informacoes": {"emoji": get_emoji(self.bot, 'info', default='ℹ️'), "color": Color.teal()},
            "Interacoes": {"emoji": get_emoji(self.bot, 'happy_flower', default='🌸'), "color": Color.magenta()},
            "Jogos": {"emoji": get_emoji(self.bot, 'dice', default='🎲'), "color": Color.green()},
            "Utilitarios": {"emoji": get_emoji(self.bot, 'tool', default='🛠️'), "color": Color.orange()},
            "Musica": {"emoji": get_emoji(self.bot, 'music', default='🎵'), "color": Color.red()}
        }
        display_info = cog_display_info.get(cog_name, {"emoji": "❓", "color": Color.default()})
        friendly_name = cog_name.replace("Informacoes", "Informações").replace("Interacoes", "Interações")

        embed = Embed(title=f"{display_info['emoji']} Ajuda - {friendly_name}", color=display_info['color'])

        if not cog:
            embed.description = f"{get_emoji(self.bot, 'sad')} Categoria não encontrada ou desativada."
            if cog_name == "Musica": # Mensagem específica para música desativada
                 embed.description += f"\n\n{get_emoji(self.bot, 'warn')} A categoria de música está temporariamente indisponível."
            return embed

        commands_list = []
        # Prioriza slash commands
        app_commands = sorted(cog.get_application_commands(), key=lambda c: c.name)
        for command in app_commands:
            # Tenta obter a descrição completa (incluindo subcomandos se houver)
            desc = command.description or "Sem descrição."
            # if hasattr(command, 'options') and command.options:
            #     opts = " ".join([f"`<{opt.name}>`" for opt in command.options])
            #     commands_list.append(f"</{command.name}:{command.id}> {opts}\n* {desc}*" )
            # else:
            commands_list.append(f"</{command.name}:{command.id}> - *{desc}*" )

        if not commands_list:
            embed.description = f"{get_emoji(self.bot, 'info')} Nenhum comando de barra (/) encontrado nesta categoria."
        else:
            embed.description = "\n".join(commands_list)
            embed.set_footer(text="Use / seguido do nome do comando para executá-lo.")
            
        # Adiciona docstring da cog se existir
        if cog.__doc__:
             embed.add_field(name="Sobre", value=f"```{cog.__doc__}```", inline=False)

        return embed

    async def _show_help(self, interaction: Interaction, cog_id: str | None):
        """Atualiza a mensagem com o embed de ajuda apropriado."""
        self.current_cog = cog_id
        self._update_buttons()
        
        if cog_id == "help_home" or cog_id is None:
            embed = self._get_home_embed()
        else:
            cog_name = cog_id.replace("help_", "").capitalize()
            # Ajustes de nome
            if cog_name == "Informacoes": cog_name = "Informacoes"
            if cog_name == "Interacoes": cog_name = "Interacoes"
            embed = await self._get_cog_help_embed(cog_name)
            
        await interaction.response.edit_message(embed=embed, view=self)

    def _get_home_embed(self) -> Embed:
        """Cria o Embed inicial da ajuda."""
        embed = Embed(
            title=f"{get_emoji(self.bot, 'question', default='❓')} Ajuda - ShirayukiBot",
            description=f"Olá {self.initial_interaction.user.mention}! {get_emoji(self.bot, 'happy_flower', default='😊')}\nSou a Shirayuki, sua assistente para diversas tarefas!\n\nUse os botões abaixo para navegar pelas categorias de comandos.",
            color=Color.blue()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Selecione uma categoria para ver os comandos.")
        return embed

    # --- Botões --- 
    @ui.button(label="Início", custom_id="help_home", style=ButtonStyle.primary, row=0)
    async def show_home(self, button: Button, interaction: Interaction):
        await self._show_help(interaction, "help_home")
        
    @ui.button(label="Comandos", custom_id="help_comandos", style=ButtonStyle.secondary, row=1)
    async def show_comandos(self, button: Button, interaction: Interaction):
        await self._show_help(interaction, "help_comandos")

    @ui.button(label="Economia", custom_id="help_economia", style=ButtonStyle.green, row=1)
    async def show_economia(self, button: Button, interaction: Interaction):
        await self._show_help(interaction, "help_economia")

    @ui.button(label="Informações", custom_id="help_informacoes", style=ButtonStyle.secondary, row=1)
    async def show_informacoes(self, button: Button, interaction: Interaction):
        await self._show_help(interaction, "help_informacoes")

    @ui.button(label="Interações", custom_id="help_interacoes", style=ButtonStyle.secondary, row=2)
    async def show_interacoes(self, button: Button, interaction: Interaction):
        await self._show_help(interaction, "help_interacoes")

    @ui.button(label="Jogos", custom_id="help_jogos", style=ButtonStyle.green, row=2)
    async def show_jogos(self, button: Button, interaction: Interaction):
        await self._show_help(interaction, "help_jogos")

    @ui.button(label="Utilitários", custom_id="help_utilitarios", style=ButtonStyle.secondary, row=2)
    async def show_utilitarios(self, button: Button, interaction: Interaction):
        await self._show_help(interaction, "help_utilitarios")

    @ui.button(label="Música", custom_id="help_musica", style=ButtonStyle.red, row=3)
    async def show_musica(self, button: Button, interaction: Interaction):
        await self._show_help(interaction, "help_musica")

# --- Cog Comandos --- 
class Comandos(commands.Cog):
    """Comandos gerais, moderação básica, sugestões, reports e ajuda interativa."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
        print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] Cog Comandos carregada.")

    # --- Comando de Ajuda --- 
    @nextcord.slash_command(
        # guild_ids=[SERVER_ID], # Comentado para ser global, mas pode ser descomentado para teste rápido
        name="ajuda",
        description="Mostra a lista de comandos disponíveis."
    )
    async def ajuda(self, interaction: Interaction):
        """Exibe um painel de ajuda interativo com botões para categorias de comandos."""
        view = HelpView(self.bot, interaction)
        embed = view._get_home_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_message() # Guarda a mensagem para editar no timeout

    # --- Comandos Gerais --- 
    @nextcord.slash_command(guild_ids=[SERVER_ID], name="ping", description="Testa a latência do bot.")
    async def ping(self, interaction: Interaction):
        """Verifica a latência da API do Discord e o tempo de resposta do bot."""
        start_time = time.monotonic()
        # Envia uma mensagem inicial para medir o tempo de resposta completo
        await interaction.response.defer(ephemeral=True)
        end_time = time.monotonic()
        latency_api = round(self.bot.latency * 1000)
        latency_response = round((end_time - start_time) * 1000)
        
        embed = Embed(title=f"{get_emoji(self.bot, 'ping_pong', default='🏓')} Pong!", color=Color.blue())
        embed.add_field(name="Latência da API", value=f"`{latency_api}ms`", inline=True)
        embed.add_field(name="Latência de Resposta", value=f"`{latency_response}ms`", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="botinfo", description="Mostra informações sobre mim!")
    async def botinfo(self, interaction: Interaction):
        """Exibe informações detalhadas sobre o bot Shirayuki."""
        await interaction.response.defer()
        
        app_info = await self.bot.application_info()
        owner = app_info.owner
        
        # Uptime
        current_time = time.time()
        difference = int(round(current_time - self.start_time))
        uptime_str = str(timedelta(seconds=difference))
        
        # Uso de Recursos
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / (1024 * 1024) # Em MB
        cpu_usage = process.cpu_percent() / psutil.cpu_count()
        
        # Contagens
        total_servers = len(self.bot.guilds)
        total_users = sum(guild.member_count for guild in self.bot.guilds if guild.member_count is not None)
        total_commands = len(self.bot.get_all_application_commands())
        
        embed = Embed(
            title=f"{get_emoji(self.bot, 'info', default='ℹ️')} Informações sobre {self.bot.user.name}",
            description=f"Uma bot multifuncional criada com carinho. {get_emoji(self.bot, 'happy_flower')}",
            color=Color.purple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        embed.add_field(name="Desenvolvedor", value=f"{owner.mention} (`{owner.id}`)", inline=True)
        embed.add_field(name="Versão Nextcord", value=f"`{nextcord.__version__}`", inline=True)
        embed.add_field(name="Versão Python", value=f"`{platform.python_version()}`", inline=True)
        
        embed.add_field(name="Servidores", value=f"`{total_servers}`", inline=True)
        embed.add_field(name="Usuários Totais", value=f"`{total_users}`", inline=True)
        embed.add_field(name="Comandos (/)", value=f"`{total_commands}`", inline=True)
        
        embed.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="Uso de CPU", value=f"`{cpu_usage:.2f}%`", inline=True)
        embed.add_field(name="Uso de RAM", value=f"`{memory_usage:.2f} MB`", inline=True)
        
        # Links Úteis (se houver)
        # embed.add_field(name="Links", value="[Convite](link_convite) | [Suporte](link_suporte) | [Código](link_codigo)", inline=False)
        
        await interaction.followup.send(embed=embed)

    # --- Comandos de Utilidade/Feedback --- 
    @nextcord.slash_command(guild_ids=[SERVER_ID], name="sugerir", description="Envie uma sugestão para melhorar o bot.")
    async def sugerir(self, interaction: Interaction):
        """Abre um formulário para o usuário enviar uma sugestão."""
        modal = SuggestionModal(self.bot, SUGGESTION_CHANNEL_ID)
        await interaction.response.send_modal(modal)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="reportarbug", description="Reporte um bug encontrado no bot.")
    async def reportarbug(self, interaction: Interaction):
        """Abre um formulário para o usuário reportar um bug."""
        modal = BugReportModal(self.bot, BUG_REPORT_CHANNEL_ID)
        await interaction.response.send_modal(modal)

    # --- Comandos de Moderação Básica --- 
    # Decorator para verificar permissões de moderação
    def check_mod_permissions(**perms):
        async def predicate(interaction: Interaction) -> bool:
            if not isinstance(interaction.user, Member):
                 await interaction.response.send_message(f"{get_emoji(interaction.client, 'warn')} Este comando só pode ser usado em servidores.", ephemeral=True)
                 return False
                 
            user_perms = interaction.channel.permissions_for(interaction.user)
            missing_perms = [perm for perm, value in perms.items() if value and not getattr(user_perms, perm, False)]
            
            if not missing_perms:
                return True
            else:
                perms_str = ", ".join([f"`{p.replace('_', ' ').title()}`" for p in missing_perms])
                await interaction.response.send_message(f"{get_emoji(interaction.client, 'sad')} Você não tem permissão para usar este comando. Permissões faltando: {perms_str}", ephemeral=True)
                return False
        return application_checks.check(predicate)
        
    # Decorator para verificar se o bot pode realizar a ação
    def check_bot_permissions(**perms):
         async def predicate(interaction: Interaction) -> bool:
             if not interaction.guild:
                 # Não deveria acontecer com check_mod_permissions, mas por segurança
                 await interaction.response.send_message(f"{get_emoji(interaction.client, 'warn')} Este comando só pode ser usado em servidores.", ephemeral=True)
                 return False
                 
             bot_member = interaction.guild.me
             bot_perms = interaction.channel.permissions_for(bot_member)
             missing_perms = [perm for perm, value in perms.items() if value and not getattr(bot_perms, perm, False)]
             
             if not missing_perms:
                 return True
             else:
                 perms_str = ", ".join([f"`{p.replace('_', ' ').title()}`" for p in missing_perms])
                 await interaction.response.send_message(f"{get_emoji(interaction.client, 'sad')} Eu não tenho permissão para realizar esta ação. Preciso de: {perms_str}", ephemeral=True)
                 return False
         return application_checks.check(predicate)
         
    # Decorator para verificar hierarquia de cargos
    def check_role_hierarchy():
        async def predicate(interaction: Interaction) -> bool:
            if not isinstance(interaction.user, Member) or not interaction.guild:
                return False # Já tratado por outros checks
                
            # Assume que o alvo é o primeiro argumento do tipo Member
            target_member = None
            for option_name, option_value in interaction.data.get('options', {}).items():
                 # Precisa buscar o membro pelo ID fornecido nas opções
                 if 'value' in option_value and isinstance(option_value['value'], str): # IDs são strings
                     try:
                         member_id = int(option_value['value'])
                         resolved_member = interaction.guild.get_member(member_id)
                         if resolved_member:
                             target_member = resolved_member
                             break # Encontrou o alvo
                     except (ValueError, TypeError):
                         continue # Não é um ID de membro válido
                         
            if not target_member:
                 # Se não achar o alvo (pode ser comando sem alvo ou erro), permite prosseguir (outros checks pegarão)
                 return True 
                 
            moderator = interaction.user
            bot_member = interaction.guild.me

            # Verifica se o moderador está tentando agir em si mesmo
            if moderator.id == target_member.id:
                await interaction.response.send_message(f"{get_emoji(interaction.client, 'warn')} Você não pode usar comandos de moderação em si mesmo.", ephemeral=True)
                return False

            # Verifica hierarquia: Moderador vs Alvo
            if moderator.top_role <= target_member.top_role and interaction.guild.owner_id != moderator.id:
                await interaction.response.send_message(f"{get_emoji(interaction.client, 'sad')} Você não pode moderar {target_member.mention} porque o cargo dele(a) é igual ou superior ao seu.", ephemeral=True)
                return False

            # Verifica hierarquia: Bot vs Alvo
            if bot_member.top_role <= target_member.top_role:
                await interaction.response.send_message(f"{get_emoji(interaction.client, 'sad')} Eu não posso moderar {target_member.mention} porque o cargo dele(a) é igual ou superior ao meu.", ephemeral=True)
                return False

            return True
        return application_checks.check(predicate)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="kick", description="Expulsa um usuário do servidor.")
    @check_mod_permissions(kick_members=True)
    @check_bot_permissions(kick_members=True)
    @check_role_hierarchy()
    async def kick(self, interaction: Interaction, 
                 usuario: Member = SlashOption(description="O usuário a ser expulso"), 
                 motivo: str = SlashOption(description="O motivo da expulsão (opcional)", required=False)):
        """Expulsa um membro do servidor com confirmação."""
        view = ConfirmModerationView(self.bot, "kick", usuario, interaction.user, motivo)
        embed = Embed(
            title=f"{get_emoji(self.bot, 'thinking')} Confirmação de Kick",
            description=f"Você tem certeza que deseja expulsar {usuario.mention}?",
            color=Color.orange()
        )
        embed.add_field(name="Usuário", value=f"{usuario.mention} (`{usuario.id}`)", inline=True)
        embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
        embed.add_field(name="Motivo", value=motivo or "Não especificado", inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_message()

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="ban", description="Bane um usuário do servidor.")
    @check_mod_permissions(ban_members=True)
    @check_bot_permissions(ban_members=True)
    @check_role_hierarchy()
    async def ban(self, interaction: Interaction, 
                usuario: Member = SlashOption(description="O usuário a ser banido"), 
                motivo: str = SlashOption(description="O motivo do banimento (opcional)", required=False),
                delete_days: int = SlashOption(name="delete_message_days", description="Apagar mensagens dos últimos X dias (0-7)", default=0, min_value=0, max_value=7, required=False)
                ):
        """Bane um membro do servidor com confirmação."""
        # Nota: O ban via ID não é suportado diretamente aqui para simplificar a verificação de hierarquia
        # Pode ser adicionado um comando separado /forceban <user_id> se necessário.
        
        view = ConfirmModerationView(self.bot, "ban", usuario, interaction.user, motivo)
        embed = Embed(
            title=f"{get_emoji(self.bot, 'thinking')} Confirmação de Ban",
            description=f"Você tem certeza que deseja banir {usuario.mention}?",
            color=Color.red()
        )
        embed.add_field(name="Usuário", value=f"{usuario.mention} (`{usuario.id}`)", inline=True)
        embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
        embed.add_field(name="Motivo", value=motivo or "Não especificado", inline=False)
        embed.add_field(name="Apagar Mensagens", value=f"{delete_days} dias", inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_message()

    # TODO: Comando /mute (requer cargo ou timeout)
    # TODO: Comando /unmute (requer cargo ou timeout)
    # TODO: Comando /clear (limpar mensagens)
    # TODO: Comando /slowmode
    # TODO: Comando /lock /unlock (canal)

    # --- Tratamento de Erros Específico da Cog --- 
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        # Trata erros de permissão e hierarquia DENTRO desta cog
        if isinstance(error, (application_checks.ApplicationMissingPermissions, application_checks.ApplicationBotMissingPermissions, application_checks.CheckFailure)):
             # As mensagens de erro já são enviadas pelos decorators check_...
             # Apenas marca como tratado para evitar logs desnecessários do handler global
             try:
                 error.handled = True 
             except AttributeError:
                 pass 
        # Deixa outros erros passarem para o handler global (se houver)

# Função setup para carregar a cog
def setup(bot):
    """Adiciona a cog Comandos ao bot."""
    bot.add_cog(Comandos(bot))
