# /home/ubuntu/ShirayukiBot/cogs/Musica.py (MODIFICADO PARA MAFIC)
import os
import asyncio
import datetime
import random
import nextcord
from nextcord import Interaction, Embed, ButtonStyle, SlashOption, Color, VoiceChannel
from nextcord.ui import View, Button, button # Import button decorator
from nextcord.ext import commands, tasks
import mafic # <--- MUDANÇA: Wavelink para Mafic
import traceback
import re
import math

# Spotify (Credentials are now primarily used by Lavalink server with LavaSrc plugin)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Helper function to format duration (mantida, pois é genérica)
def format_duration(duration_ms):
    try:
        if duration_ms is None:
            return "00:00"
        seconds = int(duration_ms / 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    except Exception as e:
        print(f"❌ Erro em format_duration:")
        traceback.print_exc()
        return "Erro"

# --- Views (Precisarão de adaptação para usar mafic.Player) ---

class MusicControlView(View):
    def __init__(self, cog: commands.Cog):
        super().__init__(timeout=None) # Persistent view
        self.cog = cog
        print("[DEBUG Musica MAFIC] MusicControlView inicializada.")

    async def interaction_check(self, interaction: Interaction) -> bool:
        try:
            print(f"[DEBUG Musica MAFIC] MusicControlView interaction_check por {interaction.user}")
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.response.send_message("❌ Você precisa estar em um canal de voz para usar os controles.", ephemeral=True)
                return False

            player: mafic.Player = interaction.guild.voice_client # <--- MUDANÇA: Tipo do Player
            if not player or not player.connected:
                await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)
                return False

            if player.channel.id != interaction.user.voice.channel.id:
                await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que eu.", ephemeral=True)
                return False

            return True
        except Exception as e:
            print(f"❌ Erro em MusicControlView.interaction_check (MAFIC):")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro interno ao verificar a interação.", ephemeral=True)
            except:
                pass
            return False

    @button(label="⏯️", style=ButtonStyle.gray)
    async def toggle(self, button_obj: Button, interaction: Interaction): # Renomeado 'button' para 'button_obj' para evitar conflito
        try:
            print(f"[DEBUG Musica MAFIC] Botão toggle pressionado por {interaction.user}")
            player: mafic.Player = interaction.guild.voice_client
            if not player:
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)
            
            if player.paused:
                await player.resume()
                status = "resumida"
            else:
                await player.pause()
                status = "pausada"
            await interaction.response.send_message(f"⏯️ Música {status}.", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão toggle (MAFIC):")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao pausar/continuar.", ephemeral=True)
            except:
                pass

    @button(label="⏭️", style=ButtonStyle.blurple)
    async def skip(self, button_obj: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica MAFIC] Botão skip pressionado por {interaction.user}")
            player: mafic.Player = interaction.guild.voice_client
            if not player or not player.current:
                return await interaction.response.send_message("❌ Não estou tocando nada.", ephemeral=True)

            await player.stop() # Mafic usa stop() para pular para o próximo se houver na fila, ou parar se não.
            await interaction.response.send_message("⏭️ Pulando música...", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão skip (MAFIC):")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao pular a música.", ephemeral=True)
            except:
                pass

    @button(label="⏹️", style=ButtonStyle.red)
    async def stop_player(self, button_obj: Button, interaction: Interaction): # Renomeado de 'stop' para 'stop_player'
        try:
            print(f"[DEBUG Musica MAFIC] Botão stop_player pressionado por {interaction.user}")
            player: mafic.Player = interaction.guild.voice_client
            if not player:
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)

            player.queue.clear()
            await player.disconnect(force=True) # force=True pode não ser necessário ou existir, verificar API Mafic

            if interaction.message:
                try:
                    await interaction.message.delete()
                except nextcord.NotFound:
                    pass
                except nextcord.Forbidden:
                    pass
                except Exception as e_del:
                    print(f"[DEBUG Musica MAFIC] Erro (ignorado) ao deletar msg de controle no stop: {e_del}")

            await interaction.response.send_message("⏹️ Reprodução interrompida e bot desconectado.", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão stop_player (MAFIC):")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao parar a reprodução.", ephemeral=True)
            except:
                pass

    @button(label="🔁", style=ButtonStyle.gray)
    async def loop(self, button_obj: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica MAFIC] Botão loop pressionado por {interaction.user}")
            player: mafic.Player = interaction.guild.voice_client
            if not player:
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)

            current_mode = player.loop_type # Mafic usa loop_type (None, CURRENT, QUEUE)
            mode_text = ""

            if current_mode == mafic.LoopType.NONE:
                player.loop_type = mafic.LoopType.CURRENT
                mode_text = "repetição da música atual"
            elif current_mode == mafic.LoopType.CURRENT:
                player.loop_type = mafic.LoopType.QUEUE
                mode_text = "repetição da fila"
            elif current_mode == mafic.LoopType.QUEUE:
                player.loop_type = mafic.LoopType.NONE
                mode_text = "repetição desativada"
            
            await interaction.response.send_message(f"🔁 Modo de {mode_text} ativado.", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão loop (MAFIC):")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao alterar o modo de loop.", ephemeral=True)
            except:
                pass

    @button(label="🔀", style=ButtonStyle.gray)
    async def shuffle(self, button_obj: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica MAFIC] Botão shuffle pressionado por {interaction.user}")
            player: mafic.Player = interaction.guild.voice_client
            if not player or len(player.queue) < 2:
                return await interaction.response.send_message("❌ A fila precisa ter pelo menos 2 músicas para embaralhar.", ephemeral=True)

            random.shuffle(player.queue)
            await interaction.response.send_message("🔀 Fila embaralhada!", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão shuffle (MAFIC):")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao embaralhar a fila.", ephemeral=True)
            except:
                pass

class QueuePaginatorView(View):
    def __init__(self, embeds: list[Embed]):
        super().__init__(timeout=120)
        self.embeds = embeds
        self.page = 0
        self.update_buttons()
        print("[DEBUG Musica MAFIC] QueuePaginatorView inicializada.")

    def update_buttons(self):
        try:
            prev_button = next((item for item in self.children if isinstance(item, Button) and item.custom_id == "prev_queue"), None)
            next_button = next((item for item in self.children if isinstance(item, Button) and item.custom_id == "next_queue"), None)

            if prev_button:
                prev_button.disabled = self.page == 0
            if next_button:
                next_button.disabled = self.page == len(self.embeds) - 1
        except Exception as e:
            print(f"❌ Erro em QueuePaginatorView.update_buttons (MAFIC):")
            traceback.print_exc()

    @button(label="⬅️ Anterior", style=ButtonStyle.gray, custom_id="prev_queue")
    async def prev_page(self, button_obj: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica MAFIC] Botão prev_page (queue) pressionado por {interaction.user}")
            if self.page > 0:
                self.page -= 1
                self.update_buttons()
                await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
            else:
                await interaction.response.defer()
        except Exception as e:
            print(f"❌ Erro no botão prev_page (queue) (MAFIC):")
            traceback.print_exc()

    @button(label="Próxima ➡️", style=ButtonStyle.gray, custom_id="next_queue")
    async def next_page(self, button_obj: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica MAFIC] Botão next_page (queue) pressionado por {interaction.user}")
            if self.page < len(self.embeds) - 1:
                self.page += 1
                self.update_buttons()
                await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
            else:
                await interaction.response.defer()
        except Exception as e:
            print(f"❌ Erro no botão next_page (queue) (MAFIC):")
            traceback.print_exc()

# --- Cog ---

class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_control_messages = {} # guild_id: (channel_id, message_id)
        print("[DEBUG Musica MAFIC] Cog Musica inicializado.")
        # A inicialização do NodePool e dos nós será feita no setup_hook do bot principal
        # ou em um listener on_ready da cog, se preferível.

    # Listener para quando um nó Mafic está pronto
    @commands.Cog.listener()
    async def on_mafic_node_ready(self, node: mafic.Node):
        print(f"✅ Nó Lavalink (Mafic) 	'{node.label}	' conectado e pronto! Região: {node.region}, Sessão: {node.session_id}")
        if hasattr(self.bot, 'lavalink_ready'): # Para compatibilidade com lógica antiga, se houver
            self.bot.lavalink_ready.set()

    @commands.Cog.listener()
    async def on_mafic_track_start(self, event: mafic.TrackStartEvent):
        player = event.player
        track = event.track
        print(f"[DEBUG Musica MAFIC] on_mafic_track_start: Iniciando 	'{track.title}	' em {player.guild.name}")
        
        original_interaction = getattr(track, 'interaction', None) # Recupera a interação original se foi salva
        channel = None

        if original_interaction:
            channel = original_interaction.channel
        elif player.guild:
            text_channels = [ch for ch in player.guild.text_channels if ch.permissions_for(player.guild.me).send_messages]
            if text_channels:
                channel = text_channels[0]
            else:
                print(f"[DEBUG Musica MAFIC] on_mafic_track_start: Nenhum canal de texto encontrado em {player.guild.name}")

        if channel:
            embed = Embed(title="🎧 Tocando agora", color=Color.green())
            embed.description = f"[{track.title}]({track.uri or track.url})"
            if track.artwork_url:
                embed.set_thumbnail(url=track.artwork_url)
            embed.add_field(name="Duração", value=format_duration(track.length))
            if track.requester:
                embed.add_field(name="Pedido por", value=f"<@{track.requester}>" if isinstance(track.requester, int) else track.requester.mention)

            guild_id = player.guild.id
            if guild_id in self.active_control_messages:
                old_channel_id, old_message_id = self.active_control_messages[guild_id]
                try:
                    old_channel = self.bot.get_channel(old_channel_id)
                    if old_channel:
                        old_msg = await old_channel.fetch_message(old_message_id)
                        await old_msg.delete()
                except (nextcord.NotFound, nextcord.Forbidden):
                    pass 
                except Exception as e_del_unk:
                     print(f"❌ Erro INESPERADO ao deletar msg antiga {old_message_id} em on_mafic_track_start:")
                     traceback.print_exc()
                if guild_id in self.active_control_messages:
                    del self.active_control_messages[guild_id]

            try:
                view = MusicControlView(self)
                message = await channel.send(embed=embed, view=view)
                self.active_control_messages[guild_id] = (channel.id, message.id)
            except Exception as e_send:
                print(f"❌ Erro ao enviar mensagem 'Tocando agora' em on_mafic_track_start:")
                traceback.print_exc()
        else:
             print(f"[DEBUG Musica MAFIC] on_mafic_track_start: Não foi possível determinar o canal para enviar a mensagem 'Tocando agora' em {player.guild.name}")

    @commands.Cog.listener()
    async def on_mafic_track_end(self, event: mafic.TrackEndEvent):
        player = event.player
        reason = event.reason
        print(f"[DEBUG Musica MAFIC] on_mafic_track_end: Track ended em {player.guild.name if player else 'Guild Desconhecida'}. Reason: {reason}")
        # Mafic geralmente lida com a próxima música automaticamente se a fila não estiver vazia e o loop não for apenas para a música atual.
        # Se a fila estiver vazia e o loop não estiver ativo, o player para.
        # Se precisar de lógica adicional (ex: mensagem de fila vazia), adicione aqui.
        if reason == mafic.TrackEndReason.FINISHED and not player.queue and player.loop_type != mafic.LoopType.QUEUE:
            # Opcional: enviar mensagem de fila vazia ou player parado
            pass

    @commands.Cog.listener()
    async def on_mafic_track_exception(self, event: mafic.TrackExceptionEvent):
        player = event.player
        track = event.track
        error = event.exception # ou event.message, verificar API
        print(f"❌ ERRO DE REPRODUÇÃO em on_mafic_track_exception (Guild: {player.guild.name if player else '?'}) para '{track.title if track else '?'}' : {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        original_interaction = getattr(track, 'interaction', None)
        channel = None
        if original_interaction:
            channel = original_interaction.channel
        elif player and player.guild:
            text_channels = [ch for ch in player.guild.text_channels if ch.permissions_for(player.guild.me).send_messages]
            if text_channels:
                channel = text_channels[0]

        if channel:
            try:
                await channel.send(f"❌ Ocorreu um erro ao tentar tocar `{track.title if track else 'música desconhecida'}`. Pulando...\n`Erro: {error}`")
            except Exception as e_send:
                print(f"❌ Erro ao enviar mensagem de erro em on_mafic_track_exception:")
                traceback.print_exc()
        
        # Mafic deve tentar tocar o próximo automaticamente após um erro, dependendo da configuração.
        # Se não, pode ser necessário chamar player.skip() ou player.stop() aqui.

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        try:
            if member.id != self.bot.user.id:
                return

            player: mafic.Player = member.guild.voice_client

            if player and after.channel is None: # Bot foi desconectado
                print(f"[DEBUG Musica MAFIC] on_voice_state_update: Bot desconectado do canal de voz em {member.guild.name}")
                guild_id = member.guild.id
                if guild_id in self.active_control_messages:
                    old_channel_id, old_message_id = self.active_control_messages[guild_id]
                    try:
                        channel_obj = self.bot.get_channel(old_channel_id)
                        if channel_obj and isinstance(channel_obj, nextcord.TextChannel):
                            old_msg = await channel_obj.fetch_message(old_message_id)
                            await old_msg.delete()
                    except (nextcord.NotFound, nextcord.Forbidden, AttributeError):
                        pass
                    except Exception as e_del_unk:
                        print(f"❌ Erro INESPERADO ao deletar msg antiga {old_message_id} em on_voice_state_update (MAFIC):")
                        traceback.print_exc()
                    finally:
                        if guild_id in self.active_control_messages:
                            del self.active_control_messages[guild_id]
                # Limpar a fila e destruir o player já é feito pelo disconnect do Mafic
        except Exception as e:
            print(f"❌ Erro GERAL em on_voice_state_update (MAFIC):")
            traceback.print_exc()

    async def ensure_voice(self, interaction: Interaction) -> mafic.Player | None:
        try:
            print(f"[DEBUG Musica MAFIC] ensure_voice chamado por {interaction.user}")
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("❌ Você precisa estar em um canal de voz primeiro!", ephemeral=True)
                return None

            player: mafic.Player = interaction.guild.voice_client
            user_channel = interaction.user.voice.channel

            if not player or not player.connected:
                try:
                    print(f"[DEBUG Musica MAFIC] ensure_voice: Conectando ao canal '{user_channel.name}' em '{interaction.guild.name}'")
                    # Mafic conecta diretamente ao canal de voz do usuário
                    player = await user_channel.connect(cls=mafic.Player, timeout=30.0) 
                    print(f"[DEBUG Musica MAFIC] Bot conectado com sucesso.")
                except asyncio.TimeoutError:
                    print(f"❌ TIMEOUT ao conectar ao canal de voz em ensure_voice (MAFIC)")
                    await interaction.followup.send("❌ Tempo esgotado ao tentar conectar ao canal de voz.", ephemeral=True)
                    return None
                except Exception as e_conn:
                    print(f"❌ Erro ao conectar ao canal de voz em ensure_voice (MAFIC):")
                    traceback.print_exc()
                    await interaction.followup.send(f"❌ Ocorreu um erro ao conectar ao canal de voz: `{e_conn}`", ephemeral=True)
                    return None
            elif player.channel.id != user_channel.id:
                try:
                    print(f"[DEBUG Musica MAFIC] ensure_voice: Movendo para o canal '{user_channel.name}' em '{interaction.guild.name}'")
                    await player.move_to(user_channel)
                    print(f"[DEBUG Musica MAFIC] Bot movido com sucesso.")
                except asyncio.TimeoutError:
                    print(f"❌ TIMEOUT ao mover para o canal de voz em ensure_voice (MAFIC)")
                    await interaction.followup.send("❌ Tempo esgotado ao tentar mover para o seu canal de voz.", ephemeral=True)
                    return None
                except Exception as e_move:
                    print(f"❌ Erro ao mover para o canal de voz em ensure_voice (MAFIC):")
                    traceback.print_exc()
                    await interaction.followup.send(f"❌ Ocorreu um erro ao mover para o seu canal de voz: `{e_move}`", ephemeral=True)
                    return None
            
            # Mafic lida com o volume de forma diferente, geralmente player.set_volume(0-1000)
            # Vamos manter o padrão de 100 (que seria 1.0f ou 100%)
            if player.volume != 100:
                 await player.set_volume(100)
                 print(f"[DEBUG Musica MAFIC] Volume ajustado para 100 em ensure_voice.")

            return player
        except Exception as e:
            print(f"❌ Erro GERAL em ensure_voice (MAFIC):")
            traceback.print_exc()
            try:
                 await interaction.followup.send("❌ Ocorreu um erro interno ao tentar conectar ou mover o bot.", ephemeral=True)
            except:
                 pass
            return None

    # A função play_next_track pode não ser necessária se Mafic gerencia a fila automaticamente
    # async def play_next_track(self, player: mafic.Player):
    #     ...

    async def build_queue_embed(self, player: mafic.Player, page: int = 1):
        try:
            print(f"[DEBUG Musica MAFIC] build_queue_embed chamado para página {page} em {player.guild.name}")
            items_per_page = 10
            queue_list = list(player.queue)
            pages = math.ceil(len(queue_list) / items_per_page) if queue_list else 1
            if page < 1:
                page = 1
            elif page > pages:
                page = pages

            start_index = (page - 1) * items_per_page
            end_index = start_index + items_per_page
            page_items = queue_list[start_index:end_index]

            embed = Embed(title="🎵 Fila de Reprodução", color=Color.blue())

            if player.current:
                current_requester_id = getattr(player.current, 'requester', None)
                current_requester_mention = f"<@{current_requester_id}>" if current_requester_id else 'Desconhecido'
                embed.add_field(name="▶️ Tocando Agora", value=f"[{player.current.title}]({player.current.uri or player.current.url}) ({format_duration(player.current.length)}) - Pedido por: {current_requester_mention}", inline=False)

            if not page_items:
                if page == 1 and not player.current:
                    embed.description = "A fila está vazia!"
                elif page > 1:
                    embed.description = "Não há mais músicas nesta página da fila."
            else:
                queue_text = ""
                for i, track in enumerate(page_items, start=start_index + 1):
                    duration = format_duration(track.length)
                    requester_id = getattr(track, 'requester', None)
                    requester_mention = f"<@{requester_id}>" if requester_id else 'Desconhecido'
                    queue_text += f"`{i}.` [{track.title}]({track.uri or track.url}) ({duration}) - Pedido por: {requester_mention}\n"
                embed.add_field(name=f"Próximas na Fila (Total: {len(player.queue)})", value=queue_text, inline=False)

            if pages > 1:
                embed.set_footer(text=f"Página {page}/{pages}")

            return embed
        except Exception as e:
            print(f"❌ Erro em build_queue_embed (MAFIC):")
            traceback.print_exc()
            error_embed = Embed(title="Erro ao Construir Fila", description="Ocorreu um erro interno.", color=Color.red())
            return error_embed

    # --- Comandos Slash (Adaptados para Mafic) ---

    @nextcord.slash_command(name="tocar", description="Toca uma música ou adiciona à fila.")
    async def tocar(self, interaction: Interaction,
                  busca: str = SlashOption(description="Nome da música, link do YouTube/Spotify ou playlist", required=True)):
        try:
            await interaction.response.defer(ephemeral=False)
            print(f"[DEBUG Musica MAFIC] Comando /tocar recebido: '{busca}' por {interaction.user} em {interaction.guild.name}")

            # Verificar se o NodePool do bot (self.bot.pool) está pronto
            if not hasattr(self.bot, 'mafic_pool') or not self.bot.mafic_pool.nodes:
                 await interaction.followup.send("❌ O bot não está conectado ao servidor de música (pool não iniciado). Contate um administrador.", ephemeral=True)
                 return
            
            # Tenta pegar um nó, se não houver nós disponíveis, informa o usuário.
            try:
                node = self.bot.mafic_pool.get_node() # Pega o melhor nó disponível
                if not node or not node.available:
                    await interaction.followup.send("❌ Nenhum servidor de música disponível no momento. Tente novamente mais tarde.", ephemeral=True)
                    return
            except mafic.NoNodesAvailable:
                await interaction.followup.send("❌ Nenhum servidor de música disponível no momento (NoNodesAvailable). Tente novamente mais tarde.", ephemeral=True)
                return

            player = await self.ensure_voice(interaction)
            if not player:
                print("[DEBUG Musica MAFIC] /tocar: ensure_voice falhou.")
                return

            tracks: list[mafic.Track] | mafic.Playlist | None = None
            # Mafic usa player.fetch_tracks() que pode retornar uma lista de tracks ou uma Playlist
            try:
                print(f"[DEBUG Musica MAFIC] /tocar: Buscando por: {busca}")
                tracks = await player.fetch_tracks(busca)
            except Exception as e_fetch:
                print(f"❌ Erro ao buscar músicas com Mafic: {e_fetch}")
                traceback.print_exc()
                await interaction.followup.send(f"❌ Ocorreu um erro ao buscar suas músicas: `{e_fetch}`", ephemeral=True)
                return

            if not tracks:
                print("[DEBUG Musica MAFIC] /tocar: Nenhuma música encontrada.")
                return await interaction.followup.send("❌ Nenhuma música encontrada com essa busca.", ephemeral=True)

            added_count = 0
            first_track_title = ""
            is_playlist = False

            if isinstance(tracks, mafic.Playlist):
                is_playlist = True
                added_count = len(tracks.tracks)
                first_track_title = tracks.name
                for track in tracks.tracks:
                    track.requester = interaction.user.id # Armazena o ID do requisitante
                    setattr(track, 'interaction', interaction) # Salva a interação original
                    player.queue.put(track)
                print(f"[DEBUG Musica MAFIC] /tocar: Playlist '{tracks.name}' ({added_count} músicas) adicionada à fila.")
                await interaction.followup.send(f"🎶 Playlist **{first_track_title}** ({added_count} músicas) adicionada à fila!")
            elif isinstance(tracks, list): # Lista de tracks (resultado de busca)
                track_to_add = tracks[0]
                track_to_add.requester = interaction.user.id
                setattr(track_to_add, 'interaction', interaction)
                player.queue.put(track_to_add)
                added_count = 1
                first_track_title = track_to_add.title
                print(f"[DEBUG Musica MAFIC] /tocar: Música '{track_to_add.title}' adicionada à fila.")
                await interaction.followup.send(f"🎶 **{first_track_title}** adicionada à fila!")
            else:
                # Caso inesperado
                print(f"[DEBUG Musica MAFIC] /tocar: Tipo de resultado inesperado para tracks: {type(tracks)}")
                return await interaction.followup.send("❌ Ocorreu um erro ao processar o resultado da busca.", ephemeral=True)

            if not player.playing:
                await player.play(player.queue[0]) # Começa a tocar a primeira da fila
        
        except Exception as e:
            print(f"❌ Erro GERAL no comando /tocar (MAFIC):")
            traceback.print_exc()
            try:
                await interaction.followup.send("❌ Ocorreu um erro interno ao processar o comando /tocar.", ephemeral=True)
            except:
                pass

    # ... (Outros comandos como /pular, /parar, /fila, etc. precisarão ser adaptados similarmente)
    # Vou focar no /tocar e nos listeners de evento primeiro para estabelecer a base.

    @nextcord.slash_command(name="pular", description="Pula a música atual.")
    async def pular(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        player: mafic.Player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.followup.send("❌ Não estou tocando nada para pular.", ephemeral=True)
        
        current_title = player.current.title
        await player.stop() # Em Mafic, stop() pula para a próxima se houver, ou para.
        await interaction.followup.send(f"⏭️ Música **{current_title}** pulada.")

    @nextcord.slash_command(name="parar", description="Para a reprodução e desconecta o bot.")
    async def parar(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=False)
        player: mafic.Player = interaction.guild.voice_client
        if not player:
            return await interaction.followup.send("❌ Não estou conectado a nenhum canal de voz.", ephemeral=True)

        player.queue.clear()
        await player.disconnect(force=True) # force=True pode não ser necessário/existir
        await interaction.followup.send("⏹️ Reprodução parada e bot desconectado.")
        # Lógica para deletar mensagem de controle, se aplicável
        guild_id = interaction.guild.id
        if guild_id in self.active_control_messages:
            try:
                channel_id, message_id = self.active_control_messages[guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(message_id)
                    await message.delete()
                del self.active_control_messages[guild_id]
            except Exception as e:
                print(f"[DEBUG Musica MAFIC] Erro ao deletar msg de controle em /parar: {e}")

    @nextcord.slash_command(name="fila", description="Mostra a fila de músicas.")
    async def fila(self, interaction: Interaction, pagina: int = SlashOption(description="Número da página da fila", required=False, default=1)):
        await interaction.response.defer(ephemeral=False)
        player: mafic.Player = interaction.guild.voice_client
        if not player or (not player.current and not player.queue):
            return await interaction.followup.send("ℹ️ Nada tocando e a fila está vazia.", ephemeral=True)

        embed = await self.build_queue_embed(player, page=pagina)
        # Mafic não tem um sistema de paginação de embeds embutido como Wavelink em algumas versões.
        # A view QueuePaginatorView precisaria ser adaptada ou uma lógica de paginação manual implementada aqui.
        # Por simplicidade, vamos enviar a primeira página por enquanto.
        # Para paginação, precisaríamos de uma view mais complexa ou múltiplas mensagens.
        
        # Simplificando para enviar apenas um embed por enquanto, a view de paginação precisaria ser refeita.
        await interaction.followup.send(embed=embed) # View de paginação removida temporariamente

    # ... (Adicionar outros comandos: pausar, continuar, volume, loop, shuffle, conectar, desconectar, agora, buscar)
    # Estes comandos seguirão um padrão similar de adaptação para a API do Mafic.

    @nextcord.slash_command(name="conectar", description="Conecta o bot ao seu canal de voz.")
    async def conectar(self, interaction: Interaction, canal: VoiceChannel = SlashOption(description="Canal de voz para conectar (opcional, usa o seu atual)", required=False)):
        await interaction.response.defer(ephemeral=True)
        target_channel = canal or interaction.user.voice.channel
        if not target_channel:
            return await interaction.followup.send("❌ Você não está em um canal de voz e não especificou um para eu entrar.", ephemeral=True)

        player: mafic.Player = interaction.guild.voice_client
        if player and player.connected:
            if player.channel.id == target_channel.id:
                return await interaction.followup.send(f"✅ Já estou conectado em {target_channel.mention}.", ephemeral=True)
            else:
                await player.move_to(target_channel)
                return await interaction.followup.send(f"↪️ Movido para {target_channel.mention}.", ephemeral=True)
        else:
            try:
                await target_channel.connect(cls=mafic.Player, timeout=30.0)
                await interaction.followup.send(f"✅ Conectado a {target_channel.mention}.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Falha ao conectar a {target_channel.mention}: `{e}`", ephemeral=True)

    @nextcord.slash_command(name="desconectar", description="Desconecta o bot do canal de voz.")
    async def desconectar(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=False)
        player: mafic.Player = interaction.guild.voice_client
        if not player or not player.connected:
            return await interaction.followup.send("❌ Não estou conectado a nenhum canal de voz.", ephemeral=True)
        
        await player.disconnect(force=True)
        await interaction.followup.send("👋 Desconectado do canal de voz.")
        # Limpar mensagem de controle
        guild_id = interaction.guild.id
        if guild_id in self.active_control_messages:
            try:
                channel_id, message_id = self.active_control_messages[guild_id]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(message_id)
                    await message.delete()
                del self.active_control_messages[guild_id]
            except Exception as e:
                print(f"[DEBUG Musica MAFIC] Erro ao deletar msg de controle em /desconectar: {e}")

# Função setup para carregar a cog
def setup(bot: commands.Bot):
    # A inicialização do NodePool do Mafic deve ocorrer no setup_hook do bot principal
    # para garantir que o pool esteja disponível quando a cog for carregada.
    # Exemplo de como seria no bot principal (main.py):
    # async def setup_hook(self):
    #     self.mafic_pool = mafic.NodePool(self)
    #     await self.mafic_pool.create_node(
    #         host="lavalink.jirayu.net",
    #         port=13592,
    #         label="LAVALINK_JIRAYU",
    #         password="youshallnotpass" # Sua senha Lavalink
    #     )
    #     await self.load_extension("cogs.Musica") # Carrega a cog depois do pool
    
    bot.add_cog(Musica(bot))
    print("[DEBUG Musica MAFIC] Cog Musica carregada e adicionada ao bot.")
