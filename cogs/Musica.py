import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, Embed, ui
import yt_dlp
import asyncio
import requests
import base64
import random
import os

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

class MusicView(ui.View):
    def __init__(self, bot, interaction, musica_cog):
        super().__init__(timeout=None)
        self.bot = bot
        self.interaction = interaction
        self.musica_cog = musica_cog

    @ui.button(emoji="⏪", style=nextcord.ButtonStyle.secondary)
    async def back(self, button: ui.Button, interaction: Interaction):
        await self.musica_cog.previous(interaction)

    @ui.button(emoji="⏸", style=nextcord.ButtonStyle.secondary)
    async def pause_resume(self, button: ui.Button, interaction: Interaction):
        await self.musica_cog.toggle_pause(interaction)

    @ui.button(emoji="⏭", style=nextcord.ButtonStyle.secondary)
    async def skip(self, button: ui.Button, interaction: Interaction):
        await self.musica_cog.skip(interaction)

    @ui.button(emoji="🔁", style=nextcord.ButtonStyle.secondary)
    async def loop(self, button: ui.Button, interaction: Interaction):
        await self.musica_cog.toggle_loop(interaction)

    @ui.button(emoji="🔀", style=nextcord.ButtonStyle.secondary)
    async def shuffle(self, button: ui.Button, interaction: Interaction):
        await self.musica_cog.shuffle(interaction)

    @ui.button(emoji="⏹", style=nextcord.ButtonStyle.danger)
    async def stop(self, button: ui.Button, interaction: Interaction):
        await self.musica_cog.stop(interaction)

class Musica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}
        self.voice_clients = {}
        self.is_playing = {}
        self.current_song = {}
        self.looping = {}

    def search_yt(self, item):
        ydl_opts = {
            'format': 'bestaudio[ext=webm]/bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch5',
            'cookiefile': 'cookies.txt',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(item, download=False)
                entries = info['entries'] if 'entries' in info else [info]

                for video in entries:
                    if not video.get('is_live', False) and not video.get('was_live', False):
                        if 'url' in video:
                            return {
                                'source': video['url'],
                                'title': video['title'],
                                'duration': video.get('duration', 0),
                                'webpage_url': video['webpage_url']
                            }
                return None
            except Exception as e:
                print(f"[YT-DLP ERROR] {e}")
                return None

    def get_spotify_tracks(self, url):
        try:
            token_url = "https://accounts.spotify.com/api/token"
            credentials = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {
                "Authorization": f"Basic {b64_credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {"grant_type": "client_credentials"}
            response = requests.post(token_url, headers=headers, data=data)
            access_token = response.json()["access_token"]

            headers = {"Authorization": f"Bearer {access_token}"}

            if "track/" in url:
                track_id = url.split("track/")[1].split("?")[0]
                track_url = f"https://api.spotify.com/v1/tracks/{track_id}"
                track_info = requests.get(track_url, headers=headers).json()
                name = track_info["name"]
                artists = ", ".join(artist["name"] for artist in track_info["artists"])
                return [f"{name} {artists}"]

            elif "playlist/" in url:
                playlist_id = url.split("playlist/")[1].split("?")[0]
                playlist_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
                response = requests.get(playlist_url, headers=headers).json()
                return [f"{item['track']['name']} {', '.join(artist['name'] for artist in item['track']['artists'])}" for item in response['items'] if item['track']]

        except Exception as e:
            print(f"[SPOTIFY ERROR] {e}")
            return []

    async def play_music(self, interaction: Interaction):
        guild_id = interaction.guild.id
        if guild_id in self.queue and self.queue[guild_id]:
            song = self.queue[guild_id][0] if self.looping.get(guild_id) else self.queue[guild_id].pop(0)
            self.current_song[guild_id] = song
            self.is_playing[guild_id] = True
            vc = self.voice_clients[guild_id]

            vc.play(nextcord.PCMVolumeTransformer(nextcord.FFmpegPCMAudio(song['source'])),
                    after=lambda e: asyncio.run_coroutine_threadsafe(self.play_music(interaction), self.bot.loop))

            embed = Embed(title="🎶 MUSIC PANEL", color=0x7289DA)
            embed.add_field(name="📌 Música", value=f"[{song['title']}]({song['webpage_url']})", inline=False)
            embed.add_field(name="⏱ Duração", value=f"{song['duration'] // 60}m {song['duration'] % 60}s", inline=True)
            embed.add_field(name="🎧 Requisitado por", value=interaction.user.mention, inline=True)
            await interaction.followup.send(embed=embed, view=MusicView(self.bot, interaction, self))
        else:
            self.is_playing[guild_id] = False
            await interaction.followup.send("🎶 A fila acabou!")

    @nextcord.slash_command(name="play", description="Toca uma música (YouTube ou Spotify)")
    async def play(self, interaction: Interaction, query: str = SlashOption(description="Link ou nome da música")):
        await interaction.response.defer()
        guild_id = interaction.guild.id
        if not interaction.user.voice:
            await interaction.followup.send("Você precisa estar em um canal de voz!", ephemeral=True)
            return

        tracks = []
        if "open.spotify.com/" in query:
            tracks = self.get_spotify_tracks(query)
            if not tracks:
                await interaction.followup.send("Erro ao buscar no Spotify.", ephemeral=True)
                return
        else:
            tracks = [query]

        added = []
        for q in tracks:
            song = self.search_yt(q)
            if song:
                self.queue.setdefault(guild_id, []).append(song)
                added.append(song['title'])

        if not added:
            await interaction.followup.send("Nenhuma música válida encontrada!", ephemeral=True)
            return

        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            channel = interaction.user.voice.channel
            vc = await channel.connect()
            self.voice_clients[guild_id] = vc
            await self.play_music(interaction)
        elif not self.is_playing.get(guild_id, False):
            await self.play_music(interaction)
        else:
            await interaction.followup.send(f"Adicionadas: **{', '.join(added)}** à fila!")

    async def toggle_pause(self, interaction: Interaction):
        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("⏸ Música pausada.", ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("▶ Música retomada.", ephemeral=True)

    async def skip(self, interaction: Interaction):
        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭ Pulando música...", ephemeral=True)

    async def previous(self, interaction: Interaction):
        await interaction.response.send_message("🔙 Voltar ainda não implementado.", ephemeral=True)

    async def toggle_loop(self, interaction: Interaction):
        guild_id = interaction.guild.id
        self.looping[guild_id] = not self.looping.get(guild_id, False)
        estado = "ativado" if self.looping[guild_id] else "desativado"
        await interaction.response.send_message(f"🔁 Loop {estado}.", ephemeral=True)

    async def shuffle(self, interaction: Interaction):
        guild_id = interaction.guild.id
        if guild_id in self.queue and len(self.queue[guild_id]) > 1:
            random.shuffle(self.queue[guild_id])
            await interaction.response.send_message("🔀 Fila embaralhada!", ephemeral=True)
        else:
            await interaction.response.send_message("Fila vazia ou com apenas uma música.", ephemeral=True)

    async def stop(self, interaction: Interaction):
        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)
        if vc:
            vc.stop()
            await vc.disconnect()
        self.queue[guild_id] = []
        self.is_playing[guild_id] = False
        await interaction.response.send_message("⏹ Música parada e desconectado.", ephemeral=True)

def setup(bot):
    bot.add_cog(Musica(bot))
