import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction, SlashOption, Embed, ButtonStyle
from nextcord.ui import View, Button
import asyncio
import yt_dlp
import os
import functools
import datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'cookiefile': 'cookies.txt',
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

class QueuePaginatorView(View):
    def __init__(self, embeds):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.page = 0

        self.prev_button = Button(label="⬅️", style=ButtonStyle.gray)
        self.next_button = Button(label="➡️", style=ButtonStyle.gray)

        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def update_message(self, interaction: Interaction):
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    async def prev_page(self, interaction: Interaction):
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    async def next_page(self, interaction: Interaction):
        if self.page < len(self.embeds) - 1:
            self.page += 1
            await self.update_message(interaction)

class MusicButtonView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @nextcord.ui.button(emoji="⏯️", style=ButtonStyle.gray)
    async def pause_resume(self, button: Button, interaction: Interaction):
        vc = self.cog.get_voice_client(interaction.guild)
        if vc.is_playing():
            vc.pause()
        elif vc.is_paused():
            vc.resume()
        await interaction.response.defer()

    @nextcord.ui.button(emoji="⏭️", style=ButtonStyle.blurple)
    async def skip(self, button: Button, interaction: Interaction):
        vc = self.cog.get_voice_client(interaction.guild)
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        await interaction.response.defer()

    @nextcord.ui.button(emoji="⏹️", style=ButtonStyle.red)
    async def stop(self, button: Button, interaction: Interaction):
        vc = self.cog.get_voice_client(interaction.guild)
        if vc:
            await vc.disconnect()
            self.cog.queues.pop(interaction.guild.id, None)
        await interaction.response.defer()

    @nextcord.ui.button(emoji="🔁", style=ButtonStyle.gray)
    async def shuffle(self, button: Button, interaction: Interaction):
        queue = self.cog.queues.get(interaction.guild.id, [])
        if queue:
            import random
            random.shuffle(queue)
        await interaction.response.defer()

    @nextcord.ui.button(emoji="⏮️", style=ButtonStyle.gray)
    async def back(self, button: Button, interaction: Interaction):
        await interaction.followup.send("Função de voltar ainda não implementada.")

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.autoleave_check.start()

    def get_voice_client(self, guild):
        return nextcord.utils.get(self.bot.voice_clients, guild=guild)

    async def search_youtube(self, query):
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    return [{'title': entry['title'], 'url': entry['url'], 'webpage_url': entry['webpage_url']} for entry in info['entries'] if entry]
                return [{'title': info['title'], 'url': info['url'], 'webpage_url': info['webpage_url']}]
            except Exception as e:
                print(f"Erro ao buscar música: {e}")
                return None

    async def prepare_source(self, url):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False))
        return nextcord.FFmpegPCMAudio(data['url'])

    async def play_next(self, ctx):
        vc = self.get_voice_client(ctx.guild)
        if not self.queues[ctx.guild.id]:
            return

        song = self.queues[ctx.guild.id].pop(0)
        source = await self.prepare_source(song['url'])

        def after_playing(err):
            if err:
                print(f"Erro ao tocar: {err}")
            fut = self.play_next(ctx)
            asyncio.run_coroutine_threadsafe(fut, self.bot.loop)

        vc.play(source, after=after_playing)

    def extract_spotify_tracks(self, url):
        results = []
        if 'track' in url:
            track = sp.track(url)
            results.append(f"{track['name']} {track['artists'][0]['name']}")
        elif 'playlist' in url:
            playlist = sp.playlist_tracks(url)
            results.extend(f"{item['track']['name']} {item['track']['artists'][0]['name']}" for item in playlist['items'])
        return results

    @commands.slash_command(name="tocar", description="Toca uma música do YouTube ou Spotify")
    async def tocar(self, interaction: Interaction, query: str = SlashOption(description="Nome ou link da música")):
        await interaction.response.defer()
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Você precisa estar em um canal de voz!")
            return

        vc = self.get_voice_client(interaction.guild)
        if not vc:
            vc = await interaction.user.voice.channel.connect()
            self.queues[interaction.guild.id] = []

        search_terms = self.extract_spotify_tracks(query) if "spotify" in query else [query]

        for term in search_terms:
            songs = await self.search_youtube(term)
            if songs:
                self.queues[interaction.guild.id].extend(songs)

        embed = Embed(title="🎶 Músicas adicionadas", description=f"Total: {len(search_terms)} músicas", color=0x1DB954)
        await interaction.followup.send(embed=embed, view=MusicButtonView(self))

        if not vc.is_playing() and not vc.is_paused():
            await self.play_next(interaction)

    @commands.slash_command(name="fila", description="Mostra a fila de reprodução")
    async def fila(self, interaction: Interaction):
        queue = self.queues.get(interaction.guild.id, [])
        if not queue:
            await interaction.response.send_message("A fila está vazia.")
            return

        embeds = []
        for i in range(0, len(queue), 5):
            embed = Embed(title="📜 Fila de músicas", color=0x1DB954)
            for j, song in enumerate(queue[i:i+5], start=i+1):
                embed.add_field(name=f"{j}.", value=f"[{song['title']}]({song['webpage_url']})", inline=False)
            embeds.append(embed)

        view = QueuePaginatorView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view)

    @tasks.loop(minutes=1)
    async def autoleave_check(self):
        for vc in self.bot.voice_clients:
            if not vc.is_playing() and not vc.is_paused():
                guild_id = vc.guild.id
                if hasattr(vc, "idle_since"):
                    if (datetime.datetime.utcnow() - vc.idle_since).seconds > 900:
                        await vc.disconnect()
                        print(f"Saindo automaticamente do canal em {vc.guild.name}")
                        self.queues.pop(guild_id, None)
                else:
                    vc.idle_since = datetime.datetime.utcnow()
            else:
                if hasattr(vc, "idle_since"):
                    del vc.idle_since

def setup(bot):
    bot.add_cog(Music(bot))
