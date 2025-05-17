from typing import Optional # ADICIONADO PARA CORRIGIR NameError
# /home/ubuntu/ShirayukiBot/cogs/Comandos.py
# Cog principal para comandos gerais, moderação básica e o sistema de ajuda.

import nextcord
from nextcord import Interaction, Embed, SlashOption, Color, Member, User, Role, TextChannel, Permissions, AuditLogAction, Forbidden, HTTPException, ButtonStyle, NotFound
from nextcord.ext import commands
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
        "gear": "⚙️", "money": "💰", "info": "ℹ️", "dice": "🎲", "tools": "🛠️",
        "question": "❓", "music": "🎵", "interact": "🤝"
    }
    return emoji_map.get(name, "▫️") # Retorna um emoji padrão ou placeholder

# ID do servidor fornecido pelo usuário para carregamento rápido de comandos
SERVER_ID = 1367345048458498219
# ID do Desenvolvedor (Kevyn) para receber DMs
DEVELOPER_ID = 1278842453159444582
# IDs de canais (Mantidos caso sejam usados para outras coisas, mas não para sugestões/bugs)
MOD_LOG_CHANNEL_ID = None  # Canal para logs de moderação

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
        embed.set_author(
            name=f"{interaction.user.display_name} ({interaction.user.id})",
            icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
        )
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
        embed.set_author(
            name=f"{interaction.user.display_name} ({interaction.user.id})",
            icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
        )
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
        self.action = action  # "kick", "ban", "mute", "unmute"
        self.target = target
        self.moderator = moderator
        self.reason = reason or "Motivo não especificado"
        self.delete_days = delete_days  # Adicionado para o ban
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
            
            timeout_embed = Embed(
                title=f"Ação de Moderação Cancelada ({self.action.capitalize()})",
                description="Você demorou muito para confirmar a ação e ela foi cancelada.",
                color=Color.dark_gray()
            )
            
            # Tenta editar a mensagem original
            try:
                message = self.message
                if message:
                    await message.edit(embed=timeout_embed, view=self)
            except Exception as e:
                print(f"[ERRO MODERACAO] Erro ao editar mensagem após timeout: {e}")
    
    @nextcord.ui.button(label="Confirmar", style=ButtonStyle.danger, custom_id="confirm_mod_action")
    async def confirm_button(self, button: Button, interaction: Interaction):
        self.confirmed = True
        
        # Desabilita os botões
        for item in self.children:
            if isinstance(item, (Button, Select)):
                item.disabled = True
        
        # Executa a ação de moderação
        success = False
        error_message = None
        
        try:
            if self.action == "kick":
                await self.target.kick(reason=f"{self.moderator.name}: {self.reason}")
                success = True
            elif self.action == "ban":
                await self.target.ban(reason=f"{self.moderator.name}: {self.reason}", delete_message_days=self.delete_days)
                success = True
            elif self.action == "mute":
                # Implementação de mute depende da versão do Discord e da configuração do servidor
                # Esta é uma implementação simplificada usando timeout
                await self.target.edit(timeout=timedelta(minutes=60), reason=f"{self.moderator.name}: {self.reason}")
                success = True
            elif self.action == "unmute":
                # Remove o timeout
                await self.target.edit(timeout=None, reason=f"{self.moderator.name}: {self.reason}")
                success = True
        except Forbidden:
            error_message = "Não tenho permissão para executar esta ação."
        except HTTPException as e:
            error_message = f"Erro ao executar a ação: {e}"
        except Exception as e:
            error_message = f"Erro inesperado: {e}"
            traceback.print_exc()
        
        # Atualiza o embed com o resultado
        if success:
            result_embed = Embed(
                title=f"Ação de Moderação Executada: {self.action.capitalize()}",
                description=f"{self.target.mention} foi {self.action}d por {self.moderator.mention}",
                color=Color.green()
            )
            result_embed.add_field(name="Motivo", value=self.reason, inline=False)
            
            # Envia log para o canal de moderação, se configurado
            if MOD_LOG_CHANNEL_ID:
                try:
                    log_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
                    if log_channel:
                        await log_channel.send(embed=result_embed)
                except Exception as e:
                    print(f"[ERRO MODERACAO] Erro ao enviar log: {e}")
        else:
            result_embed = Embed(
                title=f"Falha na Ação de Moderação: {self.action.capitalize()}",
                description=f"Não foi possível {self.action} {self.target.mention}",
                color=Color.red()
            )
            result_embed.add_field(name="Erro", value=error_message or "Erro desconhecido", inline=False)
        
        # Edita a mensagem original
        await interaction.response.edit_message(embed=result_embed, view=self)
    
    @nextcord.ui.button(label="Cancelar", style=ButtonStyle.secondary)
    async def cancel_button(self, button: Button, interaction: Interaction):
        self.confirmed = True  # Marca como confirmado para evitar o timeout
        
        # Desabilita os botões
        for item in self.children:
            if isinstance(item, (Button, Select)):
                item.disabled = True
        
        cancel_embed = Embed(
            title=f"Ação de Moderação Cancelada: {self.action.capitalize()}",
            description=f"A ação contra {self.target.mention} foi cancelada por {self.moderator.mention}",
            color=Color.dark_gray()
        )
        
        await interaction.response.edit_message(embed=cancel_embed, view=self)

# View para Ajuda
class HelpView(View):
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.current_page = "main"
        self.current_embed = None
    
    # Método para criar o embed principal de ajuda
    def create_main_help_embed(self):
        embed = Embed(
            title="📚 Sistema de Ajuda da Shirayuki",
            description="Selecione uma categoria abaixo para ver os comandos disponíveis.",
            color=Color.blue()
        )
        
        # Adiciona campos para cada categoria
        embed.add_field(
            name=f"{get_emoji(self.bot, 'gear')} Comandos Gerais",
            value="Comandos básicos e utilitários.",
            inline=True
        )
        embed.add_field(
            name=f"{get_emoji(self.bot, 'money')} Economia",
            value="Sistema de economia e loja.",
            inline=True
        )
        embed.add_field(
            name=f"{get_emoji(self.bot, 'dice')} Jogos",
            value="Mini-jogos e diversão.",
            inline=True
        )
        embed.add_field(
            name=f"{get_emoji(self.bot, 'music')} Música",
            value="Comandos para tocar música.",
            inline=True
        )
        embed.add_field(
            name=f"{get_emoji(self.bot, 'interact')} Interações",
            value="Interações sociais com outros usuários.",
            inline=True
        )
        embed.add_field(
            name=f"{get_emoji(self.bot, 'hammer')} Moderação",
            value="Comandos para moderadores.",
            inline=True
        )
        
        embed.set_footer(text="Use o menu suspenso abaixo para navegar entre as categorias.")
        return embed
    
    # Método para criar embeds de categorias específicas
    def create_category_embed(self, category):
        categories = {
            "general": {
                "title": f"{get_emoji(self.bot, 'gear')} Comandos Gerais",
                "description": "Comandos básicos e utilitários para todos os usuários.",
                "commands": [
                    {"name": "/ping", "value": "Verifica a latência do bot."},
                    {"name": "/info", "value": "Mostra informações sobre o bot."},
                    {"name": "/sugerir", "value": "Envia uma sugestão para o desenvolvedor."},
                    {"name": "/reportar", "value": "Reporta um bug para o desenvolvedor."},
                    {"name": "/avatar", "value": "Mostra o avatar de um usuário."},
                    {"name": "/serverinfo", "value": "Mostra informações sobre o servidor."},
                    {"name": "/userinfo", "value": "Mostra informações sobre um usuário."}
                ],
                "color": Color.blue()
            },
            "economy": {
                "title": f"{get_emoji(self.bot, 'money')} Economia",
                "description": "Comandos do sistema de economia e loja.",
                "commands": [
                    {"name": "/saldo", "value": "Verifica seu saldo atual."},
                    {"name": "/daily", "value": "Recebe sua recompensa diária."},
                    {"name": "/trabalhar", "value": "Trabalha para ganhar moedas."},
                    {"name": "/loja", "value": "Abre a loja para comprar itens."},
                    {"name": "/inventario", "value": "Mostra seu inventário de itens."},
                    {"name": "/transferir", "value": "Transfere moedas para outro usuário."}
                ],
                "color": Color.gold()
            },
            "games": {
                "title": f"{get_emoji(self.bot, 'dice')} Jogos",
                "description": "Mini-jogos e comandos de diversão.",
                "commands": [
                    {"name": "/rolardado", "value": "Rola um dado com o número de faces especificado."},
                    {"name": "/caracoroa", "value": "Joga cara ou coroa."},
                    {"name": "/8ball", "value": "Faz uma pergunta e recebe uma resposta aleatória."},
                    {"name": "/pedrapapeltesoura", "value": "Joga pedra, papel e tesoura contra o bot."},
                    {"name": "/apostar", "value": "Aposta moedas em um jogo de azar."}
                ],
                "color": Color.purple()
            },
            "music": {
                "title": f"{get_emoji(self.bot, 'music')} Música",
                "description": "Comandos para tocar música no canal de voz.",
                "commands": [
                    {"name": "/tocar", "value": "Toca uma música ou adiciona à fila."},
                    {"name": "/fila", "value": "Mostra a fila de músicas atual."},
                    {"name": "/pular", "value": "Pula para a próxima música na fila."},
                    {"name": "/pausar", "value": "Pausa a música atual."},
                    {"name": "/continuar", "value": "Continua a música pausada."},
                    {"name": "/parar", "value": "Para a música e limpa a fila."},
                    {"name": "/volume", "value": "Ajusta o volume da música."}
                ],
                "color": Color.red()
            },
            "interactions": {
                "title": f"{get_emoji(self.bot, 'interact')} Interações",
                "description": "Comandos de interação social com outros usuários.",
                "commands": [
                    {"name": "/interacao lista", "value": "Lista todas as interações disponíveis."},
                    {"name": "/interacao stats", "value": "Mostra suas estatísticas de interação."},
                    {"name": "/interacao [tipo]", "value": "Interage com outro usuário (ex: abraçar, cumprimentar, etc)."}
                ],
                "color": Color.pink()
            },
            "moderation": {
                "title": f"{get_emoji(self.bot, 'hammer')} Moderação",
                "description": "Comandos para moderadores do servidor.",
                "commands": [
                    {"name": "/kick", "value": "Expulsa um usuário do servidor."},
                    {"name": "/ban", "value": "Bane um usuário do servidor."},
                    {"name": "/unban", "value": "Remove o banimento de um usuário."},
                    {"name": "/mute", "value": "Silencia um usuário temporariamente."},
                    {"name": "/unmute", "value": "Remove o silenciamento de um usuário."},
                    {"name": "/limpar", "value": "Limpa mensagens do canal."},
                    {"name": "/slowmode", "value": "Define o modo lento do canal."}
                ],
                "color": Color.dark_red()
            }
        }
        
        if category not in categories:
            return self.create_main_help_embed()
        
        cat_data = categories[category]
        embed = Embed(
            title=cat_data["title"],
            description=cat_data["description"],
            color=cat_data["color"]
        )
        
        for cmd in cat_data["commands"]:
            embed.add_field(name=cmd["name"], value=cmd["value"], inline=False)
        
        embed.set_footer(text="Use o menu suspenso abaixo para navegar entre as categorias.")
        return embed
    
    # Dropdown para seleção de categoria
    @nextcord.ui.select(
        placeholder="Selecione uma categoria...",
        options=[
            nextcord.SelectOption(label="Menu Principal", value="main", emoji="🏠"),
            nextcord.SelectOption(label="Comandos Gerais", value="general", emoji="⚙️"),
            nextcord.SelectOption(label="Economia", value="economy", emoji="💰"),
            nextcord.SelectOption(label="Jogos", value="games", emoji="🎲"),
            nextcord.SelectOption(label="Música", value="music", emoji="🎵"),
            nextcord.SelectOption(label="Interações", value="interactions", emoji="🤝"),
            nextcord.SelectOption(label="Moderação", value="moderation", emoji="🔨")
        ]
    )
    async def select_category(self, select: Select, interaction: Interaction):
        self.current_page = select.values[0]
        
        if self.current_page == "main":
            self.current_embed = self.create_main_help_embed()
        else:
            self.current_embed = self.create_category_embed(self.current_page)
        
        await interaction.response.edit_message(embed=self.current_embed)
    
    # Botão para sugerir comandos
    @nextcord.ui.button(label="Sugerir Comando", style=ButtonStyle.primary, row=1)
    async def suggest_command_button(self, button: Button, interaction: Interaction):
        modal = SuggestionModal(self.bot)
        await interaction.response.send_modal(modal)
    
    # Botão para reportar bugs
    @nextcord.ui.button(label="Reportar Bug", style=ButtonStyle.danger, row=1)
    async def report_bug_button(self, button: Button, interaction: Interaction):
        modal = BugReportModal(self.bot)
        await interaction.response.send_modal(modal)

class Comandos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)
    
    # Evento de erro em comandos de aplicação
    @nextcord.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        # Verifica se o erro é de um comando desta cog
        # Não podemos mais usar cog_name, então verificamos de outra forma
        if hasattr(interaction, 'application_command'):
            # Verifica tipos específicos de erros
            if isinstance(error, commands.CommandOnCooldown):
                await interaction.response.send_message(
                    f"{get_emoji(self.bot, 'warn')} Este comando está em cooldown. Tente novamente em {error.retry_after:.1f} segundos.",
                    ephemeral=True
                )
            elif isinstance(error, commands.MissingPermissions):
                await interaction.response.send_message(
                    f"{get_emoji(self.bot, 'warn')} Você não tem permissão para usar este comando.",
                    ephemeral=True
                )
            # Removido o check de ApplicationGuildOnly que não existe mais
            elif isinstance(error, commands.NoPrivateMessage):
                await interaction.response.send_message(
                    f"{get_emoji(self.bot, 'warn')} Este comando não pode ser usado em mensagens privadas.",
                    ephemeral=True
                )
            else:
                # Erro genérico
                try:
                    await interaction.response.send_message(
                        f"{get_emoji(self.bot, 'warn')} Ocorreu um erro ao executar este comando: {str(error)}",
                        ephemeral=True
                    )
                except nextcord.errors.InteractionResponded:
                    # Se a interação já foi respondida, tenta usar followup
                    try:
                        await interaction.followup.send(
                            f"{get_emoji(self.bot, 'warn')} Ocorreu um erro ao executar este comando: {str(error)}",
                            ephemeral=True
                        )
                    except Exception as e:
                        print(f"[ERRO COMANDO] Erro ao enviar mensagem de erro: {e}")
                
                # Loga o erro para debug
                print(f"[ERRO COMANDO] {error}")
                traceback.print_exception(type(error), error, error.__traceback__)
    
    # Comando de ping
    @nextcord.slash_command(
        name="ping",
        description="Verifica a latência do bot."
    )
    async def ping(self, interaction: Interaction):
        start_time = time.time()
        await interaction.response.defer(ephemeral=False)
        end_time = time.time()
        
        api_latency = round((end_time - start_time) * 1000)
        websocket_latency = round(self.bot.latency * 1000)
        
        embed = Embed(
            title="🏓 Pong!",
            description=f"**API**: {api_latency}ms\n**WebSocket**: {websocket_latency}ms",
            color=Color.green() if websocket_latency < 200 else Color.orange() if websocket_latency < 500 else Color.red()
        )
        
        await interaction.followup.send(embed=embed)
    
    # Comando de informações do bot
    @nextcord.slash_command(
        name="info",
        description="Mostra informações sobre o bot."
    )
    async def info(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=False)
        
        # Coleta informações do sistema
        uptime = datetime.now(timezone.utc) - self.start_time
        days, remainder = divmod(int(uptime.total_seconds()), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        
        # Informações do sistema
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Informações do bot
        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count for guild in self.bot.guilds)
        
        embed = Embed(
            title=f"ℹ️ Informações da Shirayuki",
            color=Color.blue()
        )
        
        # Adiciona campos com as informações
        embed.add_field(name="Versão", value="1.0.0", inline=True)
        embed.add_field(name="Desenvolvedor", value="<@1278842453159444582>", inline=True)
        embed.add_field(name="Biblioteca", value=f"Nextcord {nextcord.__version__}", inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="Sistema", value=platform.system(), inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="CPU", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="Memória", value=f"{memory_usage}%", inline=True)
        embed.add_field(name="Servidores", value=str(guild_count), inline=True)
        embed.add_field(name="Usuários", value=str(user_count), inline=True)
        
        # Adiciona links úteis
        embed.add_field(
            name="Links",
            value="[Convite](https://discord.com/api/oauth2/authorize?client_id=1367345048458498219&permissions=8&scope=bot%20applications.commands) | [Suporte](https://discord.gg/seu-servidor) | [GitHub](https://github.com/iamkevyn/ShirayukiBot)",
            inline=False
        )
        
        # Define o thumbnail como o avatar do bot
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        await interaction.followup.send(embed=embed)
    
    # Comando de sugestão
    @nextcord.slash_command(
        name="sugerir",
        description="Envia uma sugestão para o desenvolvedor do bot."
    )
    async def suggest(self, interaction: Interaction):
        modal = SuggestionModal(self.bot)
        await interaction.response.send_modal(modal)
    
    # Comando de reportar bug
    @nextcord.slash_command(
        name="reportar",
        description="Reporta um bug para o desenvolvedor do bot."
    )
    async def report_bug(self, interaction: Interaction):
        modal = BugReportModal(self.bot)
        await interaction.response.send_modal(modal)
    
    # Comando de avatar
    @nextcord.slash_command(
        name="avatar",
        description="Mostra o avatar de um usuário."
    )
    async def avatar(
        self,
        interaction: Interaction,
        usuario: User = SlashOption(
            name="usuario",
            description="Usuário para mostrar o avatar (opcional, padrão: você mesmo)",
            required=False
        )
    ):
        target = usuario or interaction.user
        
        embed = Embed(
            title=f"Avatar de {target.display_name}",
            color=Color.blue()
        )
        
        if target.avatar:
            embed.set_image(url=target.avatar.url)
            embed.description = f"[Link do Avatar]({target.avatar.url})"
        else:
            embed.description = "Este usuário não possui um avatar personalizado."
        
        await interaction.response.send_message(embed=embed)
    
    # Comando de informações do servidor
    @nextcord.slash_command(
        name="serverinfo",
        description="Mostra informações sobre o servidor."
    )
    # Usando commands.guild_only() em vez de application_checks.guild_only()
    @commands.guild_only()
    async def serverinfo(self, interaction: Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Este comando só pode ser usado em servidores.", ephemeral=True)
            return
        
        # Coleta informações do servidor
        created_at = guild.created_at.replace(tzinfo=timezone.utc)
        created_time = int(created_at.timestamp())
        
        # Contagem de canais
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        # Contagem de membros
        total_members = guild.member_count
        humans = sum(1 for member in guild.members if not member.bot)
        bots = total_members - humans
        
        # Contagem de emojis e boosts
        emoji_count = len(guild.emojis)
        boost_count = guild.premium_subscription_count
        
        embed = Embed(
            title=f"ℹ️ Informações do Servidor: {guild.name}",
            description=f"**ID:** {guild.id}\n**Criado em:** <t:{created_time}:F> (<t:{created_time}:R>)",
            color=Color.blue()
        )
        
        # Adiciona o ícone do servidor como thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Adiciona campos com as informações
        embed.add_field(name="Dono", value=f"{guild.owner.mention if guild.owner else 'Desconhecido'}", inline=True)
        embed.add_field(name="Região", value="Automática", inline=True)  # Discord agora usa região automática
        embed.add_field(name="Nível de Boost", value=f"{guild.premium_tier} ({boost_count} boosts)", inline=True)
        
        embed.add_field(name="Membros", value=f"Total: {total_members}\nHumanos: {humans}\nBots: {bots}", inline=True)
        embed.add_field(name="Canais", value=f"Texto: {text_channels}\nVoz: {voice_channels}\nCategorias: {categories}", inline=True)
        embed.add_field(name="Emojis", value=f"{emoji_count}/{guild.emoji_limit}", inline=True)
        
        # Adiciona informações de segurança
        verification_level = {
            nextcord.VerificationLevel.none: "Nenhum",
            nextcord.VerificationLevel.low: "Baixo",
            nextcord.VerificationLevel.medium: "Médio",
            nextcord.VerificationLevel.high: "Alto",
            nextcord.VerificationLevel.highest: "Muito Alto"
        }.get(guild.verification_level, "Desconhecido")
        
        content_filter = {
            nextcord.ContentFilter.disabled: "Desativado",
            nextcord.ContentFilter.no_role: "Membros sem cargo",
            nextcord.ContentFilter.all_members: "Todos os membros"
        }.get(guild.explicit_content_filter, "Desconhecido")
        
        embed.add_field(name="Nível de Verificação", value=verification_level, inline=True)
        embed.add_field(name="Filtro de Conteúdo", value=content_filter, inline=True)
        embed.add_field(name="Cargos", value=f"{len(guild.roles)} cargos", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    # Comando de informações do usuário
    @nextcord.slash_command(
        name="userinfo",
        description="Mostra informações sobre um usuário."
    )
    async def userinfo(
        self,
        interaction: Interaction,
        usuario: User = SlashOption(
            name="usuario",
            description="Usuário para mostrar informações (opcional, padrão: você mesmo)",
            required=False
        )
    ):
        target = usuario or interaction.user
        member = None
        
        if interaction.guild:
            member = interaction.guild.get_member(target.id)
        
        embed = Embed(
            title=f"ℹ️ Informações do Usuário: {target.display_name}",
            color=Color.blue()
        )
        
        # Adiciona o avatar como thumbnail
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
        
        # Informações básicas
        created_at = target.created_at.replace(tzinfo=timezone.utc)
        created_time = int(created_at.timestamp())
        embed.add_field(name="ID", value=target.id, inline=True)
        embed.add_field(name="Bot", value="Sim" if target.bot else "Não", inline=True)
        embed.add_field(name="Conta Criada", value=f"<t:{created_time}:F> (<t:{created_time}:R>)", inline=False)
        
        # Informações específicas do servidor (se disponíveis)
        if member:
            joined_at = member.joined_at.replace(tzinfo=timezone.utc) if member.joined_at else None
            joined_time = int(joined_at.timestamp()) if joined_at else None
            
            if joined_time:
                embed.add_field(name="Entrou no Servidor", value=f"<t:{joined_time}:F> (<t:{joined_time}:R>)", inline=False)
            
            # Cargos
            roles = [role.mention for role in member.roles if role.name != "@everyone"]
            roles_str = ", ".join(roles) if roles else "Nenhum"
            
            if len(roles_str) > 1024:
                roles_str = f"{len(roles)} cargos (muitos para mostrar)"
            
            embed.add_field(name="Cargos", value=roles_str, inline=False)
            
            # Status de boost
            if member.premium_since:
                boost_time = int(member.premium_since.replace(tzinfo=timezone.utc).timestamp())
                embed.add_field(name="Boosting Desde", value=f"<t:{boost_time}:F> (<t:{boost_time}:R>)", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    # Comando de ajuda
    @nextcord.slash_command(
        name="ajuda",
        description="Mostra o menu de ajuda com todos os comandos disponíveis."
    )
    async def help(self, interaction: Interaction):
        view = HelpView(self.bot)
        view.current_embed = view.create_main_help_embed()
        
        await interaction.response.send_message(embed=view.current_embed, view=view)
    
    # Comando de teste (para verificar se o bot está funcionando)
    @nextcord.slash_command(
        name="testemainslash",
        description="Comando de teste para verificar se o bot está funcionando."
    )
    async def test_main_slash(self, interaction: Interaction):
        print(f"--- [TESTE MAIN SLASH] Comando /testemainslash executado por {interaction.user.name} ---")
        await interaction.response.send_message("✅ O bot está funcionando corretamente! Este é um comando de teste.")
        print(f"--- [TESTE MAIN SLASH] Resposta enviada. ---")
    
    # Comandos de moderação
    
    # Comando de kick
    @nextcord.slash_command(
        name="kick",
        description="Expulsa um usuário do servidor."
    )
    # Usando commands.has_permissions em vez de application_checks
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(
        self,
        interaction: Interaction,
        usuario: Member = SlashOption(
            name="usuario",
            description="Usuário para expulsar",
            required=True
        ),
        motivo: str = SlashOption(
            name="motivo",
            description="Motivo da expulsão",
            required=False
        )
    ):
        # Verifica se o bot tem permissão para expulsar
        if not interaction.guild.me.guild_permissions.kick_members:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não tenho permissão para expulsar membros.", ephemeral=True)
            return
        
        # Verifica se o alvo é o próprio usuário
        if usuario.id == interaction.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode expulsar a si mesmo.", ephemeral=True)
            return
        
        # Verifica se o alvo é o dono do servidor
        if usuario.id == interaction.guild.owner_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode expulsar o dono do servidor.", ephemeral=True)
            return
        
        # Verifica hierarquia de cargos
        if interaction.user.id != interaction.guild.owner_id and usuario.top_role >= interaction.user.top_role:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode expulsar alguém com cargo igual ou superior ao seu.", ephemeral=True)
            return
        
        # Verifica hierarquia de cargos do bot
        if usuario.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não posso expulsar alguém com cargo superior ao meu.", ephemeral=True)
            return
        
        # Cria o embed de confirmação
        embed = Embed(
            title=f"{get_emoji(self.bot, 'hammer')} Confirmação de Kick",
            description=f"Você está prestes a expulsar {usuario.mention} do servidor.",
            color=Color.orange()
        )
        embed.add_field(name="Motivo", value=motivo or "Nenhum motivo especificado", inline=False)
        embed.set_footer(text="Esta ação será registrada nos logs do servidor.")
        
        # Cria a view de confirmação
        view = ConfirmModerationView(self.bot, "kick", usuario, interaction.user, motivo)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # Comando de ban
    @nextcord.slash_command(
        name="ban",
        description="Bane um usuário do servidor."
    )
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(
        self,
        interaction: Interaction,
        usuario: Member = SlashOption(
            name="usuario",
            description="Usuário para banir",
            required=True
        ),
        motivo: str = SlashOption(
            name="motivo",
            description="Motivo do banimento",
            required=False
        ),
        apagar_mensagens: int = SlashOption(
            name="apagar_mensagens",
            description="Dias de mensagens para apagar (0-7)",
            required=False,
            min_value=0,
            max_value=7
        )
    ):
        # Define o valor padrão para apagar_mensagens
        if apagar_mensagens is None:
            apagar_mensagens = 0
        
        # Verifica se o bot tem permissão para banir
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não tenho permissão para banir membros.", ephemeral=True)
            return
        
        # Verifica se o alvo é o próprio usuário
        if usuario.id == interaction.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode banir a si mesmo.", ephemeral=True)
            return
        
        # Verifica se o alvo é o dono do servidor
        if usuario.id == interaction.guild.owner_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode banir o dono do servidor.", ephemeral=True)
            return
        
        # Verifica hierarquia de cargos
        if interaction.user.id != interaction.guild.owner_id and usuario.top_role >= interaction.user.top_role:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode banir alguém com cargo igual ou superior ao seu.", ephemeral=True)
            return
        
        # Verifica hierarquia de cargos do bot
        if usuario.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não posso banir alguém com cargo superior ao meu.", ephemeral=True)
            return
        
        # Cria o embed de confirmação
        embed = Embed(
            title=f"{get_emoji(self.bot, 'hammer')} Confirmação de Ban",
            description=f"Você está prestes a banir {usuario.mention} do servidor.",
            color=Color.red()
        )
        embed.add_field(name="Motivo", value=motivo or "Nenhum motivo especificado", inline=False)
        embed.add_field(name="Apagar Mensagens", value=f"{apagar_mensagens} dias", inline=False)
        embed.set_footer(text="Esta ação será registrada nos logs do servidor.")
        
        # Cria a view de confirmação
        view = ConfirmModerationView(self.bot, "ban", usuario, interaction.user, motivo, apagar_mensagens)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # Comando de unban
    @nextcord.slash_command(
        name="unban",
        description="Remove o banimento de um usuário."
    )
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(
        self,
        interaction: Interaction,
        usuario_id: str = SlashOption(
            name="id_usuario",
            description="ID do usuário para desbanir",
            required=True
        ),
        motivo: str = SlashOption(
            name="motivo",
            description="Motivo do desbanimento",
            required=False
        )
    ):
        # Verifica se o bot tem permissão para desbanir
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não tenho permissão para desbanir membros.", ephemeral=True)
            return
        
        # Verifica se o ID é válido
        try:
            user_id = int(usuario_id)
        except ValueError:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} ID de usuário inválido. Deve ser um número.", ephemeral=True)
            return
        
        # Verifica se o usuário está banido
        try:
            ban_entry = await interaction.guild.fetch_ban(nextcord.Object(id=user_id))
            banned_user = ban_entry.user
        except NotFound:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Usuário com ID {user_id} não está banido.", ephemeral=True)
            return
        except HTTPException as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Erro ao verificar banimento: {e}", ephemeral=True)
            return
        
        # Tenta desbanir o usuário
        try:
            await interaction.guild.unban(banned_user, reason=f"{interaction.user.name}: {motivo or 'Nenhum motivo especificado'}")
            
            # Cria o embed de sucesso
            embed = Embed(
                title=f"{get_emoji(self.bot, 'hammer')} Usuário Desbanido",
                description=f"**{banned_user}** ({banned_user.id}) foi desbanido com sucesso.",
                color=Color.green()
            )
            embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
            embed.add_field(name="Motivo", value=motivo or "Nenhum motivo especificado", inline=True)
            
            # Envia log para o canal de moderação, se configurado
            if MOD_LOG_CHANNEL_ID:
                try:
                    log_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
                    if log_channel:
                        await log_channel.send(embed=embed)
                except Exception as e:
                    print(f"[ERRO MODERACAO] Erro ao enviar log de unban: {e}")
            
            await interaction.response.send_message(embed=embed)
        except HTTPException as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Erro ao desbanir usuário: {e}", ephemeral=True)
    
    # Comando de limpar mensagens
    @nextcord.slash_command(
        name="limpar",
        description="Limpa mensagens do canal."
    )
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear(
        self,
        interaction: Interaction,
        quantidade: int = SlashOption(
            name="quantidade",
            description="Número de mensagens para limpar (1-100)",
            required=True,
            min_value=1,
            max_value=100
        ),
        usuario: User = SlashOption(
            name="usuario",
            description="Limpar apenas mensagens deste usuário (opcional)",
            required=False
        )
    ):
        # Verifica se o bot tem permissão para gerenciar mensagens
        if not interaction.guild.me.guild_permissions.manage_messages:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não tenho permissão para gerenciar mensagens.", ephemeral=True)
            return
        
        # Adia a resposta para evitar que a mensagem de resposta seja deletada
        await interaction.response.defer(ephemeral=True)
        
        # Define a função de verificação para filtrar mensagens de um usuário específico
        def check_user(message):
            return usuario is None or message.author.id == usuario.id
        
        try:
            # Limpa as mensagens
            if usuario:
                # Se um usuário foi especificado, precisamos filtrar as mensagens
                deleted = 0
                async for message in interaction.channel.history(limit=500):
                    if check_user(message) and deleted < quantidade:
                        await message.delete()
                        deleted += 1
                        # Pequeno delay para evitar rate limits
                        if deleted % 5 == 0:
                            await asyncio.sleep(0.5)
                    
                    if deleted >= quantidade:
                        break
            else:
                # Se nenhum usuário foi especificado, podemos usar purge
                deleted = await interaction.channel.purge(limit=quantidade)
                deleted = len(deleted)
            
            # Envia mensagem de sucesso
            user_str = f" de {usuario.mention}" if usuario else ""
            await interaction.followup.send(f"{get_emoji(self.bot, 'trash')} {deleted} mensagens{user_str} foram limpas com sucesso!", ephemeral=True)
        except HTTPException as e:
            await interaction.followup.send(f"{get_emoji(self.bot, 'warn')} Erro ao limpar mensagens: {e}", ephemeral=True)
    
    # Comando de slowmode
    @nextcord.slash_command(
        name="slowmode",
        description="Define o modo lento do canal."
    )
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def slowmode(
        self,
        interaction: Interaction,
        segundos: int = SlashOption(
            name="segundos",
            description="Segundos de delay (0-21600, 0 para desativar)",
            required=True,
            min_value=0,
            max_value=21600
        ),
        canal: TextChannel = SlashOption(
            name="canal",
            description="Canal para definir o modo lento (opcional, padrão: canal atual)",
            required=False
        )
    ):
        # Verifica se o bot tem permissão para gerenciar canais
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não tenho permissão para gerenciar canais.", ephemeral=True)
            return
        
        # Define o canal alvo
        target_channel = canal or interaction.channel
        
        try:
            # Define o modo lento
            await target_channel.edit(slowmode_delay=segundos)
            
            # Mensagem de sucesso
            if segundos == 0:
                await interaction.response.send_message(f"{get_emoji(self.bot, 'gear')} Modo lento desativado em {target_channel.mention}.")
            else:
                # Formata o tempo de forma legível
                if segundos < 60:
                    time_str = f"{segundos} segundo{'s' if segundos != 1 else ''}"
                elif segundos < 3600:
                    minutes = segundos // 60
                    time_str = f"{minutes} minuto{'s' if minutes != 1 else ''}"
                else:
                    hours = segundos // 3600
                    minutes = (segundos % 3600) // 60
                    time_str = f"{hours} hora{'s' if hours != 1 else ''}"
                    if minutes > 0:
                        time_str += f" e {minutes} minuto{'s' if minutes != 1 else ''}"
                
                await interaction.response.send_message(f"{get_emoji(self.bot, 'gear')} Modo lento definido para {time_str} em {target_channel.mention}.")
        except HTTPException as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Erro ao definir modo lento: {e}", ephemeral=True)
    
    # Comando de mute (timeout)
    @nextcord.slash_command(
        name="mute",
        description="Silencia um usuário temporariamente."
    )
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def mute(
        self,
        interaction: Interaction,
        usuario: Member = SlashOption(
            name="usuario",
            description="Usuário para silenciar",
            required=True
        ),
        duracao: int = SlashOption(
            name="duracao",
            description="Duração em minutos (1-40320, máximo de 28 dias)",
            required=True,
            min_value=1,
            max_value=40320
        ),
        motivo: str = SlashOption(
            name="motivo",
            description="Motivo do silenciamento",
            required=False
        )
    ):
        # Verifica se o bot tem permissão para moderar membros
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não tenho permissão para silenciar membros.", ephemeral=True)
            return
        
        # Verifica se o alvo é o próprio usuário
        if usuario.id == interaction.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode silenciar a si mesmo.", ephemeral=True)
            return
        
        # Verifica se o alvo é o dono do servidor
        if usuario.id == interaction.guild.owner_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode silenciar o dono do servidor.", ephemeral=True)
            return
        
        # Verifica hierarquia de cargos
        if interaction.user.id != interaction.guild.owner_id and usuario.top_role >= interaction.user.top_role:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode silenciar alguém com cargo igual ou superior ao seu.", ephemeral=True)
            return
        
        # Verifica hierarquia de cargos do bot
        if usuario.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não posso silenciar alguém com cargo superior ao meu.", ephemeral=True)
            return
        
        # Cria o embed de confirmação
        embed = Embed(
            title=f"{get_emoji(self.bot, 'hammer')} Confirmação de Mute",
            description=f"Você está prestes a silenciar {usuario.mention} por {duracao} minutos.",
            color=Color.orange()
        )
        embed.add_field(name="Motivo", value=motivo or "Nenhum motivo especificado", inline=False)
        embed.set_footer(text="Esta ação será registrada nos logs do servidor.")
        
        # Cria a view de confirmação
        view = ConfirmModerationView(self.bot, "mute", usuario, interaction.user, motivo)
        
        # Armazena a duração para uso posterior
        view.duration = timedelta(minutes=duracao)
        
        # Modifica o callback do botão de confirmação para usar a duração
        original_callback = view.confirm_button.callback
        
        async def new_callback(button, button_interaction):
            # Desabilita os botões
            for item in view.children:
                if isinstance(item, (Button, Select)):
                    item.disabled = True
            
            # Executa a ação de mute
            success = False
            error_message = None
            
            try:
                await usuario.edit(timeout=view.duration, reason=f"{interaction.user.name}: {view.reason}")
                success = True
            except Forbidden:
                error_message = "Não tenho permissão para silenciar este usuário."
            except HTTPException as e:
                error_message = f"Erro ao silenciar usuário: {e}"
            except Exception as e:
                error_message = f"Erro inesperado: {e}"
                traceback.print_exc()
            
            # Atualiza o embed com o resultado
            if success:
                result_embed = Embed(
                    title=f"Ação de Moderação Executada: Mute",
                    description=f"{usuario.mention} foi silenciado por {duracao} minutos por {interaction.user.mention}",
                    color=Color.green()
                )
                result_embed.add_field(name="Motivo", value=view.reason, inline=False)
                
                # Envia log para o canal de moderação, se configurado
                if MOD_LOG_CHANNEL_ID:
                    try:
                        log_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
                        if log_channel:
                            await log_channel.send(embed=result_embed)
                    except Exception as e:
                        print(f"[ERRO MODERACAO] Erro ao enviar log: {e}")
            else:
                result_embed = Embed(
                    title=f"Falha na Ação de Moderação: Mute",
                    description=f"Não foi possível silenciar {usuario.mention}",
                    color=Color.red()
                )
                result_embed.add_field(name="Erro", value=error_message or "Erro desconhecido", inline=False)
            
            # Edita a mensagem original
            await button_interaction.response.edit_message(embed=result_embed, view=view)
        
        # Substitui o callback
        view.confirm_button.callback = new_callback
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # Comando de unmute
    @nextcord.slash_command(
        name="unmute",
        description="Remove o silenciamento de um usuário."
    )
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def unmute(
        self,
        interaction: Interaction,
        usuario: Member = SlashOption(
            name="usuario",
            description="Usuário para remover o silenciamento",
            required=True
        ),
        motivo: str = SlashOption(
            name="motivo",
            description="Motivo da remoção do silenciamento",
            required=False
        )
    ):
        # Verifica se o bot tem permissão para moderar membros
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Não tenho permissão para remover silenciamento de membros.", ephemeral=True)
            return
        
        # Verifica se o usuário está silenciado
        if not usuario.is_timed_out():
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Este usuário não está silenciado.", ephemeral=True)
            return
        
        # Cria o embed de confirmação
        embed = Embed(
            title=f"{get_emoji(self.bot, 'hammer')} Confirmação de Unmute",
            description=f"Você está prestes a remover o silenciamento de {usuario.mention}.",
            color=Color.green()
        )
        embed.add_field(name="Motivo", value=motivo or "Nenhum motivo especificado", inline=False)
        embed.set_footer(text="Esta ação será registrada nos logs do servidor.")
        
        # Cria a view de confirmação
        view = ConfirmModerationView(self.bot, "unmute", usuario, interaction.user, motivo)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Função setup para carregar a cog
def setup(bot):
    bot.add_cog(Comandos(bot))
