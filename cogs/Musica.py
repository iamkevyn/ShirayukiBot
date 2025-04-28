import os
import asyncio
import datetime
import random
import nextcord
from nextcord import Interaction, Embed, ButtonStyle, SlashOption
from nextcord.ui import View, Button
from nextcord.ext import commands, tasks
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Configurações do yt_dlp com opções alternativas para contornar bloqueios
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "cookiefile": "cookies.txt",
    "default_search": "ytsearch",
    "noplaylist": False,
    "source_address": "0.0.0.0",
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "no_warnings": True,
    "geo_bypass": True,
    "geo_bypass_country": "BR",
    "extractor_retries": 5,
    "extractor_args": {
        "youtube": {
            "skip": ["dash", "hls"],
            "player_client": ["android", "web"]
        }
    },
    "socket_timeout": 20,
    "retry_sleep_functions": {"http": lambda x: 5},
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192"
    }]
}

# Configuração alternativa para tentar quando a principal falhar
YDL_OPTIONS_FALLBACK = {
    "format": "bestaudio/best",
    "quiet": True,
    "default_search": "ytsearch",
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "no_warnings": True,
    "socket_timeout": 30,
    "extractor_retries": 10,
    "external_downloader": "aria2c",
    "external_downloader_args": ["--min-split-size=1M", "--max-connection-per-server=16"]
}

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Inicializar o cliente Spotify apenas se as credenciais estiverem disponíveis
sp = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
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

        # Criar botões com callbacks conectados
        prev_button = Button(label="⬅️", style=ButtonStyle.gray, custom_id="prev")
        prev_button.callback = self.button_callback
        self.add_item(prev_button)
        
        next_button = Button(label="➡️", style=ButtonStyle.gray, custom_id="next")
        next_button.callback = self.button_callback
        self.add_item(next_button)

    async def button_callback(self, interaction: Interaction):
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
        try:
            # Tenta com as opções principais
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(query, download=False))
            if "entries" in data:
                return [{"title": e["title"], "url": e["url"], "webpage_url": e["webpage_url"]} for e in data["entries"]]
            return [{"title": data["title"], "url": data["url"], "webpage_url": data["webpage_url"]}]
        except Exception as e:
            print(f"Erro ao buscar música com opções principais: {e}")
            try:
                # Tenta com as opções de fallback
                print("Tentando com opções alternativas...")
                data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS_FALLBACK).extract_info(query, download=False))
                if "entries" in data:
                    return [{"title": e["title"], "url": e["url"], "webpage_url": e["webpage_url"]} for e in data["entries"]]
                return [{"title": data["title"], "url": data["url"], "webpage_url": data["webpage_url"]}]
            except Exception as e2:
                print(f"Erro ao buscar música com opções alternativas: {e2}")
                # Se for um link do YouTube, tenta usar um serviço alternativo
                if "youtube.com" in query or "youtu.be" in query:
                    try:
                        # Extrai o ID do vídeo
                        video_id = None
                        if "youtube.com/watch?v=" in query:
                            video_id = query.split("youtube.com/watch?v=")[1].split("&")[0]
                        elif "youtu.be/" in query:
                            video_id = query.split("youtu.be/")[1].split("?")[0]
                        
                        if video_id:
                            # Usa um serviço alternativo (exemplo fictício)
                            title = f"Música do YouTube (ID: {video_id})"
                            return [{"title": title, "url": query, "webpage_url": query}]
                    except Exception as e3:
                        print(f"Erro ao processar link do YouTube: {e3}")
                return []

    async def prepare_audio(self, url):
        loop = asyncio.get_event_loop()
        try:
            # Tenta com as opções principais
            info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False))
            return nextcord.FFmpegPCMAudio(info["url"])
        except Exception as e:
            print(f"Erro ao preparar áudio com opções principais: {e}")
            try:
                # Tenta com as opções de fallback
                print("Tentando preparar áudio com opções alternativas...")
                info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS_FALLBACK).extract_info(url, download=False))
                return nextcord.FFmpegPCMAudio(info["url"])
            except Exception as e2:
                print(f"Erro ao preparar áudio com opções alternativas: {e2}")
                return None

    def extract_spotify(self, link):
        faixas = []
        if not sp:
            print("Credenciais do Spotify não configuradas. Usando link direto.")
            return [link]  # Retorna o link original se o cliente Spotify não estiver disponível
            
        try:
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
        except Exception as e:
            print(f"Erro ao extrair do Spotify: {e}")
            # Tenta extrair o ID da faixa ou playlist para busca manual
            try:
                if "track" in link:
                    track_id = link.split("track/")[1].split("?")[0]
                    return [f"música {track_id}"]
                elif "playlist" in link:
                    return [link]  # Retorna o link original para playlists
            except:
                pass
            return [link]  # Retorna o link original em caso de erro

    async def play_next(self, interaction):
        guild_id = interaction.guild.id
        vc = self.get_voice(interaction.guild)
        if not vc:
            return
            
        if not self.queues.get(guild_id):
            await vc.disconnect()
            return
            
        musica = self.queues[guild_id].pop(0)
        source = await self.prepare_audio(musica["url"])
        if not source:
            await interaction.channel.send("❌ Não foi possível reproduzir esta música. Pulando para a próxima...")
            if self.queues.get(guild_id):
                await self.play_next(interaction)
            return
            
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(interaction), self.bot.loop))
        embed = Embed(title="🎧 Tocando agora", description=f"[{musica['title']}]({musica['webpage_url']})", color=0x1DB954)
        await interaction.channel.send(embed=embed, view=MusicControlView(self))

    @nextcord.slash_command(name="tocar", description="Toque uma música ou playlist do YouTube/Spotify.")
    async def tocar(self, interaction: Interaction, query: str = SlashOption(description="Link ou nome da música")):
        await interaction.response.defer()
        if not interaction.user.voice:
            await interaction.followup.send("Você precisa estar em um canal de voz!")
            return
        vc = self.get_voice(interaction.guild)
        if not vc:
            try:
                vc = await interaction.user.voice.channel.connect()
                self.queues[interaction.guild.id] = []
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao conectar ao canal de voz: {str(e)}")
                return

        await interaction.followup.send(f"🔍 Buscando: `{query}`...")
        
        termos = self.extract_spotify(query) if "spotify" in query else [query]
        musicas_adicionadas = 0
        
        for termo in termos:
            resultados = await self.yt_search(termo)
            if resultados:
                self.queues[interaction.guild.id].append(resultados[0])
                musicas_adicionadas += 1
                await interaction.followup.send(f"✅ Adicionado à fila: `{resultados[0]['title']}`")

        if musicas_adicionadas == 0:
            await interaction.followup.send("❌ Não foi possível encontrar nenhuma música com essa busca.")
            return
            
        if not vc.is_playing():
            await interaction.followup.send("▶️ Iniciando reprodução...")
            await self.play_next(interaction)
        else:
            await interaction.followup.send(f"🎶 {musicas_adicionadas} música(s) adicionada(s) à fila!")

    @nextcord.slash_command(name="fila", description="Mostra a fila de músicas.")
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
