import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction, SlashOption, Embed, ButtonStyle
from nextcord.ui import View, Button
import asyncio
import yt_dlp
import os
import functools
import datetime

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'cookiefile': 'cookies.txt',  # Usa cookies.txt
    'default_search': 'ytsearch',
    'extract_flat': 'in_playlist',
    'source_address': '0.0.0.0',
}

class MusicButtonView(View):
    def __init__(self, cog, interaction: Interaction):
        super().__init__(timeout=None)
        self.cog = cog
        self.interaction = interaction

    @nextcord.ui.button(label="⏯ Pausar/Retomar", style=ButtonStyle.gray)
    async def pause_resume(self, button: Button, interaction: Interaction):
        vc = self.cog.get_voice_client(interaction.guild)
        if vc.is_playing():
            vc.pause()
        elif vc.is_paused():
            vc.resume()
        await interaction.response.defer()

    @nextcord.ui.button(label="⏭ Pular", style=ButtonStyle.blurple)
    async def skip(self, button: Button, interaction: Interaction):
        vc = self.cog.get_voice_client(interaction.guild)
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        await interaction.response.defer()

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
                    info = info['entries'][0]
                return {'title': info['title'], 'url': info['url'], 'webpage_url': info['webpage_url']}
            except Exception as e:
                print(f"Erro ao buscar música: {e}")
                return None

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

    async def prepare_source(self, url):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False))
        return nextcord.FFmpegPCMAudio(data['url'])

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

        song = await self.search_youtube(query)
        if not song:
            await interaction.followup.send("Não encontrei a música.")
            return

        self.queues[interaction.guild.id].append(song)
        embed = Embed(title="🎶 Adicionada à fila", description=f"[{song['title']}]({song['webpage_url']})", color=0x1DB954)
        view = MusicButtonView(self, interaction)

        if not vc.is_playing() and not vc.is_paused():
            await self.play_next(interaction)

        await interaction.followup.send(embed=embed, view=view)

    @commands.slash_command(name="fila", description="Mostra a fila de reprodução")
    async def fila(self, interaction: Interaction):
        queue = self.queues.get(interaction.guild.id, [])
        if not queue:
            await interaction.response.send_message("A fila está vazia.")
            return

        embed = Embed(title="📜 Fila de músicas", color=0x1DB954)
        for i, song in enumerate(queue, start=1):
            embed.add_field(name=f"{i}.", value=f"[{song['title']}]({song['webpage_url']})", inline=False)
        await interaction.response.send_message(embed=embed)

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
