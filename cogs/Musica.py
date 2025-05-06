# /home/ubuntu/jsbot/cogs/Musica.py (MODIFICADO COM DEBUG)
import os
import asyncio
import datetime
import random
import nextcord
from nextcord import Interaction, Embed, ButtonStyle, SlashOption, Color, VoiceChannel
from nextcord.ui import View, Button, button # Import button decorator
from nextcord.ext import commands, tasks
import wavelinkcord as wavelink
import traceback
import re
import math

# Spotify (Credentials are now primarily used by Lavalink server with LavaSrc plugin)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Helper function to format duration
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

# --- Views ---

class MusicControlView(View):
    def __init__(self, cog):
        super().__init__(timeout=None) # Persistent view
        self.cog = cog
        print("[DEBUG Musica] MusicControlView inicializada.")

    async def interaction_check(self, interaction: Interaction) -> bool:
        try:
            print(f"[DEBUG Musica] MusicControlView interaction_check por {interaction.user}")
            # Check if the user is in the same voice channel as the bot
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.response.send_message("❌ Você precisa estar em um canal de voz para usar os controles.", ephemeral=True)
                return False

            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)
                return False

            if player.channel.id != interaction.user.voice.channel.id:
                await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que eu.", ephemeral=True)
                return False

            return True
        except Exception as e:
            print(f"❌ Erro em MusicControlView.interaction_check:")
            traceback.print_exc()
            # Tenta notificar o usuário sobre o erro interno
            try:
                await interaction.response.send_message("❌ Ocorreu um erro interno ao verificar a interação.", ephemeral=True)
            except:
                pass
            return False

    @button(label="⏯️", style=ButtonStyle.gray)
    async def toggle(self, button: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Botão toggle pressionado por {interaction.user}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player:
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)

            await player.pause(not player.paused)
            status = "pausada" if player.paused else "resumida"
            await interaction.response.send_message(f"⏯️ Música {status}.", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão toggle:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao pausar/continuar.", ephemeral=True)
            except:
                pass

    @button(label="⏭️", style=ButtonStyle.blurple)
    async def skip(self, button: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Botão skip pressionado por {interaction.user}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.current:
                return await interaction.response.send_message("❌ Não estou tocando nada.", ephemeral=True)

            await player.skip(force=True)
            await interaction.response.send_message("⏭️ Pulando música...", ephemeral=True)
            # A mensagem de "tocando agora" será enviada pelo evento on_track_start
        except Exception as e:
            print(f"❌ Erro no botão skip:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao pular a música.", ephemeral=True)
            except:
                pass

    @button(label="⏹️", style=ButtonStyle.red)
    async def stop(self, button: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Botão stop pressionado por {interaction.user}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player:
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)

            player.queue.clear()
            await player.disconnect()

            # Remover a mensagem de controle se existir
            if interaction.message:
                try:
                    await interaction.message.delete()
                except nextcord.NotFound:
                    pass # Mensagem já foi deletada
                except nextcord.Forbidden:
                    pass # Sem permissão para deletar
                except Exception as e_del:
                    print(f"[DEBUG Musica] Erro (ignorado) ao deletar msg de controle no stop: {e_del}")

            await interaction.response.send_message("⏹️ Reprodução interrompida e bot desconectado.", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão stop:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao parar a reprodução.", ephemeral=True)
            except:
                pass

    @button(label="🔁", style=ButtonStyle.gray)
    async def loop(self, button: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Botão loop pressionado por {interaction.user}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player:
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)

            current_mode = player.queue.mode
            next_mode = wavelink.QueueMode.loop
            mode_text = "repetição da música atual"

            if current_mode == wavelink.QueueMode.loop:
                next_mode = wavelink.QueueMode.loop_all
                mode_text = "repetição da fila"
            elif current_mode == wavelink.QueueMode.loop_all:
                next_mode = wavelink.QueueMode.normal
                mode_text = "repetição desativada"

            player.queue.mode = next_mode
            await interaction.response.send_message(f"🔁 Modo de {mode_text} ativado.", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão loop:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao alterar o modo de loop.", ephemeral=True)
            except:
                pass

    @button(label="🔀", style=ButtonStyle.gray)
    async def shuffle(self, button: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Botão shuffle pressionado por {interaction.user}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or player.queue.count < 2:
                return await interaction.response.send_message("❌ A fila precisa ter pelo menos 2 músicas para embaralhar.", ephemeral=True)

            player.queue.shuffle()
            await interaction.response.send_message("🔀 Fila embaralhada!", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no botão shuffle:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao embaralhar a fila.", ephemeral=True)
            except:
                pass

class QueuePaginatorView(View):
    def __init__(self, embeds):
        super().__init__(timeout=120) # Aumentar timeout
        self.embeds = embeds
        self.page = 0
        self.update_buttons()
        print("[DEBUG Musica] QueuePaginatorView inicializada.")

    def update_buttons(self):
        try:
            # Desabilitar/Habilitar botões conforme a página
            prev_button = next((item for item in self.children if isinstance(item, Button) and item.custom_id == "prev"), None)
            next_button = next((item for item in self.children if isinstance(item, Button) and item.custom_id == "next"), None)

            if prev_button:
                prev_button.disabled = self.page == 0
            if next_button:
                next_button.disabled = self.page == len(self.embeds) - 1
        except Exception as e:
            print(f"❌ Erro em QueuePaginatorView.update_buttons:")
            traceback.print_exc()

    @button(label="⬅️ Anterior", style=ButtonStyle.gray, custom_id="prev")
    async def prev_page(self, button: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Botão prev_page pressionado por {interaction.user}")
            if self.page > 0:
                self.page -= 1
                self.update_buttons()
                await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
            else:
                await interaction.response.defer() # Apenas reconhece a interação se já estiver na primeira página
        except Exception as e:
            print(f"❌ Erro no botão prev_page:")
            traceback.print_exc()
            # Não envia mensagem de erro aqui para não poluir

    @button(label="Próxima ➡️", style=ButtonStyle.gray, custom_id="next")
    async def next_page(self, button: Button, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Botão next_page pressionado por {interaction.user}")
            if self.page < len(self.embeds) - 1:
                self.page += 1
                self.update_buttons()
                await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
            else:
                await interaction.response.defer() # Apenas reconhece a interação se já estiver na última página
        except Exception as e:
            print(f"❌ Erro no botão next_page:")
            traceback.print_exc()
            # Não envia mensagem de erro aqui para não poluir

# --- Cog ---

class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_control_messages = {} # guild_id: (channel_id, message_id)
        print("[DEBUG Musica] Cog Musica inicializado.")
        # self.autoleave.start() # Mantendo autoleave desativado conforme solicitado

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        """Evento chamado quando um nó Lavalink está pronto."""
        try:
            print(f"✅ Nó Lavalink 	'{payload.node.identifier}	' (Sessão: {payload.session_id}) está pronto!")
            # Sinaliza no bot principal que o Lavalink está pronto (se o evento estiver lá)
            if hasattr(self.bot, 'lavalink_ready'):
                self.bot.lavalink_ready.set()
        except Exception as e:
            print(f"❌ Erro em on_wavelink_node_ready:")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """Evento chamado quando uma música começa a tocar."""
        try:
            player = payload.player
            if not player or not player.current:
                print("[DEBUG Musica] on_wavelink_track_start: Player ou current track ausente.")
                return

            track = player.current
            print(f"[DEBUG Musica] on_wavelink_track_start: Iniciando 	'{track.title}	' em {player.guild.name}")
            original_interaction = getattr(track, 'interaction', None) # Recupera a interação original se foi salva
            channel = None

            if original_interaction:
                channel = original_interaction.channel
            elif player.guild:
                # Tenta encontrar um canal de texto adequado no servidor
                text_channels = [ch for ch in player.guild.text_channels if ch.permissions_for(player.guild.me).send_messages]
                if text_channels:
                    channel = text_channels[0] # Usa o primeiro canal de texto disponível
                else:
                    print(f"[DEBUG Musica] on_wavelink_track_start: Nenhum canal de texto encontrado em {player.guild.name}")

            if channel:
                embed = Embed(title="🎧 Tocando agora", color=Color.green())
                embed.description = f"[{track.title}]({track.uri or track.url})"
                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)
                embed.add_field(name="Duração", value=format_duration(track.length))
                if track.requester:
                    embed.add_field(name="Pedido por", value=track.requester.mention)

                # Limpar mensagem de controle antiga se existir
                guild_id = player.guild.id
                if guild_id in self.active_control_messages:
                    old_channel_id, old_message_id = self.active_control_messages[guild_id]
                    try:
                        old_channel = self.bot.get_channel(old_channel_id)
                        if old_channel:
                            old_msg = await old_channel.fetch_message(old_message_id)
                            await old_msg.delete()
                            print(f"[DEBUG Musica] Mensagem de controle antiga ({old_message_id}) no canal {old_channel_id} deletada para guild {guild_id}")
                        else:
                            print(f"[DEBUG Musica] Canal antigo {old_channel_id} não encontrado para deletar msg {old_message_id} em on_track_start.")
                    except (nextcord.NotFound, nextcord.Forbidden) as e_del:
                        print(f"[DEBUG Musica] Erro (ignorado) ao deletar msg antiga {old_message_id} em on_track_start: {e_del}")
                        pass # Ignora se não encontrar ou não tiver permissão
                    except Exception as e_del_unk:
                         print(f"❌ Erro INESPERADO ao deletar msg antiga {old_message_id} em on_track_start:")
                         traceback.print_exc()
                    # Garante que a chave seja removida mesmo se a deleção falhar
                    if guild_id in self.active_control_messages:
                        del self.active_control_messages[guild_id]

                try:
                    view = MusicControlView(self)
                    message = await channel.send(embed=embed, view=view)
                    self.active_control_messages[guild_id] = (channel.id, message.id) # Store channel_id and message_id
                    print(f"[DEBUG Musica] Nova mensagem de controle enviada para guild {guild_id}: ({channel.id}, {message.id})")
                except Exception as e_send:
                    print(f"❌ Erro ao enviar mensagem 'Tocando agora' em on_wavelink_track_start:")
                    traceback.print_exc()
            else:
                 print(f"[DEBUG Musica] on_wavelink_track_start: Não foi possível determinar o canal para enviar a mensagem 'Tocando agora' em {player.guild.name}")

        except Exception as e:
            print(f"❌ Erro GERAL em on_wavelink_track_start:")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Evento chamado quando uma música termina."""
        try:
            player = payload.player
            reason = payload.reason
            print(f"[DEBUG Musica] on_wavelink_track_end: Track ended em {player.guild.name if player else 'Guild Desconhecida'}. Reason: {reason}")
            # Wavelink v3+ lida com a fila automaticamente
            # Se a razão for FINISHED e a fila estiver vazia (e sem loop), o player para.
            # Se precisar de lógica adicional (ex: mensagem de fila vazia), adicione aqui.
        except Exception as e:
            print(f"❌ Erro em on_wavelink_track_end:")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        """Evento chamado quando ocorre um erro durante a reprodução."""
        try:
            player = payload.player
            track = payload.track
            error = payload.error
            print(f"❌ ERRO DE REPRODUÇÃO em on_wavelink_track_exception (Guild: {player.guild.name if player else '?'}) para 	'{track.title if track else '?'}	': {error}")
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
                    print(f"❌ Erro ao enviar mensagem de erro em on_wavelink_track_exception:")
                    traceback.print_exc()

            # Tenta pular para a próxima música
            if player and player.is_connected():
                try:
                    await player.skip(force=True)
                    print(f"[DEBUG Musica] on_wavelink_track_exception: Pulando música após erro.")
                except Exception as e_skip:
                    print(f"❌ Erro ao tentar pular música após exceção em on_wavelink_track_exception:")
                    traceback.print_exc()
        except Exception as e:
            print(f"❌ Erro GERAL em on_wavelink_track_exception:")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        """Listener para eventos de estado de voz (entrar/sair/mover)."""
        try:
            # Ignora se o membro não for o próprio bot
            if member.id != self.bot.user.id:
                return

            player: wavelink.Player = member.guild.voice_client

            # Bot foi desconectado do canal de voz
            if player and after.channel is None:
                print(f"[DEBUG Musica] on_voice_state_update: Bot desconectado do canal de voz em {member.guild.name}")
                guild_id = member.guild.id
                if guild_id in self.active_control_messages:
                    old_channel_id, old_message_id = self.active_control_messages[guild_id]
                    try:
                        channel = self.bot.get_channel(old_channel_id)
                        if channel and isinstance(channel, nextcord.TextChannel):
                            old_msg = await channel.fetch_message(old_message_id)
                            await old_msg.delete()
                            print(f"[DEBUG Musica] Mensagem de controle ({old_message_id}) deletada após desconexão para guild {guild_id}")
                        else:
                            print(f"[DEBUG Musica] Não foi possível encontrar o canal {old_channel_id} da mensagem de controle antiga para guild {guild_id}")
                    except (nextcord.NotFound, nextcord.Forbidden, AttributeError) as e_del:
                        print(f"[DEBUG Musica] Erro (ignorado) ao deletar msg antiga {old_message_id} em on_voice_state_update: {e_del}")
                        pass # Ignora se não encontrar, não tiver permissão ou canal/player não existir mais
                    except Exception as e_del_unk:
                        print(f"❌ Erro INESPERADO ao deletar msg antiga {old_message_id} em on_voice_state_update:")
                        traceback.print_exc()
                    finally:
                        if guild_id in self.active_control_messages:
                            del self.active_control_messages[guild_id]
                # Limpa a fila e destrói o player associado ao servidor
                try:
                    # Wavelink pode já ter desconectado, mas garantir
                    if player.is_connected():
                        await player.disconnect(force=True)
                        print(f"[DEBUG Musica] Player desconectado forçadamente em on_voice_state_update para guild {guild_id}")
                except Exception as e_disc:
                    print(f"[DEBUG Musica] Erro (ignorado) ao tentar desconectar player em on_voice_state_update: {e_disc}")
        except Exception as e:
            print(f"❌ Erro GERAL em on_voice_state_update:")
            traceback.print_exc()

    async def ensure_voice(self, interaction: Interaction) -> wavelink.Player | None:
        """Garante que o bot esteja conectado ao canal de voz do usuário."""
        try:
            print(f"[DEBUG Musica] ensure_voice chamado por {interaction.user}")
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("❌ Você precisa estar em um canal de voz primeiro!", ephemeral=True)
                return None

            player: wavelink.Player = interaction.guild.voice_client
            user_channel = interaction.user.voice.channel

            if not player:
                try:
                    print(f"[DEBUG Musica] ensure_voice: Conectando ao canal 	'{user_channel.name}	' em 	'{interaction.guild.name}	'")
                    player = await user_channel.connect(cls=wavelink.Player, timeout=30) # Timeout aumentado
                    print(f"[DEBUG Musica] Bot conectado com sucesso.")
                except asyncio.TimeoutError:
                    print(f"❌ TIMEOUT ao conectar ao canal de voz em ensure_voice")
                    await interaction.followup.send("❌ Tempo esgotado ao tentar conectar ao canal de voz.", ephemeral=True)
                    return None
                except Exception as e_conn:
                    print(f"❌ Erro ao conectar ao canal de voz em ensure_voice:")
                    traceback.print_exc()
                    await interaction.followup.send(f"❌ Ocorreu um erro ao conectar ao canal de voz: `{e_conn}`", ephemeral=True)
                    return None
            elif player.channel.id != user_channel.id:
                try:
                    print(f"[DEBUG Musica] ensure_voice: Movendo para o canal 	'{user_channel.name}	' em 	'{interaction.guild.name}	'")
                    await player.move_to(user_channel)
                    print(f"[DEBUG Musica] Bot movido com sucesso.")
                except asyncio.TimeoutError:
                    print(f"❌ TIMEOUT ao mover para o canal de voz em ensure_voice")
                    await interaction.followup.send("❌ Tempo esgotado ao tentar mover para o seu canal de voz.", ephemeral=True)
                    return None
                except Exception as e_move:
                    print(f"❌ Erro ao mover para o canal de voz em ensure_voice:")
                    traceback.print_exc()
                    await interaction.followup.send(f"❌ Ocorreu um erro ao mover para o seu canal de voz: `{e_move}`", ephemeral=True)
                    return None

            # Define o volume padrão se não estiver definido ou for muito baixo/alto
            try:
                if player.volume < 10 or player.volume > 150: # Ajustado max_value do comando volume
                    await player.set_volume(100)
                    print(f"[DEBUG Musica] Volume ajustado para 100 em ensure_voice.")
            except Exception as e_vol:
                 print(f"[DEBUG Musica] Erro (ignorado) ao setar volume em ensure_voice: {e_vol}")

            return player
        except Exception as e:
            print(f"❌ Erro GERAL em ensure_voice:")
            traceback.print_exc()
            try:
                 await interaction.followup.send("❌ Ocorreu um erro interno ao tentar conectar ou mover o bot.", ephemeral=True)
            except:
                 pass
            return None

    async def play_next_track(self, player: wavelink.Player):
        """Toca a próxima música da fila, se houver."""
        try:
            print(f"[DEBUG Musica] play_next_track chamado para player em {player.guild.name}")
            if player.is_playing() or player.queue.is_empty:
                status = "já tocando" if player.is_playing() else "fila vazia"
                print(f"[DEBUG Musica] play_next_track: Saindo ({status}).")
                return

            next_track = player.queue.get()
            print(f"[DEBUG Musica] play_next_track: Tocando próxima: 	'{next_track.title}	'")
            await player.play(next_track)

        except wavelink.QueueEmpty:
            print("[DEBUG Musica] play_next_track: Fila vazia ao tentar obter próxima música.")
            # Opcional: Enviar mensagem de fila vazia?
        except Exception as e:
            print(f"❌ Erro em play_next_track:")
            traceback.print_exc()

    async def build_queue_embed(self, player: wavelink.Player, page: int = 1):
        """Constrói embeds paginados para a fila de reprodução."""
        try:
            print(f"[DEBUG Musica] build_queue_embed chamado para página {page} em {player.guild.name}")
            items_per_page = 10
            pages = math.ceil(player.queue.count / items_per_page) if player.queue.count > 0 else 1
            if page < 1:
                page = 1
            elif page > pages:
                page = pages

            start_index = (page - 1) * items_per_page
            end_index = start_index + items_per_page

            queue_list = list(player.queue)
            page_items = queue_list[start_index:end_index]

            embed = Embed(title="🎵 Fila de Reprodução", color=Color.blue())

            if player.current:
                current_requester = player.current.requester.mention if player.current.requester else 'Desconhecido'
                embed.add_field(name="▶️ Tocando Agora", value=f"[{player.current.title}]({player.current.uri or player.current.url}) ({format_duration(player.current.length)}) - Pedido por: {current_requester}", inline=False)

            if not page_items:
                if page == 1 and not player.current: # Só mostra fila vazia se nada estiver tocando
                    embed.description = "A fila está vazia!"
                elif page > 1:
                    embed.description = "Não há mais músicas nesta página da fila."
                # Se page == 1 e current existe, não adiciona descrição
            else:
                queue_text = ""
                for i, track in enumerate(page_items, start=start_index + 1):
                    duration = format_duration(track.length)
                    requester = track.requester.mention if track.requester else 'Desconhecido'
                    queue_text += f"`{i}.` [{track.title}]({track.uri or track.url}) ({duration}) - Pedido por: {requester}\n"
                embed.add_field(name=f"Próximas na Fila (Total: {player.queue.count})", value=queue_text, inline=False)

            if pages > 1:
                embed.set_footer(text=f"Página {page}/{pages}")

            return embed
        except Exception as e:
            print(f"❌ Erro em build_queue_embed:")
            traceback.print_exc()
            # Retorna um embed de erro simples
            error_embed = Embed(title="Erro ao Construir Fila", description="Ocorreu um erro interno.", color=Color.red())
            return error_embed

    # --- Comandos Slash ---

    @nextcord.slash_command(name="tocar", description="Toca uma música ou adiciona à fila.")
    async def tocar(self, interaction: Interaction,
                  busca: str = SlashOption(description="Nome da música, link do YouTube/Spotify ou playlist", required=True)):
        try:
            await interaction.response.defer(ephemeral=False) # Resposta inicial visível
            print(f"[DEBUG Musica] Comando /tocar recebido: \t'{busca}\t' por {interaction.user} em {interaction.guild.name}")

            # --- Adicionar verificação de nó conectado ---
            node = wavelink.Pool.get_node() # Use Pool instead of NodePool
            if not node or node.status != wavelink.NodeStatus.CONNECTED:
                print("[DEBUG Musica] /tocar: Nenhum nó Lavalink conectado encontrado.")
                await interaction.followup.send("❌ O bot não está conectado ao servidor de música no momento. Tente novamente mais tarde ou contate um administrador.", ephemeral=True)
                return
            # --- Fim da verificação ---

            player = await self.ensure_voice(interaction)
            if not player:
                print("[DEBUG Musica] /tocar: ensure_voice falhou.")
                return # ensure_voice já enviou a mensagem de erro

            tracks: wavelink.SearchableTrack | wavelink.Playlist | list[wavelink.Playable] | None = None
            search_type = "Busca"

            # Verifica se é URL (simplificado)
            if re.match(r"https?://", busca):
                search_type = "URL"
                print(f"[DEBUG Musica] /tocar: Buscando por URL: {busca}")
                # Usar fetch_tracks para URLs, pode retornar Playlist ou lista de Track
                tracks = await wavelink.Pool.fetch_tracks(busca)
            else:
                # Tenta busca no YouTube Music por padrão
                search_type = "Texto (YTM)"
                print(f"[DEBUG Musica] /tocar: Buscando por texto (YouTube Music): {busca}")
                tracks = await wavelink.Playable.search(busca, source=wavelink.TrackSource.YouTubeMusic)
                if not tracks:
                    # Se não encontrar no YTM, tenta no YouTube normal
                    search_type = "Texto (YT)"
                    print(f"[DEBUG Musica] /tocar: Buscando por texto (YouTube): {busca}")
                    tracks = await wavelink.Playable.search(busca, source=wavelink.TrackSource.YouTube)

            if not tracks:
                print("[DEBUG Musica] /tocar: Nenhuma música encontrada.")
                return await interaction.followup.send("❌ Nenhuma música encontrada com essa busca.", ephemeral=True)

            added_count = 0
            first_track_title = ""
            is_playlist = False

            if isinstance(tracks, wavelink.Playlist):
                search_type = "Playlist"
                is_playlist = True
                added_count = len(tracks.tracks)
                first_track_title = tracks.name
                # Adiciona todas as músicas da playlist à fila
                for track in tracks.tracks:
                    setattr(track, 'requester', interaction.user)
                    setattr(track, 'interaction', interaction) # Salva a interação original
                    player.queue.put(track)
                print(f"[DEBUG Musica] /tocar: Playlist 	'{tracks.name}	' ({added_count} músicas) adicionada à fila.")
            elif isinstance(tracks, list):
                 # Resultado de busca (lista de tracks) ou URL de vídeo único
                if not tracks: # Verifica se a lista está vazia (caso raro)
                     print("[DEBUG Musica] /tocar: Lista de tracks vazia após busca/fetch.")
                     return await interaction.followup.send("❌ Nenhuma música encontrada com essa busca.", ephemeral=True)
                track = tracks[0] # Pega a primeira música da busca ou o vídeo único
                setattr(track, 'requester', interaction.user)
                setattr(track, 'interaction', interaction) # Salva a interação original
                first_track_title = track.title
                player.queue.put(track)
                added_count = 1
                print(f"[DEBUG Musica] /tocar: Música 	'{track.title}	' adicionada à fila.")
            else: # Caso inesperado (talvez um único Track de fetch_tracks?)
                 if isinstance(tracks, wavelink.Playable):
                     track = tracks
                     setattr(track, 'requester', interaction.user)
                     setattr(track, 'interaction', interaction)
                     first_track_title = track.title
                     player.queue.put(track)
                     added_count = 1
                     print(f"[DEBUG Musica] /tocar: Música única (tipo {type(tracks)}) 	'{track.title}	' adicionada à fila.")
                 else:
                    print(f"[DEBUG Musica] /tocar: Tipo de resultado inesperado: {type(tracks)}")
                    return await interaction.followup.send("❌ Ocorreu um erro inesperado ao processar a busca.", ephemeral=True)

            # Envia mensagem de confirmação
            if is_playlist:
                await interaction.followup.send(f"✅ Playlist **{first_track_title}** ({added_count} músicas) adicionada à fila!")
            else:
                await interaction.followup.send(f"✅ **{first_track_title}** adicionado à fila!")

            # Se não estiver tocando nada, começa a tocar
            if not player.is_playing():
                print("[DEBUG Musica] /tocar: Player não estava tocando, iniciando play_next_track.")
                await self.play_next_track(player)
            else:
                 print("[DEBUG Musica] /tocar: Player já estava tocando.")

        except Exception as e:
            print(f"❌ Erro CRÍTICO no comando /tocar:")
            traceback.print_exc()
            try:
                await interaction.followup.send("❌ Ocorreu um erro interno ao tentar tocar a música. Verifique os logs.", ephemeral=True)
            except:
                 pass # Falha ao enviar followup

    @nextcord.slash_command(name="pular", description="Pula a música atual.")
    async def pular(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /pular recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)
            if not player.current:
                return await interaction.response.send_message("❌ Não há música tocando para pular.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel.id != player.channel.id:
                 return await interaction.response.send_message("❌ Você precisa estar no meu canal de voz para pular.", ephemeral=True)

            print(f"[DEBUG Musica] /pular: Pulando 	'{player.current.title}	'")
            await player.skip(force=True)
            await interaction.response.send_message("⏭️ Música pulada!")
            # O evento on_track_start cuidará de tocar a próxima, se houver
        except Exception as e:
            print(f"❌ Erro no comando /pular:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar pular a música.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="parar", description="Para a reprodução e desconecta o bot.")
    async def parar(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /parar recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel.id != player.channel.id:
                 return await interaction.response.send_message("❌ Você precisa estar no meu canal de voz para parar.", ephemeral=True)

            print(f"[DEBUG Musica] /parar: Limpando fila e desconectando.")
            player.queue.clear()
            await player.disconnect(force=True)

            # Remover a mensagem de controle se existir
            guild_id = interaction.guild.id
            if guild_id in self.active_control_messages:
                try:
                    # Tenta usar o canal da interação atual, mais confiável
                    old_msg = await interaction.channel.fetch_message(self.active_control_messages[guild_id])
                    await old_msg.delete()
                    print(f"[DEBUG Musica] Mensagem de controle deletada via /parar para guild {guild_id}")
                except (nextcord.NotFound, nextcord.Forbidden) as e_del:
                     print(f"[DEBUG Musica] Erro (ignorado) ao deletar msg antiga em /parar: {e_del}")
                     pass
                except Exception as e_del_unk:
                     print(f"❌ Erro INESPERADO ao deletar msg antiga em /parar:")
                     traceback.print_exc()
                finally:
                    if guild_id in self.active_control_messages:
                        del self.active_control_messages[guild_id]

            await interaction.response.send_message("⏹️ Reprodução interrompida e bot desconectado.")
        except Exception as e:
            print(f"❌ Erro no comando /parar:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar parar a reprodução.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="fila", description="Mostra a fila de reprodução atual.")
    async def fila(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /fila recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

            if player.queue.is_empty and not player.current:
                return await interaction.response.send_message("ℹ️ A fila está vazia e nada está tocando.", ephemeral=True)

            # Constrói múltiplos embeds se a fila for grande
            items_per_page = 10
            total_items = player.queue.count
            total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1
            embeds = []
            print(f"[DEBUG Musica] /fila: Construindo {total_pages} páginas para {total_items} itens.")

            for page_num in range(1, total_pages + 1):
                embed = await self.build_queue_embed(player, page=page_num)
                embeds.append(embed)

            if not embeds: # Caso algo dê errado ou a fila esteja vazia mas tenha current
                 print("[DEBUG Musica] /fila: Lista de embeds vazia, construindo página 1.")
                 embed = await self.build_queue_embed(player, page=1)
                 embeds.append(embed)

            view = QueuePaginatorView(embeds) if len(embeds) > 1 else None
            await interaction.response.send_message(embed=embeds[0], view=view)
            print(f"[DEBUG Musica] /fila: Enviada página 1 com {'View' if view else 'sem View'}.")

        except Exception as e:
            print(f"❌ Erro no comando /fila:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar mostrar a fila.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="pausar", description="Pausa a música atual.")
    async def pausar(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /pausar recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)
            if not player.is_playing():
                return await interaction.response.send_message("❌ Não há música tocando para pausar.", ephemeral=True)
            if player.paused:
                return await interaction.response.send_message("⏸️ A música já está pausada.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel.id != player.channel.id:
                 return await interaction.response.send_message("❌ Você precisa estar no meu canal de voz.", ephemeral=True)

            await player.pause(True)
            await interaction.response.send_message("⏸️ Música pausada.")
        except Exception as e:
            print(f"❌ Erro no comando /pausar:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar pausar a música.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="continuar", description="Continua a música pausada.")
    async def continuar(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /continuar recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)
            if not player.paused:
                return await interaction.response.send_message("▶️ A música não está pausada.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel.id != player.channel.id:
                 return await interaction.response.send_message("❌ Você precisa estar no meu canal de voz.", ephemeral=True)

            await player.pause(False)
            await interaction.response.send_message("▶️ Música continuada.")
        except Exception as e:
            print(f"❌ Erro no comando /continuar:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar continuar a música.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="volume", description="Ajusta o volume do bot (0 a 150).")
    async def volume(self, interaction: Interaction,
                   nivel: int = SlashOption(description="Nível do volume (0-150)", required=True, min_value=0, max_value=150)):
        try:
            print(f"[DEBUG Musica] Comando /volume {nivel} recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel.id != player.channel.id:
                 return await interaction.response.send_message("❌ Você precisa estar no meu canal de voz.", ephemeral=True)

            await player.set_volume(nivel)
            await interaction.response.send_message(f"🔊 Volume ajustado para {nivel}%.")
        except Exception as e:
            print(f"❌ Erro no comando /volume:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar ajustar o volume.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="loop", description="Ativa/desativa a repetição (música atual, fila ou desligado).")
    async def loop_cmd(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /loop recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel.id != player.channel.id:
                 return await interaction.response.send_message("❌ Você precisa estar no meu canal de voz.", ephemeral=True)

            current_mode = player.queue.mode
            next_mode = wavelink.QueueMode.loop
            mode_text = "repetição da música atual"

            if current_mode == wavelink.QueueMode.loop:
                next_mode = wavelink.QueueMode.loop_all
                mode_text = "repetição da fila"
            elif current_mode == wavelink.QueueMode.loop_all:
                next_mode = wavelink.QueueMode.normal
                mode_text = "repetição desativada"

            player.queue.mode = next_mode
            await interaction.response.send_message(f"🔁 Modo de {mode_text} ativado.")
        except Exception as e:
            print(f"❌ Erro no comando /loop:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar alterar o modo de repetição.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="shuffle", description="Embaralha a fila de reprodução.")
    async def shuffle_cmd(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /shuffle recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)
            if player.queue.count < 2:
                return await interaction.response.send_message("❌ A fila precisa ter pelo menos 2 músicas para embaralhar.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel.id != player.channel.id:
                 return await interaction.response.send_message("❌ Você precisa estar no meu canal de voz.", ephemeral=True)

            player.queue.shuffle()
            await interaction.response.send_message("🔀 Fila embaralhada!")
        except Exception as e:
            print(f"❌ Erro no comando /shuffle:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar embaralhar a fila.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="conectar", description="Conecta o bot ao seu canal de voz.")
    async def conectar(self, interaction: Interaction,
                     canal: VoiceChannel = SlashOption(description="Canal de voz para conectar (opcional, padrão: seu canal)", required=False)):
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"[DEBUG Musica] Comando /conectar recebido por {interaction.user} em {interaction.guild.name}")
            target_channel = canal or interaction.user.voice.channel if interaction.user.voice else None

            if not target_channel:
                return await interaction.followup.send("❌ Você precisa estar em um canal de voz ou especificar um canal para eu conectar.", ephemeral=True)

            player: wavelink.Player = interaction.guild.voice_client
            if player and player.is_connected():
                if player.channel.id == target_channel.id:
                    return await interaction.followup.send(f"ℹ️ Já estou conectado em `{target_channel.name}`.", ephemeral=True)
                else:
                    print(f"[DEBUG Musica] /conectar: Movendo para 	'{target_channel.name}	'")
                    await player.move_to(target_channel)
                    await interaction.followup.send(f"✅ Movido para `{target_channel.name}`.", ephemeral=True)
            else:
                print(f"[DEBUG Musica] /conectar: Conectando a 	'{target_channel.name}	'")
                await target_channel.connect(cls=wavelink.Player, timeout=30)
                await interaction.followup.send(f"✅ Conectado a `{target_channel.name}`.", ephemeral=True)
        except Exception as e:
            print(f"❌ Erro no comando /conectar:")
            traceback.print_exc()
            try:
                await interaction.followup.send("❌ Ocorreu um erro ao tentar conectar/mover.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="desconectar", description="Desconecta o bot do canal de voz.")
    async def desconectar(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /desconectar recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.is_connected():
                return await interaction.response.send_message("❌ Não estou conectado a nenhum canal de voz.", ephemeral=True)
            if not interaction.user.voice or interaction.user.voice.channel.id != player.channel.id:
                 return await interaction.response.send_message("❌ Você precisa estar no meu canal de voz para me desconectar.", ephemeral=True)

            print(f"[DEBUG Musica] /desconectar: Desconectando.")
            await player.disconnect(force=True)
            await interaction.response.send_message("👋 Bot desconectado.")
        except Exception as e:
            print(f"❌ Erro no comando /desconectar:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar desconectar.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="agora", description="Mostra a música que está tocando agora.")
    async def agora(self, interaction: Interaction):
        try:
            print(f"[DEBUG Musica] Comando /agora recebido por {interaction.user} em {interaction.guild.name}")
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.current:
                return await interaction.response.send_message("❌ Nada está tocando no momento.", ephemeral=True)

            track = player.current
            position = format_duration(player.position)
            total = format_duration(track.length)

            embed = Embed(title="🎧 Tocando Agora", color=Color.blurple())
            embed.description = f"[{track.title}]({track.uri or track.url})"
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
            embed.add_field(name="Progresso", value=f"{position} / {total}")
            if track.requester:
                embed.add_field(name="Pedido por", value=track.requester.mention)
            if player.queue.mode != wavelink.QueueMode.normal:
                 loop_mode_name = player.queue.mode.name.replace('_', ' ').capitalize()
                 embed.add_field(name="Modo Loop", value=loop_mode_name)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"❌ Erro no comando /agora:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Ocorreu um erro ao tentar mostrar a música atual.", ephemeral=True)
            except:
                 pass

    @nextcord.slash_command(name="buscar", description="Busca músicas (YouTube/Spotify) e mostra os resultados.")
    async def buscar(self, interaction: Interaction,
                   busca: str = SlashOption(description="Termo de busca ou link", required=True)):
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"[DEBUG Musica] Comando /buscar recebido: 	'{busca}	' por {interaction.user} em {interaction.guild.name}")

            tracks: list[wavelink.Playable] | None = None
            source_used = "YouTube Music"

            # Tenta busca no YouTube Music primeiro
            print(f"[DEBUG Musica] /buscar: Buscando em YTM: {busca}")
            tracks = await wavelink.Playable.search(busca, source=wavelink.TrackSource.YouTubeMusic)
            if not tracks:
                # Se não encontrar, tenta no YouTube normal
                source_used = "YouTube"
                print(f"[DEBUG Musica] /buscar: Buscando em YT: {busca}")
                tracks = await wavelink.Playable.search(busca, source=wavelink.TrackSource.YouTube)

            if not tracks:
                print("[DEBUG Musica] /buscar: Nenhuma música encontrada.")
                return await interaction.followup.send("❌ Nenhuma música encontrada com essa busca.", ephemeral=True)

            embed = Embed(title=f"🔎 Resultados da Busca ({source_used})", description=f"Para: `{busca}`", color=Color.orange())
            results_text = ""
            print(f"[DEBUG Musica] /buscar: Encontrados {len(tracks)} resultados.")
            for i, track in enumerate(tracks[:10], 1): # Limita a 10 resultados
                duration = format_duration(track.length)
                results_text += f"`{i}.` [{track.title}]({track.uri or track.url}) ({duration})\n"
            embed.description += f"\n\n{results_text}"
            embed.set_footer(text="Use /tocar com o nome ou link exato para adicionar à fila.")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando /buscar:")
            traceback.print_exc()
            try:
                await interaction.followup.send("❌ Ocorreu um erro interno ao tentar buscar músicas.", ephemeral=True)
            except:
                 pass

# Função setup para carregar o Cog
def setup(bot: commands.Bot):
    print("[SETUP Musica] Adicionando Cog Musica...")
    try:
        bot.add_cog(Musica(bot))
        print("[SETUP Musica] Cog Musica adicionado com sucesso.")
    except Exception as e:
        print(f"❌ Erro CRÍTICO ao adicionar Cog Musica:")
        traceback.print_exc()
        # Considerar relançar o erro ou parar o bot se o cog de música for essencial
        # raise e
