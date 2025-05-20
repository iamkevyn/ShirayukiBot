# /home/ubuntu/ShirayukiBot/cogs/Musica.py
# Cog de Música reescrita para usar Mafic

import nextcord
from nextcord import Interaction, SlashOption, ChannelType
from nextcord.ext import commands
import mafic
import logging
import asyncio
import re
from typing import Optional, List, Union

logger = logging.getLogger("discord_bot.musica_mafic")

# Regex para validar URLs do YouTube e Soundcloud, e termos de busca
URL_REGEX = re.compile(
    r"^(?:(?:https?:)?//)?(?:www\.)?"
    r"(?:(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/|playlist\?list=))"
    r"|(?:youtu\.be/)|(?:soundcloud\.com/[^/]+(?:/(?:sets/)?/[^/]+)?))"
    r"([a-zA-Z0-9_-]+)"
)
SEARCH_TERM_REGEX = re.compile(r"^.{3,500}$") # Termos de busca genéricos

class PlayerControls(nextcord.ui.View):
    def __init__(self, player: mafic.Player, cog_instance):
        super().__init__(timeout=None) # Controles persistentes
        self.player = player
        self.cog = cog_instance

    @nextcord.ui.button(label="⏯️ Pausar/Continuar", style=nextcord.ButtonStyle.primary, row=0)
    async def pause_resume(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player or not self.player.current:
            await interaction.response.send_message("Não há nada tocando para pausar/continuar.", ephemeral=True)
            return

        if self.player.paused:
            await self.player.resume()
            await interaction.response.send_message("▶️ Música retomada!", ephemeral=True)
        else:
            await self.player.pause()
            await interaction.response.send_message("⏸️ Música pausada!", ephemeral=True)
        await self.cog.update_now_playing_message(self.player)

    @nextcord.ui.button(label="⏭️ Pular", style=nextcord.ButtonStyle.secondary, row=0)
    async def skip(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player or not self.player.current:
            await interaction.response.send_message("Não há nada tocando para pular.", ephemeral=True)
            return
        await self.player.stop() # Mafic lida com a próxima música da fila automaticamente
        await interaction.response.send_message("⏭️ Música pulada!", ephemeral=True)
        # A mensagem de "agora tocando" será atualizada pelo evento on_track_end/on_track_start

    @nextcord.ui.button(label="⏹️ Parar e Limpar", style=nextcord.ButtonStyle.danger, row=0)
    async def stop_clear(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player:
            await interaction.response.send_message("O player não está ativo.", ephemeral=True)
            return

        self.player.queue.clear()
        await self.player.stop() # Para a música atual
        
        try:
            await self.player.disconnect(force=True) # Desconecta do canal de voz
        except Exception as e:
            logger.error(f"Erro ao desconectar player para guild {interaction.guild_id}: {e}")

        # Remove o player da lista do cog
        if interaction.guild_id in self.cog.players:
            del self.cog.players[interaction.guild_id]

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

    @nextcord.ui.button(label="🔁 Loop Faixa/Fila/Off", style=nextcord.ButtonStyle.secondary, row=1)
    async def loop_mode(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player:
            await interaction.response.send_message("O player não está ativo.", ephemeral=True)
            return

        current_loop_mode = self.player.loop
        if current_loop_mode == mafic.LoopType.NONE:
            self.player.loop = mafic.LoopType.TRACK
            await interaction.response.send_message("🔁 Loop da faixa atual ativado!", ephemeral=True)
        elif current_loop_mode == mafic.LoopType.TRACK:
            self.player.loop = mafic.LoopType.QUEUE
            await interaction.response.send_message("🔁 Loop da fila ativado!", ephemeral=True)
        elif current_loop_mode == mafic.LoopType.QUEUE:
            self.player.loop = mafic.LoopType.NONE
            await interaction.response.send_message("🔁 Loop desativado!", ephemeral=True)
        await self.cog.update_now_playing_message(self.player)

    @nextcord.ui.button(label="🔀 Shuffle", style=nextcord.ButtonStyle.secondary, row=1)
    async def shuffle_queue(self, button: nextcord.ui.Button, interaction: Interaction):
        if not self.player or not self.player.queue:
            await interaction.response.send_message("A fila está vazia para embaralhar.", ephemeral=True)
            return
        self.player.queue.shuffle()
        await interaction.response.send_message("🔀 Fila embaralhada!", ephemeral=True)
        await self.cog.update_now_playing_message(self.player) # Para atualizar a exibição da fila se estiver visível

class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}  # guild_id: mafic.Player
        self.now_playing_messages = {}  # guild_id: (message_id, channel_id)
        self.reconnect_attempts = {}  # guild_id: número de tentativas
        self.max_reconnect_attempts = 3  # Máximo de tentativas de reconexão
        logger.info("--- [COG MUSICA MAFIC] Cog Musica (Mafic) inicializada ---")

    async def get_player(self, interaction: Interaction) -> Optional[mafic.Player]:
        """Obtém ou cria um player para o servidor."""
        # Verifica se o usuário está em um canal de voz
        if not interaction.guild or not interaction.user.voice or not interaction.user.voice.channel:
            return None

        # Verifica se o NodePool do Mafic está disponível
        if not hasattr(self.bot, "mafic_pool") or not self.bot.mafic_pool:
            logger.error("Mafic NodePool não encontrado no bot. O setup_hook do bot falhou?")
            return None

        # Verifica se já existe um player para este servidor
        if interaction.guild_id in self.players:
            player = self.players[interaction.guild_id]
            
            # Verifica se o player ainda está conectado
            if player.connected:
                return player
            else:
                # Player existe mas não está conectado, vamos limpar e criar um novo
                logger.warning(f"Player para guild {interaction.guild_id} encontrado mas não conectado. Limpando...")
                try:
                    await player.destroy()
                except Exception as e_destroy:
                    logger.error(f"Erro ao tentar destruir player desconectado para guild {interaction.guild_id}: {e_destroy}")
                
                # Remove o player da lista
                del self.players[interaction.guild_id]
                
                # Reseta contagem de tentativas de reconexão
                self.reconnect_attempts[interaction.guild_id] = 0

        # Incrementa contador de tentativas de reconexão
        if interaction.guild_id not in self.reconnect_attempts:
            self.reconnect_attempts[interaction.guild_id] = 0
        
        self.reconnect_attempts[interaction.guild_id] += 1
        
        # Verifica se excedeu o número máximo de tentativas
        if self.reconnect_attempts[interaction.guild_id] > self.max_reconnect_attempts:
            logger.warning(f"Máximo de tentativas de reconexão excedido para guild {interaction.guild_id}")
            return None

        try:
            # Conecta ao canal de voz e cria o player
            logger.info(f"Tentando conectar ao canal de voz: {interaction.user.voice.channel.name} (ID: {interaction.user.voice.channel.id}) para guild {interaction.guild_id}")
            
            # Tenta obter um nó disponível
            # Corrigido: Usando next(iter()) para obter o primeiro nó disponível
            node = None
            if self.bot.mafic_pool.nodes:
                node = next(iter(self.bot.mafic_pool.nodes), None)
            
            if not node:
                logger.error("Nenhum nó Lavalink disponível")
                return None
            
            # Conecta ao canal de voz
            player: mafic.Player = await interaction.user.voice.channel.connect(cls=mafic.Player)
            logger.info(f"Conectado ao canal de voz. Player: {player}")

            # Tenta definir self_deaf após a conexão
            if player and player.guild and player.guild.me:
                try:
                    await player.guild.me.edit(deafen=True)
                    logger.info(f"Bot definido como surdo no canal para guild {interaction.guild_id}")
                except Exception as e_deafen:
                    logger.warning(f"Não foi possível definir o bot como surdo para guild {interaction.guild_id}: {e_deafen}")
            else:
                logger.warning(f"Não foi possível definir o bot como surdo: player, guild ou guild.me não disponíveis após conexão. Guild ID: {interaction.guild_id}")
            
            # Armazena o player e reseta contador de tentativas
            self.players[interaction.guild_id] = player
            self.reconnect_attempts[interaction.guild_id] = 0
            
            logger.info(f"Player criado e armazenado para guild {interaction.guild_id} no canal {interaction.user.voice.channel.name}")
            return player
        except mafic.errors.NoNodesAvailable:
            logger.error("Falha ao conectar: Nenhum nó Lavalink disponível.")
            return None
        except mafic.errors.HTTPNotFound as e:
            logger.error(f"Erro HTTP 404 ao conectar ao canal de voz: {e}")
            # Tenta reconectar ao Lavalink se for um erro de sessão
            if "Session not found" in str(e):
                logger.warning("Sessão não encontrada. Tentando reconectar ao Lavalink...")
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
                # Para termos de busca, usamos fetch_tracks com prefixo ytsearch:
                try:
                    # Corrigido: Usando fetch_tracks com prefixo ytsearch: para busca
                    search_query = f"ytsearch:{busca}"  # Formato para busca no YouTube
                    tracks = await player.fetch_tracks(search_query)
                except mafic.errors.HTTPNotFound as e:
                    logger.error(f"Erro HTTP 404 ao buscar faixas: {e}")
                    await interaction.followup.send("Erro ao conectar ao servidor de música. Tente novamente mais tarde.", ephemeral=True)
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

            # Adiciona o requester às faixas
            if isinstance(tracks, mafic.Playlist):
                for track in tracks.tracks:
                    track.requester = interaction.user
                player.queue.extend(tracks.tracks)
                added_to_queue_count = len(tracks.tracks)
                first_track_title = tracks.name # Nome da playlist
                await interaction.followup.send(f"🎶 Playlist **{tracks.name}** ({added_to_queue_count} músicas) adicionada à fila!")
            elif isinstance(tracks, list) and tracks: # Lista de faixas (resultado de busca)
                if is_search_term: # Se foi uma busca, geralmente pegamos a primeira e adicionamos
                    track_to_add = tracks[0]
                    track_to_add.requester = interaction.user
                    player.queue.append(track_to_add)
                    added_to_queue_count = 1
                    first_track_title = track_to_add.title
                    await interaction.followup.send(f"🎵 **{track_to_add.title}** adicionada à fila!")
                else: # Se foi uma URL de faixa única que retornou uma lista (improvável, mas para cobrir)
                    for track in tracks:
                        track.requester = interaction.user
                    player.queue.extend(tracks)
                    added_to_queue_count = len(tracks)
                    first_track_title = tracks[0].title
                    await interaction.followup.send(f"🎵 **{tracks[0].title}** ({added_to_queue_count} música(s)) adicionada(s) à fila!")
            else:
                await interaction.followup.send(f"Não foi possível processar o resultado para: `{busca}`", ephemeral=True)
                return

            if not player.current and player.queue:
                # Inicia a primeira música da fila
                try:
                    first_track = player.queue.pop(0)
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
        if not player or not player.guild_id or not player.current:
            return

        message_info = self.now_playing_messages.get(player.guild_id)
        if not message_info:
            return

        msg_id, channel_id = message_info
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, nextcord.TextChannel):
            logger.warning(f"Canal não encontrado ou não é canal de texto para guild {player.guild_id} ao atualizar NP.")
            return

        try:
            message = await channel.fetch_message(msg_id)
        except nextcord.NotFound:
            logger.warning(f"Mensagem 'agora tocando' (ID: {msg_id}) não encontrada para guild {player.guild_id} ao atualizar.")
            # Se a mensagem não existe mais, limpa a referência
            del self.now_playing_messages[player.guild_id]
            return
        except Exception as e:
            logger.error(f"Erro ao buscar mensagem 'agora tocando' para guild {player.guild_id}: {e}")
            return

        current_track = player.current
        embed = nextcord.Embed(
            title=f"🎶 Tocando Agora", 
            description=f"**[{current_track.title}]({current_track.uri})**", 
            color=nextcord.Color.blue()
        )
        embed.add_field(name="Duração", value=self.format_duration(current_track.length), inline=True)
        embed.add_field(name="Autor", value=current_track.author, inline=True)
        
        loop_status = "Desativado"
        if player.loop == mafic.LoopType.TRACK: loop_status = "Faixa Atual"
        elif player.loop == mafic.LoopType.QUEUE: loop_status = "Fila Inteira"
        embed.add_field(name="Loop", value=loop_status, inline=True)

        if current_track.artwork_url:
            embed.set_thumbnail(url=current_track.artwork_url)
        
        queue_display = []
        if player.queue:
            for i, item in enumerate(player.queue[:5]): # Mostra as próximas 5
                queue_display.append(f"{i+1}. {item.title} ({self.format_duration(item.length)})")
        
        embed.add_field(name=f"Próximas na Fila ({len(player.queue)})", value="\n".join(queue_display) if queue_display else "Fila vazia", inline=False)
        
        # Corrigido o problema de aspas na f-string
        embed.set_footer(text=f"Adicionado por: {current_track.requester.display_name if current_track.requester else 'Desconhecido'}", 
                         icon_url=current_track.requester.display_avatar.url if current_track.requester else self.bot.user.display_avatar.url)

        try:
            await message.edit(content=None, embed=embed, view=PlayerControls(player, self))
        except Exception as e:
            logger.error(f"Erro ao atualizar mensagem 'agora tocando' para guild {player.guild_id}: {e}")

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

        embed = nextcord.Embed(
            title="🎵 Fila de Músicas",
            color=nextcord.Color.blue()
        )

        # Informações da música atual
        if player.current:
            embed.add_field(
                name="🎶 Tocando Agora",
                value=f"**[{player.current.title}]({player.current.uri})** ({self.format_duration(player.current.length)})\n"
                      f"Adicionado por: {player.current.requester.mention if player.current.requester else 'Desconhecido'}",
                inline=False
            )
        else:
            embed.add_field(
                name="🎶 Tocando Agora",
                value="Nada tocando no momento.",
                inline=False
            )

        # Lista de músicas na fila
        if player.queue:
            queue_list = []
            for i, track in enumerate(player.queue[:10]):  # Limita a 10 músicas para não sobrecarregar o embed
                requester = track.requester.mention if track.requester else "Desconhecido"
                queue_list.append(f"**{i+1}.** [{track.title}]({track.uri}) ({self.format_duration(track.length)}) - {requester}")
            
            remaining = len(player.queue) - 10
            queue_text = "\n".join(queue_list)
            if remaining > 0:
                queue_text += f"\n\n*E mais {remaining} música(s)...*"
            
            embed.add_field(
                name=f"📋 Próximas na Fila ({len(player.queue)})",
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
        if player.loop == mafic.LoopType.TRACK: loop_status = "Faixa Atual"
        elif player.loop == mafic.LoopType.QUEUE: loop_status = "Fila Inteira"
        
        embed.add_field(name="🔁 Loop", value=loop_status, inline=True)
        embed.add_field(name="🔊 Volume", value=f"{player.volume}%", inline=True)
        
        if player.paused:
            embed.add_field(name="⏸️ Status", value="Pausado", inline=True)
        else:
            embed.add_field(name="▶️ Status", value="Tocando", inline=True)

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="pular", description="Pula para a próxima música na fila.")
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
        await interaction.response.send_message("⏭️ Música pulada!")
        # A mensagem de "agora tocando" será atualizada pelo evento on_track_end/on_track_start

    @nextcord.slash_command(name="pausar", description="Pausa a música atual.")
    async def pause(self, interaction: Interaction):
        """Comando para pausar a música atual."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected or not player.current:
            await interaction.response.send_message("Não há nada tocando para pausar.", ephemeral=True)
            return

        if player.paused:
            await interaction.response.send_message("A música já está pausada. Use `/continuar` para retomar.", ephemeral=True)
            return

        await player.pause()
        await interaction.response.send_message("⏸️ Música pausada!")
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="continuar", description="Continua a música pausada.")
    async def resume(self, interaction: Interaction):
        """Comando para continuar a música pausada."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected or not player.current:
            await interaction.response.send_message("Não há nada tocando para continuar.", ephemeral=True)
            return

        if not player.paused:
            await interaction.response.send_message("A música já está tocando. Use `/pausar` para pausar.", ephemeral=True)
            return

        await player.resume()
        await interaction.response.send_message("▶️ Música retomada!")
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="parar", description="Para a música e limpa a fila.")
    async def stop(self, interaction: Interaction):
        """Comando para parar a música e limpar a fila."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return

        player.queue.clear()
        await player.stop()  # Para a música atual
        
        try:
            await player.disconnect(force=True)  # Desconecta do canal de voz
        except Exception as e:
            logger.error(f"Erro ao desconectar player para guild {interaction.guild_id}: {e}")

        # Remove o player da lista do cog
        del self.players[interaction.guild_id]

        await interaction.response.send_message("⏹️ Player parado, fila limpa e bot desconectado.")

        if self.now_playing_messages.get(interaction.guild_id):
            try:
                msg_id, channel_id = self.now_playing_messages[interaction.guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(content="Player desconectado. Use `/tocar` para iniciar novamente.", view=None, embed=None)
                del self.now_playing_messages[interaction.guild_id]
            except nextcord.NotFound:
                logger.warning(f"Mensagem 'agora tocando' não encontrada para guild {interaction.guild_id} ao parar.")
            except Exception as e:
                logger.error(f"Erro ao limpar mensagem 'agora tocando' para guild {interaction.guild_id}: {e}")

    @nextcord.slash_command(name="volume", description="Ajusta o volume da música (0-100).")
    async def volume(
        self,
        interaction: Interaction,
        nivel: int = SlashOption(
            name="nivel",
            description="Nível de volume (0-100)",
            required=True,
            min_value=0,
            max_value=100
        )
    ):
        """Comando para ajustar o volume da música."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return

        await player.set_volume(nivel)
        await interaction.response.send_message(f"🔊 Volume ajustado para {nivel}%.")

    @nextcord.slash_command(name="loop", description="Alterna entre modos de loop (desativado, faixa, fila).")
    async def loop(
        self,
        interaction: Interaction,
        modo: str = SlashOption(
            name="modo",
            description="Modo de loop",
            required=True,
            choices={"Desativado": "none", "Faixa Atual": "track", "Fila Inteira": "queue"}
        )
    ):
        """Comando para alternar entre modos de loop."""
        if not interaction.guild_id or interaction.guild_id not in self.players:
            await interaction.response.send_message("Não há player de música ativo neste servidor.", ephemeral=True)
            return

        player = self.players[interaction.guild_id]
        if not player.connected:
            await interaction.response.send_message("O player de música não está conectado a um canal de voz.", ephemeral=True)
            return

        if modo == "none":
            player.loop = mafic.LoopType.NONE
            await interaction.response.send_message("🔁 Loop desativado.")
        elif modo == "track":
            player.loop = mafic.LoopType.TRACK
            await interaction.response.send_message("🔁 Loop da faixa atual ativado.")
        elif modo == "queue":
            player.loop = mafic.LoopType.QUEUE
            await interaction.response.send_message("🔁 Loop da fila inteira ativado.")

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

        if not player.queue:
            await interaction.response.send_message("A fila está vazia para embaralhar.", ephemeral=True)
            return

        player.queue.shuffle()
        await interaction.response.send_message("🔀 Fila embaralhada!")
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

        logger.info(f"Faixa iniciada: {track.title} em {player.guild.name} ({player.guild.id})")

        # Cria ou atualiza a mensagem de "agora tocando"
        embed = nextcord.Embed(
            title=f"🎶 Tocando Agora",
            description=f"**[{track.title}]({track.uri})**",
            color=nextcord.Color.blue()
        )
        embed.add_field(name="Duração", value=self.format_duration(track.length), inline=True)
        embed.add_field(name="Autor", value=track.author, inline=True)
        
        loop_status = "Desativado"
        if player.loop == mafic.LoopType.TRACK: loop_status = "Faixa Atual"
        elif player.loop == mafic.LoopType.QUEUE: loop_status = "Fila Inteira"
        embed.add_field(name="Loop", value=loop_status, inline=True)

        if track.artwork_url:
            embed.set_thumbnail(url=track.artwork_url)
        
        queue_display = []
        if player.queue:
            for i, item in enumerate(player.queue[:5]):  # Mostra as próximas 5
                queue_display.append(f"{i+1}. {item.title} ({self.format_duration(item.length)})")
        
        embed.add_field(name=f"Próximas na Fila ({len(player.queue)})", value="\n".join(queue_display) if queue_display else "Fila vazia", inline=False)
        
        # Corrigido o problema de aspas na f-string
        embed.set_footer(text=f"Adicionado por: {track.requester.display_name if track.requester else 'Desconhecido'}", 
                         icon_url=track.requester.display_avatar.url if track.requester else self.bot.user.display_avatar.url)

        # Verifica se já existe uma mensagem de "agora tocando" para este servidor
        if player.guild.id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[player.guild.id]
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
                        logger.error(f"Erro ao editar mensagem 'agora tocando' para guild {player.guild.id}: {e}")
            except Exception as e:
                logger.error(f"Erro ao processar mensagem 'agora tocando' existente para guild {player.guild.id}: {e}")

        # Se chegou aqui, precisamos criar uma nova mensagem
        # Encontra o canal de texto mais adequado para enviar a mensagem
        text_channel = None
        
        # Tenta encontrar o canal onde o comando foi executado
        if track.requester and isinstance(track.requester, nextcord.Member):
            for channel in player.guild.text_channels:
                if channel.permissions_for(player.guild.me).send_messages and channel.permissions_for(track.requester).read_messages:
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
                self.now_playing_messages[player.guild.id] = (message.id, text_channel.id)
                logger.info(f"Nova mensagem 'agora tocando' criada para guild {player.guild.id} no canal {text_channel.name}")
            except Exception as e:
                logger.error(f"Erro ao criar mensagem 'agora tocando' para guild {player.guild.id}: {e}")

    @commands.Cog.listener()
    async def on_mafic_track_end(self, player: mafic.Player, track: mafic.Track, reason: str):
        """Evento disparado quando uma faixa termina de tocar."""
        logger.info(f"Faixa terminada: {track.title} em {player.guild.name if player.guild else 'Unknown'} ({player.guild.id if player.guild else 'Unknown'}). Razão: {reason}")
        
        # Se a fila estiver vazia e não houver mais nada tocando, podemos limpar a mensagem de "agora tocando"
        if not player.queue and not player.current and player.guild and player.guild.id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[player.guild.id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(content="Fila vazia. Use `/tocar` para adicionar mais músicas!", embed=None, view=None)
            except Exception as e:
                logger.error(f"Erro ao atualizar mensagem 'agora tocando' após fim da fila para guild {player.guild.id if player.guild else 'Unknown'}: {e}")

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
                    player.queue.clear()
                    
                    try:
                        await player.destroy()
                    except Exception as e_destroy:
                        logger.error(f"Erro ao destruir player após desconexão para guild {member.guild.id}: {e_destroy}")
                    
                    # Remove o player da lista
                    del self.players[member.guild.id]
                    
                    # Atualiza a mensagem de "agora tocando"
                    if member.guild.id in self.now_playing_messages:
                        try:
                            msg_id, channel_id = self.now_playing_messages[member.guild.id]
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                message = await channel.fetch_message(msg_id)
                                await message.edit(content="Bot desconectado do canal de voz. Use `/tocar` para iniciar novamente.", embed=None, view=None)
                            del self.now_playing_messages[member.guild.id]
                        except Exception as e:
                            logger.error(f"Erro ao atualizar mensagem 'agora tocando' após desconexão para guild {member.guild.id}: {e}")
                except Exception as e:
                    logger.error(f"Erro ao limpar player após desconexão para guild {member.guild.id}: {e}")

    @commands.Cog.listener()
    async def on_mafic_node_ready(self, node: mafic.Node):
        """Evento disparado quando um nó Lavalink fica pronto."""
        logger.info(f"Nó Lavalink {node.label} está pronto!")
        
        # Reseta contadores de tentativas de reconexão
        self.reconnect_attempts = {}

    @commands.Cog.listener()
    async def on_mafic_node_unavailable(self, node: mafic.Node):
        """Evento disparado quando um nó Lavalink fica indisponível."""
        logger.warning(f"Nó Lavalink {node.label} ficou indisponível!")
        
        # Tenta reconectar o nó
        try:
            await node.reconnect()
            logger.info(f"Tentativa de reconexão ao nó {node.label} iniciada")
        except Exception as e:
            logger.error(f"Erro ao tentar reconectar ao nó {node.label}: {e}")

    # Tratamento de erros para comandos de aplicação
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        # Verifica se o erro é de um comando desta cog
        if hasattr(interaction, 'application_command'):
            try:
                # Verifica tipos específicos de erros
                if isinstance(error, commands.CommandOnCooldown):
                    await interaction.response.send_message(
                        f"⚠️ Este comando está em cooldown. Tente novamente em {error.retry_after:.1f} segundos.",
                        ephemeral=True
                    )
                elif isinstance(error, mafic.errors.HTTPNotFound):
                    await interaction.response.send_message(
                        f"⚠️ Erro de conexão com o servidor de música. Tente usar o comando `/reconectar` e depois tente novamente.",
                        ephemeral=True
                    )
                    logger.error(f"Erro HTTP 404 do Lavalink: {error}")
                elif isinstance(error, nextcord.errors.InteractionResponded):
                    # Interação já respondida, apenas loga
                    logger.warning(f"Interação já respondida: {error}")
                else:
                    # Erro genérico
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                f"⚠️ Ocorreu um erro ao executar este comando: {str(error)}",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                f"⚠️ Ocorreu um erro ao executar este comando: {str(error)}",
                                ephemeral=True
                            )
                    except Exception as e:
                        logger.error(f"Erro ao enviar mensagem de erro: {e}")
                
                # Loga o erro para debug
                logger.error(f"Erro em comando de música: {error}", exc_info=True)
            except Exception as e:
                logger.error(f"Erro ao tratar erro de comando: {e}", exc_info=True)

# Função setup para carregar a cog
def setup(bot):
    bot.add_cog(Musica(bot))
