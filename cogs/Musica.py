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
                logger.warning(f"Mensagem \'agora tocando\' não encontrada para guild {interaction.guild_id} ao parar.")
            except Exception as e:
                logger.error(f"Erro ao limpar mensagem \'agora tocando\' para guild {interaction.guild_id}: {e}")


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
        logger.info(f"✅ Nó Lavalink (Mafic) \'{node.label}\' conectado e pronto! Região: {node.region}, Sessão: {node.session_id}")

    @commands.Cog.listener()
    async def on_mafic_track_start(self, event: mafic.TrackStartEvent):
        logger.info(f"▶️ Tocando agora: {event.track.title} em {event.player.guild.name}")
        await self.update_now_playing_message(event.player, event.track)

    @commands.Cog.listener()
    async def on_mafic_track_end(self, event: mafic.TrackEndEvent):
        logger.info(f"⏹️ Faixa finalizada: {event.track.title} em {event.player.guild.name}. Razão: {event.reason.name}")
        if not event.player.current and not event.player.queue and event.player.connected:
            if event.player.guild.id in self.now_playing_messages:
                await self.update_now_playing_message(event.player)

    @commands.Cog.listener()
    async def on_mafic_track_exception(self, event: mafic.TrackExceptionEvent):
        logger.error(f"❌ Erro ao tocar {event.track.title} em {event.player.guild.name}: {event.message}", exc_info=event.exception)
        if event.player.guild.id in self.now_playing_messages:
            msg_id, channel_id = self.now_playing_messages[event.player.guild.id]
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(f"⚠️ Ocorreu um erro ao tentar tocar **{event.track.title}**: `{event.message}`. Pulando para a próxima, se houver.", delete_after=30)

    @commands.Cog.listener()
    async def on_mafic_websocket_closed(self, event: mafic.WebSocketClosedEvent):
        logger.warning(f"⚠️ Websocket do Lavalink fechado para Guild {event.guild.id if event.guild else 'Desconhecido'}. Código: {event.code}, Razão: {event.reason}")
        guild_id_to_check = event.guild.id if event.guild else None
        if guild_id_to_check and guild_id_to_check in self.players:
            del self.players[guild_id_to_check]
        if guild_id_to_check and guild_id_to_check in self.now_playing_messages:
            try:
                msg_id, channel_id = self.now_playing_messages[guild_id_to_check]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(content="Conexão com o sistema de áudio perdida. Tente usar `/conectar` ou `/tocar` novamente.", embed=None, view=None)
                del self.now_playing_messages[guild_id_to_check]
            except Exception as e:
                logger.error(f"Erro ao limpar mensagem \'agora tocando\' após websocket closed: {e}")

    @nextcord.slash_command(name="tocar", description="Toca uma música ou adiciona à fila. Use URL ou nome da música.")
    async def tocar(self, interaction: Interaction, busca: str = SlashOption(description="URL da música/playlist (YouTube, SoundCloud) ou nome para buscar", required=True)):
        
        player = await self.get_player(interaction)
        if not player:
            return

        await interaction.response.defer(ephemeral=False)

        if not URL_REGEX.match(busca) and not SEARCH_TERM_REGEX.match(busca):
            await interaction.followup.send("Entrada inválida. Por favor, forneça uma URL válida (YouTube, SoundCloud) ou um termo de busca (3-500 caracteres).", ephemeral=True)
            return

        try:
            tracks: Union[mafic.Playlist, List[mafic.Track]] = await player.fetch_tracks(busca, requester=interaction.user)
        except mafic.TrackLoadFailed as e:
            logger.error(f"Falha ao carregar faixa/playlist \'{busca}\': {e.message} (Severidade: {e.severity.name})")
            await interaction.followup.send(f"😥 Não consegui carregar sua música/playlist: `{e.message}`. Verifique o link ou tente outra busca.", ephemeral=True)
            return
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar faixas \'{busca}\': {e}", exc_info=True)
            await interaction.followup.send("😥 Ocorreu um erro inesperado ao buscar suas músicas. Tente novamente.", ephemeral=True)
            return

        if not tracks:
            await interaction.followup.send("Não encontrei nada para essa busca. Verifique o link ou tente outras palavras-chave.", ephemeral=True)
            return

        if isinstance(tracks, mafic.Playlist):
            player.queue.extend(tracks.tracks)
            await interaction.followup.send(f"🎶 Playlist **{tracks.name}** ({len(tracks.tracks)} músicas) adicionada à fila!")
            logger.info(f"Playlist {tracks.name} adicionada à fila por {interaction.user} em {interaction.guild.name}.")
        else: # É uma lista de faixas (geralmente uma única faixa de uma busca)
            player.queue.append(tracks[0])
            await interaction.followup.send(f"🎵 **{tracks[0].title}** adicionada à fila!")
            logger.info(f"Faixa {tracks[0].title} adicionada à fila por {interaction.user} em {interaction.guild.name}.")

        if not player.current:
            await player.play(player.queue.pop(0)) # Inicia a primeira música se nada estiver tocando
        
        # Envia ou atualiza a mensagem "agora tocando"
        if interaction.guild_id not in self.now_playing_messages:
            # Se não há mensagem, cria uma nova
            msg_content = "Iniciando player..."
            if player.current:
                msg_content = None # Será preenchido pelo update_now_playing_message
            
            now_playing_embed = nextcord.Embed(title="🎶 Player de Música 🎶", description="Carregando informações...", color=nextcord.Color.blue())
            message = await interaction.channel.send(content=msg_content, embed=now_playing_embed, view=PlayerControls(player, self))
            self.now_playing_messages[interaction.guild_id] = (message.id, message.channel.id)
        
        await self.update_now_playing_message(player) # Atualiza com a faixa atual e a fila

    @nextcord.slash_command(name="fila", description="Mostra a fila de músicas atual.")
    async def fila(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.current:
            await interaction.response.send_message("Não há nada tocando ou na fila no momento.", ephemeral=True)
            return

        embed = nextcord.Embed(title="🎶 Fila de Músicas 🎶", color=nextcord.Color.gold())
        
        if player.current:
            embed.add_field(name="Tocando Agora", value=f"**[{player.current.title}]({player.current.uri})** ({self.format_duration(player.current.length)}) - Adicionado por: {player.current.requester.display_name if player.current.requester else 'Desconhecido'}", inline=False)
        
        queue_display = []
        if player.queue:
            for i, track in enumerate(player.queue[:10]): # Mostra as próximas 10
                queue_display.append(f"{i+1}. **{track.title}** ({self.format_duration(track.length)}) - Adicionado por: {track.requester.display_name if track.requester else 'Desconhecido'}")
            embed.description = "\n".join(queue_display)
            if len(player.queue) > 10:
                embed.set_footer(text=f"... e mais {len(player.queue) - 10} música(s).")
        else:
            embed.description = "A fila está vazia após a música atual."

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="conectar", description="Conecta o bot ao seu canal de voz atual.")
    async def conectar(self, interaction: Interaction):
        player = await self.get_player(interaction)
        if player and player.connected:
            await interaction.response.send_message(f"Já estou conectado em {player.channel.name}!", ephemeral=True)
        elif player: # Conectou com sucesso via get_player
            await interaction.response.send_message(f"Conectado a {player.channel.name}!", ephemeral=True)
        # Se player for None, get_player já enviou a mensagem de erro.

    @nextcord.slash_command(name="desconectar", description="Desconecta o bot do canal de voz.")
    async def desconectar(self, interaction: Interaction):
        player = self.players.get(interaction.guild_id)
        if not player or not player.connected:
            await interaction.response.send_message("Não estou conectado a nenhum canal de voz.", ephemeral=True)
            return

        await player.disconnect(force=True)
        if interaction.guild_id in self.players:
            del self.players[interaction.guild_id]
        
        await interaction.response.send_message("Desconectado do canal de voz.", ephemeral=True)
        if self.now_playing_messages.get(interaction.guild_id):
            try:
                msg_id, channel_id = self.now_playing_messages[interaction.guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(msg_id)
                    await message.edit(content="Player desconectado. Use `/tocar` para iniciar novamente.", view=None, embed=None)
                del self.now_playing_messages[interaction.guild_id]
            except Exception as e:
                logger.error(f"Erro ao limpar mensagem \'agora tocando\' ao desconectar: {e}")

def setup(bot):
    logger.info("--- [COG MUSICA MAFIC] Tentando adicionar Cog Musica (Mafic) ao bot ---")
    bot.add_cog(Musica(bot))
    logger.info("--- [COG MUSICA MAFIC] Cog Musica (Mafic) adicionada ao bot ---")
