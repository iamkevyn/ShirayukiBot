# /home/ubuntu/ShirayukiBot/cogs/Interacoes.py
# Cog para comandos de interação social.

import random
import traceback
import json
import os
import asyncio
from datetime import datetime, timedelta, timezone # Adicionado timezone
import nextcord
from nextcord import Interaction, Embed, Color, Member, SlashOption, User
from nextcord.ext import commands, application_checks # Adicionado application_checks

# Importar helper de emojis (usando placeholder como em outras cogs)
def get_emoji(bot, name):
    emoji_map = {
        "blush_hands": "🥰", "happy_flower": "🌸", "sparkle_happy": "✨", 
        "determined": "😠", "peek": "👀", "thinking": "🤔", "sad": "😥",
        "interaction_stats": "📊", "error": "❌"
    }
    return emoji_map.get(name, "▫️")

# --- Configurações --- 
DEFAULT_COLOR = Color.magenta()
COOLDOWN_SECONDS = 5
STATS_FILE = "/home/ubuntu/ShirayukiBot/data/interaction_stats.json"
# A GIF_DATABASE_URL não está sendo usada ativamente no código fornecido, mas mantida se for usada no futuro.
# GIF_DATABASE_URL = "https://gist.githubusercontent.com/iamkevyn/41010316f46a2a3cf4b531b183b6e40e/raw/"

INTERACTION_GIFS_LOCAL = {
    "hug": {"verb": "abraçou", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/2roX3uxz_68AAAAC/hug.gif", "https://media.tenor.com/NeXn0mMF5iYAAAAC/anime-hug.gif"]},
    "pat": {"verb": "acariciou", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/7vZ9TnA1fFQAAAAC/pat-head.gif", "https://media.tenor.com/YGdCdp9bMGUAAAAC/anime-pat.gif"]},
    "cuddle": {"verb": "se aconchegou com", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/Pj4YjKdCMhcAAAAC/anime-cuddle.gif", "https://media.tenor.com/Nhcz0gKaNfcAAAAC/anime-hug-cuddle.gif"]},
    "highfive": {"verb": "bateu um highfive com", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/jC1aHxw_d7gAAAAC/anime-highfive.gif", "https://media.tenor.com/MNeOgw0Af5sAAAAC/highfive-anime.gif"]},
    "wave": {"verb": "acenou para", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/WRR8oR6pqOwAAAAC/anime-wave.gif", "https://media.tenor.com/pS5fGiDw6vQAAAAC/hi-hello.gif"]},
    "applaud": {"verb": "aplaudiu", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/mGH6yxTQ5g0AAAAC/anime-clapping.gif", "https://media.tenor.com/tJHUJ9QY8iAAAAAC/clapping-anime.gif"]},
    "feed": {"verb": "deu comida para", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/3vDgHFUAN7gAAAAC/feed-anime.gif", "https://media.tenor.com/zDjHvJbuwq4AAAAC/anime-feed.gif"]},
    "cheer": {"verb": "animou", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/jGG5XLQkkJAAAAAC/anime-cheer.gif", "https://media.tenor.com/6C5T3DtAYCUAAAAC/anime-cheer.gif"]},
    "comfort": {"verb": "consolou", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/9e1aE_xBLCsAAAAC/anime-hug.gif", "https://media.tenor.com/1T1X5kDk574AAAAC/anime-hug-sweet.gif"]},
    "protect": {"verb": "protegeu", "emoji_name": "determined", "gifs": ["https://media.tenor.com/5WQEduGM3-AAAAAC/protect-anime.gif", "https://media.tenor.com/QnHW2dt5mXAAAAAC/anime-protect.gif"]},
    "kiss": {"verb": "beijou", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/Bq7iU7yb3OsAAAAC/kiss-anime.gif", "https://media.tenor.com/0AVn4U0VOnwAAAAC/anime-kiss.gif"]},
    "holdhands": {"verb": "segurou as mãos de", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/J7eCq3yX0qAAAAAC/anime-hold-hands.gif", "https://media.tenor.com/WUZAwo5KFdMAAAAC/love-holding-hands.gif"]},
    "propose": {"verb": "pediu em casamento", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/3-z5Xd7QpY0AAAAC/anime-proposal.gif", "https://media.tenor.com/84dGsQZ0CBsAAAAC/anime-propose.gif"]},
    "slap": {"verb": "deu um tapa em", "emoji_name": "determined", "gifs": ["https://media.tenor.com/5zv7N_p4OZMAAAAC/anime-slap.gif", "https://media.tenor.com/RwD7bRfGzIYAAAAC/slap.gif"]},
    "punch": {"verb": "deu um soco em", "emoji_name": "determined", "gifs": ["https://media.tenor.com/LIYkB7qz2JQAAAAC/anime-punch.gif", "https://media.tenor.com/bmA4WcLh-YkAAAAC/punch-anime.gif"]},
    "kick": {"verb": "chutou", "emoji_name": "determined", "gifs": ["https://media.tenor.com/_uS2CBQW0aYAAAAC/kick-anime.gif", "https://media.tenor.com/GzyM0mHf2ksAAAAC/anime-kick.gif"]},
    "bonk": {"verb": "deu uma bonkada em", "emoji_name": "peek", "gifs": ["https://media.tenor.com/C2LXJtz1MCMAAAAC/anime-bonk.gif", "https://media.tenor.com/1T3_ADd1k-UAAAAC/bonk-anime.gif"]},
    "poke": {"verb": "cutucou", "emoji_name": "peek", "gifs": ["https://media.tenor.com/vEGlwQZ9HdgAAAAC/poke-anime.gif", "https://media.tenor.com/fuX0aW1FhZsAAAAC/anime-poke.gif"]},
    "stare": {"verb": "encarou", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/GzEcNNhxW7IAAAAC/anime-stare.gif", "https://media.tenor.com/lZZzHtJAM7EAAAAC/stare-anime.gif"]},
    "facepalm": {"verb": "fez um facepalm por causa de", "emoji_name": "sad", "gifs": ["https://media.tenor.com/JBgP4kX7L00AAAAC/anime-facepalm.gif", "https://media.tenor.com/PDgN5-8EB1wAAAAC/facepalm-anime.gif"]},
    "kill": {"verb": "eliminou", "emoji_name": "determined", "gifs": ["https://media.tenor.com/J1fA7A1rS-UAAAAC/kill-anime.gif", "https://media.tenor.com/iFSY803ypEMAAAAC/chainsaw-man-anime.gif"]},
    "bite": {"verb": "mordeu", "emoji_name": "peek", "gifs": ["https://media.tenor.com/UDfwDPuV_yoAAAAC/anime-bite.gif", "https://media.tenor.com/xsKZJ8-LUGkAAAAC/anime.gif"]},
    "lick": {"verb": "lambeu", "emoji_name": "peek", "gifs": ["https://media.tenor.com/bJDa8H-rQZ4AAAAC/anime-lick.gif", "https://media.tenor.com/RRjht8v7voIAAAAC/lick-anime.gif"]},
    "confused": {"verb": "ficou confuso com", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/N4NUK19U8NMAAAAC/anime-confused.gif", "https://media.tenor.com/UoG4jQE0-_cAAAAC/anime-confused.gif"]},
    "dance": {"verb": "dançou", "emoji_name": "sparkle_happy", "solo": True, "gifs": ["https://media.tenor.com/NZfPdV2pFFYAAAAC/anime-dance.gif", "https://media.tenor.com/TObCV91w6bEAAAAC/dance.gif"]},
    "blush": {"verb": "ficou corado", "emoji_name": "blush_hands", "solo": True, "gifs": ["https://media.tenor.com/1v3uPQVCn6cAAAAC/anime-blush.gif", "https://media.tenor.com/FJwHkE_JwCwAAAAC/blush-anime.gif"]},
    "cry": {"verb": "chorou", "emoji_name": "sad", "solo": True, "gifs": ["https://media.tenor.com/6u6UEvWhYdwAAAAC/crying-anime.gif", "https://media.tenor.com/RVvnVPK-6dcAAAAC/anime-crying.gif"]},
    "sleep": {"verb": "foi dormir", "emoji_name": "thinking", "solo": True, "gifs": ["https://media.tenor.com/9iS9kivD8JMAAAAC/sleepy.gif", "https://media.tenor.com/ZghfHZ-W4B0AAAAC/sleep.gif"]},
    "think": {"verb": "pensou", "emoji_name": "thinking", "solo": True, "gifs": ["https://media.tenor.com/j3h-Q4u4kSAAAAAC/anime-thinking.gif", "https://media.tenor.com/Qd8riWOc0-8AAAAC/anime-think.gif"]},
    "laugh": {"verb": "riu", "emoji_name": "sparkle_happy", "solo": True, "gifs": ["https://media.tenor.com/Et0b8wd0gFMAAAAC/anime-laugh.gif", "https://media.tenor.com/hBPwD7hV0aYAAAAC/anime-laughing.gif"]},
    "celebrate": {"verb": "celebrou", "emoji_name": "sparkle_happy", "solo": True, "gifs": ["https://media.tenor.com/j1XTP9FNrI0AAAAC/anime-celebrate.gif", "https://media.tenor.com/2fEtKlGg00AAAAAC/anime-celebrate.gif"]}
}

# --- Gerenciamento de Estatísticas --- 
def load_stats() -> dict:
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_stats(stats: dict):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4)
    except IOError as e:
        print(f"Erro ao salvar estatísticas de interação: {e}")

# --- Classe da Cog --- 
class Interacoes(commands.Cog):
    """Comandos de interação social com GIFs e estatísticas."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.interaction_stats = load_stats()
        self.user_cooldowns = {}
        print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] Cog Interacoes carregada.")

    def _update_stats(self, action: str, actor_id: int, target_id: int = None):
        actor_id_str = str(actor_id)
        target_id_str = str(target_id) if target_id else None

        if actor_id_str not in self.interaction_stats:
            self.interaction_stats[actor_id_str] = {"sent": {}, "received": {}}
        if target_id_str and target_id_str not in self.interaction_stats:
            self.interaction_stats[target_id_str] = {"sent": {}, "received": {}}

        # Contar ação enviada pelo ator
        self.interaction_stats[actor_id_str]["sent"][action] = self.interaction_stats[actor_id_str]["sent"].get(action, 0) + 1
        
        # Contar ação recebida pelo alvo (se houver)
        if target_id_str:
            self.interaction_stats[target_id_str]["received"][action] = self.interaction_stats[target_id_str]["received"].get(action, 0) + 1
        
        save_stats(self.interaction_stats)

    async def _send_interaction_embed(self, interaction: Interaction, action: str, target: Member | User = None):
        action_details = INTERACTION_GIFS_LOCAL.get(action)
        if not action_details:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Ação '{action}' não configurada.", ephemeral=True)
            return

        actor = interaction.user
        verb = action_details["verb"]
        emoji = get_emoji(self.bot, action_details["emoji_name"])
        gif_url = random.choice(action_details["gifs"]) if action_details["gifs"] else None
        is_solo = action_details.get("solo", False)

        if is_solo:
            description = f"{emoji} {actor.mention} {verb}!"
            self._update_stats(action, actor.id)
        elif target:
            if target == actor:
                await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} Você não pode {verb.split(' ')[0]} você mesmo dessa forma!", ephemeral=True)
                return
            if target.bot:
                await interaction.response.send_message(f"{get_emoji(self.bot, 'peek')} Eu agradeço o gesto, mas prefiro interagir com humanos!", ephemeral=True)
                return
            description = f"{emoji} {actor.mention} {verb} {target.mention}!"
            self._update_stats(action, actor.id, target.id)
        else:
            # Caso de ação não-solo sem alvo (não deveria acontecer com os comandos atuais)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Esta ação requer um alvo.", ephemeral=True)
            return

        embed = Embed(description=description, color=DEFAULT_COLOR)
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.response.send_message(embed=embed)

    # --- Comandos de Interação Dinâmicos --- 
    # Criar comandos slash para cada interação definida em INTERACTION_GIFS_LOCAL
    # Esta é uma forma mais avançada e pode precisar de ajustes dependendo da versão do nextcord
    # e como ele lida com a criação dinâmica de comandos slash dentro de cogs.
    # Por simplicidade e robustez, vamos definir cada comando explicitamente abaixo.

    # --- Comandos Slash Explícitos ---
    # (Adicionar decorador de cooldown para cada um)
    # @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))

    @nextcord.slash_command(name="hug", description="Abrace alguém com carinho.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def hug(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer abraçar?", required=True)):
        await self._send_interaction_embed(interaction, "hug", usuario)

    @nextcord.slash_command(name="pat", description="Faça um cafuné em alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def pat(self, interaction: Interaction, usuario: Member = SlashOption(description="Em quem você quer fazer cafuné?", required=True)):
        await self._send_interaction_embed(interaction, "pat", usuario)

    @nextcord.slash_command(name="cuddle", description="Aconchegue-se com alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def cuddle(self, interaction: Interaction, usuario: Member = SlashOption(description="Com quem você quer se aconchegar?", required=True)):
        await self._send_interaction_embed(interaction, "cuddle", usuario)

    @nextcord.slash_command(name="kiss", description="Beije alguém com paixão.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def kiss(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer beijar?", required=True)):
        await self._send_interaction_embed(interaction, "kiss", usuario)

    @nextcord.slash_command(name="slap", description="Dê um tapa em alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def slap(self, interaction: Interaction, usuario: Member = SlashOption(description="Em quem você quer dar um tapa?", required=True)):
        await self._send_interaction_embed(interaction, "slap", usuario)

    @nextcord.slash_command(name="punch", description="Dê um soco em alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def punch(self, interaction: Interaction, usuario: Member = SlashOption(description="Em quem você quer dar um soco?", required=True)):
        await self._send_interaction_embed(interaction, "punch", usuario)
    
    @nextcord.slash_command(name="kick", description="Chute alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def kick(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer chutar?", required=True)):
        await self._send_interaction_embed(interaction, "kick", usuario)

    @nextcord.slash_command(name="bonk", description="Dê uma bonkada em alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def bonk(self, interaction: Interaction, usuario: Member = SlashOption(description="Em quem você quer dar uma bonkada?", required=True)):
        await self._send_interaction_embed(interaction, "bonk", usuario)

    @nextcord.slash_command(name="poke", description="Cutuque alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def poke(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer cutucar?", required=True)):
        await self._send_interaction_embed(interaction, "poke", usuario)

    @nextcord.slash_command(name="bite", description="Morda alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def bite(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer morder?", required=True)):
        await self._send_interaction_embed(interaction, "bite", usuario)

    @nextcord.slash_command(name="lick", description="Lamba alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def lick(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer lamber?", required=True)):
        await self._send_interaction_embed(interaction, "lick", usuario)

    @nextcord.slash_command(name="feed", description="Alimente alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def feed(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer alimentar?", required=True)):
        await self._send_interaction_embed(interaction, "feed", usuario)

    @nextcord.slash_command(name="highfive", description="Bata um highfive com alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def highfive(self, interaction: Interaction, usuario: Member = SlashOption(description="Com quem você quer bater um highfive?", required=True)):
        await self._send_interaction_embed(interaction, "highfive", usuario)

    @nextcord.slash_command(name="wave", description="Acene para alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def wave(self, interaction: Interaction, usuario: Member = SlashOption(description="Para quem você quer acenar?", required=True)):
        await self._send_interaction_embed(interaction, "wave", usuario)

    @nextcord.slash_command(name="stare", description="Encare alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def stare(self, interaction: Interaction, usuario: Member = SlashOption(description="Para quem você quer encarar?", required=True)):
        await self._send_interaction_embed(interaction, "stare", usuario)

    @nextcord.slash_command(name="facepalm", description="Faça um facepalm por causa de alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def facepalm(self, interaction: Interaction, usuario: Member = SlashOption(description="Por causa de quem você quer fazer um facepalm?", required=True)):
        await self._send_interaction_embed(interaction, "facepalm", usuario)

    @nextcord.slash_command(name="applaud", description="Aplauda alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def applaud(self, interaction: Interaction, usuario: Member = SlashOption(description="Para quem você quer aplaudir?", required=True)):
        await self._send_interaction_embed(interaction, "applaud", usuario)

    @nextcord.slash_command(name="cheer", description="Anime alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def cheer(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer animar?", required=True)):
        await self._send_interaction_embed(interaction, "cheer", usuario)

    @nextcord.slash_command(name="comfort", description="Console alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def comfort(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer consolar?", required=True)):
        await self._send_interaction_embed(interaction, "comfort", usuario)

    @nextcord.slash_command(name="protect", description="Proteja alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def protect(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer proteger?", required=True)):
        await self._send_interaction_embed(interaction, "protect", usuario)

    @nextcord.slash_command(name="holdhands", description="Segure as mãos de alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def holdhands(self, interaction: Interaction, usuario: Member = SlashOption(description="De quem você quer segurar as mãos?", required=True)):
        await self._send_interaction_embed(interaction, "holdhands", usuario)

    @nextcord.slash_command(name="propose", description="Peça alguém em casamento.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def propose(self, interaction: Interaction, usuario: Member = SlashOption(description="Para quem você quer se declarar?", required=True)):
        await self._send_interaction_embed(interaction, "propose", usuario)

    @nextcord.slash_command(name="kill", description="Elimine alguém (use com moderação!).")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def kill(self, interaction: Interaction, usuario: Member = SlashOption(description="Quem você quer eliminar?", required=True)):
        await self._send_interaction_embed(interaction, "kill", usuario)

    @nextcord.slash_command(name="confused", description="Fique confuso com alguém.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def confused(self, interaction: Interaction, usuario: Member = SlashOption(description="Com quem você está confuso?", required=True)):
        await self._send_interaction_embed(interaction, "confused", usuario)

    # Comandos Solo
    @nextcord.slash_command(name="dance", description="Dance com alegria!")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def dance(self, interaction: Interaction):
        await self._send_interaction_embed(interaction, "dance")

    @nextcord.slash_command(name="blush", description="Fique corado(a).")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def blush(self, interaction: Interaction):
        await self._send_interaction_embed(interaction, "blush")

    @nextcord.slash_command(name="cry", description="Chore um pouco.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def cry(self, interaction: Interaction):
        await self._send_interaction_embed(interaction, "cry")

    @nextcord.slash_command(name="sleep", description="Vá dormir um pouco.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def sleep(self, interaction: Interaction):
        await self._send_interaction_embed(interaction, "sleep")

    @nextcord.slash_command(name="think", description="Pense sobre a vida.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def think(self, interaction: Interaction):
        await self._send_interaction_embed(interaction, "think")

    @nextcord.slash_command(name="laugh", description="Dê uma boa risada.")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def laugh(self, interaction: Interaction):
        await self._send_interaction_embed(interaction, "laugh")

    @nextcord.slash_command(name="celebrate", description="Celebre algo!")
    @application_checks.cooldown(1, COOLDOWN_SECONDS, key=lambda i: (i.guild_id, i.user.id))
    async def celebrate(self, interaction: Interaction):
        await self._send_interaction_embed(interaction, "celebrate")

    # --- Comando de Estatísticas --- 
    @nextcord.slash_command(name="interacoesstats", description="Mostra suas estatísticas de interação ou de outro usuário.")
    async def interacoesstats(self, interaction: Interaction, usuario: Member | User = SlashOption(description="De quem você quer ver as estatísticas? (Opcional)", required=False)):
        target_user = usuario or interaction.user
        target_id_str = str(target_user.id)

        if target_id_str not in self.interaction_stats:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} {target_user.mention} ainda não participou de interações ou não tem estatísticas registradas.", ephemeral=True)
            return

        user_stats = self.interaction_stats[target_id_str]
        embed = Embed(title=f"{get_emoji(self.bot, 'interaction_stats')} Estatísticas de Interação de {target_user.display_name}", color=DEFAULT_COLOR)
        if target_user.display_avatar: embed.set_thumbnail(url=target_user.display_avatar.url)

        sent_actions_str = "Nenhuma ação enviada."
        if user_stats.get("sent"):
            sent_actions = [f"**{action.capitalize()}**: {count}x" for action, count in sorted(user_stats["sent"].items())]
            sent_actions_str = "\n".join(sent_actions)
        embed.add_field(name="Ações Enviadas", value=sent_actions_str, inline=False)

        received_actions_str = "Nenhuma ação recebida."
        if user_stats.get("received"):
            received_actions = [f"**{action.capitalize()}**: {count}x" for action, count in sorted(user_stats["received"].items())]
            received_actions_str = "\n".join(received_actions)
        embed.add_field(name="Ações Recebidas", value=received_actions_str, inline=False)

        await interaction.response.send_message(embed=embed)

    # --- Tratamento de Erro de Cooldown --- 
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, application_checks.ApplicationCommandOnCooldown):
            retry_after_formatted = str(timedelta(seconds=int(error.retry_after))) # Formata para HH:MM:SS
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'sad')} Ei, vá com calma! Você pode usar este comando novamente em **{retry_after_formatted}**.", 
                ephemeral=True
            )
        else:
            # Para outros erros, podemos logar ou enviar uma mensagem genérica
            print(f"Erro em um comando de aplicação da cog Interacoes: {error}")
            # traceback.print_exc() # Descomente para log completo no console
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Ocorreu um erro ao processar este comando.", ephemeral=True)
                except nextcord.NotFound:
                    # A interação pode ter expirado se o processamento do erro demorar muito
                    pass 
                except Exception as e_send:
                    print(f"Erro ao enviar mensagem de erro na cog Interacoes: {e_send}")

def setup(bot: commands.Bot):
    bot.add_cog(Interacoes(bot))
