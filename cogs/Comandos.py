from typing import Optional # ADICIONADO PARA CORRIGIR NameError
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
            "help_comandos": {"name": "Comandos Gerais", "emoji": get_emoji(self.bot, 'tools'), "color": Color.blue(), "real_cog_name": "Comandos"},
            "help_economia": {"name": "Economia", "emoji": get_emoji(self.bot, 'money'), "color": Color.gold(), "real_cog_name": "Economia"},
            "help_interacoes": {"name": "Interações", "emoji": get_emoji(self.bot, 'interact'), "color": Color.magenta(), "real_cog_name": "Interacoes"},
            "help_jogos": {"name": "Jogos", "emoji": get_emoji(self.bot, 'dice'), "color": Color.green(), "real_cog_name": "Jogos"},
            "help_musica": {"name": "Música", "emoji": get_emoji(self.bot, 'music'), "color": Color.red(), "real_cog_name": "Musica"},
            "help_utilitarios": {"name": "Utilitários", "emoji": get_emoji(self.bot, 'gear'), "color": Color.orange(), "real_cog_name": "Utilitarios"},
            "help_informacoes": {"name": "Informações", "emoji": get_emoji(self.bot, 'info'), "color": Color.teal(), "real_cog_name": "Informacoes"}
        }

        info = cog_display_info.get(internal_cog_name)
        if not info:
            return Embed(title="Erro", description="Categoria de ajuda não encontrada.", color=Color.red())

        embed = Embed(title=f"{info['emoji']} Ajuda: {info['name']}", color=info['color'])
        embed.set_footer(text=f"Use os botões para navegar. | Shirayuki v{self.bot.version}")

        if internal_cog_name == "help_home":
            embed.description = (
                f"Bem-vindo(a) à central de ajuda da Shirayuki! ✨\n\n"
                f"Eu sou um bot multifuncional com comandos de moderação, economia, música, jogos e muito mais. "
                f"Use os botões abaixo para explorar as categorias de comandos disponíveis.\n\n"
                f"**Como usar os comandos:**\n"
                f"A maioria dos meus comandos são comandos de barra (slash commands). Comece digitando `/` no chat "
                f"e o Discord mostrará uma lista dos meus comandos disponíveis para você.\n\n"
                f"Se precisar de ajuda com um comando específico, geralmente a descrição do comando ao selecioná-lo "
                f"já oferece uma boa ideia do que ele faz e quais opções ele aceita.\n\n"
                f"{get_emoji(self.bot, 'happy_flower')} Divirta-se explorando!"
            )
            embed.add_field(name="Versão do Bot", value=f"`{self.bot.version}`", inline=True)
            embed.add_field(name="Prefixo (Legado)", value="`/` (Slash Commands são o padrão)", inline=True)
            embed.add_field(name="Desenvolvedor", value=f"<@{DEVELOPER_ID}>", inline=True)
            # Adicionar contagem de cogs e comandos?
            total_cogs = len(self.bot.cogs)
            total_app_commands = len(self.bot.get_all_application_commands())
            embed.add_field(name="Módulos (Cogs)", value=str(total_cogs), inline=True)
            embed.add_field(name="Comandos Slash", value=str(total_app_commands), inline=True)
            ping = round(self.bot.latency * 1000)
            embed.add_field(name="Latência", value=f"{ping}ms", inline=True)

        elif info["real_cog_name"]:
            cog = self.bot.get_cog(info["real_cog_name"])
            if cog:
                commands_list = []
                # Filtrar apenas comandos de aplicação (slash commands) da cog
                app_commands = [cmd for cmd in cog.get_application_commands() if isinstance(cmd, (nextcord.SlashApplicationCommand, nextcord.GroupCog))]
                
                if not app_commands:
                    commands_list.append("*Nenhum comando de barra encontrado nesta categoria.*");
                else:
                    for cmd in sorted(app_commands, key=lambda c: c.qualified_name):
                        if isinstance(cmd, nextcord.SlashApplicationCommand):
                            description = cmd.description or "Sem descrição."
                            if len(description) > 70: description = description[:67] + "..."
                            commands_list.append(f"**`/{cmd.qualified_name}`** - {description}")
                        elif isinstance(cmd, nextcord.GroupCog): # Para grupos de subcomandos
                            # Listar subcomandos do grupo
                            sub_cmds_desc = []
                            for sub_cmd_name, sub_cmd_obj in sorted(cmd.walk_commands(), key=lambda c: c[0]):
                                if isinstance(sub_cmd_obj, nextcord.SlashApplicationSubcommand):
                                    sub_desc = sub_cmd_obj.description or "Sem descrição."
                                    if len(sub_desc) > 60: sub_desc = sub_desc[:57] + "..."
                                    sub_cmds_desc.append(f"  **`{sub_cmd_obj.qualified_name}`** - {sub_desc}")
                            
                            if sub_cmds_desc:
                                group_desc = cmd.description or f"Comandos relacionados a {cmd.name}."
                                commands_list.append(f"**`/{cmd.name}`** - {group_desc}\n" + "\n".join(sub_cmds_desc))
                            else:
                                commands_list.append(f"**`/{cmd.name}`** - {cmd.description or 'Grupo de comandos.'} (Sem subcomandos visíveis)")
                                
                embed.description = "\n".join(commands_list) if commands_list else "Nenhum comando de barra encontrado nesta categoria."
            else:
                embed.description = f"A categoria '{info['name']}' não pôde ser carregada ou não possui comandos."
        else:
            embed.description = "Informações para esta categoria não disponíveis."

        return embed

    @nextcord.ui.button(label="Início", style=ButtonStyle.primary, custom_id="help_home")
    async def home_button(self, button: Button, interaction: Interaction):
        self.current_cog_name = "help_home"
        self._update_buttons()
        embed = await self._get_cog_help_embed("help_home")
        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Comandos", style=ButtonStyle.secondary, custom_id="help_comandos")
    async def comandos_button(self, button: Button, interaction: Interaction):
        self.current_cog_name = "help_comandos"
        self._update_buttons()
        embed = await self._get_cog_help_embed("help_comandos")
        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Economia", style=ButtonStyle.green, custom_id="help_economia")
    async def economia_button(self, button: Button, interaction: Interaction):
        self.current_cog_name = "help_economia"
        self._update_buttons()
        embed = await self._get_cog_help_embed("help_economia")
        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Interações", style=ButtonStyle.secondary, custom_id="help_interacoes", row=1)
    async def interacoes_button(self, button: Button, interaction: Interaction):
        self.current_cog_name = "help_interacoes"
        self._update_buttons()
        embed = await self._get_cog_help_embed("help_interacoes")
        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Jogos", style=ButtonStyle.green, custom_id="help_jogos", row=1)
    async def jogos_button(self, button: Button, interaction: Interaction):
        self.current_cog_name = "help_jogos"
        self._update_buttons()
        embed = await self._get_cog_help_embed("help_jogos")
        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Música", style=ButtonStyle.secondary, custom_id="help_musica", row=2)
    async def musica_button(self, button: Button, interaction: Interaction):
        self.current_cog_name = "help_musica"
        self._update_buttons()
        embed = await self._get_cog_help_embed("help_musica")
        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Utilitários", style=ButtonStyle.secondary, custom_id="help_utilitarios", row=2)
    async def utilitarios_button(self, button: Button, interaction: Interaction):
        self.current_cog_name = "help_utilitarios"
        self._update_buttons()
        embed = await self._get_cog_help_embed("help_utilitarios")
        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Informações", style=ButtonStyle.secondary, custom_id="help_informacoes", row=2)
    async def informacoes_button(self, button: Button, interaction: Interaction):
        self.current_cog_name = "help_informacoes"
        self._update_buttons()
        embed = await self._get_cog_help_embed("help_informacoes")
        await interaction.response.edit_message(embed=embed, view=self)

# --- Cog Principal --- 
class Comandos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
        self.bot.version = "3.1.0-alpha" # Versão do bot
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Cog Comandos carregada.')

    def cog_unload(self):
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Cog Comandos descarregada.')

    async def send_error_embed(self, interaction: Interaction, title: str, description: str):
        embed = Embed(title=f"{get_emoji(self.bot, 'sad')} {title}", description=description, color=Color.red())
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def send_success_embed(self, interaction: Interaction, title: str, description: str):
        embed = Embed(title=f"{get_emoji(self.bot, 'happy_flower')} {title}", description=description, color=Color.green())
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Comandos Gerais --- 
    @nextcord.slash_command(name="ping", description="Verifica a latência do bot.", guild_ids=[SERVER_ID])
    async def ping(self, interaction: Interaction):
        latency_ms = round(self.bot.latency * 1000)
        embed = Embed(title="🏓 Pong!", description=f"Latência da API: **{latency_ms}ms**", color=Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="avatar", description="Mostra o avatar de um usuário.", guild_ids=[SERVER_ID])
    async def avatar(self, interaction: Interaction, usuario: Optional[Member] = SlashOption(description="O usuário para mostrar o avatar (padrão: você mesmo).", required=False)):
        target_user = usuario or interaction.user
        avatar_url = target_user.display_avatar.url
        embed = Embed(title=f"🖼️ Avatar de {target_user.display_name}", color=target_user.color)
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="userinfo", description="Mostra informações sobre um usuário.", guild_ids=[SERVER_ID])
    async def userinfo(self, interaction: Interaction, usuario: Optional[Member] = SlashOption(description="O usuário para mostrar informações (padrão: você mesmo).", required=False)):
        target_user = usuario or interaction.user
        
        embed = Embed(title=f"👤 Informações de {target_user.display_name}", color=target_user.color, timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Nome Completo", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
        embed.add_field(name="ID do Usuário", value=f"`{target_user.id}`", inline=True)
        embed.add_field(name="Apelido", value=target_user.nick or "Nenhum", inline=True)
        
        created_at_unix = int(target_user.created_at.timestamp())
        embed.add_field(name="Conta Criada em", value=f"<t:{created_at_unix}:F> (<t:{created_at_unix}:R>)", inline=False)
        
        if isinstance(target_user, Member):
            joined_at_unix = int(target_user.joined_at.timestamp())
            embed.add_field(name="Entrou no Servidor em", value=f"<t:{joined_at_unix}:F> (<t:{joined_at_unix}:R>)", inline=False)
            
            roles = [role.mention for role in reversed(target_user.roles) if role.name != "@everyone"]
            roles_str = ", ".join(roles) if roles else "Nenhum cargo"
            if len(roles_str) > 1024: roles_str = roles_str[:1020] + "..."
            embed.add_field(name=f"Cargos ({len(roles)})", value=roles_str, inline=False)
            
            highest_role = target_user.top_role.mention if target_user.top_role.name != "@everyone" else "Nenhum (além de @everyone)"
            embed.add_field(name="Cargo Mais Alto", value=highest_role, inline=True)
            embed.add_field(name="É Bot?", value="Sim" if target_user.bot else "Não", inline=True)
            
            # Permissões (exemplo, pode ser muito longo)
            # perms = target_user.guild_permissions
            # if perms.administrator: embed.add_field(name="Administrador?", value="Sim", inline=True)
            
        embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="serverinfo", description="Mostra informações sobre o servidor atual.", guild_ids=[SERVER_ID])
    @application_checks.guild_only()
    async def serverinfo(self, interaction: Interaction):
        guild = interaction.guild
        if not guild: # Checagem extra, embora guild_only() já faça isso
            await self.send_error_embed(interaction, "Comando Inválido", "Este comando só pode ser usado em um servidor.")
            return

        embed = Embed(title=f"ℹ️ Informações do Servidor: {guild.name}", color=Color.random(), timestamp=datetime.now(timezone.utc))
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="ID do Servidor", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="Dono(a)", value=guild.owner.mention if guild.owner else "Desconhecido", inline=True)
        
        created_at_unix = int(guild.created_at.timestamp())
        embed.add_field(name="Criado em", value=f"<t:{created_at_unix}:F> (<t:{created_at_unix}:R>)", inline=True)
        
        embed.add_field(name="Nível de Verificação", value=str(guild.verification_level).capitalize(), inline=True)
        embed.add_field(name="Filtro de Conteúdo Explícito", value=str(guild.explicit_content_filter).capitalize(), inline=True)
        # embed.add_field(name="Nível de MFA", value="Ativado" if guild.mfa_level == nextcord.MFALevel.require_mfa else "Desativado", inline=True)
        embed.add_field(name="Nível de MFA", value=str(guild.mfa_level).replace("require_mfa", "Requer MFA").replace("none", "Nenhum"), inline=True)

        total_members = guild.member_count
        online_members = sum(1 for m in guild.members if m.status != nextcord.Status.offline and not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        humans = total_members - bots
        embed.add_field(name="Membros", value=f"**Total:** {total_members}\n**Humanos:** {humans} ({online_members} online)\n**Bots:** {bots}", inline=True)

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        embed.add_field(name="Canais", value=f"**Texto:** {text_channels}\n**Voz:** {voice_channels}\n**Categorias:** {categories}", inline=True)

        roles_count = len(guild.roles)
        emojis_count = len(guild.emojis)
        # stickers_count = len(guild.stickers) # Requer intents.stickers
        embed.add_field(name="Outros", value=f"**Cargos:** {roles_count}\n**Emojis:** {emojis_count}", inline=True)
        
        if guild.premium_tier > 0:
            embed.add_field(name="Nível de Boost", value=f"Nível {guild.premium_tier}", inline=True)
            embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
        
        if guild.features:
            features_str = ", ".join([f.replace("_", " ").title() for f in guild.features])
            if len(features_str) > 1024: features_str = features_str[:1020] + "..."
            embed.add_field(name="Recursos do Servidor", value=features_str, inline=False)

        if guild.banner:
            embed.set_image(url=guild.banner.url)
        
        embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="botinfo", description="Mostra informações sobre mim, a Shirayuki!", guild_ids=[SERVER_ID])
    async def botinfo(self, interaction: Interaction):
        app_info = await self.bot.application_info()
        owner = app_info.owner

        # Uptime
        current_time = time.time()
        difference = int(round(current_time - self.start_time))
        uptime_str = str(timedelta(seconds=difference))

        # CPU e RAM
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
        ram_total_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        ram_used_gb = round(psutil.virtual_memory().used / (1024**3), 1)

        embed = Embed(title=f"❄️ Informações sobre {self.bot.user.name}", color=Color.blurple(), timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Desenvolvedor(a)", value=owner.mention if owner else "Desconhecido", inline=True)
        embed.add_field(name="Versão do Bot", value=f"`{self.bot.version}`", inline=True)
        embed.add_field(name="Versão do Nextcord", value=f"`{nextcord.__version__}`", inline=True)
        embed.add_field(name="Versão do Python", value=f"`{platform.python_version()}`", inline=True)
        embed.add_field(name="Sistema Operacional", value=f"`{platform.system()} {platform.release()}`", inline=True)
        embed.add_field(name="Tempo Online (Uptime)", value=uptime_str, inline=True)
        embed.add_field(name="Servidores", value=str(len(self.bot.guilds)), inline=True)
        total_users = sum(guild.member_count for guild in self.bot.guilds)
        embed.add_field(name="Usuários Totais (em cache)", value=str(total_users), inline=True)
        embed.add_field(name="Latência da API", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Uso de CPU", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="Uso de RAM", value=f"{ram_usage}% ({ram_used_gb}GB / {ram_total_gb}GB)", inline=True)
        
        # Comandos (contagem)
        total_app_commands = len(self.bot.get_all_application_commands())
        embed.add_field(name="Comandos Slash Registrados", value=str(total_app_commands), inline=True)

        embed.set_footer(text="Feita com ❤️ e muito código!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="sugestao", description="Envia uma sugestão para o desenvolvedor do bot.", guild_ids=[SERVER_ID])
    async def sugestao(self, interaction: Interaction):
        modal = SuggestionModal(self.bot)
        await interaction.response.send_modal(modal)

    @nextcord.slash_command(name="bugreport", description="Reporta um bug para o desenvolvedor do bot.", guild_ids=[SERVER_ID])
    async def bugreport(self, interaction: Interaction):
        modal = BugReportModal(self.bot)
        await interaction.response.send_modal(modal)

    @nextcord.slash_command(name="ajuda", description="Mostra a mensagem de ajuda com todos os comandos.", guild_ids=[SERVER_ID])
    async def ajuda(self, interaction: Interaction):
        view = HelpView(self.bot, interaction)
        initial_embed = await view._get_cog_help_embed("help_home")
        await interaction.response.send_message(embed=initial_embed, view=view, ephemeral=True)
        view.message = await interaction.original_message() # Armazena a mensagem para edição no timeout

    # --- Comandos de Moderação --- 
    @nextcord.slash_command(name="limpar", description="Limpa uma quantidade de mensagens no canal atual.", guild_ids=[SERVER_ID])
    @application_checks.has_permissions(manage_messages=True)
    @application_checks.bot_has_permissions(manage_messages=True)
    async def limpar(self, interaction: Interaction, 
                     quantidade: int = SlashOption(description="Número de mensagens para limpar (1-100).", required=True, min_value=1, max_value=100),
                     usuario: Optional[Member] = SlashOption(description="Limpar mensagens apenas deste usuário (opcional).", required=False)):
        
        if not isinstance(interaction.channel, TextChannel):
            await self.send_error_embed(interaction, "Comando Inválido", "Este comando só pode ser usado em canais de texto.")
            return

        await interaction.response.defer(ephemeral=True) # Deferir para dar tempo de deletar

        check_func = (lambda m: m.author == usuario) if usuario else None
        
        try:
            deleted_messages = await interaction.channel.purge(limit=quantidade, check=check_func)
            msg_suffix = "mensagem" if len(deleted_messages) == 1 else "mensagens"
            user_suffix = f" de {usuario.mention}" if usuario else ""
            await interaction.followup.send(f"{get_emoji(self.bot, 'trash')} {len(deleted_messages)} {msg_suffix}{user_suffix} foram limpas com sucesso!", ephemeral=True)
        except Forbidden:
            await self.send_error_embed(interaction, "Permissão Negada", "Não tenho permissão para limpar mensagens neste canal.")
        except HTTPException as e:
            await self.send_error_embed(interaction, "Erro de API", f"Ocorreu um erro ao tentar limpar mensagens: {e}")
        except Exception as e:
            await self.send_error_embed(interaction, "Erro Inesperado", f"Ocorreu um erro: {e}")
            print(f"[ERRO LIMPAR] Erro ao limpar mensagens: {e}")
            traceback.print_exc()

    @nextcord.slash_command(name="kick", description="Expulsa um usuário do servidor.", guild_ids=[SERVER_ID])
    @application_checks.has_permissions(kick_members=True)
    @application_checks.bot_has_permissions(kick_members=True)
    async def kick(self, interaction: Interaction, 
                   usuario: Member = SlashOption(description="Usuário a ser expulso.", required=True),
                   motivo: Optional[str] = SlashOption(description="Motivo da expulsão (opcional).", required=False)):
        
        if usuario == interaction.user:
            await self.send_error_embed(interaction, "Ação Inválida", "Você não pode se expulsar.")
            return
        if usuario == self.bot.user:
            await self.send_error_embed(interaction, "Ação Inválida", "Eu não posso me expulsar.")
            return
        if usuario.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
            await self.send_error_embed(interaction, "Hierarquia Inválida", "Você não pode expulsar um usuário com cargo igual ou superior ao seu.")
            return
        if usuario.top_role >= interaction.guild.me.top_role:
            await self.send_error_embed(interaction, "Hierarquia Inválida (Bot)", "Não posso expulsar um usuário com cargo igual ou superior ao meu.")
            return

        view = ConfirmModerationView(self.bot, "kick", usuario, interaction.user, motivo)
        embed = Embed(title=f"🔨 Confirmar Expulsão de {usuario.name}", 
                      description=f"Você tem certeza que deseja expulsar {usuario.mention}?\n**Motivo:** {motivo or 'Não especificado'}", 
                      color=Color.orange())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_message()

    @nextcord.slash_command(name="ban", description="Bane um usuário do servidor.", guild_ids=[SERVER_ID])
    @application_checks.has_permissions(ban_members=True)
    @application_checks.bot_has_permissions(ban_members=True)
    async def ban(self, interaction: Interaction, 
                  usuario: Member = SlashOption(description="Usuário a ser banido.", required=True),
                  motivo: Optional[str] = SlashOption(description="Motivo do banimento (opcional).", required=False),
                  delete_days: Optional[int] = SlashOption(description="Número de dias de mensagens do usuário para deletar (0-7, padrão 0).", required=False, default=0, min_value=0, max_value=7)):

        if usuario == interaction.user:
            await self.send_error_embed(interaction, "Ação Inválida", "Você não pode se banir.")
            return
        if usuario == self.bot.user:
            await self.send_error_embed(interaction, "Ação Inválida", "Eu não posso me banir.")
            return
        if usuario.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
            await self.send_error_embed(interaction, "Hierarquia Inválida", "Você não pode banir um usuário com cargo igual ou superior ao seu.")
            return
        if usuario.top_role >= interaction.guild.me.top_role:
            await self.send_error_embed(interaction, "Hierarquia Inválida (Bot)", "Não posso banir um usuário com cargo igual ou superior ao meu.")
            return

        view = ConfirmModerationView(self.bot, "ban", usuario, interaction.user, motivo, delete_days)
        embed = Embed(title=f"🔨 Confirmar Banimento de {usuario.name}", 
                      description=f"Você tem certeza que deseja banir {usuario.mention}?\n**Motivo:** {motivo or 'Não especificado'}\n**Deletar mensagens dos últimos:** {delete_days} dias", 
                      color=Color.red())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_message()

    @nextcord.slash_command(name="unban", description="Desbane um usuário do servidor.", guild_ids=[SERVER_ID])
    @application_checks.has_permissions(ban_members=True)
    @application_checks.bot_has_permissions(ban_members=True)
    async def unban(self, interaction: Interaction, 
                    user_id: str = SlashOption(description="ID do usuário a ser desbanido.", required=True),
                    motivo: Optional[str] = SlashOption(description="Motivo do desbanimento (opcional).", required=False)):
        try:
            user_id_int = int(user_id)
            banned_user = await self.bot.fetch_user(user_id_int)
        except ValueError:
            await self.send_error_embed(interaction, "ID Inválido", "O ID fornecido não é um número válido.")
            return
        except NotFound:
            await self.send_error_embed(interaction, "Usuário Não Encontrado", f"Não foi possível encontrar um usuário com o ID `{user_id}`.")
            return
        except Exception as e:
            await self.send_error_embed(interaction, "Erro ao Buscar Usuário", f"Ocorreu um erro: {e}")
            return

        try:
            # Verificar se o usuário está realmente banido
            await interaction.guild.fetch_ban(banned_user)
        except NotFound:
            await self.send_error_embed(interaction, "Usuário Não Banido", f"{banned_user.mention} (`{banned_user.id}`) não está banido deste servidor.")
            return
        except Forbidden:
            await self.send_error_embed(interaction, "Permissão Negada", "Não tenho permissão para verificar a lista de banidos.")
            return
        except HTTPException as e:
            await self.send_error_embed(interaction, "Erro de API", f"Erro ao verificar banimento: {e}")
            return

        try:
            mod_reason = f"{motivo or 'Não especificado'} (Moderador: {interaction.user.name}#{interaction.user.discriminator} [{interaction.user.id}])"
            await interaction.guild.unban(banned_user, reason=mod_reason)
            await self.send_success_embed(interaction, "Usuário Desbanido", f"{banned_user.mention} (`{banned_user.id}`) foi desbanido com sucesso.")
            
            # Log de desbanimento (se configurado)
            if MOD_LOG_CHANNEL_ID and interaction.guild:
                log_channel = interaction.guild.get_channel(MOD_LOG_CHANNEL_ID)
                if log_channel and isinstance(log_channel, TextChannel):
                    log_embed = Embed(
                        title=f"{get_emoji(self.bot, 'happy_flower')} Usuário Desbanido: {banned_user.name}",
                        description=f"**Usuário:** {banned_user.mention} (`{banned_user.id}`)\n**Moderador:** {interaction.user.mention}\n**Motivo:** {motivo or 'Não especificado'}",
                        color=Color.green(),
                        timestamp=datetime.now(timezone.utc)
                    )
                    try:
                        await log_channel.send(embed=log_embed)
                    except Exception as e_log:
                        print(f"[ERRO MODLOG UNBAN] Erro ao enviar log de desbanimento: {e_log}")

        except Forbidden:
            await self.send_error_embed(interaction, "Permissão Negada", f"Não tenho permissão para desbanir usuários. Verifique minhas permissões.")
        except HTTPException as e:
            await self.send_error_embed(interaction, "Erro de API", f"Ocorreu um erro ao tentar desbanir {banned_user.mention}: {e}")
        except Exception as e:
            await self.send_error_embed(interaction, "Erro Inesperado", f"Ocorreu um erro ao tentar desbanir {banned_user.mention}: {e}")
            print(f"[ERRO UNBAN] Erro ao desbanir {banned_user.id}: {e}")
            traceback.print_exc()

    # TODO: Comandos de Mute e Unmute (requerem mais lógica, como gerenciamento de cargo ou uso de timeout do Discord)
    # @nextcord.slash_command(name="mute", description="Silencia um usuário no servidor.")
    # @application_checks.has_permissions(manage_roles=True) # ou moderate_members para timeout
    # @application_checks.bot_has_permissions(manage_roles=True) # ou moderate_members
    # async def mute(self, interaction: Interaction, usuario: Member, duracao: Optional[str] = None, motivo: Optional[str] = None):
    #     pass

    # @nextcord.slash_command(name="unmute", description="Remove o silenciamento de um usuário.")
    # @application_checks.has_permissions(manage_roles=True)
    # @application_checks.bot_has_permissions(manage_roles=True)
    # async def unmute(self, interaction: Interaction, usuario: Member, motivo: Optional[str] = None):
    #     pass

    # Listener para erros de comando de aplicação
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error: Exception):
        # Tratar erros comuns de checagem
        if isinstance(error, application_checks.ApplicationMissingPermissions):
            perms_faltantes = ", ".join([f"`{perm.replace('_', ' ').title()}`" for perm in error.missing_permissions])
            await self.send_error_embed(interaction, "Permissão Faltando (Você)", f"Você não tem as seguintes permissões para usar este comando: {perms_faltantes}")
            return
        elif isinstance(error, application_checks.ApplicationBotMissingPermissions):
            perms_faltantes = ", ".join([f"`{perm.replace('_', ' ').title()}`" for perm in error.missing_permissions])
            await self.send_error_embed(interaction, "Permissão Faltando (Eu)", f"Eu não tenho as seguintes permissões para executar este comando: {perms_faltantes}")
            return
        elif isinstance(error, application_checks.ApplicationNotOwner):
            await self.send_error_embed(interaction, "Comando Restrito", "Apenas o dono do bot pode usar este comando.")
            return
        elif isinstance(error, application_checks.ApplicationGuildOnly):
            await self.send_error_embed(interaction, "Comando de Servidor", "Este comando só pode ser usado dentro de um servidor.")
            return
        elif isinstance(error, application_checks.ApplicationNSFWChannelRequired):
            await self.send_error_embed(interaction, "Canal NSFW Requerido", "Este comando só pode ser usado em um canal marcado como NSFW.")
            return
        elif isinstance(error, application_checks.ApplicationCooldown): # Erro de cooldown para comandos de app
            retry_after_formatted = str(timedelta(seconds=int(error.retry_after))).split('.')[0] # Formata para HH:MM:SS
            await self.send_error_embed(interaction, "Comando em Cooldown", f"Este comando está em cooldown. Tente novamente em **{retry_after_formatted}**.")
            return
        
        # Erros mais genéricos ou inesperados
        # Se a interação já foi respondida (ex: por um defer), usa followup
        # Caso contrário, tenta responder diretamente.
        
        # Logar o erro completo no console para o desenvolvedor
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO CMD APP] Ignorando exceção no comando de aplicação {interaction.application_command.qualified_name if interaction.application_command else "desconhecido"}:')
        traceback.print_exception(type(error), error, error.__traceback__)

        # Enviar uma mensagem de erro genérica para o usuário
        error_message = f"Ocorreu um erro ao executar o comando `{interaction.application_command.qualified_name if interaction.application_command else "desconhecido"}`.\nJá notifiquei meu mestre sobre isso! {get_emoji(self.bot, 'sad')}"
        
        # Tentar notificar o desenvolvedor via DM
        try:
            dev_user = await self.bot.fetch_user(DEVELOPER_ID)
            if dev_user:
                error_details = f"Erro no comando `/{interaction.application_command.qualified_name if interaction.application_command else "desconhecido"}`:\n" \
                                f"Usuário: {interaction.user} ({interaction.user.id})\n" \
                                f"Servidor: {interaction.guild.name if interaction.guild else 'DM'} ({interaction.guild_id if interaction.guild else 'N/A'})\n" \
                                f"Erro: ```{type(error).__name__}: {str(error)}```"
                if len(error_details) > 1900: error_details = error_details[:1900] + "... (truncado)"
                await dev_user.send(error_details)
        except Exception as e_dev_dm:
            print(f"[WARN ERRO CMD APP] Falha ao enviar DM de erro para o desenvolvedor: {e_dev_dm}")

        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except Exception as e_resp:
            print(f"[WARN ERRO CMD APP] Falha ao enviar mensagem de erro para o usuário: {e_resp}")


def setup(bot):
    bot.add_cog(Comandos(bot))
