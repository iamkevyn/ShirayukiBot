# /home/ubuntu/ShirayukiBot/cogs/Musica.py
# Cog de música para o bot Shirayuki usando Mafic (Lavalink) com integração Spotify

import asyncio
import datetime
import logging
import re
import time
import os
import json
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlparse, parse_qs

import mafic
import nextcord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from nextcord import Interaction, SlashOption
from nextcord.ext import commands

# Configuração de logging
logger = logging.getLogger("discord_bot.musica_mafic")

# Regex para validar URLs e termos de busca
URL_REGEX = re.compile(r"^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z0-9-]+(/[^/\s]*)*$")
SEARCH_TERM_REGEX = re.compile(r"^.{3,500}$")
SPOTIFY_URL_REGEX = re.compile(r"^(https?://)?(open\.)?spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)")

# Emojis para os controles de música
EMOJIS = {
    "music": "🎵",
    "playlist": "🎶",
    "volume_up": "🔊",
    "volume_down": "🔉",
    "pause": "⏸️",
    "play": "▶️",
    "stop": "⏹️",
    "skip": "⏭️",
    "back": "⏮️",
    "loop": "🔁",
    "shuffle": "🔀",
    "autoplay": "♾️",
    "spotify": "💚"
}

# Classe para cache de resultados do Spotify
class SpotifyCache:
    def __init__(self, max_size=100, expiry_time=3600):  # Cache por 1 hora
        self.cache = {}
        self.max_size = max_size
        self.expiry_time = expiry_time
        
    def get(self, key):
        if key in self.cache:
            item = self.cache[key]
            if time.time() - item["timestamp"] < self.expiry_time:
                return item["data"]
            else:
                # Expirado
                del self.cache[key]
        return None
        
    def set(self, key, data):
        # Se o cache estiver cheio, remova o item mais antigo
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
            
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

class MusicControls(nextcord.ui.View):
    """Controles interativos unificados para o player de música."""
    def __init__(self, player, cog_instance):
        super().__init__(timeout=None)
        self.player = player
        self.cog = cog_instance
        
    @nextcord.ui.button(emoji=EMOJIS["volume_down"], style=nextcord.ButtonStyle.secondary, row=0)
    async def volume_down(self, button: nextcord.ui.Button, interaction: Interaction):
        """Diminui o volume em 10%."""
        current_volume = self.cog.get_player_volume(self.player)
        if current_volume > 0:
            new_volume = max(0, current_volume - 10)
            await self.cog.set_player_volume(self.player, new_volume)
            await interaction.response.send_message(f"{EMOJIS['volume_down']} Volume diminuído para {new_volume}%", ephemeral=True)
            await self.cog.update_now_playing_message(self.player)
        else:
            await interaction.response.send_message("Volume já está no mínimo.", ephemeral=True)
    
    @nextcord.ui.button(emoji=EMOJIS["back"], style=nextcord.ButtonStyle.secondary, row=0)
    async def back(self, button: nextcord.ui.Button, interaction: Interaction):
        """Volta para a música anterior."""
        guild_id = interaction.guild_id
        last_track = self.cog.last_tracks.get(guild_id)
        
        if last_track:
            # Adiciona a música atual de volta à fila (no início)
            if self.player.current:
                queue = self.cog.get_queue(guild_id)
                queue.insert(0, self.player.current)
                
            # Toca a última música
            try:
                await self.player.play(last_track)
                await interaction.response.send_message(f"{EMOJIS['back']} Voltando para a música anterior: **{last_track.title}**", ephemeral=True)
            except Exception as e:
                logger.error(f"Erro ao voltar para música anterior: {e}")
                await interaction.response.send_message(f"Erro ao voltar para música anterior: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("Não há música anterior para voltar.", ephemeral=True)
    
    @nextcord.ui.button(emoji=EMOJIS["pause"], style=nextcord.ButtonStyle.secondary, row=0)
    async def pause(self, button: nextcord.ui.Button, interaction: Interaction):
        """Pausa ou retoma a música atual."""
        if self.player.paused:
            await self.player.resume()
            await interaction.response.send_message(f"{EMOJIS['play']} Música retomada!", ephemeral=True)
        else:
            await self.player.pause()
            await interaction.response.send_message(f"{EMOJIS['pause']} Música pausada!", ephemeral=True)
        
        await self.cog.update_now_playing_message(self.player)
    
    @nextcord.ui.button(emoji=EMOJIS["skip"], style=nextcord.ButtonStyle.secondary, row=0)
    async def skip(self, button: nextcord.ui.Button, interaction: Interaction):
        """Pula para a próxima música."""
        await self.player.stop()  # Mafic lida com a próxima música da fila automaticamente
        await interaction.response.send_message(f"{EMOJIS['skip']} Música pulada!", ephemeral=True)
    
    @nextcord.ui.button(emoji=EMOJIS["volume_up"], style=nextcord.ButtonStyle.secondary, row=0)
    async def volume_up(self, button: nextcord.ui.Button, interaction: Interaction):
        """Aumenta o volume em 10%."""
        current_volume = self.cog.get_player_volume(self.player)
        if current_volume < 100:
            new_volume = min(100, current_volume + 10)
            await self.cog.set_player_volume(self.player, new_volume)
            await interaction.response.send_message(f"{EMOJIS['volume_up']} Volume aumentado para {new_volume}%", ephemeral=True)
            await self.cog.update_now_playing_message(self.player)
        else:
            await interaction.response.send_message("Volume já está no máximo.", ephemeral=True)
    
    @nextcord.ui.button(emoji=EMOJIS["shuffle"], style=nextcord.ButtonStyle.secondary, row=1)
    async def shuffle(self, button: nextcord.ui.Button, interaction: Interaction):
        """Embaralha a fila de músicas."""
        guild_id = interaction.guild_id
        queue = self.cog.get_queue(guild_id)
        
        if len(queue) <= 1:
            await interaction.response.send_message("Não há músicas suficientes na fila para embaralhar.", ephemeral=True)
            return
            
        # Embaralha a fila
        import random
        random.shuffle(queue)
        
        await interaction.response.send_message(f"{EMOJIS['shuffle']} Fila embaralhada! Use `/fila` para ver a nova ordem.", ephemeral=True)
        await self.cog.update_now_playing_message(self.player)
    
    @nextcord.ui.button(emoji=EMOJIS["loop"], style=nextcord.ButtonStyle.secondary, row=1)
    async def loop(self, button: nextcord.ui.Button, interaction: Interaction):
        """Alterna entre os modos de loop (desativado, faixa, fila)."""
        guild_id = interaction.guild_id
        current_state = self.cog.get_loop_state(guild_id)
        
        # Alterna entre os estados: none -> track -> queue -> none
        if current_state == "none":
            new_state = "track"
            message = f"{EMOJIS['loop']} Loop ativado para a faixa atual!"
        elif current_state == "track":
            new_state = "queue"
            message = f"{EMOJIS['loop']} Loop ativado para toda a fila!"
        else:  # queue
            new_state = "none"
            message = f"{EMOJIS['loop']} Loop desativado!"
            
        self.cog.set_loop_state(guild_id, new_state)
        await interaction.response.send_message(message, ephemeral=True)
        await self.cog.update_now_playing_message(self.player)
    
    @nextcord.ui.button(emoji=EMOJIS["stop"], style=nextcord.ButtonStyle.danger, row=1)
    async def stop(self, button: nextcord.ui.Button, interaction: Interaction):
        """Para a reprodução e limpa a fila."""
        guild_id = interaction.guild_id
        
        # Limpa a fila personalizada
        if guild_id in self.cog.queues:
            self.cog.queues[guild_id].clear()
            
        await self.player.stop()  # Para a música atual
        
        try:
            await self.player.disconnect(force=True)  # Desconecta do canal de voz
        except Exception as e:
            logger.error(f"Erro ao desconectar player para guild {guild_id}: {e}")

        # Remove o player da lista
        if guild_id in self.cog.players:
            del self.cog.players[guild_id]
        
        # Limpa o dicionário de requesters
        if guild_id in self.cog.track_requesters:
            del self.cog.track_requesters[guild_id]
        
        # Limpa a fila personalizada
        if guild_id in self.cog.queues:
            del self.cog.queues[guild_id]
            
        # Limpa o estado de loop
        if guild_id in self.cog.loop_states:
            del self.cog.loop_states[guild_id]
            
        # Limpa a última música tocada
        if guild_id in self.cog.last_tracks:
            del self.cog.last_tracks[guild_id]
            
        # Limpa a mensagem de "agora tocando"
        if guild_id in self.cog.now_playing_messages:
            del self.cog.now_playing_messages[guild_id]
            
        await interaction.response.send_message(f"{EMOJIS['stop']} Reprodução parada e fila limpa!", ephemeral=True)
    
    @nextcord.ui.button(emoji=EMOJIS["playlist"], style=nextcord.ButtonStyle.secondary, row=1)
    async def playlist(self, button: nextcord.ui.Button, interaction: Interaction):
        """Mostra a fila de músicas atual."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.cog.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.cog.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Obtém a fila personalizada para este servidor
        queue = self.cog.get_queue(guild_id)

        embed = nextcord.Embed(
            title=f"{EMOJIS['music']} Fila de Músicas",
            color=nextcord.Color.purple()
        )

        # Informações da música atual
        if player.current:
            # Obtém o requester da faixa atual
            requester = self.cog.get_requester(guild_id, player.current)
            requester_mention = requester.mention if requester else "Desconhecido"
            
            embed.add_field(
                name=f"{EMOJIS['music']} Tocando Agora",
                value=f"**[{player.current.title}]({player.current.uri})** ({self.cog.format_duration(player.current.length)})\n"
                      f"Adicionado por: {requester_mention}",
                inline=False
            )
        else:
            embed.add_field(
                name=f"{EMOJIS['music']} Tocando Agora",
                value="Nada tocando no momento.",
                inline=False
            )

        # Lista de músicas na fila
        if queue:
            queue_list = []
            for i, track in enumerate(queue[:10]):  # Limita a 10 músicas para não sobrecarregar o embed
                # Obtém o requester da faixa
                requester = self.cog.get_requester(guild_id, track)
                requester_mention = requester.mention if requester else "Desconhecido"
                
                queue_list.append(f"**{i+1}.** [{track.title}]({track.uri}) ({self.cog.format_duration(track.length)}) - {requester_mention}")
            
            remaining = len(queue) - 10
            queue_text = "\n".join(queue_list)
            if remaining > 0:
                queue_text += f"\n\n*E mais {remaining} música(s)...*"
            
            embed.add_field(
                name=f"{EMOJIS['playlist']} Próximas na Fila ({len(queue)})",
                value=queue_text,
                inline=False
            )
        else:
            embed.add_field(
                name=f"{EMOJIS['playlist']} Próximas na Fila",
                value="A fila está vazia. Adicione músicas com `/tocar`!",
                inline=False
            )

        # Informações adicionais
        loop_status = "Desativado"
        loop_state = self.cog.get_loop_state(guild_id)
        if loop_state == "track": loop_status = "Faixa"
        elif loop_state == "queue": loop_status = "Fila"
        
        # Obtém o volume de forma segura
        volume = self.cog.get_player_volume(player)
        
        embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Status: {'Pausado' if player.paused else 'Tocando'}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @nextcord.ui.button(emoji=EMOJIS["autoplay"], style=nextcord.ButtonStyle.secondary, row=2)
    async def autoplay(self, button: nextcord.ui.Button, interaction: Interaction):
        """Ativa ou desativa o autoplay."""
        guild_id = interaction.guild_id
        
        # Alterna o estado do autoplay
        current_autoplay = self.cog.get_autoplay_state(guild_id)
        new_autoplay = not current_autoplay
        self.cog.set_autoplay_state(guild_id, new_autoplay)
        
        if new_autoplay:
            await interaction.response.send_message(f"{EMOJIS['autoplay']} Autoplay ativado! Músicas relacionadas serão adicionadas automaticamente.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{EMOJIS['autoplay']} Autoplay desativado!", ephemeral=True)
            
        await self.cog.update_now_playing_message(self.player)

class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Dicionário para armazenar os players ativos por guild
        self.players: Dict[int, mafic.Player] = {}
        
        # Dicionário para armazenar as filas personalizadas por guild
        self.queues: Dict[int, List[mafic.Track]] = {}
        
        # Dicionário para armazenar os requesters das faixas por guild
        # Formato: {guild_id: {track_identifier: requester}}
        self.track_requesters: Dict[int, Dict[str, nextcord.Member]] = {}
        
        # Dicionário para armazenar as mensagens de "agora tocando" por guild
        # Formato: {guild_id: (message_id, channel_id)}
        self.now_playing_messages: Dict[int, tuple] = {}
        
        # Dicionário para armazenar o estado de loop por guild
        # Valores possíveis: "none", "track", "queue"
        self.loop_states: Dict[int, str] = {}
        
        # Dicionário para armazenar o estado de autoplay por guild
        # Valores possíveis: True, False
        self.autoplay_states: Dict[int, bool] = {}
        
        # Dicionário para armazenar a última música tocada por guild
        self.last_tracks: Dict[int, mafic.Track] = {}
        
        # Dicionário para armazenar tentativas de reconexão por guild
        self.reconnect_attempts: Dict[int, int] = {}
        
        # Cache para resultados do Spotify
        self.spotify_cache = SpotifyCache()
        
        # Inicializa o cliente do Spotify
        self.init_spotify_client()
        
        # Inicializa o pool do Mafic quando o bot estiver pronto
        self.bot.loop.create_task(self.initialize_mafic())
        
    def init_spotify_client(self):
        """Inicializa o cliente do Spotify."""
        try:
            # Tenta obter as credenciais do ambiente
            client_id = os.getenv("SPOTIFY_CLIENT_ID")
            client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
            
            # Se não encontrar no ambiente, tenta carregar de um arquivo de configuração
            if not client_id or not client_secret:
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                        client_id = config.get("spotify", {}).get("client_id")
                        client_secret = config.get("spotify", {}).get("client_secret")
            
            if client_id and client_secret:
                auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
                self.spotify = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("Cliente do Spotify inicializado com sucesso.")
            else:
                logger.warning("Credenciais do Spotify não encontradas. A integração com Spotify será limitada.")
                self.spotify = None
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente do Spotify: {e}", exc_info=True)
            self.spotify = None
        
    async def initialize_mafic(self):
        """Inicializa o pool do Mafic quando o bot estiver pronto."""
        await self.bot.wait_until_ready()
        
        # Verifica se o bot já tem um pool Mafic inicializado
        if hasattr(self.bot, "mafic_pool") and self.bot.mafic_pool:
            logger.info("Pool Mafic já inicializado.")
            return
            
        try:
            # Cria o pool do Mafic com os nós do Lavalink
            # Você pode adicionar mais nós conforme necessário
            self.bot.mafic_pool = mafic.NodePool(self.bot)
            
            # Adiciona o nó do Lavalink
            # Substitua host, port, password pelos valores corretos do seu servidor Lavalink
            await self.bot.mafic_pool.create_node(
                host="127.0.0.1",
                port=2333,
                label="MAIN",
                password="youshallnotpass",
                secure=False
            )
            
            logger.info("Pool Mafic inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao inicializar o pool Mafic: {e}", exc_info=True)
    
    def get_queue(self, guild_id: int) -> List[mafic.Track]:
        """Obtém a fila personalizada para um servidor específico."""
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]
    
    def set_requester(self, guild_id: int, track: mafic.Track, requester: nextcord.Member):
        """Armazena o requester para uma faixa específica."""
        if guild_id not in self.track_requesters:
            self.track_requesters[guild_id] = {}
        
        # Usa o identificador único da faixa como chave
        track_id = f"{track.title}:{track.uri}"
        self.track_requesters[guild_id][track_id] = requester
    
    def get_requester(self, guild_id: int, track: mafic.Track) -> Optional[nextcord.Member]:
        """Obtém o requester para uma faixa específica."""
        if guild_id not in self.track_requesters:
            return None
        
        # Usa o identificador único da faixa como chave
        track_id = f"{track.title}:{track.uri}"
        return self.track_requesters[guild_id].get(track_id)
    
    def get_loop_state(self, guild_id: int) -> str:
        """Obtém o estado de loop para um servidor específico."""
        return self.loop_states.get(guild_id, "none")
    
    def set_loop_state(self, guild_id: int, state: str):
        """Define o estado de loop para um servidor específico."""
        self.loop_states[guild_id] = state
        
    def get_autoplay_state(self, guild_id: int) -> bool:
        """Obtém o estado de autoplay para um servidor específico."""
        return self.autoplay_states.get(guild_id, False)
    
    def set_autoplay_state(self, guild_id: int, state: bool):
        """Define o estado de autoplay para um servidor específico."""
        self.autoplay_states[guild_id] = state
        
    def get_player_volume(self, player):
        """Obtém o volume do player de forma segura, com fallback para valor padrão."""
        try:
            return getattr(player, "volume", 100)
        except:
            return 100
            
    async def set_player_volume(self, player, volume):
        """Define o volume do player de forma segura."""
        try:
            if hasattr(player, "set_volume"):
                await player.set_volume(volume)
        except Exception as e:
            logger.error(f"Erro ao definir volume: {e}")
            # Silenciosamente falha se o método não existir
    
    async def get_player(self, interaction: Interaction) -> Optional[mafic.Player]:
        """Obtém ou cria um player para o servidor."""
        if not interaction.guild_id:
            return None
            
        # Se já existe um player para este servidor, retorna-o
        if interaction.guild_id in self.players:
            return self.players[interaction.guild_id]
            
        # Verifica se o usuário está em um canal de voz
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Você precisa estar em um canal de voz para usar os comandos de música.", ephemeral=True)
            return None
            
        voice_channel = interaction.user.voice.channel
        
        # Verifica permissões
        permissions = voice_channel.permissions_for(interaction.guild.me)
        if not permissions.connect or not permissions.speak:
            await interaction.followup.send(f"Não tenho permissão para conectar ou falar no canal {voice_channel.mention}.", ephemeral=True)
            return None
            
        try:
            # Cria o player e conecta ao canal de voz
            # Usando o método correto para a versão atual da Mafic
            player = await voice_channel.connect(cls=mafic.Player)
            
            # Armazena o player para uso futuro
            self.players[interaction.guild_id] = player
            
            # Reseta contadores de tentativas
            self.reconnect_attempts[interaction.guild_id] = 0
            
            logger.info(f"Novo player criado e conectado para guild {interaction.guild_id} no canal {voice_channel.name}")
            return player
        except Exception as e:
            logger.error(f"Erro ao criar player para guild {interaction.guild_id}: {e}", exc_info=True)
            # Incrementa contador de tentativas
            self.reconnect_attempts[interaction.guild_id] = self.reconnect_attempts.get(interaction.guild_id, 0) + 1
            return None
    
    async def get_spotify_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de uma faixa do Spotify."""
        if not self.spotify:
            return None
            
        # Verifica o cache primeiro
        cache_key = f"track:{track_id}"
        cached_data = self.spotify_cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            track_data = self.spotify.track(track_id)
            self.spotify_cache.set(cache_key, track_data)
            return track_data
        except Exception as e:
            logger.error(f"Erro ao obter faixa do Spotify: {e}")
            return None
            
    async def get_spotify_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de um álbum do Spotify."""
        if not self.spotify:
            return None
            
        # Verifica o cache primeiro
        cache_key = f"album:{album_id}"
        cached_data = self.spotify_cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            album_data = self.spotify.album(album_id)
            self.spotify_cache.set(cache_key, album_data)
            return album_data
        except Exception as e:
            logger.error(f"Erro ao obter álbum do Spotify: {e}")
            return None
            
    async def get_spotify_playlist(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de uma playlist do Spotify."""
        if not self.spotify:
            return None
            
        # Verifica o cache primeiro
        cache_key = f"playlist:{playlist_id}"
        cached_data = self.spotify_cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            playlist_data = self.spotify.playlist(playlist_id)
            self.spotify_cache.set(cache_key, playlist_data)
            return playlist_data
        except Exception as e:
            logger.error(f"Erro ao obter playlist do Spotify: {e}")
            return None
    
    async def process_spotify_url(self, url: str, player: mafic.Player, interaction: Interaction) -> Optional[Union[mafic.Track, List[mafic.Track]]]:
        """Processa uma URL do Spotify e retorna faixas do Lavalink."""
        if not self.spotify:
            await interaction.followup.send("⚠️ Integração com Spotify não está configurada. Configure as credenciais do Spotify para usar esta funcionalidade.", ephemeral=True)
            return None
            
        # Extrai o tipo e ID da URL do Spotify
        match = SPOTIFY_URL_REGEX.match(url)
        if not match:
            await interaction.followup.send("❌ URL do Spotify inválida.", ephemeral=True)
            return None
            
        spotify_type = match.group(3)  # track, album ou playlist
        spotify_id = match.group(4)
        
        if spotify_type == "track":
            # Processa uma faixa única
            await interaction.followup.send(f"{EMOJIS['spotify']} Buscando faixa do Spotify...", ephemeral=True)
            track_data = await self.get_spotify_track(spotify_id)
            
            if not track_data:
                await interaction.followup.send("❌ Não foi possível obter informações da faixa do Spotify.", ephemeral=True)
                return None
                
            # Formata a consulta de busca para o YouTube
            artist_name = track_data["artists"][0]["name"] if track_data["artists"] else ""
            track_name = track_data["name"]
            search_query = f"ytsearch:{artist_name} - {track_name} audio"
            
            try:
                tracks = await player.fetch_tracks(search_query)
                if not tracks:
                    await interaction.followup.send(f"❌ Não foi possível encontrar a faixa do Spotify no YouTube: {artist_name} - {track_name}", ephemeral=True)
                    return None
                    
                # Retorna a primeira faixa encontrada
                return tracks[0]
            except Exception as e:
                logger.error(f"Erro ao buscar faixa do Spotify no YouTube: {e}")
                await interaction.followup.send(f"❌ Erro ao buscar faixa do Spotify no YouTube: {e}", ephemeral=True)
                return None
                
        elif spotify_type == "album":
            # Processa um álbum
            await interaction.followup.send(f"{EMOJIS['spotify']} Buscando álbum do Spotify...", ephemeral=True)
            album_data = await self.get_spotify_album(spotify_id)
            
            if not album_data:
                await interaction.followup.send("❌ Não foi possível obter informações do álbum do Spotify.", ephemeral=True)
                return None
                
            # Obtém todas as faixas do álbum
            tracks_data = album_data["tracks"]["items"]
            
            if not tracks_data:
                await interaction.followup.send("❌ O álbum do Spotify não contém faixas.", ephemeral=True)
                return None
                
            # Busca cada faixa no YouTube
            result_tracks = []
            
            # Informa o usuário sobre o progresso
            progress_msg = await interaction.followup.send(f"{EMOJIS['spotify']} Buscando {len(tracks_data)} faixas do álbum '{album_data['name']}' no YouTube...", ephemeral=True)
            
            for i, track_data in enumerate(tracks_data):
                # Atualiza a mensagem de progresso a cada 5 faixas
                if i % 5 == 0 and i > 0:
                    try:
                        await progress_msg.edit(content=f"{EMOJIS['spotify']} Buscando faixas do álbum '{album_data['name']}' no YouTube... ({i}/{len(tracks_data)})")
                    except:
                        pass
                
                artist_name = track_data["artists"][0]["name"] if track_data["artists"] else ""
                track_name = track_data["name"]
                search_query = f"ytsearch:{artist_name} - {track_name} audio"
                
                try:
                    search_result = await player.fetch_tracks(search_query)
                    if search_result:
                        result_tracks.append(search_result[0])
                except Exception as e:
                    logger.error(f"Erro ao buscar faixa '{track_name}' do álbum no YouTube: {e}")
                    # Continua para a próxima faixa
                    continue
                    
            if not result_tracks:
                await interaction.followup.send("❌ Não foi possível encontrar nenhuma faixa do álbum no YouTube.", ephemeral=True)
                return None
                
            # Atualiza a mensagem final
            try:
                await progress_msg.edit(content=f"{EMOJIS['spotify']} Encontradas {len(result_tracks)}/{len(tracks_data)} faixas do álbum '{album_data['name']}' no YouTube.")
            except:
                pass
                
            return result_tracks
            
        elif spotify_type == "playlist":
            # Processa uma playlist
            await interaction.followup.send(f"{EMOJIS['spotify']} Buscando playlist do Spotify...", ephemeral=True)
            playlist_data = await self.get_spotify_playlist(spotify_id)
            
            if not playlist_data:
                await interaction.followup.send("❌ Não foi possível obter informações da playlist do Spotify.", ephemeral=True)
                return None
                
            # Obtém todas as faixas da playlist
            tracks_data = playlist_data["tracks"]["items"]
            
            if not tracks_data:
                await interaction.followup.send("❌ A playlist do Spotify não contém faixas.", ephemeral=True)
                return None
                
            # Busca cada faixa no YouTube
            result_tracks = []
            
            # Informa o usuário sobre o progresso
            progress_msg = await interaction.followup.send(f"{EMOJIS['spotify']} Buscando {len(tracks_data)} faixas da playlist '{playlist_data['name']}' no YouTube...", ephemeral=True)
            
            # Limita a 50 faixas para evitar sobrecarregar o Lavalink
            max_tracks = min(50, len(tracks_data))
            
            for i, item in enumerate(tracks_data[:max_tracks]):
                # Atualiza a mensagem de progresso a cada 5 faixas
                if i % 5 == 0 and i > 0:
                    try:
                        await progress_msg.edit(content=f"{EMOJIS['spotify']} Buscando faixas da playlist '{playlist_data['name']}' no YouTube... ({i}/{max_tracks})")
                    except:
                        pass
                
                track_data = item["track"]
                if not track_data:
                    continue
                    
                artist_name = track_data["artists"][0]["name"] if track_data["artists"] else ""
                track_name = track_data["name"]
                search_query = f"ytsearch:{artist_name} - {track_name} audio"
                
                try:
                    search_result = await player.fetch_tracks(search_query)
                    if search_result:
                        result_tracks.append(search_result[0])
                except Exception as e:
                    logger.error(f"Erro ao buscar faixa '{track_name}' da playlist no YouTube: {e}")
                    # Continua para a próxima faixa
                    continue
                    
            if not result_tracks:
                await interaction.followup.send("❌ Não foi possível encontrar nenhuma faixa da playlist no YouTube.", ephemeral=True)
                return None
                
            # Atualiza a mensagem final
            try:
                await progress_msg.edit(content=f"{EMOJIS['spotify']} Encontradas {len(result_tracks)}/{max_tracks} faixas da playlist '{playlist_data['name']}' no YouTube.")
            except:
                pass
                
            return result_tracks
            
        else:
            await interaction.followup.send(f"❌ Tipo de URL do Spotify não suportado: {spotify_type}", ephemeral=True)
            return None
    
    @nextcord.slash_command(name="tocar", description="Toca uma música ou playlist do YouTube/Spotify.")
    async def play(
        self, 
        interaction: Interaction, 
        busca: str = SlashOption(
            name="musica_ou_url", 
            description="Nome da música, URL do YouTube/SoundCloud ou URL do Spotify.", 
            required=True
        )
    ):
        """Comando para tocar música."""
        # Primeiro, verificamos se o usuário está em um canal de voz
        if not interaction.guild or not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Você precisa estar em um canal de voz para usar os comandos de música.", ephemeral=True)
            return

        # Deferimos a resposta para dar tempo de processar
        await interaction.response.defer(ephemeral=False)

        try:
            # Obtemos ou criamos o player
            player = await self.get_player(interaction)
            
            if not player:
                await interaction.followup.send("Não foi possível conectar ao canal de voz. Verifique se o bot tem permissão ou tente novamente mais tarde.", ephemeral=True)
                return

            # Verifica se é uma URL do Spotify
            is_spotify = bool(SPOTIFY_URL_REGEX.match(busca))
            
            # Verifica se é uma URL válida ou um termo de busca
            is_url = bool(URL_REGEX.match(busca))
            is_search_term = bool(SEARCH_TERM_REGEX.match(busca)) and not is_url

            tracks: Union[mafic.Playlist, List[mafic.Track], mafic.Track, None] = None

            if is_spotify:
                logger.info(f"Buscando URL do Spotify: {busca} para guild {interaction.guild_id}")
                tracks = await self.process_spotify_url(busca, player, interaction)
                
                if not tracks:
                    # O método process_spotify_url já envia mensagens de erro
                    return
                    
            elif is_url:
                logger.info(f"Buscando por URL: {busca} para guild {interaction.guild_id}")
                
                try:
                    tracks = await player.fetch_tracks(busca)  # Deixa Mafic decidir a fonte pela URL
                except mafic.errors.HTTPNotFound as e:
                    logger.error(f"Erro HTTP 404 ao buscar faixas: {e}")
                    await interaction.followup.send("❌ Erro ao conectar ao servidor de música. Tente novamente mais tarde.", ephemeral=True)
                    return
                except Exception as e:
                    logger.error(f"Erro ao buscar faixas por URL: {e}")
                    await interaction.followup.send(f"❌ Erro ao buscar música: {e}\n\nSe você está tentando usar um serviço não suportado, tente buscar a música diretamente pelo nome ou use um link do YouTube/SoundCloud.", ephemeral=True)
                    return
            elif is_search_term:
                logger.info(f"Buscando por termo: {busca} para guild {interaction.guild_id}")
                # Para termos de busca, tentamos várias abordagens
                try:
                    # Tentativa 1: ytsearch:
                    search_query = f"ytsearch:{busca}"
                    tracks = await player.fetch_tracks(search_query)
                    
                    # Se não encontrou nada, tenta outras abordagens
                    if not tracks:
                        # Tentativa 2: scsearch:
                        search_query = f"scsearch:{busca}"
                        tracks = await player.fetch_tracks(search_query)
                        
                    # Se ainda não encontrou, tenta uma busca direta no YouTube
                    if not tracks:
                        # Tentativa 3: URL direta do YouTube com o termo
                        search_query = f"https://www.youtube.com/results?search_query={busca.replace(' ', '+')}"
                        tracks = await player.fetch_tracks(search_query)
                        
                    # Se todas as tentativas falharam, informa ao usuário
                    if not tracks:
                        await interaction.followup.send(
                            "❌ Não foi possível encontrar resultados para sua busca. Tente usar termos mais específicos ou um link direto do YouTube ou SoundCloud.", 
                            ephemeral=True
                        )
                        return
                        
                except mafic.errors.HTTPNotFound as e:
                    logger.error(f"Erro HTTP 404 ao buscar faixas: {e}")
                    await interaction.followup.send(
                        "❌ O servidor de música não conseguiu processar sua busca. Tente usar termos mais simples ou um link direto do YouTube ou SoundCloud.", 
                        ephemeral=True
                    )
                    return
                except Exception as e:
                    logger.error(f"Erro ao buscar faixas por termo: {e}")
                    # Verifica se é um erro de formato desconhecido
                    if "Unknown file format" in str(e):
                        await interaction.followup.send(
                            "❌ Formato de arquivo desconhecido. O termo de busca pode conter caracteres especiais ou palavras que confundem o sistema de busca.\n\nTente usar termos mais simples ou específicos, como o nome da música e do artista.", 
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            f"❌ Erro ao buscar música: {e}\n\nTente usar termos mais simples ou um link direto do YouTube ou SoundCloud.", 
                            ephemeral=True
                        )
                    return
            else:
                await interaction.followup.send("Entrada inválida. Por favor, forneça uma URL válida (YouTube/SoundCloud/Spotify) ou um termo de busca (3-500 caracteres).", ephemeral=True)
                return

            if not tracks:
                await interaction.followup.send(f"Nenhuma música encontrada para: `{busca}`", ephemeral=True)
                return

            added_to_queue_count = 0
            first_track_title = ""
            
            # Obtém a fila personalizada para este servidor
            queue = self.get_queue(interaction.guild_id)

            # Cria o painel estilizado ANTES de adicionar à fila
            # Isso garante que o painel sempre apareça, independente do estado do player
            if player.current:
                # Se já está tocando algo, atualizamos o painel existente
                await self.update_now_playing_message(player)
            else:
                # Se não está tocando nada, criamos um painel inicial com a primeira música que será adicionada
                # Sem tentar modificar player.current que é somente leitura
                if isinstance(tracks, mafic.Playlist) and tracks.tracks:
                    temp_track = tracks.tracks[0]
                    self.set_requester(interaction.guild_id, temp_track, interaction.user)
                    # Criamos o painel diretamente com a faixa temporária
                    await self.create_now_playing_panel_for_track(interaction.channel, player, temp_track)
                elif isinstance(tracks, list) and tracks:
                    temp_track = tracks[0]
                    self.set_requester(interaction.guild_id, temp_track, interaction.user)
                    # Criamos o painel diretamente com a faixa temporária
                    await self.create_now_playing_panel_for_track(interaction.channel, player, temp_track)
                elif isinstance(tracks, mafic.Track):
                    temp_track = tracks
                    self.set_requester(interaction.guild_id, temp_track, interaction.user)
                    # Criamos o painel diretamente com a faixa temporária
                    await self.create_now_playing_panel_for_track(interaction.channel, player, temp_track)
            
            # Adiciona o requester às faixas usando nosso sistema de armazenamento separado
            if isinstance(tracks, mafic.Playlist):
                for track in tracks.tracks:
                    # Armazena o requester para cada faixa
                    self.set_requester(interaction.guild_id, track, interaction.user)
                queue.extend(tracks.tracks)
                added_to_queue_count = len(tracks.tracks)
                first_track_title = tracks.name # Nome da playlist
                
                # Envia mensagem de confirmação
                confirm_msg = await interaction.followup.send(f"🎶 Playlist **{tracks.name}** ({added_to_queue_count} músicas) adicionada à fila!")
                
            elif isinstance(tracks, list) and tracks: # Lista de faixas (resultado de busca ou Spotify)
                if is_search_term and not is_spotify: # Se foi uma busca normal, geralmente pegamos a primeira e adicionamos
                    track_to_add = tracks[0]
                    # Armazena o requester para a faixa
                    self.set_requester(interaction.guild_id, track_to_add, interaction.user)
                    queue.append(track_to_add)
                    added_to_queue_count = 1
                    first_track_title = track_to_add.title
                    
                    # Envia mensagem de confirmação
                    confirm_msg = await interaction.followup.send(f"🎵 **{track_to_add.title}** adicionada à fila!")
                    
                else: # Se foi uma URL de faixa única que retornou uma lista ou resultado do Spotify
                    for track in tracks:
                        # Armazena o requester para cada faixa
                        self.set_requester(interaction.guild_id, track, interaction.user)
                    queue.extend(tracks)
                    added_to_queue_count = len(tracks)
                    first_track_title = tracks[0].title
                    
                    # Envia mensagem de confirmação
                    if is_spotify:
                        confirm_msg = await interaction.followup.send(f"{EMOJIS['spotify']} **{added_to_queue_count} música(s)** do Spotify adicionada(s) à fila!")
                    else:
                        confirm_msg = await interaction.followup.send(f"🎵 **{tracks[0].title}** ({added_to_queue_count} música(s)) adicionada(s) à fila!")
            
            elif isinstance(tracks, mafic.Track): # Faixa única
                # Armazena o requester para a faixa
                self.set_requester(interaction.guild_id, tracks, interaction.user)
                queue.append(tracks)
                added_to_queue_count = 1
                first_track_title = tracks.title
                
                # Envia mensagem de confirmação
                confirm_msg = await interaction.followup.send(f"🎵 **{tracks.title}** adicionada à fila!")
                
            else:
                await interaction.followup.send(f"Não foi possível processar o resultado para: `{busca}`", ephemeral=True)
                return

            if not player.current and queue:
                # Inicia a primeira música da fila
                try:
                    first_track = queue.pop(0)
                    await player.play(first_track, start_time=0)
                    logger.info(f"Iniciando reprodução de {first_track.title} para guild {interaction.guild_id}")
                except mafic.errors.HTTPNotFound as e:
                    logger.error(f"Erro HTTP 404 ao iniciar reprodução: {e}")
                    await interaction.followup.send("Erro ao conectar ao servidor de música. Tente novamente mais tarde.", ephemeral=True)
                    return
                except Exception as e:
                    logger.error(f"Erro ao iniciar reprodução: {e}")
                    await interaction.followup.send(f"Erro ao iniciar reprodução: {e}", ephemeral=True)
                    return
            elif player.current and added_to_queue_count > 0:
                # Se já está tocando e algo foi adicionado, a mensagem de "agora tocando" pode ser atualizada
                # para refletir a fila, se a view estiver ativa.
                await self.update_now_playing_message(player)
        except nextcord.errors.InteractionResponded:
            logger.warning("Interação já respondida durante o comando /tocar")
        except Exception as e:
            logger.error(f"Erro inesperado no comando /tocar: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"Ocorreu um erro inesperado: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"Ocorreu um erro inesperado: {e}", ephemeral=True)
            except:
                pass

    @nextcord.slash_command(name="spotify", description="Toca uma música, álbum ou playlist do Spotify.")
    async def spotify(
        self, 
        interaction: Interaction, 
        url: str = SlashOption(
            name="url", 
            description="URL do Spotify (faixa, álbum ou playlist).", 
            required=True
        )
    ):
        """Comando específico para tocar música do Spotify."""
        # Primeiro, verificamos se o usuário está em um canal de voz
        if not interaction.guild or not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Você precisa estar em um canal de voz para usar os comandos de música.", ephemeral=True)
            return

        # Verifica se é uma URL do Spotify
        if not SPOTIFY_URL_REGEX.match(url):
            await interaction.response.send_message("❌ URL do Spotify inválida. Forneça uma URL de faixa, álbum ou playlist do Spotify.", ephemeral=True)
            return

        # Deferimos a resposta para dar tempo de processar
        await interaction.response.defer(ephemeral=False)

        try:
            # Obtemos ou criamos o player
            player = await self.get_player(interaction)
            
            if not player:
                await interaction.followup.send("Não foi possível conectar ao canal de voz. Verifique se o bot tem permissão ou tente novamente mais tarde.", ephemeral=True)
                return

            # Processa a URL do Spotify
            tracks = await self.process_spotify_url(url, player, interaction)
            
            if not tracks:
                # O método process_spotify_url já envia mensagens de erro
                return

            # Obtém a fila personalizada para este servidor
            queue = self.get_queue(interaction.guild_id)

            # Cria o painel estilizado ANTES de adicionar à fila
            if player.current:
                # Se já está tocando algo, atualizamos o painel existente
                await self.update_now_playing_message(player)
            else:
                # Se não está tocando nada, criamos um painel inicial com a primeira música que será adicionada
                if isinstance(tracks, list) and tracks:
                    temp_track = tracks[0]
                    self.set_requester(interaction.guild_id, temp_track, interaction.user)
                    await self.create_now_playing_panel_for_track(interaction.channel, player, temp_track)
                elif isinstance(tracks, mafic.Track):
                    temp_track = tracks
                    self.set_requester(interaction.guild_id, temp_track, interaction.user)
                    await self.create_now_playing_panel_for_track(interaction.channel, player, temp_track)
            
            # Adiciona as faixas à fila
            added_to_queue_count = 0
            
            if isinstance(tracks, list):
                for track in tracks:
                    self.set_requester(interaction.guild_id, track, interaction.user)
                queue.extend(tracks)
                added_to_queue_count = len(tracks)
                
                # Envia mensagem de confirmação
                await interaction.followup.send(f"{EMOJIS['spotify']} **{added_to_queue_count} música(s)** do Spotify adicionada(s) à fila!")
            elif isinstance(tracks, mafic.Track):
                self.set_requester(interaction.guild_id, tracks, interaction.user)
                queue.append(tracks)
                added_to_queue_count = 1
                
                # Envia mensagem de confirmação
                await interaction.followup.send(f"{EMOJIS['spotify']} **{tracks.title}** do Spotify adicionada à fila!")

            if not player.current and queue:
                # Inicia a primeira música da fila
                try:
                    first_track = queue.pop(0)
                    await player.play(first_track, start_time=0)
                    logger.info(f"Iniciando reprodução de {first_track.title} para guild {interaction.guild_id}")
                except Exception as e:
                    logger.error(f"Erro ao iniciar reprodução: {e}")
                    await interaction.followup.send(f"Erro ao iniciar reprodução: {e}", ephemeral=True)
                    return
            elif player.current and added_to_queue_count > 0:
                # Se já está tocando e algo foi adicionado, atualiza a mensagem de "agora tocando"
                await self.update_now_playing_message(player)
        except Exception as e:
            logger.error(f"Erro inesperado no comando /spotify: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"Ocorreu um erro inesperado: {e}", ephemeral=True)
            except:
                pass

    async def create_now_playing_panel_for_track(self, channel, player, track):
        """Cria um novo painel estilizado para uma faixa específica, sem depender de player.current."""
        if not player or not player.guild or not track:
            return None
            
        guild_id = player.guild.id
        
        # Cria um embed estilizado para o painel de música
        embed = nextcord.Embed(
            title="MUSIC PANEL",
            description=f"**[{track.title}]({track.uri})**",
            color=nextcord.Color.purple()  # Cor roxa para combinar com o exemplo
        )
        
        # Obtém o requester da faixa
        requester = self.get_requester(guild_id, track)
        
        # Adiciona campos para Requested By, Duration e Music Author
        embed.add_field(
            name="Requested By",
            value=f"{requester.mention if requester else 'Desconhecido'}",
            inline=True
        )
        
        embed.add_field(
            name="Music Duration",
            value=self.format_duration(track.length),
            inline=True
        )
        
        embed.add_field(
            name="Music Author",
            value=track.author,
            inline=True
        )
        
        # Define a thumbnail como a artwork da música, se disponível
        if track.artwork_url:
            embed.set_thumbnail(url=track.artwork_url)
            
        # Adiciona o footer com informações adicionais
        loop_status = "Desativado"
        loop_state = self.get_loop_state(guild_id)
        if loop_state == "track": loop_status = "Faixa"
        elif loop_state == "queue": loop_status = "Fila"
        
        # Obtém o volume de forma segura
        volume = self.get_player_volume(player)
        
        # Obtém o estado de autoplay
        autoplay = "Ativado" if self.get_autoplay_state(guild_id) else "Desativado"
        
        embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Autoplay: {autoplay} | Status: {'Pausado' if player.paused else 'Tocando'}")

        try:
            # Envia a mensagem com o embed e os controles
            message = await channel.send(embed=embed, view=MusicControls(player, self))
            
            # Armazena a referência para atualização futura
            self.now_playing_messages[guild_id] = (message.id, channel.id)
            logger.info(f"Novo painel 'agora tocando' criado para guild {guild_id} no canal {channel.name}")
            return message
        except Exception as e:
            logger.error(f"Erro ao criar painel 'agora tocando' para guild {guild_id}: {e}")
            return None
            
    async def create_now_playing_panel(self, channel, player):
        """Cria um novo painel estilizado para a música atual."""
        if not player or not player.guild or not player.current:
            return None
            
        guild_id = player.guild.id
        current_track = player.current
        
        # Cria um embed estilizado para o painel de música
        embed = nextcord.Embed(
            title="MUSIC PANEL",
            description=f"**[{current_track.title}]({current_track.uri})**",
            color=nextcord.Color.purple()  # Cor roxa para combinar com o exemplo
        )
        
        # Obtém o requester da faixa atual
        requester = self.get_requester(guild_id, current_track)
        
        # Adiciona campos para Requested By, Duration e Music Author
        embed.add_field(
            name="Requested By",
            value=f"{requester.mention if requester else 'Desconhecido'}",
            inline=True
        )
        
        embed.add_field(
            name="Music Duration",
            value=self.format_duration(current_track.length),
            inline=True
        )
        
        embed.add_field(
            name="Music Author",
            value=current_track.author,
            inline=True
        )
        
        # Define a thumbnail como a artwork da música, se disponível
        if current_track.artwork_url:
            embed.set_thumbnail(url=current_track.artwork_url)
            
        # Adiciona o footer com informações adicionais
        loop_status = "Desativado"
        loop_state = self.get_loop_state(guild_id)
        if loop_state == "track": loop_status = "Faixa"
        elif loop_state == "queue": loop_status = "Fila"
        
        # Obtém o volume de forma segura
        volume = self.get_player_volume(player)
        
        # Obtém o estado de autoplay
        autoplay = "Ativado" if self.get_autoplay_state(guild_id) else "Desativado"
        
        embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Autoplay: {autoplay} | Status: {'Pausado' if player.paused else 'Tocando'}")

        try:
            # Envia a mensagem com o embed e os controles
            message = await channel.send(embed=embed, view=MusicControls(player, self))
            
            # Armazena a referência para atualização futura
            self.now_playing_messages[guild_id] = (message.id, channel.id)
            logger.info(f"Novo painel 'agora tocando' criado para guild {guild_id} no canal {channel.name}")
            return message
        except Exception as e:
            logger.error(f"Erro ao criar painel 'agora tocando' para guild {guild_id}: {e}")
            return None
            
    async def update_now_playing_message(self, player: mafic.Player):
        """Atualiza a mensagem de 'agora tocando'."""
        if not player or not player.guild or not player.current:
            return

        guild_id = player.guild.id
        
        message_info = self.now_playing_messages.get(guild_id)
        if not message_info:
            return

        msg_id, channel_id = message_info
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, nextcord.TextChannel):
            logger.warning(f"Canal não encontrado ou não é canal de texto para guild {guild_id} ao atualizar NP.")
            return

        try:
            message = await channel.fetch_message(msg_id)
        except nextcord.NotFound:
            logger.warning(f"Mensagem 'agora tocando' (ID: {msg_id}) não encontrada para guild {guild_id} ao atualizar.")
            # Se a mensagem não existe mais, limpa a referência
            del self.now_playing_messages[guild_id]
            return
        except Exception as e:
            logger.error(f"Erro ao buscar mensagem 'agora tocando' para guild {guild_id}: {e}")
            return

        current_track = player.current
        
        # Cria um embed estilizado para o painel de música
        embed = nextcord.Embed(
            title="MUSIC PANEL",
            description=f"**[{current_track.title}]({current_track.uri})**",
            color=nextcord.Color.purple()  # Cor roxa para combinar com o exemplo
        )
        
        # Obtém o requester da faixa atual
        requester = self.get_requester(guild_id, current_track)
        
        # Adiciona campos para Requested By, Duration e Music Author
        embed.add_field(
            name="Requested By",
            value=f"{requester.mention if requester else 'Desconhecido'}",
            inline=True
        )
        
        embed.add_field(
            name="Music Duration",
            value=self.format_duration(current_track.length),
            inline=True
        )
        
        embed.add_field(
            name="Music Author",
            value=current_track.author,
            inline=True
        )
        
        # Define a thumbnail como a artwork da música, se disponível
        if current_track.artwork_url:
            embed.set_thumbnail(url=current_track.artwork_url)
            
        # Adiciona o footer com informações adicionais
        loop_status = "Desativado"
        loop_state = self.get_loop_state(guild_id)
        if loop_state == "track": loop_status = "Faixa"
        elif loop_state == "queue": loop_status = "Fila"
        
        # Obtém o volume de forma segura
        volume = self.get_player_volume(player)
        
        # Obtém o estado de autoplay
        autoplay = "Ativado" if self.get_autoplay_state(guild_id) else "Desativado"
        
        embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Autoplay: {autoplay} | Status: {'Pausado' if player.paused else 'Tocando'}")

        try:
            # Atualiza a mensagem com o novo embed e os controles
            await message.edit(content=None, embed=embed, view=MusicControls(player, self))
        except Exception as e:
            logger.error(f"Erro ao atualizar mensagem 'agora tocando' para guild {guild_id}: {e}")

    def format_duration(self, milliseconds: int) -> str:
        """Formata duração de milissegundos para HH:MM:SS ou MM:SS."""
        if milliseconds is None: return "N/A"
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @nextcord.slash_command(name="fila", description="Mostra a fila de músicas atual.")
    async def queue(self, interaction: Interaction):
        """Comando para mostrar a fila de músicas."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(interaction.guild_id)

        embed = nextcord.Embed(
            title=f"{EMOJIS['music']} Fila de Músicas",
            color=nextcord.Color.purple()
        )

        # Informações da música atual
        if player.current:
            # Obtém o requester da faixa atual
            requester = self.get_requester(interaction.guild_id, player.current)
            requester_mention = requester.mention if requester else "Desconhecido"
            
            embed.add_field(
                name=f"{EMOJIS['music']} Tocando Agora",
                value=f"**[{player.current.title}]({player.current.uri})** ({self.format_duration(player.current.length)})\n"
                      f"Adicionado por: {requester_mention}",
                inline=False
            )
        else:
            embed.add_field(
                name=f"{EMOJIS['music']} Tocando Agora",
                value="Nada tocando no momento.",
                inline=False
            )

        # Lista de músicas na fila
        if queue:
            queue_list = []
            for i, track in enumerate(queue[:10]):  # Limita a 10 músicas para não sobrecarregar o embed
                # Obtém o requester da faixa
                requester = self.get_requester(interaction.guild_id, track)
                requester_mention = requester.mention if requester else "Desconhecido"
                
                queue_list.append(f"**{i+1}.** [{track.title}]({track.uri}) ({self.format_duration(track.length)}) - {requester_mention}")
            
            remaining = len(queue) - 10
            queue_text = "\n".join(queue_list)
            if remaining > 0:
                queue_text += f"\n\n*E mais {remaining} música(s)...*"
            
            embed.add_field(
                name=f"{EMOJIS['playlist']} Próximas na Fila ({len(queue)})",
                value=queue_text,
                inline=False
            )
        else:
            embed.add_field(
                name=f"{EMOJIS['playlist']} Próximas na Fila",
                value="A fila está vazia. Adicione músicas com `/tocar`!",
                inline=False
            )

        # Informações adicionais
        loop_status = "Desativado"
        loop_state = self.get_loop_state(interaction.guild_id)
        if loop_state == "track": loop_status = "Faixa"
        elif loop_state == "queue": loop_status = "Fila"
        
        # Obtém o volume de forma segura
        volume = self.get_player_volume(player)
        
        # Obtém o estado de autoplay
        autoplay = "Ativado" if self.get_autoplay_state(interaction.guild_id) else "Desativado"
        
        embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Autoplay: {autoplay} | Status: {'Pausado' if player.paused else 'Tocando'}")
        
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="pausar", description="Pausa a música atual.")
    async def pause(self, interaction: Interaction):
        """Comando para pausar a música atual."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected or not player.current:
            await interaction.response.send_message("Não há música tocando no momento.", ephemeral=True)
            return
            
        if player.paused:
            await interaction.response.send_message("A música já está pausada. Use `/retomar` para continuar a reprodução.", ephemeral=True)
            return
            
        await player.pause()
        await interaction.response.send_message(f"{EMOJIS['pause']} Música pausada!")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="retomar", description="Retoma a reprodução da música pausada.")
    async def resume(self, interaction: Interaction):
        """Comando para retomar a reprodução da música pausada."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected or not player.current:
            await interaction.response.send_message("Não há música tocando no momento.", ephemeral=True)
            return
            
        if not player.paused:
            await interaction.response.send_message("A música já está tocando. Use `/pausar` para pausar a reprodução.", ephemeral=True)
            return
            
        await player.resume()
        await interaction.response.send_message(f"{EMOJIS['play']} Música retomada!")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="pular", description="Pula para a próxima música da fila.")
    async def skip(self, interaction: Interaction):
        """Comando para pular para a próxima música da fila."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected or not player.current:
            await interaction.response.send_message("Não há música tocando no momento.", ephemeral=True)
            return
            
        # Armazena a música atual como última tocada antes de pular
        if player.current:
            self.last_tracks[interaction.guild_id] = player.current
            
        await player.stop()  # Mafic lida com a próxima música da fila automaticamente
        await interaction.response.send_message(f"{EMOJIS['skip']} Música pulada!")

    @nextcord.slash_command(name="voltar", description="Volta para a música anterior.")
    async def back(self, interaction: Interaction):
        """Comando para voltar para a música anterior."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        last_track = self.last_tracks.get(interaction.guild_id)
        
        if last_track:
            # Adiciona a música atual de volta à fila (no início)
            if player.current:
                queue = self.get_queue(interaction.guild_id)
                queue.insert(0, player.current)
                
            # Toca a última música
            try:
                await player.play(last_track)
                await interaction.response.send_message(f"{EMOJIS['back']} Voltando para a música anterior: **{last_track.title}**")
            except Exception as e:
                logger.error(f"Erro ao voltar para música anterior: {e}")
                await interaction.response.send_message(f"Erro ao voltar para música anterior: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("Não há música anterior para voltar.", ephemeral=True)

    @nextcord.slash_command(name="volume", description="Ajusta o volume da reprodução.")
    async def volume(
        self, 
        interaction: Interaction, 
        nivel: int = SlashOption(
            name="nivel", 
            description="Nível de volume (0-100).", 
            required=True,
            min_value=0,
            max_value=100
        )
    ):
        """Comando para ajustar o volume da reprodução."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Define o volume
        await self.set_player_volume(player, nivel)
        
        # Determina o emoji com base no nível de volume
        emoji = EMOJIS["volume_down"] if nivel <= 50 else EMOJIS["volume_up"]
        
        await interaction.response.send_message(f"{emoji} Volume ajustado para {nivel}%!")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="loop", description="Alterna entre os modos de loop (desativado, faixa, fila).")
    async def loop_command(self, interaction: Interaction):
        """Comando para alternar entre os modos de loop."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Obtém o estado atual de loop
        current_state = self.get_loop_state(interaction.guild_id)
        
        # Alterna entre os estados: none -> track -> queue -> none
        if current_state == "none":
            new_state = "track"
            message = f"{EMOJIS['loop']} Loop ativado para a faixa atual!"
        elif current_state == "track":
            new_state = "queue"
            message = f"{EMOJIS['loop']} Loop ativado para toda a fila!"
        else:  # queue
            new_state = "none"
            message = f"{EMOJIS['loop']} Loop desativado!"
            
        self.set_loop_state(interaction.guild_id, new_state)
        await interaction.response.send_message(message)
        
        # Atualiza a mensagem de "agora tocando" para refletir o novo estado de loop
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="autoplay", description="Ativa ou desativa o autoplay.")
    async def autoplay_command(self, interaction: Interaction):
        """Comando para ativar ou desativar o autoplay."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Alterna o estado do autoplay
        current_autoplay = self.get_autoplay_state(interaction.guild_id)
        new_autoplay = not current_autoplay
        self.set_autoplay_state(interaction.guild_id, new_autoplay)
        
        if new_autoplay:
            await interaction.response.send_message(f"{EMOJIS['autoplay']} Autoplay ativado! Músicas relacionadas serão adicionadas automaticamente.")
        else:
            await interaction.response.send_message(f"{EMOJIS['autoplay']} Autoplay desativado!")
            
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="embaralhar", description="Embaralha a fila de músicas.")
    async def shuffle(self, interaction: Interaction):
        """Comando para embaralhar a fila de músicas."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(interaction.guild_id)
        
        if len(queue) <= 1:
            await interaction.response.send_message("Não há músicas suficientes na fila para embaralhar.", ephemeral=True)
            return
            
        # Embaralha a fila
        import random
        random.shuffle(queue)
        
        await interaction.response.send_message(f"{EMOJIS['shuffle']} Fila embaralhada! Use `/fila` para ver a nova ordem.")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="parar", description="Para a reprodução e limpa a fila.")
    async def stop(self, interaction: Interaction):
        """Comando para parar a reprodução e limpar a fila."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Limpa a fila personalizada
        if interaction.guild_id in self.queues:
            self.queues[interaction.guild_id].clear()
            
        await player.stop()  # Para a música atual
        
        try:
            await player.disconnect(force=True)  # Desconecta do canal de voz
        except Exception as e:
            logger.error(f"Erro ao desconectar player para guild {interaction.guild_id}: {e}")

        # Remove o player da lista
        del self.players[interaction.guild_id]
        
        # Limpa o dicionário de requesters
        if interaction.guild_id in self.track_requesters:
            del self.track_requesters[interaction.guild_id]
        
        # Limpa a fila personalizada
        if interaction.guild_id in self.queues:
            del self.queues[interaction.guild_id]
            
        # Limpa o estado de loop
        if interaction.guild_id in self.loop_states:
            del self.loop_states[interaction.guild_id]
            
        # Limpa o estado de autoplay
        if interaction.guild_id in self.autoplay_states:
            del self.autoplay_states[interaction.guild_id]
            
        # Limpa a última música tocada
        if interaction.guild_id in self.last_tracks:
            del self.last_tracks[interaction.guild_id]
            
        # Limpa a mensagem de "agora tocando"
        if interaction.guild_id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[interaction.guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(msg_id)
                        await message.edit(content="🚶 Reprodução parada e fila limpa!", embed=None, view=None)
                    except:
                        pass
            except:
                pass
                
            del self.now_playing_messages[interaction.guild_id]
            
        await interaction.response.send_message(f"{EMOJIS['stop']} Reprodução parada e fila limpa!")

    @nextcord.slash_command(name="sair", description="Desconecta o bot do canal de voz.")
    async def leave(self, interaction: Interaction):
        """Comando para desconectar o bot do canal de voz."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O bot não está conectado a um canal de voz.", ephemeral=True)
            return
            
        try:
            await player.disconnect(force=True)  # Desconecta do canal de voz
        except Exception as e:
            logger.error(f"Erro ao desconectar player para guild {interaction.guild_id}: {e}")

        # Remove o player da lista
        del self.players[interaction.guild_id]
        
        # Limpa a mensagem de "agora tocando"
        if interaction.guild_id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[interaction.guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(msg_id)
                        await message.edit(content="🚶 Bot desconectado do canal de voz.", embed=None, view=None)
                    except:
                        pass
            except:
                pass
                
            del self.now_playing_messages[interaction.guild_id]
            
        await interaction.response.send_message("🚶 Desconectado do canal de voz!")

    @nextcord.slash_command(name="reconectar", description="Força a reconexão do bot ao servidor de música.")
    async def reconnect(self, interaction: Interaction):
        """Comando para forçar a reconexão do bot ao servidor de música."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Tenta reconectar todos os nós do Lavalink
            if hasattr(self.bot, "mafic_pool") and self.bot.mafic_pool:
                for node in self.bot.mafic_pool.nodes:
                    await node.reconnect()
                
                # Reseta contadores de tentativas
                self.reconnect_attempts = {}
                
                await interaction.followup.send("✅ Reconexão ao servidor de música concluída com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Sistema de música não inicializado corretamente.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao reconectar ao Lavalink: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Erro ao reconectar ao servidor de música: {e}", ephemeral=True)

    @nextcord.slash_command(name="configurar_spotify", description="Configura as credenciais do Spotify para integração completa.")
    async def setup_spotify(
        self, 
        interaction: Interaction, 
        client_id: str = SlashOption(
            name="client_id", 
            description="Client ID do Spotify Developer.", 
            required=True
        ),
        client_secret: str = SlashOption(
            name="client_secret", 
            description="Client Secret do Spotify Developer.", 
            required=True
        )
    ):
        """Comando para configurar as credenciais do Spotify."""
        # Verifica se o usuário tem permissão de administrador
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Você precisa ter permissão de administrador para usar este comando.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Cria o diretório de configuração se não existir
            config_dir = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(config_dir, "config.json")
            
            # Carrega a configuração existente ou cria uma nova
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
            else:
                config = {}
                
            # Adiciona ou atualiza as credenciais do Spotify
            if "spotify" not in config:
                config["spotify"] = {}
                
            config["spotify"]["client_id"] = client_id
            config["spotify"]["client_secret"] = client_secret
            
            # Salva a configuração
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
                
            # Reinicializa o cliente do Spotify
            self.init_spotify_client()
            
            if self.spotify:
                await interaction.followup.send("✅ Credenciais do Spotify configuradas com sucesso! A integração completa com Spotify está ativada.", ephemeral=True)
            else:
                await interaction.followup.send("⚠️ Credenciais do Spotify salvas, mas houve um erro ao inicializar o cliente. Verifique se as credenciais estão corretas.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao configurar credenciais do Spotify: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Erro ao configurar credenciais do Spotify: {e}", ephemeral=True)

    # Eventos Mafic
    @commands.Cog.listener()
    async def on_mafic_track_start(self, player: mafic.Player, track: mafic.Track):
        """Evento disparado quando uma faixa começa a tocar."""
        if not player.guild:
            return

        guild_id = player.guild.id
        logger.info(f"Faixa iniciada: {track.title} em {player.guild.name} ({guild_id})")
        
        # Armazena a última música tocada para referência
        last_track = self.last_tracks.get(guild_id)
        
        # Envia mensagem de confirmação de início de música
        if last_track:
            # Encontra o canal para enviar a mensagem
            channel = None
            if guild_id in self.now_playing_messages:
                msg_id, channel_id = self.now_playing_messages[guild_id]
                channel = self.bot.get_channel(channel_id)
            
            if channel:
                try:
                    await channel.send(f"🎵 Música **{last_track.title}** acabou, música **{track.title}** começou!")
                except Exception as e:
                    logger.error(f"Erro ao enviar mensagem de confirmação para guild {guild_id}: {e}")
        
        # Atualiza a última música tocada
        self.last_tracks[guild_id] = track

        # Cria ou atualiza a mensagem de "agora tocando"
        # Verifica se já existe uma mensagem de "agora tocando" para este servidor
        if guild_id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(msg_id)
                        # Atualiza a mensagem existente
                        await self.update_now_playing_message(player)
                        return
                    except nextcord.NotFound:
                        # Se a mensagem não existe mais, cria uma nova
                        pass
                    except Exception as e:
                        logger.error(f"Erro ao buscar mensagem 'agora tocando' para guild {guild_id}: {e}")
            except Exception as e:
                logger.error(f"Erro ao processar mensagem 'agora tocando' para guild {guild_id}: {e}")
        
        # Se chegou aqui, precisa criar uma nova mensagem
        # Encontra um canal adequado para enviar a mensagem
        channel = None
        
        # Tenta usar o canal de texto associado ao canal de voz, se existir
        if player.channel and hasattr(player.channel, 'text_channel') and player.channel.text_channel:
            channel = player.channel.text_channel
        
        # Se não encontrou um canal associado, tenta usar o canal de sistema
        if not channel and player.guild.system_channel:
            channel = player.guild.system_channel
            
        # Se ainda não encontrou, tenta o primeiro canal de texto visível
        if not channel:
            for ch in player.guild.text_channels:
                if ch.permissions_for(player.guild.me).send_messages:
                    channel = ch
                    break
        
        if channel:
            await self.create_now_playing_panel(channel, player)

    @commands.Cog.listener()
    async def on_mafic_track_end(self, player: mafic.Player, track: mafic.Track, reason: str):
        """Evento disparado quando uma faixa termina de tocar."""
        if not player.guild:
            return
            
        guild_id = player.guild.id
        logger.info(f"Faixa terminada: {track.title} em {player.guild.name} ({guild_id}) - Razão: {reason}")
        
        # Verifica se há mais músicas na fila
        queue = self.get_queue(guild_id)
        
        # Verifica o estado de loop
        loop_state = self.get_loop_state(guild_id)
        
        # Se o loop de faixa estiver ativado, adiciona a mesma faixa de volta à fila
        if loop_state == "track" and reason != "REPLACED":
            await player.play(track)
            return
            
        # Se o loop de fila estiver ativado, adiciona a faixa ao final da fila
        if loop_state == "queue" and reason != "REPLACED":
            queue.append(track)
            
        # Se não há mais músicas na fila e não é um loop, verifica se o autoplay está ativado
        if not queue and reason != "REPLACED":
            # Verifica se o autoplay está ativado
            if self.get_autoplay_state(guild_id) and track:
                # Tenta buscar uma música relacionada
                try:
                    # Usa o título da música atual para buscar músicas relacionadas
                    search_query = f"ytsearch:{track.title} similar music"
                    related_tracks = await player.fetch_tracks(search_query)
                    
                    if related_tracks and len(related_tracks) > 0:
                        # Adiciona a primeira música relacionada à fila
                        related_track = related_tracks[0]
                        
                        # Evita adicionar a mesma música
                        if related_track.title != track.title:
                            # Armazena o bot como requester para músicas de autoplay
                            self.set_requester(guild_id, related_track, player.guild.me)
                            
                            # Toca a música relacionada
                            await player.play(related_track)
                            
                            # Encontra um canal para enviar a mensagem
                            channel = None
                            if guild_id in self.now_playing_messages:
                                msg_id, channel_id = self.now_playing_messages[guild_id]
                                channel = self.bot.get_channel(channel_id)
                            
                            if channel:
                                await channel.send(f"{EMOJIS['autoplay']} Autoplay adicionou: **{related_track.title}**")
                                
                            return
                except Exception as e:
                    logger.error(f"Erro ao buscar música relacionada para autoplay: {e}")
            
            # Armazena a última música tocada antes de limpar
            self.last_tracks[guild_id] = track
            
            # Limpa a mensagem de "agora tocando"
            if guild_id in self.now_playing_messages:
                try:
                    msg_id, channel_id = self.now_playing_messages[guild_id]
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        try:
                            message = await channel.fetch_message(msg_id)
                            await message.edit(content="🎵 Reprodução finalizada. Use `/tocar` para adicionar mais músicas!", embed=None, view=None)
                        except Exception as e:
                            logger.error(f"Erro ao atualizar mensagem 'agora tocando' para guild {guild_id}: {e}")
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem 'agora tocando' para guild {guild_id}: {e}")
                
                # Limpa a referência da mensagem
                del self.now_playing_messages[guild_id]
            return
            
        # Se há mais músicas na fila e não é um loop ou substituição, toca a próxima
        if queue and reason != "REPLACED":
            next_track = queue.pop(0)
            try:
                await player.play(next_track)
            except Exception as e:
                logger.error(f"Erro ao tocar próxima faixa para guild {guild_id}: {e}")
                
                # Tenta a próxima música da fila, se houver
                if queue:
                    try:
                        next_track = queue.pop(0)
                        await player.play(next_track)
                    except Exception as e2:
                        logger.error(f"Erro ao tocar faixa alternativa para guild {guild_id}: {e2}")

    @commands.Cog.listener()
    async def on_mafic_track_exception(self, player: mafic.Player, track: mafic.Track, exception: Exception):
        """Evento disparado quando ocorre um erro ao tocar uma faixa."""
        if not player.guild:
            return
            
        guild_id = player.guild.id
        logger.error(f"Erro ao tocar faixa: {track.title} em {player.guild.name} ({guild_id}): {exception}")
        
        # Encontra um canal para enviar a mensagem de erro
        channel = None
        if guild_id in self.now_playing_messages:
            msg_id, channel_id = self.now_playing_messages[guild_id]
            channel = self.bot.get_channel(channel_id)
        
        if channel:
            await channel.send(f"❌ Erro ao tocar **{track.title}**: {exception}")
        
        # Tenta tocar a próxima música da fila
        queue = self.get_queue(guild_id)
        if queue:
            next_track = queue.pop(0)
            try:
                await player.play(next_track)
            except Exception as e:
                logger.error(f"Erro ao tocar próxima faixa após exceção para guild {guild_id}: {e}")

    @commands.Cog.listener()
    async def on_mafic_track_stuck(self, player: mafic.Player, track: mafic.Track, threshold_ms: int):
        """Evento disparado quando uma faixa fica presa (travada)."""
        if not player.guild:
            return
            
        guild_id = player.guild.id
        logger.warning(f"Faixa travada: {track.title} em {player.guild.name} ({guild_id}) - Threshold: {threshold_ms}ms")
        
        # Encontra um canal para enviar a mensagem
        channel = None
        if guild_id in self.now_playing_messages:
            msg_id, channel_id = self.now_playing_messages[guild_id]
            channel = self.bot.get_channel(channel_id)
        
        if channel:
            await channel.send(f"⚠️ A música **{track.title}** travou. Tentando pular para a próxima...")
        
        # Tenta pular para a próxima música
        await player.stop()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        """Evento disparado quando o estado de voz de um membro muda."""
        # Ignora se não for o próprio bot
        if member.id != self.bot.user.id:
            return
            
        # Verifica se o bot foi desconectado do canal de voz
        if before.channel and not after.channel:
            guild_id = member.guild.id
            
            # Verifica se há um player ativo para este servidor
            if guild_id in self.players:
                logger.info(f"Bot desconectado do canal de voz em {member.guild.name} ({guild_id})")
                
                # Limpa a fila personalizada
                if guild_id in self.queues:
                    self.queues[guild_id].clear()
                
                # Remove o player da lista
                del self.players[guild_id]
                
                # Limpa o dicionário de requesters
                if guild_id in self.track_requesters:
                    del self.track_requesters[guild_id]
                
                # Limpa a fila personalizada
                if guild_id in self.queues:
                    del self.queues[guild_id]
                    
                # Limpa o estado de loop
                if guild_id in self.loop_states:
                    del self.loop_states[guild_id]
                    
                # Limpa o estado de autoplay
                if guild_id in self.autoplay_states:
                    del self.autoplay_states[guild_id]
                    
                # Limpa a última música tocada
                if guild_id in self.last_tracks:
                    del self.last_tracks[guild_id]
                    
                # Limpa a mensagem de "agora tocando"
                if guild_id in self.now_playing_messages:
                    try:
                        msg_id, channel_id = self.now_playing_messages[guild_id]
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            try:
                                message = await channel.fetch_message(msg_id)
                                await message.edit(content="🚶 Bot desconectado do canal de voz.", embed=None, view=None)
                            except Exception as e:
                                logger.error(f"Erro ao atualizar mensagem 'agora tocando' para guild {guild_id}: {e}")
                    except Exception as e:
                        logger.error(f"Erro ao processar mensagem 'agora tocando' para guild {guild_id}: {e}")
                    
                    # Limpa a referência da mensagem
                    del self.now_playing_messages[guild_id]

def setup(bot: commands.Bot):
    bot.add_cog(Musica(bot))
