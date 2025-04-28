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
import traceback
import urllib.request
import json

# Configurações do yt_dlp para busca (sem download)
YDL_OPTIONS_SEARCH = {
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
    "extractor_retries": 3,
    "socket_timeout": 15
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
        vc = self.get_voice(interaction.guild)
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
        self.now_playing = {}
        self.autoleave.start()

    def get_voice(self, guild):
        return nextcord.utils.get(self.bot.voice_clients, guild=guild)

    async def yt_search(self, query):
        loop = asyncio.get_event_loop()
        try:
            # Tenta com as opções de busca
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS_SEARCH).extract_info(query, download=False))
            if "entries" in data and data["entries"]:
                return [{"title": e.get("title", "Música sem título"), "url": e.get("webpage_url", ""), "webpage_url": e.get("webpage_url", "")} for e in data["entries"] if e and "webpage_url" in e]
            if data and "webpage_url" in data:
                return [{"title": data.get("title", "Música sem título"), "url": data.get("webpage_url", ""), "webpage_url": data.get("webpage_url", "")}]
            return []
        except Exception as e:
            print(f"Erro ao buscar música: {e}")
            traceback.print_exc()
            
            # Tenta uma abordagem alternativa para YouTube
            if "youtube.com" in query or "youtu.be" in query:
                try:
                    # Extrai o ID do vídeo
                    video_id = None
                    if "youtube.com/watch?v=" in query:
                        video_id = query.split("youtube.com/watch?v=")[1].split("&")[0]
                    elif "youtu.be/" in query:
                        video_id = query.split("youtu.be/")[1].split("?")[0]
                    
                    if video_id:
                        # Tenta obter informações básicas
                        title = f"Música do YouTube (ID: {video_id})"
                        return [{"title": title, "url": query, "webpage_url": query}]
                except Exception as e2:
                    print(f"Erro ao processar link do YouTube: {e2}")
            
            return []

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
                limit = 50  # Limite máximo por requisição
                total_tracks = 0
                
                # Primeira requisição para obter o total
                playlist_info = sp.playlist_items(link, limit=1, offset=0)
                if "total" in playlist_info:
                    total_tracks = min(playlist_info["total"], 50)  # Limitar a 50 faixas para evitar sobrecarga
                
                while offset < total_tracks:
                    items = sp.playlist_items(link, limit=limit, offset=offset)["items"]
                    if not items:
                        break
                    for item in items:
                        if item.get("track") and item["track"].get("name") and item["track"].get("artists"):
                            track_name = item["track"]["name"]
                            artist_name = item["track"]["artists"][0]["name"]
                            faixas.append(f"{track_name} {artist_name}")
                    offset += len(items)
                    
                print(f"Extraídas {len(faixas)} faixas da playlist Spotify")
            return faixas if faixas else [link]
        except Exception as e:
            print(f"Erro ao extrair do Spotify: {e}")
            traceback.print_exc()
            return [link]  # Retorna o link original em caso de erro

    async def play_next(self, interaction):
        guild_id = interaction.guild.id
        vc = self.get_voice(interaction.guild)
        if not vc:
            return
                
        if not self.queues.get(guild_id) or len(self.queues[guild_id]) == 0:
            self.now_playing.pop(guild_id, None)
            await vc.disconnect()
            return
            
        musica = self.queues[guild_id].pop(0)
        self.now_playing[guild_id] = musica
        
        try:
            # Obter URL de áudio diretamente do YouTube
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS_SEARCH).extract_info(musica["url"], download=False))
            
            if not info or "url" not in info:
                await interaction.channel.send("❌ Não foi possível obter o áudio desta música. Pulando para a próxima...", delete_after=10)
                if self.queues.get(guild_id) and len(self.queues[guild_id]) > 0:
                    await self.play_next(interaction)
                return
            
            # Usar o URL de áudio diretamente
            audio_url = info["url"]
            source = nextcord.FFmpegPCMAudio(audio_url)
            
            # Definir um callback seguro para quando a música terminar
            def after_playing(error):
                if error:
                    print(f"Erro durante a reprodução: {error}")
                # Usar create_task para evitar problemas com o loop de eventos
                asyncio.run_coroutine_threadsafe(self.play_next(interaction), self.bot.loop)
            
            vc.play(source, after=after_playing)
            
            embed = Embed(title="🎧 Tocando agora", description=f"[{musica['title']}]({musica['webpage_url']})", color=0x1DB954)
            await interaction.channel.send(embed=embed, view=MusicControlView(self))
        except Exception as e:
            print(f"Erro ao iniciar reprodução: {e}")
            traceback.print_exc()
            
            # Tentar método alternativo sem FFmpeg
            try:
                print("Tentando método alternativo de reprodução...")
                # Usar o URL diretamente sem FFmpeg
                if "url" in info:
                    source = nextcord.PCMVolumeTransformer(nextcord.FFmpegPCMAudio(info["url"]))
                    
                    def after_playing_alt(error):
                        if error:
                            print(f"Erro durante a reprodução alternativa: {error}")
                        asyncio.run_coroutine_threadsafe(self.play_next(interaction), self.bot.loop)
                    
                    vc.play(source, after=after_playing_alt)
                    
                    embed = Embed(title="🎧 Tocando agora (método alternativo)", description=f"[{musica['title']}]({musica['webpage_url']})", color=0x1DB954)
                    await interaction.channel.send(embed=embed, view=MusicControlView(self))
                    return
            except Exception as e2:
                print(f"Erro no método alternativo: {e2}")
                traceback.print_exc()
            
            await interaction.channel.send(f"❌ Erro ao reproduzir: {str(e)[:100]}...", delete_after=10)
            if self.queues.get(guild_id) and len(self.queues[guild_id]) > 0:
                await self.play_next(interaction)

    @nextcord.slash_command(name="tocar", description="Toque uma música ou playlist do YouTube/Spotify.")
    async def tocar(self, interaction: Interaction, query: str = SlashOption(description="Link ou nome da música")):
        # Verificar se o usuário está em um canal de voz
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Você precisa estar em um canal de voz!", ephemeral=True)
            return
            
        # Adiar a resposta para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        # Conectar ao canal de voz se ainda não estiver conectado
        vc = self.get_voice(interaction.guild)
        if not vc:
            try:
                vc = await interaction.user.voice.channel.connect()
                self.queues[interaction.guild.id] = []
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao conectar ao canal de voz: {str(e)}", ephemeral=True)
                return

        # Informar ao usuário que estamos buscando (apenas para ele)
        await interaction.followup.send(f"🔍 Buscando: `{query}`...", ephemeral=True)
        
        # Processar links do Spotify ou buscar diretamente
        termos = self.extract_spotify(query) if "spotify" in query else [query]
        musicas_adicionadas = 0
        
        # Buscar e adicionar músicas à fila
        for termo in termos:
            resultados = await self.yt_search(termo)
            if resultados:
                self.queues.setdefault(interaction.guild.id, []).append(resultados[0])
                musicas_adicionadas += 1
                
                # Enviar mensagem de sucesso (visível para todos)
                await interaction.channel.send(f"✅ **{interaction.user.display_name}** adicionou à fila: `{resultados[0]['title']}`")

        # Informar se nenhuma música foi encontrada (apenas para o usuário)
        if musicas_adicionadas == 0:
            await interaction.followup.send("❌ Não foi possível encontrar nenhuma música com essa busca.", ephemeral=True)
            return
            
        # Iniciar reprodução se não estiver tocando nada
        if not vc.is_playing() and not vc.is_paused():
            await interaction.followup.send("▶️ Iniciando reprodução...", ephemeral=True)
            await self.play_next(interaction)

    @nextcord.slash_command(name="fila", description="Mostra a fila de músicas.")
    async def fila(self, interaction: Interaction):
        guild_id = interaction.guild.id
        fila = self.queues.get(guild_id, [])
        
        # Verificar se há algo tocando ou na fila
        if not fila and not self.now_playing.get(guild_id):
            await interaction.response.send_message("📭 A fila está vazia.", ephemeral=True)
            return

        # Criar embed para a música atual
        embeds = []
        if self.now_playing.get(guild_id):
            current = self.now_playing[guild_id]
            embed = Embed(title="🎵 Fila de Reprodução", color=0x1DB954)
            embed.add_field(name="🎧 Tocando agora:", value=f"[{current['title']}]({current['webpage_url']})", inline=False)
            
            # Adicionar as próximas músicas
            if fila:
                for i, musica in enumerate(fila[:5], start=1):
                    embed.add_field(name=f"{i}.", value=f"[{musica['title']}]({musica['webpage_url']})", inline=False)
                
                if len(fila) > 5:
                    embed.set_footer(text=f"+ {len(fila) - 5} músicas na fila")
            
            embeds.append(embed)
            
            # Criar páginas adicionais se houver muitas músicas
            if len(fila) > 5:
                for i in range(5, len(fila), 5):
                    embed = Embed(title="📜 Continuação da Fila", color=0x1DB954)
                    for j, musica in enumerate(fila[i:i+5], start=i+1):
                        embed.add_field(name=f"{j}.", value=f"[{musica['title']}]({musica['webpage_url']})", inline=False)
                    embeds.append(embed)
        
        # Enviar a fila
        if embeds:
            if len(embeds) > 1:
                await interaction.response.send_message(embed=embeds[0], view=QueuePaginatorView(embeds))
            else:
                await interaction.response.send_message(embed=embeds[0])
        else:
            await interaction.response.send_message("📭 A fila está vazia.", ephemeral=True)

    @nextcord.slash_command(name="pular", description="Pula para a próxima música na fila.")
    async def pular(self, interaction: Interaction):
        vc = self.get_voice(interaction.guild)
        if not vc:
            await interaction.response.send_message("❌ Não estou conectado a um canal de voz!", ephemeral=True)
            return
            
        if not vc.is_playing() and not vc.is_paused():
            await interaction.response.send_message("❌ Não estou tocando nada no momento!", ephemeral=True)
            return
            
        vc.stop()
        await interaction.response.send_message("⏭️ Pulando para a próxima música...")

    @nextcord.slash_command(name="parar", description="Para a reprodução e limpa a fila.")
    async def parar(self, interaction: Interaction):
        vc = self.get_voice(interaction.guild)
        if not vc:
            await interaction.response.send_message("❌ Não estou conectado a um canal de voz!", ephemeral=True)
            return
            
        if interaction.guild.id in self.queues:
            self.queues[interaction.guild.id] = []
            
        self.now_playing.pop(interaction.guild.id, None)
        await vc.disconnect()
        await interaction.response.send_message("⏹️ Reprodução interrompida e fila limpa.")

    @tasks.loop(minutes=1)
    async def autoleave(self):
        for vc in self.bot.voice_clients:
            if not vc.is_playing() and not vc.is_paused():
                guild_id = vc.guild.id
                if not hasattr(vc, "idle_since"):
                    vc.idle_since = datetime.datetime.utcnow()
                elif (datetime.datetime.utcnow() - vc.idle_since).seconds > 300:  # 5 minutos
                    self.now_playing.pop(guild_id, None)
                    self.queues.pop(guild_id, None)
                    await vc.disconnect()
            elif hasattr(vc, "idle_since"):
                del vc.idle_since

def setup(bot):
    bot.add_cog(Musica(bot))
