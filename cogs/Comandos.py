# /home/ubuntu/ShirayukiBot/cogs/Comandos.py
# Cog principal para comandos gerais e o sistema de ajuda.

import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Button

# ID do servidor fornecido pelo usuário para carregamento rápido de comandos
SERVER_ID = 1367345048458498219

# --- Emojis Customizados ---
EMOJI_SUCCESS = "<:8_:1366997164521164830>" # Emoji de sucesso
EMOJI_FAILURE = "<:1_:1366996823654535208>" # Emoji de falha/triste
EMOJI_INFO = "<:7_:1366997117410873404>"    # Emoji de informação/neutro
EMOJI_WAIT = "<:2_:1366996885398749254>"     # Emoji de espera
EMOJI_QUESTION = "<:6_:1366997079347429427>" # Emoji de dúvida/ajuda
EMOJI_WARN = "<:4_:1366996921297801216>"     # Emoji de aviso
EMOJI_CELEBRATE = "<:5_:1366997045445132360>" # Emoji de celebração
EMOJI_HAPPY = "<:3_:1366996904663322654>"     # Emoji feliz genérico

# --- View para o Comando Help ---
class HelpView(View):
    def __init__(self, bot):
        super().__init__(timeout=180) # Timeout de 3 minutos
        self.bot = bot
        # Adiciona botões para cada categoria de cog
        self.add_item(Button(label="Comandos", custom_id="help_comandos", style=nextcord.ButtonStyle.blurple))
        self.add_item(Button(label="Economia", custom_id="help_economia", style=nextcord.ButtonStyle.green))
        self.add_item(Button(label="Informações", custom_id="help_informacoes", style=nextcord.ButtonStyle.grey))
        self.add_item(Button(label="Interações", custom_id="help_interacoes", style=nextcord.ButtonStyle.blurple))
        self.add_item(Button(label="Jogos", custom_id="help_jogos", style=nextcord.ButtonStyle.green))
        self.add_item(Button(label="Utilitários", custom_id="help_utilitarios", style=nextcord.ButtonStyle.grey))
        # Botão para Música (mesmo desativada)
        self.add_item(Button(label="Música", custom_id="help_musica", style=nextcord.ButtonStyle.red))

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        # Permite que qualquer um use os botões por enquanto
        return True

    async def send_cog_help(self, interaction: nextcord.Interaction, cog_name: str):
        """Função auxiliar para enviar a ajuda de uma cog específica."""
        cog = self.bot.get_cog(cog_name)
        if not cog:
            await interaction.response.edit_message(content=f"{EMOJI_FAILURE} Categoria '{cog_name}' não encontrada ou desativada.", embed=None, view=self)
            return

        embed = nextcord.Embed(title=f"{EMOJI_QUESTION} Ajuda - {cog_name}", color=nextcord.Color.blue())
        commands_list = []
        for command in cog.get_application_commands():
            # TODO: Melhorar a formatação da descrição e parâmetros
            commands_list.append(f"</{command.name}:{command.id}> - {command.description or 'Sem descrição.'}")

        if not commands_list:
            embed.description = f"{EMOJI_INFO} Nenhum comando encontrado nesta categoria."
        else:
            embed.description = "\n".join(commands_list)

        # Indicar se a cog está desativada (ex: Música)
        if cog_name == "Musica" and "Musica.py" not in [f.split('/')[-1] for f in self.bot.cogs]: # Checa se a cog Musica não está carregada
             embed.add_field(name=f"{EMOJI_WARN} Atenção", value="Esta categoria (Música) está temporariamente desativada.")

        await interaction.response.edit_message(embed=embed, view=self)

    @nextcord.ui.button(label="Comandos", custom_id="help_comandos", style=nextcord.ButtonStyle.blurple)
    async def show_comandos(self, button: Button, interaction: nextcord.Interaction):
        await self.send_cog_help(interaction, "Comandos")

    @nextcord.ui.button(label="Economia", custom_id="help_economia", style=nextcord.ButtonStyle.green)
    async def show_economia(self, button: Button, interaction: nextcord.Interaction):
        await self.send_cog_help(interaction, "Economia")

    @nextcord.ui.button(label="Informações", custom_id="help_informacoes", style=nextcord.ButtonStyle.grey)
    async def show_informacoes(self, button: Button, interaction: nextcord.Interaction):
        await self.send_cog_help(interaction, "Informacoes")

    @nextcord.ui.button(label="Interações", custom_id="help_interacoes", style=nextcord.ButtonStyle.blurple)
    async def show_interacoes(self, button: Button, interaction: nextcord.Interaction):
        await self.send_cog_help(interaction, "Interacoes")

    @nextcord.ui.button(label="Jogos", custom_id="help_jogos", style=nextcord.ButtonStyle.green)
    async def show_jogos(self, button: Button, interaction: nextcord.Interaction):
        await self.send_cog_help(interaction, "Jogos")

    @nextcord.ui.button(label="Utilitários", custom_id="help_utilitarios", style=nextcord.ButtonStyle.grey)
    async def show_utilitarios(self, button: Button, interaction: nextcord.Interaction):
        await self.send_cog_help(interaction, "Utilitarios")

    @nextcord.ui.button(label="Música", custom_id="help_musica", style=nextcord.ButtonStyle.red)
    async def show_musica(self, button: Button, interaction: nextcord.Interaction):
        await self.send_cog_help(interaction, "Musica") # A função send_cog_help tratará o caso desativado

# --- Cog Comandos ---
class Comandos(commands.Cog):
    """Cog responsável pelos comandos gerais e pelo sistema de ajuda interativo."""

    def __init__(self, bot):
        self.bot = bot
        print(f"[DIAGNÓSTICO] Cog Comandos carregada.")

    @nextcord.slash_command(
        guild_ids=[SERVER_ID], # Registra apenas neste servidor para testes rápidos
        name="ajuda",
        description="Mostra a lista de comandos disponíveis."
    )
    async def ajuda(self, interaction: nextcord.Interaction):
        """Exibe um painel de ajuda interativo com botões para categorias de comandos."""
        embed = nextcord.Embed(
            title=f"{EMOJI_QUESTION} Ajuda - ShirayukiBot",
            description=f"Olá {interaction.user.mention}! {EMOJI_HAPPY}\nUse os botões abaixo para navegar pelas categorias de comandos.",
            color=nextcord.Color.blue()
        )
        embed.set_footer(text="Selecione uma categoria para ver os comandos.")
        view = HelpView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Adicionar outros comandos GERAIS aqui (ex: ping, info do bot, etc.)
    # Lembre-se de usar guild_ids=[SERVER_ID] para registro rápido durante o desenvolvimento.
    # Para comandos globais, remova o guild_ids.

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="ping", description="Testa a latência do bot.")
    async def ping(self, interaction: nextcord.Interaction):
        """Verifica a latência do bot."""
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"{EMOJI_SUCCESS} Pong! Latência: {latency}ms")

    # --- Comandos para adicionar/expandir --- 
    # - Comando de informações do servidor
    # - Comando de informações do usuário
    # - Comando de avatar
    # - Comando de banner
    # - Comando de sugestão
    # - Comando de reportar bug
    # - Comandos de moderação básicos (kick, ban, mute - com confirmação e logs)
    # - ... (Expandir para atingir a meta de linhas)

# Função setup para carregar a cog
def setup(bot):
    bot.add_cog(Comandos(bot))

# Nota: Registrar comandos com guild_ids=[SERVER_ID] faz com que eles apareçam quase instantaneamente
# no servidor especificado, ideal para desenvolvimento e testes. Comandos globais podem levar
# até uma hora para serem registrados.
