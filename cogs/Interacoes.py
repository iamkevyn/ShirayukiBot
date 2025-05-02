# /home/ubuntu/ShirayukiBot/cogs/Interacoes.py
# Cog para comandos de interação social.

import random
import traceback
import json
import os
import asyncio
from datetime import datetime, timedelta

import nextcord
from nextcord import Interaction, Embed, Color, Member, SlashOption, User
from nextcord.ext import commands, application_checks

# Importar helper de emojis
from utils.emojis import get_emoji

# --- Configurações --- 
SERVER_ID = 1367345048458498219 # Para registro rápido de comandos
DEFAULT_COLOR = Color.magenta() # Cor padrão para embeds de interação
COOLDOWN_SECONDS = 5 # Cooldown padrão para comandos de interação
STATS_FILE = "/home/ubuntu/ShirayukiBot/data/interaction_stats.json" # Arquivo para estatísticas
GIF_DATABASE_URL = "https://gist.githubusercontent.com/iamkevyn/41010316f46a2a3cf4b531b183b6e40e/raw/" # URL base para GIFs (Exemplo, precisa ser real)
# Se a URL acima não funcionar, usaremos o dicionário local como fallback.

# --- Banco de GIFs (Fallback local) --- 
# Expandido com muitas mais opções e novas interações
# Idealmente, carregar de um arquivo JSON ou API externa para facilitar a manutenção
# Mantendo local por enquanto para garantir funcionalidade
INTERACTION_GIFS_LOCAL = {
    # Positivas / Amigáveis
    "hug": {
        "verb": "abraçou",
        "emoji": "blush_hands",
        "gifs": [
            "https://media.tenor.com/2roX3uxz_68AAAAC/hug.gif",
            "https://media.tenor.com/NeXn0mMF5iYAAAAC/anime-hug.gif",
            "https://media.tenor.com/Jl8nD1kOAQMAAAAC/kyoukai-no-kanata-hug.gif",
            "https://media.tenor.com/82Ax6lt0__4AAAAC/hug-anime.gif",
            "https://media.tenor.com/YY94q2HwWNEAAAAC/anime-hug.gif",
            "https://media.tenor.com/9e1aE_xBLCsAAAAC/anime-hug.gif",
            "https://media.tenor.com/1T1X5kDk574AAAAC/anime-hug-sweet.gif"
        ]
    },
    "pat": {
        "verb": "acariciou",
        "emoji": "happy_flower",
        "gifs": [
            "https://media.tenor.com/7vZ9TnA1fFQAAAAC/pat-head.gif",
            "https://media.tenor.com/YGdCdp9bMGUAAAAC/anime-pat.gif",
            "https://media.tenor.com/wfTj8Dh9EYAAAAAC/pat-anime.gif",
            "https://media.tenor.com/N-dZg4hN6wYAAAAC/anime-head-pat.gif",
            "https://media.tenor.com/HYbMAU0X2fkAAAAC/anime-pat.gif",
            "https://media.tenor.com/E6fMkQRZBdIAAAAC/kanna-kamui-pat.gif",
            "https://media.tenor.com/m6Xh_uRj69UAAAAC/anime-pat.gif"
        ]
    },
    "cuddle": {
        "verb": "se aconchegou com",
        "emoji": "blush_hands",
        "gifs": [
            "https://media.tenor.com/Pj4YjKdCMhcAAAAC/anime-cuddle.gif",
            "https://media.tenor.com/Nhcz0gKaNfcAAAAC/anime-hug-cuddle.gif",
            "https://media.tenor.com/NtdhsW5TKaAAAAAC/cuddle.gif",
            "https://media.tenor.com/oSPiG4-92NAAAAAC/anime-cuddle.gif",
            "https://media.tenor.com/gksuvTLMu2IAAAAC/cuddle-anime.gif"
        ]
    },
    "highfive": {
        "verb": "bateu um highfive com",
        "emoji": "sparkle_happy",
        "gifs": [
            "https://media.tenor.com/jC1aHxw_d7gAAAAC/anime-highfive.gif",
            "https://media.tenor.com/MNeOgw0Af5sAAAAC/highfive-anime.gif",
            "https://media.tenor.com/j2doT4CBhyUAAAAC/high-five-anime.gif",
            "https://media.tenor.com/3Lz7gB_gXHUAAAAC/high-five.gif",
            "https://media.tenor.com/y6aVdzuQ-pUAAAAC/anime.gif"
        ]
    },
    "wave": {
        "verb": "acenou para",
        "emoji": "happy_flower",
        "gifs": [
            "https://media.tenor.com/WRR8oR6pqOwAAAAC/anime-wave.gif",
            "https://media.tenor.com/pS5fGiDw6vQAAAAC/hi-hello.gif",
            "https://media.tenor.com/qHdzgBl8XMQAAAAC/hello-anime.gif",
            "https://media.tenor.com/NMVny6GqqW8AAAAC/anime-wave.gif",
            "https://media.tenor.com/23QeN0d46kQAAAAC/anime-wave.gif"
        ]
    },
    "applaud": {
        "verb": "aplaudiu",
        "emoji": "sparkle_happy",
        "gifs": [
            "https://media.tenor.com/mGH6yxTQ5g0AAAAC/anime-clapping.gif",
            "https://media.tenor.com/tJHUJ9QY8iAAAAAC/clapping-anime.gif",
            "https://media.tenor.com/7FfPzfgh5WgAAAAC/anime-clap.gif",
            "https://media.tenor.com/1FDy6HTQnFMAAAAC/anime-clapping.gif"
        ]
    },
    "feed": {
        "verb": "deu comida para",
        "emoji": "happy_flower",
        "gifs": [
            "https://media.tenor.com/3vDgHFUAN7gAAAAC/feed-anime.gif",
            "https://media.tenor.com/zDjHvJbuwq4AAAAC/anime-feed.gif",
            "https://media.tenor.com/Ll9d9CnJGywAAAAC/feeding-anime.gif",
            "https://media.tenor.com/7jOcQ055jMoAAAAC/anime-feed.gif",
            "https://media.tenor.com/XfWvQG4cbqEAAAAC/anime-feed.gif"
        ]
    },
    "cheer": {
        "verb": "animou",
        "emoji": "sparkle_happy",
        "gifs": [
            "https://media.tenor.com/jGG5XLQkkJAAAAAC/anime-cheer.gif",
            "https://media.tenor.com/6C5T3DtAYCUAAAAC/anime-cheer.gif",
            "https://media.tenor.com/o8hxfy9H69AAAAAC/anime-cheer.gif",
            "https://media.tenor.com/3mY0ZC6w4qAAAAAC/anime-cheer.gif"
        ]
    },
    "comfort": {
        "verb": "consolou",
        "emoji": "blush_hands",
        "gifs": [
            "https://media.tenor.com/9e1aE_xBLCsAAAAC/anime-hug.gif", # Reusing hug gifs
            "https://media.tenor.com/1T1X5kDk574AAAAC/anime-hug-sweet.gif",
            "https://media.tenor.com/HYbMAU0X2fkAAAAC/anime-pat.gif", # Reusing pat gifs
            "https://media.tenor.com/m6Xh_uRj69UAAAAC/anime-pat.gif"
        ]
    },
    "protect": {
        "verb": "protegeu",
        "emoji": "determined",
        "gifs": [
            "https://media.tenor.com/5WQEduGM3-AAAAAC/protect-anime.gif",
            "https://media.tenor.com/QnHW2dt5mXAAAAAC/anime-protect.gif",
            "https://media.tenor.com/zYvL0N0MSJQAAAAC/anime-protect.gif",
            "https://media.tenor.com/3hQ3lq4zXqAAAAAC/anime-protect.gif"
        ]
    },
    # Românticas
    "kiss": {
        "verb": "beijou",
        "emoji": "blush_hands",
        "gifs": [
            "https://media.tenor.com/Bq7iU7yb3OsAAAAC/kiss-anime.gif",
            "https://media.tenor.com/0AVn4U0VOnwAAAAC/anime-kiss.gif",
            "https://media.tenor.com/QvL8v7lPPX8AAAAC/kaguya-sama-kiss.gif",
            "https://media.tenor.com/jnndDmOm5wMAAAAC/kiss.gif",
            "https://media.tenor.com/bM043Eb44jcAAAAC/anime-kiss.gif"
        ]
    },
    "holdhands": {
        "verb": "segurou as mãos de",
        "emoji": "blush_hands",
        "gifs": [
            "https://media.tenor.com/J7eCq3yX0qAAAAAC/anime-hold-hands.gif",
            "https://media.tenor.com/WUZAwo5KFdMAAAAC/love-holding-hands.gif",
            "https://media.tenor.com/rU3xZo2_jaIAAAAC/anime-hold-hands.gif",
            "https://media.tenor.com/wCk-dSyHJYIAAAAC/anime.gif"
        ]
    },
    "propose": {
        "verb": "pediu em casamento",
        "emoji": "sparkle_happy",
        "gifs": [
            "https://media.tenor.com/3-z5Xd7QpY0AAAAC/anime-proposal.gif",
            "https://media.tenor.com/84dGsQZ0CBsAAAAC/anime-propose.gif",
            "https://media.tenor.com/b8t4gY090ZAAAAAC/anime-propose.gif",
            "https://media.tenor.com/jYvSNyvj8YcAAAAC/anime-proposal.gif"
        ]
    },
    # Negativas / Brincalhonas
    "slap": {
        "verb": "deu um tapa em",
        "emoji": "determined", # Ou sad?
        "gifs": [
            "https://media.tenor.com/5zv7N_p4OZMAAAAC/anime-slap.gif",
            "https://media.tenor.com/RwD7bRfGzIYAAAAC/slap.gif",
            "https://media.tenor.com/2xl4JgxTtIUAAAAC/anime-hit.gif",
            "https://media.tenor.com/1-1Lkl_3L_QAAAAC/slap-anime.gif",
            "https://media.tenor.com/UDo0WPttiJAAAAAC/anime-slap-mad.gif"
        ]
    },
    "punch": {
        "verb": "deu um soco em",
        "emoji": "determined",
        "gifs": [
            "https://media.tenor.com/LIYkB7qz2JQAAAAC/anime-punch.gif",
            "https://media.tenor.com/bmA4WcLh-YkAAAAC/punch-anime.gif",
            "https://media.tenor.com/TS8u4IS_2NIAAAAC/punch-hit.gif",
            "https://media.tenor.com/EvBn8X0W7Q0AAAAC/anime-punch.gif",
            "https://media.tenor.com/6YhF0F0B0hIAAAAC/anime-fight.gif"
        ]
    },
    "kick": {
        "verb": "chutou",
        "emoji": "determined",
        "gifs": [
            "https://media.tenor.com/_uS2CBQW0aYAAAAC/kick-anime.gif",
            "https://media.tenor.com/GzyM0mHf2ksAAAAC/anime-kick.gif",
            "https://media.tenor.com/rNHyL8PzAoYAAAAC/kick.gif",
            "https://media.tenor.com/Y59d_Nl0gRQAAAAC/anime-kick.gif",
            "https://media.tenor.com/YfW-8gOcOLAAAAAC/anime-kick.gif"
        ]
    },
    "bonk": {
        "verb": "deu uma bonkada em",
        "emoji": "peek",
        "gifs": [
            "https://media.tenor.com/C2LXJtz1MCMAAAAC/anime-bonk.gif",
            "https://media.tenor.com/1T3_ADd1k-UAAAAC/bonk-anime.gif",
            "https://media.tenor.com/Gt6h55UP9yMAAAAC/bonk-horny.gif",
            "https://media.tenor.com/nLtzZ1Mx6wYAAAAC/bonk-anime.gif"
        ]
    },
    "poke": {
        "verb": "cutucou",
        "emoji": "peek",
        "gifs": [
            "https://media.tenor.com/vEGlwQZ9HdgAAAAC/poke-anime.gif",
            "https://media.tenor.com/fuX0aW1FhZsAAAAC/anime-poke.gif",
            "https://media.tenor.com/7uhzLQxcmcUAAAAC/poking-anime.gif",
            "https://media.tenor.com/LzgzRM95tqgAAAAC/poke.gif",
            "https://media.tenor.com/b0g6a-ZSKTAAAAAC/anime-poke.gif"
        ]
    },
    "stare": {
        "verb": "encarou",
        "emoji": "thinking",
        "gifs": [
            "https://media.tenor.com/GzEcNNhxW7IAAAAC/anime-stare.gif",
            "https://media.tenor.com/lZZzHtJAM7EAAAAC/stare-anime.gif",
            "https://media.tenor.com/lE84w_Vl_WUAAAAC/anime-look.gif",
            "https://media.tenor.com/u_n1L6Lg04AAAAAC/anime-stare.gif",
            "https://media.tenor.com/3N080V5m7NQAAAAC/stare-anime.gif"
        ]
    },
    "facepalm": {
        "verb": "fez um facepalm por causa de",
        "emoji": "sad",
        "gifs": [
            "https://media.tenor.com/JBgP4kX7L00AAAAC/anime-facepalm.gif",
            "https://media.tenor.com/PDgN5-8EB1wAAAAC/facepalm-anime.gif",
            "https://media.tenor.com/Gu0dGgk77uQAAAAC/anime-facepalm.gif",
            "https://media.tenor.com/VLcxIXJd8oQAAAAC/facepalm-anime.gif"
        ]
    },
    "kill": { # Ação mais "forte", usar com moderação
        "verb": "eliminou",
        "emoji": "determined",
        "gifs": [
            "https://media.tenor.com/J1fA7A1rS-UAAAAC/kill-anime.gif",
            "https://media.tenor.com/iFSY803ypEMAAAAC/chainsaw-man-anime.gif",
            "https://media.tenor.com/r3hFv0RROpcAAAAC/anime-gun.gif",
            "https://media.tenor.com/tSE2SUZ-8oAAAAAC/gun-anime.gif"
        ]
    },
    # Outras / Neutras
    "bite": {
        "verb": "mordeu",
        "emoji": "peek",
        "gifs": [
            "https://media.tenor.com/UDfwDPuV_yoAAAAC/anime-bite.gif",
            "https://media.tenor.com/xsKZJ8-LUGkAAAAC/anime.gif",
            "https://media.tenor.com/W9FJKdGzOjcAAAAC/bite-anime.gif",
            "https://media.tenor.com/89QWOU0h7TEAAAAC/anime-bite.gif",
            "https://media.tenor.com/X1Erht6hwJgAAAAC/anime-bite.gif"
        ]
    },
    "lick": {
        "verb": "lambeu",
        "emoji": "peek",
        "gifs": [
            "https://media.tenor.com/bJDa8H-rQZ4AAAAC/anime-lick.gif",
            "https://media.tenor.com/RRjht8v7voIAAAAC/lick-anime.gif",
            "https://media.tenor.com/B5sh8dESbZ4AAAAC/anime-licking.gif",
            "https://media.tenor.com/1E0t0D-V6TIAAAAC/lick-anime.gif",
            "https://media.tenor.com/jXThnL95hCUAAAAC/lick.gif"
        ]
    },
    "confused": {
        "verb": "ficou confuso com",
        "emoji": "thinking",
        "gifs": [
            "https://media.tenor.com/N4NUK19U8NMAAAAC/anime-confused.gif",
            "https://media.tenor.com/UoG4jQE0-_cAAAAC/anime-confused.gif",
            "https://media.tenor.com/f54j144m0gAAAAAC/confused-anime.gif",
            "https://media.tenor.com/3XSYGjpzylMAAAAC/anime-confused.gif"
        ]
    },
    # Ações "solo" (sem alvo)
    "dance": {
        "verb": "dançou",
        "emoji": "sparkle_happy",
        "solo": True,
        "gifs": [
            "https://media.tenor.com/NZfPdV2pFFYAAAAC/anime-dance.gif",
            "https://media.tenor.com/TObCV91w6bEAAAAC/dance.gif",
            "https://media.tenor.com/4cKkGBeAKDMAAAAC/anime-dancing.gif",
            "https://media.tenor.com/CgGUXLN0gVsAAAAC/anime-dance.gif",
            "https://media.tenor.com/hMeQTq60R-0AAAAC/dance-anime.gif"
        ]
    },
    "blush": {
        "verb": "ficou corado",
        "emoji": "blush_hands",
        "solo": True,
        "gifs": [
            "https://media.tenor.com/1v3uPQVCn6cAAAAC/anime-blush.gif",
            "https://media.tenor.com/FJwHkE_JwCwAAAAC/blush-anime.gif",
            "https://media.tenor.com/lkW5R4SBYWwAAAAC/blushing-anime.gif",
            "https://media.tenor.com/e6EUOM0qQ5IAAAAC/anime-blush.gif",
            "https://media.tenor.com/r7fzaM7Lp0UAAAAC/anime-blush.gif"
        ]
    },
    "cry": {
        "verb": "chorou",
        "emoji": "sad",
        "solo": True,
        "gifs": [
            "https://media.tenor.com/6u6UEvWhYdwAAAAC/crying-anime.gif",
            "https://media.tenor.com/RVvnVPK-6dcAAAAC/anime-crying.gif",
            "https://media.tenor.com/RSj3vGkL5X8AAAAC/cry-anime.gif",
            "https://media.tenor.com/8hDrYLd4Y6YAAAAC/anime-cry.gif",
            "https://media.tenor.com/3KCaJ0TYVm0AAAAC/anime-cry.gif"
        ]
    },
    "sleep": {
        "verb": "foi dormir",
        "emoji": "thinking", # Ou um emoji de sono? Zzz
        "solo": True,
        "gifs": [
            "https://media.tenor.com/9iS9kivD8JMAAAAC/sleepy.gif",
            "https://media.tenor.com/ZghfHZ-W4B0AAAAC/sleep.gif",
            "https://media.tenor.com/BzLaCmQ_WQQAAAAC/anime-sleep.gif",
            "https://media.tenor.com/T7wQZ40nY0wAAAAC/anime-sleep.gif",
            "https://media.tenor.com/z4rmrZK9-qIAAAAC/anime-sleep.gif"
        ]
    },
    "think": {
        "verb": "pensou",
        "emoji": "thinking",
        "solo": True,
        "gifs": [
            "https://media.tenor.com/j3h-Q4u4kSAAAAAC/anime-thinking.gif",
            "https://media.tenor.com/Qd8riWOc0-8AAAAC/anime-think.gif",
            "https://media.tenor.com/6KVp-z338D4AAAAC/thinking-anime.gif",
            "https://media.tenor.com/juriVna96-AAAAAC/anime-thinking.gif"
        ]
    },
    "laugh": {
        "verb": "riu",
        "emoji": "sparkle_happy",
        "solo": True,
        "gifs": [
            "https://media.tenor.com/Et0b8wd0gFMAAAAC/anime-laugh.gif",
            "https://media.tenor.com/hBPwD7hV0aYAAAAC/anime-laughing.gif",
            "https://media.tenor.com/9bFBJzjvM7YAAAAC/anime-laugh.gif",
            "https://media.tenor.com/0zM3ytRm0jQAAAAC/anime-laugh.gif"
        ]
    },
    "celebrate": {
        "verb": "celebrou",
        "emoji": "sparkle_happy",
        "solo": True,
        "gifs": [
            "https://media.tenor.com/j1XTP9FNrI0AAAAC/anime-celebrate.gif",
            "https://media.tenor.com/2fEtKlGg00AAAAAC/anime-celebrate.gif",
            "https://media.tenor.com/lQkEz0WPQJAAAAAC/anime-celebrate.gif",
            "https://media.tenor.com/v0wNPlSp4f4AAAAC/anime-celebrate.gif"
        ]
    }
}

# --- Gerenciamento de Estatísticas --- 
def load_stats() -> dict:
    """Carrega as estatísticas do arquivo JSON."""
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"[AVISO] Erro ao carregar {STATS_FILE}. Criando um novo.")
        return {}

def save_stats(stats: dict):
    """Salva as estatísticas no arquivo JSON."""
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4)
    except IOError as e:
        print(f"[ERRO] Falha ao salvar estatísticas em {STATS_FILE}: {e}")

def update_stats(user_id: int, target_id: int | None, action: str):
    """Atualiza as estatísticas de interação."""
    stats = load_stats()
    user_id_str = str(user_id)
    target_id_str = str(target_id) if target_id else "solo"

    # Estatísticas do usuário que realizou a ação
    if user_id_str not in stats:
        stats[user_id_str] = {"sent": {}, "received": {}, "solo": {}}
    if "sent" not in stats[user_id_str]: stats[user_id_str]["sent"] = {}
    if "received" not in stats[user_id_str]: stats[user_id_str]["received"] = {}
    if "solo" not in stats[user_id_str]: stats[user_id_str]["solo"] = {}

    if target_id:
        # Ação direcionada
        if target_id_str not in stats[user_id_str]["sent"]:
            stats[user_id_str]["sent"][target_id_str] = {}
        stats[user_id_str]["sent"][target_id_str][action] = stats[user_id_str]["sent"].get(target_id_str, {}).get(action, 0) + 1
        
        # Estatísticas do usuário que recebeu a ação
        if target_id_str not in stats:
            stats[target_id_str] = {"sent": {}, "received": {}, "solo": {}}
        if "sent" not in stats[target_id_str]: stats[target_id_str]["sent"] = {}
        if "received" not in stats[target_id_str]: stats[target_id_str]["received"] = {}
        if "solo" not in stats[target_id_str]: stats[target_id_str]["solo"] = {}
            
        if user_id_str not in stats[target_id_str]["received"]:
            stats[target_id_str]["received"][user_id_str] = {}
        stats[target_id_str]["received"][user_id_str][action] = stats[target_id_str]["received"].get(user_id_str, {}).get(action, 0) + 1
    else:
        # Ação solo
        stats[user_id_str]["solo"][action] = stats[user_id_str]["solo"].get(action, 0) + 1

    save_stats(stats)

# --- Cog Interacoes --- 
class Interacoes(commands.Cog):
    """Comandos de interação social com outros usuários ou solo, usando GIFs e estatísticas."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.interaction_gifs = INTERACTION_GIFS_LOCAL # Começa com o fallback local
        self.commands_generated = False
        self.bot.loop.create_task(self.load_gifs_from_source()) # Tenta carregar da fonte externa
        print(f"[{datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}] Cog Interacoes inicializada.")

    async def load_gifs_from_source(self):
        """Tenta carregar a lista de GIFs de uma fonte externa (ex: Gist)."""
        # Esta função é um exemplo, precisa de uma biblioteca HTTP como aiohttp
        # Por simplicidade, vamos pular a implementação real com aiohttp por enquanto
        # e manter o fallback local.
        print(f"[INFO] Tentando carregar GIFs de fonte externa: {GIF_DATABASE_URL} (Implementação pendente)")
        # Exemplo (requer aiohttp):
        # try:
        #     async with aiohttp.ClientSession() as session:
        #         async with session.get(GIF_DATABASE_URL + "interaction_gifs.json") as resp:
        #             if resp.status == 200:
        #                 self.interaction_gifs = await resp.json()
        #                 print("[INFO] GIFs carregados com sucesso da fonte externa.")
        #                 return
        #             else:
        #                 print(f"[AVISO] Falha ao carregar GIFs da fonte externa (Status: {resp.status}). Usando fallback local.")
        # except Exception as e:
        #     print(f"[ERRO] Erro ao carregar GIFs da fonte externa: {e}. Usando fallback local.")
        pass # Mantém o fallback local por enquanto

    @commands.Cog.listener()
    async def on_ready(self):
        """Gera os comandos dinamicamente quando o bot está pronto."""
        if not self.commands_generated:
            print("--- [Interacoes] Bot pronto, gerando comandos de interação... ---")
            await self._generate_commands()
            self.commands_generated = True
            print(f"--- [Interacoes] Geração de {len(self.interaction_gifs)} comandos de interação concluída. ---")

    def get_interaction_details(self, action: str) -> dict | None:
        """Retorna os detalhes (verbo, emoji, gifs, solo) para uma ação."""
        return self.interaction_gifs.get(action)

    def create_interaction_embed(self, action_details: dict, user1: Member | User, user2: Member | User | None = None) -> Embed:
        """Cria o embed para a mensagem de interação (solo ou com alvo)."""
        action = next(key for key, val in self.interaction_gifs.items() if val == action_details) # Pega o nome da ação
        gif = random.choice(action_details["gifs"])
        verb = action_details["verb"]
        emoji_name = action_details["emoji"]
        emoji_str = get_emoji(self.bot, emoji_name)
        
        # Mensagens variadas
        messages = []
        if user2: # Interação com alvo
            messages = [
                f"{emoji_str} **{user1.display_name}** {verb} **{user2.display_name}**!",


                f"Olha só! **{user1.display_name}** {verb} **{user2.display_name}** {emoji_str}",
                f"Que fofo! **{user1.display_name}** acabou de {verb} **{user2.display_name}** {emoji_str}"
            ]
        else: # Ação solo
            messages = [
                f"{emoji_str} **{user1.display_name}** {verb}!",
                f"**{user1.display_name}** está a {verb} {emoji_str}",
                f"Momento de {action}! **{user1.display_name}** {verb} {emoji_str}"
            ]

        embed = Embed(description=random.choice(messages), color=DEFAULT_COLOR)
        embed.set_image(url=gif)
        # Footer pode mostrar estatísticas?
        # embed.set_footer(text=f"Interagindo... {get_emoji(self.bot, random.choice(['happy_flower', 'peek', 'thinking']))}")
        return embed

    async def _interaction_command_template(self, interaction: Interaction, target_user: Member | User | None, action: str):
        """Template interno para a lógica dos comandos de interação (solo ou com alvo)."""
        action_details = self.get_interaction_details(action)
        if not action_details:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Ação '{action}' não encontrada internamente.", ephemeral=True)
            return

        is_solo = action_details.get("solo", False)
        author = interaction.user

        if is_solo:
            # Ação solo, não requer alvo
            if target_user:
                await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} A ação '{action}' é individual, não precisa mencionar um usuário.", ephemeral=True)
                return
            embed = self.create_interaction_embed(action_details, author)
            await interaction.response.send_message(embed=embed)
            update_stats(author.id, None, action)
        else:
            # Ação com alvo
            if not target_user:
                await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} Você precisa mencionar um usuário para {verb} com ele!", ephemeral=True)
                return

            if target_user.id == author.id:
                self_messages = [
                    f"{get_emoji(self.bot, 'thinking')} {author.mention}, por que você tentaria {action_details['verb']} a si mesmo?",
                    f"{get_emoji(self.bot, 'peek')} {author.mention}, interagir consigo mesmo? Talvez tente com outro usuário!",
                    f"{get_emoji(self.bot, 'thinking')} {author.mention} parece precisar de um {action}... de si mesmo? {get_emoji(self.bot, 'peek')}"
                ]
                await interaction.response.send_message(random.choice(self_messages), ephemeral=True)
            elif target_user.bot:
                bot_messages = [
                    f"{get_emoji(self.bot, 'sad')} {author.mention}, você não pode {action_details['verb']} um bot como {target_user.mention}! Eles são imunes!",
                    f"{get_emoji(self.bot, 'peek')} Bots não têm sentimentos para {action}, {author.mention}. Tente com um humano!",
                    f"{target_user.mention} observa {author.mention} tentando {action_details['verb']}... {get_emoji(self.bot, 'thinking')}"
                ]
                await interaction.response.send_message(random.choice(bot_messages), ephemeral=True)
            else:
                embed = self.create_interaction_embed(action_details, author, target_user)
                # Mensagem inicial menciona o alvo para notificação
                await interaction.response.send_message(f"{target_user.mention}", embed=embed)
                update_stats(author.id, target_user.id, action)

    async def _generate_commands(self):
        """Gera e registra todos os comandos de interação dinamicamente."""
        # Tenta buscar comandos registrados no servidor específico
        try:
            registered_commands = await self.bot.fetch_guild_commands(SERVER_ID)
            registered_command_names = {cmd.name for cmd in registered_commands}
            print(f"--- [Interacoes] {len(registered_command_names)} comandos já registrados no servidor {SERVER_ID}.")
        except Exception as e:
            print(f"[AVISO] Falha ao buscar comandos do servidor {SERVER_ID}: {e}. Verificação de duplicados pode falhar.")
            registered_command_names = set()

        commands_added = 0
        for action_name, details in self.interaction_gifs.items():
            if action_name in registered_command_names:
                # print(f"--> [Interacoes] Comando '/{action_name}' já registrado. Pulando.")
                continue

            is_solo = details.get("solo", False)
            verb = details["verb"]
            description = f"{verb.capitalize()}.


            if not is_solo:
                description += " um usuário."

            # Define a função de comando específica para esta ação
            # Usamos um truque com default arguments para capturar o action_name correto no momento da definição
            async def command_func(interaction: Interaction, 
                                   target: Member | User | None = SlashOption(description="O usuário para interagir (ou deixe em branco para ações solo)", required=not is_solo),
                                   _action=action_name): # Captura o nome da ação
                await self._interaction_command_template(interaction, target, _action)

            # Define o nome da função dinamicamente (importante para o nextcord)
            command_func.__name__ = f"cmd_{action_name}"

            # Aplica cooldown
            # Usando cooldown por usuário
            cooled_down_func = application_checks.cooldown(1, COOLDOWN_SECONDS, bucket=nextcord.Buckets.user)(command_func)

            # Cria o comando slash usando o decorator e o associa à função criada
            slash_command = nextcord.slash_command(
                name=action_name,
                description=description,
                guild_ids=[SERVER_ID]
            )(cooled_down_func)

            # Adiciona o comando slash criado ao bot
            try:
                self.bot.add_application_command(slash_command)
                # print(f"--> [Interacoes] Comando '/{action_name}' adicionado para registro.")
                commands_added += 1
            except Exception as e:
                 print(f"[ERRO] Falha ao adicionar comando '/{action_name}': {e}")
                 traceback.print_exc()
                 
        print(f"--- [Interacoes] {commands_added} novos comandos adicionados para registro.")

    # --- Comando de Estatísticas --- 
    @nextcord.slash_command(
        guild_ids=[SERVER_ID],
        name="interstats",
        description="Mostra suas estatísticas de interação ou de outro usuário."
    )
    async def interstats(self, interaction: Interaction, usuario: Member | User = SlashOption(required=False, description="Usuário para ver as estatísticas (padrão: você)")):
        """Exibe as estatísticas de interações enviadas e recebidas."""
        target_user = usuario or interaction.user
        stats = load_stats()
        user_id_str = str(target_user.id)

        if user_id_str not in stats:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} {target_user.mention} ainda não tem estatísticas de interação registradas.", ephemeral=True)
            return

        user_stats = stats[user_id_str]
        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Estatísticas de Interação de {target_user.display_name}", color=DEFAULT_COLOR)
        embed.set_thumbnail(url=target_user.display_avatar.url)

        # Stats Enviadas
        sent_actions = user_stats.get("sent", {})
        sent_total = sum(count for target_actions in sent_actions.values() for count in target_actions.values())
        sent_top_action = "Nenhuma" 
        sent_top_count = 0
        sent_top_target = "Ninguém"
        sent_top_target_count = 0
        
        action_counts = {}
        target_counts = {}
        for target_id, actions in sent_actions.items():
            target_total = sum(actions.values())
            target_counts[target_id] = target_total
            if target_total > sent_top_target_count:
                sent_top_target_count = target_total
                sent_top_target = target_id
            for action, count in actions.items():
                action_counts[action] = action_counts.get(action, 0) + count
                if action_counts[action] > sent_top_count:
                    sent_top_count = action_counts[action]
                    sent_top_action = action
                    
        sent_top_target_mention = f"<@{sent_top_target}>" if sent_top_target != "Ninguém" else "Ninguém"
        sent_desc = f"Total: **{sent_total}** interações enviadas.\n" \
                    f"Ação mais usada: **{sent_top_action}** ({sent_top_count} vezes).\n" \
                    f"Mais interagiu com: **{sent_top_target_mention}** ({sent_top_target_count} vezes)."
        embed.add_field(name="📤 Enviadas", value=sent_desc, inline=False)

        # Stats Recebidas
        received_actions = user_stats.get("received", {})
        received_total = sum(count for sender_actions in received_actions.values() for count in sender_actions.values())
        received_top_action = "Nenhuma"
        received_top_count = 0
        received_top_sender = "Ninguém"
        received_top_sender_count = 0
        
        action_counts_rec = {}
        sender_counts = {}
        for sender_id, actions in received_actions.items():
            sender_total = sum(actions.values())
            sender_counts[sender_id] = sender_total
            if sender_total > received_top_sender_count:
                received_top_sender_count = sender_total
                received_top_sender = sender_id
            for action, count in actions.items():
                action_counts_rec[action] = action_counts_rec.get(action, 0) + count
                if action_counts_rec[action] > received_top_count:
                    received_top_count = action_counts_rec[action]
                    received_top_action = action
                    
        received_top_sender_mention = f"<@{received_top_sender}>" if received_top_sender != "Ninguém" else "Ninguém"
        received_desc = f"Total: **{received_total}** interações recebidas.\n" \
                        f"Ação mais recebida: **{received_top_action}** ({received_top_count} vezes).\n" \
                        f"Mais interagiu com você: **{received_top_sender_mention}** ({received_top_sender_count} vezes)."
        embed.add_field(name="📥 Recebidas", value=received_desc, inline=False)

        # Stats Solo
        solo_actions = user_stats.get("solo", {})
        solo_total = sum(solo_actions.values())
        solo_top_action = "Nenhuma"
        solo_top_count = 0
        for action, count in solo_actions.items():
            if count > solo_top_count:
                solo_top_count = count
                solo_top_action = action
                
        solo_desc = f"Total: **{solo_total}** interações solo.\n" \
                    f"Ação mais usada: **{solo_top_action}** ({solo_top_count} vezes)."
        embed.add_field(name="🧘 Solo", value=solo_desc, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    # --- Tratamento de Erro de Cooldown --- 
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        if isinstance(error, application_checks.ApplicationCommandOnCooldown):
            retry_after = round(error.retry_after)
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'sad')} Calma aí, apressadinho! {get_emoji(self.bot, 'peek')} Você precisa esperar **{retry_after} segundos** para usar este comando novamente.", 
                ephemeral=True
            )
        else:
            # Para outros erros, podemos apenas logar ou enviar uma mensagem genérica
            # Evita que o erro de cooldown seja tratado por outros listeners
            # print(f"Erro em comando de aplicação (Interacoes): {error}")
            pass # Deixa outros error handlers (se houver) cuidarem

# Função setup para carregar a cog
def setup(bot):
    """Adiciona a cog Interacoes ao bot."""
    # Cria o diretório de dados se não existir
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    bot.add_cog(Interacoes(bot))
