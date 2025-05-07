# /home/ubuntu/ShirayukiBot/cogs/Informacoes.py
# Cog para comandos de informação.

import platform
import psutil
import datetime
import time # Mantido para self.start_time
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Embed, Color, SlashOption, Member, Role, TextChannel, VoiceChannel, CategoryChannel, ForumChannel, StageChannel, User, Invite, Sticker, PartialEmoji
from nextcord.ui import View, Select # Removido Button pois não é usado diretamente aqui, mas Select é.
from nextcord.utils import format_dt
import traceback # Para log de erros no painel

# Importar helper de emojis (usando placeholder como em outras cogs)
def get_emoji(bot, name):
    emoji_map = {
        "happy_flower": "🌸", "peek": "👀", "smug": "😏", "determined": "😠",
        "thinking": "🤔", "sad": "😥", "sparkle_happy": "✨",
        "info": "ℹ️", "user": "👤", "server": "🌐", "system": "💻", "avatar": "🖼️",
        "uptime": "⏱️", "roles": "👥", "banner": "<:_:1366996885398749254>", # Placeholder para banner
        "server_emojis": "😀", "member_count": "📊", "permissions": "🔑",
        "server_icon": "<:_:1366996904663322654>" # Placeholder para ícone do servidor
    }
    return emoji_map.get(name, "▫️")

# --- Constantes do Bot ---
CRIADOR_ID = 1278842453159444582
DATA_CRIACAO_STR = "22 de Abril de 2025"
PRIMEIRO_SERVIDOR = "Jardim Secreto"
SLOGAN = "Um Bot Para A Vida!"
GITHUB_REPO_URL = "https://github.com/iamkevyn/ShirayukiBot"

# --- Funções Auxiliares --- 
def format_timedelta(delta: datetime.timedelta) -> str:
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if seconds > 0 or not parts: parts.append(f"{seconds}s")
    return " ".join(parts) if parts else "0s"

def get_member_status_counts(guild: nextcord.Guild) -> dict:
    status_counts = {"online": 0, "idle": 0, "dnd": 0, "offline": 0, "streaming": 0}
    for member in guild.members:
        if member.status == nextcord.Status.online: status_counts["online"] += 1
        elif member.status == nextcord.Status.idle: status_counts["idle"] += 1
        elif member.status == nextcord.Status.dnd: status_counts["dnd"] += 1
        elif member.status == nextcord.Status.offline: status_counts["offline"] += 1
        if member.activity and isinstance(member.activity, nextcord.Streaming):
            status_counts["streaming"] += 1
    return status_counts

def format_permissions(permissions: nextcord.Permissions) -> str:
    enabled_perms = [name.replace("_", " ").replace("guild", "server").title() 
                     for name, value in permissions if value]
    return ", ".join(enabled_perms) if enabled_perms else "Nenhuma permissão especial."

# --- Views e Selects (Painel de Informações) ---
class InfoView(View):
    def __init__(self, bot: commands.Bot, cog_instance):
        super().__init__(timeout=180)
        self.add_item(InfoSelect(bot, cog_instance))

class InfoSelect(Select):
    def __init__(self, bot: commands.Bot, cog_instance):
        self.bot = bot
        self.cog_instance = cog_instance # Passa a instância da cog Informacoes
        options = [
            nextcord.SelectOption(label="Sobre o Bot", description="Informações gerais sobre Shirayuki", emoji=get_emoji(bot, "info")),
            nextcord.SelectOption(label="Usuário", description="Dados do seu perfil no servidor", emoji=get_emoji(bot, "user")),
            nextcord.SelectOption(label="Servidor", description="Informações do servidor atual", emoji=get_emoji(bot, "server")),
            nextcord.SelectOption(label="Sistema", description="Status e uso de sistema do bot", emoji=get_emoji(bot, "system")),
            nextcord.SelectOption(label="Avatar", description="Veja seu avatar ou de outro membro", emoji=get_emoji(bot, "avatar")),
            nextcord.SelectOption(label="Uptime", description="Tempo online do bot desde a inicialização", emoji=get_emoji(bot, "uptime")),
            nextcord.SelectOption(label="Cargos do Usuário", description="Veja seus cargos neste servidor", emoji=get_emoji(bot, "roles")),
            nextcord.SelectOption(label="Banner do Usuário", description="Veja seu banner ou de outro membro", emoji=get_emoji(bot, "banner")),
            nextcord.SelectOption(label="Emojis do Servidor", description="Lista os emojis personalizados deste servidor", emoji=get_emoji(bot, "server_emojis")),
            nextcord.SelectOption(label="Contagem de Membros", description="Detalhes sobre os membros do servidor", emoji=get_emoji(bot, "member_count")),
            nextcord.SelectOption(label="Minhas Permissões", description="Verifica suas permissões no canal atual", emoji=get_emoji(bot, "permissions")),
            nextcord.SelectOption(label="Ícone do Servidor", description="Mostra o ícone deste servidor", emoji=get_emoji(bot, "server_icon")),
        ]
        super().__init__(placeholder=f"{get_emoji(self.bot, 'thinking')} Escolha uma opção de informação", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        label = self.values[0]
        embed = None
        view_to_send = None # Renomeado para evitar conflito com nextcord.ui.View
        user = interaction.user
        guild = interaction.guild

        await interaction.response.defer(ephemeral=True)

        try:
            if not self.cog_instance:
                 await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro interno ao buscar informações. Cog não encontrada.", ephemeral=True)
                 return

            if label == "Sobre o Bot":
                embed = await self.cog_instance.create_bot_info_embed(self.bot.user) # Passa self.bot.user
            elif label == "Usuário":
                if not isinstance(user, Member):
                     await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Não foi possível obter informações completas (você está em DM?). Use em um servidor.", ephemeral=True)
                     return
                embed = self.cog_instance.create_user_info_embed(user)
            elif label == "Servidor":
                if not guild:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed = await self.cog_instance.create_server_info_embed(guild)
            elif label == "Sistema":
                embed = self.cog_instance.create_system_info_embed()
            elif label == "Avatar":
                embed, view_to_send = self.cog_instance.create_avatar_embed_and_view(user)
            elif label == "Uptime":
                embed = self.cog_instance.create_uptime_embed()
            elif label == "Cargos do Usuário":
                if not isinstance(user, Member):
                     await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Não foi possível obter seus cargos (você está em DM?). Use em um servidor.", ephemeral=True)
                     return
                embed = self.cog_instance.create_roles_embed(user)
            elif label == "Banner do Usuário":
                fetched_user = await self.bot.fetch_user(user.id) # fetch_user é necessário para banner
                embed, view_to_send = self.cog_instance.create_banner_embed_and_view(fetched_user)
            elif label == "Emojis do Servidor":
                if not guild:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed = self.cog_instance.create_server_emojis_embed(guild)
            elif label == "Contagem de Membros":
                if not guild:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed = self.cog_instance.create_member_count_embed(guild)
            elif label == "Minhas Permissões":
                if not guild or not isinstance(interaction.channel, nextcord.abc.GuildChannel):
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Verifique suas permissões dentro de um canal de servidor específico.", ephemeral=True)
                    return
                if not isinstance(user, Member):
                     await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Não foi possível verificar suas permissões (você está em DM?).", ephemeral=True)
                     return
                embed = self.cog_instance.create_permissions_embed(user, interaction.channel)
            elif label == "Ícone do Servidor":
                if not guild:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed, view_to_send = self.cog_instance.create_server_icon_embed_and_view(guild)

            if embed:
                await interaction.followup.send(embed=embed, view=view_to_send, ephemeral=True)
            else:
                await interaction.followup.send(f"{get_emoji(self.bot, 'thinking')} Opção '{label}' selecionada, mas não gerou um embed.", ephemeral=True)

        except Exception as e:
            print(f"Erro no painel de info ({label}): {e}")
            traceback.print_exc()
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro inesperado ao processar sua solicitação.", ephemeral=True)

# --- Cog Principal --- 
class Informacoes(commands.Cog):
    """Comandos para obter informações diversas sobre o bot, servidor, usuários, etc."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.datetime.now(datetime.timezone.utc) # Usar timezone.utc
        timestamp = self.start_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Cog Informacoes carregada. Uptime iniciado.")

    # --- Funções para criar embeds ---
    async def create_bot_info_embed(self, bot_user: nextcord.ClientUser) -> Embed:
        embed = Embed(title=f"{get_emoji(self.bot, 'happy_flower')} Sobre {bot_user.name}", description=SLOGAN, color=Color.blue())
        criador_mention = f"ID: {CRIADOR_ID} (Não encontrado)"
        try:
            criador = await self.bot.fetch_user(CRIADOR_ID)
            if criador: criador_mention = criador.mention
        except Exception as e: print(f"Erro ao buscar criador: {e}")
            
        embed.add_field(name="📅 Criado em", value=DATA_CRIACAO_STR, inline=True)
        embed.add_field(name="🛡️ Primeiro servidor", value=PRIMEIRO_SERVIDOR, inline=True)
        embed.add_field(name="👑 Criador", value=criador_mention, inline=True)
        embed.add_field(name="📊 Servidores", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Usuários (Visíveis)", value=str(len(self.bot.users)), inline=True)
        embed.add_field(name="📚 Biblioteca", value=f"Nextcord v{nextcord.__version__}", inline=True)
        embed.add_field(name="🔗 Código Fonte", value=f"[GitHub]({GITHUB_REPO_URL})", inline=False)
        if bot_user.display_avatar: embed.set_thumbnail(url=bot_user.display_avatar.url)
        embed.set_footer(text=f"Obrigado por usar o bot! {get_emoji(self.bot, 'sparkle_happy')}")
        return embed

    def create_user_info_embed(self, user: Member) -> Embed: # User já é garantido ser Member pelo callback do Select
        color = user.color if user.color != Color.default() else Color.blue()
        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Informações de {user.name}", color=color)
        if user.display_avatar: embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="📛 Nome Completo", value=f"{user}", inline=True) # user já é formatado como Nome#Discrim
        embed.add_field(name="🆔 ID", value=user.id, inline=True)
        embed.add_field(name="🤖 É um Bot?", value=f"{get_emoji(self.bot, 'smug') if user.bot else get_emoji(self.bot, 'determined')}", inline=True)
        embed.add_field(name="📅 Conta Criada em", value=f"{format_dt(user.created_at, 'F')} ({format_dt(user.created_at, 'R')})", inline=False)
        if user.joined_at: embed.add_field(name="📥 Entrou no Servidor em", value=f"{format_dt(user.joined_at, 'F')} ({format_dt(user.joined_at, 'R')})", inline=False)
        
        roles = sorted([role for role in user.roles if role.name != "@everyone"], key=lambda r: r.position, reverse=True)
        roles_str = ", ".join([r.mention for r in roles]) if roles else "Nenhum cargo."
        if len(roles_str) > 1024: roles_str = roles_str[:1020] + "..."
        embed.add_field(name=f"🎭 Cargos ({len(roles)})", value=roles_str, inline=False)
        
        if user.premium_since: embed.add_field(name="✨ Impulsionando desde", value=f"{format_dt(user.premium_since, 'R')}", inline=True)
        
        flags_str = ", ".join([flag_name.replace("_", " ").title() for flag_name, value in user.public_flags if value])
        if flags_str: embed.add_field(name="🚩 Flags Públicas", value=flags_str, inline=False)
        embed.set_footer(text=f"Nickname no servidor: {user.display_name}")
        return embed

    async def create_server_info_embed(self, guild: nextcord.Guild) -> Embed:
        embed = Embed(title=f"{get_emoji(self.bot, 'happy_flower')} Informações de {guild.name}", color=Color.green())
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        if guild.banner: embed.set_image(url=guild.banner.url)
            
        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        owner_mention = guild.owner.mention if guild.owner else (await self.bot.fetch_user(guild.owner_id)).mention if guild.owner_id else "Desconhecido"
        embed.add_field(name="👑 Dono", value=owner_mention, inline=True)
        embed.add_field(name="📅 Criado em", value=f"{format_dt(guild.created_at, 'F')} ({format_dt(guild.created_at, 'R')})", inline=False)
        embed.add_field(name="👥 Membros Totais", value=str(guild.member_count), inline=True)
        humans = sum(1 for m in guild.members if not m.bot)
        bots = guild.member_count - humans
        embed.add_field(name="👤 Humanos", value=str(humans), inline=True)
        embed.add_field(name="🤖 Bots", value=str(bots), inline=True)
        
        embed.add_field(name="🗨️ Canais de Texto", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="🗣️ Canais de Voz", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="🗂️ Categorias", value=str(len(guild.categories)), inline=True)
        embed.add_field(name="🎭 Cargos", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="😀 Emojis", value=str(len(guild.emojis)), inline=True)
        if guild.stickers: embed.add_field(name="🎨 Figurinhas", value=str(len(guild.stickers)), inline=True)

        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count
        embed.add_field(name="✨ Nível de Impulso", value=str(boost_level), inline=True)
        embed.add_field(name="💖 Impulsos", value=str(boost_count), inline=True)
        if guild.rules_channel: embed.add_field(name="📜 Canal de Regras", value=guild.rules_channel.mention, inline=True)
        if guild.public_updates_channel: embed.add_field(name="📢 Canal de Atualizações", value=guild.public_updates_channel.mention, inline=True)
        embed.add_field(name="🌍 Região de Voz (Preferida)", value=str(guild.preferred_locale), inline=True)
        features_str = ", ".join([feature.replace("_", " ").title() for feature in guild.features]) if guild.features else "Nenhuma especial."
        if len(features_str) > 1024: features_str = features_str[:1020] + "..."
        embed.add_field(name="🌟 Features do Servidor", value=features_str, inline=False)
        return embed

    def create_system_info_embed(self) -> Embed:
        embed = Embed(title=f"{get_emoji(self.bot, 'system')} Informações do Sistema do Bot", color=Color.orange())
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        cpu_usage = psutil.cpu_percent(interval=0.1)
        embed.add_field(name="🐍 Versão Python", value=platform.python_version(), inline=True)
        embed.add_field(name="📚 Versão Nextcord", value=nextcord.__version__, inline=True)
        embed.add_field(name="💻 OS", value=f"{platform.system()} {platform.release()}", inline=True)
        embed.add_field(name="🧠 Uso de CPU", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="💾 Uso de RAM (Processo)", value=f"{mem_info.rss / 1024**2:.2f} MB", inline=True)
        total_ram = psutil.virtual_memory().total / (1024**3)
        avail_ram = psutil.virtual_memory().available / (1024**3)
        embed.add_field(name="💾 RAM Total (Sistema)", value=f"{total_ram:.2f} GB", inline=True)
        embed.add_field(name="💾 RAM Disponível (Sistema)", value=f"{avail_ram:.2f} GB", inline=True)
        return embed

    def create_avatar_embed_and_view(self, user: User | Member) -> tuple[Embed, View | None]:
        embed = Embed(title=f"{get_emoji(self.bot, 'avatar')} Avatar de {user.display_name}", color=user.color if isinstance(user, Member) else Color.default())
        if user.display_avatar: 
            embed.set_image(url=user.display_avatar.url)
            view = View()
            view.add_item(nextcord.ui.Button(label="Link do Avatar", url=user.display_avatar.url))
            return embed, view
        embed.description = "Este usuário não possui um avatar customizado."
        return embed, None

    def create_uptime_embed(self) -> Embed:
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = now - self.start_time
        uptime_str = format_timedelta(delta)
        embed = Embed(title=f"{get_emoji(self.bot, 'uptime')} Tempo de Atividade do Bot", description=f"Estou online há: **{uptime_str}**", color=Color.teal())
        embed.add_field(name="Iniciado em", value=format_dt(self.start_time, "F"))
        return embed

    def create_roles_embed(self, user: Member) -> Embed:
        roles = sorted([role for role in user.roles if role.name != "@everyone"], key=lambda r: r.position, reverse=True)
        embed = Embed(title=f"{get_emoji(self.bot, 'roles')} Cargos de {user.display_name} ({len(roles)})", color=user.color)
        if not roles:
            embed.description = "Este usuário não possui cargos (além de @everyone)."
        else:
            roles_str = "\n".join([f"{r.mention} (ID: `{r.id}`)" for r in roles])
            if len(roles_str) > 4096: roles_str = roles_str[:4090] + "..."
            embed.description = roles_str
        return embed

    def create_banner_embed_and_view(self, user: User) -> tuple[Embed, View | None]: # User deve ser `fetch_user` para banner
        embed = Embed(title=f"{get_emoji(self.bot, 'banner')} Banner de {user.display_name}", color=user.accent_color or Color.default())
        if user.banner:
            embed.set_image(url=user.banner.url)
            view = View()
            view.add_item(nextcord.ui.Button(label="Link do Banner", url=user.banner.url))
            return embed, view
        embed.description = "Este usuário não possui um banner."
        return embed, None

    def create_server_emojis_embed(self, guild: nextcord.Guild) -> Embed:
        embed = Embed(title=f"{get_emoji(self.bot, 'server_emojis')} Emojis de {guild.name} ({len(guild.emojis)})", color=Color.random())
        if not guild.emojis:
            embed.description = "Este servidor não possui emojis personalizados."
            return embed
        
        emoji_list_animated = []
        emoji_list_static = []
        for emoji in guild.emojis:
            if emoji.animated:
                emoji_list_animated.append(f"<a:{emoji.name}:{emoji.id}> (`{emoji.name}`)")
            else:
                emoji_list_static.append(f"<:{emoji.name}:{emoji.id}> (`{emoji.name}`)")
        
        desc = ""
        if emoji_list_static:
            desc += "**Estáticos:**\n" + " ".join(emoji_list_static) + "\n\n"
        if emoji_list_animated:
            desc += "**Animados:**\n" + " ".join(emoji_list_animated)
            
        if len(desc) > 4096: desc = desc[:4090] + "..."
        embed.description = desc if desc else "Nenhum emoji encontrado (estranho!)."
        return embed

    def create_member_count_embed(self, guild: nextcord.Guild) -> Embed:
        status_counts = get_member_status_counts(guild)
        embed = Embed(title=f"{get_emoji(self.bot, 'member_count')} Contagem de Membros - {guild.name}", color=Color.purple())
        embed.add_field(name="Total", value=str(guild.member_count), inline=False)
        embed.add_field(name="Online", value=str(status_counts["online"]), inline=True)
        embed.add_field(name="Ausente", value=str(status_counts["idle"]), inline=True)
        embed.add_field(name="Não Perturbe", value=str(status_counts["dnd"]), inline=True)
        embed.add_field(name="Offline", value=str(status_counts["offline"]), inline=True)
        embed.add_field(name="Streaming", value=str(status_counts["streaming"]), inline=True)
        return embed

    def create_permissions_embed(self, user: Member, channel: nextcord.abc.GuildChannel) -> Embed:
        perms = channel.permissions_for(user)
        embed = Embed(title=f"{get_emoji(self.bot, 'permissions')} Permissões de {user.display_name} em #{channel.name}", color=user.color)
        perms_str = format_permissions(perms)
        if len(perms_str) > 4096: perms_str = perms_str[:4090] + "..."
        embed.description = perms_str
        return embed

    def create_server_icon_embed_and_view(self, guild: nextcord.Guild) -> tuple[Embed, View | None]:
        embed = Embed(title=f"{get_emoji(self.bot, 'server_icon')} Ícone de {guild.name}", color=Color.random())
        if guild.icon:
            embed.set_image(url=guild.icon.url)
            view = View()
            view.add_item(nextcord.ui.Button(label="Link do Ícone", url=guild.icon.url))
            return embed, view
        embed.description = "Este servidor não possui um ícone."
        return embed, None

    # --- Comando Slash Principal (Painel) ---
    @nextcord.slash_command(name="info", description="Mostra um painel com várias opções de informação.")
    async def info_panel(self, interaction: Interaction):
        """Abre um painel interativo para selecionar diferentes tipos de informação."""
        # Passa a instância da cog para o InfoSelect e InfoView
        await interaction.response.send_message(
            f"{get_emoji(self.bot, 'thinking')} Selecione uma categoria de informação abaixo:", 
            view=InfoView(self.bot, self), 
            ephemeral=True
        )

    # --- Comandos Slash Individuais (Exemplos, podem ser expandidos) ---
    @nextcord.slash_command(name="botinfo", description="Mostra informações sobre mim!")
    async def botinfo(self, interaction: Interaction):
        embed = await self.create_bot_info_embed(self.bot.user)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="userinfo", description="Mostra informações sobre um usuário ou você mesmo.")
    async def userinfo(self, interaction: Interaction, usuario: Member | User = SlashOption(description="O usuário para ver informações (opcional)", required=False)):
        target_user = usuario or interaction.user
        if isinstance(target_user, User) and interaction.guild: # Se for User, tenta pegar Member
            member_maybe = interaction.guild.get_member(target_user.id)
            if member_maybe: target_user = member_maybe
        
        if not isinstance(target_user, Member) and isinstance(target_user, User):
            # Se ainda for User (não está no servidor ou DM)
            # Criar um embed mais simples para User, pois não teremos info de Member
            color = target_user.accent_color or Color.blue()
            embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Informações de {target_user.name}", color=color)
            if target_user.display_avatar: embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.add_field(name="📛 Nome Completo", value=f"{target_user}", inline=True)
            embed.add_field(name="🆔 ID", value=target_user.id, inline=True)
            embed.add_field(name="🤖 É um Bot?", value=f"{get_emoji(self.bot, 'smug') if target_user.bot else get_emoji(self.bot, 'determined')}", inline=True)
            embed.add_field(name="📅 Conta Criada em", value=f"{format_dt(target_user.created_at, 'F')} ({format_dt(target_user.created_at, 'R')})", inline=False)
            flags_str = ", ".join([flag_name.replace("_", " ").title() for flag_name, value in target_user.public_flags if value])
            if flags_str: embed.add_field(name="🚩 Flags Públicas", value=flags_str, inline=False)
            embed.set_footer(text="Usuário não encontrado neste servidor ou informações limitadas.")
        else: # É um Member
            embed = self.create_user_info_embed(target_user)
            
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="serverinfo", description="Mostra informações sobre o servidor atual.")
    async def serverinfo(self, interaction: Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        embed = await self.create_server_info_embed(interaction.guild)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="avatar", description="Mostra o avatar de um usuário.")
    async def avatar(self, interaction: Interaction, usuario: Member | User = SlashOption(description="O usuário para ver o avatar (opcional)", required=False)):
        target_user = usuario or interaction.user
        embed, view = self.create_avatar_embed_and_view(target_user)
        await interaction.response.send_message(embed=embed, view=view)

    @nextcord.slash_command(name="banner", description="Mostra o banner de um usuário (se tiver).")
    async def banner(self, interaction: Interaction, usuario: User = SlashOption(description="O usuário para ver o banner (opcional).", required=False)):
        target_user = usuario or interaction.user
        # Banner requer fetch_user para garantir que o atributo banner seja populado
        fetched_user = await self.bot.fetch_user(target_user.id)
        embed, view = self.create_banner_embed_and_view(fetched_user)
        await interaction.response.send_message(embed=embed, view=view)

    @nextcord.slash_command(name="ping", description="Verifica a latência do bot.")
    async def ping(self, interaction: Interaction):
        latency_ms = round(self.bot.latency * 1000)
        embed = Embed(title="🏓 Pong!", description=f"Latência da API: **{latency_ms}ms**", color=Color.blurple())
        await interaction.response.send_message(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(Informacoes(bot))
