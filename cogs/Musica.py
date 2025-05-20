# /home/ubuntu/ShirayukiBot/cogs/Musica.py
# Cog de Música reescrita para usar Mafic com painel estilizado

import nextcord
from nextcord import Interaction, SlashOption, ChannelType
from nextcord.ext import commands
import mafic
import logging
import asyncio
import re
from typing import Optional, List, Union, Dict
from collections import deque

logger = logging.getLogger("discord_bot.musica_mafic")

# Regex para validar URLs do YouTube e Soundcloud, e termos de busca
URL_REGEX = re.compile(
    r"^(?:(?:https?:)?//)?(?:www\.)?"
    r"(?:(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/|playlist\?list=))"
    r"|(?:youtu\.be/)|(?:soundcloud\.com/[^/]+(?:/(?:sets/)?/[^/]+)?))"
    r"([a-zA-Z0-9_-]+)"
)
SEARCH_TERM_REGEX = re.compile(r"^.{3,500}$") # Termos de busca genéricos

# Emojis estilizados para o player (vermelho e branco)
EMOJIS = {
    "play": "▶️",
    "pause": "⏸️",
    "stop": "⏹️",
    "skip": "⏭️",
    "back": "⏮️",
    "shuffle": "🔀",
    "loop": "🔁",
    "volume_up": "🔊",
    "volume_down": "🔉",
    "playlist": "📋",
    "autoplay": "♾️",
    "music": "🎵",
    "heart": "❤️"
}

class CustomQueue:
    """Implementação personalizada de fila para substituir player.queue."""
    def __init__(self):
        self.items = deque()
    
    def append(self, item):
        """Adiciona um item ao final da fila."""
        self.items.append(item)
    
    def extend(self, items):
        """Adiciona vários itens ao final da fila."""
        self.items.extend(items)
    
    def pop(self, index=0):
        """Remove e retorna um item da fila."""
        if not self.items:
            return None
        return self.items.popleft() if index == 0 else self.items.pop(index)
    
    def clear(self):
        """Limpa a fila."""
        self.items.clear()
    
    def shuffle(self):
        """Embaralha a fila."""
        items_list = list(self.items)
        import random
        random.shuffle(items_list)
        self.items = deque(items_list)
    
    def __len__(self):
        """Retorna o tamanho da fila."""
        return len(self.items)
    
    def __getitem__(self, index):
        """Permite acessar itens por índice ou slice."""
        if isinstance(index, slice):
            return list(self.items)[index]
        return list(self.items)[index]
    
    def __iter__(self):
        """Permite iterar sobre a fila."""
        return iter(self.items)

class PlayerControls(nextcord.ui.View):
    def __init__(self, player, cog_instance):
        super().__init__(timeout=None) # Controles persistentes
        self.player = player
        self.cog = cog_instance

    @nextcord.ui.button(emoji=EMOJIS["pause"], style=nextcord.ButtonStyle.danger, row=0)
    async def pause_resume(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player or not self.player.current:
            await interaction.response.send_message("Não há nada tocando para pausar/continuar.", ephemeral=True)
            return

        if self.player.paused:
            await self.player.resume()
            button.emoji = EMOJIS["play"]
            await interaction.response.send_message("▶️ Música retomada!", ephemeral=True)
        else:
            await self.player.pause()
            button.emoji = EMOJIS["pause"]
            await interaction.response.send_message("⏸️ Música pausada!", ephemeral=True)
        await self.cog.update_now_playing_message(self.player)

    @nextcord.ui.button(emoji=EMOJIS["back"], style=nextcord.ButtonStyle.secondary, row=0)
    async def back(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player or not self.player.current:
            await interaction.response.send_message("Não há nada tocando para voltar.", ephemeral=True)
            return
            
        # Implementação básica de "voltar" - na verdade reinicia a música atual
        await self.player.seek(0)
        await interaction.response.send_message("⏮️ Voltando ao início da música!", ephemeral=True)

    @nextcord.ui.button(emoji=EMOJIS["skip"], style=nextcord.ButtonStyle.secondary, row=0)
    async def skip(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player or not self.player.current:
            await interaction.response.send_message("Não há nada tocando para pular.", ephemeral=True)
            return
        await self.player.stop() # Mafic lida com a próxima música da fila automaticamente
        await interaction.response.send_message("⏭️ Música pulada!", ephemeral=True)
        # A mensagem de "agora tocando" será atualizada pelo evento on_track_end/on_track_start

    @nextcord.ui.button(emoji=EMOJIS["stop"], style=nextcord.ButtonStyle.danger, row=0)
    async def stop_clear(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player:
            await interaction.response.send_message("O player não está ativo.", ephemeral=True)
            return

        # Limpa a fila personalizada
        guild_id = interaction.guild_id
        if guild_id in self.cog.queues:
            self.cog.queues[guild_id].clear()
            
        await self.player.stop() # Para a música atual
        
        try:
            await self.player.disconnect(force=True) # Desconecta do canal de voz
        except Exception as e:
            logger.error(f"Erro ao desconectar player para guild {interaction.guild_id}: {e}")

        # Remove o player da lista do cog
        if interaction.guild_id in self.cog.players:
            del self.cog.players[interaction.guild_id]
            
        # Limpa o dicionário de requesters
        if interaction.guild_id in self.cog.track_requesters:
            del self.cog.track_requesters[interaction.guild_id]
            
        # Limpa a fila personalizada
        if interaction.guild_id in self.cog.queues:
            del self.cog.queues[interaction.guild_id]
            
        # Limpa o estado de loop
        if interaction.guild_id in self.cog.loop_states:
            del self.cog.loop_states[interaction.guild_id]

        await interaction.response.send_message("⏹️ Player parado, fila limpa e bot desconectado.", ephemeral=True)

        if self.cog.now_playing_messages.get(interaction.guild_id):
            try:
                msg_id, channel_id = self.cog.now_playing_messages[interaction.guild_id]
                channel = self.cog.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(content="Player desconectado. Use `/tocar` para iniciar novamente.", view=None, embed=None)
                del self.cog.now_playing_messages[interaction.guild_id]
            except nextcord.NotFound:
                logger.warning(f"Mensagem 'agora tocando' não encontrada para guild {interaction.guild_id} ao parar.")
            except Exception as e:
                logger.error(f"Erro ao limpar mensagem 'agora tocando' para guild {interaction.guild_id}: {e}")

    @nextcord.ui.button(emoji=EMOJIS["volume_down"], style=nextcord.ButtonStyle.secondary, row=1)
    async def volume_down(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player:
            await interaction.response.send_message("O player não está ativo.", ephemeral=True)
            return
            
        # Diminui o volume em 10%
        current_volume = self.player.volume
        new_volume = max(0, current_volume - 10)
        await self.player.set_volume(new_volume)
        await interaction.response.send_message(f"🔉 Volume diminuído para {new_volume}%", ephemeral=True)
        await self.cog.update_now_playing_message(self.player)

    @nextcord.ui.button(emoji=EMOJIS["loop"], style=nextcord.ButtonStyle.secondary, row=1)
    async def loop_mode(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player:
            await interaction.response.send_message("O player não está ativo.", ephemeral=True)
            return

        guild_id = interaction.guild_id
        current_loop_mode = self.cog.get_loop_state(guild_id)
        
        if current_loop_mode == "none":
            self.cog.set_loop_state(guild_id, "track")
            await interaction.response.send_message("🔁 Loop da faixa atual ativado!", ephemeral=True)
        elif current_loop_mode == "track":
            self.cog.set_loop_state(guild_id, "queue")
            await interaction.response.send_message("🔁 Loop da fila ativado!", ephemeral=True)
        elif current_loop_mode == "queue":
            self.cog.set_loop_state(guild_id, "none")
            await interaction.response.send_message("🔁 Loop desativado!", ephemeral=True)
            
        await self.cog.update_now_playing_message(self.player)

    @nextcord.ui.button(emoji=EMOJIS["volume_up"], style=nextcord.ButtonStyle.secondary, row=1)
    async def volume_up(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player:
            await interaction.response.send_message("O player não está ativo.", ephemeral=True)
            return
            
        # Aumenta o volume em 10%
        current_volume = self.player.volume
        new_volume = min(100, current_volume + 10)
        await self.player.set_volume(new_volume)
        await interaction.response.send_message(f"🔊 Volume aumentado para {new_volume}%", ephemeral=True)
        await self.cog.update_now_playing_message(self.player)

    @nextcord.ui.button(emoji=EMOJIS["shuffle"], style=nextcord.ButtonStyle.secondary, row=2)
    async def shuffle_queue(self, button: nextcord.ui.Button, interaction: Interaction):
        guild_id = interaction.guild_id
        if guild_id not in self.cog.queues or not self.cog.queues[guild_id]:
            await interaction.response.send_message("A fila está vazia para embaralhar.", ephemeral=True)
            return
            
        self.cog.queues[guild_id].shuffle()
        await interaction.response.send_message("🔀 Fila embaralhada!", ephemeral=True)
        await self.cog.update_now_playing_message(self.player) # Para atualizar a exibição da fila se estiver visível

    @nextcord.ui.button(emoji=EMOJIS["playlist"], style=nextcord.ButtonStyle.secondary, row=2)
    async def show_queue(self, button: nextcord.ui.Button, interaction: Interaction):
        guild_id = interaction.guild_id
        if guild_id not in self.cog.queues or not self.cog.queues[guild_id]:
            await interaction.response.send_message("A fila está vazia.", ephemeral=True)
            return
            
        # Mostra a fila atual
        queue = self.cog.queues[guild_id]
        
        embed = nextcord.Embed(
            title="🎵 Fila de Músicas",
            color=nextcord.Color.red()
        )

        # Informações da música atual
        if self.player.current:
            # Obtém o requester da faixa atual
            requester = self.cog.get_requester(guild_id, self.player.current)
            requester_mention = requester.mention if requester else "Desconhecido"
            
            embed.add_field(
                name="🎶 Tocando Agora",
                value=f"**[{self.player.current.title}]({self.player.current.uri})** ({self.cog.format_duration(self.player.current.length)})\n"
                      f"Adicionado por: {requester_mention}",
                inline=False
            )
        else:
            embed.add_field(
                name="🎶 Tocando Agora",
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
                name=f"📋 Próximas na Fila ({len(queue)})",
                value=queue_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Próximas na Fila",
                value="A fila está vazia. Adicione músicas com `/tocar`!",
                inline=False
            )

        # Informações adicionais
        loop_status = "Desativado"
        loop_state = self.cog.get_loop_state(guild_id)
        if loop_state == "track": loop_status = "Faixa Atual"
        elif loop_state == "queue": loop_status = "Fila Inteira"
        
        embed.add_field(name="🔁 Loop", value=loop_status, inline=True)
        embed.add_field(name="🔊 Volume", value=f"{self.player.volume}%", inline=True)
        
        if self.player.paused:
            embed.add_field(name="⏸️ Status", value="Pausado", inline=True)
        else:
            embed.add_field(name="▶️ Status", value="Tocando", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(emoji=EMOJIS["autoplay"], style=nextcord.ButtonStyle.secondary, row=2)
    async def autoplay(self, button: nextcord.ui.Button, interaction: Interaction):
        # Implementação básica de autoplay - na verdade apenas uma mensagem informativa
        await interaction.response.send_message("♾️ Autoplay não está disponível nesta versão do bot.", ephemeral=True)

class MusicPanel(nextcord.ui.View):
    """Painel estilizado para exibição da música atual."""
    def __init__(self, player, cog_instance):
        super().__init__(timeout=None)
        self.player = player
        self.cog = cog_instance
        self.add_controls()
        
    def add_controls(self):
        # Primeira linha: controles básicos
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["volume_down"], style=nextcord.ButtonStyle.danger, row=0, custom_id="volume_down"))
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["back"], style=nextcord.ButtonStyle.danger, row=0, custom_id="back"))
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["pause"], style=nextcord.ButtonStyle.danger, row=0, custom_id="pause"))
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["skip"], style=nextcord.ButtonStyle.danger, row=0, custom_id="skip"))
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["volume_up"], style=nextcord.ButtonStyle.danger, row=0, custom_id="volume_up"))
        
        # Segunda linha: controles adicionais
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["shuffle"], style=nextcord.ButtonStyle.danger, row=1, custom_id="shuffle"))
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["loop"], style=nextcord.ButtonStyle.danger, row=1, custom_id="loop"))
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["stop"], style=nextcord.ButtonStyle.danger, row=1, custom_id="stop"))
        
        # Terceira linha: playlist e autoplay
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["autoplay"], style=nextcord.ButtonStyle.danger, row=2, custom_id="autoplay"))
        self.add_item(nextcord.ui.Button(emoji=EMOJIS["playlist"], style=nextcord.ButtonStyle.danger, row=2, custom_id="playlist"))

class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}  # guild_id: mafic.Player
        self.now_playing_messages = {}  # guild_id: (message_id, channel_id)
        self.reconnect_attempts = {}  # guild_id: número de tentativas
        self.max_reconnect_attempts = 3  # Máximo de tentativas de reconexão
        
        # Dicionário para armazenar os requesters das faixas
        # Formato: {guild_id: {track_identifier: requester}}
        self.track_requesters = {}
        
        # Dicionário para armazenar as filas personalizadas
        # Formato: {guild_id: CustomQueue}
        self.queues = {}
        
        # Dicionário para armazenar o estado de loop
        # Formato: {guild_id: "none"|"track"|"queue"}
        self.loop_states = {}
        
        # Dicionário para armazenar a última música tocada
        # Formato: {guild_id: track}
        self.last_tracks = {}

    def get_queue(self, guild_id: int) -> CustomQueue:
        """Obtém a fila personalizada para um servidor."""
        if guild_id not in self.queues:
            self.queues[guild_id] = CustomQueue()
        return self.queues[guild_id]

    def get_loop_state(self, guild_id: int) -> str:
        """Obtém o estado de loop para um servidor."""
        return self.loop_states.get(guild_id, "none")

    def set_loop_state(self, guild_id: int, state: str):
        """Define o estado de loop para um servidor."""
        self.loop_states[guild_id] = state

    def set_requester(self, guild_id: int, track: mafic.Track, requester: nextcord.Member):
        """Armazena o requester de uma faixa."""
        if guild_id not in self.track_requesters:
            self.track_requesters[guild_id] = {}
        
        # Usamos o identificador da faixa como chave
        track_id = f"{track.identifier}_{track.title}"
        self.track_requesters[guild_id][track_id] = requester

    def get_requester(self, guild_id: int, track: mafic.Track) -> Optional[nextcord.Member]:
        """Obtém o requester de uma faixa."""
        if guild_id not in self.track_requesters:
            return None
        
        # Usamos o identificador da faixa como chave
        track_id = f"{track.identifier}_{track.title}"
        return self.track_requesters[guild_id].get(track_id)

    async def get_player(self, interaction: Interaction) -> Optional[mafic.Player]:
        """Obtém ou cria um player para o servidor."""
        if not interaction.guild_id:
            return None
            
        # Se já existe um player para este servidor, retorna-o
        if interaction.guild_id in self.players:
            player = self.players[interaction.guild_id]
            
            # Verifica se o player está conectado
            if player.connected:
                return player
                
            # Se não estiver conectado, tenta reconectar
            try:
                # Tenta reconectar ao canal de voz do usuário
                voice_channel = interaction.user.voice.channel
                await player.connect(voice_channel.id)
                return player
            except Exception as e:
                logger.error(f"Erro ao reconectar player para guild {interaction.guild_id}: {e}")
                # Continua para criar um novo player
        
        # Cria um novo player
        try:
            # Verifica se o usuário está em um canal de voz
            if not interaction.user.voice or not interaction.user.voice.channel:
                return None
                
            voice_channel = interaction.user.voice.channel
            
            # Verifica se o bot tem permissão para se conectar e falar no canal
            bot_member = interaction.guild.get_member(self.bot.user.id)
            if not voice_channel.permissions_for(bot_member).connect or not voice_channel.permissions_for(bot_member).speak:
                await interaction.followup.send(
                    "Não tenho permissão para me conectar ou falar no seu canal de voz. "
                    "Por favor, verifique as permissões do canal.", 
                    ephemeral=True
                )
                return None
            
            # Cria um novo player e conecta ao canal de voz
            try:
                # Tenta obter um nó do pool
                if not hasattr(self.bot, "mafic_pool") or not self.bot.mafic_pool:
                    await interaction.followup.send(
                        "O sistema de música não está inicializado corretamente. "
                        "Por favor, informe ao administrador do bot.", 
                        ephemeral=True
                    )
                    return None
                    
                # Cria o player
                player = await self.bot.mafic_pool.create_player(interaction.guild_id)
                
                # Conecta ao canal de voz
                await player.connect(voice_channel.id)
                
                # Define o volume padrão
                await player.set_volume(70)
                
                # Armazena o player
                self.players[interaction.guild_id] = player
                
                # Reseta o contador de tentativas de reconexão
                self.reconnect_attempts[interaction.guild_id] = 0
                
                logger.info(f"Novo player criado e conectado para guild {interaction.guild_id} no canal {voice_channel.name}")
                return player
            except mafic.errors.NoNodesAvailable:
                logger.error(f"Nenhum nó Lavalink disponível para guild {interaction.guild_id}")
                await interaction.followup.send(
                    "O servidor de música não está disponível no momento. "
                    "Por favor, tente novamente mais tarde ou informe ao administrador do bot.", 
                    ephemeral=True
                )
                
                # Incrementa o contador de tentativas de reconexão
                self.reconnect_attempts[interaction.guild_id] = self.reconnect_attempts.get(interaction.guild_id, 0) + 1
                
                # Se excedeu o número máximo de tentativas, tenta reconectar o nó
                if self.reconnect_attempts.get(interaction.guild_id, 0) >= self.max_reconnect_attempts:
                    logger.warning(f"Tentando reconectar ao Lavalink após {self.max_reconnect_attempts} falhas para guild {interaction.guild_id}")
                    try:
                        # Tenta reconectar o nó
                        for node in self.bot.mafic_pool.nodes:
                            await node.reconnect()
                        logger.info("Reconexão ao Lavalink concluída")
                    except Exception as reconnect_error:
                        logger.error(f"Erro ao reconectar ao Lavalink: {reconnect_error}")
                return None
        except Exception as e:
            logger.error(f"Erro ao conectar ao canal de voz para guild {interaction.guild_id}: {e}", exc_info=True)
            return None

    @nextcord.slash_command(name="tocar", description="Toca uma música ou adiciona à fila. Use URL ou nome da música.")
    async def play(
        self, 
        interaction: Interaction, 
        busca: str = SlashOption(
            name="musica_ou_url", 
            description="Nome da música, URL do YouTube/SoundCloud ou playlist.", 
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

            # Verifica se é uma URL válida ou um termo de busca
            is_url = bool(URL_REGEX.match(busca))
            is_search_term = bool(SEARCH_TERM_REGEX.match(busca)) and not is_url

            tracks: Union[mafic.Playlist, List[mafic.Track], None] = None

            if is_url:
                logger.info(f"Buscando por URL: {busca} para guild {interaction.guild_id}")
                # Para URLs, incluindo playlists, fetch_tracks é geralmente o melhor
                try:
                    tracks = await player.fetch_tracks(busca)  # Deixa Mafic decidir a fonte pela URL
                except mafic.errors.HTTPNotFound as e:
                    logger.error(f"Erro HTTP 404 ao buscar faixas: {e}")
                    await interaction.followup.send("Erro ao conectar ao servidor de música. Tente novamente mais tarde.", ephemeral=True)
                    return
                except Exception as e:
                    logger.error(f"Erro ao buscar faixas por URL: {e}")
                    await interaction.followup.send(f"Erro ao buscar música: {e}", ephemeral=True)
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
                            "Não foi possível encontrar resultados para sua busca. Tente usar um link direto do YouTube ou SoundCloud.", 
                            ephemeral=True
                        )
                        return
                        
                except mafic.errors.HTTPNotFound as e:
                    logger.error(f"Erro HTTP 404 ao buscar faixas: {e}")
                    await interaction.followup.send(
                        "O servidor de música não conseguiu processar sua busca. Tente usar um link direto do YouTube ou SoundCloud.", 
                        ephemeral=True
                    )
                    return
                except Exception as e:
                    logger.error(f"Erro ao buscar faixas por termo: {e}")
                    await interaction.followup.send(f"Erro ao buscar música: {e}", ephemeral=True)
                    return
            else:
                await interaction.followup.send("Entrada inválida. Por favor, forneça uma URL válida (YouTube/SoundCloud) ou um termo de busca (3-500 caracteres).", ephemeral=True)
                return

            if not tracks:
                await interaction.followup.send(f"Nenhuma música encontrada para: `{busca}`", ephemeral=True)
                return

            added_to_queue_count = 0
            first_track_title = ""
            
            # Obtém a fila personalizada para este servidor
            queue = self.get_queue(interaction.guild_id)

            # Adiciona o requester às faixas usando nosso sistema de armazenamento separado
            if isinstance(tracks, mafic.Playlist):
                for track in tracks.tracks:
                    # Armazena o requester para cada faixa
                    self.set_requester(interaction.guild_id, track, interaction.user)
                queue.extend(tracks.tracks)
                added_to_queue_count = len(tracks.tracks)
                first_track_title = tracks.name # Nome da playlist
                await interaction.followup.send(f"🎶 Playlist **{tracks.name}** ({added_to_queue_count} músicas) adicionada à fila!")
            elif isinstance(tracks, list) and tracks: # Lista de faixas (resultado de busca)
                if is_search_term: # Se foi uma busca, geralmente pegamos a primeira e adicionamos
                    track_to_add = tracks[0]
                    # Armazena o requester para a faixa
                    self.set_requester(interaction.guild_id, track_to_add, interaction.user)
                    queue.append(track_to_add)
                    added_to_queue_count = 1
                    first_track_title = track_to_add.title
                    await interaction.followup.send(f"🎵 **{track_to_add.title}** adicionada à fila!")
                else: # Se foi uma URL de faixa única que retornou uma lista (improvável, mas para cobrir)
                    for track in tracks:
                        # Armazena o requester para cada faixa
                        self.set_requester(interaction.guild_id, track, interaction.user)
                    queue.extend(tracks)
                    added_to_queue_count = len(tracks)
                    first_track_title = tracks[0].title
                    await interaction.followup.send(f"🎵 **{tracks[0].title}** ({added_to_queue_count} música(s)) adicionada(s) à fila!")
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

    async def update_now_playing_message(self, player: mafic.Player):
        """Atualiza a mensagem de 'agora tocando'."""
        if not player or not player.guild or not player.current:
            return

        guild_id = player.guild.id  # Corrigido: Usando player.guild.id em vez de player.guild_id
        
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
            title=f"{EMOJIS['music']} PAINEL DE MÚSICA",
            description=f"**[{current_track.title}]({current_track.uri})**",
            color=nextcord.Color.red()  # Cor vermelha para combinar com os botões
        )
        
        # Obtém o requester da faixa atual
        requester = self.get_requester(guild_id, current_track)
        
        # Adiciona campos para Requested By, Duration e Music Author
        embed.add_field(
            name="Adicionado por",
            value=f"{requester.mention if requester else 'Desconhecido'}",
            inline=True
        )
        
        embed.add_field(
            name="Duração",
            value=self.format_duration(current_track.length),
            inline=True
        )
        
        embed.add_field(
            name="Autor",
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
        
        embed.set_footer(text=f"Volume: {player.volume}% | Loop: {loop_status} | Status: {'Pausado' if player.paused else 'Tocando'}")

        try:
            # Atualiza a mensagem com o novo embed e os controles
            await message.edit(content=None, embed=embed, view=PlayerControls(player, self))
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
            color=nextcord.Color.red()
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
        if loop_state == "track": loop_status = "Faixa Atual"
        elif loop_state == "queue": loop_status = "Fila Inteira"
        
        embed.add_field(name=f"{EMOJIS['loop']} Loop", value=loop_status, inline=True)
        embed.add_field(name=f"{EMOJIS['volume_up']} Volume", value=f"{player.volume}%", inline=True)
        
        if player.paused:
            embed.add_field(name="⏸️ Status", value="Pausado", inline=True)
        else:
            embed.add_field(name="▶️ Status", value="Tocando", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="pular", description="Pula a música atual.")
    async def skip(self, interaction: Interaction):
        """Comando para pular a música atual."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected or not player.current:
            await interaction.response.send_message("Não há nada tocando para pular.", ephemeral=True)
            return

        await player.stop()  # Mafic lida com a próxima música da fila automaticamente
        await interaction.response.send_message(f"{EMOJIS['skip']} Música pulada!")

    @nextcord.slash_command(name="pausar", description="Pausa ou retoma a música atual.")
    async def pause(self, interaction: Interaction):
        """Comando para pausar ou retomar a música atual."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected or not player.current:
            await interaction.response.send_message("Não há nada tocando para pausar/continuar.", ephemeral=True)
            return

        if player.paused:
            await player.resume()
            await interaction.response.send_message(f"{EMOJIS['play']} Música retomada!")
        else:
            await player.pause()
            await interaction.response.send_message(f"{EMOJIS['pause']} Música pausada!")

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
            
        # Limpa a última música tocada
        if interaction.guild_id in self.last_tracks:
            del self.last_tracks[interaction.guild_id]

        await interaction.response.send_message(f"{EMOJIS['stop']} Player parado, fila limpa e bot desconectado.")

        # Atualiza a mensagem de "agora tocando"
        if interaction.guild_id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[interaction.guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(content="Player desconectado. Use `/tocar` para iniciar novamente.", view=None, embed=None)
                del self.now_playing_messages[interaction.guild_id]
            except Exception as e:
                logger.error(f"Erro ao atualizar mensagem 'agora tocando' após parar para guild {interaction.guild_id}: {e}")

    @nextcord.slash_command(name="volume", description="Ajusta o volume da reprodução (0-100).")
    async def volume(
        self, 
        interaction: Interaction, 
        volume: int = SlashOption(
            name="nivel", 
            description="Nível de volume (0-100)", 
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

        await player.set_volume(volume)
        
        emoji = EMOJIS["volume_up"] if volume >= 50 else EMOJIS["volume_down"]
        await interaction.response.send_message(f"{emoji} Volume ajustado para {volume}%")
        
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="loop", description="Configura o modo de repetição (desativado, faixa, fila).")
    async def loop(
        self, 
        interaction: Interaction, 
        modo: str = SlashOption(
            name="modo", 
            description="Modo de repetição", 
            required=True,
            choices={"Desativado": "none", "Faixa Atual": "track", "Fila Inteira": "queue"}
        )
    ):
        """Comando para configurar o modo de repetição."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return

        self.set_loop_state(interaction.guild_id, modo)
        
        if modo == "none":
            await interaction.response.send_message(f"{EMOJIS['loop']} Loop desativado.")
        elif modo == "track":
            await interaction.response.send_message(f"{EMOJIS['loop']} Loop da faixa atual ativado.")
        elif modo == "queue":
            await interaction.response.send_message(f"{EMOJIS['loop']} Loop da fila inteira ativado.")

        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="shuffle", description="Embaralha a fila de músicas.")
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
        
        if not queue:
            await interaction.response.send_message("A fila está vazia para embaralhar.", ephemeral=True)
            return

        queue.shuffle()
        await interaction.response.send_message(f"{EMOJIS['shuffle']} Fila embaralhada!")
        await self.update_now_playing_message(player)

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
        # Cria um embed estilizado para o painel de música
        embed = nextcord.Embed(
            title=f"{EMOJIS['music']} PAINEL DE MÚSICA",
            description=f"**[{track.title}]({track.uri})**",
            color=nextcord.Color.red()  # Cor vermelha para combinar com os botões
        )
        
        # Obtém o requester da faixa atual
        requester = self.get_requester(guild_id, track)
        
        # Adiciona campos para Requested By, Duration e Music Author
        embed.add_field(
            name="Adicionado por",
            value=f"{requester.mention if requester else 'Desconhecido'}",
            inline=True
        )
        
        embed.add_field(
            name="Duração",
            value=self.format_duration(track.length),
            inline=True
        )
        
        embed.add_field(
            name="Autor",
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
        
        embed.set_footer(text=f"Volume: {player.volume}% | Loop: {loop_status} | Status: {'Pausado' if player.paused else 'Tocando'}")

        # Verifica se já existe uma mensagem de "agora tocando" para este servidor
        if guild_id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(msg_id)
                        await message.edit(content=None, embed=embed, view=PlayerControls(player, self))
                        return
                    except nextcord.NotFound:
                        # Mensagem não encontrada, vamos criar uma nova
                        pass
                    except Exception as e:
                        logger.error(f"Erro ao editar mensagem 'agora tocando' para guild {guild_id}: {e}")
            except Exception as e:
                logger.error(f"Erro ao processar mensagem 'agora tocando' existente para guild {guild_id}: {e}")

        # Se chegou aqui, precisamos criar uma nova mensagem
        # Encontra o canal de texto mais adequado para enviar a mensagem
        text_channel = None
        
        # Tenta encontrar o canal onde o comando foi executado
        requester = self.get_requester(guild_id, track)
        if requester and isinstance(requester, nextcord.Member):
            for channel in player.guild.text_channels:
                if channel.permissions_for(player.guild.me).send_messages and channel.permissions_for(requester).read_messages:
                    text_channel = channel
                    break
        
        # Se não encontrou, tenta o canal geral ou o primeiro canal disponível
        if not text_channel:
            for channel in player.guild.text_channels:
                if channel.permissions_for(player.guild.me).send_messages:
                    if channel.name.lower() in ["geral", "general", "chat", "música", "music"]:
                        text_channel = channel
                        break
            
            if not text_channel:
                for channel in player.guild.text_channels:
                    if channel.permissions_for(player.guild.me).send_messages:
                        text_channel = channel
                        break
        
        if text_channel:
            try:
                message = await text_channel.send(embed=embed, view=PlayerControls(player, self))
                self.now_playing_messages[guild_id] = (message.id, text_channel.id)
                logger.info(f"Nova mensagem 'agora tocando' criada para guild {guild_id} no canal {text_channel.name}")
            except Exception as e:
                logger.error(f"Erro ao criar mensagem 'agora tocando' para guild {guild_id}: {e}")

    @commands.Cog.listener()
    async def on_mafic_track_end(self, player: mafic.Player, track: mafic.Track, reason: str):
        """Evento disparado quando uma faixa termina de tocar."""
        logger.info(f"Faixa terminada: {track.title} em {player.guild.name if player.guild else 'Unknown'} ({player.guild.id if player.guild else 'Unknown'}). Razão: {reason}")
        
        # Verifica se o player e o guild existem
        if not player or not player.guild:
            return
            
        guild_id = player.guild.id
        
        # Obtém o estado de loop para este servidor
        loop_state = self.get_loop_state(guild_id)
        
        # Obtém a fila personalizada para este servidor
        queue = self.get_queue(guild_id)
        
        # Implementa o comportamento de loop
        if loop_state == "track" and reason != "REPLACED":
            # Loop de faixa: adiciona a faixa atual de volta à fila e a toca novamente
            try:
                await player.play(track, start_time=0)
                logger.info(f"Loop de faixa: Reproduzindo novamente {track.title} para guild {guild_id}")
                return
            except Exception as e:
                logger.error(f"Erro ao implementar loop de faixa: {e}")
        elif loop_state == "queue" and reason != "REPLACED":
            # Loop de fila: adiciona a faixa atual ao final da fila
            queue.append(track)
            logger.info(f"Loop de fila: Adicionando {track.title} ao final da fila para guild {guild_id}")
        
        # Se a fila não estiver vazia, toca a próxima música
        if queue:
            try:
                next_track = queue.pop(0)
                await player.play(next_track, start_time=0)
                logger.info(f"Reproduzindo próxima faixa: {next_track.title} para guild {guild_id}")
            except Exception as e:
                logger.error(f"Erro ao reproduzir próxima faixa: {e}")
        elif not queue and not player.current:
            # Se a fila estiver vazia e não houver mais nada tocando, podemos limpar a mensagem de "agora tocando"
            if guild_id in self.now_playing_messages:
                try:
                    msg_id, channel_id = self.now_playing_messages[guild_id]
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        message = await channel.fetch_message(msg_id)
                        await message.edit(content="Fila vazia. Use `/tocar` para adicionar mais músicas!", embed=None, view=None)
                        
                        # Envia mensagem de confirmação de fim de música
                        await channel.send(f"🎵 Música **{track.title}** acabou. A fila está vazia!")
                except Exception as e:
                    logger.error(f"Erro ao atualizar mensagem 'agora tocando' após fim da fila para guild {guild_id}: {e}")

    @commands.Cog.listener()
    async def on_mafic_track_exception(self, player: mafic.Player, track: mafic.Track, exception: Exception):
        """Evento disparado quando ocorre um erro ao tocar uma faixa."""
        logger.error(f"Erro ao tocar faixa: {track.title} em {player.guild.name if player.guild else 'Unknown'} ({player.guild.id if player.guild else 'Unknown'}). Erro: {exception}")
        
        # Tenta notificar no canal onde a mensagem de "agora tocando" está
        if player.guild and player.guild.id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[player.guild.id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"❌ Erro ao tocar **{track.title}**: {exception}")
            except Exception as e:
                logger.error(f"Erro ao enviar notificação de erro para guild {player.guild.id if player.guild else 'Unknown'}: {e}")
                
        # Tenta tocar a próxima música da fila
        guild_id = player.guild.id if player.guild else None
        if guild_id:
            queue = self.get_queue(guild_id)
            if queue:
                try:
                    next_track = queue.pop(0)
                    await player.play(next_track, start_time=0)
                    logger.info(f"Reproduzindo próxima faixa após erro: {next_track.title} para guild {guild_id}")
                except Exception as e:
                    logger.error(f"Erro ao reproduzir próxima faixa após erro: {e}")

    @commands.Cog.listener()
    async def on_mafic_track_stuck(self, player: mafic.Player, track: mafic.Track, threshold_ms: int):
        """Evento disparado quando uma faixa fica presa (não avança)."""
        logger.warning(f"Faixa presa: {track.title} em {player.guild.name if player.guild else 'Unknown'} ({player.guild.id if player.guild else 'Unknown'}). Threshold: {threshold_ms}ms")
        
        # Tenta pular a faixa presa
        try:
            await player.stop()
            
            # Notifica no canal onde a mensagem de "agora tocando" está
            if player.guild and player.guild.id in self.now_playing_messages:
                try:
                    msg_id, channel_id = self.now_playing_messages[player.guild.id]
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send(f"⚠️ A música **{track.title}** ficou presa e foi pulada automaticamente.")
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação de faixa presa para guild {player.guild.id if player.guild else 'Unknown'}: {e}")
        except Exception as e:
            logger.error(f"Erro ao tentar pular faixa presa: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        """Evento disparado quando o estado de voz de um membro muda."""
        # Ignora se não for o bot
        if member.id != self.bot.user.id:
            return
        
        # Verifica se o bot foi desconectado do canal de voz
        if before.channel and not after.channel:
            # Bot foi desconectado, limpa o player
            if member.guild.id in self.players:
                logger.info(f"Bot desconectado do canal de voz em {member.guild.name} ({member.guild.id}). Limpando player.")
                
                try:
                    # Tenta destruir o player corretamente
                    player = self.players[member.guild.id]
                    
                    # Limpa a fila personalizada
                    if member.guild.id in self.queues:
                        self.queues[member.guild.id].clear()
                    
                    try:
                        await player.destroy()
                    except Exception as e_destroy:
                        logger.error(f"Erro ao destruir player após desconexão para guild {member.guild.id}: {e_destroy}")
                    
                    # Remove o player da lista
                    del self.players[member.guild.id]
                    
                    # Limpa o dicionário de requesters
                    if member.guild.id in self.track_requesters:
                        del self.track_requesters[member.guild.id]
                    
                    # Limpa a fila personalizada
                    if member.guild.id in self.queues:
                        del self.queues[member.guild.id]
                        
                    # Limpa o estado de loop
                    if member.guild.id in self.loop_states:
                        del self.loop_states[member.guild.id]
                        
                    # Limpa a última música tocada
                    if member.guild.id in self.last_tracks:
                        del self.last_tracks[member.guild.id]
                    
                    # Atualiza a mensagem de "agora tocando"
                    if member.guild.id in self.now_playing_messages:
                        try:
                            msg_id, channel_id = self.now_playing_messages[member.guild.id]
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                message = await channel.fetch_message(msg_id)
                                await message.edit(content="Bot desconectado do canal de voz. Use `/tocar` para iniciar novamente.", view=None, embed=None)
                            del self.now_playing_messages[member.guild.id]
                        except Exception as e:
                            logger.error(f"Erro ao atualizar mensagem 'agora tocando' após desconexão para guild {member.guild.id}: {e}")
                except Exception as e:
                    logger.error(f"Erro ao limpar player após desconexão para guild {member.guild.id}: {e}")

def setup(bot):
    bot.add_cog(Musica(bot))
