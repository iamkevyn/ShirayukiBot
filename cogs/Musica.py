import os
import asyncio
import datetime
import random
import nextcord
from nextcord import Interaction, Embed, ButtonStyle, SlashOption
from nextcord.ui import View, Button
from nextcord.ext import commands, tasks
import wavelink
from wavelink.ext import spotify
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import traceback
import re

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
        player = self.cog.get_player(interaction.guild)
        if not player:
            await interaction.response.send_message("❌ Não estou conectado a um canal de voz!", ephemeral=True)
            return
            
        if player.is_playing():
            await player.pause()
            await interaction.response.send_message("⏸️ Música pausada", ephemeral=True)
        else:
            await player.resume()
            await interaction.response.send_message("▶️ Música resumida", ephemeral=True)

    @nextcord.ui.button(emoji="⏭️", style=ButtonStyle.blurple)
    async def skip(self, button, interaction: Interaction):
        player = self.cog.get_player(interaction.guild)
        if not player or not player.is_playing():
            await interaction.response.send_message("❌ Não estou tocando nada no momento!", ephemeral=True)
            return
            
        await player.stop()
        await interaction.response.send_message("⏭️ Pulando para a próxima música...")

    @nextcord.ui.button(emoji="🔀", style=ButtonStyle.gray)
    async def shuffle(self, button, interaction: Interaction):
        guild_id = interaction.guild.id
        queue = self.cog.queues.get(guild_id, [])
        if not queue:
            await interaction.response.send_message("❌ A fila está vazia!", ephemeral=True)
            return
            
        random.shuffle(queue)
        self.cog.queues[guild_id] = queue
        await interaction.response.send_message("🔀 Fila embaralhada!")

    @nextcord.ui.button(emoji="⏹️", style=ButtonStyle.red)
    async def stop(self, button, interaction: Interaction):
        player = self.cog.get_player(interaction.guild)
        if not player:
            await interaction.response.send_message("❌ Não estou conectado a um canal de voz!", ephemeral=True)
            return
            
        guild_id = interaction.guild.id
        self.cog.queues[guild_id] = []
        self.cog.now_playing.pop(guild_id, None)
        await player.disconnect()
        await interaction.response.send_message("⏹️ Reprodução interrompida e fila limpa.")

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
        
    def get_player(self, guild):
        return wavelink.NodePool.get_node().get_player(guild.id)
        
    async def extract_spotify(self, query):
        """Extrai informações do Spotify e retorna termos de busca"""
        faixas = []
        
        # Verificar se é um link do Spotify
        spotify_pattern = r'https?://open\.spotify\.com/(?P<type>track|playlist|album)/(?P<id>[a-zA-Z0-9]+)'
        match = re.match(spotify_pattern, query)
        
        if not match:
            return [query]  # Não é um link do Spotify
            
        spotify_type = match.group('type')
        spotify_id = match.group('id')
        
        try:
            if spotify_type == 'track':
                # Usar a biblioteca wavelink.ext.spotify para buscar
                decoded = await spotify.SpotifyTrack.search(query=query)
                if decoded:
                    return [decoded[0]]
                    
            elif spotify_type == 'playlist' or spotify_type == 'album':
                # Usar a biblioteca wavelink.ext.spotify para buscar
                decoded = await spotify.SpotifyTrack.search(query=query)
                if decoded:
                    return decoded[:25]  # Limitar a 25 faixas para evitar sobrecarga
        except Exception as e:
            print(f"Erro ao decodificar link do Spotify com wavelink: {e}")
            traceback.print_exc()
            
            # Fallback: usar a biblioteca spotipy se disponível
            if sp:
                try:
                    if spotify_type == 'track':
                        track = sp.track(spotify_id)
                        track_name = track['name']
                        artist_name = track['artists'][0]['name']
                        faixas.append(f"{track_name} {artist_name}")
                    elif spotify_type == 'playlist':
                        items = sp.playlist_items(spotify_id, limit=25)['items']
                        for item in items:
                            if item.get('track') and item['track'].get('name') and item['track'].get('artists'):
                                track_name = item['track']['name']
                                artist_name = item['track']['artists'][0]['name']
                                faixas.append(f"{track_name} {artist_name}")
                    elif spotify_type == 'album':
                        items = sp.album_tracks(spotify_id, limit=25)['items']
                        for item in items:
                            if item.get('name') and item.get('artists'):
                                track_name = item['name']
                                artist_name = item['artists'][0]['name']
                                faixas.append(f"{track_name} {artist_name}")
                                
                    return faixas if faixas else [query]
                except Exception as e2:
                    print(f"Erro ao extrair do Spotify com spotipy: {e2}")
                    traceback.print_exc()
                    
        return [query]  # Retorna a consulta original se tudo falhar

    async def play_next(self, interaction):
        guild_id = interaction.guild.id
        player = self.get_player(interaction.guild)
        
        if not player or not player.is_connected:
            return
            
        if not self.queues.get(guild_id) or len(self.queues[guild_id]) == 0:
            self.now_playing.pop(guild_id, None)
            await player.disconnect()
            return
            
        track = self.queues[guild_id].pop(0)
        self.now_playing[guild_id] = track
        
        try:
            # Tocar a faixa
            await player.play(track)
            
            # Criar embed para a música atual
            if isinstance(track, wavelink.YouTubeTrack):
                embed = Embed(
                    title="🎧 Tocando agora", 
                    description=f"[{track.title}]({track.uri})", 
                    color=0x1DB954
                )
                embed.set_thumbnail(url=track.thumbnail)
                embed.add_field(name="Duração", value=self.format_duration(track.duration))
                
            elif isinstance(track, spotify.SpotifyTrack):
                embed = Embed(
                    title="🎧 Tocando agora (Spotify)", 
                    description=f"[{track.title}](https://open.spotify.com/track/{track.id})", 
                    color=0x1DB954
                )
                if track.images:
                    embed.set_thumbnail(url=track.images[0])
                embed.add_field(name="Artista", value=track.author)
                embed.add_field(name="Duração", value=self.format_duration(track.duration))
                
            else:
                embed = Embed(
                    title="🎧 Tocando agora", 
                    description=f"{track.title}", 
                    color=0x1DB954
                )
                
            await interaction.channel.send(embed=embed, view=MusicControlView(self))
            
        except Exception as e:
            print(f"Erro ao iniciar reprodução: {e}")
            traceback.print_exc()
            await interaction.channel.send(f"❌ Erro ao reproduzir: {str(e)[:100]}...", delete_after=10)
            
            # Tentar a próxima música
            if self.queues.get(guild_id) and len(self.queues[guild_id]) > 0:
                await self.play_next(interaction)

    def format_duration(self, duration_ms):
        """Formata a duração em milissegundos para formato legível"""
        seconds = int(duration_ms / 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @nextcord.slash_command(name="tocar", description="Toque uma música ou playlist do YouTube/Spotify.")
    async def tocar(self, interaction: Interaction, query: str = SlashOption(description="Link ou nome da música")):
        # Verificar se o usuário está em um canal de voz
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Você precisa estar em um canal de voz!", ephemeral=True)
            return
            
        # Adiar a resposta para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        # Obter ou criar player
        player = self.get_player(interaction.guild)
        
        # Conectar ao canal de voz se ainda não estiver conectado
        if not player or not player.is_connected:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
                self.queues[interaction.guild.id] = []
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao conectar ao canal de voz: {str(e)}", ephemeral=True)
                return

        # Informar ao usuário que estamos buscando (apenas para ele)
        await interaction.followup.send(f"🔍 Buscando: `{query}`...", ephemeral=True)
        
        # Processar links do Spotify ou buscar diretamente
        tracks_to_add = []
        
        try:
            # Verificar se é um link do Spotify e extrair
            if "spotify.com" in query:
                tracks = await self.extract_spotify(query)
                
                # Se retornou uma lista de strings, buscar cada uma no YouTube
                if tracks and isinstance(tracks[0], str):
                    for track_query in tracks:
                        search_result = await wavelink.YouTubeTrack.search(track_query)
                        if search_result:
                            tracks_to_add.append(search_result[0])
                            
                # Se retornou SpotifyTrack diretamente
                elif tracks and isinstance(tracks[0], spotify.SpotifyTrack):
                    tracks_to_add.extend(tracks)
                    
            # Link ou busca do YouTube
            elif "youtube.com" in query or "youtu.be" in query:
                tracks = await wavelink.YouTubeTrack.search(query)
                if tracks:
                    # Se for uma playlist, adicionar várias faixas
                    if "&list=" in query or "playlist" in query:
                        tracks_to_add.extend(tracks[:25])  # Limitar a 25 faixas
                    else:
                        tracks_to_add.append(tracks[0])
            else:
                # Busca normal
                tracks = await wavelink.YouTubeTrack.search(query)
                if tracks:
                    tracks_to_add.append(tracks[0])
        except Exception as e:
            print(f"Erro ao buscar música: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Erro ao buscar música: {str(e)[:100]}...", ephemeral=True)
            return
            
        # Verificar se encontrou alguma música
        if not tracks_to_add:
            await interaction.followup.send("❌ Não foi possível encontrar nenhuma música com essa busca.", ephemeral=True)
            return
            
        # Adicionar músicas à fila
        guild_id = interaction.guild.id
        for track in tracks_to_add:
            self.queues.setdefault(guild_id, []).append(track)
            
            # Enviar mensagem de sucesso (visível para todos)
            if track == tracks_to_add[0]:  # Apenas para a primeira música
                await interaction.channel.send(f"✅ **{interaction.user.display_name}** adicionou à fila: `{track.title}`")
                
        # Informar quantas músicas foram adicionadas se for mais de uma
        if len(tracks_to_add) > 1:
            await interaction.followup.send(f"✅ Adicionadas {len(tracks_to_add)} músicas à fila!", ephemeral=True)
            
        # Iniciar reprodução se não estiver tocando nada
        if not player.is_playing():
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
            
            # Adicionar informações da música atual
            if isinstance(current, wavelink.YouTubeTrack):
                embed.add_field(
                    name="🎧 Tocando agora:", 
                    value=f"[{current.title}]({current.uri})", 
                    inline=False
                )
                if current.thumbnail:
                    embed.set_thumbnail(url=current.thumbnail)
                    
            elif isinstance(current, spotify.SpotifyTrack):
                embed.add_field(
                    name="🎧 Tocando agora (Spotify):", 
                    value=f"{current.title} - {current.author}", 
                    inline=False
                )
                if current.images:
                    embed.set_thumbnail(url=current.images[0])
            else:
                embed.add_field(
                    name="🎧 Tocando agora:", 
                    value=current.title, 
                    inline=False
                )
            
            # Adicionar as próximas músicas
            if fila:
                for i, track in enumerate(fila[:5], start=1):
                    if isinstance(track, (wavelink.YouTubeTrack, spotify.SpotifyTrack)):
                        embed.add_field(
                            name=f"{i}.", 
                            value=f"{track.title} ({self.format_duration(track.duration)})", 
                            inline=False
                        )
                    else:
                        embed.add_field(name=f"{i}.", value=track.title, inline=False)
                
                if len(fila) > 5:
                    embed.set_footer(text=f"+ {len(fila) - 5} músicas na fila")
            
            embeds.append(embed)
            
            # Criar páginas adicionais se houver muitas músicas
            if len(fila) > 5:
                for i in range(5, len(fila), 5):
                    embed = Embed(title="📜 Continuação da Fila", color=0x1DB954)
                    for j, track in enumerate(fila[i:i+5], start=i+1):
                        if isinstance(track, (wavelink.YouTubeTrack, spotify.SpotifyTrack)):
                            embed.add_field(
                                name=f"{j}.", 
                                value=f"{track.title} ({self.format_duration(track.duration)})", 
                                inline=False
                            )
                        else:
                            embed.add_field(name=f"{j}.", value=track.title, inline=False)
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
        player = self.get_player(interaction.guild)
        if not player or not player.is_connected:
            await interaction.response.send_message("❌ Não estou conectado a um canal de voz!", ephemeral=True)
            return
            
        if not player.is_playing():
            await interaction.response.send_message("❌ Não estou tocando nada no momento!", ephemeral=True)
            return
            
        await player.stop()
        await interaction.response.send_message("⏭️ Pulando para a próxima música...")

    @nextcord.slash_command(name="parar", description="Para a reprodução e limpa a fila.")
    async def parar(self, interaction: Interaction):
        player = self.get_player(interaction.guild)
        if not player or not player.is_connected:
            await interaction.response.send_message("❌ Não estou conectado a um canal de voz!", ephemeral=True)
            return
            
        guild_id = interaction.guild.id
        if guild_id in self.queues:
            self.queues[guild_id] = []
            
        self.now_playing.pop(guild_id, None)
        await player.disconnect()
        await interaction.response.send_message("⏹️ Reprodução interrompida e fila limpa.")

    @tasks.loop(minutes=1)
    async def autoleave(self):
        for guild in self.bot.guilds:
            player = self.get_player(guild)
            if player and player.is_connected:
                if not player.is_playing():
                    guild_id = guild.id
                    if not hasattr(player, "idle_since"):
                        player.idle_since = datetime.datetime.utcnow()
                    elif (datetime.datetime.utcnow() - player.idle_since).seconds > 300:  # 5 minutos
                        self.now_playing.pop(guild_id, None)
                        self.queues.pop(guild_id, None)
                        await player.disconnect()
                elif hasattr(player, "idle_since"):
                    del player.idle_since

    @autoleave.before_loop
    async def before_autoleave(self):
        await self.bot.wait_until_ready()

    # Eventos do Wavelink
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player, track, reason):
        if reason == "FINISHED" and player.guild:
            interaction = player._last_interaction
            if interaction:
                await self.play_next(interaction)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, player, track, error):
        if player.guild:
            channel = player.guild.text_channels[0]  # Canal padrão
            await channel.send(f"❌ Erro ao reproduzir a música: {error}")
            
            interaction = player._last_interaction
            if interaction:
                await self.play_next(interaction)

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, player, track, threshold):
        if player.guild:
            channel = player.guild.text_channels[0]  # Canal padrão
            await channel.send("⚠️ A música travou. Pulando para a próxima...")
            
            interaction = player._last_interaction
            if interaction:
                await self.play_next(interaction)

def setup(bot):
    bot.add_cog(Musica(bot))
