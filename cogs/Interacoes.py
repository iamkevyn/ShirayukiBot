import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Embed
import random

INTERACTION_GIFS = {
    "hug": [
        "https://media.tenor.com/2roX3uxz_68AAAAC/hug.gif",
        "https://media.tenor.com/NeXn0mMF5iYAAAAC/anime-hug.gif",
        "https://media.tenor.com/Jl8nD1kOAQMAAAAC/kyoukai-no-kanata-hug.gif"
    ],
    "kiss": [
        "https://media.tenor.com/Bq7iU7yb3OsAAAAC/kiss-anime.gif",
        "https://media.tenor.com/0AVn4U0VOnwAAAAC/anime-kiss.gif",
        "https://media.tenor.com/QvL8v7lPPX8AAAAC/kaguya-sama-kiss.gif"
    ],
    "slap": [
        "https://media.tenor.com/5zv7N_p4OZMAAAAC/anime-slap.gif",
        "https://media.tenor.com/RwD7bRfGzIYAAAAC/slap.gif",
        "https://media.tenor.com/2xl4JgxTtIUAAAAC/anime-hit.gif"
    ],
    "pat": [
        "https://media.tenor.com/7vZ9TnA1fFQAAAAC/pat-head.gif",
        "https://media.tenor.com/YGdCdp9bMGUAAAAC/anime-pat.gif",
        "https://media.tenor.com/wfTj8Dh9EYAAAAAC/pat-anime.gif"
    ],
    "bite": [
        "https://media.tenor.com/UDfwDPuV_yoAAAAC/anime-bite.gif",
        "https://media.tenor.com/xsKZJ8-LUGkAAAAC/anime.gif",
        "https://media.tenor.com/W9FJKdGzOjcAAAAC/bite-anime.gif"
    ],
    "lick": [
        "https://media.tenor.com/bJDa8H-rQZ4AAAAC/anime-lick.gif",
        "https://media.tenor.com/RRjht8v7voIAAAAC/lick-anime.gif",
        "https://media.tenor.com/B5sh8dESbZ4AAAAC/anime-licking.gif"
    ],
    "punch": [
        "https://media.tenor.com/LIYkB7qz2JQAAAAC/anime-punch.gif",
        "https://media.tenor.com/bmA4WcLh-YkAAAAC/punch-anime.gif",
        "https://media.tenor.com/TS8u4IS_2NIAAAAC/punch-hit.gif"
    ],
    "kick": [
        "https://media.tenor.com/_uS2CBQW0aYAAAAC/kick-anime.gif",
        "https://media.tenor.com/GzyM0mHf2ksAAAAC/anime-kick.gif",
        "https://media.tenor.com/rNHyL8PzAoYAAAAC/kick.gif"
    ],
    "cuddle": [
        "https://media.tenor.com/Pj4YjKdCMhcAAAAC/anime-cuddle.gif",
        "https://media.tenor.com/Nhcz0gKaNfcAAAAC/anime-hug-cuddle.gif",
        "https://media.tenor.com/NtdhsW5TKaAAAAAC/cuddle.gif"
    ],
    "poke": [
        "https://media.tenor.com/vEGlwQZ9HdgAAAAC/poke-anime.gif",
        "https://media.tenor.com/fuX0aW1FhZsAAAAC/anime-poke.gif",
        "https://media.tenor.com/7uhzLQxcmcUAAAAC/poking-anime.gif"
    ],
    "highfive": [
        "https://media.tenor.com/jC1aHxw_d7gAAAAC/anime-highfive.gif",
        "https://media.tenor.com/MNeOgw0Af5sAAAAC/highfive-anime.gif",
        "https://media.tenor.com/j2doT4CBhyUAAAAC/high-five-anime.gif"
    ],
    "wave": [
        "https://media.tenor.com/WRR8oR6pqOwAAAAC/anime-wave.gif",
        "https://media.tenor.com/pS5fGiDw6vQAAAAC/hi-hello.gif",
        "https://media.tenor.com/qHdzgBl8XMQAAAAC/hello-anime.gif"
    ],
    "stare": [
        "https://media.tenor.com/GzEcNNhxW7IAAAAC/anime-stare.gif",
        "https://media.tenor.com/lZZzHtJAM7EAAAAC/stare-anime.gif",
        "https://media.tenor.com/lE84w_Vl_WUAAAAC/anime-look.gif"
    ],
    "dance": [
        "https://media.tenor.com/NZfPdV2pFFYAAAAC/anime-dance.gif",
        "https://media.tenor.com/TObCV91w6bEAAAAC/dance.gif",
        "https://media.tenor.com/4cKkGBeAKDMAAAAC/anime-dancing.gif"
    ],
    "blush": [
        "https://media.tenor.com/1v3uPQVCn6cAAAAC/anime-blush.gif",
        "https://media.tenor.com/FJwHkE_JwCwAAAAC/blush-anime.gif",
        "https://media.tenor.com/lkW5R4SBYWwAAAAC/blushing-anime.gif"
    ],
    "cry": [
        "https://media.tenor.com/6u6UEvWhYdwAAAAC/crying-anime.gif",
        "https://media.tenor.com/RVvnVPK-6dcAAAAC/anime-crying.gif",
        "https://media.tenor.com/RSj3vGkL5X8AAAAC/cry-anime.gif"
    ],
    "sleep": [
        "https://media.tenor.com/9iS9kivD8JMAAAAC/sleepy.gif",
        "https://media.tenor.com/ZghfHZ-W4B0AAAAC/sleep.gif",
        "https://media.tenor.com/BzLaCmQ_WQQAAAAC/anime-sleep.gif"
    ],
    "feed": [
        "https://media.tenor.com/3vDgHFUAN7gAAAAC/feed-anime.gif",
        "https://media.tenor.com/zDjHvJbuwq4AAAAC/anime-feed.gif",
        "https://media.tenor.com/Ll9d9CnJGywAAAAC/feeding-anime.gif"
    ]
}

class Interacoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_embed(self, action, user1, user2):
        gif = random.choice(INTERACTION_GIFS[action])
        embed = Embed(
            title=f"{user1.name} {self.verb(action)} {user2.name}!",
            color=0xff69b4
        )
        embed.set_image(url=gif)
        embed.set_footer(text="Interações animadas ✨")
        return embed

    def verb(self, action):
        return {
            "hug": "abraçou",
            "kiss": "beijou",
            "slap": "deu um tapa em",
            "pat": "acariciou",
            "bite": "mordeu",
            "lick": "lambeu",
            "punch": "deu um soco em",
            "kick": "chutou",
            "cuddle": "se aconchegou com",
            "poke": "cutucou",
            "highfive": "bateu um highfive com",
            "wave": "acenou para",
            "stare": "encarou",
            "dance": "dançou com",
            "blush": "ficou corado com",
            "cry": "chorou com",
            "sleep": "dormiu junto com",
            "feed": "deu comida para"
        }.get(action, action)

    async def interaction_command(self, interaction: Interaction, user: nextcord.Member, action: str):
        if user.id == interaction.user.id:
            await interaction.response.send_message(f"😅 {interaction.user.mention} tentou {self.verb(action)} a si mesmo... está tudo bem por aí?", ephemeral=True)
        else:
            embed = self.get_embed(action, interaction.user, user)
            await interaction.response.send_message(embed=embed)

    def add_command(self, name, description):
        async def command(interaction: Interaction, user: nextcord.Member):
            await self.interaction_command(interaction, user, name)
        command.__name__ = name
        setattr(self, name, nextcord.slash_command(name=name, description=description)(command))

    def cog_load(self):
        for name in INTERACTION_GIFS:
            if not hasattr(self, name):
                self.add_command(name, f"{self.verb(name).capitalize()} um usuário")


def setup(bot):
    bot.add_cog(Interacoes(bot))
