# /home/ubuntu/ShirayukiBot/cogs/Informacoes.py
# Cog para comandos de informação.

import platform
import psutil
import datetime
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Embed, Color, SlashOption, Member, Role, TextChannel, VoiceChannel, CategoryChannel, ForumChannel, StageChannel
from nextcord.ui import View, Select
import time # Para uptime

# --- Emojis Customizados ---
EMOJI_SUCCESS = "<:8_:1366997164521164830>" # Emoji de sucesso
EMOJI_FAILURE = "<:1_:1366996823654535208>" # Emoji de falha/triste
EMOJI_INFO = "<:7_:1366997117410873404>"    # Emoji de informação/neutro
EMOJI_WAIT = "<:2_:1366996885398749254>"     # Emoji de espera
EMOJI_QUESTION = "<:6_:1366997079347429427>" # Emoji de dúvida/ajuda
EMOJI_WARN = "<:4_:1366996921297801216>"     # Emoji de aviso
EMOJI_CELEBRATE = "<:5_:1366997045445132360>" # Emoji de celebração
EMOJI_HAPPY = "<:3_:1366996904663322654>"     # Emoji feliz genérico

# --- Constantes do Bot (Podem ser movidas para config) ---
CRIADOR_ID = 1278842453159444582
DATA_CRIACAO_STR = "22 de Abril de 2025"
PRIMEIRO_SERVIDOR = "Jardim Secreto"
SLOGAN = "Um Bot Para A Vida!"
SERVER_ID = 1367345048458498219 # Para registro rápido de comandos

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

# --- Views e Selects (Mantendo o painel por enquanto) ---
class InfoView(View):
    def __init__(self, bot_start_time):
        super().__init__(timeout=180) # Timeout de 3 minutos
        self.add_item(InfoSelect(bot_start_time))

class InfoSelect(Select):
    def __init__(self, bot_start_time):
        self.bot_start_time = bot_start_time
        options = [
            nextcord.SelectOption(label="Sobre o Bot", description="Informações gerais", emoji="🤖"),
            nextcord.SelectOption(label="Usuário", description="Dados do seu perfil", emoji="👤"),
            nextcord.SelectOption(label="Servidor", description="Informações do servidor atual", emoji="🌐"),
            nextcord.SelectOption(label="Sistema", description="Status e uso de sistema do bot", emoji="💻"),
            nextcord.SelectOption(label="Avatar", description="Veja seu avatar ou de outro membro", emoji="🖼️"),
            nextcord.SelectOption(label="Uptime", description="Tempo online do bot", emoji="⏱️"),
            nextcord.SelectOption(label="Cargos", description="Veja seus cargos", emoji="👥"),
            nextcord.SelectOption(label="Banner", description="Veja seu banner ou de outro membro", emoji="<:banner:ID_EMOJI_BANNER>"), # TODO: Adicionar emoji de banner?
            nextcord.SelectOption(label="Emojis Servidor", description="Lista os emojis do servidor", emoji="😀")
        ]
        super().__init__(placeholder=f"{EMOJI_QUESTION} Escolha uma opção de informação", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        label = self.values[0]
        embed = None
        user = interaction.user # Usuário que interagiu
        guild = interaction.guild # Servidor onde ocorreu a interação

        # Defer a resposta para operações mais longas
        await interaction.response.defer(ephemeral=True)

        try:
            if label == "Sobre o Bot":
                embed = Embed(title=f"🤖 Sobre {interaction.client.user.name}", description=SLOGAN, color=Color.blue())
                criador = await interaction.client.fetch_user(CRIADOR_ID)
                embed.add_field(name="📅 Criado em", value=DATA_CRIACAO_STR, inline=True)
                embed.add_field(name="🛡️ Primeiro servidor", value=PRIMEIRO_SERVIDOR, inline=True)
                embed.add_field(name="👑 Criador", value=criador.mention if criador else f"ID: {CRIADOR_ID}", inline=True)
                embed.add_field(name="📊 Servidores", value=str(len(interaction.client.guilds)), inline=True)
                embed.add_field(name="👥 Usuários Totais", value=str(len(interaction.client.users)), inline=True)
                embed.add_field(name="📚 Biblioteca", value=f"Nextcord v{nextcord.__version__}", inline=True)
                embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
                embed.set_footer(text=f"Obrigado por usar o bot! {EMOJI_HAPPY}")

            elif label == "Usuário":
                embed = self.create_user_info_embed(user)

            elif label == "Servidor":
                if not guild:
                    await interaction.followup.send(f"{EMOJI_FAILURE} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed = await self.create_server_info_embed(guild)

            elif label == "Sistema":
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent()
                disk = psutil.disk_usage("/")
                embed = Embed(title=f"💻 Status do Sistema ({interaction.client.user.name})", color=Color.orange())
                embed.add_field(name="🐍 Versão Python", value=platform.python_version(), inline=True)
                embed.add_field(name="🔧 Biblioteca", value=f"Nextcord v{nextcord.__version__}", inline=True)
                embed.add_field(name="🖥️ Sistema Operacional", value=f"{platform.system()} {platform.release()}", inline=False)
                embed.add_field(name="🧠 Uso de CPU", value=f"{cpu}%", inline=True)
                embed.add_field(name="💾 Uso de RAM", value=f"{memory.percent}% ({psutil._common.bytes2human(memory.used)}/{psutil._common.bytes2human(memory.total)})", inline=True)
                embed.add_field(name="💿 Uso de Disco", value=f"{disk.percent}% ({psutil._common.bytes2human(disk.used)}/{psutil._common.bytes2human(disk.total)})", inline=True)
                embed.set_footer(text=f"Monitoramento em tempo real {EMOJI_INFO}")

            elif label == "Avatar":
                # No painel, mostra o avatar do próprio usuário
                embed = self.create_avatar_embed(user)

            elif label == "Uptime":
                delta = datetime.datetime.utcnow() - self.bot_start_time
                uptime_str = format_timedelta(delta)
                embed = Embed(title="⏱️ Uptime do Bot", description=f"{EMOJI_SUCCESS} Online há: **{uptime_str}**", color=Color.gold())

            elif label == "Cargos":
                # No painel, mostra os cargos do próprio usuário
                if not isinstance(user, Member):
                     await interaction.followup.send(f"{EMOJI_FAILURE} Não foi possível obter seus cargos (você está em DM?).", ephemeral=True)
                     return
                embed = self.create_roles_embed(user)

            elif label == "Banner":
                # No painel, mostra o banner do próprio usuário
                fetched_user = await interaction.client.fetch_user(user.id)
                embed = self.create_banner_embed(fetched_user)

            elif label == "Emojis Servidor":
                if not guild:
                    await interaction.followup.send(f"{EMOJI_FAILURE} Este comando só pode ser usado em um servidor.", ephemeral=True)
                    return
                embed = self.create_server_emojis_embed(guild)

            if embed:
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"{EMOJI_WARN} Opção 

        except Exception as e:
            print(f"Erro no painel de info ({label}): {e}")
            await interaction.followup.send(f"{EMOJI_FAILURE} Ocorreu um erro ao processar sua solicitação.", ephemeral=True)

    # --- Funções para criar embeds (reutilizáveis pelos comandos slash) ---
    def create_user_info_embed(self, user: Member | nextcord.User) -> Embed:
        """Cria o embed de informações do usuário."""
        color = user.color if isinstance(user, Member) and user.color != Color.default() else Color.blue()
        embed = Embed(title=f"👤 Informações de {user.name}", color=color)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="📛 Nome Completo", value=f"{user.name}#{user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=user.id, inline=True)
        embed.add_field(name="🤖 É um Bot?", value=f"{EMOJI_SUCCESS if user.bot else EMOJI_FAILURE}", inline=True)
        
        creation_timestamp = int(user.created_at.timestamp())
        embed.add_field(name="📅 Conta Criada em", value=f"<t:{creation_timestamp}:F> (<t:{creation_timestamp}:R>)", inline=False)

        if isinstance(user, Member):
            join_timestamp = int(user.joined_at.timestamp())
            embed.add_field(name="📥 Entrou no Servidor em", value=f"<t:{join_timestamp}:F> (<t:{join_timestamp}:R>)", inline=False)
            
            roles = [role.mention for role in user.roles if role.name != "@everyone"]
            roles_str = ", ".join(roles) if roles else "Nenhum cargo."
            if len(roles_str) > 1024:
                 roles_str = roles_str[:1020] + "..."
            embed.add_field(name=f"🎭 Cargos ({len(roles)})", value=roles_str, inline=False)
            
            if user.premium_since:
                premium_timestamp = int(user.premium_since.timestamp())
                embed.add_field(name="✨ Impulsionando desde", value=f"<t:{premium_timestamp}:R>", inline=True)
            
            embed.set_footer(text=f"Nickname no servidor: {user.display_name}")
        else:
             embed.set_footer(text="Usuário não está neste servidor.")
             
        return embed

    async def create_server_info_embed(self, guild: nextcord.Guild) -> Embed:
        """Cria o embed de informações do servidor."""
        embed = Embed(title=f"🌐 Informações de {guild.name}", color=Color.green())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)
            
        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        if guild.owner:
             embed.add_field(name="👑 Dono", value=guild.owner.mention, inline=True)
        else:
             embed.add_field(name="👑 Dono", value="Desconhecido", inline=True)
             
        creation_timestamp = int(guild.created_at.timestamp())
        embed.add_field(name="📅 Criado em", value=f"<t:{creation_timestamp}:F> (<t:{creation_timestamp}:R>)", inline=False)
        
        embed.add_field(name="👥 Membros Totais", value=str(guild.member_count), inline=True)
        # Contagem mais precisa de humanos e bots
        humans = sum(1 for member in guild.members if not member.bot)
        bots = sum(1 for member in guild.members if member.bot)
        embed.add_field(name="👤 Humanos", value=str(humans), inline=True)
        embed.add_field(name="🤖 Bots", value=str(bots), inline=True)
        
        embed.add_field(name="💬 Canais de Texto", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="🔊 Canais de Voz", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="📚 Categorias", value=str(len(guild.categories)), inline=True)
        embed.add_field(name="🎭 Cargos", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="😀 Emojis", value=str(len(guild.emojis)), inline=True)
        embed.add_field(name="✨ Impulsos", value=str(guild.premium_subscription_count or 0), inline=True)
        embed.add_field(name="💎 Nível de Impulso", value=str(guild.premium_tier), inline=True)
        embed.add_field(name="🛡️ Nível de Verificação", value=str(guild.verification_level).capitalize(), inline=True)
        
        features_str = ", ".join(guild.features) if guild.features else "Nenhuma"
        if len(features_str) > 1024:
            features_str = features_str[:1020] + "..."
        embed.add_field(name="🌟 Features", value=features_str, inline=False)
        
        embed.set_footer(text=f"Servidor incrível! {EMOJI_HAPPY}")
        return embed

    def create_avatar_embed(self, user: Member | nextcord.User) -> Embed:
        """Cria o embed do avatar do usuário."""
        embed = Embed(title=f"🖼️ Avatar de {user.name}", color=user.color if isinstance(user, Member) else Color.random())
        embed.set_image(url=user.display_avatar.url)
        embed.set_footer(text=f"Solicitado por {user.name}") # Ajustar se for chamado por outro usuário
        return embed

    def create_roles_embed(self, user: Member) -> Embed:
        """Cria o embed dos cargos do usuário."""
        roles = sorted([role for role in user.roles if role.name != "@everyone"], key=lambda r: r.position, reverse=True)
        roles_str = "\n".join([f"{role.mention} (`{role.id}`)

 for role in roles]) if roles else f"{EMOJI_INFO} Nenhum cargo."
        if len(roles_str) > 4000: # Limite de descrição do Embed
            roles_str = roles_str[:3990] + "... (lista muito longa)"
        embed = Embed(title=f"👥 Cargos de {user.display_name} ({len(roles)})", description=roles_str, color=user.color if user.color != Color.default() else Color.orange())
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    def create_banner_embed(self, user: nextcord.User) -> Embed:
        """Cria o embed do banner do usuário."""
        embed = Embed(title=f"🖼️ Banner de {user.name}", color=user.accent_color or Color.random())
        if user.banner:
            embed.set_image(url=user.banner.url)
            embed.description = f"[Link Direto]({user.banner.url})"
        else:
            embed.description = f"{EMOJI_FAILURE} Este usuário não possui um banner."
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    def create_server_emojis_embed(self, guild: nextcord.Guild) -> Embed:
        """Cria o embed da lista de emojis do servidor."""
        embed = Embed(title=f"😀 Emojis de {guild.name} ({len(guild.emojis)})", color=Color.light_grey())
        if not guild.emojis:
            embed.description = f"{EMOJI_FAILURE} Este servidor não possui emojis personalizados."
        else:
            emoji_list = []
            static_emojis = []
            animated_emojis = []
            for emoji in guild.emojis:
                if emoji.animated:
                    animated_emojis.append(str(emoji))
                else:
                    static_emojis.append(str(emoji))
            
            if static_emojis:
                emoji_str = " ".join(static_emojis)
                if len(emoji_str) > 1024:
                     emoji_str = emoji_str[:1020] + "..."
                embed.add_field(name=f"Estáticos ({len(static_emojis)})", value=emoji_str, inline=False)
                
            if animated_emojis:
                emoji_str = " ".join(animated_emojis)
                if len(emoji_str) > 1024:
                     emoji_str = emoji_str[:1020] + "..."
                embed.add_field(name=f"Animados ({len(animated_emojis)})", value=emoji_str, inline=False)

        return embed

# --- Cog Principal --- 
class Informacoes(commands.Cog):
    """Comandos para obter informações diversas sobre o bot, servidor, usuários, etc."""
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.utcnow()
        self.info_select_helper = InfoSelect(self.start_time) # Instancia helper para criar embeds
        print(f"[DIAGNÓSTICO] Cog Informacoes carregada.")

    @nextcord.slash_command(
        guild_ids=[SERVER_ID], 
        name="painel_info", 
        description="Abre o painel interativo de informações"
    )
    async def painel_info(self, interaction: Interaction):
        """Mostra um painel com botões para selecionar informações."""
        embed = Embed(title=f"{EMOJI_QUESTION} Painel de Informações", description="Selecione uma categoria abaixo:", color=Color.dark_purple())
        await interaction.response.send_message(embed=embed, view=InfoView(self.start_time), ephemeral=True)

    # --- Comandos Slash Individuais --- 

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="userinfo",
        description="Mostra informações sobre um usuário (ou você mesmo)."
    )
    async def userinfo(self, interaction: Interaction, usuario: Member = SlashOption(required=False, description="O usuário para ver as informações (deixe em branco para você mesmo)")):
        """Exibe informações detalhadas sobre um membro do servidor."""
        target_user = usuario or interaction.user
        embed = self.info_select_helper.create_user_info_embed(target_user)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="serverinfo",
        description="Mostra informações sobre este servidor."
    )
    async def serverinfo(self, interaction: Interaction):
        """Exibe informações detalhadas sobre o servidor atual."""
        if not interaction.guild:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        await interaction.response.defer() # Pode demorar um pouco para coletar tudo
        embed = await self.info_select_helper.create_server_info_embed(interaction.guild)
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="botinfo",
        description="Mostra informações sobre mim, o Bot!"
    )
    async def botinfo(self, interaction: Interaction):
        """Exibe informações sobre o bot Shirayuki."""
        # Reutiliza a lógica do painel para "Sobre o Bot"
        embed = Embed(title=f"🤖 Sobre {interaction.client.user.name}", description=SLOGAN, color=Color.blue())
        try:
            criador = await interaction.client.fetch_user(CRIADOR_ID)
            criador_mention = criador.mention
        except:
            criador_mention = f"ID: {CRIADOR_ID}"
        embed.add_field(name="📅 Criado em", value=DATA_CRIACAO_STR, inline=True)
        embed.add_field(name="🛡️ Primeiro servidor", value=PRIMEIRO_SERVIDOR, inline=True)
        embed.add_field(name="👑 Criador", value=criador_mention, inline=True)
        embed.add_field(name="📊 Servidores", value=str(len(interaction.client.guilds)), inline=True)
        embed.add_field(name="👥 Usuários Totais", value=str(len(interaction.client.users)), inline=True)
        embed.add_field(name="📚 Biblioteca", value=f"Nextcord v{nextcord.__version__}", inline=True)
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
        embed.set_footer(text=f"Obrigado por usar o bot! {EMOJI_HAPPY}")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="avatar",
        description="Mostra o avatar de um usuário (ou o seu)."
    )
    async def avatar(self, interaction: Interaction, usuario: Member = SlashOption(required=False, description="O usuário para ver o avatar (deixe em branco para você mesmo)")):
        """Exibe o avatar de um membro do servidor."""
        target_user = usuario or interaction.user
        embed = self.info_select_helper.create_avatar_embed(target_user)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="banner",
        description="Mostra o banner de um usuário (ou o seu)."
    )
    async def banner(self, interaction: Interaction, usuario: nextcord.User = SlashOption(required=False, description="O usuário para ver o banner (deixe em branco para você mesmo)")):
        """Exibe o banner de perfil de um usuário (requer fetch)."""
        target_user = usuario or interaction.user
        await interaction.response.defer() # Fetch pode demorar
        try:
            fetched_user = await self.bot.fetch_user(target_user.id)
            embed = self.info_select_helper.create_banner_embed(fetched_user)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            print(f"Erro ao buscar banner no comando /banner: {e}")
            await interaction.followup.send(f"{EMOJI_FAILURE} Não foi possível obter o banner para {target_user.mention}.", ephemeral=True)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="roleinfo",
        description="Mostra informações sobre um cargo específico."
    )
    async def roleinfo(self, interaction: Interaction, cargo: Role = SlashOption(description="O cargo para ver as informações")):
        """Exibe informações detalhadas sobre um cargo do servidor."""
        embed = Embed(title=f"🎭 Informações do Cargo: {cargo.name}", color=cargo.color)
        embed.add_field(name="🆔 ID", value=cargo.id, inline=True)
        embed.add_field(name="🎨 Cor (Hex)", value=str(cargo.color), inline=True)
        embed.add_field(name="👥 Membros com o Cargo", value=str(len(cargo.members)), inline=True)
        embed.add_field(name="📌 Posição", value=str(cargo.position), inline=True)
        embed.add_field(name=" hoisting?", value=f"{EMOJI_SUCCESS if cargo.hoist else EMOJI_FAILURE}", inline=True)
        embed.add_field(name="🗣️ Mencionável?", value=f"{EMOJI_SUCCESS if cargo.mentionable else EMOJI_FAILURE}", inline=True)
        creation_timestamp = int(cargo.created_at.timestamp())
        embed.add_field(name="📅 Criado em", value=f"<t:{creation_timestamp}:F> (<t:{creation_timestamp}:R>)", inline=False)
        # TODO: Listar permissões?
        await interaction.response.send_message(embed=embed)
        
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="channelinfo",
        description="Mostra informações sobre um canal específico."
    )
    async def channelinfo(self, interaction: Interaction, canal: nextcord.abc.GuildChannel = SlashOption(required=False, description="O canal para ver as informações (padrão: canal atual)")):
        """Exibe informações detalhadas sobre um canal do servidor."""
        target_channel = canal or interaction.channel
        
        embed = Embed(title=f"ℹ️ Informações do Canal: #{target_channel.name}", color=Color.blurple())
        embed.add_field(name="🆔 ID", value=target_channel.id, inline=True)
        embed.add_field(name="🏷️ Tipo", value=str(target_channel.type).capitalize(), inline=True)
        embed.add_field(name="📌 Posição", value=str(target_channel.position), inline=True)
        
        creation_timestamp = int(target_channel.created_at.timestamp())
        embed.add_field(name="📅 Criado em", value=f"<t:{creation_timestamp}:F> (<t:{creation_timestamp}:R>)", inline=False)
        
        if target_channel.category:
            embed.add_field(name="📚 Categoria", value=target_channel.category.name, inline=True)
            
        if isinstance(target_channel, TextChannel):
            embed.add_field(name="🐌 Slowmode", value=f"{target_channel.slowmode_delay}s" if target_channel.slowmode_delay > 0 else "Desativado", inline=True)
            embed.add_field(name="🔞 NSFW?", value=f"{EMOJI_SUCCESS if target_channel.is_nsfw() else EMOJI_FAILURE}", inline=True)
            embed.add_field(name="📰 Tópico", value=target_channel.topic or "Nenhum", inline=False)
        elif isinstance(target_channel, VoiceChannel):
            embed.add_field(name="👤 Limite de Usuários", value=str(target_channel.user_limit) if target_channel.user_limit > 0 else "Sem limite", inline=True)
            embed.add_field(name="🔊 Bitrate", value=f"{target_channel.bitrate // 1000} kbps", inline=True)
            embed.add_field(name="🌍 Região", value=str(target_channel.rtc_region) or "Automático", inline=True)
        elif isinstance(target_channel, CategoryChannel):
            embed.add_field(name="📢 Canais na Categoria", value=str(len(target_channel.channels)), inline=True)
        # Adicionar mais tipos se necessário (Stage, Forum, etc.)
            
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="emojis",
        description="Lista os emojis deste servidor."
    )
    async def emojis(self, interaction: Interaction):
        """Exibe a lista de emojis estáticos e animados do servidor."""
        if not interaction.guild:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        embed = self.info_select_helper.create_server_emojis_embed(interaction.guild)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="uptime",
        description="Mostra há quanto tempo o bot está online."
    )
    async def uptime(self, interaction: Interaction):
        """Exibe o tempo de atividade do bot desde a última inicialização."""
        delta = datetime.datetime.utcnow() - self.start_time
        uptime_str = format_timedelta(delta)
        embed = Embed(title="⏱️ Uptime do Bot", description=f"{EMOJI_SUCCESS} Online há: **{uptime_str}**", color=Color.gold())
        await interaction.response.send_message(embed=embed)

# Função setup para carregar a cog
def setup(bot):
    bot.add_cog(Informacoes(bot))
