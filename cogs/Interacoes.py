# /home/ubuntu/ShirayukiBot/cogs/Interacoes.py
# Cog para comandos de interação social.

import random
import nextcord
from nextcord import Interaction, Embed, Color, Member, SlashOption
from nextcord.ext import commands

# --- Emojis Customizados ---
EMOJI_SUCCESS = "<:8_:1366997164521164830>" # Emoji de sucesso
EMOJI_FAILURE = "<:1_:1366996823654535208>" # Emoji de falha/triste
EMOJI_INFO = "<:7_:1366997117410873404>"    # Emoji de informação/neutro
EMOJI_WAIT = "<:2_:1366996885398749254>"     # Emoji de espera
EMOJI_QUESTION = "<:6_:1366997079347429427>" # Emoji de dúvida/ajuda
EMOJI_WARN = "<:4_:1366996921297801216>"     # Emoji de aviso
EMOJI_CELEBRATE = "<:5_:1366997045445132360>" # Emoji de celebração
EMOJI_HAPPY = "<:3_:1366996904663322654>"     # Emoji feliz genérico

# --- Configurações ---
SERVER_ID = 1367345048458498219 # Para registro rápido de comandos
DEFAULT_COLOR = Color.magenta() # Cor padrão para embeds de interação

# --- Banco de GIFs --- 
# Expandido com mais opções e novas interações
INTERACTION_GIFS = {
    "hug": [
        "https://media.tenor.com/2roX3uxz_68AAAAC/hug.gif",
        "https://media.tenor.com/NeXn0mMF5iYAAAAC/anime-hug.gif",
        "https://media.tenor.com/Jl8nD1kOAQMAAAAC/kyoukai-no-kanata-hug.gif",
        "https://media.tenor.com/82Ax6lt0__4AAAAC/hug-anime.gif",
        "https://media.tenor.com/YY94q2HwWNEAAAAC/anime-hug.gif"
    ],
    "kiss": [
        "https://media.tenor.com/Bq7iU7yb3OsAAAAC/kiss-anime.gif",
        "https://media.tenor.com/0AVn4U0VOnwAAAAC/anime-kiss.gif",
        "https://media.tenor.com/QvL8v7lPPX8AAAAC/kaguya-sama-kiss.gif",
        "https://media.tenor.com/jnndDmOm5wMAAAAC/kiss.gif",
        "https://media.tenor.com/bM043Eb44jcAAAAC/anime-kiss.gif"
    ],
    "slap": [
        "https://media.tenor.com/5zv7N_p4OZMAAAAC/anime-slap.gif",
        "https://media.tenor.com/RwD7bRfGzIYAAAAC/slap.gif",
        "https://media.tenor.com/2xl4JgxTtIUAAAAC/anime-hit.gif",
        "https://media.tenor.com/1-1Lkl_3L_QAAAAC/slap-anime.gif",
        "https://media.tenor.com/UDo0WPttiJAAAAAC/anime-slap-mad.gif"
    ],
    "pat": [
        "https://media.tenor.com/7vZ9TnA1fFQAAAAC/pat-head.gif",
        "https://media.tenor.com/YGdCdp9bMGUAAAAC/anime-pat.gif",
        "https://media.tenor.com/wfTj8Dh9EYAAAAAC/pat-anime.gif",
        "https://media.tenor.com/N-dZg4hN6wYAAAAC/anime-head-pat.gif",
        "https://media.tenor.com/HYbMAU0X2fkAAAAC/anime-pat.gif"
    ],
    "bite": [
        "https://media.tenor.com/UDfwDPuV_yoAAAAC/anime-bite.gif",
        "https://media.tenor.com/xsKZJ8-LUGkAAAAC/anime.gif",
        "https://media.tenor.com/W9FJKdGzOjcAAAAC/bite-anime.gif",
        "https://media.tenor.com/89QWOU0h7TEAAAAC/anime-bite.gif",
        "https://media.tenor.com/X1Erht6hwJgAAAAC/anime-bite.gif"
    ],
    "lick": [
        "https://media.tenor.com/bJDa8H-rQZ4AAAAC/anime-lick.gif",
        "https://media.tenor.com/RRjht8v7voIAAAAC/lick-anime.gif",
        "https://media.tenor.com/B5sh8dESbZ4AAAAC/anime-licking.gif",
        "https://media.tenor.com/1E0t0D-V6TIAAAAC/lick-anime.gif",
        "https://media.tenor.com/jXThnL95hCUAAAAC/lick.gif"
    ],
    "punch": [
        "https://media.tenor.com/LIYkB7qz2JQAAAAC/anime-punch.gif",
        "https://media.tenor.com/bmA4WcLh-YkAAAAC/punch-anime.gif",
        "https://media.tenor.com/TS8u4IS_2NIAAAAC/punch-hit.gif",
        "https://media.tenor.com/EvBn8X0W7Q0AAAAC/anime-punch.gif",
        "https://media.tenor.com/6YhF0F0B0hIAAAAC/anime-fight.gif"
    ],
    "kick": [
        "https://media.tenor.com/_uS2CBQW0aYAAAAC/kick-anime.gif",
        "https://media.tenor.com/GzyM0mHf2ksAAAAC/anime-kick.gif",
        "https://media.tenor.com/rNHyL8PzAoYAAAAC/kick.gif",
        "https://media.tenor.com/Y59d_Nl0gRQAAAAC/anime-kick.gif",
        "https://media.tenor.com/YfW-8gOcOLAAAAAC/anime-kick.gif"
    ],
    "cuddle": [
        "https://media.tenor.com/Pj4YjKdCMhcAAAAC/anime-cuddle.gif",
        "https://media.tenor.com/Nhcz0gKaNfcAAAAC/anime-hug-cuddle.gif",
        "https://media.tenor.com/NtdhsW5TKaAAAAAC/cuddle.gif",
        "https://media.tenor.com/oSPiG4-92NAAAAAC/anime-cuddle.gif",
        "https://media.tenor.com/gksuvTLMu2IAAAAC/cuddle-anime.gif"
    ],
    "poke": [
        "https://media.tenor.com/vEGlwQZ9HdgAAAAC/poke-anime.gif",
        "https://media.tenor.com/fuX0aW1FhZsAAAAC/anime-poke.gif",
        "https://media.tenor.com/7uhzLQxcmcUAAAAC/poking-anime.gif",
        "https://media.tenor.com/LzgzRM95tqgAAAAC/poke.gif",
        "https://media.tenor.com/b0g6a-ZSKTAAAAAC/anime-poke.gif"
    ],
    "highfive": [
        "https://media.tenor.com/jC1aHxw_d7gAAAAC/anime-highfive.gif",
        "https://media.tenor.com/MNeOgw0Af5sAAAAC/highfive-anime.gif",
        "https://media.tenor.com/j2doT4CBhyUAAAAC/high-five-anime.gif",
        "https://media.tenor.com/3Lz7gB_gXHUAAAAC/high-five.gif",
        "https://media.tenor.com/y6aVdzuQ-pUAAAAC/anime.gif"
    ],
    "wave": [
        "https://media.tenor.com/WRR8oR6pqOwAAAAC/anime-wave.gif",
        "https://media.tenor.com/pS5fGiDw6vQAAAAC/hi-hello.gif",
        "https://media.tenor.com/qHdzgBl8XMQAAAAC/hello-anime.gif",
        "https://media.tenor.com/NMVny6GqqW8AAAAC/anime-wave.gif",
        "https://media.tenor.com/23QeN0d46kQAAAAC/anime-wave.gif"
    ],
    "stare": [
        "https://media.tenor.com/GzEcNNhxW7IAAAAC/anime-stare.gif",
        "https://media.tenor.com/lZZzHtJAM7EAAAAC/stare-anime.gif",
        "https://media.tenor.com/lE84w_Vl_WUAAAAC/anime-look.gif",
        "https://media.tenor.com/u_n1L6Lg04AAAAAC/anime-stare.gif",
        "https://media.tenor.com/3N080V5m7NQAAAAC/stare-anime.gif"
    ],
    "dance": [
        "https://media.tenor.com/NZfPdV2pFFYAAAAC/anime-dance.gif",
        "https://media.tenor.com/TObCV91w6bEAAAAC/dance.gif",
        "https://media.tenor.com/4cKkGBeAKDMAAAAC/anime-dancing.gif",
        "https://media.tenor.com/CgGUXLN0gVsAAAAC/anime-dance.gif",
        "https://media.tenor.com/hMeQTq60R-0AAAAC/dance-anime.gif"
    ],
    "blush": [
        "https://media.tenor.com/1v3uPQVCn6cAAAAC/anime-blush.gif",
        "https://media.tenor.com/FJwHkE_JwCwAAAAC/blush-anime.gif",
        "https://media.tenor.com/lkW5R4SBYWwAAAAC/blushing-anime.gif",
        "https://media.tenor.com/e6EUOM0qQ5IAAAAC/anime-blush.gif",
        "https://media.tenor.com/r7fzaM7Lp0UAAAAC/anime-blush.gif"
    ],
    "cry": [
        "https://media.tenor.com/6u6UEvWhYdwAAAAC/crying-anime.gif",
        "https://media.tenor.com/RVvnVPK-6dcAAAAC/anime-crying.gif",
        "https://media.tenor.com/RSj3vGkL5X8AAAAC/cry-anime.gif",
        "https://media.tenor.com/8hDrYLd4Y6YAAAAC/anime-cry.gif",
        "https://media.tenor.com/3KCaJ0TYVm0AAAAC/anime-cry.gif"
    ],
    "sleep": [
        "https://media.tenor.com/9iS9kivD8JMAAAAC/sleepy.gif",
        "https://media.tenor.com/ZghfHZ-W4B0AAAAC/sleep.gif",
        "https://media.tenor.com/BzLaCmQ_WQQAAAAC/anime-sleep.gif",
        "https://media.tenor.com/T7wQZ40nY0wAAAAC/anime-sleep.gif",
        "https://media.tenor.com/z4rmrZK9-qIAAAAC/anime-sleep.gif"
    ],
    "feed": [
        "https://media.tenor.com/3vDgHFUAN7gAAAAC/feed-anime.gif",
        "https://media.tenor.com/zDjHvJbuwq4AAAAC/anime-feed.gif",
        "https://media.tenor.com/Ll9d9CnJGywAAAAC/feeding-anime.gif",
        "https://media.tenor.com/7jOcQ055jMoAAAAC/anime-feed.gif",
        "https://media.tenor.com/XfWvQG4cbqEAAAAC/anime-feed.gif"
    ],
    "confused": [
        "https://media.tenor.com/N4NUK19U8NMAAAAC/anime-confused.gif",
        "https://media.tenor.com/UoG4jQE0-_cAAAAC/anime-confused.gif",
        "https://media.tenor.com/f54j144m0gAAAAAC/confused-anime.gif",
        "https://media.tenor.com/3XSYGjpzylMAAAAC/anime-confused.gif"
    ],
    "facepalm": [
        "https://media.tenor.com/JBgP4kX7L00AAAAC/anime-facepalm.gif",
        "https://media.tenor.com/PDgN5-8EB1wAAAAC/facepalm-anime.gif",
        "https://media.tenor.com/Gu0dGgk77uQAAAAC/anime-facepalm.gif",
        "https://media.tenor.com/VLcxIXJd8oQAAAAC/facepalm-anime.gif"
    ],
    "applaud": [
        "https://media.tenor.com/mGH6yxTQ5g0AAAAC/anime-clapping.gif",
        "https://media.tenor.com/tJHUJ9QY8iAAAAAC/clapping-anime.gif",
        "https://media.tenor.com/7FfPzfgh5WgAAAAC/anime-clap.gif",
        "https://media.tenor.com/1FDy6HTQnFMAAAAC/anime-clapping.gif"
    ]
}

# --- Cog Interacoes --- 
class Interacoes(commands.Cog):
    """Comandos de interação social com outros usuários, usando GIFs."""
    def __init__(self, bot):
        self.bot = bot
        # A geração de comandos agora acontece no evento on_ready ou similar
        # para garantir que o bot esteja pronto. Vamos adicionar um método para isso.
        # self._generate_commands() # Não gerar aqui diretamente
        self.commands_generated = False
        print(f"[DIAGNÓSTICO] Cog Interacoes inicializada.")

    @commands.Cog.listener()
    async def on_ready(self):
        """Gera os comandos dinamicamente quando o bot está pronto."""
        # Garante que os comandos sejam gerados apenas uma vez
        if not self.commands_generated:
            print("--- [Interacoes] Bot pronto, gerando comandos de interação... ---")
            await self._generate_commands()
            self.commands_generated = True
            print("--- [Interacoes] Geração de comandos de interação concluída. ---")

    def get_interaction_verb(self, action: str) -> str:
        """Retorna o verbo formatado para uma ação específica."""
        verbs = {
            "hug": "abraçou",
            "kiss": "beijou",
            "slap": "deu um tapa em",
            "pat": "acariciou",
            "bite": "mordeu",
            "lick": "lambeu",
            "punch": "deu um soco em",
            "kick": "chutou",
            "cuddle": "se aconchegou com",
            "poke": "cutucou",
            "highfive": "bateu um highfive com",
            "wave": "acenou para",
            "stare": "encarou",
            "dance": "dançou com",
            "blush": "ficou corado com", # Ou "por causa de"?
            "cry": "chorou com", # Ou "por causa de"?
            "sleep": "dormiu junto com",
            "feed": "deu comida para",
            "confused": "ficou confuso com",
            "facepalm": "fez um facepalm por causa de",
            "applaud": "aplaudiu"
        }
        return verbs.get(action, action) # Retorna a própria ação se não encontrar verbo

    def get_interaction_emoji(self, action: str) -> str:
        """Retorna um emoji apropriado para a ação."""
        # Mapeamento simples, pode ser mais elaborado
        if action in ["hug", "kiss", "cuddle", "pat", "highfive", "wave", "applaud", "feed", "dance", "blush", "sleep"]:
            return EMOJI_HAPPY
        elif action in ["slap", "punch", "kick", "bite", "stare", "facepalm"]:
            return EMOJI_WARN # Ou talvez um emoji de raiva?
        elif action in ["cry"]:
            return EMOJI_FAILURE
        elif action in ["poke", "lick", "confused"]:
            return EMOJI_QUESTION
        else:
            return EMOJI_INFO # Padrão

    def create_interaction_embed(self, action: str, user1: Member, user2: Member) -> Embed:
        """Cria o embed para a mensagem de interação."""
        gif = random.choice(INTERACTION_GIFS[action])
        verb = self.get_interaction_verb(action)
        emoji = self.get_interaction_emoji(action)
        
        # Variações de título
        titles = [
            f"{emoji} {user1.display_name} {verb} {user2.display_name}!",
            f"{user1.display_name} e {user2.display_name} - {action.capitalize()}! {emoji}",
            f"{action.capitalize()}! {user1.display_name} {verb} {user2.display_name} {emoji}"
        ]
        
        embed = Embed(title=random.choice(titles), color=DEFAULT_COLOR)
        embed.set_image(url=gif)
        embed.set_footer(text=f"Interagindo... {random.choice([EMOJI_HAPPY, EMOJI_CELEBRATE, EMOJI_INFO])}")
        return embed

    async def _interaction_command_template(self, interaction: Interaction, user: Member, action: str):
        """Template interno para a lógica dos comandos de interação."""
        if user.id == interaction.user.id:
            # Mensagens variadas para auto-interação
            self_messages = [
                f"{EMOJI_QUESTION} {interaction.user.mention}, por que você tentaria {self.get_interaction_verb(action)} a si mesmo?",
                f"{EMOJI_WARN} {interaction.user.mention}, interagir consigo mesmo? Talvez tente com outro usuário!",
                f"{EMOJI_INFO} {interaction.user.mention} parece precisar de um {action}... de si mesmo? {EMOJI_WAIT}"
            ]
            await interaction.response.send_message(random.choice(self_messages), ephemeral=True)
        elif user.bot:
             # Mensagens variadas para interação com bots
            bot_messages = [
                f"{EMOJI_FAILURE} {interaction.user.mention}, você não pode {self.get_interaction_verb(action)} um bot como {user.mention}!",
                f"{EMOJI_WARN} Bots não têm sentimentos para {action}, {interaction.user.mention}. Tente com um humano!",
                f"{user.mention} observa {interaction.user.mention} tentando {self.get_interaction_verb(action)}... {EMOJI_INFO}"
            ]
            await interaction.response.send_message(random.choice(bot_messages), ephemeral=True)
        else:
            embed = self.create_interaction_embed(action, interaction.user, user)
            await interaction.response.send_message(f"{user.mention}", embed=embed) # Menciona o usuário alvo

    async def _generate_commands(self):
        """Gera e registra todos os comandos de interação dinamicamente."""
        registered_commands = await self.bot.fetch_global_commands() # Ou fetch_guild_commands(SERVER_ID)
        registered_command_names = {cmd.name for cmd in registered_commands}
        
        for action_name in INTERACTION_GIFS:
            if action_name in registered_command_names:
                print(f"--> [Interacoes] Comando 
                continue
                
            # Cria a função de comando específica para esta ação
            async def command_func(interaction: Interaction, user: Member = SlashOption(description="O usuário para interagir", required=True)):
                # Captura o nome da ação do nome da função interna
                action = interaction.application_command.name
                await self._interaction_command_template(interaction, user, action)
            
            # Define o nome da função dinamicamente (importante para o nextcord)
            command_func.__name__ = f"cmd_{action_name}" 
            
            # Cria o comando slash usando o decorator e o associa à função criada
            # Registrando no servidor específico para testes rápidos
            slash_command = nextcord.slash_command(
                name=action_name, 
                description=f"{self.get_interaction_verb(action_name).capitalize()} um usuário.",
                guild_ids=[SERVER_ID] 
            )(command_func)
            
            # Adiciona o comando slash criado ao bot
            # O nextcord cuida de adicioná-lo ao cog correto se chamado de dentro do cog
            self.bot.add_application_command(slash_command)
            print(f"--> [Interacoes] Comando 

# Função setup para carregar a cog
def setup(bot):
    """Adiciona a cog Interacoes ao bot."""
    bot.add_cog(Interacoes(bot))
