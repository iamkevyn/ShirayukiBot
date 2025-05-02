# /home/ubuntu/ShirayukiBot/cogs/Informacoes.py
# Cog para comandos de informação.

import platform
import psutil
import datetime
import time
import random
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Embed, Color, SlashOption, Member, Role, TextChannel, VoiceChannel, CategoryChannel, ForumChannel, StageChannel, User, Invite, Sticker, PartialEmoji
from nextcord.ui import View, Select, Button
from nextcord.utils import format_dt # Importar format_dt para formatação de data/hora

# Importar helper de emojis
from utils.emojis import get_emoji

# --- Constantes do Bot (Podem ser movidas para config) ---
CRIADOR_ID = 1278842453159444582
DATA_CRIACAO_STR = "22 de Abril de 2025"
PRIMEIRO_SERVIDOR = "Jardim Secreto"
SLOGAN = "Um Bot Para A Vida!"
SERVER_ID = 1367345048458498219 # Para registro rápido de comandos
GITHUB_REPO_URL = "https://github.com/iamkevyn/ShirayukiBot"
ITEMS_PER_PAGE = 10 # Para paginação

# --- Funções Auxiliares --- 
def format_timedelta(delta):
    """Formata um timedelta em dias, horas, minutos, segundos."""
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts: # Mostra segundos se for a única unidade ou se for 0s
        parts.append(f"{seconds}s")
    return " ".join(parts)

def get_member_status_counts(guild: nextcord.Guild) -> dict:
    """Conta membros por status."""
    status_counts = {
        "online": 0,
        "idle": 0,
        "dnd": 0,
        "offline": 0,
        "streaming": 0,
        "mobile": 0, # Conta quantos estão em mobile (independente do status principal)
    }
    for member in guild.members:
        if member.status == nextcord.Status.online:
            status_counts["online"] += 1
        elif member.status == nextcord.Status.idle:
            status_counts["idle"] += 1
        elif member.status == nextcord.Status.dnd:
            status_counts["dnd"] += 1
        elif member.status == nextcord.Status.offline:
            status_counts["offline"] += 1
        
        if member.activity and isinstance(member.activity, nextcord.Streaming):
            status_counts["streaming"] += 1
            
        # Verifica status mobile (pode coexistir com online, idle, dnd)
        # Nota: A API pode não fornecer isso de forma consistente ou para todos os clientes.
        # Vamos verificar se o status mobile está presente em alguma das presenças.
        if any(p.is_on_mobile() for p in member.presences):
             status_counts["mobile"] += 1
             
    return status_counts

def format_permissions(permissions: nextcord.Permissions) -> str:
    """Formata uma lista de permissões habilitadas."""
    enabled_perms = [name.replace("_", " ").replace("guild", "server").title() 
                     for name, value in permissions 
                     if value]
    if not enabled_perms:
        return "Nenhuma permissão especial."
    return ", ".join(enabled_perms)

# --- Views e Selects (Painel de Informações) ---
class InfoView(View):
    def __init__(self, bot, bot_start_time):
        super().__init__(timeout=180) # Timeout de 3 minutos
        self.add_item(InfoSelect(bot, bot_start_time))

class InfoSelect(Select):
    def __init__(self, bot, bot_start_time):
        self.bot = bot
        self.bot_start_time = bot_start_time
        options = [
            nextcord.SelectOption(label="Sobre o Bot", description="Informações gerais sobre Shirayuki", emoji="🤖"),
            nextcord.SelectOption(label="Usuário", description="Dados do seu perfil no servidor", emoji="👤"),
            nextcord.SelectOption(label="Servidor", description="Informações do servidor atual", emoji="🌐"),
            nextcord.SelectOption(label="Sistema", description="Status e uso de sistema do bot", emoji="💻"),
            nextcord.SelectOption(label="Avatar", description="Veja seu avatar ou de outro membro", emoji="🖼️"),
            nextcord.SelectOption(label="Uptime", description="Tempo online do bot desde a inicialização", emoji="⏱️"),
            nextcord.SelectOption(label="Cargos do Usuário", description="Veja seus cargos neste servidor", emoji="👥"),
            nextcord.SelectOption(label="Banner do Usuário", description="Veja seu banner ou de outro membro", emoji="<:_:1366996885398749254>"), # Usando emoji peek
            nextcord.SelectOption(label="Emojis do Servidor", description="Lista os emojis personalizados deste servidor", emoji="😀"),
            nextcord.SelectOption(label="Contagem de Membros", description="Detalhes sobre os membros do servidor", emoji="📊"),
            nextcord.SelectOption(label="Minhas Permissões", description="Verifica suas permissões no canal atual", emoji="🔑"),
            nextcord.SelectOption(label="Ícone do Servidor", description="Mostra o ícone deste servidor", emoji="<:_:1366996904663322654>"), # Usando happy_flower
        ]
        super().__init__(placeholder=f"{get_emoji(self.bot, 'thinking')} Escolha uma opção de informação", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        label = self.values[0]
        embed = None
        view = None # Para adicionar botões (ex: link do avatar)
        user = interaction.user # Usuário que interagiu
        guild = interaction.guild # Servidor onde ocorreu a interação

        # Defer a resposta para operações mais longas
        await interaction.response.defer(ephemeral=True)

        try:
            # Instancia a classe principal da Cog para acessar métodos auxiliares
            # Isso é um pouco estranho, idealmente os métodos de criação de embed seriam static ou fora da classe
            # Mas vamos manter a estrutura atual por enquanto.
            cog_instance = self.bot.get_cog("Informacoes")
            if not cog_instance:
                 await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro interno ao buscar informações. Tente novamente mais tarde.", ephemeral=True)
                 return

            if label == "Sobre o Bot":
                embed = await cog_instance.create_bot_info_embed(interaction.client)

            elif label == "Usuário":
                if not isinstance(user, Member):
                     await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Não foi possível obter informações completas (você está em DM?). Use em um servidor.", ephemeral=True)
                     return
                embed = cog_instance.create_user_info_embed(user)

            elif label == "Servidor":
                if not guild:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed = await cog_instance.create_server_info_embed(guild)

            elif label == "Sistema":
                embed = cog_instance.create_system_info_embed(interaction.client)

            elif label == "Avatar":
                embed, view = cog_instance.create_avatar_embed_and_view(user)

            elif label == "Uptime":
                embed = cog_instance.create_uptime_embed()

            elif label == "Cargos do Usuário":
                if not isinstance(user, Member):
                     await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Não foi possível obter seus cargos (você está em DM?). Use em um servidor.", ephemeral=True)
                     return
                embed = cog_instance.create_roles_embed(user)

            elif label == "Banner do Usuário":
                fetched_user = await self.bot.fetch_user(user.id)
                embed, view = cog_instance.create_banner_embed_and_view(fetched_user)

            elif label == "Emojis do Servidor":
                if not guild:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed = cog_instance.create_server_emojis_embed(guild)
                
            elif label == "Contagem de Membros":
                if not guild:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed = cog_instance.create_member_count_embed(guild)
                
            elif label == "Minhas Permissões":
                if not guild or not isinstance(interaction.channel, nextcord.abc.GuildChannel):
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Verifique suas permissões dentro de um canal de servidor específico.", ephemeral=True)
                    return
                if not isinstance(user, Member):
                     await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Não foi possível verificar suas permissões (você está em DM?).", ephemeral=True)
                     return
                embed = cog_instance.create_permissions_embed(user, interaction.channel)
                
            elif label == "Ícone do Servidor":
                if not guild:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed, view = cog_instance.create_server_icon_embed_and_view(guild)

            if embed:
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                # Fallback caso uma opção não gere um embed (não deveria acontecer)
                await interaction.followup.send(f"{get_emoji(self.bot, 'thinking')} Opção '{label}' selecionada, mas não gerou um embed.", ephemeral=True)

        except Exception as e:
            print(f"Erro no painel de info ({label}): {e}")
            traceback.print_exc() # Log completo do erro
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro inesperado ao processar sua solicitação.", ephemeral=True)

# --- Cog Principal --- 
class Informacoes(commands.Cog):
    """Comandos para obter informações diversas sobre o bot, servidor, usuários, etc."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.datetime.utcnow()
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cog Informacoes carregada. Uptime iniciado.")

    # --- Funções para criar embeds (reutilizáveis pelos comandos slash e painel) ---

    async def create_bot_info_embed(self, bot_user: nextcord.ClientUser) -> Embed:
        """Cria o embed de informações do bot."""
        embed = Embed(title=f"{get_emoji(self.bot, 'happy_flower')} Sobre {bot_user.name}", description=SLOGAN, color=Color.blue())
        try:
            criador = await self.bot.fetch_user(CRIADOR_ID)
            criador_mention = criador.mention
        except nextcord.NotFound:
            criador_mention = f"ID: {CRIADOR_ID} (Não encontrado)"
        except Exception as e:
            print(f"Erro ao buscar criador: {e}")
            criador_mention = f"ID: {CRIADOR_ID} (Erro ao buscar)"
            
        embed.add_field(name="📅 Criado em", value=DATA_CRIACAO_STR, inline=True)
        embed.add_field(name="🛡️ Primeiro servidor", value=PRIMEIRO_SERVIDOR, inline=True)
        embed.add_field(name="👑 Criador", value=criador_mention, inline=True)
        embed.add_field(name="📊 Servidores", value=str(len(self.bot.guilds)), inline=True)
        # Contar usuários únicos pode ser intensivo, usamos a contagem padrão
        embed.add_field(name="👥 Usuários (Visíveis)", value=str(len(self.bot.users)), inline=True)
        embed.add_field(name="📚 Biblioteca", value=f"Nextcord v{nextcord.__version__}", inline=True)
        embed.add_field(name="🔗 Código Fonte", value=f"[GitHub]({GITHUB_REPO_URL})", inline=False)
        embed.set_thumbnail(url=bot_user.display_avatar.url)
        embed.set_footer(text=f"Obrigado por usar o bot! {get_emoji(self.bot, 'sparkle_happy')}")
        return embed

    def create_user_info_embed(self, user: Member | User) -> Embed:
        """Cria o embed de informações do usuário."""
        color = user.color if isinstance(user, Member) and user.color != Color.default() else Color.blue()
        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Informações de {user.name}", color=color)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="📛 Nome Completo", value=f"{user.name}#{user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=user.id, inline=True)
        embed.add_field(name="🤖 É um Bot?", value=f"{get_emoji(self.bot, 'smug') if user.bot else get_emoji(self.bot, 'determined')}", inline=True)
        
        embed.add_field(name="📅 Conta Criada em", value=f"{format_dt(user.created_at, 'F')} ({format_dt(user.created_at, 'R')})", inline=False)

        if isinstance(user, Member):
            embed.add_field(name="📥 Entrou no Servidor em", value=f"{format_dt(user.joined_at, 'F')} ({format_dt(user.joined_at, 'R')})", inline=False)
            
            roles = sorted([role for role in user.roles if role.name != "@everyone"], key=lambda r: r.position, reverse=True)
            roles_str = ", ".join([r.mention for r in roles]) if roles else "Nenhum cargo."
            if len(roles_str) > 1024:
                 roles_str = roles_str[:1020] + "..."
            embed.add_field(name=f"🎭 Cargos ({len(roles)})", value=roles_str, inline=False)
            
            if user.premium_since:
                embed.add_field(name="✨ Impulsionando desde", value=f"{format_dt(user.premium_since, 'R')}", inline=True)
            
            # Flags do usuário (se houver)
            flags = [flag.replace("_", " ").title() for flag, value in user.public_flags if value]
            if flags:
                embed.add_field(name="🚩 Flags Públicas", value=", ".join(flags), inline=False)
                
            embed.set_footer(text=f"Nickname no servidor: {user.display_name}")
        else:
             embed.set_footer(text=f"Usuário não encontrado neste servidor. {get_emoji(self.bot, 'thinking')}")
             
        return embed

    async def create_server_info_embed(self, guild: nextcord.Guild) -> Embed:
        """Cria o embed de informações do servidor."""
        embed = Embed(title=f"{get_emoji(self.bot, 'happy_flower')} Informações de {guild.name}", color=Color.green())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)
            
        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        owner_mention = "Desconhecido"
        if guild.owner:
             owner_mention = guild.owner.mention
        elif guild.owner_id:
            try:
                owner = await self.bot.fetch_user(guild.owner_id)
                owner_mention = owner.mention
            except:
                owner_mention = f"ID: {guild.owner_id} (Não encontrado)"
        embed.add_field(name="👑 Dono", value=owner_mention, inline=True)
             
        embed.add_field(name="📅 Criado em", value=f"{format_dt(guild.created_at, 'F')} ({format_dt(guild.created_at, 'R')})", inline=False)
        
        embed.add_field(name="👥 Membros Totais", value=str(guild.member_count), inline=True)
        humans = sum(1 for member in guild.members if not member.bot)
        bots = guild.member_count - humans # Mais eficiente que iterar de novo
        embed.add_field(name="👤 Humanos", value=str(humans), inline=True)
        embed.add_field(name="🤖 Bots", value=str(bots), inline=True)
        
        # Contagem detalhada de canais
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        category_channels = len(guild.categories)
        forum_channels = len(guild.forum_channels)
        stage_channels = len(guild.stage_channels)
        embed.add_field(name="💬 Texto", value=str(text_channels), inline=True)
        embed.add_field(name="🔊 Voz", value=str(voice_channels), inline=True)
        embed.add_field(name="📚 Categorias", value=str(category_channels), inline=True)
        embed.add_field(name="<:forum:123456789> Fóruns", value=str(forum_channels), inline=True) # Placeholder emoji
        embed.add_field(name="<:stage:123456789> Palcos", value=str(stage_channels), inline=True) # Placeholder emoji
        
        embed.add_field(name="🎭 Cargos", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="😀 Emojis", value=str(len(guild.emojis)), inline=True)
        embed.add_field(name="🎨 Stickers", value=str(len(guild.stickers)), inline=True)
        embed.add_field(name="✨ Impulsos", value=str(guild.premium_subscription_count or 0), inline=True)
        embed.add_field(name="💎 Nível Impulso", value=str(guild.premium_tier), inline=True)
        embed.add_field(name="🛡️ Verificação", value=str(guild.verification_level).capitalize(), inline=True)
        embed.add_field(name="🌍 Região Preferida", value=str(guild.preferred_locale).replace("_", "-"), inline=True)
        
        features_str = ", ".join([f.replace("_", " ").title() for f in guild.features]) if guild.features else "Nenhuma"
        if len(features_str) > 1024:
            features_str = features_str[:1020] + "..."
        embed.add_field(name="🌟 Features", value=features_str, inline=False)
        
        embed.set_footer(text=f"Um servidor incrível! {get_emoji(self.bot, 'sparkle_happy')}")
        return embed

    def create_system_info_embed(self, bot_user: nextcord.ClientUser) -> Embed:
        """Cria o embed de informações do sistema."""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        disk = psutil.disk_usage("/")
        embed = Embed(title=f"{get_emoji(self.bot, 'determined')} Status do Sistema ({bot_user.name})", color=Color.orange())
        embed.add_field(name="🐍 Versão Python", value=platform.python_version(), inline=True)
        embed.add_field(name="🔧 Biblioteca", value=f"Nextcord v{nextcord.__version__}", inline=True)
        embed.add_field(name="🖥️ Sistema Operacional", value=f"{platform.system()} {platform.release()}", inline=False)
        embed.add_field(name="🧠 Uso de CPU", value=f"{cpu}%", inline=True)
        embed.add_field(name="💾 Uso de RAM", value=f"{memory.percent}% ({psutil._common.bytes2human(memory.used)}/{psutil._common.bytes2human(memory.total)})", inline=True)
        embed.add_field(name="💿 Uso de Disco", value=f"{disk.percent}% ({psutil._common.bytes2human(disk.used)}/{psutil._common.bytes2human(disk.total)})", inline=True)
        # Adicionar Latência
        latency = round(self.bot.latency * 1000) # em ms
        embed.add_field(name="📡 Latência API", value=f"{latency} ms", inline=True)
        embed.set_footer(text=f"Monitoramento em tempo real {get_emoji(self.bot, 'thinking')}")
        return embed

    def create_avatar_embed_and_view(self, user: Member | User) -> tuple[Embed, View | None]:
        """Cria o embed e a view (com botão de link) do avatar do usuário."""
        embed = Embed(title=f"{get_emoji(self.bot, 'blush_hands')} Avatar de {user.name}", color=user.color if isinstance(user, Member) else Color.random())
        avatar_url = user.display_avatar.url
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"ID: {user.id}")
        
        view = View()
        view.add_item(Button(label="Link Direto", url=avatar_url, style=nextcord.ButtonStyle.link))
        return embed, view

    def create_uptime_embed(self) -> Embed:
        """Cria o embed do uptime do bot."""
        delta = datetime.datetime.utcnow() - self.start_time
        uptime_str = format_timedelta(delta)
        embed = Embed(title="⏱️ Uptime do Bot", description=f"{get_emoji(self.bot, 'sparkle_happy')} Online há: **{uptime_str}**", color=Color.gold())
        embed.add_field(name="Iniciado em", value=format_dt(self.start_time, 'F'))
        return embed

    def create_roles_embed(self, user: Member) -> Embed:
        """Cria o embed dos cargos do usuário."""
        roles = sorted([role for role in user.roles if role.name != "@everyone"], key=lambda r: r.position, reverse=True)
        roles_str = "\n".join([f"{role.mention} (`{role.id}`)" for role in roles]) if roles else f"{get_emoji(self.bot, 'thinking')} Nenhum cargo."
        if len(roles_str) > 4000: # Limite de descrição do Embed
            roles_str = roles_str[:3990] + "... (lista muito longa)"
        embed = Embed(title=f"{get_emoji(self.bot, 'determined')} Cargos de {user.display_name} ({len(roles)})", description=roles_str, color=user.color if user.color != Color.default() else Color.orange())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Cargo mais alto: {user.top_role.name}")
        return embed

    def create_banner_embed_and_view(self, user: User) -> tuple[Embed, View | None]:
        """Cria o embed e a view (com botão de link) do banner do usuário."""
        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Banner de {user.name}", color=user.accent_color or Color.random())
        view = None
        if user.banner:
            banner_url = user.banner.url
            embed.set_image(url=banner_url)
            embed.description = f"Que banner bonito! {get_emoji(self.bot, 'blush_hands')}"
            view = View()
            view.add_item(Button(label="Link Direto", url=banner_url, style=nextcord.ButtonStyle.link))
        else:
            embed.description = f"{get_emoji(self.bot, 'sad')} Este usuário não possui um banner personalizado."
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"ID: {user.id}")
        return embed, view

    def create_server_emojis_embed(self, guild: nextcord.Guild) -> Embed:
        """Cria o embed da lista de emojis do servidor (com paginação se necessário)."""
        embed = Embed(title=f"{get_emoji(self.bot, 'sparkle_happy')} Emojis de {guild.name} ({len(guild.emojis)})", color=Color.light_grey())
        if not guild.emojis:
            embed.description = f"{get_emoji(self.bot, 'sad')} Este servidor não possui emojis personalizados."
            return embed
        
        static_emojis = []
        animated_emojis = []
        for emoji in guild.emojis:
            if emoji.animated:
                animated_emojis.append(f"{str(emoji)} (`{emoji.name}`)")
            else:
                static_emojis.append(f"{str(emoji)} (`{emoji.name}`)")
        
        # Simplesmente listar todos pode exceder limites. Paginação seria ideal aqui.
        # Por agora, vamos limitar a quantidade exibida.
        MAX_EMOJIS_DISPLAY = 50 
        
        static_str = " ".join(static_emojis[:MAX_EMOJIS_DISPLAY])
        if len(static_emojis) > MAX_EMOJIS_DISPLAY:
            static_str += f" ... (+{len(static_emojis) - MAX_EMOJIS_DISPLAY})"
        if static_emojis:
            embed.add_field(name=f"Estáticos ({len(static_emojis)})", value=static_str or "Nenhum", inline=False)
            
        animated_str = " ".join(animated_emojis[:MAX_EMOJIS_DISPLAY])
        if len(animated_emojis) > MAX_EMOJIS_DISPLAY:
            animated_str += f" ... (+{len(animated_emojis) - MAX_EMOJIS_DISPLAY})"
        if animated_emojis:
            embed.add_field(name=f"Animados ({len(animated_emojis)})", value=animated_str or "Nenhum", inline=False)
            
        embed.set_footer(text="Use /emojiinfo para detalhes de um emoji específico.")
        return embed
        
    def create_member_count_embed(self, guild: nextcord.Guild) -> Embed:
        """Cria o embed com contagem detalhada de membros por status."""
        status_counts = get_member_status_counts(guild)
        embed = Embed(title=f"📊 Contagem de Membros em {guild.name}", color=Color.purple())
        embed.description = f"Total: **{guild.member_count}** membros"
        embed.add_field(name="<:online:12345> Online", value=str(status_counts["online"]), inline=True) # Placeholder
        embed.add_field(name="<:idle:12345> Ausente", value=str(status_counts["idle"]), inline=True) # Placeholder
        embed.add_field(name="<:dnd:12345> Não Perturbe", value=str(status_counts["dnd"]), inline=True) # Placeholder
        embed.add_field(name="<:offline:12345> Offline", value=str(status_counts["offline"]), inline=True) # Placeholder
        embed.add_field(name="<:streaming:12345> Streaming", value=str(status_counts["streaming"]), inline=True) # Placeholder
        embed.add_field(name="📱 Mobile", value=str(status_counts["mobile"]), inline=True)
        
        humans = sum(1 for m in guild.members if not m.bot)
        bots = guild.member_count - humans
        embed.add_field(name="👤 Humanos", value=str(humans), inline=True)
        embed.add_field(name="🤖 Bots", value=str(bots), inline=True)
        
        embed.set_footer(text=f"Status atualizado em {format_dt(datetime.datetime.now(), 'T')}")
        return embed
        
    def create_permissions_embed(self, member: Member, channel: nextcord.abc.GuildChannel) -> Embed:
        """Cria o embed mostrando as permissões de um membro em um canal."""
        perms = channel.permissions_for(member)
        embed = Embed(title=f"🔑 Permissões de {member.display_name}", description=f"No canal {channel.mention}", color=member.color)
        
        # Permissões Gerais Importantes
        general_perms = [
            ("Administrador", perms.administrator),
            ("Ver Canal", perms.view_channel),
            ("Gerenciar Canal", perms.manage_channels),
            ("Gerenciar Cargos", perms.manage_roles),
            ("Gerenciar Emojis/Stickers", perms.manage_emojis_and_stickers),
            ("Gerenciar Webhooks", perms.manage_webhooks),
            ("Gerenciar Servidor", perms.manage_guild),
        ]
        general_str = "\n".join([f"{get_emoji(self.bot, 'sparkle_happy') if v else get_emoji(self.bot, 'sad')} {k}" for k, v in general_perms])
        embed.add_field(name="Gerais", value=general_str, inline=True)
        
        # Permissões de Texto
        text_perms = [
            ("Enviar Mensagens", perms.send_messages),
            ("Enviar Mensagens em Threads", perms.send_messages_in_threads),
            ("Criar Threads Públicas", perms.create_public_threads),
            ("Criar Threads Privadas", perms.create_private_threads),
            ("Inserir Links", perms.embed_links),
            ("Anexar Arquivos", perms.attach_files),
            ("Adicionar Reações", perms.add_reactions),
            ("Usar Emojis Externos", perms.use_external_emojis),
            ("Usar Stickers Externos", perms.use_external_stickers),
            ("Mencionar @everyone", perms.mention_everyone),
            ("Gerenciar Mensagens", perms.manage_messages),
            ("Gerenciar Threads", perms.manage_threads),
            ("Ler Histórico", perms.read_message_history),
            ("Usar Comandos Slash", perms.use_application_commands),
        ]
        text_str = "\n".join([f"{get_emoji(self.bot, 'sparkle_happy') if v else get_emoji(self.bot, 'sad')} {k}" for k, v in text_perms])
        embed.add_field(name="Texto", value=text_str, inline=True)
        
        # Permissões de Voz
        voice_perms = [
            ("Conectar", perms.connect),
            ("Falar", perms.speak),
            ("Vídeo", perms.stream),
            ("Usar Atividade de Voz", perms.use_voice_activation),
            ("Voz Prioritária", perms.priority_speaker),
            ("Silenciar Membros", perms.mute_members),
            ("Ensurdecer Membros", perms.deafen_members),
            ("Mover Membros", perms.move_members),
            ("Usar Atividades", perms.start_embedded_activities),
        ]
        voice_str = "\n".join([f"{get_emoji(self.bot, 'sparkle_happy') if v else get_emoji(self.bot, 'sad')} {k}" for k, v in voice_perms])
        embed.add_field(name="Voz", value=voice_str, inline=True)
        
        if perms.administrator:
            embed.description += f"\n{get_emoji(self.bot, 'smug')} **Este usuário tem permissão de Administrador!**"
            
        embed.set_footer(text="Permissões efetivas neste canal específico.")
        return embed
        
    def create_server_icon_embed_and_view(self, guild: nextcord.Guild) -> tuple[Embed, View | None]:
        """Cria o embed e a view (com botão de link) do ícone do servidor."""
        embed = Embed(title=f"{get_emoji(self.bot, 'happy_flower')} Ícone de {guild.name}", color=Color.random())
        view = None
        if guild.icon:
            icon_url = guild.icon.url
            embed.set_image(url=icon_url)
            view = View()
            view.add_item(Button(label="Link Direto", url=icon_url, style=nextcord.ButtonStyle.link))
        else:
            embed.description = f"{get_emoji(self.bot, 'sad')} Este servidor não possui um ícone."
        return embed, view
        
    def create_server_banner_embed_and_view(self, guild: nextcord.Guild) -> tuple[Embed, View | None]:
        """Cria o embed e a view (com botão de link) do banner do servidor."""
        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Banner de {guild.name}", color=Color.random())
        view = None
        if guild.banner:
            banner_url = guild.banner.url
            embed.set_image(url=banner_url)
            view = View()
            view.add_item(Button(label="Link Direto", url=banner_url, style=nextcord.ButtonStyle.link))
        else:
            embed.description = f"{get_emoji(self.bot, 'sad')} Este servidor não possui um banner."
        return embed, view
        
    def create_invite_info_embed(self, invite: Invite) -> Embed:
        """Cria o embed com informações sobre um convite."""
        embed = Embed(title=f"{get_emoji(self.bot, 'thinking')} Informações do Convite: `{invite.code}`", color=Color.teal())
        if invite.guild:
            embed.description = f"Convite para: **{invite.guild.name}**"
            if invite.guild.icon:
                embed.set_thumbnail(url=invite.guild.icon.url)
            embed.add_field(name="ID Servidor", value=invite.guild.id, inline=True)
            embed.add_field(name="Membros Online", value=str(invite.approximate_presence_count), inline=True)
            embed.add_field(name="Membros Totais", value=str(invite.approximate_member_count), inline=True)
            if invite.guild.description:
                embed.add_field(name="Descrição Servidor", value=invite.guild.description, inline=False)
        if invite.channel:
            embed.add_field(name="Canal Destino", value=f"#{invite.channel.name} ({invite.channel.type})", inline=True)
        if invite.inviter:
            embed.add_field(name="Criado por", value=invite.inviter.mention, inline=True)
        if invite.created_at:
            embed.add_field(name="Criado em", value=format_dt(invite.created_at, 'R'), inline=True)
        if invite.expires_at:
            embed.add_field(name="Expira em", value=format_dt(invite.expires_at, 'R'), inline=True)
        else:
            embed.add_field(name="Expiração", value="Nunca", inline=True)
        embed.add_field(name="Usos", value=str(invite.uses) if hasattr(invite, 'uses') else 'N/A', inline=True)
        embed.add_field(name="Usos Máximos", value=str(invite.max_uses) if invite.max_uses else 'Infinito', inline=True)
        embed.add_field(name="Temporário?", value=f"{get_emoji(self.bot, 'sparkle_happy') if invite.temporary else get_emoji(self.bot, 'sad')}", inline=True)
        
        embed.set_footer(text=f"URL: {invite.url}")
        return embed
        
    def create_emoji_info_embed(self, emoji: PartialEmoji | nextcord.Emoji) -> Embed:
        """Cria o embed com informações sobre um emoji."""
        embed = Embed(title=f"{get_emoji(self.bot, 'thinking')} Informações do Emoji", color=Color.random())
        embed.set_thumbnail(url=emoji.url)
        embed.add_field(name="Nome", value=emoji.name, inline=True)
        embed.add_field(name="ID", value=emoji.id, inline=True)
        embed.add_field(name="Animado?", value=f"{get_emoji(self.bot, 'sparkle_happy') if emoji.animated else get_emoji(self.bot, 'sad')}", inline=True)
        embed.add_field(name="Link Direto", value=f"[Clique Aqui]({emoji.url})", inline=False)
        embed.add_field(name="Formato Discord", value=f"`{str(emoji)}`", inline=False)
        
        if isinstance(emoji, nextcord.Emoji):
            embed.add_field(name="Criado em", value=format_dt(emoji.created_at, 'R'), inline=True)
            if emoji.guild:
                embed.add_field(name="Servidor", value=emoji.guild.name, inline=True)
            if emoji.user:
                embed.add_field(name="Enviado por", value=emoji.user.mention, inline=True)
            embed.add_field(name="Disponível?", value=f"{get_emoji(self.bot, 'sparkle_happy') if emoji.available else get_emoji(self.bot, 'sad')}", inline=True)
            embed.add_field(name="Gerenciado?", value=f"{get_emoji(self.bot, 'smug') if emoji.managed else get_emoji(self.bot, 'determined')}", inline=True)
            embed.add_field(name="Requer Colons?", value=f"{get_emoji(self.bot, 'sparkle_happy') if emoji.require_colons else get_emoji(self.bot, 'sad')}", inline=True)
            # TODO: Listar cargos que podem usar? (emoji.roles)
            
        return embed
        
    def create_sticker_info_embed(self, sticker: Sticker) -> Embed:
        """Cria o embed com informações sobre um sticker."""
        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Informações do Sticker: {sticker.name}", color=Color.random())
        embed.set_thumbnail(url=sticker.url)
        embed.add_field(name="ID", value=sticker.id, inline=True)
        embed.add_field(name="Formato", value=str(sticker.format).replace("StickerFormatType.", "").upper(), inline=True)
        if sticker.guild:
            embed.add_field(name="Servidor", value=sticker.guild.name, inline=True)
        embed.add_field(name="Link Direto", value=f"[Clique Aqui]({sticker.url})", inline=False)
        if sticker.description:
            embed.add_field(name="Descrição", value=sticker.description, inline=False)
        if sticker.tags:
            embed.add_field(name="Tags", value=", ".join(sticker.tags), inline=False)
        if sticker.created_at:
             embed.add_field(name="Criado em", value=format_dt(sticker.created_at, 'R'), inline=True)
        if sticker.user:
             embed.add_field(name="Enviado por", value=sticker.user.mention, inline=True)
        embed.add_field(name="Disponível?", value=f"{get_emoji(self.bot, 'sparkle_happy') if sticker.available else get_emoji(self.bot, 'sad')}", inline=True)
        return embed

    # --- Comandos Slash --- 

    @nextcord.slash_command(
        guild_ids=[SERVER_ID], 
        name="painel_info", 
        description="Abre o painel interativo de informações"
    )
    async def painel_info(self, interaction: Interaction):
        """Abre um painel com um menu select para escolher informações."""
        await interaction.response.send_message(
            f"{get_emoji(self.bot, 'thinking')} Olá {interaction.user.mention}! Use o menu abaixo para explorar as informações disponíveis.", 
            view=InfoView(self.bot, self.start_time), 
            ephemeral=True
        )

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="userinfo",
        description="Mostra informações sobre um usuário (ou você mesmo)."
    )
    async def userinfo(self, interaction: Interaction, usuario: Member | User = SlashOption(required=False, description="O usuário para ver as informações (deixe em branco para você mesmo)")):
        """Exibe informações detalhadas sobre um membro do servidor ou usuário."""
        target_user = usuario or interaction.user
        # Se for User, tenta buscar como Member para mais infos
        if isinstance(target_user, User) and interaction.guild:
            member = interaction.guild.get_member(target_user.id)
            if member:
                target_user = member
                
        embed = self.create_user_info_embed(target_user)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="serverinfo",
        description="Mostra informações sobre este servidor."
    )
    async def serverinfo(self, interaction: Interaction):
        """Exibe informações detalhadas sobre o servidor atual."""
        if not interaction.guild:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        await interaction.response.defer() # Pode demorar um pouco para coletar tudo
        embed = await self.create_server_info_embed(interaction.guild)
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="botinfo",
        description="Mostra informações sobre mim, o Bot!"
    )
    async def botinfo(self, interaction: Interaction):
        """Exibe informações sobre o bot Shirayuki."""
        embed = await self.create_bot_info_embed(self.bot.user)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="avatar",
        description="Mostra o avatar de um usuário (ou o seu)."
    )
    async def avatar(self, interaction: Interaction, usuario: Member | User = SlashOption(required=False, description="O usuário para ver o avatar (deixe em branco para você mesmo)")):
        """Exibe o avatar de um membro do servidor ou usuário."""
        target_user = usuario or interaction.user
        embed, view = self.create_avatar_embed_and_view(target_user)
        await interaction.response.send_message(embed=embed, view=view)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="banner",
        description="Mostra o banner de um usuário (ou o seu)."
    )
    async def banner(self, interaction: Interaction, usuario: User = SlashOption(required=False, description="O usuário para ver o banner (deixe em branco para você mesmo)")):
        """Exibe o banner de perfil de um usuário (requer fetch)."""
        target_user = usuario or interaction.user
        await interaction.response.defer() # Fetch pode demorar
        try:
            # Sempre busca o usuário para garantir banner atualizado
            fetched_user = await self.bot.fetch_user(target_user.id)
            embed, view = self.create_banner_embed_and_view(fetched_user)
            await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            print(f"Erro ao buscar banner no comando /banner: {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Não foi possível obter o banner para {target_user.mention}.", ephemeral=True)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="roleinfo",
        description="Mostra informações sobre um cargo específico."
    )
    async def roleinfo(self, interaction: Interaction, cargo: Role = SlashOption(description="O cargo para ver as informações")):
        """Exibe informações detalhadas sobre um cargo do servidor."""
        embed = Embed(title=f"{get_emoji(self.bot, 'determined')} Informações do Cargo: {cargo.name}", color=cargo.color)
        embed.add_field(name="ID", value=cargo.id, inline=True)
        embed.add_field(name="Cor (Hex)", value=str(cargo.color), inline=True)
        embed.add_field(name="Membros", value=str(len(cargo.members)), inline=True)
        embed.add_field(name="Posição", value=str(cargo.position), inline=True)
        embed.add_field(name="Separado (Hoist)", value=f"{get_emoji(self.bot, 'sparkle_happy') if cargo.hoist else get_emoji(self.bot, 'sad')}", inline=True)
        embed.add_field(name="Mencionável", value=f"{get_emoji(self.bot, 'sparkle_happy') if cargo.mentionable else get_emoji(self.bot, 'sad')}", inline=True)
        embed.add_field(name="Gerenciado (Bot/Integ)", value=f"{get_emoji(self.bot, 'smug') if cargo.managed else get_emoji(self.bot, 'determined')}", inline=True)
        embed.add_field(name="É Padrão?", value=f"{get_emoji(self.bot, 'sparkle_happy') if cargo.is_default() else get_emoji(self.bot, 'sad')}", inline=True)
        embed.add_field(name="É Premium (Booster)?", value=f"{get_emoji(self.bot, 'sparkle_happy') if cargo.is_premium_subscriber() else get_emoji(self.bot, 'sad')}", inline=True)
        embed.add_field(name="Criado em", value=f"{format_dt(cargo.created_at, 'F')} ({format_dt(cargo.created_at, 'R')})", inline=False)
        
        # Mostrar ícone do cargo se houver
        if cargo.icon:
            embed.set_thumbnail(url=cargo.icon.url)
        elif cargo.unicode_emoji:
            embed.add_field(name="Emoji Unicode", value=cargo.unicode_emoji, inline=True)
            
        # Listar permissões (pode ser muito longo, talvez um comando separado?)
        # perms_str = format_permissions(cargo.permissions)
        # if len(perms_str) < 1020:
        #     embed.add_field(name="Permissões", value=perms_str, inline=False)
        # else:
        #     embed.add_field(name="Permissões", value="Muitas para listar aqui.", inline=False)
            
        await interaction.response.send_message(embed=embed)
        
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="channelinfo",
        description="Mostra informações sobre um canal específico."
    )
    async def channelinfo(self, interaction: Interaction, canal: nextcord.abc.GuildChannel = SlashOption(required=False, description="O canal para ver as informações (padrão: canal atual)")):
        """Exibe informações detalhadas sobre um canal do servidor."""
        target_channel = canal or interaction.channel
        if not isinstance(target_channel, nextcord.abc.GuildChannel): # Garante que é um canal de servidor
             await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Canal inválido ou não é um canal de servidor.", ephemeral=True)
             return

        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Informações do Canal: #{target_channel.name}", color=Color.blurple())
        embed.add_field(name="ID", value=target_channel.id, inline=True)
        embed.add_field(name="Tipo", value=str(target_channel.type).capitalize(), inline=True)
        embed.add_field(name="Posição", value=str(target_channel.position), inline=True)
        embed.add_field(name="Criado em", value=f"{format_dt(target_channel.created_at, 'F')} ({format_dt(target_channel.created_at, 'R')})", inline=False)
        
        if target_channel.category:
            embed.add_field(name="Categoria", value=target_channel.category.name, inline=True)
            
        # Informações específicas por tipo de canal
        if isinstance(target_channel, TextChannel):
            embed.title = f"{get_emoji(self.bot, 'peek')} Info Canal Texto: #{target_channel.name}"
            embed.add_field(name="Slowmode", value=f"{target_channel.slowmode_delay}s" if target_channel.slowmode_delay > 0 else "Desativado", inline=True)
            embed.add_field(name="NSFW", value=f"{get_emoji(self.bot, 'smug') if target_channel.is_nsfw() else get_emoji(self.bot, 'determined')}", inline=True)
            embed.add_field(name="Tópico", value=target_channel.topic or "Nenhum", inline=False)
        elif isinstance(target_channel, VoiceChannel):
            embed.title = f"{get_emoji(self.bot, 'peek')} Info Canal Voz: {target_channel.name}"
            embed.add_field(name="Limite Usuários", value=str(target_channel.user_limit) if target_channel.user_limit > 0 else "Sem limite", inline=True)
            embed.add_field(name="Bitrate", value=f"{target_channel.bitrate // 1000} kbps", inline=True)
            embed.add_field(name="Região", value=str(target_channel.rtc_region) or "Automático", inline=True)
            embed.add_field(name="Modo Vídeo", value=str(target_channel.video_quality_mode).replace("VideoQualityMode.",""), inline=True)
        elif isinstance(target_channel, CategoryChannel):
            embed.title = f"{get_emoji(self.bot, 'peek')} Info Categoria: {target_channel.name}"
            embed.add_field(name="Canais Contidos", value=str(len(target_channel.channels)), inline=True)
            embed.add_field(name="NSFW", value=f"{get_emoji(self.bot, 'smug') if target_channel.is_nsfw() else get_emoji(self.bot, 'determined')}", inline=True)
        elif isinstance(target_channel, ForumChannel):
            embed.title = f"{get_emoji(self.bot, 'peek')} Info Fórum: {target_channel.name}"
            embed.add_field(name="Slowmode Post", value=f"{target_channel.default_thread_slowmode_delay}s", inline=True)
            embed.add_field(name="Slowmode Msg", value=f"{target_channel.slowmode_delay}s", inline=True)
            embed.add_field(name="NSFW", value=f"{get_emoji(self.bot, 'smug') if target_channel.is_nsfw() else get_emoji(self.bot, 'determined')}", inline=True)
            if target_channel.topic:
                 embed.add_field(name="Tópico", value=target_channel.topic, inline=False)
            if target_channel.available_tags:
                 tags_str = ", ".join([f"{t.emoji or ''} {t.name}" for t in target_channel.available_tags])
                 if len(tags_str) < 1020:
                     embed.add_field(name="Tags Disponíveis", value=tags_str, inline=False)
                 else:
                     embed.add_field(name="Tags Disponíveis", value=f"{len(target_channel.available_tags)} tags (muitas para listar)", inline=False)
        elif isinstance(target_channel, StageChannel):
            embed.title = f"{get_emoji(self.bot, 'peek')} Info Palco: {target_channel.name}"
            embed.add_field(name="Bitrate", value=f"{target_channel.bitrate // 1000} kbps", inline=True)
            embed.add_field(name="Região", value=str(target_channel.rtc_region) or "Automático", inline=True)
            if target_channel.topic:
                 embed.add_field(name="Tópico", value=target_channel.topic, inline=False)
                 
        # TODO: Adicionar mais tipos se necessário (Threads?)
            
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="emojis",
        description="Lista os emojis deste servidor (pode ser paginado)."
    )
    async def emojis(self, interaction: Interaction):
        """Exibe a lista de emojis estáticos e animados do servidor, com paginação."""
        if not interaction.guild:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        if not interaction.guild.emojis:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} Este servidor não possui emojis personalizados.", ephemeral=True)
            return

        await interaction.response.defer() # Paginação pode demorar um pouco

        all_emojis = sorted(interaction.guild.emojis, key=lambda e: e.name.lower())
        emoji_lines = [f"{str(e)} `:{e.name}:` (ID: {e.id}){' [Animado]' if e.animated else ''}" for e in all_emojis]

        paginator = Paginator(timeout=180.0)
        pages = []
        current_page = ""
        title = f"{get_emoji(self.bot, 'sparkle_happy')} Emojis de {interaction.guild.name} ({len(all_emojis)})"
        
        # Divide em páginas de ~2000 caracteres ou ITEMS_PER_PAGE
        lines_on_page = 0
        for line in emoji_lines:
            if len(current_page) + len(line) + 1 > 1900 or lines_on_page >= ITEMS_PER_PAGE * 2: # Limite aproximado e por itens
                pages.append(Embed(title=title, description=current_page, color=Color.light_grey()))
                current_page = line + "\n"
                lines_on_page = 1
            else:
                current_page += line + "\n"
                lines_on_page += 1
        
        # Adiciona a última página
        if current_page:
            pages.append(Embed(title=title, description=current_page, color=Color.light_grey()))
            
        # Adiciona numeração às páginas
        for i, page_embed in enumerate(pages):
            page_embed.set_footer(text=f"Página {i+1}/{len(pages)}")

        paginator.add_pages(pages)
        await paginator.start(interaction=interaction, ephemeral=False) # Manda não efêmero para todos verem

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="stickers",
        description="Lista os stickers deste servidor (pode ser paginado)."
    )
    async def stickers(self, interaction: Interaction):
        """Exibe a lista de stickers do servidor, com paginação."""
        if not interaction.guild:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        
        await interaction.response.defer()
        try:
            stickers = await interaction.guild.fetch_stickers()
        except Exception as e:
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao buscar stickers: {e}", ephemeral=True)
            return
            
        if not stickers:
            await interaction.followup.send(f"{get_emoji(self.bot, 'thinking')} Este servidor não possui stickers personalizados.", ephemeral=True)
            return

        all_stickers = sorted(stickers, key=lambda s: s.name.lower())
        sticker_lines = [f"**{s.name}** (ID: {s.id}) - Tags: `{', '.join(s.tags) if s.tags else 'Nenhuma'}`" for s in all_stickers]

        paginator = Paginator(timeout=180.0)
        pages = []
        current_page = ""
        title = f"{get_emoji(self.bot, 'peek')} Stickers de {interaction.guild.name} ({len(all_stickers)})"
        
        lines_on_page = 0
        for line in sticker_lines:
            if len(current_page) + len(line) + 1 > 1900 or lines_on_page >= ITEMS_PER_PAGE:
                pages.append(Embed(title=title, description=current_page, color=Color.magenta()))
                current_page = line + "\n"
                lines_on_page = 1
            else:
                current_page += line + "\n"
                lines_on_page += 1
        
        if current_page:
            pages.append(Embed(title=title, description=current_page, color=Color.magenta()))
            
        for i, page_embed in enumerate(pages):
            page_embed.set_footer(text=f"Página {i+1}/{len(pages)} | Use /stickerinfo para detalhes")

        paginator.add_pages(pages)
        await paginator.start(interaction=interaction, ephemeral=False)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="uptime",
        description="Mostra há quanto tempo o bot está online."
    )
    async def uptime(self, interaction: Interaction):
        """Exibe o tempo de atividade do bot desde a última inicialização."""
        embed = self.create_uptime_embed()
        await interaction.response.send_message(embed=embed)
        
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="ping",
        description="Verifica a latência do bot."
    )
    async def ping(self, interaction: Interaction):
        """Mede a latência da API do Discord e o tempo de resposta do bot."""
        start_time = time.monotonic()
        await interaction.response.defer(ephemeral=True)
        end_time = time.monotonic()
        
        api_latency = round(self.bot.latency * 1000)
        response_latency = round((end_time - start_time) * 1000)
        
        emoji = get_emoji(self.bot, 'sparkle_happy') if api_latency < 150 else get_emoji(self.bot, 'thinking') if api_latency < 300 else get_emoji(self.bot, 'sad')
        
        embed = Embed(title=f"{emoji} Pong!", color=Color.random())
        embed.add_field(name="Latência da API", value=f"{api_latency} ms", inline=True)
        embed.add_field(name="Latência da Resposta", value=f"{response_latency} ms", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="membercount",
        description="Mostra a contagem detalhada de membros por status."
    )
    async def membercount(self, interaction: Interaction):
        """Exibe a contagem de membros online, offline, etc."""
        if not interaction.guild:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        await interaction.response.defer()
        embed = self.create_member_count_embed(interaction.guild)
        await interaction.followup.send(embed=embed)
        
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="permissions",
        description="Verifica as permissões de um usuário em um canal."
    )
    async def permissions(self, interaction: Interaction, 
                          usuario: Member = SlashOption(required=False, description="Usuário para verificar (padrão: você)"),
                          canal: nextcord.abc.GuildChannel = SlashOption(required=False, description="Canal para verificar (padrão: atual)")):
        """Mostra as permissões efetivas de um usuário em um canal específico."""
        target_user = usuario or interaction.user
        target_channel = canal or interaction.channel
        
        if not isinstance(target_channel, nextcord.abc.GuildChannel):
             await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Por favor, especifique um canal de servidor válido.", ephemeral=True)
             return
             
        if not isinstance(target_user, Member):
             # Tenta buscar o membro se for User
             if interaction.guild:
                 member = interaction.guild.get_member(target_user.id)
                 if member:
                     target_user = member
                 else:
                     await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Usuário {target_user.mention} não encontrado neste servidor.", ephemeral=True)
                     return
             else:
                 await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não é possível verificar permissões fora de um servidor.", ephemeral=True)
                 return
                 
        embed = self.create_permissions_embed(target_user, target_channel)
        await interaction.response.send_message(embed=embed, ephemeral=True) # Permissões podem ser sensíveis
        
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="servericon",
        description="Mostra o ícone deste servidor."
    )
    async def servericon(self, interaction: Interaction):
        """Exibe o ícone do servidor atual."""
        if not interaction.guild:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        embed, view = self.create_server_icon_embed_and_view(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)
        
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="serverbanner",
        description="Mostra o banner deste servidor (se houver)."
    )
    async def serverbanner(self, interaction: Interaction):
        """Exibe o banner do servidor atual."""
        if not interaction.guild:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        embed, view = self.create_server_banner_embed_and_view(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)
        
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="inviteinfo",
        description="Mostra informações sobre um código de convite."
    )
    async def inviteinfo(self, interaction: Interaction, codigo: str = SlashOption(description="O código do convite (ex: discordgg ou abcdef)")):
        """Busca e exibe informações sobre um convite do Discord."""
        await interaction.response.defer()
        try:
            invite = await self.bot.fetch_invite(codigo)
            embed = self.create_invite_info_embed(invite)
            await interaction.followup.send(embed=embed)
        except nextcord.NotFound:
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Convite `{codigo}` não encontrado ou inválido.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao buscar informações do convite: {e}", ephemeral=True)
            
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="emojiinfo",
        description="Mostra informações detalhadas sobre um emoji."
    )
    async def emojiinfo(self, interaction: Interaction, emoji: str = SlashOption(description="O emoji personalizado para ver informações")):
        """Exibe informações detalhadas sobre um emoji personalizado."""
        try:
            # Tenta converter para PartialEmoji primeiro (funciona para emojis de outros servers)
            partial_emoji = await commands.PartialEmojiConverter().convert(interaction, emoji)
            
            # Se for do servidor atual, tenta pegar o objeto Emoji completo para mais infos
            full_emoji = None
            if interaction.guild and partial_emoji.id:
                full_emoji = interaction.guild.get_emoji(partial_emoji.id)
                
            target_emoji = full_emoji or partial_emoji # Usa o completo se disponível
            embed = self.create_emoji_info_embed(target_emoji)
            await interaction.response.send_message(embed=embed)
            
        except commands.PartialEmojiConversionFailure:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Emoji `{emoji}` inválido ou não reconhecido.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Erro ao obter informações do emoji: {e}", ephemeral=True)
            
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="stickerinfo",
        description="Mostra informações detalhadas sobre um sticker."
    )
    async def stickerinfo(self, interaction: Interaction, sticker_id: str = SlashOption(description="O ID do sticker para ver informações")):
        """Busca e exibe informações detalhadas sobre um sticker pelo ID."""
        await interaction.response.defer()
        try:
            sticker = await self.bot.fetch_sticker(int(sticker_id))
            embed = self.create_sticker_info_embed(sticker)
            await interaction.followup.send(embed=embed)
        except (ValueError, TypeError):
             await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} ID `{sticker_id}` inválido. Forneça apenas o número do ID.", ephemeral=True)
        except nextcord.NotFound:
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Sticker com ID `{sticker_id}` não encontrado.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao buscar informações do sticker: {e}", ephemeral=True)

# Função setup para carregar a cog
def setup(bot):
    bot.add_cog(Informacoes(bot))
