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
# from utils.emojis import get_emoji # Supondo que este helper existe e funciona
# Para fins de teste sem o utils.emojis, vou usar emojis unicode diretamente ou placeholders
def get_emoji(bot, name):
    # Placeholder para emojis, substitua pela sua lógica real se necessário
    emoji_map = {
        "sad": "😥", "happy_flower": "🌸", "warn": "⚠️", "hammer": "🔨", "trash": "🗑️",
        "gear": "⚙️", "money": "💰", "info": "ℹ️", "dice": "🎲", "tools": "🛠️", "question": "❓",
        "music": "🎵", "interact": "🤝"
    }
    return emoji_map.get(name, "▫️") # Retorna um emoji padrão ou placeholder

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
        embed.set_author(name=f"{interaction.user.display_name} ({interaction.user.id})", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
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
        embed.set_author(name=f"{interaction.user.display_name} ({interaction.user.id})", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
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
    def __init__(self, bot, action: str, target: Member, moderator: Member, reason: str | None, delete_days: int = 0):
        super().__init__(timeout=60.0)
        self.bot = bot
        self.action = action # "kick", "ban", "mute", "unmute"
        self.target = target
        self.moderator = moderator
        self.reason = reason or "Motivo não especificado"
        self.delete_days = delete_days # Adicionado para o ban
        self.confirmed = False

        action_labels = {
            "kick": "Confirmar Kick",
            "ban": "Confirmar Ban",
            "mute": "Confirmar Mute",
            "unmute": "Confirmar Unmute"
        }
        confirm_button = nextcord.utils.get(self.children, custom_id="confirm_mod_action")
        if confirm_button and isinstance(confirm_button, Button):
            confirm_button.label = action_labels.get(action, "Confirmar")

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')}{interaction.user.mention}, apenas {self.moderator.mention} pode confirmar esta ação.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if not self.confirmed:
            for item in self.children:
                if isinstance(item, (Button, Select)):
                    item.disabled = True
            timeout_embed = Embed(title=f"Ação de Moderação Cancelada ({self.action.capitalize()})", description="Você demorou muito para confirmar.", color=Color.red())
            try:
                if self.message: # Garante que self.message existe
                    await self.message.edit(embed=timeout_embed, view=self)
            except (NotFound, AttributeError, HTTPException):
                pass

    @nextcord.ui.button(label="Confirmar", style=ButtonStyle.danger, custom_id="confirm_mod_action")
    async def confirm_button(self, button: Button, interaction: Interaction):
        self.confirmed = True
        for item in self.children:
            if isinstance(item, (Button, Select)):
                item.disabled = True
        
        success = False
        error_message = None
        log_embed = None

        try:
            mod_reason = f"{self.reason} (Moderador: {self.moderator.name}#{self.moderator.discriminator} [{self.moderator.id}])"
            if self.action == "kick":
                await self.target.kick(reason=mod_reason)
                success = True
            elif self.action == "ban":
                await self.target.ban(reason=mod_reason, delete_message_days=self.delete_days)
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

        if success:
            result_embed = Embed(
                title=f"{get_emoji(self.bot, 'hammer')} Ação Concluída: {self.action.capitalize()} de {self.target.name}",
                description=f"**Usuário:** {self.target.mention} (`{self.target.id}`)\n**Moderador:** {self.moderator.mention}\n**Motivo:** {self.reason}",
                color=Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed = result_embed
        else:
            result_embed = Embed(
                title=f"{get_emoji(self.bot, 'sad')}{self.action.capitalize()} Falhou",
                description=error_message or "Erro desconhecido.",
                color=Color.red()
            )

        try:
            await interaction.response.edit_message(embed=result_embed, view=None) # Limpa a view após a ação
        except Exception as e:
             print(f"[WARN MOD] Falha ao editar mensagem de confirmação: {e}")
             try:
                 await interaction.followup.send(embed=result_embed, ephemeral=True)
             except Exception as e2:
                 print(f"[ERRO MOD] Falha ao enviar followup após falha na edição: {e2}")

        if success and MOD_LOG_CHANNEL_ID and interaction.guild:
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
            if isinstance(item, (Button, Select)):
                item.disabled = True
        cancel_embed = Embed(title=f"Ação Cancelada ({self.action.capitalize()})", description=f"A ação de {self.action} em {self.target.mention} foi cancelada.", color=Color.light_grey())
        await interaction.response.edit_message(embed=cancel_embed, view=self)
        self.stop()

# --- View para o Comando Help --- 
class HelpView(View):
    def __init__(self, bot: commands.Bot, initial_interaction: Interaction):
        super().__init__(timeout=180) 
        self.bot = bot
        self.initial_interaction = initial_interaction 
        self.current_cog_name = "help_home" # Nome interno da categoria atual
        self._update_buttons()

    def _update_buttons(self):
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = False
                # Estilos padrão
                if child.custom_id == "help_home": child.style = ButtonStyle.primary
                elif child.custom_id == "help_musica": child.style = ButtonStyle.secondary 
                elif child.custom_id in ["help_economia", "help_jogos"]: child.style = ButtonStyle.green
                else: child.style = ButtonStyle.secondary
                # Desabilita e destaca o atual
                if child.custom_id == self.current_cog_name:
                    child.disabled = True
                    child.style = ButtonStyle.primary 

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.initial_interaction.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')}{interaction.user.mention}, apenas {self.initial_interaction.user.mention} pode usar estes botões.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, (Button, Select)):
                item.disabled = True
        try:
            if self.initial_interaction.message: # Garante que a mensagem original existe
                await self.initial_interaction.edit_original_message(content="*Esta sessão de ajuda expirou.*", view=self)
        except (NotFound, HTTPException, AttributeError):
            pass

    async def _get_cog_help_embed(self, internal_cog_name: str) -> Embed:
        # Mapeamento de Nomes Amigáveis, Emojis e Nomes Reais das Cogs
        cog_display_info = {
            "help_home": {"name": "Página Inicial", "emoji": get_emoji(self.bot, 'question'), "color": Color.purple(), "real_cog_name": None},
            "help_comandos": {"name": "Comandos Gerais", "emoji": get_emoji(self.bot, 'gear'), "color": Color.blue(), "real_cog_name": "Comandos"},
            "help_economia": {"name": "Economia", "emoji": get_emoji(self.bot, 'money'), "color": Color.gold(), "real_cog_name": "Economia"},
            "help_informacoes": {"name": "Informações", "emoji": get_emoji(self.bot, 'info'), "color": Color.teal(), "real_cog_name": "Informacoes"},
            "help_interacoes": {"name": "Interações", "emoji": get_emoji(self.bot, 'interact'), "color": Color.magenta(), "real_cog_name": "Interacoes"},
            "help_jogos": {"name": "Jogos", "emoji": get_emoji(self.bot, 'dice'), "color": Color.green(), "real_cog_name": "Jogos"},
            "help_musica": {"name": "Música", "emoji": get_emoji(self.bot, 'music'), "color": Color.red(), "real_cog_name": "Musica"},
            "help_utilitarios": {"name": "Utilitários", "emoji": get_emoji(self.bot, 'tools'), "color": Color.dark_grey(), "real_cog_name": "Utilitarios"}
        }

        display_info = cog_display_info.get(internal_cog_name, cog_display_info["help_home"])
        embed = Embed(title=f"{display_info['emoji']} Ajuda: {display_info['name']}", color=display_info['color'])
        
        if internal_cog_name == "help_home":
            embed.description = (f"Bem-vindo(a) à ajuda da {self.bot.user.name}!\n\n"
                               f"Use os botões abaixo para navegar pelas categorias de comandos. "
                               f"Cada categoria mostrará os comandos slash disponíveis e uma breve descrição.\n\n"
                               f"Lembre-se que todos os comandos são executados usando `/` seguido do nome do comando.")
            embed.add_field(name="Como Usar?", value="Clique em um botão de categoria para ver os comandos. Se precisar de mais detalhes sobre um comando específico, geralmente a descrição do próprio comando ao digitá-lo no Discord já ajuda!", inline=False)
            embed.set_footer(text="Selecione uma categoria abaixo.")
            return embed

        real_cog_name = display_info.get("real_cog_name")
        if not real_cog_name:
            embed.description = "Categoria de ajuda não encontrada."
            return embed
            
        cog = self.bot.get_cog(real_cog_name)
        if not cog:
            embed.description = f"A categoria 	`{display_info['name']}`	 não está carregada ou não existe."
            return embed

        # Atualizado para buscar comandos de aplicação (slash commands)
        app_commands = cog.get_application_commands()
        if not app_commands:
            embed.description = "Nenhum comando de barra (/) encontrado nesta categoria."
            return embed

        command_text_list = []
        for cmd in sorted(app_commands, key=lambda c: c.qualified_name):
            if isinstance(cmd, (nextcord.SlashApplicationCommand, nextcord.MessageApplicationCommand, nextcord.UserApplicationCommand)):
                param_string = ""
                if hasattr(cmd, 'options') and cmd.options:
                    for option_name, option_details in cmd.options.items():
                        required_indicator = "" # Não há indicador padrão de obrigatoriedade visível aqui, a UI do Discord mostra
                        param_string += f" `{{{option_name}}}`"
                
                cmd_type_prefix = "/" # Default para SlashCommand
                if isinstance(cmd, nextcord.MessageApplicationCommand): cmd_type_prefix = "(Msg) "
                elif isinstance(cmd, nextcord.UserApplicationCommand): cmd_type_prefix = "(Usr) "
                
                command_text_list.append(f"**`{cmd_type_prefix}{cmd.qualified_name}{param_string}`**\n{cmd.description}")
        
        if command_text_list:
            embed.description = "\n\n".join(command_text_list)
        else:
            embed.description = "Nenhum comando de barra (/) encontrado nesta categoria que possa ser exibido."

        return embed

    async def _send_help_for_cog(self, interaction: Interaction, cog_name_key: str):
        self.current_cog_name = cog_name_key
        self._update_buttons()
        help_embed = await self._get_cog_help_embed(cog_name_key)
        await interaction.response.edit_message(embed=help_embed, view=self)

    @nextcord.ui.button(label="Início", style=ButtonStyle.primary, custom_id="help_home", row=0)
    async def home_button(self, button: Button, interaction: Interaction):
        await self._send_help_for_cog(interaction, "help_home")

    @nextcord.ui.button(label="Comandos", style=ButtonStyle.secondary, custom_id="help_comandos", row=0)
    async def comandos_button(self, button: Button, interaction: Interaction):
        await self._send_help_for_cog(interaction, "help_comandos")

    @nextcord.ui.button(label="Economia", style=ButtonStyle.green, custom_id="help_economia", row=0)
    async def economia_button(self, button: Button, interaction: Interaction):
        await self._send_help_for_cog(interaction, "help_economia")

    @nextcord.ui.button(label="Informações", style=ButtonStyle.secondary, custom_id="help_informacoes", row=1)
    async def informacoes_button(self, button: Button, interaction: Interaction):
        await self._send_help_for_cog(interaction, "help_informacoes")

    @nextcord.ui.button(label="Interações", style=ButtonStyle.secondary, custom_id="help_interacoes", row=1)
    async def interacoes_button(self, button: Button, interaction: Interaction):
        await self._send_help_for_cog(interaction, "help_interacoes")
    
    @nextcord.ui.button(label="Jogos", style=ButtonStyle.green, custom_id="help_jogos", row=1)
    async def jogos_button(self, button: Button, interaction: Interaction):
        await self._send_help_for_cog(interaction, "help_jogos")

    @nextcord.ui.button(label="Música", style=ButtonStyle.secondary, custom_id="help_musica", row=2)
    async def musica_button(self, button: Button, interaction: Interaction):
        await self._send_help_for_cog(interaction, "help_musica")

    @nextcord.ui.button(label="Utilitários", style=ButtonStyle.secondary, custom_id="help_utilitarios", row=2)
    async def utilitarios_button(self, button: Button, interaction: Interaction):
        await self._send_help_for_cog(interaction, "help_utilitarios")

class Comandos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
        print("Cog Comandos carregada.")

    @nextcord.slash_command(name="sugestao", description="Envia uma sugestão para o desenvolvedor do bot.")
    async def sugestao(self, interaction: Interaction):
        await interaction.response.send_modal(SuggestionModal(self.bot))

    @nextcord.slash_command(name="bugreport", description="Reporta um bug encontrado no bot para o desenvolvedor.")
    async def bug_report(self, interaction: Interaction):
        await interaction.response.send_modal(BugReportModal(self.bot))

    @nextcord.slash_command(name="botinfo", description="Mostra informações sobre mim!")
    async def bot_info(self, interaction: Interaction):
        await interaction.response.defer()
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
        ram_total_gb = psutil.virtual_memory().total / (1024**3)
        ram_used_gb = psutil.virtual_memory().used / (1024**3)
        uptime_seconds = time.time() - self.start_time
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))

        embed = Embed(title=f"{get_emoji(self.bot, 'info')} Informações sobre {self.bot.user.name}", color=Color.blue(), timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None)
        embed.add_field(name="Desenvolvedor", value=f"<@{DEVELOPER_ID}>", inline=True)
        embed.add_field(name="Versão Nextcord", value=nextcord.__version__, inline=True)
        embed.add_field(name="Versão Python", value=platform.python_version(), inline=True)
        embed.add_field(name="Sistema Operacional", value=f"{platform.system()} {platform.release()}", inline=True)
        embed.add_field(name="Uso de CPU", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="Uso de RAM", value=f"{ram_usage}% ({ram_used_gb:.2f}GB / {ram_total_gb:.2f}GB)", inline=True)
        embed.add_field(name="Tempo de Atividade", value=uptime_str, inline=True)
        embed.add_field(name="Servidores", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Usuários Totais (aproximado)", value=str(sum(guild.member_count for guild in self.bot.guilds if guild.member_count is not None)), inline=True)
        embed.add_field(name="Latência da API", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Links Úteis", value=f"[Me adicione](https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands) | [Suporte (se houver)]", inline=False)
        embed.set_footer(text=f"ID do Bot: {self.bot.user.id}")
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="avatar", description="Mostra o avatar de um usuário.")
    async def avatar(self, interaction: Interaction, usuario: Member = SlashOption(description="O usuário para mostrar o avatar (opcional)", required=False)):
        target = usuario or interaction.user
        embed = Embed(title=f"Avatar de {target.display_name}", color=target.color)
        if target.display_avatar:
            embed.set_image(url=target.display_avatar.url)
            embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Não foi possível obter o avatar deste usuário.", ephemeral=True)

    @nextcord.slash_command(name="serverinfo", description="Mostra informações sobre o servidor atual.")
    @application_checks.guild_only()
    async def server_info(self, interaction: Interaction):
        guild = interaction.guild
        if not guild: # Checagem extra, embora guild_only() já faça isso
            await interaction.response.send_message("Este comando só pode ser usado em um servidor.", ephemeral=True)
            return

        await interaction.response.defer()
        embed = Embed(title=f"Informações do Servidor: {guild.name}", color=Color.random(), timestamp=guild.created_at)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="ID do Servidor", value=guild.id, inline=True)
        embed.add_field(name="Dono(a)", value=guild.owner.mention if guild.owner else "Desconhecido", inline=True)
        embed.add_field(name="Membros", value=str(guild.member_count), inline=True)
        embed.add_field(name="Canais de Texto", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="Canais de Voz", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="Cargos", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Nível de Boost", value=f"Nível {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
        embed.add_field(name="Criado em", value=f"<t:{int(guild.created_at.timestamp())}:F> (<t:{int(guild.created_at.timestamp())}:R>)", inline=False)
        
        features_str = ", ".join(guild.features) if guild.features else "Nenhuma especial"
        embed.add_field(name="Recursos do Servidor", value=features_str, inline=False)

        if guild.banner:
            embed.set_image(url=guild.banner.url)
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="userinfo", description="Mostra informações sobre um usuário.")
    async def user_info(self, interaction: Interaction, usuario: Member = SlashOption(description="O usuário para mostrar informações (opcional)", required=False)):
        target_user = usuario or interaction.user
        
        # Se for um User e não Member (ex: usuário não está no servidor, mas é um comando global)
        # Tentamos buscar o Member para ter informações do servidor se possível
        target_member: Optional[Member] = None
        if isinstance(target_user, User) and interaction.guild:
            target_member = interaction.guild.get_member(target_user.id)
        elif isinstance(target_user, Member):
            target_member = target_user
        
        display_target = target_member or target_user # Prioriza Member para infos do servidor

        await interaction.response.defer()
        embed = Embed(title=f"Informações de {display_target.name}#{display_target.discriminator}", color=display_target.color, timestamp=display_target.created_at)
        if display_target.display_avatar:
            embed.set_thumbnail(url=display_target.display_avatar.url)
        
        embed.add_field(name="ID do Usuário", value=display_target.id, inline=True)
        embed.add_field(name="Menção", value=display_target.mention, inline=True)
        embed.add_field(name="É um Bot?", value="Sim" if display_target.bot else "Não", inline=True)
        embed.add_field(name="Conta Criada em", value=f"<t:{int(display_target.created_at.timestamp())}:F> (<t:{int(display_target.created_at.timestamp())}:R>)", inline=False)

        if target_member: # Informações específicas do membro no servidor
            embed.add_field(name="Apelido no Servidor", value=target_member.nick or "Nenhum", inline=True)
            embed.add_field(name="Entrou no Servidor em", value=f"<t:{int(target_member.joined_at.timestamp())}:F> (<t:{int(target_member.joined_at.timestamp())}:R>)" if target_member.joined_at else "Desconhecido", inline=False)
            roles = [role.mention for role in reversed(target_member.roles) if role.name != "@everyone"]
            roles_str = ", ".join(roles) if roles else "Nenhum cargo específico"
            if len(roles_str) > 1024: # Limite do campo do embed
                roles_str = roles_str[:1020] + "..."
            embed.add_field(name=f"Cargos ({len(roles)})", value=roles_str, inline=False)
            if target_member.guild_permissions:
                perms_list = [perm.replace("_", " ").title() for perm, value in target_member.guild_permissions if value]
                # embed.add_field(name="Permissões Chave", value=", ".join(perms_list[:5]) if perms_list else "Nenhuma especial", inline=False)
        
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="kick", description="Expulsa um membro do servidor.")
    @application_checks.has_permissions(kick_members=True)
    @application_checks.bot_has_permissions(kick_members=True)
    async def kick_member(self, interaction: Interaction, 
                          membro: Member = SlashOption(description="O membro para expulsar", required=True),
                          motivo: Optional[str] = SlashOption(description="Motivo da expulsão (opcional)", required=False)):
        if not interaction.guild:
            await interaction.response.send_message("Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        if membro == interaction.user:
            await interaction.response.send_message("Você não pode se expulsar!", ephemeral=True)
            return
        if membro == self.bot.user:
            await interaction.response.send_message("Eu não posso me expulsar!", ephemeral=True)
            return
        # Checagem de hierarquia (simplificada)
        if interaction.user.top_role <= membro.top_role and interaction.guild.owner != interaction.user:
            await interaction.response.send_message("Você não pode expulsar um membro com cargo igual ou superior ao seu.", ephemeral=True)
            return
        if interaction.guild.me.top_role <= membro.top_role:
            await interaction.response.send_message("Eu não posso expulsar um membro com cargo igual ou superior ao meu.", ephemeral=True)
            return

        confirm_embed = Embed(
            title=f"Confirmação de Kick: {membro.name}",
            description=f"Você tem certeza que deseja expulsar {membro.mention}?\n**Motivo:** {motivo or 'Não especificado'}",
            color=Color.orange()
        )
        view = ConfirmModerationView(self.bot, "kick", membro, interaction.user, motivo)
        msg = await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)
        view.message = msg # Passa a mensagem para a view poder editá-la no timeout

    @nextcord.slash_command(name="ban", description="Bane um membro do servidor.")
    @application_checks.has_permissions(ban_members=True)
    @application_checks.bot_has_permissions(ban_members=True)
    async def ban_member(self, interaction: Interaction, 
                       membro: Member = SlashOption(description="O membro para banir", required=True),
                       motivo: Optional[str] = SlashOption(description="Motivo do banimento (opcional)", required=False),
                       dias_mensagens_deletadas: Optional[int] = SlashOption(description="Número de dias de mensagens para deletar (0-7, padrão 0)", required=False, min_value=0, max_value=7)):
        if not interaction.guild:
            await interaction.response.send_message("Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        if membro == interaction.user:
            await interaction.response.send_message("Você não pode se banir!", ephemeral=True)
            return
        if membro == self.bot.user:
            await interaction.response.send_message("Eu não posso me banir!", ephemeral=True)
            return
        if interaction.user.top_role <= membro.top_role and interaction.guild.owner != interaction.user:
            await interaction.response.send_message("Você não pode banir um membro com cargo igual ou superior ao seu.", ephemeral=True)
            return
        if interaction.guild.me.top_role <= membro.top_role:
            await interaction.response.send_message("Eu não posso banir um membro com cargo igual ou superior ao meu.", ephemeral=True)
            return

        delete_days = dias_mensagens_deletadas if dias_mensagens_deletadas is not None else 0

        confirm_embed = Embed(
            title=f"Confirmação de Ban: {membro.name}",
            description=f"Você tem certeza que deseja banir {membro.mention}?\n**Motivo:** {motivo or 'Não especificado'}\n**Deletar mensagens dos últimos:** {delete_days} dias",
            color=Color.red()
        )
        view = ConfirmModerationView(self.bot, "ban", membro, interaction.user, motivo, delete_days=delete_days)
        msg = await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)
        view.message = msg

    @nextcord.slash_command(name="limpar", description="Limpa uma quantidade de mensagens no canal.")
    @application_checks.has_permissions(manage_messages=True)
    @application_checks.bot_has_permissions(manage_messages=True)
    async def limpar_mensagens(self, interaction: Interaction, quantidade: int = SlashOption(description="Número de mensagens para limpar (1-100)", required=True, min_value=1, max_value=100)):
        if not interaction.channel or not isinstance(interaction.channel, TextChannel):
            await interaction.response.send_message("Este comando só pode ser usado em um canal de texto.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        try:
            deleted_messages = await interaction.channel.purge(limit=quantidade)
            await interaction.followup.send(f"{get_emoji(self.bot, 'trash')} {len(deleted_messages)} mensagens foram limpas!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao limpar mensagens: {e}", ephemeral=True)
            print(f"[ERRO LIMPAR] {e}")

    @nextcord.slash_command(name="ajuda", description="Mostra a lista de comandos e como usá-los.")
    async def ajuda(self, interaction: Interaction):
        view = HelpView(self.bot, initial_interaction=interaction)
        initial_embed = await view._get_cog_help_embed("help_home")
        await interaction.response.send_message(embed=initial_embed, view=view)

def setup(bot: commands.Bot):
    bot.add_cog(Comandos(bot))
