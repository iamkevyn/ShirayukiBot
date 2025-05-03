# /home/ubuntu/ShirayukiBot/cogs/Utilitarios.py
# Cog para comandos utilitários diversos.

import os
import random
import secrets
import math
import asyncio
import aiohttp
import nextcord
from nextcord import Interaction, Embed, SlashOption, Color, File, Member, User, TextChannel, Role
from nextcord.ext import commands, tasks, application_checks
from nextcord import ui
import datetime
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
SERVER_ID = 1367345048458498219 # Para registro rápido de comandos
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
        print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Diretório criado: {directory}")

def load_json_data(file_path, default_data):
    """Carrega dados de um arquivo JSON, criando-o com dados padrão se não existir."""
    ensure_dir_exists(file_path)
    if not os.path.exists(file_path):
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [AVISO] Arquivo {os.path.basename(file_path)} não encontrado. Criando com dados padrão.')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO] Falha ao carregar {os.path.basename(file_path)}, usando dados padrão.')
        return default_data

def save_json_data(file_path, data):
    """Salva dados em um arquivo JSON."""
    ensure_dir_exists(file_path)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO] Falha ao salvar {os.path.basename(file_path)}: {e}')
# Função para converter tempo (ex: 1d12h30m5s) para segundos
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

# Função para formatar segundos em uma string legível (ex: 1d 12h 30m 5s)
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
    if secs > 0 or not parts: # Mostra segundos se for a única unidade ou se houver outras
        parts.append(f"{secs}s")
        
    return " ".join(parts)

# --- Calculadora Segura --- 
# Operadores permitidos
allowed_operators = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod,
    ast.USub: op.neg, ast.UAdd: op.pos
}
# Funções matemáticas permitidas
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
        elif isinstance(node, ast.Num): # Deprecated in Python 3.8+, use ast.Constant
            return node.n
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

# --- Views e Modals --- 

class SugestaoModal(ui.Modal):
    def __init__(self, suggestions_channel_name: str, bot):
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
        
        # Tenta encontrar o canal de sugestões
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
            # Se não encontrar, avisa o usuário (não envia no canal atual para evitar spam)
            await interaction.followup.send(f"{get_emoji(self.bot, 'warn')} Canal #{self.suggestions_channel_name} não encontrado neste servidor. A sugestão foi registrada, mas não pude enviá-la para o canal específico.", ephemeral=True)
            # Opcional: Logar a sugestão em outro lugar ou para o dono do bot via DM
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [Sugestão] {interaction.user}: {self.titulo.value} - {self.descricao.value}")

class EnqueteView(ui.View):
    def __init__(self, interaction: Interaction, pergunta: str, opcoes_lista: list, bot):
        super().__init__(timeout=None) # Enquetes não expiram por padrão
        self.creator_id = interaction.user.id
        self.pergunta = pergunta
        self.opcoes = opcoes_lista
        self.bot = bot
        self.votos = {i: 0 for i in range(len(opcoes_lista))}
        self.votantes = set() # Guarda IDs de quem já votou
        self.message = None # Referência à mensagem da enquete
        self.update_buttons()

    def update_buttons(self):
        """Atualiza os botões com a contagem de votos."""
        self.clear_items()
        total_votos = sum(self.votos.values())
        for i, opcao in enumerate(self.opcoes):
            # Limita o tamanho do label
            label_text = opcao[:75] + ('...' if len(opcao) > 75 else '')
            label = f"{label_text} ({self.votos[i]})"
            button = ui.Button(label=label, custom_id=f"vote_{i}", style=ButtonStyle.primary)
            button.callback = self.create_callback(i)
            self.add_item(button)
        # Adiciona botão para finalizar (só para o criador)
        finish_button = ui.Button(label="Finalizar Enquete", custom_id="finish_poll", style=ButtonStyle.danger, row=4)
        finish_button.callback = self.finish_poll_callback
        self.add_item(finish_button)

    def create_callback(self, index: int):
        """Cria a função de callback para um botão de voto específico."""
        async def callback(interaction: Interaction):
            user_id = interaction.user.id
            if user_id in self.votantes:
                await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você já votou nesta enquete!", ephemeral=True)
                return

            self.votos[index] += 1
            self.votantes.add(user_id)
            self.update_buttons() # Atualiza contagem nos botões
            
            # Atualiza o embed com os resultados
            embed = self.create_poll_embed()
            try:
                await interaction.response.edit_message(embed=embed, view=self)
                # Confirmação efêmera para o votante
                await interaction.followup.send(f"{get_emoji(self.bot, 'happy_flower')} Seu voto para **{self.opcoes[index]}** foi registrado!", ephemeral=True)
            except nextcord.NotFound:
                self.stop() # Mensagem foi deletada
            except nextcord.HTTPException as e:
                print(f"[ERRO Enquete] Falha ao editar mensagem: {e}")
                await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao registrar seu voto. Tente novamente.", ephemeral=True)
                # Reverte o voto se a edição falhar?
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
            pass # Mensagem já não existe
        self.stop()

    def create_poll_embed(self, final: bool = False) -> Embed:
        """Cria o embed da enquete com os resultados atuais."""
        title = f"📊 Enquete{' Finalizada' if final else ''}"
        embed = Embed(title=title, description=self.pergunta, color=Color.blue())
        total_votos = sum(self.votos.values())
        
        resultados = []
        # Ordena pela quantidade de votos (maior primeiro)
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

# --- Cog Utilitarios --- 
class Utilitarios(commands.Cog):
    """Comandos utilitários diversos para o dia a dia."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession() # Sessão para requests HTTP
        self.translator = googletrans.Translator()
        self.wiki = wikipediaapi.Wikipedia(
            language='pt', 
            user_agent=WIKIPEDIA_USER_AGENT
        )
        self.reminders = load_json_data(REMINDERS_FILE, [])
        self.quotes = self.load_default_quotes()
        self.curiosidades = self.load_default_curiosidades()
        self.check_reminders.start() # Inicia a task de verificação de lembretes
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Cog Utilitarios carregada.")
        print(f"[Utilitarios] {len(self.reminders)} lembretes carregados.")

    def cog_unload(self):
        """Para a task e fecha a sessão HTTP quando o cog é descarregado."""
        self.check_reminders.cancel()
        asyncio.create_task(self.session.close()) # Fecha a sessão aiohttp

    def load_default_quotes(self):
        # Retorna lista de citações padrão
        # Fonte: Pensador, etc.
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
            ("A mente que se abre a uma nova ideia jamais voltará ao seu tamanho original.", "Albert Einstein"), 
            ("Tudo o que um sonho precisa para ser realizado é alguém que acredite que ele possa ser realizado.", "Roberto Shinyashiki"),
            ("Só se pode alcançar um grande êxito quando nos mantemos fiéis a nós mesmos.", "Friedrich Nietzsche"), 
            ("O sucesso nasce do querer, da determinação e persistência em se chegar a um objetivo.", "Desconhecido"),
            ("A única maneira de fazer um excelente trabalho é amar o que você faz.", "Steve Jobs"), 
            ("Você é mais forte do que pensa.", "Desconhecido"),
            ("Acredite no seu potencial.", "Desconhecido"), 
            ("A sua única limitação é aquela que você aceita.", "Desconhecido"),
            ("Transforme seus obstáculos em aprendizado.", "Desconhecido"), 
            ("Não pare até se orgulhar.", "Desconhecido"), 
            ("Desistir não é uma opção.", "Desconhecido"),
            ("O melhor ainda está por vir.", "Desconhecido"), 
            ("Você está exatamente onde precisa estar.", "Desconhecido"),
            ("Pequenos passos também te levam ao destino.", "Desconhecido"), 
            ("A ação é o antídoto do medo.", "Desconhecido"), 
            ("Você não precisa ser perfeito, só persistente.", "Desconhecido")
        ]

    def load_default_curiosidades(self):
        # Retorna lista de curiosidades padrão
        # Fontes: Mundo Estranho, Superinteressante, etc.
        return [
            "Polvos têm três corações e sangue azul.", "O corpo humano brilha no escuro (mas nossos olhos não percebem).",
            "O mel nunca estraga.", "Bananas são tecnicamente frutas vermelhas (bagas).", "Existem mais estrelas no universo do que grãos de areia na Terra.",
            "Os cavalos-marinhos são os únicos animais onde os machos engravidam.", "A Terra não é perfeitamente redonda, é um geoide ligeiramente achatado nos polos.",
            "Formigas não dormem como os humanos, elas têm ciclos de descanso.", "O cérebro humano é mais ativo durante o sono REM do que acordado.", "O DNA humano e o da banana compartilham cerca de 60% de genes.",
            "Os flamingos nascem cinzas e ficam rosas devido à sua dieta rica em carotenoides.", "Os tubarões existem há mais tempo que as árvores.", "A água-viva Turritopsis dohrnii é considerada biologicamente imortal.",
            "O corpo humano contém cerca de 0,2 miligramas de ouro.", "O nariz humano pode detectar mais de 1 trilhão de odores distintos.",
            "As abelhas podem reconhecer rostos humanos.", "Cada pessoa tem uma impressão de língua única, assim como as digitais.", "A Lua já teve uma atmosfera vulcânica temporária.",
            "O Sol representa aproximadamente 99,86% da massa total do nosso sistema solar.", "O kiwi é uma ave nativa da Nova Zelândia, não apenas uma fruta.",
            "Um dia em Vênus (243 dias terrestres) é mais longo que seu ano (225 dias terrestres).", "Os olhos da lula-colossal podem ser maiores que bolas de basquete.",
            "Existe uma ilha (Vulcan Point) dentro de um lago (Crater Lake) dentro de uma ilha (Taal Volcano Island) dentro de um lago (Taal Lake) dentro de uma ilha (Luzon), nas Filipinas.",
            "Os dragões-de-komodo fêmeas podem se reproduzir sem um macho através de partenogênese.", "A temperatura no núcleo da Terra é estimada em cerca de 6.000°C, similar à superfície do Sol."
        ]

    # --- Task de Lembretes --- 
    @tasks.loop(seconds=30) # Verifica a cada 30 segundos
    async def check_reminders(self):
        now = datetime.datetime.now(pytz.utc).timestamp()
        reminders_to_remove_indices = []
        reminders_updated = False

        # Cria uma cópia para iterar, permitindo modificação segura da original
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
                    # Tenta enviar no canal original, se existir e for acessível
                    if channel and isinstance(channel, TextChannel):
                        try:
                            await channel.send(content=user.mention, embed=embed)
                            sent = True
                        except (nextcord.Forbidden, nextcord.HTTPException) as e:
                            print(f"[ERRO Lembrete] Falha ao enviar no canal {channel.id}: {e}")
                    
                    # Se não enviou no canal, tenta DM
                    if not sent:
                        try:
                            dm_channel = await user.create_dm()
                            await dm_channel.send(content=f"Lembrete do servidor/canal `{reminder.get('guild_id', 'DM') or 'DM'}/{reminder.get('channel_id', 'DM')}`:", embed=embed)
                            sent = True
                        except (nextcord.Forbidden, nextcord.HTTPException) as e:
                            print(f"[ERRO Lembrete] Falha ao enviar DM para {user.id}: {e}")
                            
                    # Marca para remoção mesmo se falhar ao enviar (evita spam de erros)
                    reminders_to_remove_indices.append(reminder["created_at"]) # Usa timestamp de criação como ID único
                    reminders_updated = True
                    
                except Exception as e:
                    print(f"[{datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}] [ERRO Lembrete] Erro geral ao processar lembrete criado em {reminder.get('created_at', '???')}: {e}")
                    # Marca para remoção para evitar loop de erro
                    reminders_to_remove_indices.append(reminder["created_at"])
                    reminders_updated = True

        # Remove lembretes concluídos da lista original self.reminders
        if reminders_updated:
            self.reminders = [r for r in self.reminders if r["created_at"] not in reminders_to_remove_indices]
            save_json_data(REMINDERS_FILE, self.reminders)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready() # Espera o bot estar pronto

    # --- Comandos Slash --- 

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="lembrete", description="Define um lembrete para você.")
    @application_checks.cooldown(1, 5, bucket=nextcord.Buckets.user)
    async def lembrete(self, interaction: Interaction, 
                       tempo: str = SlashOption(description="Tempo até o lembrete (ex: 10s, 5m, 2h, 1d, 1d12h)"), 
                       mensagem: str = SlashOption(description="A mensagem do lembrete (máx 1000 chars)", max_length=1000)):
        """Agenda uma mensagem para ser enviada após um tempo especificado."""
        seconds = parse_time(tempo)
        if seconds is None:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Formato de tempo inválido. Use d, h, m, s (ex: '2h30m', '1d', '45s').", ephemeral=True)
            return

        if seconds > 30 * 86400: # Limite de 30 dias
             await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} O tempo máximo para lembretes é de 30 dias.", ephemeral=True)
             return

        future_timestamp = datetime.datetime.now(pytz.utc).timestamp() + seconds
        created_at = datetime.datetime.now(pytz.utc).timestamp()
        future_dt = datetime.datetime.fromtimestamp(future_timestamp, tz=pytz.utc)
        
        reminder_data = {
            "user_id": interaction.user.id,
            "channel_id": interaction.channel.id,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "timestamp": future_timestamp,
            "created_at": created_at, # Usado como ID
            "message": mensagem
        }
        
        self.reminders.append(reminder_data)
        save_json_data(REMINDERS_FILE, self.reminders)
        
        embed = Embed(title=f"{get_emoji(self.bot, 'alarm')} Lembrete Definido!", color=Color.green())
        embed.description = f"Ok, {interaction.user.mention}! Vou te lembrar sobre:" \
                          f"\n>>> {mensagem}"
        embed.add_field(name="Quando", value=f"<t:{int(future_timestamp)}:F> (<t:{int(future_timestamp)}:R>)")
        
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="sugerir", description="Envia uma sugestão para o desenvolvimento do bot.")
    async def sugerir(self, interaction: Interaction):
        """Abre um formulário para enviar sugestões sobre o bot."""
        modal = SugestaoModal(SUGGESTIONS_CHANNEL_NAME, self.bot)
        await interaction.response.send_modal(modal)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="enquete", description="Cria uma enquete simples com botões.")
    async def enquete(self, interaction: Interaction, 
                      pergunta: str = SlashOption(description="A pergunta da enquete", required=True, max_length=250),
                      opcao1: str = SlashOption(description="Opção de voto 1", required=True, max_length=80),
                      opcao2: str = SlashOption(description="Opção de voto 2", required=True, max_length=80),
                      opcao3: str = SlashOption(description="Opção de voto 3 (opcional)", required=False, max_length=80),
                      opcao4: str = SlashOption(description="Opção de voto 4 (opcional)", required=False, max_length=80),
                      opcao5: str = SlashOption(description="Opção de voto 5 (opcional)", required=False, max_length=80)
                      ):
        """Cria uma enquete interativa com até 5 opções."""
        opcoes = [opt for opt in [opcao1, opcao2, opcao3, opcao4, opcao5] if opt is not None]
        if len(opcoes) < 2:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você precisa fornecer pelo menos 2 opções!", ephemeral=True)
            return
            
        view = EnqueteView(interaction, pergunta, opcoes, self.bot)
        embed = view.create_poll_embed()
        embed.set_footer(text=f"Enquete criada por {interaction.user.display_name} | Clique para votar!")
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="citacao", description="Mostra uma citação inspiradora aleatória.")
    async def citacao(self, interaction: Interaction):
        """Exibe uma citação aleatória para inspirar o dia."""
        quote, author = random.choice(self.quotes)
        embed = Embed(title=f"{get_emoji(self.bot, 'idea')} Citação do Dia", description=f'> *"{quote}"*', color=Color.inspirational())
        embed.set_footer(text=f"- {author}")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="curiosidade", description="Conta um fato curioso aleatório.")
    async def curiosidade(self, interaction: Interaction):
        """Exibe uma curiosidade aleatória."""
        fact = random.choice(self.curiosidades)
        embed = Embed(title=f"{get_emoji(self.bot, 'thinking')} Você Sabia?", description=fact, color=Color.random())
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="senha", description="Gera uma senha segura aleatória.")
    async def senha(self, interaction: Interaction, 
                    tamanho: int = SlashOption(description="Tamanho da senha (8-64)", default=16, min_value=8, max_value=64),
                    usar_simbolos: bool = SlashOption(description="Incluir símbolos? (ex: !@#$)", default=True),
                    usar_numeros: bool = SlashOption(description="Incluir números?", default=True),
                    usar_maiusculas: bool = SlashOption(description="Incluir letras maiúsculas?", default=True),
                    usar_minusculas: bool = SlashOption(description="Incluir letras minúsculas?", default=True)
                    ):
        """Gera uma senha aleatória com opções de caracteres."""
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
            # Tenta enviar por DM primeiro
            await interaction.user.send(embed=embed)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Enviei a senha gerada na sua DM!", ephemeral=True)
        except nextcord.Forbidden:
            # Se DM estiver fechada, envia ephemeral
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"[ERRO Senha] Falha ao enviar senha: {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Erro ao gerar ou enviar a senha.", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="qrcode", description="Gera um QR Code para um texto ou URL.")
    async def qrcode_cmd(self, interaction: Interaction, texto: str = SlashOption(description="O texto ou URL para gerar o QR Code")):
        """Cria uma imagem de QR Code a partir do texto fornecido."""
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

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="tempo", description="Mostra a hora atual em diferentes fusos horários.")
    async def tempo(self, interaction: Interaction, fuso: str = SlashOption(description="Fuso horário (ex: America/Sao_Paulo, Europe/London, Asia/Tokyo)", default=DEFAULT_TIMEZONE)):
        """Exibe a data e hora atual no fuso horário especificado."""
        try:
            tz = pytz.timezone(fuso)
            now = datetime.datetime.now(tz)
            embed = Embed(title=f"⏰ Hora Atual em {fuso}", color=Color.blue())
            embed.description = f"**Data:** {now.strftime('%d/%m/%Y')}\n" \
                              f"**Hora:** {now.strftime('%H:%M:%S')}\n" \
                              f"**Fuso:** {now.strftime('%Z%z')}"
            # Adiciona timestamp do Discord para visualização local
            embed.add_field(name="Horário Local (Discord)", value=f"<t:{int(now.timestamp())}:F> (<t:{int(now.timestamp())}:R>)")
            await interaction.response.send_message(embed=embed)
        except pytz.UnknownTimeZoneError:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Fuso horário '{fuso}' desconhecido. Tente um formato como 'Continent/City'.", ephemeral=True)
        except Exception as e:
            print(f"[ERRO Tempo] Falha ao obter hora: {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Erro ao obter a hora para {fuso}.", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="avatar", description="Mostra o avatar de um usuário.")
    async def avatar(self, interaction: Interaction, usuario: Member | User = SlashOption(description="O usuário para ver o avatar (padrão: você)", required=False)):
        """Exibe o avatar de um membro ou usuário."""
        target_user = usuario or interaction.user
        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Avatar de {target_user.display_name}", color=target_user.color)
        embed.set_image(url=target_user.display_avatar.url)
        # Adiciona link para download
        view = ui.View()
        view.add_item(ui.Button(label="Download", url=target_user.display_avatar.url, style=ButtonStyle.link))
        await interaction.response.send_message(embed=embed, view=view)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="serverinfo", description="Mostra informações sobre o servidor.")
    async def serverinfo(self, interaction: Interaction):
        """Exibe informações detalhadas sobre o servidor atual."""
        if not interaction.guild:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Este comando só funciona em servidores.", ephemeral=True)
            return

        guild = interaction.guild
        embed = Embed(title=f"{get_emoji(self.bot, 'info')} Informações do Servidor: {guild.name}", color=guild.owner.color if guild.owner else Color.blue())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="👑 Dono", value=guild.owner.mention if guild.owner else "Desconhecido", inline=True)
        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        embed.add_field(name="📅 Criado em", value=f"<t:{int(guild.created_at.timestamp())}:F> (<t:{int(guild.created_at.timestamp())}:R>)", inline=False)
        
        total_members = guild.member_count or len(guild.members)
        online_members = sum(1 for m in guild.members if m.status != nextcord.Status.offline)
        humans = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        embed.add_field(name="👥 Membros", value=f"**Total:** {total_members}\n**Online:** {online_members}\n**Humanos:** {humans}\n**Bots:** {bots}", inline=True)

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles_count = len(guild.roles)
        embed.add_field(name="💬 Canais e Cargos", value=f"**Texto:** {text_channels}\n**Voz:** {voice_channels}\n**Categorias:** {categories}\n**Cargos:** {roles_count}", inline=True)

        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count
        embed.add_field(name="✨ Boosts", value=f"**Nível:** {boost_level}\n**Contagem:** {boost_count}", inline=True)

        features = ", ".join(guild.features) if guild.features else "Nenhuma"
        # Limita o tamanho do campo de features
        if len(features) > 1000:
            features = features[:1000] + "..."
        embed.add_field(name="🌟 Features", value=features, inline=False)

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="userinfo", description="Mostra informações sobre um usuário.")
    async def userinfo(self, interaction: Interaction, usuario: Member | User = SlashOption(description="O usuário para ver as informações (padrão: você)", required=False)):
        """Exibe informações detalhadas sobre um membro ou usuário."""
        target_user = usuario or interaction.user
        is_member = isinstance(target_user, Member)

        embed = Embed(title=f"{get_emoji(self.bot, 'peek')} Informações de {target_user.display_name}", color=target_user.color)
        embed.set_thumbnail(url=target_user.display_avatar.url)

        embed.add_field(name="📛 Nome Completo", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=target_user.id, inline=True)
        embed.add_field(name="🤖 É Bot?", value="Sim" if target_user.bot else "Não", inline=True)

        embed.add_field(name="📅 Conta Criada em", value=f"<t:{int(target_user.created_at.timestamp())}:F> (<t:{int(target_user.created_at.timestamp())}:R>)", inline=False)

        if is_member:
            embed.add_field(name="📥 Entrou no Servidor em", value=f"<t:{int(target_user.joined_at.timestamp())}:F> (<t:{int(target_user.joined_at.timestamp())}:R>)", inline=False)
            
            roles = [role.mention for role in reversed(target_user.roles) if role.name != "@everyone"]
            roles_str = ", ".join(roles) if roles else "Nenhum cargo"
            # Limita o tamanho do campo de cargos
            if len(roles_str) > 1000:
                roles_str = roles_str[:1000] + f"... (+{len(roles) - roles_str[:1000].count(',')})"
            embed.add_field(name=f"🎭 Cargos ({len(roles)})", value=roles_str, inline=False)
            
            embed.add_field(name="🔊 Status de Voz", value=str(target_user.voice.channel.mention) if target_user.voice and target_user.voice.channel else "Não conectado", inline=True)
            embed.add_field(name="🚦 Status", value=str(target_user.status).capitalize(), inline=True)
            if target_user.activity:
                 embed.add_field(name="🕹️ Atividade", value=target_user.activity.name, inline=True)

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="calcular", description="Calcula uma expressão matemática.")
    async def calcular(self, interaction: Interaction, expressao: str = SlashOption(description="A expressão matemática a ser calculada")):
        """Avalia uma expressão matemática de forma segura."""
        try:
            # Remove formatação de código se houver
            expr_clean = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', expressao).strip()
            if not expr_clean:
                raise ValueError("Expressão vazia.")
                
            result = safe_eval_math(expr_clean)
            
            # Formata resultado para evitar notação científica excessiva e limita casas decimais
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

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="traduzir", description="Traduz um texto para outro idioma.")
    async def traduzir(self, interaction: Interaction, 
                       texto: str = SlashOption(description="O texto a ser traduzido"), 
                       idioma_destino: str = SlashOption(name="para", description="Idioma de destino (ex: en, pt, es, ja)", default="pt"),
                       idioma_origem: str = SlashOption(name="de", description="Idioma de origem (opcional, detecta automaticamente)", required=False))
        :
        """Traduz texto usando Google Translate."""
        await interaction.response.defer()
        try:
            # Define origem e destino
            src_lang = idioma_origem if idioma_origem else 'auto'
            dest_lang = idioma_destino.lower()
            
            # Verifica se os idiomas são válidos (opcional, mas bom)
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

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="wikipedia", description="Busca um resumo na Wikipedia.")
    async def wikipedia_summary(self, interaction: Interaction, termo: str = SlashOption(description="O termo para buscar na Wikipedia")):
        """Busca e exibe um resumo de um artigo da Wikipedia."""
        await interaction.response.defer()
        try:
            page = self.wiki.page(termo)
            if not page.exists():
                await interaction.followup.send(f"{get_emoji(self.bot, 'thinking')} Não encontrei uma página na Wikipedia para '{termo}'. Tente um termo diferente.", ephemeral=True)
                return

            summary = page.summary
            # Limita o resumo e adiciona link
            max_len = 1900 # Deixa espaço para título e link
            if len(summary) > max_len:
                summary = summary[:max_len].rsplit('.', 1)[0] + f"... [Leia mais]({page.fullurl})"
            else:
                summary += f"\n\n[Leia mais]({page.fullurl})"

            embed = Embed(title=f"📖 Wikipedia: {page.title}", description=summary, color=Color.light_grey())
            # Tenta adicionar imagem principal se houver
            # images = page.images
            # if images:
            #     try:
            #         # Tenta pegar a primeira imagem (pode não ser a mais relevante)
            #         async with self.session.get(list(images)[0]) as resp:
            #             if resp.status == 200:
            #                 embed.set_thumbnail(url=list(images)[0])
            #     except Exception:
            #         pass # Ignora erro ao buscar imagem

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[ERRO Wikipedia] Termo '{termo}': {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro ao buscar na Wikipedia. A API pode estar indisponível ou o termo é inválido.", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="clima", description="Mostra a previsão do tempo para uma cidade.")
    async def clima(self, interaction: Interaction, cidade: str = SlashOption(description="A cidade para ver o clima (ex: São Paulo,BR)")):
        """Busca e exibe informações meteorológicas de uma cidade usando OpenWeatherMap."""
        if not WEATHER_API_KEY:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} A API de clima não está configurada. Peça ao administrador para definir a chave da API.", ephemeral=True)
            return
            
        await interaction.response.defer()
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": cidade,
            "appid": WEATHER_API_KEY,
            "units": "metric", # Para Celsius
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
                    wind_speed = data['wind']['speed'] # m/s
                    sunrise = data['sys']['sunrise']
                    sunset = data['sys']['sunset']
                    timezone_offset = data['timezone'] # Offset em segundos

                    # Converte timezone offset para objeto timezone
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
                    embed.add_field(name="💨 Vento", value=f"{wind_speed * 3.6:.1f} km/h", inline=True) # Converte m/s para km/h
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
                    data = await response.text()
                    await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao buscar clima ({response.status}): {data}", ephemeral=True)
                    
        except aiohttp.ClientError as e:
            print(f"[ERRO Clima] Erro de conexão: {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro de conexão ao buscar o clima.", ephemeral=True)
        except Exception as e:
            print(f"[ERRO Clima] Cidade '{cidade}': {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Ocorreu um erro inesperado ao buscar o clima.", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="ascii", description="Converte texto em arte ASCII.")
    async def ascii_art(self, interaction: Interaction, texto: str = SlashOption(description="O texto para converter"), fonte: str = SlashOption(description="A fonte a ser usada (opcional)", required=False)):
        """Gera arte ASCII a partir de um texto usando pyfiglet."""
        try:
            if fonte:
                # Verifica se a fonte existe
                available_fonts = pyfiglet.FigletFont.getFonts()
                if fonte not in available_fonts:
                    await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Fonte '{fonte}' não encontrada. Use `/listfonts` para ver as opções.", ephemeral=True)
                    return
                fig = pyfiglet.Figlet(font=fonte)
            else:
                fig = pyfiglet.Figlet() # Usa fonte padrão
                
            ascii_text = fig.renderText(texto)
            
            # Limita o tamanho para caber na mensagem
            if len(ascii_text) > 1950:
                ascii_text = ascii_text[:1950] + "\n[Texto muito longo, cortado]"
                
            await interaction.response.send_message(f"```\n{ascii_text}\n```")
            
        except Exception as e:
            print(f"[ERRO ASCII] Texto '{texto}', Fonte '{fonte}': {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Erro ao gerar a arte ASCII.", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="listfonts", description="Lista as fontes disponíveis para o comando /ascii.")
    async def list_fonts(self, interaction: Interaction):
        """Mostra uma lista das fontes disponíveis para pyfiglet."""
        await interaction.response.defer(ephemeral=True)
        try:
            fonts = sorted(pyfiglet.FigletFont.getFonts())
            font_list_str = ", ".join(fonts)
            
            # Envia em partes se for muito longo
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
                    await asyncio.sleep(0.5) # Pequena pausa para evitar rate limit
                    
        except Exception as e:
            print(f"[ERRO ListFonts]: {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao listar as fontes.", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="cor", description="Mostra informações sobre uma cor (Hex ou RGB).",)
    async def cor_info(self, interaction: Interaction, cor_valor: str = SlashOption(name="cor", description="Código Hex (ex: #FF0000) ou RGB (ex: 255,0,0)")):
        """Exibe uma amostra da cor e seus valores em Hex, RGB e HSL."""
        await interaction.response.defer()
        try:
            color = None
            color_hex = ""
            color_rgb = (0, 0, 0)

            # Tenta parsear como Hex
            if cor_valor.startswith('#'):
                color_hex = cor_valor.lstrip('#')
                if len(color_hex) == 3:
                    color_hex = "".join([c*2 for c in color_hex])
                if len(color_hex) == 6:
                    try:
                        color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                        color = Color.from_rgb(*color_rgb)
                        color_hex = f"#{color_hex.upper()}"
                    except ValueError:
                        pass # Não é Hex válido
            
            # Se não for Hex, tenta parsear como RGB
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
                        pass # Não é RGB válido

            if color is None:
                await interaction.followup.send(f"{get_emoji(self.bot, 'warn')} Formato de cor inválido. Use Hex (ex: `#FF5733` ou `#F53`) ou RGB (ex: `255, 87, 51`).", ephemeral=True)
                return

            # Gera imagem da cor
            img = Image.new('RGB', (100, 100), color=color_rgb)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            file = File(buffer, filename="color.png")

            embed = Embed(title=f"🎨 Informações da Cor", color=color)
            embed.set_thumbnail(url="attachment://color.png")
            embed.add_field(name="Hex", value=f"`{color_hex}`", inline=True)
            embed.add_field(name="RGB", value=f"`rgb({color_rgb[0]}, {color_rgb[1]}, {color_rgb[2]})`", inline=True)
            # embed.add_field(name="Valor Int", value=str(color.value), inline=True) # Opcional

            await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            print(f"[ERRO Cor] Valor '{cor_valor}': {e}")
            await interaction.followup.send(f"{get_emoji(self.bot, 'sad')} Erro ao processar a cor.", ephemeral=True)

    # --- Tratamento de Erro de Cooldown --- 
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        # Trata especificamente erros de cooldown DENTRO desta cog
        if isinstance(error, application_checks.ApplicationCommandOnCooldown) and interaction.application_command.cog_name == self.__cog_name__:
            retry_after = round(error.retry_after)
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'sad')} Calma aí! {get_emoji(self.bot, 'peek')} Você precisa esperar **{format_seconds(retry_after)}** para usar o comando `/{interaction.application_command.name}` novamente.", 
                ephemeral=True
            )
            try:
                error.handled = True # Marca como tratado para não ir para handlers globais (se o atributo existir)
            except AttributeError:
                pass # Ignora se o atributo não existir em versões mais antigas
        # Deixa outros erros passarem para handlers globais, se houver

# Função setup para carregar a cog
def setup(bot):
    """Adiciona a cog Utilitarios ao bot."""
    # Verifica dependências opcionais
    if not WEATHER_API_KEY:
        print(f"[{datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}] [AVISO Utilitarios] Chave da API OpenWeatherMap não definida (OPENWEATHERMAP_API_KEY). Comando /clima desabilitado.")
    bot.add_cog(Utilitarios(bot))
