import os
import asyncio
import datetime
import random
import nextcord
from nextcord import Interaction, Embed, ButtonStyle
from nextcord.ui import View, Button
from nextcord.ext import commands, tasks
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Configurações do yt_dlp
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "cookiefile": "cookies.txt",
    "default_search": "ytsearch",
    "noplaylist": False,
    "source_address": "0.0.0.0"
}

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# View para botões
class MusicControlView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @nextcord.ui.button(emoji="⏯️", style=ButtonStyle.gray)
    async def toggle(self, button, interaction: Interaction):
        vc = self.cog.get_voice(interaction.guild)
        if vc.is_playing():
            vc.pause()
        elif vc.is_paused():
            vc.resume()
        await interaction.response.defer()

    @nextcord.ui.button(emoji="⏭️", style=ButtonStyle.blurple)
    async def skip(self, button, interaction: Interaction):
        vc = self.cog.get_voice(interaction.guild)
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        await interaction.response.defer()

    @nextcord.ui.button(emoji="🔀", style=ButtonStyle.gray)
    async def shuffle(self, button, interaction: Interaction):
        queue = self.cog.queues.get(interaction.guild.id, [])
        if queue:
            import random
            random.shuffle(queue)
        await interaction.response.defer()

    @nextcord.ui.button(emoji="⏹️", style=ButtonStyle.red)
    async def stop(self, button, interaction: Interaction):
        vc = self.cog.get_voice(interaction.guild)
        if vc:
            await vc.disconnect()
            self.cog.queues.pop(interaction.guild.id, None)
        await interaction.response.defer()

class QueuePaginatorView(View):
    def __init__(self, embeds):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.page = 0

        self.add_item(Button(label="⬅️", style=ButtonStyle.gray, custom_id="prev"))
        self.add_item(Button(label="➡️", style=ButtonStyle.gray, custom_id="next"))

    async def interaction_check(self, interaction: Interaction):
        return True

    async def interaction_handler(self, interaction: Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id == "prev" and self.page > 0:
            self.page -= 1
        elif custom_id == "next" and self.page < len(self.embeds) - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

class Musica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.autoleave.start()

    def get_voice(self, guild):
        return nextcord.utils.get(self.bot.voice_clients, guild=guild)

    async def yt_search(self, query):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(query, download=False))
        if "entries" in data:
            return [{"title": e["title"], "url": e["url"], "webpage_url": e["webpage_url"]} for e in data["entries"]]
        return [{"title": data["title"], "url": data["url"], "webpage_url": data["webpage_url"]}]

    async def prepare_audio(self, url):
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False))
        return nextcord.FFmpegPCMAudio(info["url"])

    def extract_spotify(self, link):
        faixas = []
        if "track" in link:
            track = sp.track(link)
            faixas.append(f"{track['name']} {track['artists'][0]['name']}")
        elif "playlist" in link:
            offset = 0
            while True:
                items = sp.playlist_items(link, offset=offset)["items"]
                if not items:
                    break
                faixas += [f"{i['track']['name']} {i['track']['artists'][0]['name']}" for i in items if i["track"]]
                offset += len(items)
        return faixas

    async def play_next(self, interaction):
        guild_id = interaction.guild.id
        vc = self.get_voice(interaction.guild)
        if not self.queues.get(guild_id):
            await vc.disconnect()
            return
        musica = self.queues[guild_id].pop(0)
        source = await self.prepare_audio(musica["url"])
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(interaction), self.bot.loop))
        embed = Embed(title="🎧 Tocando agora", description=f"[{musica['title']}]({musica['webpage_url']})", color=0x1DB954)
        await interaction.channel.send(embed=embed, view=MusicControlView(self))

    @commands.slash_command(name="tocar", description="Toque uma música ou playlist do YouTube/Spotify.")
    async def tocar(self, interaction: Interaction, query: str = SlashOption(description="Link ou nome da música")):
        await interaction.response.defer()
        if not interaction.user.voice:
            await interaction.followup.send("Você precisa estar em um canal de voz!")
            return
        vc = self.get_voice(interaction.guild)
        if not vc:
            vc = await interaction.user.voice.channel.connect()
            self.queues[interaction.guild.id] = []

        termos = self.extract_spotify(query) if "spotify" in query else [query]
        for termo in termos:
            resultados = await self.yt_search(termo)
            if resultados:
                self.queues[interaction.guild.id].append(resultados[0])

        if not vc.is_playing():
            await self.play_next(interaction)
        else:
            await interaction.followup.send(f"🎶 {len(termos)} música(s) adicionada(s) à fila!")

    @commands.slash_command(name="fila", description="Mostra a fila de músicas.")
    async def fila(self, interaction: Interaction):
        fila = self.queues.get(interaction.guild.id, [])
        if not fila:
            await interaction.response.send_message("A fila está vazia.")
            return

        embeds = []
        for i in range(0, len(fila), 5):
            embed = Embed(title="📜 Fila de Reprodução", color=0x1DB954)
            for j, musica in enumerate(fila[i:i+5], start=i+1):
                embed.add_field(name=f"{j}.", value=f"[{musica['title']}]({musica['webpage_url']})", inline=False)
            embeds.append(embed)
        await interaction.response.send_message(embed=embeds[0], view=QueuePaginatorView(embeds))

    @tasks.loop(minutes=1)
    async def autoleave(self):
        for vc in self.bot.voice_clients:
            if not vc.is_playing() and not vc.is_paused():
                guild_id = vc.guild.id
                if not hasattr(vc, "idle_since"):
                    vc.idle_since = datetime.datetime.utcnow()
                elif (datetime.datetime.utcnow() - vc.idle_since).seconds > 900:
                    await vc.disconnect()
                    self.queues.pop(guild_id, None)
            elif hasattr(vc, "idle_since"):
                del vc.idle_since

def setup(bot):
    bot.add_cog(Musica(bot))
