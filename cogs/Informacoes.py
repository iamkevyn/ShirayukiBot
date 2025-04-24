import platform
import psutil
import datetime

import nextcord
from nextcord import Interaction, Embed
from nextcord.ext import commands

CRIADOR_ID = 1278842453159444582
DATA_CRIACAO = "22 de Abril de 2025"
PRIMEIRO_SERVIDOR = "Jardim Secreto"
SLOGAN = "Um Bot Para A Vida!"

class InfoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(InfoSelect())

class InfoSelect(ui.Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="Sobre o Bot", description="Informações gerais"),
            nextcord.SelectOption(label="Usuário", description="Dados do seu perfil"),
            nextcord.SelectOption(label="Servidor", description="Informações do servidor atual"),
            nextcord.SelectOption(label="Sistema do Bot", description="Status e uso de sistema"),
            nextcord.SelectOption(label="Avatar", description="Veja avatares"),
            nextcord.SelectOption(label="Uptime", description="Tempo online do bot"),
            nextcord.SelectOption(label="Cargos", description="Veja os cargos de um membro"),
            nextcord.SelectOption(label="Banner", description="Veja o banner de um usuário"),
            nextcord.SelectOption(label="Emojis", description="Lista os emojis do servidor")
        ]
        super().__init__(placeholder="Escolha uma opção", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        label = self.values[0]
        if label == "Sobre o Bot":
            embed = Embed(title="🤖 Sobre o Bot", description=SLOGAN, color=0x00BFFF)
            embed.add_field(name="📅 Criado em", value=DATA_CRIACAO, inline=True)
            embed.add_field(name="🛡️ Primeiro servidor", value=PRIMEIRO_SERVIDOR, inline=True)
            embed.add_field(name="👤 Criador", value=f"<@{1278842453159444582}>", inline=True)
            embed.set_footer(text="Obrigado por usar o bot! 💙")
        elif label == "Usuário":
            user = interaction.user
            embed = Embed(title="👤 Informações do Usuário", color=0x3498db)
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.add_field(name="Nome", value=user.name, inline=True)
            embed.add_field(name="ID", value=user.id, inline=True)
            embed.add_field(name="Criador?", value="Sim" if user.id == CRIADOR_ID else "Não", inline=True)
            embed.set_footer(text="Legal te ver por aqui!")
        elif label == "Servidor":
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
        elif label == "Sistema do Bot":
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent()
            embed = Embed(title="💻 Status do Bot", color=0xffc300)
            embed.add_field(name="Versão Python", value=platform.python_version(), inline=True)
            embed.add_field(name="Sistema", value=platform.system(), inline=True)
            embed.add_field(name="Uso de CPU", value=f"{cpu}%", inline=True)
            embed.add_field(name="Uso de RAM", value=f"{memory.percent}%", inline=True)
            embed.set_footer(text="Monitoramento em tempo real.")
        elif label == "Avatar":
            user = interaction.user
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            embed = Embed(title=f"🖼️ Avatar de {user.name}", color=0x9b59b6)
            embed.set_image(url=avatar_url)
        elif label == "Uptime":
            now = datetime.datetime.utcnow()
            delta = now - interaction.client.get_cog("Informacoes").start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            embed = Embed(title="⏱️ Uptime do Bot", description=f"{hours}h {minutes}m {seconds}s", color=0xf39c12)
        elif label == "Cargos":
            user = interaction.user
            roles = [role.mention for role in user.roles if role.name != "@everyone"]
            roles_str = ", ".join(roles) if roles else "Nenhum cargo."
            embed = Embed(title=f"👥 Cargos de {user.display_name}", description=roles_str, color=0xe67e22)
        elif label == "Banner":
            user = await interaction.client.fetch_user(interaction.user.id)
            embed = Embed(title=f"🖼️ Banner de {user.name}", color=0x1abc9c)
            if user.banner:
                embed.set_image(url=user.banner.url)
            else:
                embed.description = "❌ Esse usuário não possui um banner."
        elif label == "Emojis":
            guild = interaction.guild
            if not guild.emojis:
                embed = Embed(description="❌ Este servidor não possui emojis personalizados.", color=0xe74c3c)
            else:
                emoji_list = " ".join(str(emoji) for emoji in guild.emojis[:50])
                embed = Embed(title="😀 Emojis do servidor", description=emoji_list, color=0x95a5a6)

        await interaction.response.edit_message(embed=embed, view=self.view)

class Informacoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.utcnow()

    @nextcord.slash_command(name="painel_info", description="Abre o painel interativo de informações")
    async def painel_info(self, interaction: Interaction):
        embed = Embed(title="📊 Painel de Informações", description="Selecione uma categoria abaixo:", color=0x7289da)
        await interaction.response.send_message(embed=embed, view=InfoView(), ephemeral=True)

def setup(bot):
    bot.add_cog(Informacoes(bot))
