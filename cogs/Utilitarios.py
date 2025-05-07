# /home/ubuntu/ShirayukiBot/cogs/Utilitarios.py
# Cog para comandos utilitários diversos.

import os
import random
import secrets
import math
import asyncio
import aiohttp
import nextcord
from nextcord import Interaction, Embed, SlashOption, Color, File, Member, User, TextChannel, Role, ButtonStyle
from nextcord.ext import commands, tasks, application_checks
from nextcord import ui
import datetime
from datetime import timezone # Alterado para importar timezone diretamente de datetime
import pytz # Para fusos horários
import qrcode # Para gerar QR codes
from io import BytesIO
import json
import wikipediaapi # Para buscar na Wikipedia
import googletrans # Para tradução
import pyfiglet # Para ASCII Art
from PIL import Image, ImageDraw, ImageFont # Para manipulação de imagem (ex: color)
import re # Para parsing de tempo e calculadora
import ast # Para avaliação segura de expressões matemáticas
import operator as op # Para calculadora segura

# Importar helper de emojis
from utils.emojis import get_emoji

# --- Configurações --- 
DATA_DIR = "/home/ubuntu/ShirayukiBot/data"
REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")
SUGGESTIONS_CHANNEL_NAME = "sugestoes" # Nome do canal para enviar sugestões
DEFAULT_TIMEZONE = "America/Sao_Paulo"
WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY") # Necessário definir variável de ambiente
WIKIPEDIA_USER_AGENT = "ShirayukiBot/1.0 (Discord Bot; https://github.com/iamkevyn/ShirayukiBot)"

# --- Funções Auxiliares --- 
def ensure_dir_exists(file_path):
    """Garante que o diretório de um arquivo exista."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"[{datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Diretório criado: {directory}")

def load_json_data(file_path, default_data):
    """Carrega dados de um arquivo JSON, criando-o com dados padrão se não existir."""
    ensure_dir_exists(file_path)
    if not os.path.exists(file_path):
        print(f'[{datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [AVISO] Arquivo {os.path.basename(file_path)} não encontrado. Criando com dados padrão.')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f'[{datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO] Falha ao carregar {os.path.basename(file_path)}, usando dados padrão.')
        return default_data

def save_json_data(file_path, data):
    """Salva dados em um arquivo JSON."""
    ensure_dir_exists(file_path)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f'[{datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO] Falha ao salvar {os.path.basename(file_path)}: {e}')

def parse_time(time_str: str) -> int | None:
    seconds = 0
    matches = re.findall(r'(\\d+)([dhms])', time_str.lower())
    if not matches:
        return None
    for value, unit in matches:
        value = int(value)
        if unit == 'd':
            seconds += value * 86400
        elif unit == 'h':
            seconds += value * 3600
        elif unit == 'm':
            seconds += value * 60
        elif unit == 's':
            seconds += value
    return seconds if seconds > 0 else None

def format_seconds(seconds: int) -> str:
    if seconds < 0:
        return "Tempo inválido"
    if seconds == 0:
        return "0s"
    
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts: 
        parts.append(f"{secs}s")
        
    return " ".join(parts)

allowed_operators = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod,
    ast.USub: op.neg, ast.UAdd: op.pos
}
allowed_math_funcs = {
    'sqrt': math.sqrt, 'pow': math.pow, 'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
    'asin': math.asin, 'acos': math.acos, 'atan': math.atan, 'log': math.log, 'log10': math.log10,
    'pi': math.pi, 'e': math.e, 'abs': abs, 'round': round
}

def safe_eval_math(expr):
    """Avalia uma expressão matemática de forma segura."""
    try:
        node = ast.parse(expr, mode='eval')
    except (SyntaxError, ValueError):
        raise ValueError("Expressão inválida")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_func = allowed_operators.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Operador não permitido: {type(node.op).__name__}")
            return op_func(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op_func = allowed_operators.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Operador unário não permitido: {type(node.op).__name__}")
            return op_func(operand)
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            func = allowed_math_funcs.get(func_name.lower())
            if func is None:
                raise ValueError(f"Função não permitida: {func_name}")
            args = [_eval(arg) for arg in node.args]
            return func(*args)
        elif isinstance(node, ast.Name):
            const_val = allowed_math_funcs.get(node.id.lower())
            if const_val is None or callable(const_val):
                 raise ValueError(f"Nome não permitido: {node.id}")
            return const_val
        else:
            raise ValueError(f"Tipo de nó não suportado: {type(node).__name__}")
    return _eval(node)

class SugestaoModal(ui.Modal):
    def __init__(self, suggestions_channel_name: str, bot: commands.Bot):
        super().__init__("Sugestão para o Bot")
        self.suggestions_channel_name = suggestions_channel_name
        self.bot = bot
        self.titulo = ui.TextInput(label="Título da sugestão", placeholder="Ex: Novo comando de música", required=True, max_length=100)
        self.descricao = ui.TextInput(label="Descrição detalhada", style=nextcord.TextInputStyle.paragraph, placeholder="Explique sua ideia, como funcionaria, etc.", required=True, max_length=1000)
        self.add_item(self.titulo)
        self.add_item(self.descricao)

    async def callback(self, interaction: Interaction):
        embed = Embed(title=f"{get_emoji(self.bot, 'idea')} Nova Sugestão Recebida", color=Color.green())
        embed.add_field(name="Título", value=self.titulo.value, inline=False)
        embed.add_field(name="Descrição", value=self.descricao.value, inline=False)
        embed.set_footer(text=f"Enviado por {interaction.user.display_name} ({interaction.user.id})")
        embed.timestamp = datetime.datetime.now(pytz.utc)

        await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Sugestão enviada com sucesso! Obrigado pela sua contribuição.", ephemeral=True)
        
        if not interaction.guild:
            await interaction.followup.send(f"{get_emoji(self.bot, 'thinking')} Não consigo enviar sugestões de DMs.", ephemeral=True)
            return
            
        canal_logs = nextcord.utils.get(interaction.guild.text_channels, name=self.suggestions_channel_name)
        if canal_logs:
            try:
                await canal_logs.send(embed=embed)
            except nextcord.Forbidden:
                 await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Não tenho permissão para enviar a sugestão no canal #{self.suggestions_channel_name}.", ephemeral=True)
            except Exception as e:
                 await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao enviar sugestão para #{self.suggestions_channel_name}: {e}", ephemeral=True)
        else:
            await interaction.followup.send(f"{get_emoji(self.bot, 'warn')} Canal #{self.suggestions_channel_name} não encontrado neste servidor. A sugestão foi registrada, mas não pude enviá-la para o canal específico.", ephemeral=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [Sugestão] {interaction.user}: {self.titulo.value} - {self.descricao.value}")

class EnqueteView(ui.View):
    def __init__(self, interaction: Interaction, pergunta: str, opcoes_lista: list, bot: commands.Bot):
        super().__init__(timeout=None)
        self.creator_id = interaction.user.id
        self.pergunta = pergunta
        self.opcoes = opcoes_lista
        self.bot = bot
        self.votos = {i: 0 for i in range(len(opcoes_lista))}
        self.votantes = set()
        self.message = None 
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for i, opcao in enumerate(self.opcoes):
            label_text = opcao[:75] + ('...' if len(opcao) > 75 else '')
            label = f"{label_text} ({self.votos[i]})"
            button = ui.Button(label=label, custom_id=f"vote_{i}", style=ButtonStyle.primary)
            button.callback = self.create_callback(i)
            self.add_item(button)
        finish_button = ui.Button(label="Finalizar Enquete", custom_id="finish_poll", style=ButtonStyle.danger, row=4)
        finish_button.callback = self.finish_poll_callback
        self.add_item(finish_button)

    def create_callback(self, index: int):
        async def callback(interaction: Interaction):
            user_id = interaction.user.id
            if user_id in self.votantes:
                await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você já votou nesta enquete!", ephemeral=True)
                return

            self.votos[index] += 1
            self.votantes.add(user_id)
            self.update_buttons()
            
            embed = self.create_poll_embed()
            try:
                await interaction.response.edit_message(embed=embed, view=self)
                await interaction.followup.send(f"{get_emoji(self.bot, 'happy_flower')} Seu voto para **{self.opcoes[index]}** foi registrado!", ephemeral=True)
            except nextcord.NotFound:
                self.stop()
            except nextcord.HTTPException as e:
                print(f"[ERRO Enquete] Falha ao editar mensagem: {e}")
                await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao registrar seu voto. Tente novamente.", ephemeral=True)
                self.votos[index] -= 1
                self.votantes.remove(user_id)
                self.update_buttons()
        return callback

    async def finish_poll_callback(self, interaction: Interaction):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Apenas {interaction.guild.get_member(self.creator_id).mention if interaction.guild else 'o criador'} pode finalizar esta enquete.", ephemeral=True)
            return
            
        embed = self.create_poll_embed(final=True)
        try:
            await interaction.response.edit_message(embed=embed, view=None)
        except nextcord.NotFound:
            pass 
        self.stop()

    def create_poll_embed(self, final: bool = False) -> Embed:
        title = f"📊 Enquete{' Finalizada' if final else ''}"
        embed = Embed(title=title, description=self.pergunta, color=Color.blue())
        total_votos = sum(self.votos.values())
        
        resultados = []
        sorted_indices = sorted(self.votos, key=self.votos.get, reverse=True)
        
        for i in sorted_indices:
            opcao = self.opcoes[i]
            votos_opcao = self.votos[i]
            percentual = (votos_opcao / total_votos * 100) if total_votos > 0 else 0
            resultados.append(f"**{opcao}**: {votos_opcao} voto{'s' if votos_opcao != 1 else ''} ({percentual:.1f}%)")
            
        embed.add_field(name="Resultados", value="\n".join(resultados) if resultados else "Nenhum voto ainda.", inline=False)
        embed.set_footer(text=f"Total de votos: {total_votos}")
        if not final:
            embed.timestamp = datetime.datetime.now(pytz.utc)
        return embed

class Utilitarios(commands.Cog):
    """Comandos utilitários diversos para o dia a dia."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.translator = googletrans.Translator()
        self.wiki = wikipediaapi.Wikipedia(
            language='pt', 
            user_agent=WIKIPEDIA_USER_AGENT
        )
        self.reminders = load_json_data(REMINDERS_FILE, [])
        self.quotes = self.load_default_quotes()
        self.curiosidades = self.load_default_curiosidades()
        self.check_reminders.start()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Cog Utilitarios carregada.")
        print(f"[Utilitarios] {len(self.reminders)} lembretes carregados.")

    def cog_unload(self):
        self.check_reminders.cancel()
        asyncio.create_task(self.session.close())

    def load_default_quotes(self):
        return [
            ("A persistência realiza o impossível.", "Provérbio Chinês"), 
            ("O sucesso é a soma de pequenos esforços repetidos todos os dias.", "Robert Collier"),
            ("Não sabendo que era impossível, foi lá e fez.", "Jean Cocteau"), 
            ("Coragem é resistência ao medo, domínio do medo, e não ausência do medo.", "Mark Twain"),
            ("Grandes mentes discutem ideias; mentes medianas discutem eventos; mentes pequenas discutem pessoas.", "Eleanor Roosevelt"),
            ("Seja a mudança que você quer ver no mundo.", "Mahatma Gandhi"), 
            ("A vida é 10% o que acontece com você e 90% como você reage.", "Charles R. Swindoll"),
            ("A melhor maneira de prever o futuro é criá-lo.", "Peter Drucker"), 
            ("Você nunca será velho demais para definir outro objetivo ou sonhar um novo sonho.", "C.S. Lewis"),
            ("A mente que se abre a uma nova ideia jamais voltará ao seu tamanho original.", "Albert Einstein")
        ]

    def load_default_curiosidades(self):
        return [
            "Polvos têm três corações e sangue azul.", "O corpo humano brilha no escuro (mas nossos olhos não percebem).",
            "O mel nunca estraga.", "Bananas são tecnicamente frutas vermelhas (bagas).", "Existem mais estrelas no universo do que grãos de areia na Terra.",
            "Os cavalos-marinhos são os únicos animais onde os machos engravidam.", "A Terra não é perfeitamente redonda, é um geoide ligeiramente achatado nos polos.",
            "Formigas não dormem como os humanos, elas têm ciclos de descanso.", "O cérebro humano é mais ativo durante o sono REM do que acordado.", "O DNA humano e o da banana compartilham cerca de 60% de genes."
        ]

    @tasks.loop(seconds=30)
    async def check_reminders(self):
        now = datetime.datetime.now(pytz.utc).timestamp()
        reminders_to_remove_indices = []
        reminders_updated = False
        current_reminders = list(self.reminders)

        for i, reminder in enumerate(current_reminders):
            if reminder["timestamp"] <= now:
                try:
                    user = await self.bot.fetch_user(reminder["user_id"])
                    channel = None
                    if reminder.get("channel_id"):
                        try:
                            channel = await self.bot.fetch_channel(reminder["channel_id"])
                        except (nextcord.NotFound, nextcord.Forbidden):
                            print(f"[AVISO Lembrete] Canal {reminder['channel_id']} não encontrado ou inacessível.")
                    
                    embed = Embed(title=f"{get_emoji(self.bot, 'alarm')} Lembrete!", description=reminder["message"], color=Color.orange())
                    created_dt = datetime.datetime.fromtimestamp(reminder['created_at'], tz=pytz.utc)
                    embed.set_footer(text=f"Lembrete criado em: {created_dt.strftime('%d/%m/%Y %H:%M:%S UTC')}")
                    
                    sent = False
                    if channel and isinstance(channel, TextChannel):
                        try:
                            await channel.send(content=user.mention, embed=embed)
                            sent = True
                        except (nextcord.Forbidden, nextcord.HTTPException) as e:
                            print(f"[ERRO Lembrete] Falha ao enviar no canal {channel.id}: {e}")
                    
                    if not sent:
                        try:
                            dm_channel = await user.create_dm()
                            await dm_channel.send(content=f"Lembrete do servidor/canal `{reminder.get('guild_id', 'DM') or 'DM'}/{reminder.get('channel_id', 'DM')}`:", embed=embed)
                            sent = True
                        except (nextcord.Forbidden, nextcord.HTTPException) as e:
                            print(f"[ERRO Lembrete] Falha ao enviar DM para {user.id}: {e}")
                            
                    reminders_to_remove_indices.append(reminder["created_at"])
                    reminders_updated = True
                    
                except Exception as e:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] [ERRO Lembrete] Erro geral ao processar lembrete criado em {reminder.get('created_at', '???')}: {e}")
                    reminders_to_remove_indices.append(reminder["created_at"])
                    reminders_updated = True

        if reminders_updated:
            self.reminders = [r for r in self.reminders if r["created_at"] not in reminders_to_remove_indices]
            save_json_data(REMINDERS_FILE, self.reminders)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @nextcord.slash_command(name="lembrete", description="Define um lembrete para você.")
    async def lembrete(self, interaction: Interaction, 
                       tempo: str = SlashOption(description="Tempo até o lembrete (ex: 10s, 5m, 2h, 1d, 1d12h)"), 
                       mensagem: str = SlashOption(description="A mensagem do lembrete (máx 1000 chars)", max_length=1000)):
        seconds = parse_time(tempo)
        if seconds is None:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Formato de tempo inválido. Use d, h, m, s (ex: '2h30m', '1d', '45s').", ephemeral=True)
            return

        if seconds > 30 * 86400: 
             await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} O tempo máximo para lembretes é de 30 dias.", ephemeral=True)
             return

        future_timestamp = datetime.datetime.now(pytz.utc).timestamp() + seconds
        created_at = datetime.datetime.now(pytz.utc).timestamp()
        
        reminder_data = {
            "user_id": interaction.user.id,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "timestamp": future_timestamp,
            "created_at": created_at, 
            "message": mensagem
        }
        
        self.reminders.append(reminder_data)
        save_json_data(REMINDERS_FILE, self.reminders)
        
        embed = Embed(title=f"{get_emoji(self.bot, 'alarm')} Lembrete Definido!", color=Color.green())
        embed.description = f"Ok, {interaction.user.mention}! Vou te lembrar sobre:\n>>> {mensagem}"
        embed.add_field(name="Quando", value=f"<t:{int(future_timestamp)}:F> (<t:{int(future_timestamp)}:R>)")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="sugerir", description="Envia uma sugestão para o desenvolvimento do bot.")
    async def sugerir(self, interaction: Interaction):
        modal = SugestaoModal(SUGGESTIONS_CHANNEL_NAME, self.bot)
        await interaction.response.send_modal(modal)

    @nextcord.slash_command(name="enquete", description="Cria uma enquete simples com botões.")
    async def enquete(self, interaction: Interaction, 
                      pergunta: str = SlashOption(description="A pergunta da enquete", required=True, max_length=250),
                      opcao1: str = SlashOption(description="Opção de voto 1", required=True, max_length=80),
                      opcao2: str = SlashOption(description="Opção de voto 2", required=True, max_length=80),
                      opcao3: str = SlashOption(description="Opção de voto 3 (opcional)", required=False, max_length=80),
                      opcao4: str = SlashOption(description="Opção de voto 4 (opcional)", required=False, max_length=80),
                      opcao5: str = SlashOption(description="Opção de voto 5 (opcional)", required=False, max_length=80)
                      ):
        opcoes = [opt for opt in [opcao1, opcao2, opcao3, opcao4, opcao5] if opt is not None]
        if len(opcoes) < 2:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você precisa fornecer pelo menos 2 opções!", ephemeral=True)
            return
            
        view = EnqueteView(interaction, pergunta, opcoes, self.bot)
        embed = view.create_poll_embed()
        embed.set_footer(text=f"Enquete criada por {interaction.user.display_name} | Clique para votar!")
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()

    @nextcord.slash_command(name="citacao", description="Mostra uma citação inspiradora aleatória.")
    async def citacao(self, interaction: Interaction):
        quote, author = random.choice(self.quotes)
        embed = Embed(title=f"{get_emoji(self.bot, 'idea')} Citação do Dia", description=f'> *"{quote}"*', color=Color.gold())
        embed.set_footer(text=f"- {author}")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="curiosidade", description="Conta um fato curioso aleatório.")
    async def curiosidade(self, interaction: Interaction):
        fact = random.choice(self.curiosidades)
        embed = Embed(title=f"{get_emoji(self.bot, 'thinking')} Você Sabia?", description=fact, color=Color.random())
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="senha", description="Gera uma senha segura aleatória.")
    async def senha(self, interaction: Interaction, 
                    tamanho: int = SlashOption(description="Tamanho da senha (8-64)", default=16, min_value=8, max_value=64),
                    usar_simbolos: bool = SlashOption(description="Incluir símbolos? (ex: !@#$)", default=True),
                    usar_numeros: bool = SlashOption(description="Incluir números?", default=True),
                    usar_maiusculas: bool = SlashOption(description="Incluir letras maiúsculas?", default=True),
                    usar_minusculas: bool = SlashOption(description="Incluir letras minúsculas?", default=True)
                    ):
        if not any([usar_simbolos, usar_numeros, usar_maiusculas, usar_minusculas]):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você precisa selecionar pelo menos um tipo de caractere!", ephemeral=True)
            return

        alphabet = ""
        if usar_minusculas: alphabet += "abcdefghijklmnopqrstuvwxyz"
        if usar_maiusculas: alphabet += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if usar_numeros: alphabet += "0123456789"
        if usar_simbolos: alphabet += "!@#$%^&*()_+-=[]{};:,.<>/?"
        
        password = ''.join(secrets.choice(alphabet) for i in range(tamanho))
        
        embed = Embed(title=f"{get_emoji(self.bot, 'sparkle')} Senha Gerada", description=f"Sua senha segura de {tamanho} caracteres está pronta!", color=Color.green())
        embed.add_field(name="Senha", value=f"```\n{password}\n```")
        embed.set_footer(text="Senha enviada apenas para você.")
        
        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Enviei a senha gerada na sua DM!", ephemeral=True)
        except nextcord.Forbidden:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"[ERRO Senha] Falha ao enviar senha: {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Erro ao gerar ou enviar a senha.", ephemeral=True)

    @nextcord.slash_command(name="qrcode", description="Gera um QR Code para um texto ou URL.")
    async def qrcode_cmd(self, interaction: Interaction, texto: str = SlashOption(description="O texto ou URL para gerar o QR Code")):
        await interaction.response.defer()
        try:
            qr_img = qrcode.make(texto)
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")
            buffer.seek(0)
            
            file = File(buffer, filename="qrcode.png")
            embed = Embed(title=f"{get_emoji(self.bot, 'idea')} QR Code Gerado", description=f"QR Code para: `{texto}`", color=Color.blue())
            embed.set_image(url="attachment://qrcode.png")
            
            await interaction.followup.send(embed=embed, file=file)
        except Exception as e:
            print(f"[ERRO QRCode] Falha ao gerar QR Code: {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao gerar o QR Code. Verifique o texto fornecido.", ephemeral=True)

    @nextcord.slash_command(name="tempo", description="Mostra a hora atual em diferentes fusos horários.")
    async def tempo(self, interaction: Interaction, fuso: str = SlashOption(description="Fuso horário (ex: America/Sao_Paulo, Europe/London, Asia/Tokyo)", default=DEFAULT_TIMEZONE)):
        try:
            tz = pytz.timezone(fuso)
            now = datetime.datetime.now(tz)
            embed = Embed(title=f"⏰ Hora Atual em {fuso}", color=Color.blue())
            embed.description = f"**Data:** {now.strftime('%d/%m/%Y')}\n" \
                              f"**Hora:** {now.strftime('%H:%M:%S')}\n" \
                              f"**Fuso:** {now.strftime('%Z%z')}"
            embed.add_field(name="Horário Local (Discord)", value=f"<t:{int(now.timestamp())}:F> (<t:{int(now.timestamp())}:R>)")
            await interaction.response.send_message(embed=embed)
        except pytz.UnknownTimeZoneError:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Fuso horário '{fuso}' desconhecido. Tente um formato como 'Continent/City'.", ephemeral=True)
        except Exception as e:
            print(f"[ERRO Tempo] Falha ao obter hora: {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Erro ao obter a hora para {fuso}.", ephemeral=True)

    @nextcord.slash_command(name="calcular", description="Calcula uma expressão matemática.")
    async def calcular(self, interaction: Interaction, expressao: str = SlashOption(description="A expressão matemática a ser calculada")):
        try:
            expr_clean = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', expressao).strip()
            if not expr_clean:
                raise ValueError("Expressão vazia.")
                
            result = safe_eval_math(expr_clean)
            
            if isinstance(result, float):
                if abs(result) > 1e12 or (abs(result) < 1e-4 and result != 0):
                    result_str = f"{result:.4e}"
                else:
                    result_str = f"{result:.4f}".rstrip('0').rstrip('.')
            else:
                result_str = str(result)
                
            embed = Embed(title=f"{get_emoji(self.bot, 'idea')} Calculadora", color=Color.green())
            embed.add_field(name="Expressão", value=f"```\n{expr_clean}\n```", inline=False)
            embed.add_field(name="Resultado", value=f"```\n{result_str}\n```", inline=False)
            await interaction.response.send_message(embed=embed)
            
        except ValueError as e:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Erro na expressão: {e}. Use apenas números, operadores (+, -, *, /, **, %), parênteses e funções (sqrt, sin, cos, tan, log, abs, round, pi, e).", ephemeral=True)
        except OverflowError:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Resultado muito grande para calcular!", ephemeral=True)
        except Exception as e:
            print(f"[ERRO Calculadora] Expressão '{expressao}': {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro inesperado ao calcular.", ephemeral=True)

    @nextcord.slash_command(name="traduzir", description="Traduz um texto para outro idioma.")
    async def traduzir(self, interaction: Interaction, 
                       texto: str = SlashOption(description="O texto a ser traduzido"), 
                       idioma_destino: str = SlashOption(name="para", description="Idioma de destino (ex: en, pt, es, ja)", default="pt"),
                       idioma_origem: str = SlashOption(name="de", description="Idioma de origem (opcional, detecta automaticamente)", required=False)):
        await interaction.response.defer()
        try:
            src_lang = idioma_origem if idioma_origem else 'auto'
            dest_lang = idioma_destino.lower()
            
            if dest_lang not in googletrans.LANGUAGES and dest_lang not in googletrans.LANGCODES:
                 await interaction.followup.send(f"{get_emoji(self.bot, 'warn')} Idioma de destino '{dest_lang}' inválido.", ephemeral=True)
                 return
            if src_lang != 'auto' and src_lang not in googletrans.LANGUAGES and src_lang not in googletrans.LANGCODES:
                 await interaction.followup.send(f"{get_emoji(self.bot, 'warn')} Idioma de origem '{src_lang}' inválido.", ephemeral=True)
                 return

            translated = self.translator.translate(texto, src=src_lang, dest=dest_lang)
            
            detected_lang_code = translated.src
            detected_lang_name = googletrans.LANGUAGES.get(detected_lang_code.lower(), detected_lang_code)
            target_lang_name = googletrans.LANGUAGES.get(dest_lang.lower(), dest_lang)
            
            embed = Embed(title=f"{get_emoji(self.bot, 'idea')} Tradução", color=Color.blue())
            embed.add_field(name=f"Texto Original ({detected_lang_name.capitalize()})", value=f">>> {texto[:1000]} {'...' if len(texto)>1000 else ''}", inline=False)
            embed.add_field(name=f"Tradução ({target_lang_name.capitalize()})", value=f">>> {translated.text[:1000]} {'...' if len(translated.text)>1000 else ''}", inline=False)
            if translated.pronunciation and len(translated.pronunciation) < 1000:
                 embed.add_field(name="Pronúncia", value=translated.pronunciation, inline=False)
                 
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[ERRO Traduzir] Texto '{texto}', Dest '{dest_lang}': {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro ao tentar traduzir. A API pode estar indisponível ou o texto/idioma é inválido.", ephemeral=True)

    @nextcord.slash_command(name="wikipedia", description="Busca um resumo na Wikipedia.")
    async def wikipedia_summary(self, interaction: Interaction, termo: str = SlashOption(description="O termo para buscar na Wikipedia")):
        await interaction.response.defer()
        try:
            page = self.wiki.page(termo)
            if not page.exists():
                await interaction.followup.send(f"{get_emoji(self.bot, 'thinking')} Não encontrei uma página na Wikipedia para '{termo}'. Tente um termo diferente.", ephemeral=True)
                return

            summary = page.summary
            max_len = 1900 
            if len(summary) > max_len:
                summary = summary[:max_len].rsplit('.', 1)[0] + f"... [Leia mais]({page.fullurl})"
            else:
                summary += f"\n\n[Leia mais]({page.fullurl})"

            embed = Embed(title=f"📖 Wikipedia: {page.title}", description=summary, color=Color.light_grey())
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[ERRO Wikipedia] Termo '{termo}': {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro ao buscar na Wikipedia. A API pode estar indisponível ou o termo é inválido.", ephemeral=True)

    @nextcord.slash_command(name="clima", description="Mostra a previsão do tempo para uma cidade.")
    async def clima(self, interaction: Interaction, cidade: str = SlashOption(description="A cidade para ver o clima (ex: São Paulo,BR)")):
        if not WEATHER_API_KEY:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} A API de clima não está configurada. Peça ao administrador para definir a chave da API.", ephemeral=True)
            return
            
        await interaction.response.defer()
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": cidade,
            "appid": WEATHER_API_KEY,
            "units": "metric", 
            "lang": "pt_br"
        }
        try:
            async with self.session.get(base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    city_name = data['name']
                    country = data['sys']['country']
                    weather_desc = data['weather'][0]['description'].capitalize()
                    weather_icon = data['weather'][0]['icon']
                    temp = data['main']['temp']
                    feels_like = data['main']['feels_like']
                    temp_min = data['main']['temp_min']
                    temp_max = data['main']['temp_max']
                    humidity = data['main']['humidity']
                    wind_speed = data['wind']['speed'] 
                    sunrise = data['sys']['sunrise']
                    sunset = data['sys']['sunset']
                    timezone_offset = data['timezone']

                    tz = datetime.timezone(datetime.timedelta(seconds=timezone_offset))
                    sunrise_dt = datetime.datetime.fromtimestamp(sunrise, tz=tz)
                    sunset_dt = datetime.datetime.fromtimestamp(sunset, tz=tz)

                    embed = Embed(title=f"☀️ Clima em {city_name}, {country}", color=Color.blue())
                    embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{weather_icon}@2x.png")
                    embed.description = f"**{weather_desc}**"
                    embed.add_field(name="🌡️ Temperatura", value=f"{temp:.1f}°C", inline=True)
                    embed.add_field(name="🤔 Sensação Térmica", value=f"{feels_like:.1f}°C", inline=True)
                    embed.add_field(name="↕️ Min / Max", value=f"{temp_min:.1f}°C / {temp_max:.1f}°C", inline=True)
                    embed.add_field(name="💧 Umidade", value=f"{humidity}%", inline=True)
                    embed.add_field(name="💨 Vento", value=f"{wind_speed * 3.6:.1f} km/h", inline=True)
                    embed.add_field(name="🌅 Nascer do Sol", value=sunrise_dt.strftime("%H:%M"), inline=True)
                    embed.add_field(name="🌇 Pôr do Sol", value=sunset_dt.strftime("%H:%M"), inline=True)
                    embed.set_footer(text="Dados fornecidos por OpenWeatherMap")
                    embed.timestamp = datetime.datetime.now(tz=tz)
                    
                    await interaction.followup.send(embed=embed)
                    
                elif response.status == 404:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'thinking')} Cidade '{cidade}' não encontrada. Verifique o nome e tente novamente (ex: 'Rio de Janeiro,BR').", ephemeral=True)
                elif response.status == 401:
                    await interaction.followup.send(f"{get_emoji(self.bot, 'warn')} Chave da API de clima inválida. Contate o administrador.", ephemeral=True)
                else:
                    data_text = await response.text()
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao buscar clima ({response.status}): {data_text}", ephemeral=True)
                    
        except aiohttp.ClientError as e:
            print(f"[ERRO Clima] Erro de conexão: {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro de conexão ao buscar o clima.", ephemeral=True)
        except Exception as e:
            print(f"[ERRO Clima] Cidade '{cidade}': {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro inesperado ao buscar o clima.", ephemeral=True)

    @nextcord.slash_command(name="ascii", description="Converte texto em arte ASCII.")
    async def ascii_art(self, interaction: Interaction, texto: str = SlashOption(description="O texto para converter"), fonte: str = SlashOption(description="A fonte a ser usada (opcional)", required=False)):
        try:
            if fonte:
                available_fonts = pyfiglet.FigletFont.getFonts()
                if fonte not in available_fonts:
                    await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Fonte '{fonte}' não encontrada. Use `/listfonts` para ver as opções.", ephemeral=True)
                    return
                fig = pyfiglet.Figlet(font=fonte)
            else:
                fig = pyfiglet.Figlet()
                
            ascii_text = fig.renderText(texto)
            
            if len(ascii_text) > 1950:
                ascii_text = ascii_text[:1950] + "\n[Texto muito longo, cortado]"
                
            await interaction.response.send_message(f"```\n{ascii_text}\n```")
            
        except Exception as e:
            print(f"[ERRO ASCII] Texto '{texto}', Fonte '{fonte}': {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Erro ao gerar a arte ASCII.", ephemeral=True)

    @nextcord.slash_command(name="listfonts", description="Lista as fontes disponíveis para o comando /ascii.")
    async def list_fonts(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            fonts = sorted(pyfiglet.FigletFont.getFonts())
            font_list_str = ", ".join(fonts)
            
            max_len = 1900
            if len(font_list_str) <= max_len:
                await interaction.followup.send(f"**Fontes Disponíveis para `/ascii`:**\n```\n{font_list_str}\n```", ephemeral=True)
            else:
                await interaction.followup.send(f"**Fontes Disponíveis para `/ascii` (Parte 1):**\n```\n{font_list_str[:max_len]}\n```", ephemeral=True)
                start_index = max_len
                part_num = 2
                while start_index < len(font_list_str):
                    await interaction.followup.send(f"**Fontes Disponíveis (Parte {part_num}):**\n```\n{font_list_str[start_index:start_index+max_len]}\n```", ephemeral=True)
                    start_index += max_len
                    part_num += 1
                    await asyncio.sleep(0.5)
                    
        except Exception as e:
            print(f"[ERRO ListFonts]: {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao listar as fontes.", ephemeral=True)

    @nextcord.slash_command(name="cor", description="Mostra informações sobre uma cor (Hex ou RGB).")
    async def cor_info(self, interaction: Interaction, cor_valor: str = SlashOption(name="cor", description="Código Hex (ex: #FF0000) ou RGB (ex: 255,0,0)")):
        await interaction.response.defer()
        try:
            color = None
            color_hex = ""
            color_rgb = (0, 0, 0)

            if cor_valor.startswith('#'):
                color_hex_val = cor_valor.lstrip('#')
                if len(color_hex_val) == 3:
                    color_hex_val = "".join([c*2 for c in color_hex_val])
                if len(color_hex_val) == 6:
                    try:
                        color_rgb = tuple(int(color_hex_val[i:i+2], 16) for i in (0, 2, 4))
                        color = Color.from_rgb(*color_rgb)
                        color_hex = f"#{color_hex_val.upper()}"
                    except ValueError:
                        pass 
            
            if color is None:
                parts = [p.strip() for p in cor_valor.split(',')]
                if len(parts) == 3:
                    try:
                        r, g, b = map(int, parts)
                        if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                            color_rgb = (r, g, b)
                            color = Color.from_rgb(r, g, b)
                            color_hex = f"#{r:02X}{g:02X}{b:02X}"
                        else:
                             raise ValueError("Valores RGB fora do intervalo 0-255")
                    except ValueError:
                        pass

            if color is None:
                await interaction.followup.send(f"{get_emoji(self.bot, 'warn')} Formato de cor inválido. Use Hex (ex: `#FF5733` ou `#F53`) ou RGB (ex: `255, 87, 51`).", ephemeral=True)
                return

            img = Image.new('RGB', (100, 100), color=color_rgb)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            file = File(buffer, filename="color.png")

            embed = Embed(title=f"🎨 Informações da Cor", color=color)
            embed.set_thumbnail(url="attachment://color.png")
            embed.add_field(name="Hex", value=f"`{color_hex}`", inline=True)
            embed.add_field(name="RGB", value=f"`rgb({color_rgb[0]}, {color_rgb[1]}, {color_rgb[2]})`", inline=True)
            await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            print(f"[ERRO Cor] Valor '{cor_valor}': {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao processar a cor.", ephemeral=True)

def setup(bot: commands.Bot):
    """Adiciona a cog Utilitarios ao bot."""
    if not WEATHER_API_KEY:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [AVISO Utilitarios] Chave da API OpenWeatherMap não definida (OPENWEATHERMAP_API_KEY). Comando /clima desabilitado.")
    bot.add_cog(Utilitarios(bot))
