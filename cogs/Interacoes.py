# /home/ubuntu/ShirayukiBot/cogs/Interacoes.py
# Cog para comandos de interação social.

import random
import traceback
import json
import os
import asyncio
from datetime import import datetime, timedelta, timezone # Adicionado timezone
import nextcord
from nextcord import Interaction, Embed, Color, Member, SlashOption, User
from nextcord.ext import commands # Mantido commands, removido application_checks daqui se não for usado para mais nada

# Importar helper de emojis (usando placeholder como em outras cogs)
def get_emoji(bot, name):
    emoji_map = {
        "blush_hands": "👉", "happy_flower": "🌸", "sparkle_happy": "✨",
        "determined": "😤", "peek": "👀", "thinking": "🤔", "sad": "😢",
        "interaction_stats": "📊", "error": "❌"
    }
    return emoji_map.get(name, "")

# --- Configurações ---
DEFAULT_COLOR = Color.magenta()
COOLDOWN_SECONDS = 5
STATS_FILE = "/home/ubuntu/ShirayukiBot/data/interaction_stats.json"
# A GIF_DATABASE_URL não está sendo usada ativamente no código fornecido, mas mantida se for usada no futuro.
# GIF_DATABASE_URL = "https://gist.githubusercontent.com/iamkevyn/4101031646a2a3cf4b531b183b6e40e/raw/"

INTERACTION_GIFS_LOCAL = {
    "hug": {"verb": "abraçou", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/2roX3uxz_68AAAAC/hug.gif", 
"https://media.tenor.com/NeXn0mMF5iYAAAAC/anime-hug.gif"]},
    "pat": {"verb": "acariciou", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/7vZ9TnA1fFQAAAAC/pat-head.gif", 
"https://media.tenor.com/YGdCdp9bMGUAAAAC/anime-pat.gif"]},
    "cuddle": {"verb": "se aconchegou com", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/PjsYjKdCMhcAAAAC/anime-cuddle.gif", 
"https://media.tenor.com/Nhcz0gKaNfcAAAAC/anime-hug-cuddle.gif"]},
    "highfive": {"verb": "bateu um highfive com", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/jClaHxw_d7gAAAAC/anime-highfive.gif", 
"https://media.tenor.com/MRe9gw0Af5sAAAAC/high-five-anime.gif"]},
    "wave": {"verb": "acenou para", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/WRR8oRbFq0wAAAAC/anime-wave.gif", 
"https://media.tenor.com/pS5fGiDw6vQAAAAC/hi-hello.gif"]},
    "applaud": {"verb": "aplaudiu", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/mGH6yxTQ5g0AAAAC/anime-clapping.gif", 
"https://media.tenor.com/tJHUJ9QY8iAAAAAC/clapping-anime.gif"]},
    "feed": {"verb": "deu comida para", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/3vQgHFUAN7gAAAAC/feed-anime.gif", 
"https://media.tenor.com/z9jHvJbuwq4AAAAC/anime-feed.gif"]},
    "cheer": {"verb": "animou", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/jG65XLOkkJAAAAAC/anime-cheer.gif", 
"https://media.tenor.com/6C5T3DtAYCUAAAAC/anime-cheer.gif"]},
    "comfort": {"verb": "consolou", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/9elaE_oBLCsAAAAC/anime-hug.gif", 
"https://media.tenor.com/1T1X5kDk574AAAAC/anime-hug-sweet.gif"]},
    "protect": {"verb": "protegeu", "emoji_name": "determined", "gifs": ["https://media.tenor.com/5WQEduGM3-AAAAAC/protect-anime.gif", 
"https://media.tenor.com/QnHW2dt5mXAAAAAC/anime-protect.gif"]},
    "kiss": {"verb": "beijou", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/Bq7iU7yb3OsAAAAC/kiss-anime.gif", 
"https://media.tenor.com/0AVn4U0VOnwAAAAC/anime-kiss.gif"]},
    "holdhands": {"verb": "segurou as mãos de", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/J7eCq3yX0qAAAAC/anime-hold-hands.gif", 
"https://media.tenor.com/WUZAwo5KFdMAAAAC/love-holding-hands.gif"]},
    "propose": {"verb": "pediu em casamento", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/3-z5Xd7QpY0AAAAC/anime-proposal.gif", 
"https://media.tenor.com/84d6sQ20CBsAAAAC/anime-propose.gif"]},
    "slap": {"verb": "deu um tapa em", "emoji_name": "determined", "gifs": ["https://media.tenor.com/5zv7N_p4OZMAAAAC/anime-slap.gif", 
"https://media.tenor.com/RwD7bRfGzIYAAAAC/slap.gif"]},
    "punch": {"verb": "deu um soco em", "emoji_name": "determined", "gifs": ["https://media.tenor.com/LIYEB7qz2JOAAAAC/anime-punch.gif", 
"https://media.tenor.com/bmA4WcLh-YkAAAAC/punch-anime.gif"]},
    "kick": {"verb": "chutou", "emoji_name": "determined", "gifs": ["https://media.tenor.com/_LS2CBQw0aYAAAAC/kick-anime.gif", 
"https://media.tenor.com/GzyM0mHf2ksAAAAC/anime-kick.gif"]},
    "bonk": {"verb": "deu uma bonkada em", "emoji_name": "peek", "gifs": ["https://media.tenor.com/tZLXJtz1MCMAAAAC/anime-bonk.gif", 
"https://media.tenor.com/4LfL0ZU-1l4AAAAC/anime-girl.gif"]},
    "poke": {"verb": "cutucou", "emoji_name": "peek", "gifs": ["https://media.tenor.com/p6xjxkxvQWcAAAAC/anime-poke.gif", 
"https://media.tenor.com/3dOqO0sDfpgAAAAC/anime-poke.gif"]},
    "boop": {"verb": "deu um boop em", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/OGnRVWCps7AAAAAC/boop-anime.gif", 
"https://media.tenor.com/Ug6cbVLKQr8AAAAC/boop-anime.gif"]},
    "tickle": {"verb": "fez cócegas em", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/PXL1ONAO9CEAAAAC/tickle-anime.gif", 
"https://media.tenor.com/L5-ABrIwKioAAAAC/tickle-anime.gif"]},
    "bite": {"verb": "mordeu", "emoji_name": "peek", "gifs": ["https://media.tenor.com/Ux-7WWvPJbMAAAAC/anime-bite.gif", 
"https://media.tenor.com/CsKYN49b5eEAAAAC/anime-bite.gif"]},
    "lick": {"verb": "lambeu", "emoji_name": "peek", "gifs": ["https://media.tenor.com/YgZMN7yLdcYAAAAC/anime-lick.gif", 
"https://media.tenor.com/30UeGiktwO8AAAAC/anime-lick.gif"]},
    "stare": {"verb": "encarou", "emoji_name": "peek", "gifs": ["https://media.tenor.com/ba3y7jB1-ekAAAAC/anime-stare.gif", 
"https://media.tenor.com/ixaDEFhYJLsAAAAC/anime-stare.gif"]},
    "cry": {"verb": "chorou para", "emoji_name": "sad", "gifs": ["https://media.tenor.com/dJBIzMRU4c0AAAAC/anime-cry.gif", 
"https://media.tenor.com/Mf6KNYzZsXwAAAAC/anime-cry.gif"]},
    "dance": {"verb": "dançou com", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/9tx-7cVNgXwAAAAC/anime-dance.gif", 
"https://media.tenor.com/MPxVm0G8D_AAAAAC/anime-dance.gif"]},
    "laugh": {"verb": "riu de", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/pI4S2Z0-FMMAAAAd/anime-laugh.gif", 
"https://media.tenor.com/XpU-ZgX2JCQAAAAC/anime-laugh.gif"]},
    "smile": {"verb": "sorriu para", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/71pF6p5tG7AAAAAC/anime-smile.gif", 
"https://media.tenor.com/z_AbZ_AzpFAAAAAC/anime-smile.gif"]},
    "wink": {"verb": "piscou para", "emoji_name": "peek", "gifs": ["https://media.tenor.com/QLvr6WlAZoMAAAAC/anime-wink.gif", 
"https://media.tenor.com/Ajitx1SRQNMAAAAC/anime-wink.gif"]},
    "yawn": {"verb": "bocejou para", "emoji_name": "peek", "gifs": ["https://media.tenor.com/SiBnGOkNtFEAAAAC/anime-yawn.gif", 
"https://media.tenor.com/UGikYpn9MqAAAAAC/anime-yawn.gif"]},
    "sleep": {"verb": "dormiu com", "emoji_name": "peek", "gifs": ["https://media.tenor.com/ERd5Ow9z0nMAAAAC/anime-sleep.gif", 
"https://media.tenor.com/TOJfZyXgQ4QAAAAC/anime-sleep.gif"]},
    "run": {"verb": "correu de", "emoji_name": "determined", "gifs": ["https://media.tenor.com/ZKRDC7BOXCgAAAAC/anime-run.gif", 
"https://media.tenor.com/Pj0QP2c_GmMAAAAC/anime-run.gif"]},
    "shrug": {"verb": "deu de ombros para", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/U2HXHRUuU38AAAAC/anime-shrug.gif", 
"https://media.tenor.com/9tyHIR9VeOAAAAAd/anime-shrug.gif"]},
    "facepalm": {"verb": "fez facepalm para", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/Ql7b1cCBzVUAAAAC/anime-facepalm.gif", 
"https://media.tenor.com/Vx-TcXUiq-AAAAAC/anime-facepalm.gif"]},
    "blush": {"verb": "corou para", "emoji_name": "blush_hands", "gifs": ["https://media.tenor.com/hCx1A-iyS3AAAAAC/anime-blush.gif", 
"https://media.tenor.com/hnvTwjPYAvcAAAAC/anime-blush.gif"]},
    "panic": {"verb": "entrou em pânico com", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/GFEIRU9UOIgAAAAC/anime-panic.gif", 
"https://media.tenor.com/ht_Dj9LvjUYAAAAC/anime-panic.gif"]},
    "faint": {"verb": "desmaiou por causa de", "emoji_name": "sad", "gifs": ["https://media.tenor.com/DHGXoG8cmJEAAAAC/anime-faint.gif", 
"https://media.tenor.com/Xvx4_NSX8XAAAAAC/anime-faint.gif"]},
    "shock": {"verb": "ficou chocado com", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/x6zNKP-LX8QAAAAC/anime-shock.gif", 
"https://media.tenor.com/AlvyT2QS5Z4AAAAC/anime-shock.gif"]},
    "sigh": {"verb": "suspirou para", "emoji_name": "sad", "gifs": ["https://media.tenor.com/QP3QK9_1u-AAAAAC/anime-sigh.gif", 
"https://media.tenor.com/Gv6-EwRZlJEAAAAC/anime-sigh.gif"]},
    "pout": {"verb": "fez bico para", "emoji_name": "sad", "gifs": ["https://media.tenor.com/PPdI-miAOWMAAAAC/anime-pout.gif", 
"https://media.tenor.com/3Y_jsCTWJK8AAAAC/anime-pout.gif"]},
    "smug": {"verb": "olhou com ar de superioridade para", "emoji_name": "peek", "gifs": ["https://media.tenor.com/DNVGTeUUr_EAAAAC/anime-smug.gif", 
"https://media.tenor.com/9yAYYRVpJFAAAAAC/anime-smug.gif"]},
    "greet": {"verb": "cumprimentou", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/sX8Z5-Q4o-MAAAAC/anime-greet.gif", 
"https://media.tenor.com/UG_zoMMhFgYAAAAC/anime-greet.gif"]},
    "handshake": {"verb": "apertou a mão de", "emoji_name": "determined", "gifs": ["https://media.tenor.com/EGhbN8-MJxsAAAAC/anime-handshake.gif", 
"https://media.tenor.com/pmP0scXWgD8AAAAC/anime-handshake.gif"]},
    "bow": {"verb": "se curvou para", "emoji_name": "determined", "gifs": ["https://media.tenor.com/Lqvric7IDEQAAAAC/anime-bow.gif", 
"https://media.tenor.com/9Tng5AjNGWAAAAAC/anime-bow.gif"]},
    "salute": {"verb": "saudou", "emoji_name": "determined", "gifs": ["https://media.tenor.com/QyOtKAu0kUAAAAAC/anime-salute.gif", 
"https://media.tenor.com/Aq4nnQJ4Kk8AAAAC/anime-salute.gif"]},
    "thumbsup": {"verb": "deu um joinha para", "emoji_name": "determined", "gifs": ["https://media.tenor.com/vBMSGAapO4AAAAAC/anime-thumbsup.gif", 
"https://media.tenor.com/Ff7YqYhfcJcAAAAC/anime-thumbsup.gif"]},
    "thumbsdown": {"verb": "deu um polegar para baixo para", "emoji_name": "determined", "gifs": ["https://media.tenor.com/Ux7JKt-ITMQAAAAC/anime-thumbsdown.gif", 
"https://media.tenor.com/KHQIGbuLMuUAAAAC/anime-thumbsdown.gif"]},
    "angry": {"verb": "ficou com raiva de", "emoji_name": "determined", "gifs": ["https://media.tenor.com/ikKX3hCKLYMAAAAC/anime-angry.gif", 
"https://media.tenor.com/jgFVzP4U0JQAAAAC/anime-angry.gif"]},
    "confused": {"verb": "ficou confuso com", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/VlSXTGC9J-EAAAAC/anime-confused.gif", 
"https://media.tenor.com/Xcr8fHyf_bsAAAAC/anime-confused.gif"]},
    "nod": {"verb": "acenou com a cabeça para", "emoji_name": "determined", "gifs": ["https://media.tenor.com/lwgVisdwvOYAAAAC/anime-nod.gif", 
"https://media.tenor.com/4jkT3ZET0XAAAAAC/anime-nod.gif"]},
    "headshake": {"verb": "balançou a cabeça para", "emoji_name": "determined", "gifs": ["https://media.tenor.com/N5maDXP-JXAAAAAC/anime-headshake.gif", 
"https://media.tenor.com/Y_Y7qEY3cF0AAAAC/anime-headshake.gif"]},
    "fistbump": {"verb": "deu um soquinho em", "emoji_name": "determined", "gifs": ["https://media.tenor.com/4P40sFRri48AAAAC/anime-fistbump.gif", 
"https://media.tenor.com/CrmEU2LKix4AAAAC/anime-fistbump.gif"]},
    "judge": {"verb": "julgou", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/Yrj3O3RpXGkAAAAC/anime-judge.gif", 
"https://media.tenor.com/q-zZSTX6jSAAAAAC/anime-judge.gif"]},
    "glare": {"verb": "olhou feio para", "emoji_name": "determined", "gifs": ["https://media.tenor.com/EB4dLFKV-VgAAAAC/anime-glare.gif", 
"https://media.tenor.com/AlUwZp0F0MQAAAAC/anime-glare.gif"]},
    "ignore": {"verb": "ignorou", "emoji_name": "thinking", "gifs": ["https://media.tenor.com/Tc_TUkCQQB8AAAAC/anime-ignore.gif", 
"https://media.tenor.com/YVIZq3qG-IIAAAAC/anime-ignore.gif"]},
    "sip": {"verb": "bebeu com", "emoji_name": "peek", "gifs": ["https://media.tenor.com/Uvx6-jXQ5TIAAAAC/anime-sip.gif", 
"https://media.tenor.com/12Gk1LK4MXAAAAAC/anime-sip.gif"]},
    "eat": {"verb": "comeu com", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/N_0_u_cXqVgAAAAC/anime-eat.gif", 
"https://media.tenor.com/E7Lq659I1AAAAAAC/anime-eat.gif"]},
    "nom": {"verb": "deu um nomnom em", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/Hnt4ZcFQVe4AAAAC/anime-nom.gif", 
"https://media.tenor.com/3I_W6zHvR80AAAAC/anime-nom.gif"]},
    "pet": {"verb": "fez carinho em", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/N41zKEDABuUAAAAC/anime-pet.gif", 
"https://media.tenor.com/wieV_G7L_WgAAAAC/anime-pet.gif"]},
    "pinch": {"verb": "beliscou", "emoji_name": "peek", "gifs": ["https://media.tenor.com/Vx9wYdAGIKAAAAAC/anime-pinch.gif", 
"https://media.tenor.com/HV0CrfZOQHAAAAAC/anime-pinch.gif"]},
    "squish": {"verb": "apertou as bochechas de", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/3SfqB3JEbmMAAAAC/anime-squish.gif", 
"https://media.tenor.com/MMQVw1SHf8AAAAAC/anime-squish.gif"]},
    "bully": {"verb": "zoou", "emoji_name": "peek", "gifs": ["https://media.tenor.com/PKKCAakpBZIAAAAC/anime-bully.gif", 
"https://media.tenor.com/Ht7EGVjyRtwAAAAC/anime-bully.gif"]},
    "tease": {"verb": "provocou", "emoji_name": "peek", "gifs": ["https://media.tenor.com/jF9rRqW-z1AAAAAC/anime-tease.gif", 
"https://media.tenor.com/Ql6HS0TcCakAAAAC/anime-tease.gif"]},
    "scold": {"verb": "deu bronca em", "emoji_name": "determined", "gifs": ["https://media.tenor.com/qQXjuFYKQN0AAAAC/anime-scold.gif", 
"https://media.tenor.com/XikoNQDfaqwAAAAC/anime-scold.gif"]},
    "praise": {"verb": "elogiou", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/J0qLkk9-PXAAAAAC/anime-praise.gif", 
"https://media.tenor.com/Svnb5I_LuTYAAAAC/anime-praise.gif"]},
    "thank": {"verb": "agradeceu", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/Gv0cUfzWbJAAAAAC/anime-thank.gif", 
"https://media.tenor.com/Ajitx1SRQNMAAAAC/anime-thank.gif"]},
    "sorry": {"verb": "pediu desculpas para", "emoji_name": "sad", "gifs": ["https://media.tenor.com/OPLmgzTWRuQAAAAC/anime-sorry.gif", 
"https://media.tenor.com/qXh-Y67gmVQAAAAC/anime-sorry.gif"]},
    "forgive": {"verb": "perdoou", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/YfYnrX2wnP4AAAAC/anime-forgive.gif", 
"https://media.tenor.com/qXh-Y67gmVQAAAAC/anime-forgive.gif"]},
    "congrats": {"verb": "parabenizou", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/E9qBWrKisp0AAAAC/anime-congrats.gif", 
"https://media.tenor.com/9tx-7cVNgXwAAAAC/anime-congrats.gif"]},
    "celebrate": {"verb": "celebrou com", "emoji_name": "sparkle_happy", "gifs": ["https://media.tenor.com/9tx-7cVNgXwAAAAC/anime-celebrate.gif", 
"https://media.tenor.com/E9qBWrKisp0AAAAC/anime-celebrate.gif"]},
    "welcome": {"verb": "deu boas-vindas a", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/sX8Z5-Q4o-MAAAAC/anime-welcome.gif", 
"https://media.tenor.com/UG_zoMMhFgYAAAAC/anime-welcome.gif"]},
    "goodbye": {"verb": "se despediu de", "emoji_name": "sad", "gifs": ["https://media.tenor.com/OGnRVWCps7AAAAAC/anime-goodbye.gif", 
"https://media.tenor.com/Ug6cbVLKQr8AAAAC/anime-goodbye.gif"]},
    "goodnight": {"verb": "desejou boa noite para", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/ERd5Ow9z0nMAAAAC/anime-goodnight.gif", 
"https://media.tenor.com/TOJfZyXgQ4QAAAAC/anime-goodnight.gif"]},
    "goodmorning": {"verb": "desejou bom dia para", "emoji_name": "happy_flower", "gifs": ["https://media.tenor.com/71pF6p5tG7AAAAAC/anime-goodmorning.gif", 
"https://media.tenor.com/z_AbZ_AzpFAAAAAC/anime-goodmorning.gif"]}
}

# Função para carregar estatísticas de interação
def load_interaction_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar estatísticas: {e}")
            return {}
    return {}

# Função para salvar estatísticas de interação
def save_interaction_stats(stats):
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao salvar estatísticas: {e}")

# Função para atualizar estatísticas de interação
def update_interaction_stats(interaction_type, user_id, target_id):
    stats = load_interaction_stats()
    
    # Inicializa estrutura se não existir
    if str(user_id) not in stats:
        stats[str(user_id)] = {}
    if "sent" not in stats[str(user_id)]:
        stats[str(user_id)]["sent"] = {}
    if interaction_type not in stats[str(user_id)]["sent"]:
        stats[str(user_id)]["sent"][interaction_type] = {}
    if str(target_id) not in stats[str(user_id)]["sent"][interaction_type]:
        stats[str(user_id)]["sent"][interaction_type][str(target_id)] = 0
    
    # Incrementa contador
    stats[str(user_id)]["sent"][interaction_type][str(target_id)] += 1
    
    # Faz o mesmo para o alvo (recebido)
    if str(target_id) not in stats:
        stats[str(target_id)] = {}
    if "received" not in stats[str(target_id)]:
        stats[str(target_id)]["received"] = {}
    if interaction_type not in stats[str(target_id)]["received"]:
        stats[str(target_id)]["received"][interaction_type] = {}
    if str(user_id) not in stats[str(target_id)]["received"][interaction_type]:
        stats[str(target_id)]["received"][interaction_type][str(user_id)] = 0
    
    # Incrementa contador
    stats[str(target_id)]["received"][interaction_type][str(user_id)] += 1
    
    save_interaction_stats(stats)

class Interacoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
    
    # Função para verificar cooldown
    def check_cooldown(self, user_id):
        if user_id in self.cooldowns:
            last_use = self.cooldowns[user_id]
            if datetime.now(timezone.utc) - last_use < timedelta(seconds=COOLDOWN_SECONDS):
                return False
        return True
    
    # Função para atualizar cooldown
    def update_cooldown(self, user_id):
        self.cooldowns[user_id] = datetime.now(timezone.utc)
    
    # Função para criar embed de interação
    def create_interaction_embed(self, interaction_type, user, target, gif_url):
        interaction_data = INTERACTION_GIFS_LOCAL.get(interaction_type, {"verb": "interagiu com", "emoji_name": "sparkle_happy"})
        verb = interaction_data["verb"]
        emoji_name = interaction_data["emoji_name"]
        emoji = get_emoji(self.bot, emoji_name)
        
        embed = Embed(
            title=f"{emoji} Interação Social {emoji}",
            description=f"**{user.display_name}** {verb} **{target.display_name}**",
            color=DEFAULT_COLOR
        )
        embed.set_image(url=gif_url)
        embed.set_footer(text=f"Use /interacao para ver todas as interações disponíveis!")
        return embed
    
    # Comando de interação genérico
    @nextcord.slash_command(
        name="interacao",
        description="Comandos de interação social com outros usuários."
    )
    async def interacao(self, interaction: Interaction):
        # Este é apenas o grupo de comandos, não faz nada sozinho
        pass
    
    # Subcomando para listar todas as interações disponíveis
    @interacao.subcommand(
        name="lista",
        description="Lista todas as interações sociais disponíveis."
    )
    async def lista_interacoes(self, interaction: Interaction):
        embed = Embed(
            title=f"{get_emoji(self.bot, 'interaction_stats')} Lista de Interações Sociais",
            description="Aqui estão todas as interações sociais disponíveis:",
            color=DEFAULT_COLOR
        )
        
        # Agrupa as interações por categoria
        categories = {
            "Positivas": ["hug", "pat", "cuddle", "highfive", "wave", "applaud", "cheer", "comfort", "protect", "kiss", "holdhands", "propose", "blush", "smile", "wink", "dance", "greet", "handshake", "bow", "salute", "thumbsup", "nod", "fistbump", "praise", "thank", "forgive", "congrats", "celebrate", "welcome", "goodnight", "goodmorning"],
            "Neutras": ["feed", "stare", "yawn", "sleep", "shrug", "facepalm", "sigh", "pout", "smug", "confused", "headshake", "judge", "ignore", "sip", "eat", "nom", "pet", "pinch", "squish", "tease"],
            "Negativas": ["slap", "punch", "kick", "bonk", "poke", "bite", "lick", "cry", "laugh", "run", "panic", "faint", "shock", "angry", "glare", "bully", "scold", "sorry", "goodbye"]
        }
        
        for category, interactions in categories.items():
            interaction_list = []
            for interaction_type in sorted(interactions):
                if interaction_type in INTERACTION_GIFS_LOCAL:
                    interaction_list.append(f"`/interacao {interaction_type}`")
            
            if interaction_list:
                embed.add_field(
                    name=f"**{category}**",
                    value=", ".join(interaction_list),
                    inline=False
                )
        
        embed.set_footer(text="Use /interacao stats para ver suas estatísticas de interação!")
        await interaction.response.send_message(embed=embed)
    
    # Subcomando para ver estatísticas de interação
    @interacao.subcommand(
        name="stats",
        description="Veja suas estatísticas de interação social."
    )
    async def stats_interacao(
        self,
        interaction: Interaction,
        usuario: User = SlashOption(
            name="usuario",
            description="Usuário para ver estatísticas (opcional, padrão: você mesmo)",
            required=False
        )
    ):
        target_user = usuario or interaction.user
        stats = load_interaction_stats()
        
        if str(target_user.id) not in stats:
            await interaction.response.send_message(f"{target_user.mention} ainda não tem estatísticas de interação.", ephemeral=True)
            return
        
        user_stats = stats[str(target_user.id)]
        
        embed = Embed(
            title=f"{get_emoji(self.bot, 'interaction_stats')} Estatísticas de Interação de {target_user.display_name}",
            color=DEFAULT_COLOR
        )
        
        # Estatísticas enviadas
        if "sent" in user_stats and user_stats["sent"]:
            sent_stats = []
            for interaction_type, targets in sorted(user_stats["sent"].items(), key=lambda x: sum(x[1].values()), reverse=True)[:5]:
                total = sum(targets.values())
                sent_stats.append(f"**{interaction_type}**: {total}x")
            
            if sent_stats:
                embed.add_field(
                    name="Top 5 Interações Enviadas",
                    value="\n".join(sent_stats),
                    inline=True
                )
        
        # Estatísticas recebidas
        if "received" in user_stats and user_stats["received"]:
            received_stats = []
            for interaction_type, sources in sorted(user_stats["received"].items(), key=lambda x: sum(x[1].values()), reverse=True)[:5]:
                total = sum(sources.values())
                received_stats.append(f"**{interaction_type}**: {total}x")
            
            if received_stats:
                embed.add_field(
                    name="Top 5 Interações Recebidas",
                    value="\n".join(received_stats),
                    inline=True
                )
        
        # Se não houver estatísticas
        if not embed.fields:
            embed.description = f"{target_user.mention} tem estatísticas, mas nenhuma interação significativa ainda."
        
        embed.set_footer(text="Use /interacao lista para ver todas as interações disponíveis!")
        await interaction.response.send_message(embed=embed)
    
    # Função para gerar dinamicamente os subcomandos de interação
    async def _create_interaction_command(self, interaction: Interaction, interaction_type: str, target: Member):
        # Verifica cooldown
        if not self.check_cooldown(interaction.user.id):
            remaining_seconds = COOLDOWN_SECONDS - (datetime.now(timezone.utc) - self.cooldowns[interaction.user.id]).total_seconds()
            await interaction.response.send_message(f"Você precisa esperar mais {remaining_seconds:.1f} segundos para usar outro comando de interação.", ephemeral=True)
            return
        
        # Verifica se o tipo de interação existe
        if interaction_type not in INTERACTION_GIFS_LOCAL:
            await interaction.response.send_message(f"Tipo de interação '{interaction_type}' não encontrado.", ephemeral=True)
            return
        
        # Verifica se o alvo é o próprio usuário
        if target.id == interaction.user.id:
            await interaction.response.send_message("Você não pode interagir consigo mesmo.", ephemeral=True)
            return
        
        # Verifica se o alvo é um bot
        if target.bot and target.id != self.bot.user.id:
            await interaction.response.send_message("Você não pode interagir com outros bots.", ephemeral=True)
            return
        
        # Atualiza cooldown
        self.update_cooldown(interaction.user.id)
        
        # Escolhe um GIF aleatório
        gif_url = random.choice(INTERACTION_GIFS_LOCAL[interaction_type]["gifs"])
        
        # Cria e envia o embed
        embed = self.create_interaction_embed(interaction_type, interaction.user, target, gif_url)
        await interaction.response.send_message(embed=embed)
        
        # Atualiza estatísticas
        update_interaction_stats(interaction_type, interaction.user.id, target.id)
    
    # Gera dinamicamente os subcomandos para cada tipo de interação
    for interaction_type, data in INTERACTION_GIFS_LOCAL.items():
        verb = data["verb"]
        
        # Cria o decorador para o subcomando
        @interacao.subcommand(
            name=interaction_type,
            description=f"{verb.capitalize()} alguém."
        )
        # Usa o decorator commands.cooldown em vez de application_checks.cooldown
        @commands.cooldown(1, COOLDOWN_SECONDS, commands.BucketType.user)
        async def _interaction_command(
            self,
            interaction: Interaction,
            target: Member = SlashOption(
                name="usuario",
                description="Usuário para interagir",
                required=True
            ),
            _interaction_type=interaction_type  # Captura o tipo de interação atual
        ):
            await self._create_interaction_command(interaction, _interaction_type, target)
    
    # Tratamento de erros para comandos de aplicação
    @nextcord.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        # Verifica se o erro é do comando desta cog
        # Não podemos mais usar cog_name, então verificamos de outra forma
        if hasattr(interaction, 'application_command'):
            # Verifica se o erro é de cooldown
            if isinstance(error, commands.CommandOnCooldown):
                await interaction.response.send_message(
                    f"Você precisa esperar mais {error.retry_after:.1f} segundos para usar este comando novamente.",
                    ephemeral=True
                )
                return
            
            # Outros erros específicos da cog
            try:
                # Tenta enviar uma mensagem de erro genérica
                await interaction.response.send_message(
                    f"{get_emoji(self.bot, 'error')} Ocorreu um erro ao processar o comando: {str(error)}",
                    ephemeral=True
                )
            except nextcord.errors.InteractionResponded:
                # Se a interação já foi respondida, tenta usar followup
                try:
                    await interaction.followup.send(
                        f"{get_emoji(self.bot, 'error')} Ocorreu um erro ao processar o comando: {str(error)}",
                        ephemeral=True
                    )
                except Exception as e:
                    # Se tudo falhar, apenas loga o erro
                    print(f"Erro ao enviar mensagem de erro: {e}")
            
            # Loga o erro para debug
            print(f"Erro em comando de aplicação: {error}")
            traceback.print_exception(type(error), error, error.__traceback__)

# Função setup para carregar a cog
def setup(bot):
    bot.add_cog(Interacoes(bot))
