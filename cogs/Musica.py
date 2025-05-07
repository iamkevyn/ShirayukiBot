import nextcord
from nextcord import Interaction
from nextcord.ext import commands
import logging

logger = logging.getLogger('discord_bot.musica_cog_minima')

class MusicaMinima(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("--- [COG MINIMA] Cog MusicaMinima inicializada ---")

    @nextcord.slash_command(name="testecog", description="Um comando de teste simples dentro da cog.")
    async def teste_cog_slash(self, interaction: Interaction):
        logger.info(f"--- [COG MINIMA] Comando /testecog executado por {interaction.user} ---")
        await interaction.response.send_message("Olá! Este é um comando de teste da cog mínima!", ephemeral=True)
        logger.info("--- [COG MINIMA] Resposta do /testecog enviada. ---")

def setup(bot: commands.Bot):
    bot.add_cog(MusicaMinima(bot))
    logger.info("--- [COG MINIMA] Cog MusicaMinima adicionada ao bot via setup() ---")
