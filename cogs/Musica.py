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

logger = logging.getLogger('discord_bot.musica_mafic')

# Regex para validar URLs do YouTube e Soundcloud, e termos de busca
URL_REGEX = re.compile(
    r"^(?:(?:https?:)?//)?(?:www\.)?"
    r"(?:(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/|playlist\?list=))"
    r"|(?:youtu\.be/)|(?:soundcloud\.com/[^/]+(?:/(?:sets/)?[^/]+)?))"
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
        self.players = {} # guild_id: mafic.Player
        self.now_playing_messages = {} # guild_id: (message_id, channel_id)
        logger.info("--- [COG MUSICA MAFIC] Cog Musica (Mafic) inicializada ---")

    async def get_player(self, interaction: Interaction) -> Optional[mafic.Player]:
        """Obtém ou cria um player para o servidor."""
        if interaction.guild_id in self.players:
            return self.players[interaction.guild_id]

        if not interaction.guild or not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Você precisa estar em um canal de voz para usar os comandos de música.", ephemeral=True)
            return None

        # Tenta conectar ao NodePool do bot
        if not hasattr(self.bot, 'mafic_pool') or not self.bot.mafic_pool:
            logger.error("Mafic NodePool não encontrado no bot. O setup_hook do bot falhou?")
            await interaction.response.send_message("Erro crítico: O sistema de música não está inicializado corretamente (NodePool).", ephemeral=True)
            return None
            
        try:
            # Conecta ao canal de voz e cria o player
            player: mafic.Player = await interaction.user.voice.channel.connect(cls=mafic.Player, self_deaf=True)
            self.players[interaction.guild_id] = player
            logger.info(f"Player criado e conectado para guild {interaction.guild_id} no canal {interaction.user.voice.channel.name}")
            return player
        except mafic.NoNodesAvailable:
            await interaction.response.send_message("Nenhum nó Lavalink disponível para conectar. Tente novamente mais tarde.", ephemeral=True)
            logger.error("Falha ao conectar: Nenhum nó Lavalink disponível.")
            return None
        except Exception as e:
            await interaction.response.send_message(f"Erro ao conectar ao canal de voz: {e}", ephemeral=True)
            logger.error(f"Erro ao conectar ao canal de voz para guild {interaction.guild_id}: {e}", exc_info=True)
            return None

    async def update_now_playing_message(self, player: mafic.Player, track: Optional[mafic.Track] = None):
        guild_id = player.guild.id
        if guild_id not in self.now_playing_messages:
            return

        message_id, channel_id = self.now_playing_messages[guild_id]
        channel = self.bot.get_channel(channel_id)
        if not channel:
            del self.now_playing_messages[guild_id]
            return

        try:
            message = await channel.fetch_message(message_id)
        except nextcord.NotFound:
            del self.now_playing_messages[guild_id]
            return
        
        if not player.current and not player.queue:
            await message.edit(content="Fila vazia e nada tocando. Use `/tocar` para adicionar músicas.", embed=None, view=None)
            del self.now_playing_messages[guild_id] # Remove para não tentar atualizar mais
            return

        current_track = track or player.current
        if not current_track: # Se ainda não há faixa (ex: após pular e a fila estar vazia)
             await message.edit(content="Fila vazia. Use `/tocar` para adicionar músicas.", embed=None, view=PlayerControls(player, self))
             return

        embed = nextcord.Embed(title="🎶 Agora Tocando 🎶", color=nextcord.Color.blue())
        embed.description = f"**[{current_track.title}]({current_track.uri})**"
        embed.add_field(name="Autor", value=current_track.author, inline=True)
        embed.add_field(name="Duração", value=self.format_duration(current_track.length), inline=True)
        embed.add_field(name="Fonte", value=current_track.source.capitalize(), inline=True)
        
        loop_mode_text = "Desativado"
        if player.loop == mafic.LoopType.TRACK: loop_mode_text = "Faixa Atual"
        elif player.loop == mafic.LoopType.QUEUE: loop_mode_text = "Fila Inteira"
        embed.add_field(name="Loop", value=loop_mode_text, inline=True)
        embed.add_field(name="Volume", value=f"{player.volume}%", inline=True)

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

    @commands.Cog.listener()
    async def on_mafic_node_ready(self, node: mafic.Node):
        logger.info(f"✅ Nó Lavalink (Mafic) '{node.label}' conectado e pronto! Região: {node.region}, Sessão: {node.session_id}")

    @commands.Cog.listener()
    async def on_mafic_track_start(self, event: mafic.TrackStartEvent):
        logger.info(f"▶️ Tocando agora: {event.track.title} em {event.player.guild.name}")
        await self.update_now_playing_message(event.player, event.track)

    @commands.Cog.listener()
    async def on_mafic_track_end(self, event: mafic.TrackEndEvent):
        logger.info(f"⏹️ Faixa finalizada: {event.track.title} em {event.player.guild.name}. Razão: {event.reason.name}")
        # Mafic lida com a próxima música automaticamente se houver algo na fila e o loop não for TRACK.
        # Se a fila estiver vazia e o loop não estiver ativo, o player para.
        # A mensagem de "agora tocando" será atualizada pelo on_mafic_track_start da próxima música,
        # ou precisaremos de uma lógica para limpar se a fila acabar.
        if not event.player.current and not event.player.queue and event.player.connected:
             # Se não há próxima música e a fila está vazia, atualiza a mensagem para "fila vazia"
            if event.player.guild.id in self.now_playing_messages:
                await self.update_now_playing_message(event.player) # Isso deve mostrar "fila vazia"
        # Se o player foi destruído (ex: bot desconectado), não faz nada aqui.

    @commands.Cog.listener()
    async def on_mafic_track_exception(self, event: mafic.TrackExceptionEvent):
        logger.error(f"❌ Erro ao tocar {event.track.title} em {event.player.guild.name}: {event.message}", exc_info=event.exception)
        if event.player.guild.id in self.now_playing_messages:
            msg_id, channel_id = self.now_playing_messages[event.player.guild.id]
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(f"⚠️ Ocorreu um erro ao tentar tocar **{event.track.title}**: `{event.message}`. Pulando para a próxima, se houver.", delete_after=30)
        # A lógica de pular para a próxima é geralmente tratada pelo Lavalink/Mafic dependendo da severidade.

    @commands.Cog.listener()
    async def on_mafic_websocket_closed(self, event: mafic.WebsocketClosedEvent):
        logger.warning(f"⚠️ Websocket do Lavalink fechado para Guild {event.guild_id}. Código: {event.code}, Razão: {event.reason}")
        # Aqui você pode tentar reconectar ou limpar o player
        if event.guild_id in self.players:
            del self.players[event.guild_id]
        if event.guild_id in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[event.guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(content="Conexão com o sistema de áudio perdida. Tente usar `/conectar` ou `/tocar` novamente.", embed=None, view=None)
                del self.now_playing_messages[event.guild_id]
            except Exception as e:
                logger.error(f"Erro ao limpar mensagem 'agora tocando' após websocket closed: {e}")

    @nextcord.slash_command(name="tocar", description="Toca uma música ou adiciona à fila. Use URL ou nome da música.")
    async def tocar(self, interaction: Interaction, busca: str = SlashOption(description="URL da música/playlist (YouTube, SoundCloud) ou nome para buscar", required=True)):
        
        player = await self.get_player(interaction)
        if not player:
            # get_player já envia mensagem de erro se necessário
            return

        await interaction.response.defer(ephemeral=False) # Deferir para buscas longas

        if not URL_REGEX.match(busca) and not SEARCH_TERM_REGEX.match(busca):
            await interaction.followup.send("Entrada inválida. Por favor, forneça uma URL válida (YouTube, SoundCloud) ou um termo de busca (3-500 caracteres).", ephemeral=True)
            return

        try:
            tracks: Union[mafic.Playlist, List[mafic.Track]] = await player.fetch_tracks(busca, requester=interaction.user)
        except mafic.TrackLoadFailed as e:
            logger.error(f"Falha ao carregar faixa/playlist '{busca}': {e.message} (Severidade: {e.severity.name})")
            await interaction.followup.send(f"😥 Não consegui carregar sua música/playlist: `{e.message}`. Verifique o link ou tente outra busca.", ephemeral=True)
            return
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar faixas '{busca}': {e}", exc_info=True)
            await interaction.followup.send("😥 Ocorreu um erro inesperado ao buscar suas músicas. Tente novamente.", ephemeral=True)
            return

        if not tracks:
            await interaction.followup.send(f"😥 Nenhuma música encontrada para `{busca}`.", ephemeral=True)
            return

        added_to_queue_message = ""

        if isinstance(tracks, mafic.Playlist):
            player.add_tracks(tracks.tracks)
            added_to_queue_message = f"🎶 Playlist **{tracks.name}** ({len(tracks.tracks)} músicas) adicionada à fila!"
            logger.info(f"Playlist '{tracks.name}' ({len(tracks.tracks)} músicas) adicionada por {interaction.user.name}")
        else: # É uma lista de faixas (geralmente uma, de busca)
            player.add_tracks(tracks)
            track_names = ", ".join([t.title for t in tracks])
            added_to_queue_message = f"🎶 **{track_names}** adicionada à fila!"
            logger.info(f"Faixa(s) '{track_names}' adicionada(s) por {interaction.user.name}")

        if not player.current: # Se nada estava tocando, inicia o player
            await player.play()
            # A mensagem de "agora tocando" será criada/atualizada pelo on_mafic_track_start
            # Mas precisamos criar a mensagem base aqui se ela não existir
            if interaction.guild_id not in self.now_playing_messages:
                now_playing_embed = nextcord.Embed(title="🎶 Carregando player...", color=nextcord.Color.light_grey())
                msg = await interaction.followup.send(embed=now_playing_embed, view=PlayerControls(player, self))
                self.now_playing_messages[interaction.guild_id] = (msg.id, interaction.channel_id)
            else: # Se a mensagem já existe, apenas envia a confirmação de adição
                 await interaction.followup.send(added_to_queue_message)
        else: # Se já estava tocando, apenas adiciona à fila e envia a mensagem
            await interaction.followup.send(added_to_queue_message)
            await self.update_now_playing_message(player) # Atualiza a mensagem com a nova fila

    @nextcord.slash_command(name="fila", description="Mostra a fila de músicas atual.")
    async def fila(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.queue:
            await interaction.response.send_message("A fila está vazia!", ephemeral=True)
            return

        embed = nextcord.Embed(title="🎵 Fila de Músicas 🎵", color=nextcord.Color.blurple())
        
        if player.current:
            embed.add_field(name="Tocando Agora", value=f"**[{player.current.title}]({player.current.uri})** ({self.format_duration(player.current.length)})", inline=False)

        queue_display = []
        total_duration_ms = 0
        for i, track in enumerate(player.queue):
            total_duration_ms += track.length
            if i < 10: # Limita a exibição para as primeiras 10 na mensagem
                queue_display.append(f"{i+1}. **{track.title}** ({self.format_duration(track.length)})")
        
        if queue_display:
            embed.description = "\n".join(queue_display)
            if len(player.queue) > 10:
                embed.description += f"\n... e mais {len(player.queue) - 10} música(s)."
        else: # Isso não deveria acontecer se player.queue é verdadeiro, mas por segurança
            embed.description = "A fila está vazia."

        embed.set_footer(text=f"Total de músicas na fila: {len(player.queue)} | Duração total da fila: {self.format_duration(total_duration_ms)}")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="pular", description="Pula a música atual.")
    async def pular(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.current:
            await interaction.response.send_message("Não há nada tocando para pular.", ephemeral=True)
            return
        
        track_title = player.current.title
        await player.stop() # Mafic lida com a próxima música
        await interaction.response.send_message(f"⏭️ **{track_title}** pulada!")

    @nextcord.slash_command(name="parar", description="Para a música, limpa a fila e desconecta o bot.")
    async def parar(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player:
            await interaction.response.send_message("O player não está ativo.", ephemeral=True)
            return

        player.queue.clear()
        await player.stop()
        await player.disconnect(force=True)
        
        if interaction.guild_id in self.players:
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
                pass # Mensagem já foi deletada ou não encontrada
            except Exception as e:
                logger.error(f"Erro ao limpar mensagem 'agora tocando' ao parar (comando): {e}")

    @nextcord.slash_command(name="pausar", description="Pausa a música atual.")
    async def pausar(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.current:
            await interaction.response.send_message("Não há nada tocando para pausar.", ephemeral=True)
            return
        if player.paused:
            await interaction.response.send_message("A música já está pausada.", ephemeral=True)
            return
            
        await player.pause()
        await interaction.response.send_message("⏸️ Música pausada.")
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="continuar", description="Continua a música pausada.")
    async def continuar(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.current:
            await interaction.response.send_message("Não há nada tocando para continuar.", ephemeral=True)
            return
        if not player.paused:
            await interaction.response.send_message("A música não está pausada.", ephemeral=True)
            return

        await player.resume()
        await interaction.response.send_message("▶️ Música retomada.")
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="volume", description="Ajusta o volume do player (0-1000).")
    async def volume(self, interaction: Interaction, nivel: int = SlashOption(description="Nível do volume (0 a 1000)", required=True, min_value=0, max_value=1000)):
        player = self.players.get(interaction.guild_id)
        if not player:
            await interaction.response.send_message("O player não está ativo para ajustar o volume.", ephemeral=True)
            return
        
        await player.set_volume(nivel)
        await interaction.response.send_message(f"🔊 Volume ajustado para {nivel}%. instalments")
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="loop", description="Define o modo de loop (faixa, fila ou desligado).")
    async def loop(self, interaction: Interaction, modo: str = SlashOption(description="Modo de loop", choices={"desligado": "off", "faixa": "track", "fila": "queue"}, required=True)):
        player = self.players.get(interaction.guild_id)
        if not player:
            await interaction.response.send_message("O player não está ativo.", ephemeral=True)
            return

        if modo == "off":
            player.loop = mafic.LoopType.NONE
            await interaction.response.send_message("🔁 Loop desativado.")
        elif modo == "track":
            player.loop = mafic.LoopType.TRACK
            await interaction.response.send_message("🔁 Loop da faixa atual ativado.")
        elif modo == "fila":
            player.loop = mafic.LoopType.QUEUE
            await interaction.response.send_message("🔁 Loop da fila ativado.")
        await self.update_now_playing_message(player)

    @nextcord.slash_command(name="shuffle", description="Embaralha a fila de músicas.")
    async def shuffle(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.queue:
            await interaction.response.send_message("A fila está vazia para embaralhar.", ephemeral=True)
            return
        
        player.queue.shuffle()
        await interaction.response.send_message("🔀 Fila embaralhada!")
        await self.update_now_playing_message(player) # Para atualizar a exibição da fila

    @nextcord.slash_command(name="conectar", description="Conecta o bot ao seu canal de voz.")
    async def conectar(self, interaction: Interaction, canal: Optional[nextcord.VoiceChannel] = SlashOption(description="Canal de voz para conectar (opcional, usa o seu canal atual se não especificado)", channel_types=[ChannelType.voice, ChannelType.stage_voice], required=False)):
        target_channel = canal or interaction.user.voice.channel if interaction.user.voice else None
        if not target_channel:
            await interaction.response.send_message("Você não está em um canal de voz e não especificou um para conectar.", ephemeral=True)
            return

        player = self.players.get(interaction.guild_id)
        if player and player.connected and player.channel.id == target_channel.id:
            await interaction.response.send_message(f"Já estou conectado em {target_channel.mention}.", ephemeral=True)
            return
        
        if player and player.connected: # Conectado em outro canal
            await player.disconnect() # Desconecta do antigo antes de mover

        try:
            new_player: mafic.Player = await target_channel.connect(cls=mafic.Player, self_deaf=True)
            self.players[interaction.guild_id] = new_player
            await interaction.response.send_message(f"👋 Conectado em {target_channel.mention}!")
            logger.info(f"Bot conectado ao canal {target_channel.name} por comando /conectar.")
        except Exception as e:
            await interaction.response.send_message(f"Erro ao tentar conectar em {target_channel.mention}: {e}", ephemeral=True)
            logger.error(f"Erro no comando /conectar para {target_channel.name}: {e}", exc_info=True)

    @nextcord.slash_command(name="desconectar", description="Desconecta o bot do canal de voz.")
    async def desconectar(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.connected:
            await interaction.response.send_message("Não estou conectado a um canal de voz.", ephemeral=True)
            return
        
        channel_name = player.channel.name
        player.queue.clear()
        await player.stop()
        await player.disconnect(force=True)
        if interaction.guild_id in self.players:
            del self.players[interaction.guild_id]
        await interaction.response.send_message(f"👋 Desconectado de {channel_name}.")
        if self.now_playing_messages.get(interaction.guild_id):
            try:
                msg_id, channel_id = self.now_playing_messages[interaction.guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(content="Player desconectado. Use `/tocar` para iniciar novamente.", view=None, embed=None)
                del self.now_playing_messages[interaction.guild_id]
            except nextcord.NotFound:
                pass
            except Exception as e:
                logger.error(f"Erro ao limpar mensagem 'agora tocando' ao desconectar: {e}")

    @nextcord.slash_command(name="agora", description="Mostra informações sobre a música que está tocando.")
    async def agora(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.current:
            await interaction.response.send_message("Nada está tocando no momento.", ephemeral=True)
            return

        # Reutiliza a lógica de criar a mensagem de "agora tocando"
        # Para garantir que a mensagem seja enviada no canal do comando e não apenas atualizada
        current_track = player.current
        embed = nextcord.Embed(title="🎶 Agora Tocando 🎶", color=nextcord.Color.blue())
        embed.description = f"**[{current_track.title}]({current_track.uri})**"
        embed.add_field(name="Autor", value=current_track.author, inline=True)
        embed.add_field(name="Duração", value=self.format_duration(current_track.length), inline=True)
        embed.add_field(name="Fonte", value=current_track.source.capitalize(), inline=True)
        
        loop_mode_text = "Desativado"
        if player.loop == mafic.LoopType.TRACK: loop_mode_text = "Faixa Atual"
        elif player.loop == mafic.LoopType.QUEUE: loop_mode_text = "Fila Inteira"
        embed.add_field(name="Loop", value=loop_mode_text, inline=True)
        embed.add_field(name="Volume", value=f"{player.volume}%", inline=True)

        if current_track.artwork_url:
            embed.set_thumbnail(url=current_track.artwork_url)
        
        embed.set_footer(text=f"Adicionado por: {current_track.requester.display_name if current_track.requester else 'Desconhecido'}", icon_url=current_track.requester.display_avatar.url if current_track.requester else self.bot.user.display_avatar.url)
        
        # Envia uma nova mensagem em vez de tentar atualizar uma existente, pois este é um comando de informação
        await interaction.response.send_message(embed=embed, view=PlayerControls(player, self))


def setup(bot: commands.Bot):
    bot.add_cog(Musica(bot))
    logger.info("--- [COG MUSICA MAFIC] Cog Musica (Mafic) adicionada ao bot via setup() ---")
