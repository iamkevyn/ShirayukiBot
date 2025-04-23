import nextcord
from nextcord.ext import commands
from nextcord import Interaction
import random

class Utilitarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="clear", description="Limpa uma quantidade de mensagens")
    async def clear(self, interaction: Interaction, number: int):
        await interaction.channel.purge(limit=number)
        await interaction.response.send_message(f"{number} mensagens deletadas!", ephemeral=True)

    @nextcord.slash_command(name="roll", description="Rolagem de dados aleatória")
    async def roll(self, interaction: Interaction):
        await interaction.response.send_message(f"Você rolou: {random.randint(1, 6)}")

    @nextcord.slash_command(name="coinflip", description="Joga uma moeda (cara ou coroa)")
    async def coinflip(self, interaction: Interaction):
        result = "Cara" if random.choice([True, False]) else "Coroa"
        await interaction.response.send_message(f"O resultado foi: {result}")

def setup(bot):
    bot.add_cog(Utilitarios(bot))
