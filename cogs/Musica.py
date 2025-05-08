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
        await self.player.disconnect(force=True) # Desconecta do canal de voz

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
        logger.info("--- [COG MUSICA MAFIC] Cog Musica (Mafic) inicializada ---")

    async def get_player(self, interaction: Interaction) -> Optional[mafic.Player]:
        """Obtém ou cria um player para o servidor."""
        if interaction.guild_id in self.players:
            # Verifica se o player ainda está conectado, caso contrário, tenta reconectar ou limpar
            player = self.players[interaction.guild_id]
            if not player.connected:
                logger.warning(f"Player para guild {interaction.guild_id} encontrado mas não conectado. Tentando limpar.")
                try:
                    await player.destroy()
                except Exception as e_destroy:
                    logger.error(f"Erro ao tentar destruir player desconectado para guild {interaction.guild_id}: {e_destroy}")
                del self.players[interaction.guild_id]
            else:
                return player

        if not interaction.guild or not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Você precisa estar em um canal de voz para usar os comandos de música.", ephemeral=True)
            return None

        if not hasattr(self.bot, "mafic_pool") or not self.bot.mafic_pool:
            logger.error("Mafic NodePool não encontrado no bot. O setup_hook do bot falhou?")
            await interaction.response.send_message("Erro crítico: O sistema de música não está inicializado corretamente (NodePool).", ephemeral=True)
            return None

        try:
            # Conecta ao canal de voz e cria o player
            logger.info(f"Tentando conectar ao canal de voz: {interaction.user.voice.channel.name} (ID: {interaction.user.voice.channel.id}) para guild {interaction.guild_id}")
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
            
            self.players[interaction.guild_id] = player
            logger.info(f"Player criado e armazenado para guild {interaction.guild_id} no canal {interaction.user.voice.channel.name}")
            return player
        except mafic.NoNodesAvailable:
            await interaction.response.send_message("Nenhum nó Lavalink disponível para conectar. Tente novamente mais tarde.", ephemeral=True)
            logger.error("Falha ao conectar: Nenhum nó Lavalink disponível.")
            return None
        except Exception as e:
            await interaction.response.send_message(f"Erro ao conectar ao canal de voz: {e}", ephemeral=True)
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
        await interaction.response.defer(ephemeral=False) # Deferir para dar tempo de processar

        player = await self.get_player(interaction)
        if not player:
            # get_player já envia mensagem de erro, então não precisa enviar outra aqui
            # Apenas verificamos se a interação já foi respondida para evitar erro.
            if not interaction.response.is_done():
                 await interaction.followup.send("Não foi possível obter o player de música.", ephemeral=True)
            return

        # Verifica se é uma URL válida ou um termo de busca
        is_url = bool(URL_REGEX.match(busca))
        is_search_term = bool(SEARCH_TERM_REGEX.match(busca)) and not is_url

        tracks: Union[mafic.Playlist, List[mafic.Track], None] = None
        source_type = mafic.Source.YOUTUBE # Padrão para busca

        if is_url:
            logger.info(f"Buscando por URL: {busca} para guild {interaction.guild_id}")
            if "soundcloud.com" in busca:
                source_type = mafic.Source.SOUNDCLOUD
            # Para URLs, incluindo playlists, fetch_tracks é geralmente o melhor
            tracks = await player.fetch_tracks(busca, source_type=None) # Deixa Mafic decidir a fonte pela URL
        elif is_search_term:
            logger.info(f"Buscando por termo: {busca} para guild {interaction.guild_id}")
            # Para termos de busca, usamos search_tracks e especificamos a fonte (ou deixamos padrão)
            tracks = await player.search_tracks(query=busca, source=source_type) 
        else:
            await interaction.followup.send("Entrada inválida. Por favor, forneça uma URL válida (YouTube/SoundCloud) ou um termo de busca (3-500 caracteres).", ephemeral=True)
            return

        if not tracks:
            await interaction.followup.send(f"Nenhuma música encontrada para: `{busca}`", ephemeral=True)
            return

        added_to_queue_count = 0
        first_track_title = ""

        if isinstance(tracks, mafic.Playlist):
            player.queue.extend(tracks.tracks)
            added_to_queue_count = len(tracks.tracks)
            first_track_title = tracks.name # Nome da playlist
            await interaction.followup.send(f"🎶 Playlist **{tracks.name}** ({added_to_queue_count} músicas) adicionada à fila!", ephemeral=False)
        elif isinstance(tracks, list) and tracks: # Lista de faixas (resultado de busca)
            if is_search_term: # Se foi uma busca, geralmente pegamos a primeira e adicionamos
                track_to_add = tracks[0]
                player.queue.append(track_to_add)
                added_to_queue_count = 1
                first_track_title = track_to_add.title
                await interaction.followup.send(f"🎵 **{track_to_add.title}** adicionada à fila!", ephemeral=False)
            else: # Se foi uma URL de faixa única que retornou uma lista (improvável, mas para cobrir)
                player.queue.extend(tracks)
                added_to_queue_count = len(tracks)
                first_track_title = tracks[0].title
                await interaction.followup.send(f"🎵 **{tracks[0].title}** ({added_to_queue_count} música(s)) adicionada(s) à fila!", ephemeral=False)
        else:
            await interaction.followup.send(f"Não foi possível processar o resultado para: `{busca}`", ephemeral=True)
            return

        if not player.current and player.queue:
            await player.play(player.queue.pop(0), start_time=0) # Inicia a primeira música da fila
            # A mensagem de "agora tocando" será tratada por on_track_start
        elif player.current and added_to_queue_count > 0:
            # Se já está tocando e algo foi adicionado, a mensagem de "agora tocando" pode ser atualizada
            # para refletir a fila, se a view estiver ativa.
            await self.update_now_playing_message(player)

    async def update_now_playing_message(self, player: mafic.Player):
        if not player.guild_id or not player.current:
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
            # Se a mensagem não existe mais, talvez criar uma nova? Ou apenas limpar.
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
        embed.set_footer(text=f"Adicionado por: {current_track.requester.display_name if current_track.requester else 'Desconhecido'}", icon_url=current_track.requester.display_avatar.url if current_track.requester else self.bot.user.display_avatar.url)

        await message.edit(content=None, embed=embed, view=PlayerControls(player, self))

    def format_duration(self, milliseconds: int) -> str:
        """Formata duração de milissegundos para HH:MM:SS ou MM:SS."""
        if milliseconds is None: return "N/A"
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @commands.Cog.listener("on_mafic_track_start")
    async def on_mafic_track_start(self, event: mafic.TrackStartEvent[mafic.Player]):
        logger.info(f"TrackStartEvent: {event.track.title} iniciada em {event.player.guild_id}")
        # Envia ou atualiza a mensagem "agora tocando"
        channel = event.player.text_channel # O canal onde o comando /tocar foi usado (se foi armazenado no player)
        
        # Precisamos garantir que text_channel foi definido no player. 
        # Isso geralmente é feito quando o player é criado ou o primeiro comando é usado.
        # Se não foi, tentamos pegar o canal da interação original do /tocar, se disponível.
        # No entanto, o evento não passa a interação original diretamente.
        # Uma forma de contornar é armazenar o canal de texto no player quando o comando /tocar é usado.
        # Vamos assumir que player.text_channel foi definido em algum lugar (ex: no comando /tocar)

        if not channel and event.player.guild_id:
            # Fallback: Tenta encontrar um canal de texto adequado no servidor se player.text_channel não estiver definido.
            # Isso é um paliativo e pode não ser o canal ideal.
            guild = self.bot.get_guild(event.player.guild_id)
            if guild:
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        logger.warning(f"Player.text_channel não definido para guild {event.player.guild_id}. Usando fallback: {ch.name}")
                        break
        
        if not channel:
            logger.error(f"Não foi possível determinar o canal de texto para enviar a mensagem 'agora tocando' para guild {event.player.guild_id}")
            return

        current_track = event.track
        embed = nextcord.Embed(
            title=f"🎶 Tocando Agora", 
            description=f"**[{current_track.title}]({current_track.uri})**", 
            color=nextcord.Color.green()
        )
        embed.add_field(name="Duração", value=self.format_duration(current_track.length), inline=True)
        embed.add_field(name="Autor", value=current_track.author, inline=True)
        
        loop_status = "Desativado"
        if event.player.loop == mafic.LoopType.TRACK: loop_status = "Faixa Atual"
        elif event.player.loop == mafic.LoopType.QUEUE: loop_status = "Fila Inteira"
        embed.add_field(name="Loop", value=loop_status, inline=True)

        if current_track.artwork_url:
            embed.set_thumbnail(url=current_track.artwork_url)

        queue_display = []
        if event.player.queue:
            for i, item in enumerate(event.player.queue[:5]):
                queue_display.append(f"{i+1}. {item.title} ({self.format_duration(item.length)})")
        embed.add_field(name=f"Próximas na Fila ({len(event.player.queue)})", value="\n".join(queue_display) if queue_display else "Fila vazia", inline=False)
        embed.set_footer(text=f"Adicionado por: {current_track.requester.display_name if current_track.requester else 'Desconhecido'}", icon_url=current_track.requester.display_avatar.url if current_track.requester else self.bot.user.display_avatar.url)

        # Verifica se já existe uma mensagem "agora tocando" para este servidor
        existing_message_info = self.now_playing_messages.get(event.player.guild_id)
        if existing_message_info:
            msg_id, _ = existing_message_info
            try:
                message = await channel.fetch_message(msg_id)
                await message.edit(content=None, embed=embed, view=PlayerControls(event.player, self))
                logger.info(f"Mensagem 'agora tocando' atualizada para {event.track.title} em guild {event.player.guild_id}")
            except nextcord.NotFound:
                logger.warning(f"Mensagem 'agora tocando' (ID: {msg_id}) não encontrada para guild {event.player.guild_id}. Criando uma nova.")
                message = await channel.send(embed=embed, view=PlayerControls(event.player, self))
                self.now_playing_messages[event.player.guild_id] = (message.id, channel.id)
            except Exception as e:
                logger.error(f"Erro ao editar mensagem 'agora tocando' para guild {event.player.guild_id}: {e}. Criando uma nova.")
                message = await channel.send(embed=embed, view=PlayerControls(event.player, self))
                self.now_playing_messages[event.player.guild_id] = (message.id, channel.id)
        else:
            message = await channel.send(embed=embed, view=PlayerControls(event.player, self))
            self.now_playing_messages[event.player.guild_id] = (message.id, channel.id)
            logger.info(f"Nova mensagem 'agora tocando' enviada para {event.track.title} em guild {event.player.guild_id}")

    @commands.Cog.listener("on_mafic_track_end")
    async def on_mafic_track_end(self, event: mafic.TrackEndEvent[mafic.Player]):
        logger.info(f"TrackEndEvent: {event.track.title} finalizada em {event.player.guild_id}. Razão: {event.reason}")
        # Se não houver loop da fila e a fila estiver vazia, ou se o player foi parado manualmente
        if (event.player.loop != mafic.LoopType.QUEUE and not event.player.queue) or event.reason == mafic.TrackEndReason.STOPPED:
            if event.player.guild_id in self.now_playing_messages:
                msg_id, channel_id = self.now_playing_messages[event.player.guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(msg_id)
                        await message.edit(content="Fila terminada ou player parado. Use `/tocar` para adicionar mais músicas.", embed=None, view=None)
                        del self.now_playing_messages[event.player.guild_id]
                        logger.info(f"Mensagem 'agora tocando' limpa para guild {event.player.guild_id} após fim da fila/parada.")
                    except nextcord.NotFound:
                        logger.warning(f"Mensagem 'agora tocando' não encontrada para limpar em guild {event.player.guild_id}")
                    except Exception as e:
                        logger.error(f"Erro ao limpar mensagem 'agora tocando' em guild {event.player.guild_id}: {e}")
            
            # Se o player foi parado (não apenas fim da faixa e fila vazia), desconecte
            if event.reason == mafic.TrackEndReason.STOPPED and event.player.connected:
                 # Não desconectar aqui, pois o stop_clear já faz isso. 
                 # Apenas garante que a mensagem seja limpa.
                 pass

        # Mafic lida com a próxima música automaticamente se houver algo na fila e o loop não for apenas da faixa.
        # O evento on_track_start cuidará da nova mensagem "agora tocando".

    @commands.Cog.listener("on_mafic_track_exception")
    async def on_mafic_track_exception(self, event: mafic.TrackExceptionEvent[mafic.Player]):
        logger.error(f"TrackExceptionEvent: Erro ao tocar {event.track.title} em {event.player.guild_id}. Detalhes: {event.exception}")
        if event.player.text_channel:
            await event.player.text_channel.send(f"❌ Erro ao tocar **{event.track.title}**: `{event.exception.message}`")
        # Pode ser útil pular para a próxima música ou limpar o player dependendo da severidade.

    @commands.Cog.listener("on_mafic_websocket_closed")
    async def on_mafic_websocket_closed(self, event: mafic.WebSocketClosedEvent):
        logger.error(f"WebSocketClosedEvent: Conexão com Lavalink fechada para Node {event.node.label}. Código: {event.code}, Razão: {event.reason}, Guild ID: {event.guild_id}")
        # Tentar reconectar ou notificar o usuário pode ser necessário aqui.
        # Se event.guild_id estiver presente, significa que um player específico foi afetado.
        if event.guild_id and event.guild_id in self.players:
            player = self.players[event.guild_id]
            if player.text_channel:
                await player.text_channel.send(f"⚠️ Conexão com o servidor de música perdida (WebSocket fechado). Tentando reconectar em breve ou use `/tocar` novamente.")
            # Poderia tentar player.destroy() ou uma lógica de reconexão mais robusta.

    @commands.Cog.listener("on_mafic_node_ready")
    async def on_mafic_node_ready(self, node: mafic.Node):
        logger.info(f"--- [COG MUSICA MAFIC] Nó Lavalink '{node.label}' está pronto e conectado! Região: {node.region} ---")

    # Função setup para carregar a cog
def setup(bot: commands.Bot):
    logger.info("--- [COG MUSICA MAFIC] Tentando adicionar a cog Musica (Mafic) ao bot ---")
    bot.add_cog(Musica(bot))
    logger.info("--- [COG MUSICA MAFIC] Cog Musica (Mafic) adicionada ao bot ---")
