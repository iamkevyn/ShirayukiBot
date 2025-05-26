# /home/ubuntu/ShirayukiBot/cogs/Musica.py
# Cog de música para o bot Shirayuki usando Mafic (Lavalink) com integração Spotify

import asyncio
import datetime
import logging
import re
import time
import os # Usado para getenv
import random # Movido para o topo
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlparse, parse_qs

import mafic
import nextcord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from nextcord import Interaction, SlashOption, HTTPException, NotFound, Forbidden # Adicionado HTTPException, NotFound, Forbidden
from nextcord.ext import commands

# TODO: Verificar se todas as dependências (mafic, nextcord, spotipy) estão no requirements.txt/pyproject.toml com versões compatíveis.

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
    # TODO: Considerar usar bibliotecas de cache mais robustas como `cachetools` se necessário.
    def __init__(self):
        # Carrega configurações do cache do ambiente ou usa padrões
        try:
            # Tenta obter max_size do ambiente, default 100
            self.max_size = int(os.getenv("SPOTIFY_CACHE_MAX_SIZE", "100")) 
        except ValueError:
            logger.warning("Valor inválido para SPOTIFY_CACHE_MAX_SIZE, usando padrão 100.")
            self.max_size = 100
            
        try:
             # Tenta obter expiry_time do ambiente (em segundos), default 3600 (1 hora)
            self.expiry_time = int(os.getenv("SPOTIFY_CACHE_EXPIRY_TIME", "3600"))
        except ValueError:
            logger.warning("Valor inválido para SPOTIFY_CACHE_EXPIRY_TIME, usando padrão 3600.")
            self.expiry_time = 3600
            
        self.cache: Dict[str, Dict[str, Any]] = {}
        logger.info(f"SpotifyCache inicializado com max_size={self.max_size}, expiry_time={self.expiry_time}s")
        
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
    async def back(self, button: nextcord.ui.Button, interaction: Interaction)        """Volta para a música anterior (se houver histórico)."""
        guild_id = interaction.guild_id
        last_track = self.cog.last_tracks.get(guild_id)
        
        if last_track:
            # Toca a última música diretamente, sem modificar a fila principal
            # Nota: O comportamento anterior adicionava a música atual de volta à fila.
            # Se desejar esse comportamento, descomente as linhas abaixo e ajuste a lógica.
            # if self.player.current:
            #     queue = self.cog.get_queue(guild_id)
            #     queue.insert(0, self.player.current)
            
            try:
                # Para tocar a anterior, precisamos parar a atual e então tocar a anterior.
                # Mafic pode não ter um método direto para "play previous".
                # Uma abordagem é parar a atual e confiar que o on_track_end/start lidará com isso,
                # mas isso pode ser complexo. Tocar diretamente é mais simples.
                # Guardamos a faixa atual para potencialmente restaurar se necessário, mas por simplicidade, apenas tocamos a anterior.
                
                # Limpa a flag de 'current' temporariamente para evitar conflitos no on_track_end?
                # await self.player.stop() # Parar pode avançar a fila, não queremos isso.
                
                # Tenta tocar a faixa anterior diretamente
                await self.player.play(last_track, replace=True) # Usa replace=True para substituir a atual
                await interaction.response.send_message(f"{EMOJIS['back']} Voltando para: **{last_track.title}**", ephemeral=True)
                # A mensagem 'agora tocando' será atualizada pelo on_track_start
            except mafic.errors.MaficException as e:
                logger.error(f"Erro específico do Mafic ao voltar para música anterior: {e}", exc_info=True)
                await interaction.response.send_message(f"Erro ao voltar para música anterior (Mafic): {e}", ephemeral=True)
            except Exception as e:
                logger.error(f"Erro geral ao voltar para música anterior: {e}", exc_info=True)
                await interaction.response.send_message(f"Erro ao voltar para música anterior: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("Não há música anterior no histórico para voltar.", ephemeral=True)    
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
    
    @n    @nextcord.ui.button(emoji=EMOJIS["stop"], style=nextcord.ButtonStyle.danger, row=1)
    async def stop(self, button: nextcord.ui.Button, interaction: Interaction):
        """Para a reprodução, limpa a fila e desconecta o bot."""
        guild_id = interaction.guild_id
        
        # Verifica se o player existe e está conectado
        if not self.player or not self.player.connected:
            await interaction.response.send_message("O bot não está conectado ou tocando música.", ephemeral=True)
            return
            
        logger.info(f"Comando stop recebido para guild {guild_id}")
        
        # Limpa a fila personalizada primeiro
        if guild_id in self.cog.queues:
            self.cog.queues[guild_id].clear()
            logger.debug(f"Fila limpa para guild {guild_id}")
            
        # Para a música atual (isso deve disparar on_track_end)
        await self.player.stop()
        logger.debug(f"Player.stop() chamado para guild {guild_id}")
        
        # Desconecta do canal de voz
        try:
            # force=True garante a desconexão imediata.
            await self.player.disconnect(force=True)
            logger.info(f"Player desconectado (via botão stop) para guild {guild_id}")
        except mafic.errors.MaficException as e:
            logger.error(f"Erro específico do Mafic ao desconectar player (stop) para guild {guild_id}: {e}", exc_info=True)
            # Continua mesmo se a desconexão falhar, para tentar limpar estados
        except Exception as e:
            logger.error(f"Erro geral ao desconectar player (stop) para guild {guild_id}: {e}", exc_info=True)
            # Continua mesmo se a desconexão falhar

        # Limpa os estados da cog para esta guild explicitamente
        # Isso é uma garantia extra, caso o listener on_voice_state_update falhe ou atrase.
        self.cog.cleanup_guild_states(guild_id)
        logger.info(f"Estados da cog limpos (via botão stop) para guild {guild_id}")
            
        await interaction.response.send_message(f"{EMOJIS['stop']} Reprodução parada, fila limpa e bot desconectado!", ephemeral=True)
        # A mensagem 'agora tocando' deve ser limpa/atualizada pelo cleanup_guild_states ou on_voice_state_updatel=True)
    
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
        """Inicializa o cliente do Spotify, priorizando variáveis de ambiente."""
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        
        # Se não encontrar no ambiente, tenta carregar de um arquivo config.json na raiz do projeto
        # IMPORTANTE: Certifique-se de que config.json está no seu .gitignore!
        if not client_id or not client_secret:
            logger.info("Credenciais do Spotify não encontradas no ambiente. Tentando carregar de config.json...")
            try:
                # Assume que o script está em /cogs/Musica.py, então vai duas pastas acima para a raiz
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                config_path = os.path.join(base_dir, "config.json")
                
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                    spotify_config = config.get("spotify", {})
                    client_id = spotify_config.get("client_id")
                    client_secret = spotify_config.get("client_secret")
                    if client_id and client_secret:
                        logger.info("Credenciais do Spotify carregadas de config.json.")
                    else:
                        logger.warning("Credenciais do Spotify não encontradas ou incompletas em config.json.")
                else:
                    logger.warning(f"Arquivo config.json não encontrado em {config_path}.")
            except json.JSONDecodeError:
                logger.error(f"Erro ao decodificar {config_path}. Verifique se o JSON é válido.")
            except Exception as e:
                logger.error(f"Erro inesperado ao carregar config.json: {e}", exc_info=True)

        # Inicializa o cliente se as credenciais foram encontradas
        if client_id and client_secret:
            try:
                auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
                self.spotify = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("Cliente Spotipy inicializado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao inicializar cliente Spotipy: {e}", exc_info=True)
                self.spotify = None
        else:
            logger.warning("Credenciais do Spotify não configuradas. Funcionalidades do Spotify estarão desativadas.")
            self.spotify = None
                    auth_manager=SpotifyClientCredentials(
                        client_id=client_id,
                        client_secret=client_secret
                    )
                )
                logger.info("Cliente do Spotify inicializado com sucesso!")
            else:
                self.spotify = None
                logger.warning("Credenciais do Spotify não encontradas. Funcionalidades do Spotify estarão limitadas.")
        except Exception as e:
            self.spotify = None
            logger.error(f"Erro ao inicializar cliente do Spotify: {e}")
                async def initialize_mafic(self):
        """Inicializa o pool do Mafic quando o bot estiver pronto, usando variáveis de ambiente."""
        await self.bot.wait_until_ready()
        
        # Carrega configurações do Lavalink do ambiente ou usa padrões
        lavalink_host = os.getenv("LAVALINK_HOST", "127.0.0.1")
        lavalink_port_str = os.getenv("LAVALINK_PORT", "2333")
        lavalink_password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
        lavalink_label = os.getenv("LAVALINK_LABEL", "MAIN")
        lavalink_secure_str = os.getenv("LAVALINK_SECURE", "False")
        
        try:
            lavalink_port = int(lavalink_port_str)
        except ValueError:
            logger.error(f"Valor inválido para LAVALINK_PORT: 	{lavalink_port_str}. Usando padrão 2333.")
            lavalink_port = 2333
            
        lavalink_secure = lavalink_secure_str.lower() in ["true", "1", "yes"]
        
        logger.info(f"Tentando conectar ao nó Lavalink: Host={lavalink_host}, Port={lavalink_port}, Label={lavalink_label}, Secure={lavalink_secure}")
        
        try:
            # Cria o pool do Mafic
            self.bot.mafic_pool = mafic.NodePool(self.bot)
            
            # Adiciona o nó do Lavalink com configurações do ambiente
            await self.bot.mafic_pool.create_node(
                host=lavalink_host,
                port=lavalink_port,
                label=lavalink_label,
                password=lavalink_password,
                secure=lavalink_secure
            )
            
            logger.info(f"Nó Lavalink 	{lavalink_label} adicionado ao pool Mafic com sucesso.")
        except Exception as e:
            logger.error(f"Falha ao inicializar o pool Mafic ou conectar ao nó Lavalink: {e}", exc_info=True)           
    def get_queue(self, guild_id: int) -> List[mafic.Track]:
        """Obtém a fila personalizada para um servidor."""
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]
        
    def set_requester(self, guild_id: int, track: mafic.Track, requester: nextcord.Member):
        """Define o requester para uma faixa."""
        if guild_id not in self.track_requesters:
            self.track_requesters[guild_id] = {}
            
        # Usa o identificador da faixa como chave
        track_id = self.get_track_identifier(track)
        self.track_requesters[guild_id][track_id] = requester
        
    def get_requester(self, guild_id: int, track: mafic.Track) -> Optional[nextcord.Member]:
        """Obtém o requester para uma faixa."""
        if guild_id not in self.track_requesters:
            return None
            
        # Usa o identificador da faixa como chave
        track_id = self.get_track_identifier(track)
        return self.track_requesters[guild_id].get(track_id)
        
    def get_track_identifier(self, track: mafic.Track) -> str:
        """Obtém um identificador único para uma faixa."""
        # Usa uma combinação de título, autor e duração como identificador
        return f"{track.title}|{track.author}|{track.length}"
        
    def get_loop_state(self, guild_id: int) -> str:
        """Obtém o estado de loop para um servidor."""
        return self.loop_states.get(guild_id, "none")
        
    def set_loop_state(self, guild_id: int, state: str):
        """Define o estado de loop para um servidor."""
        self.loop_states[guild_id] = state
    
    def get_autoplay_state(self, guild_id: int) -> bool:
        """Obtém o estado de autoplay para um servidor."""
        return self.autoplay_states.get(guild_id, False)
    
    def set_autoplay_state(self, guild_id: int, state: bool):
        """Define o estado de autoplay para um servidor."""
        self.autoplay_states[guild_id] = state
    
    def format_duration(self, ms: int) -> str:
        """Formata a duração em milissegundos para um formato legível."""
        seconds = ms // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    async def get_player_volume(self, player: mafic.Player) -> int:
        """Obtém o volume atual do player de forma segura."""
        try:
            # Tenta obter o volume do player
            volume = await player.fetch_volume()
            return volume
        except Exception as e:
            logger.error(f"Erro ao obter volume do player: {e}")
            return 70  # Valor padrão
    
    async def set_player_volume(self, player: mafic.Player, volume: int):
        """Define o volume do player."""
        try:
            await player.set_volume(volume)
        except Exception as e:
            logger.error(f"Erro ao definir volume do player: {e}")
    
    async def create_now_playing_panel_for_track(self, channel, player, track):
        """Cria um painel de 'agora tocando' para uma faixa."""
        guild_id = channel.guild.id
        
        # Obtém o requester da faixa
        requester = self.get_requester(guild_id, track)
        requester_mention = requester.mention if requester else "Desconhecido"
        
        # Cria o embed
        embed = nextcord.Embed(
            title=f"{EMOJIS['music']} Agora Tocando",
            description=f"**[{track.title}]({track.uri})**",
            color=nextcord.Color.purple()
        )
        
        # Adiciona informações da faixa
        embed.add_field(name="Duração", value=self.format_duration(track.length), inline=True)
        embed.add_field(name="Adicionado por", value=requester_mention, inline=True)
        
        # Adiciona informações do autor
        embed.add_field(name="Autor", value=track.author, inline=True)
        
        # Adiciona informações adicionais
        loop_status = "Desativado"
        loop_state = self.get_loop_state(guild_id)
        if loop_state == "track": loop_status = "Faixa"
        elif loop_state == "queue": loop_status = "Fila"
        
        # Obtém o volume de forma segura
        volume = await self.get_player_volume(player)
        
        embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Autoplay: {'Ativado' if self.get_autoplay_state(guild_id) else 'Desativado'}")
        
        # Adiciona a miniatura se disponível
        if hasattr(track, 'thumbnail') and track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        
        # Cria os controles de música
        view = MusicControls(player, self)
        
        # Envia a mensagem
        message = await channel.send(embed=embed, view=view)
        
        # Armazena a mensagem para atualizações futuras
        self.now_playing_messages[guild_id] = (message.id, channel.id)
        
        return message
    
    async def update_now_playing_message(self, player):
        """Atualiza a mensagem de 'agora tocando'."""
        if not player or not player.guild_id:
            return
            
        guild_id = player.guild_id
        
        # Verifica se existe uma mensagem para atualizar
        if guild_id not in self.now_playing_messages:
            return
            
        message_id, channel_id = self.now_playing_messages[guild_id]
        
        # Obtém o canal
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
            
        try:
            # Obtém a mensagem
            message = await channel.fetch_message(message_id)
            if not message:
                return
                
            # Atualiza o embed
            if player.current:
                # Obtém o requester da faixa
                requester = self.get_requester(guild_id, player.current)
                requester_mention = requester.mention if requester else "Desconhecido"
                
                # Cria o embed
                embed = nextcord.Embed(
                    title=f"{EMOJIS['music']} Agora Tocando",
                    description=f"**[{player.current.title}]({player.current.uri})**",
                    color=nextcord.Color.purple()
                )
                
                # Adiciona informações da faixa
                embed.add_field(name="Duração", value=self.format_duration(player.current.length), inline=True)
                embed.add_field(name="Adicionado por", value=requester_mention, inline=True)
                
                # Adiciona informações do autor
                embed.add_field(name="Autor", value=player.current.author, inline=True)
                
                # Adiciona informações adicionais
                loop_status = "Desativado"
                loop_state = self.get_loop_state(guild_id)
                if loop_state == "track": loop_status = "Faixa"
                elif loop_state == "queue": loop_status = "Fila"
                
                # Obtém o volume de forma segura
                volume = await self.get_player_volume(player)
                
                embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Autoplay: {'Ativado' if self.get_autoplay_state(guild_id) else 'Desativado'} | Status: {'Pausado' if player.paused else 'Tocando'}")
                
                # Adiciona a miniatura se disponível
                if hasattr(player.current, 'thumbnail') and player.current.thumbnail:
                    embed.set_thumbnail(url=player.current.thumbnail)
                
                # Atualiza a mensagem
                await message.edit(embed=embed)
            else:
                # Se não houver música tocando, atualiza para um embed vazio
                embed = nextcord.Embed(
                    title=f"{EMOJIS['music']} Nada Tocando",
                    description="A fila está vazia. Adicione músicas com `/tocar`!",
                    color=nextcord.Color.purple()
                )
                
                await message.edit(embed=embed)
            except nextcord.NotFound:
                logger.warning(f"Mensagem de 'agora tocando' não encontrada para guild {guild_id}. Removendo referência.")
                del self.now_playing_messages[guild_id]
            except nextcord.Forbidden:
                logger.error(f"Sem permissão para editar a mensagem de 'agora tocando' para guild {guild_id}.")
            except Exception as e:
                logger.error(f"Erro inesperado ao atualizar mensagem de 'agora tocando': {e}", exc_info=True)
    
    async def process_spotify_url(self, interaction: Interaction, url: str):
        """Processa um URL do Spotify."""
        await interaction.response.defer(ephemeral=True)
        
        if not self.spotify:
            await interaction.followup.send("Integração com Spotify não está disponível no momento.", ephemeral=True)
            return
            
        # Extrai o tipo e ID do URL
        match = SPOTIFY_URL_REGEX.match(url)
        if not match:
            await interaction.followup.send("URL do Spotify inválido.", ephemeral=True)
            return
            
        spotify_type = match.group(3)  # track, album ou playlist
        spotify_id = match.group(4)
        
        # Verifica se o resultado está em cache
        cache_key = f"{spotify_type}:{spotify_id}"
        cached_result = self.spotify_cache.get(cache_key)
        
        if cached_result:
            logger.info(f"Usando resultado em cache para {cache_key}")
            tracks_info = cached_result
        else:
            # Busca as informações no Spotify
            try:
                if spotify_type == "track":
                    # Busca informações da faixa
                    track = self.spotify.track(spotify_id)
                    tracks_info = [{
                        "name": track["name"],
                        "artists": [artist["name"] for artist in track["artists"]],
                        "duration_ms": track["duration_ms"],
                        "url": track["external_urls"]["spotify"],
                        "album": track["album"]["name"],
                        "album_art": track["album"]["images"][0]["url"] if track["album"]["images"] else None
                    }]
                elif spotify_type == "album":
                    # Busca informações do álbum
                    album = self.spotify.album(spotify_id)
                    tracks = self.spotify.album_tracks(spotify_id)
                    
                    tracks_info = []
                    for track in tracks["items"]:
                        tracks_info.append({
                            "name": track["name"],
                            "artists": [artist["name"] for artist in track["artists"]],
                            "duration_ms": track["duration_ms"],
                            "url": track["external_urls"]["spotify"],
                            "album": album["name"],
                            "album_art": album["images"][0]["url"] if album["images"] else None
                        })
                elif spotify_type == "playlist":
                    # Busca informações da playlist
                    playlist = self.spotify.playlist(spotify_id)
                    tracks = self.spotify.playlist_tracks(spotify_id)
                    
                    tracks_info = []
                    for item in tracks["items"]:
                        track = item["track"]
                        if track:  # Algumas playlists podem ter itens nulos
                            tracks_info.append({
                                "name": track["name"],
                                "artists": [artist["name"] for artist in track["artists"]],
                                "duration_ms": track["duration_ms"],
                                "url": track["external_urls"]["spotify"],
                                "album": track["album"]["name"] if "album" in track else "Unknown",
                                "album_art": track["album"]["images"][0]["url"] if "album" in track and track["album"]["images"] else None
                            })
                
                # Armazena o resultado em cache
                self.spotify_cache.set(cache_key, tracks_info)
            except spotipy.SpotifyException as e: # Captura exceção específica do Spotipy
                logger.error(f"Erro ao buscar informações do Spotify: {e}", exc_info=True)
                await interaction.followup.send(f"Erro ao buscar informações do Spotify: {e}", ephemeral=True)
                return
            except Exception as e: # Captura outras exceções inesperadas
                logger.error(f"Erro inesperado ao processar Spotify: {e}", exc_info=True)
                await interaction.followup.send("Ocorreu um erro inesperado ao processar a solicitação do Spotify.", ephemeral=True)
                return
        
        # Verifica se encontrou faixas
        if not tracks_info:
            await interaction.followup.send("Nenhuma faixa encontrada no Spotify.", ephemeral=True)
            return
            
        # Envia mensagem de confirmação
        await interaction.followup.send(
            f"{EMOJIS['spotify']} Processando {len(tracks_info)} faixa(s) do Spotify...",
            ephemeral=True
        )
        
        # Obtém ou cria um player para este servidor
        try:
            voice_channel = interaction.user.voice.channel
            
            # Verifica se já existe um player para este servidor
            if interaction.guild_id in self.players:
                player = self.players[interaction.guild_id]
                
                # Se o player não estiver conectado, conecta ao canal de voz
                if not player.connected:
                    await player.connect(voice_channel.id)
            else:
                # Cria um novo player e conecta ao canal de voz
                # Usando create_session em vez de create_player para compatibilidade com versões mais recentes do Mafic
                node = self.bot.mafic_pool.get_node()
                player = await node.create_session(interaction.guild_id, voice_channel.id)
                self.players[interaction.guild_id] = player
                
                # Define o volume padrão
                await self.set_player_volume(player, 70)
                
            logger.info(f"Player conectado ao canal de voz {voice_channel.name} em {interaction.guild.name}")
        except Exception as e:
            logger.error(f"Erro ao conectar ao canal de voz: {e}", exc_info=True)
            await interaction.channel.send(f"Erro ao conectar ao canal de voz: {e}")
            return
            
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(interaction.guild_id)
        
        # Cria o painel estilizado ANTES de adicionar à fila
        if player.current:
            # Se já está tocando algo, atualizamos o painel existente
            await self.update_now_playing_mess            # Adiciona as faixas à fila
            added_tracks = 0
            for track_info in tracks_info:
                # Cria uma consulta para o YouTube com o nome da faixa e artistas
                # ATENÇÃO: Usar ytsearch para faixas do Spotify é uma aproximação e pode
                # resultar em faixas incorretas sendo tocadas, especialmente para remixes
                # ou versões diferentes. Não há garantia de que será a mesma faixa do Spotify.
                artists_str = ", ".join(track_info["artists"])
                search_query = f"ytsearch:{track_info['name']} {artists_str}"          
            try:
                # Busca a faixa no YouTube
                search_results = await player.fetch_tracks(search_query)
                
                if search_results:
                    # Pega o primeiro resultado
                    track = search_results[0] if isinstance(search_results, list) else search_results
                    
                    # Define o requester
                    self.set_requester(interaction.guild_id, track, interaction.user)
                    
                    # Adiciona à fila
                    queue.append(track)
                    added_tracks += 1
                    
                    # Se for a primeira faixa e não estiver tocando nada, cria o painel
                    if added_tracks == 1 and not player.current and not player.paused:
                        await self.create_now_playing_panel_for_track(interaction.channel, player, track)
            except Exception as e:
                logger.error(f"Erro ao buscar faixa '{track_info['name']}': {e}")
                continue
        
        # Envia mensagem de confirmação
        if added_tracks > 0:
            await interaction.channel.send(f"{EMOJIS['spotify']} **{added_tracks} faixa(s)** do Spotify adicionada(s) à fila!")
        else:
            await interaction.channel.send("Não foi possível adicionar nenhuma faixa do Spotify à fila.")
    
    @nextcord.slash_command(
        name="tocar",
        description="Toca uma música a partir de um termo de busca ou URL"
    )
    async def play(
        self,
        interaction: Interaction,
        query: str = SlashOption(
            name="busca",
            description="Termo de busca ou URL (YouTube, SoundCloud, Spotify, etc.)",
            required=True
        )
    ):
        """Toca uma música a partir de um termo de busca ou URL."""
        await interaction.response.defer(ephemeral=True)
        
        # Verifica se o usuário está em um canal de voz
        if not interaction.user.voice:
            await interaction.followup.send("Você precisa estar em um canal de voz para usar este comando.", ephemeral=True)
            return
            
        voice_channel = interaction.user.voice.channel
        
        # Verifica se o bot tem permissão para entrar no canal de voz
        permissions = voice_channel.permissions_for(interaction.guild.me)
        if not permissions.connect or not permissions.speak:
            await interaction.followup.send("Não tenho permissão para entrar ou falar no seu canal de voz.", ephemeral=True)
            return
            
        # Verifica se a query é válida
        if not query:
            await interaction.followup.send("Por favor, forneça um termo de busca ou URL válido.", ephemeral=True)
            return
            
        # Verifica se é um URL do Spotify
        spotify_match = SPOTIFY_URL_REGEX.match(query)
        if spotify_match and self.spotify:
            # Processa URL do Spotify
            await self.process_spotify_url(interaction, query)
            return
            
        # Verifica se é um URL ou um termo de busca
        if URL_REGEX.match(query):
            search_query = query
        elif SEARCH_TERM_REGEX.match(query):
            search_query = f"ytsearch:{query}"
        else:
            await interaction.followup.send("Por favor, forneça um termo de busca ou URL válido.", ephemeral=True)
            return
            
        # Obtém ou cria um player para este servidor
        try:
            # Verifica se já existe um player para este servidor
            if interaction.guild_id in self.players:
                player = self.players[interaction.guild_id]
                
                # Se o player não estiver conectado, conecta ao canal de voz
                if not player.connected:
                    await player.connect(voice_channel.id)
            else:
                # Cria um novo player e conecta ao canal de voz
                # Usando create_session em vez de create_player para compatibilidade com versões mais recentes do Mafic
                node = self.bot.mafic_pool.get_node()
                player = await node.create_session(interaction.guild_id, voice_channel.id)
                self.players[interaction.guild_id] = player
                
                # Define o volume padrão
                await self.set_player_volume(player, 70)
                
            logger.info(f"Player conectado ao canal de voz {voice_channel.name} em {interaction.guild.name}")
        except Exception as e:
            logger.error(f"Erro ao conectar ao canal de voz: {e}", exc_info=True)
            await interaction.followup.send(f"Erro ao conectar ao canal de voz: {e}", ephemeral=True)
            return
            
        # Busca a música
        try:
            tracks = await player.fetch_tracks(search_query)
            
            if not tracks:
                await interaction.followup.send("Nenhuma música encontrada com esse termo de busca ou URL.", ephemeral=True)
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
                # Se for uma playlist, adiciona todas as faixas à fila
                for track in tracks:
                    self.set_requester(interaction.guild_id, track, interaction.user)
                queue.extend(tracks)
                added_to_queue_count = len(tracks)
                
                # Envia mensagem de confirmação
                await interaction.followup.send(f"{EMOJIS['playlist']} **{added_to_queue_count} música(s)** adicionada(s) à fila!")
            else:
                # Se for uma única faixa, adiciona à fila
                self.set_requester(interaction.guild_id, tracks, interaction.user)
                queue.append(tracks)
                added_to_queue_count = 1
                
                # Envia mensagem de confirmação
                await interaction.followup.send(f"{EMOJIS['music']} **{tracks.title}** adicionada à fila!")
            
            # Se não estiver tocando nada, inicia a reprodução
            if not player.current and not player.paused:
                # Pega a primeira música da fila
                if queue:
                    track = queue.pop(0)
                    await player.play(track)
                    logger.info(f"Iniciando reprodução de {track.title} em {interaction.guild.name}")
        except Exception as e:
            logger.error(f"Erro ao buscar música: {e}", exc_info=True)
            await interaction.followup.send(f"Erro ao buscar música: {e}", ephemeral=True)
    
    @nextcord.slash_command(
        name="fila",
        description="Mostra a fila de músicas atual"
    )
    async def queue(self, interaction: Interaction):
        """Mostra a fila de músicas atual."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(guild_id)

        embed = nextcord.Embed(
            title=f"{EMOJIS['music']} Fila de Músicas",
            color=nextcord.Color.purple()
        )

        # Informações da música atual
        if player.current:
            # Obtém o requester da faixa atual
            requester = self.get_requester(guild_id, player.current)
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
                requester = self.get_requester(guild_id, track)
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
        loop_state = self.get_loop_state(guild_id)
        if loop_state == "track": loop_status = "Faixa"
        elif loop_state == "queue": loop_status = "Fila"
        
        # Obtém o volume de forma segura
        volume = await self.get_player_volume(player)
        
        embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Status: {'Pausado' if player.paused else 'Tocando'}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @nextcord.slash_command(
        name="pausar",
        description="Pausa a música atual"
    )
    async def pause(self, interaction: Interaction):
        """Pausa a música atual."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        if not player.current:
            await interaction.followup.send("Não há música tocando no momento.", ephemeral=True)
            return
            
        if player.paused:
            await interaction.followup.send("A música já está pausada.", ephemeral=True)
            return
            
        await player.pause()
        await interaction.followup.send(f"{EMOJIS['pause']} Música pausada!")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
    
    @nextcord.slash_command(
        name="retomar",
        description="Retoma a reprodução da música pausada"
    )
    async def resume(self, interaction: Interaction):
        """Retoma a reprodução da música pausada."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        if not player.current:
            await interaction.followup.send("Não há música tocando no momento.", ephemeral=True)
            return
            
        if not player.paused:
            await interaction.followup.send("A música já está tocando.", ephemeral=True)
            return
            
        await player.resume()
        await interaction.followup.send(f"{EMOJIS['play']} Música retomada!")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
    
    @nextcord.slash_command(
        name="pular",
        description="Pula para a próxima música na fila"
    )
    async def skip(self, interaction: Interaction):
        """Pula para a próxima música na fila."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        if not player.current:
            await interaction.followup.send("Não há música tocando no momento.", ephemeral=True)
            return
            
        await player.stop()  # Mafic lida com a próxima música da fila automaticamente
        await interaction.followup.send(f"{EMOJIS['skip']} Música pulada!")
    
    @nextcord.slash_command(
        name="parar",
        description="Para a reprodução e limpa a fila"
    )
    async def stop(self, interaction: Interaction):
        """Para a reprodução e limpa a fila."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Limpa a fila personalizada
        if guild_id in self.queues:
            self.queues[guild_id].clear()
            
        await player.stop()  # Para a música atual
        
        try:
            await player.disconnect(force=True)  # Desconecta do canal de voz
        except Exception as e:
            logger.error(f"Erro ao desconectar player para guild {guild_id}: {e}")

        # Remove o player da lista
        if guild_id in self.players:
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
            
        # Limpa a última música tocada
        if guild_id in self.last_tracks:
            del self.last_tracks[guild_id]
            
        # Limpa a mensagem de "agora tocando"
        if guild_id in self.now_playing_messages:
            del self.now_playing_messages[guild_id]
            
        await interaction.followup.send(f"{EMOJIS['stop']} Reprodução parada e fila limpa!")
    
    @nextcord.slash_command(
        name="volume",
        description="Ajusta o volume da reprodução"
    )
    async def volume(
        self,
        interaction: Interaction,
        volume: int = SlashOption(
            name="volume",
            description="Volume (0-100)",
            required=True,
            min_value=0,
            max_value=100
        )
    ):
        """Ajusta o volume da reprodução."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Define o volume
        await self.set_player_volume(player, volume)
        
        # Envia mensagem de confirmação
        if volume == 0:
            await interaction.followup.send(f"{EMOJIS['volume_down']} Volume definido para {volume}% (mudo).")
        elif volume <= 30:
            await interaction.followup.send(f"{EMOJIS['volume_down']} Volume definido para {volume}%.")
        elif volume <= 70:
            await interaction.followup.send(f"{EMOJIS['volume_up']} Volume definido para {volume}%.")
        else:
            await interaction.followup.send(f"{EMOJIS['volume_up']} Volume definido para {volume}%.")
            
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
    
    @nextcord.slash_command(
        name="loop",
        description="Alterna entre os modos de loop (desativado, faixa, fila)"
    )
    async def loop(
        self,
        interaction: Interaction,
        mode: str = SlashOption(
            name="modo",
            description="Modo de loop",
            required=True,
            choices={"Desativado": "none", "Faixa": "track", "Fila": "queue"}
        )
    ):
        """Alterna entre os modos de loop (desativado, faixa, fila)."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Define o estado de loop
        self.set_loop_state(guild_id, mode)
        
        # Envia mensagem de confirmação
        if mode == "none":
            await interaction.followup.send(f"{EMOJIS['loop']} Loop desativado!")
        elif mode == "track":
            await interaction.followup.send(f"{EMOJIS['loop']} Loop ativado para a faixa atual!")
        elif mode == "queue":
            await interaction.followup.send(f"{EMOJIS['loop']} Loop ativado para toda a fila!")
            
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
    
    @nextcord.slash_command(
        name="embaralhar",
        description="Embaralha a fila de músicas"
    )
    async def shuffle(self, interaction: Interaction):
        """Embaralha a fila de músicas."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(guild_id)
        
        if len(queue) <= 1:
            await interaction.followup.send("Não há músicas suficientes na fila para embaralhar.", ephemeral=True)
            return
            
        # Embaralha a fila
        import random
        random.shuffle(queue)
        
        await interaction.followup.send(f"{EMOJIS['shuffle']} Fila embaralhada! Use `/fila` para ver a nova ordem.")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
    
    @nextcord.slash_command(
        name="autoplay",
        description="Ativa ou desativa o autoplay"
    )
    async def autoplay(
        self,
        interaction: Interaction,
        estado: bool = SlashOption(
            name="estado",
            description="Estado do autoplay",
            required=True,
            choices={"Ativado": True, "Desativado": False}
        )
    ):
        """Ativa ou desativa o autoplay."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Define o estado de autoplay
        self.set_autoplay_state(guild_id, estado)
        
        # Envia mensagem de confirmação
        if estado:
            await interaction.followup.send(f"{EMOJIS['autoplay']} Autoplay ativado! Músicas relacionadas serão adicionadas automaticamente.")
        else:
            await interaction.followup.send(f"{EMOJIS['autoplay']} Autoplay desativado!")
            
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
    
    @nextcord.slash_command(
        name="remover",
        description="Remove uma música específica da fila"
    )
    async def remove(
        self,
        interaction: Interaction,
        posicao: int = SlashOption(
            name="posicao",
            description="Posição da música na fila (começando em 1)",
            required=True,
            min_value=1
        )
    ):
        """Remove uma música específica da fila."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(guild_id)
        
        # Verifica se a posição é válida
        if posicao > len(queue):
            await interaction.followup.send(f"Posição inválida. A fila tem apenas {len(queue)} música(s).", ephemeral=True)
            return
            
        # Remove a música da fila
        index = posicao - 1
        removed_track = queue.pop(index)
        
        await interaction.followup.send(f"{EMOJIS['music']} **{removed_track.title}** removida da fila.")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
    
    @nextcord.slash_command(
        name="limpar",
        description="Limpa a fila de músicas"
    )
    async def clear(self, interaction: Interaction):
        """Limpa a fila de músicas."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(guild_id)
        
        # Verifica se a fila está vazia
        if not queue:
            await interaction.followup.send("A fila já está vazia.", ephemeral=True)
            return
            
        # Limpa a fila
        queue_size = len(queue)
        queue.clear()
        
        await interaction.followup.send(f"{EMOJIS['playlist']} Fila limpa! {queue_size} música(s) removida(s).")
        
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
    
    @nextcord.slash_command(
        name="agora",
        description="Mostra informações sobre a música atual"
    )
    async def now(self, interaction: Interaction):
        """Mostra informações sobre a música atual."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        if not guild_id or guild_id not in self.players:
            await interaction.followup.send("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[guild_id]
        if not player.connected:
            await interaction.followup.send("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return
            
        if not player.current:
            await interaction.followup.send("Não há música tocando no momento.", ephemeral=True)
            return
            
        # Obtém o requester da faixa atual
        requester = self.get_requester(guild_id, player.current)
        requester_mention = requester.mention if requester else "Desconhecido"
        
        # Cria o embed
        embed = nextcord.Embed(
            title=f"{EMOJIS['music']} Agora Tocando",
            description=f"**[{player.current.title}]({player.current.uri})**",
            color=nextcord.Color.purple()
        )
        
        # Adiciona informações da faixa
        embed.add_field(name="Duração", value=self.format_duration(player.current.length), inline=True)
        embed.add_field(name="Adicionado por", value=requester_mention, inline=True)
        
        # Adiciona informações do autor
        embed.add_field(name="Autor", value=player.current.author, inline=True)
        
        # Adiciona informações adicionais
        loop_status = "Desativado"
        loop_state = self.get_loop_state(guild_id)
        if loop_state == "track": loop_status = "Faixa"
        elif loop_state == "queue": loop_status = "Fila"
        
        # Obtém o volume de forma segura
        volume = await self.get_player_volume(player)
        
        embed.set_footer(text=f"Volume: {volume}% | Loop: {loop_status} | Autoplay: {'Ativado' if self.get_autoplay_state(guild_id) else 'Desativado'} | Status: {'Pausado' if player.paused else 'Tocando'}")
        
        # Adiciona a miniatura se disponível
        if hasattr(player.current, 'thumbnail') and player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)
            
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_track_start(self, player: mafic.Player, track: mafic.Track):
        """Evento disparado quando uma faixa começa a tocar."""
        if not player or not player.guild_id:
            return
            
        guild_id = player.guild_id
        
        # Armazena a última música tocada
        if player.current and player.current != track:
            self.last_tracks[guild_id] = player.current
            
        # Atualiza a mensagem de "agora tocando"
        await self.update_now_playing_message(player)
        
        logger.info(f"Iniciando reprodução de {track.title} em {guild_id}")
    
    @commands.Cog.listener()
    async def on_track_end(self, player: mafic.Player, track: mafic.Track, reason: str):
        """Evento disparado quando uma faixa termina de tocar."""
        if not player or not player.guild_id:
            return
            
        guild_id = player.guild_id
        
        # Verifica o estado de loop
        loop_state = self.get_loop_state(guild_id)
        
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(guild_id)
        
        # Lógica de loop
        if loop_state == "track" and reason != "REPLACED":
            # Loop de faixa: adiciona a mesma faixa de volta à fila (no início)
            queue.insert(0, track)
        elif loop_state == "queue" and reason != "REPLACED":
            # Loop de fila: adiciona a faixa ao final da fila
            queue.append(track)
            
        # Verifica se há mais músicas na fila
        if queue:
            # Pega a próxima música da fila
            next_track = queue.pop(0)
            
            try:
                # Toca a próxima música
                await player.play(next_track)
                logger.info(f"Tocando próxima música da fila: {next_track.title} em {guild_id}")
            except Exception as e:
                logger.error(f"Erro ao tocar próxima música: {e}")
                
                # Tenta tocar a próxima música da fila, se houver
                if queue:
                    try:
                        next_track = queue.pop(0)
                        await player.play(next_track)
                    except Exception as e2:
                        logger.error(f"Erro ao tocar música alternativa: {e2}")
        elif self.get_autoplay_state(guild_id) and track.uri:
            # Se autoplay estiver ativado e não houver mais músicas na fila, busca músicas relacionadas
            try:
                # Busca músicas relacionadas
                related_tracks = await player.fetch_tracks(f"ytsearch:related:{track.title} {track.author}")
                
                if related_tracks and isinstance(related_tracks, list) and len(related_tracks) > 0:
                    # Filtra para evitar repetir a mesma música
                    filtered_tracks = [t for t in related_tracks if t.identifier != track.identifier]
                    
                    if filtered_tracks:
                        # Pega uma música aleatória da lista
                        import random
                        next_track = random.choice(filtered_tracks)
                        
                        # Define o requester como o bot
                        guild = self.bot.get_guild(guild_id)
                        if guild:
                            self.set_requester(guild_id, next_track, guild.me)
                        
                        # Toca a música relacionada
                        await player.play(next_track)
                        
                        # Obtém o canal para enviar a mensagem
                        if guild_id in self.now_playing_messages:
                            _, channel_id = self.now_playing_messages[guild_id]
                            channel = self.bot.get_channel(channel_id)
                            
                            if channel:
                                await channel.send(f"{EMOJIS['autoplay']} Autoplay: Tocando música relacionada **{next_track.title}**")
                        
                        logger.info(f"Autoplay: Tocando música relacionada {next_track.title} em {guild_id}")
            except Exception as e:
                logger.error(f"Erro no autoplay: {e}")
        else:
            # Se não houver mais músicas na fila e autoplay estiver desativado, atualiza a mensagem
            await self.update_now_playing_message(player)
            
            # Verifica se deve desconectar após um tempo
            if not player.current and not player.paused:
                # Agenda a desconexão após 5 minutos de inatividade
                await asyncio.sleep(300)  # 5 minutos
                
                # Verifica novamente se ainda não está tocando nada
                if player.guild_id == guild_id and not player.current and not player.paused and not self.get_queue(guild_id):
                    try:
                        await player.disconnect(force=True)
                        
                        # Remove o player da lista
                        if guild_id in self.players:
                            del self.players[guild_id]
                            
                        logger.info(f"Player desconectado por inatividade em {guild_id}")
                    except Exception as e:
                        logger.error(f"Erro ao desconectar player por inatividade: {e}")
    
    @commands.Cog.listener()
    async def on_track_exception(self, player: mafic.Player, track: mafic.Track, exception: Exception):
        """Evento disparado quando ocorre um erro ao tocar uma faixa."""
        if not player or not player.guild_id:
            return
            
        guild_id = player.guild_id
        
        logger.error(f"Erro ao tocar {track.title} em {guild_id}: {exception}")
        
        # Obtém o canal para enviar a mensagem
        if guild_id in self.now_playing_messages:
            _, channel_id = self.now_playing_messages[guild_id]
            channel = self.bot.get_channel(channel_id)
            
            if channel:
                await channel.send(f"Erro ao tocar **{track.title}**: {exception}")
        
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(guild_id)
        
        # Verifica se há mais músicas na fila
        if queue:
            # Pega a próxima música da fila
            next_track = queue.pop(0)
            
            try:
                # Toca a próxima música
                await player.play(next_track)
                logger.info(f"Tocando próxima música da fila após erro: {next_track.title} em {guild_id}")
            except Exception as e:
                logger.error(f"Erro ao tocar próxima música após erro: {e}")
    
    @commands.Cog.listener()
    async def on_node_ready(self, node: mafic.Node):
        """Evento disparado quando um nó do Lavalink está pronto."""
        logger.info(f"Nó Lavalink {node.label} está pronto!")
    
    @commands.Cog.listener()
    async def on_node_unavailable(self, node: mafic.Node):
        """Evento disparado quando um nó do Lavalink fica indisponível."""
        logger.warning(f"Nó Lavalink {node.label} ficou indisponível!")
    
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
    
    async def get_or_create_player(self, interaction: Interaction) -> Optional[mafic.Player]:
        """Obtém ou cria um player para o servidor."""
        # Verifica se o usuário está em um canal de voz
        if not interaction.user.voice:
            await interaction.followup.send("Você precisa estar em um canal de voz para usar este comando.", ephemeral=True)
            return None
            
        voice_channel = interaction.user.voice.channel
        
        # Verifica se o bot tem permissão para entrar no canal de voz
        permissions = voice_channel.permissions_for(interaction.guild.me)
        if not permissions.connect or not permissions.speak:
            await interaction.followup.send("Não tenho permissão para entrar ou falar no seu canal de voz.", ephemeral=True)
            return None
            
        try:
            # Verifica se já existe um player para este servidor
            if interaction.guild_id in self.players:
                player = self.players[interaction.guild_id]
                
                # Se o player não estiver conectado, conecta ao canal de voz
                if not player.connected:
                    await player.connect(voice_channel.id)
            else:
                # Cria um novo player e conecta ao canal de voz
                # Usando create_session em vez de create_player para compatibilidade com versões mais recentes do Mafic
                node = self.bot.mafic_pool.get_node()
                player = await node.create_session(interaction.guild_id, voice_channel.id)
                self.players[interaction.guild_id] = player
                
                # Define o volume padrão
                await self.set_player_volume(player, 70)
                
            logger.info(f"Player conectado ao canal de voz {voice_channel.name} em {interaction.guild.name}")
            return player
        except Exception as e:
            logger.error(f"Erro ao conectar ao canal de voz: {e}", exc_info=True)
            await interaction.followup.send(f"Erro ao conectar ao canal de voz: {e}", ephemeral=True)
            return None

def setup(bot: commands.Bot):
    bot.add_cog(Musica(bot))


    def cleanup_guild_states(self, guild_id: int):
        """Limpa todos os estados armazenados para uma guild específica."""
        logger.debug(f"Iniciando limpeza de estados para guild {guild_id}")
        
        # Remove o player da lista
        if guild_id in self.players:
            del self.players[guild_id]
            logger.debug(f"Player removido para guild {guild_id}")
        
        # Limpa o dicionário de requesters
        if guild_id in self.track_requesters:
            del self.track_requesters[guild_id]
            logger.debug(f"Requesters limpos para guild {guild_id}")
        
        # Limpa a fila personalizada
        if guild_id in self.queues:
            del self.queues[guild_id]
            logger.debug(f"Fila limpa para guild {guild_id}")
            
        # Limpa o estado de loop
        if guild_id in self.loop_states:
            del self.loop_states[guild_id]
            logger.debug(f"Estado de loop limpo para guild {guild_id}")
            
        # Limpa o estado de autoplay
        if guild_id in self.autoplay_states:
            del self.autoplay_states[guild_id]
            logger.debug(f"Estado de autoplay limpo para guild {guild_id}")
            
        # Limpa a última música tocada
        if guild_id in self.last_tracks:
            del self.last_tracks[guild_id]
            logger.debug(f"Histórico de última música limpo para guild {guild_id}")
            
        # Limpa a mensagem de "agora tocando"
        if guild_id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[guild_id]
                # Não tenta editar a mensagem aqui, apenas remove a referência
                # A edição pode ser feita no on_voice_state_update ou no comando stop
            except Exception as e:
                logger.error(f"Erro ao processar referência da mensagem 'agora tocando' durante limpeza para guild {guild_id}: {e}")
            finally:
                del self.now_playing_messages[guild_id]
                logger.debug(f"Referência da mensagem 'agora tocando' limpa para guild {guild_id}")
                
        logger.info(f"Limpeza de estados concluída para guild {guild_id}")

    # --- Cog Unload --- 
    async def cog_unload(self):
        """Limpa recursos quando a cog é descarregada."""
        logger.info("Descarregando a cog Musica...")
        # Cria uma cópia das chaves dos players para iterar, pois o dicionário será modificado
        active_guild_ids = list(self.players.keys())
        
        for guild_id in active_guild_ids:
            player = self.players.get(guild_id)
            if player and player.connected:
                try:
                    logger.info(f"Desconectando player da guild {guild_id} durante o unload da cog.")
                    await player.disconnect(force=True)
                except Exception as e:
                    logger.error(f"Erro ao desconectar player da guild {guild_id} durante o unload: {e}", exc_info=True)
            # Limpa os estados independentemente de ter conseguido desconectar
            self.cleanup_guild_states(guild_id)
            
        logger.info("Cog Musica descarregada com sucesso.")
