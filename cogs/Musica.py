# /home/ubuntu/jsbot/cogs/Musica.py
import os
import asyncio
import datetime
import random
import nextcord
from nextcord import Interaction, Embed, ButtonStyle, SlashOption, Color, VoiceChannel
from nextcord.ui import View, Button, button # Import button decorator
from nextcord.ext import commands, tasks
import wavelink
import traceback
import re
import math

# Spotify (Credentials are now primarily used by Lavalink server with LavaSrc plugin)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Helper function to format duration
def format_duration(duration_ms):
    if duration_ms is None:
        return "00:00"
    seconds = int(duration_ms / 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

# --- Views --- 

class MusicControlView(View):
    def __init__(self, cog):
        super().__init__(timeout=None) # Persistent view
        self.cog = cog

    async def interaction_check(self, interaction: Interaction) -> bool:
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

    @button(label="⏯️", style=ButtonStyle.gray)
    async def toggle(self, button: Button, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Não estou conectado.", ephemeral=True)

        await player.pause(not player.paused)
        status = "pausada" if player.paused else "resumida"
        await interaction.response.send_message(f"⏯️ Música {status}.", ephemeral=True)

    @button(label="⏭️", style=ButtonStyle.blurple)
    async def skip(self, button: Button, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Não estou tocando nada.", ephemeral=True)

        await player.skip(force=True)
        await interaction.response.send_message("⏭️ Pulando música...", ephemeral=True)
        # A mensagem de "tocando agora" será enviada pelo evento on_track_start

    @button(label="⏹️", style=ButtonStyle.red)
    async def stop(self, button: Button, interaction: Interaction):
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
        await interaction.response.send_message("⏹️ Reprodução interrompida e bot desconectado.", ephemeral=True)

    @button(label="🔁", style=ButtonStyle.gray)
    async def loop(self, button: Button, interaction: Interaction):
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

    @button(label="🔀", style=ButtonStyle.gray)
    async def shuffle(self, button: Button, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or player.queue.count < 2:
            return await interaction.response.send_message("❌ A fila precisa ter pelo menos 2 músicas para embaralhar.", ephemeral=True)

        player.queue.shuffle()
        await interaction.response.send_message("🔀 Fila embaralhada!", ephemeral=True)


class QueuePaginatorView(View):
    def __init__(self, embeds):
        super().__init__(timeout=120) # Aumentar timeout
        self.embeds = embeds
        self.page = 0
        self.update_buttons()

    def update_buttons(self):
        # Desabilitar/Habilitar botões conforme a página
        prev_button = next((item for item in self.children if isinstance(item, Button) and item.custom_id == "prev"), None)
        next_button = next((item for item in self.children if isinstance(item, Button) and item.custom_id == "next"), None)

        if prev_button:
            prev_button.disabled = self.page == 0
        if next_button:
            next_button.disabled = self.page == len(self.embeds) - 1

    @button(label="⬅️ Anterior", style=ButtonStyle.gray, custom_id="prev")
    async def prev_page(self, button: Button, interaction: Interaction):
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
        else:
             await interaction.response.defer() # Apenas reconhece a interação se já estiver na primeira página

    @button(label="Próxima ➡️", style=ButtonStyle.gray, custom_id="next")
    async def next_page(self, button: Button, interaction: Interaction):
        if self.page < len(self.embeds) - 1:
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
        else:
            await interaction.response.defer() # Apenas reconhece a interação se já estiver na última página

# --- Cog --- 

class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_control_messages = {} # guild_id: message_id
        # self.autoleave.start() # Autoleave pode ser complexo com Wavelink v3, desativado por ora

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        """Evento chamado quando um nó Lavalink está pronto."""
        print(f"✅ Nó Lavalink '{payload.node.identifier}' (Sessão: {payload.session_id}) está pronto!")
        # Sinaliza no bot principal que o Lavalink está pronto (se o evento estiver lá)
        if hasattr(self.bot, 'lavalink_ready'):
            self.bot.lavalink_ready.set()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """Evento chamado quando uma música começa a tocar."""
        player = payload.player
        if not player or not player.current:
            return

        track = player.current
        original_interaction = getattr(track, 'interaction', None) # Recupera a interação original se foi salva
        channel = None

        if original_interaction:
            channel = original_interaction.channel
        elif player.guild:
             # Tenta encontrar um canal de texto adequado no servidor
             # Pode ser melhorado para buscar o canal onde o último comando /tocar foi usado
             text_channels = [ch for ch in player.guild.text_channels if ch.permissions_for(player.guild.me).send_messages]
             if text_channels:
                 channel = text_channels[0] # Usa o primeiro canal de texto disponível

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
                try:
                    old_msg = await channel.fetch_message(self.active_control_messages[guild_id])
                    await old_msg.delete()
                except (nextcord.NotFound, nextcord.Forbidden):
                    pass # Ignora se não encontrar ou não tiver permissão
                finally:
                    del self.active_control_messages[guild_id]

            # Enviar nova mensagem de controle
            try:
                control_message = await channel.send(embed=embed, view=MusicControlView(self))
                self.active_control_messages[guild_id] = control_message.id
            except Exception as e:
                 print(f"Erro ao enviar mensagem 'Tocando agora': {e}")
                 traceback.print_exc()

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Evento chamado quando uma música termina."""
        player = payload.player
        # A lógica de tocar a próxima música é gerenciada automaticamente pelo Wavelink
        # quando a fila não está vazia e o modo não é QueueMode.normal
        # Se a fila estiver vazia, o player para.
        # Podemos adicionar lógica de autoleave aqui se desejado.
        # print(f"Track ended: {payload.track.title}, Reason: {payload.reason}")
        # if player and not player.queue and not player.current:
        #     await asyncio.sleep(60) # Espera 60 segundos
        #     if not player.current and player.is_connected():
        #         await player.disconnect()
        #         print(f"Bot desconectado do canal {player.channel} por inatividade.")

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        """Evento chamado quando ocorre um erro ao tocar uma música."""
        print(f"❌ Erro ao tocar {payload.track.title}: {payload.exception}")
        # Poderia notificar o usuário no canal de texto
        # await payload.player.channel.send(f"Erro ao tocar {payload.track.title}. Pulando...")
        # O Wavelink geralmente tenta tocar a próxima música automaticamente

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
        """Verifica se o bot deve se desconectar quando fica sozinho."""
        if member.id == self.bot.user.id:
            return # Ignora eventos do próprio bot

        player: wavelink.Player = member.guild.voice_client
        if not player or not player.channel:
            return # Bot não está conectado

        # Verifica se o bot ficou sozinho no canal
        if before.channel == player.channel and after.channel != player.channel:
            # Conta quantos membros (não-bots) restam no canal
            human_members = [m for m in player.channel.members if not m.bot]
            if not human_members:
                await asyncio.sleep(30) # Espera 30 segundos para caso alguém volte
                # Re-verifica após a espera
                human_members_after_wait = [m for m in player.channel.members if not m.bot]
                if not human_members_after_wait and player.is_connected():
                    await player.disconnect()
                    print(f"Bot desconectado de {player.channel.name} por ficar sozinho.")
                    # Tenta limpar a mensagem de controle
                    guild_id = player.guild.id
                    if guild_id in self.active_control_messages:
                         try:
                             # Precisa de um canal de texto para buscar a mensagem
                             # Esta parte pode precisar de mais lógica para encontrar o canal correto
                             pass 
                         except Exception:
                             pass
                         finally:
                             del self.active_control_messages[guild_id]

    @nextcord.slash_command(name="conectar", description="Conecta o bot ao seu canal de voz.")
    async def conectar(self, interaction: Interaction, canal: VoiceChannel = SlashOption(description="Canal de voz para conectar", required=False)):
        if not canal:
            if interaction.user.voice and interaction.user.voice.channel:
                canal = interaction.user.voice.channel
            else:
                return await interaction.response.send_message("❌ Você não está em um canal de voz e não especificou um para conectar.", ephemeral=True)

        player: wavelink.Player = interaction.guild.voice_client
        if player and player.is_connected():
            if player.channel == canal:
                return await interaction.response.send_message(f"✅ Já estou conectado em `{canal.name}`.", ephemeral=True)
            else:
                # Mover para o novo canal
                await player.move_to(canal)
                return await interaction.response.send_message(f"✅ Movido para `{canal.name}`.", ephemeral=True)
        else:
            try:
                await canal.connect(cls=wavelink.Player)
                await interaction.response.send_message(f"✅ Conectado a `{canal.name}`.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Falha ao conectar a `{canal.name}`: {e}", ephemeral=True)

    @nextcord.slash_command(name="desconectar", description="Desconecta o bot do canal de voz.")
    async def desconectar(self, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a nenhum canal de voz.", ephemeral=True)

        # Limpar mensagem de controle se existir
        guild_id = player.guild.id
        if guild_id in self.active_control_messages:
            try:
                msg = await interaction.channel.fetch_message(self.active_control_messages[guild_id])
                await msg.delete()
            except (nextcord.NotFound, nextcord.Forbidden):
                pass
            finally:
                del self.active_control_messages[guild_id]

        await player.disconnect()
        await interaction.response.send_message("👋 Desconectado do canal de voz.", ephemeral=True)

    @nextcord.slash_command(name="tocar", description="Toque uma música ou playlist (YouTube, Spotify, SoundCloud...)." )
    async def tocar(self, interaction: Interaction, busca: str = SlashOption(description="Link ou nome da música/playlist", required=True)):
        await interaction.response.defer(ephemeral=True) # Adiar resposta

        if not interaction.guild:
             return await interaction.followup.send("Este comando só pode ser usado em servidores.")

        # Verificar se o usuário está em um canal de voz
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ Você precisa estar em um canal de voz para usar este comando.")

        # Conectar ao canal de voz se ainda não estiver conectado
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                return await interaction.followup.send(f"❌ Não foi possível conectar ao canal de voz: {e}")

        # Verificar se o usuário está no mesmo canal que o bot
        elif player.channel.id != interaction.user.voice.channel.id:
            return await interaction.followup.send("❌ Você precisa estar no mesmo canal de voz que eu.")

        # Buscar a música
        try:
            # Verificar se é um link do Spotify
            spotify_pattern = r"https?:\/\/open\.spotify\.com\/(track|album|playlist)\/([a-zA-Z0-9]+)"
            spotify_match = re.match(spotify_pattern, busca)

            if spotify_match:
                # Buscar usando o plugin LavaSrc do Lavalink
                tracks = await wavelink.Playable.search(busca)
                if not tracks:
                    return await interaction.followup.send("❌ Não foi possível encontrar essa música/playlist do Spotify.")

                # Verificar se é uma playlist
                if isinstance(tracks, wavelink.Playlist):
                    # Adicionar todas as músicas à fila
                    for track in tracks:
                        track.requester = interaction.user
                        await player.queue.put_wait(track)

                    await interaction.followup.send(f"✅ Adicionado à fila: Playlist **{tracks.name}** com {len(tracks)} músicas.")

                    # Se não estiver tocando nada, iniciar a reprodução
                    if not player.playing:
                        await player.play(player.queue.get(), volume=70)
                else:
                    # É uma única música
                    track = tracks[0]
                    track.requester = interaction.user

                    # Se já estiver tocando, adicionar à fila
                    if player.playing:
                        await player.queue.put_wait(track)
                        await interaction.followup.send(f"✅ Adicionado à fila: **{track.title}**")
                    else:
                        # Senão, tocar imediatamente
                        await player.play(track, volume=70)
                        await interaction.followup.send(f"🎵 Tocando: **{track.title}**")
            else:
                # Busca normal (YouTube, etc)
                tracks = await wavelink.Playable.search(busca)

                if not tracks:
                    return await interaction.followup.send(f"❌ Não foi possível encontrar: {busca}")

                # Verificar se é uma playlist
                if isinstance(tracks, wavelink.Playlist):
                    # Adicionar todas as músicas à fila
                    for track in tracks:
                        track.requester = interaction.user
                        await player.queue.put_wait(track)

                    await interaction.followup.send(f"✅ Adicionado à fila: Playlist **{tracks.name}** com {len(tracks)} músicas.")

                    # Se não estiver tocando nada, iniciar a reprodução
                    if not player.playing:
                        await player.play(player.queue.get(), volume=70)
                else:
                    # É uma única música
                    track = tracks[0]
                    track.requester = interaction.user
                    track.interaction = interaction # Salvar a interação para uso posterior

                    # Se já estiver tocando, adicionar à fila
                    if player.playing:
                        await player.queue.put_wait(track)
                        await interaction.followup.send(f"✅ Adicionado à fila: **{track.title}**")
                    else:
                        # Senão, tocar imediatamente
                        await player.play(track, volume=70)
                        await interaction.followup.send(f"🎵 Tocando: **{track.title}**")

        except Exception as e:
            print(f"Erro ao buscar/tocar música: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ocorreu um erro: {e}")

    @nextcord.slash_command(name="pausar", description="Pausa a música atual.")
    async def pausar(self, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        if not player.current:
            return await interaction.response.send_message("❌ Não estou tocando nada no momento.", ephemeral=True)

        if player.paused:
            return await interaction.response.send_message("⚠️ A música já está pausada.", ephemeral=True)

        await player.pause(True)
        await interaction.response.send_message("⏸️ Música pausada.", ephemeral=True)

    @nextcord.slash_command(name="retomar", description="Retoma a reprodução da música pausada.")
    async def retomar(self, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        if not player.current:
            return await interaction.response.send_message("❌ Não há nada para retomar.", ephemeral=True)

        if not player.paused:
            return await interaction.response.send_message("⚠️ A música já está tocando.", ephemeral=True)

        await player.pause(False)
        await interaction.response.send_message("▶️ Música retomada.", ephemeral=True)

    @nextcord.slash_command(name="pular", description="Pula para a próxima música da fila.")
    async def pular(self, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        if not player.current:
            return await interaction.response.send_message("❌ Não estou tocando nada no momento.", ephemeral=True)

        await player.skip(force=True)
        await interaction.response.send_message("⏭️ Música pulada.", ephemeral=True)

    @nextcord.slash_command(name="parar", description="Para a reprodução e limpa a fila.")
    async def parar(self, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        if not player.current and player.queue.is_empty:
            return await interaction.response.send_message("❌ Não estou tocando nada no momento.", ephemeral=True)

        player.queue.clear()
        await player.stop()

        # Limpar mensagem de controle se existir
        guild_id = player.guild.id
        if guild_id in self.active_control_messages:
            try:
                msg = await interaction.channel.fetch_message(self.active_control_messages[guild_id])
                await msg.delete()
            except (nextcord.NotFound, nextcord.Forbidden):
                pass
            finally:
                del self.active_control_messages[guild_id]

        await interaction.response.send_message("⏹️ Reprodução interrompida e fila limpa.", ephemeral=True)

    @nextcord.slash_command(name="fila", description="Mostra a fila de músicas.")
    async def fila(self, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        if not player.current and player.queue.is_empty:
            return await interaction.response.send_message("❌ Não estou tocando nada e a fila está vazia.", ephemeral=True)

        # Criar embed para a música atual
        embeds = []
        current_embed = Embed(title="🎵 Fila de Reprodução", color=Color.blue())

        if player.current:
            current_embed.add_field(
                name="🎧 Tocando agora:",
                value=f"[{player.current.title}]({player.current.uri or player.current.url}) - {format_duration(player.current.length)}\n" +
                      (f"Pedido por: {player.current.requester.mention}" if hasattr(player.current, 'requester') and player.current.requester else ""),
                inline=False
            )

        # Adicionar informações da fila
        if player.queue.is_empty:
            current_embed.add_field(name="📋 Próximas músicas:", value="*Nenhuma música na fila*", inline=False)
            embeds.append(current_embed)
        else:
            # Adicionar as primeiras músicas ao primeiro embed
            queue_list = list(player.queue)
            items_per_page = 10
            total_pages = math.ceil(len(queue_list) / items_per_page)

            # Adicionar informação sobre o total
            current_embed.description = f"**{len(queue_list)}** músicas na fila • Duração total aproximada: {format_duration(sum(t.length for t in queue_list if t.length))}"

            # Adicionar as primeiras músicas ao primeiro embed
            queue_text = ""
            for i, track in enumerate(queue_list[:items_per_page]):
                requester = getattr(track, 'requester', None)
                requester_text = f" • Pedido por: {requester.mention}" if requester else ""
                queue_text += f"`{i+1}.` [{track.title}]({track.uri or track.url}) - {format_duration(track.length)}{requester_text}\n"

            current_embed.add_field(name="📋 Próximas músicas:", value=queue_text, inline=False)
            current_embed.set_footer(text=f"Página 1 de {total_pages}")
            embeds.append(current_embed)

            # Criar embeds adicionais para o resto da fila
            for page in range(1, total_pages):
                start_idx = page * items_per_page
                end_idx = min(start_idx + items_per_page, len(queue_list))

                page_embed = Embed(title=f"🎵 Fila de Reprodução (Continuação)", color=Color.blue())
                page_embed.set_footer(text=f"Página {page+1} de {total_pages}")

                queue_text = ""
                for i, track in enumerate(queue_list[start_idx:end_idx]):
                    requester = getattr(track, 'requester', None)
                    requester_text = f" • Pedido por: {requester.mention}" if requester else ""
                    queue_text += f"`{start_idx+i+1}.` [{track.title}]({track.uri or track.url}) - {format_duration(track.length)}{requester_text}\n"

                page_embed.add_field(name=f"📋 Continuação da fila:", value=queue_text, inline=False)
                embeds.append(page_embed)

        # Enviar o embed com paginação se necessário
        if len(embeds) > 1:
            await interaction.response.send_message(embed=embeds[0], view=QueuePaginatorView(embeds))
        else:
            await interaction.response.send_message(embed=embeds[0])

    @nextcord.slash_command(name="repetir", description="Configura o modo de repetição.")
    async def repetir(self, interaction: Interaction, modo: str = SlashOption(
        description="Modo de repetição",
        choices={"Desativar": "off", "Repetir música atual": "single", "Repetir fila": "all"},
        required=True
    )):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        if not player.current:
            return await interaction.response.send_message("❌ Não estou tocando nada no momento.", ephemeral=True)

        if modo == "off":
            player.queue.mode = wavelink.QueueMode.normal
            await interaction.response.send_message("🔄 Modo de repetição desativado.", ephemeral=True)
        elif modo == "single":
            player.queue.mode = wavelink.QueueMode.loop
            await interaction.response.send_message("🔂 Repetindo a música atual.", ephemeral=True)
        elif modo == "all":
            player.queue.mode = wavelink.QueueMode.loop_all
            await interaction.response.send_message("🔁 Repetindo toda a fila.", ephemeral=True)

    @nextcord.slash_command(name="embaralhar", description="Embaralha a fila de músicas.")
    async def embaralhar(self, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        if player.queue.count < 2:
            return await interaction.response.send_message("❌ A fila precisa ter pelo menos 2 músicas para embaralhar.", ephemeral=True)

        player.queue.shuffle()
        await interaction.response.send_message("🔀 Fila embaralhada!", ephemeral=True)

    @nextcord.slash_command(name="volume", description="Ajusta o volume da reprodução.")
    async def volume(self, interaction: Interaction, nivel: int = SlashOption(
        description="Nível de volume (0-100)",
        min_value=0,
        max_value=100,
        required=True
    )):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        await player.set_volume(nivel)
        await interaction.response.send_message(f"🔊 Volume ajustado para {nivel}%.", ephemeral=True)

    @nextcord.slash_command(name="tocando", description="Mostra informações sobre a música atual.")
    async def tocando(self, interaction: Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("❌ Não estou conectado a um canal de voz.", ephemeral=True)

        if not player.current:
            return await interaction.response.send_message("❌ Não estou tocando nada no momento.", ephemeral=True)

        track = player.current
        embed = Embed(title="🎧 Tocando agora", color=Color.green())
        embed.description = f"[{track.title}]({track.uri or track.url})"

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        # Adicionar informações da música
        embed.add_field(name="Duração", value=format_duration(track.length), inline=True)

        # Adicionar barra de progresso
        position = player.position
        length = track.length
        if position is not None and length:
            progress = min(position / length, 1.0)  # Garantir que não ultrapasse 100%
            bar_length = 20
            filled_length = int(bar_length * progress)
            bar = "▬" * filled_length + "🔘" + "▬" * (bar_length - filled_length - 1)
            embed.add_field(
                name="Progresso", 
                value=f"{format_duration(position)} {bar} {format_duration(length)}", 
                inline=False
            )

        # Adicionar informações adicionais
        if hasattr(track, 'requester') and track.requester:
            embed.add_field(name="Pedido por", value=track.requester.mention, inline=True)

        # Adicionar informações do player
        embed.add_field(name="Volume", value=f"{player.volume}%", inline=True)

        # Adicionar modo de repetição
        repeat_modes = {
            wavelink.QueueMode.normal: "Desativado",
            wavelink.QueueMode.loop: "Repetindo música atual",
            wavelink.QueueMode.loop_all: "Repetindo fila"
        }
        embed.add_field(name="Modo de repetição", value=repeat_modes.get(player.queue.mode, "Desconhecido"), inline=True)

        # Adicionar próxima música se houver
        if not player.queue.is_empty:
            next_track = player.queue[0]
            embed.add_field(
                name="Próxima música", 
                value=f"[{next_track.title}]({next_track.uri or next_track.url}) - {format_duration(next_track.length)}", 
                inline=False
            )

        await interaction.response.send_message(embed=embed, view=MusicControlView(self))

def setup(bot):
    bot.add_cog(Musica(bot))
