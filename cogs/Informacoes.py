import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Embed, SlashOption
import platform
import psutil
import datetime

CRIADOR_ID = 1278842453159444582
DATA_CRIACAO = "22 de Abril de 2025"
PRIMEIRO_SERVIDOR = "Jardim Secreto"
SLOGAN = "Um Bot Para A Vida!"

class Informacoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.utcnow()

    @nextcord.slash_command(name="info", description="Exibe informações sobre o bot")
    async def info(self, interaction: Interaction):
        embed = Embed(title="🤖 Sobre o Bot", description=SLOGAN, color=0x00BFFF)
        embed.add_field(name="📅 Criado em", value=DATA_CRIACAO, inline=True)
        embed.add_field(name="🛡️ Primeiro servidor", value=PRIMEIRO_SERVIDOR, inline=True)
        embed.add_field(name="👤 Criador", value=f"<@{CRIADOR_ID}>", inline=True)
        embed.set_footer(text="Obrigado por usar o bot! 💙")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="user", description="Exibe informações sobre o usuário")
    async def user(self, interaction: Interaction):
        user = interaction.user
        embed = Embed(title="👤 Informações do Usuário", color=0x3498db)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.add_field(name="Nome", value=user.name, inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Criador?", value="Sim" if user.id == CRIADOR_ID else "Não", inline=True)
        embed.set_footer(text="Legal te ver por aqui!")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="server", description="Mostra informações sobre o servidor")
    async def server(self, interaction: Interaction):
        guild = interaction.guild
        embed = Embed(title="🌐 Informações do Servidor", color=0x2ecc71)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
        embed.add_field(name="Nome", value=guild.name, inline=True)
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Membros", value=guild.member_count, inline=True)
        embed.add_field(name="Criador", value=guild.owner.mention, inline=True)
        embed.add_field(name="Impulsos", value=guild.premium_subscription_count or 0, inline=True)
        embed.add_field(name="Nível de Impulso", value=str(guild.premium_tier), inline=True)
        embed.set_footer(text="Servidor incrível!")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="bot", description="Mostra informações técnicas do bot")
    async def bot(self, interaction: Interaction):
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        embed = Embed(title="💻 Status do Bot", color=0xffc300)
        embed.add_field(name="Versão Python", value=platform.python_version(), inline=True)
        embed.add_field(name="Sistema", value=platform.system(), inline=True)
        embed.add_field(name="Uso de CPU", value=f"{cpu}%", inline=True)
        embed.add_field(name="Uso de RAM", value=f"{memory.percent}%", inline=True)
        embed.set_footer(text="Monitoramento em tempo real.")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="ping", description="Mostra o ping do bot")
    async def ping(self, interaction: Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! Latência: {latency}ms")

    @nextcord.slash_command(name="avatar", description="Mostra o avatar de um usuário")
    async def avatar(self, interaction: Interaction, user: nextcord.User = SlashOption(description="Usuário", required=False)):
        user = user or interaction.user
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        embed = Embed(title=f"🖼️ Avatar de {user.name}", color=0x9b59b6)
        embed.set_image(url=avatar_url)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="uptime", description="Mostra há quanto tempo o bot está online")
    async def uptime(self, interaction: Interaction):
        now = datetime.datetime.utcnow()
        delta = now - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        await interaction.response.send_message(f"⏱️ Uptime: {hours}h {minutes}m {seconds}s")

    @nextcord.slash_command(name="roles", description="Mostra os cargos de um membro")
    async def roles(self, interaction: Interaction, user: nextcord.Member = SlashOption(description="Usuário", required=False)):
        user = user or interaction.user
        roles = [role.mention for role in user.roles if role.name != "@everyone"]
        roles_str = ", ".join(roles) if roles else "Nenhum cargo."
        await interaction.response.send_message(f"👥 Cargos de {user.mention}: {roles_str}")

    @nextcord.slash_command(name="banner", description="Mostra o banner de um usuário")
    async def banner(self, interaction: Interaction, user: nextcord.User = SlashOption(description="Usuário", required=False)):
        user = user or interaction.user
        user = await self.bot.fetch_user(user.id)
        if user.banner:
            await interaction.response.send_message(f"🖼️ Banner de {user.name}: {user.banner.url}")
        else:
            await interaction.response.send_message("❌ Esse usuário não possui um banner.")

    @nextcord.slash_command(name="emojis", description="Lista os emojis do servidor")
    async def emojis(self, interaction: Interaction):
        guild = interaction.guild
        if not guild.emojis:
            await interaction.response.send_message("❌ Este servidor não possui emojis personalizados.")
        else:
            emoji_list = " ".join(str(emoji) for emoji in guild.emojis[:50])
            await interaction.response.send_message(f"😀 Emojis do servidor:\n{emoji_list}")

def setup(bot):
    bot.add_cog(Informacoes(bot))
