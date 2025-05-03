# /home/ubuntu/ShirayukiBot/cogs/Jogos.py
# Cog para comandos de jogos diversos.

import nextcord
from nextcord import Interaction, Embed, ButtonStyle, Color, SlashOption, Member, SelectOption, User
from nextcord.ui import View, Button, Select, Modal, TextInput
from nextcord.ext import commands, application_checks
import random
import sqlite3
import asyncio
import os
import json
import time
from datetime import datetime, timedelta

# Importar helper de emojis
from utils.emojis import get_emoji

# --- Configurações --- 
SERVER_ID = 1367345048458498219 # Para registro rápido de comandos
DATA_DIR = "/home/ubuntu/ShirayukiBot/data"
QUIZ_DB_PATH = os.path.join(DATA_DIR, "quiz_ranking.db")
QUIZ_QUESTIONS_FILE = os.path.join(DATA_DIR, "quiz_questions.json")
HANGMAN_WORDS_FILE = os.path.join(DATA_DIR, "hangman_words.json")
TTT_DB_PATH = os.path.join(DATA_DIR, "ttt_stats.db") # Jogo da Velha Stats
CONNECT4_DB_PATH = os.path.join(DATA_DIR, "connect4_stats.db") # Connect 4 Stats

DEFAULT_QUIZ_QUESTIONS = [
    {
        "pergunta": "Quem é o protagonista de One Piece?",
        "opcoes": ["Zoro", "Luffy", "Naruto", "Ichigo"],
        "resposta": "Luffy",
        "imagem": "https://static.wikia.nocookie.net/onepiece/images/0/0f/Monkey_D._Luffy_Anime_Pre_Timeskip_Infobox.png/revision/latest?cb=20130429231457&path-prefix=pt"
    },
    {
        "pergunta": "Qual o nome do Bijuu selado dentro de Naruto Uzumaki?",
        "opcoes": ["Shukaku", "Matatabi", "Kurama", "Son Goku"],
        "resposta": "Kurama",
        "imagem": "https://static.wikia.nocookie.net/naruto/images/e/e6/Kurama_Infobox.png/revision/latest?cb=20170824233109&path-prefix=pt-br"
    },
    {
        "pergunta": "Em \'Attack on Titan\', qual o nome do protagonista principal?",
        "opcoes": ["Levi Ackerman", "Mikasa Ackerman", "Armin Arlert", "Eren Yeager"],
        "resposta": "Eren Yeager",
        "imagem": "https://static.wikia.nocookie.net/shingekinokyojin/images/a/a1/Eren_Yeager_Anime_Infobox.png/revision/latest?cb=20210315183633&path-prefix=pt-br"
    }
]
DEFAULT_HANGMAN_WORDS = ["python", "discord", "anime", "programacao", "bot", "shirayuki", "kawaii", "manga", "otaku"]

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

def connect_db(db_path):
    """Conecta ao banco de dados SQLite."""
    ensure_dir_exists(db_path)
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Retorna dicionários em vez de tuplas
        return conn
    except sqlite3.Error as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [ERRO SQLite] Erro ao conectar a {os.path.basename(db_path)}: {e}")
        return None

# --- Views e Componentes para Jogos ---

# --- Quiz --- 
class QuizView(View):
    def __init__(self, interaction: Interaction, quizzes: list, db_path: str, bot):
        super().__init__(timeout=60.0) # Timeout de 60 segundos por pergunta
        self.interaction = interaction
        self.quizzes = quizzes
        self.db_path = db_path
        self.bot = bot
        self.index = 0
        self.score = 0
        self.user_id = interaction.user.id
        self.username = interaction.user.name # Salva o nome atual
        self.message = None # Para editar a mensagem depois
        self.update_buttons()

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Permite apenas que o usuário original interaja
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Apenas {self.interaction.user.mention} pode responder a este quiz!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            timeout_embed = Embed(title="⏰ Tempo Esgotado!", description="Você demorou muito para responder.", color=Color.red())
            try:
                await self.message.edit(embed=timeout_embed, view=None)
            except nextcord.NotFound:
                pass # Mensagem já foi deletada ou inacessível
        self.stop()

    def update_buttons(self):
        """Limpa e atualiza os botões para a pergunta atual."""
        self.clear_items()
        current_quiz = self.quizzes[self.index]
        options = current_quiz['opcoes']
        random.shuffle(options) # Embaralha as opções
        for i, option in enumerate(options):
            # Limita tamanho do custom_id (máximo 100 caracteres)
            custom_id_payload = f"quiz_{i}_{option}"
            if len(custom_id_payload) > 95:
                custom_id_payload = custom_id_payload[:95]
            button = Button(label=option, style=ButtonStyle.primary, custom_id=custom_id_payload)
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: Interaction):
        """Processa a resposta do botão."""
        # Extrai a opção do custom_id (ignorando o prefixo e índice)
        try:
            selected_option = interaction.data['custom_id'].split('_', 2)[-1]
        except (IndexError, KeyError):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Erro ao processar sua resposta. Tente novamente.", ephemeral=True)
            return
            
        correct_answer = self.quizzes[self.index]['resposta']

        result_embed = Embed(color=Color.red())
        is_correct = (selected_option == correct_answer)

        if is_correct:
            self.score += 1
            result_embed.title = f"{get_emoji(self.bot, 'sparkle_happy')} Resposta Correta!"
            result_embed.color = Color.green()
        else:
            result_embed.title = f"{get_emoji(self.bot, 'sad')} Resposta Errada!"
            result_embed.description = f"A resposta correta era: **{correct_answer}**"

        # Desabilita botões e mostra o resultado brevemente
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True
                # Tenta comparar o label com a resposta correta/selecionada
                # Isso pode falhar se o label for muito longo e cortado no custom_id
                # Uma abordagem melhor seria armazenar o índice da opção correta
                if item.label == correct_answer:
                    item.style = ButtonStyle.success
                elif item.label == selected_option: # Compara com o label original
                    item.style = ButtonStyle.danger
        try:
            await interaction.response.edit_message(embed=result_embed, view=self)
        except nextcord.NotFound:
            self.stop()
            return
            
        await asyncio.sleep(2) # Pausa para mostrar o resultado

        # Avança para a próxima pergunta ou finaliza
        self.index += 1
        if self.index >= len(self.quizzes):
            # Fim do Quiz
            final_embed = Embed(
                title=f"{get_emoji(self.bot, 'celebrate')} Quiz Finalizado!",
                description=f"Sua pontuação: **{self.score}/{len(self.quizzes)}**",
                color=Color.gold()
            )
            self.save_score()
            try:
                await self.message.edit(embed=final_embed, view=None)
            except nextcord.NotFound:
                pass
            self.stop()
        else:
            # Próxima Pergunta
            next_quiz = self.quizzes[self.index]
            question_embed = Embed(
                title=f"🧠 Quiz - Pergunta {self.index + 1}/{len(self.quizzes)}",
                description=next_quiz['pergunta'],
                color=Color.blue()
            )
            if next_quiz.get('imagem'):
                question_embed.set_image(url=next_quiz['imagem'])
            self.update_buttons()
            try:
                await self.message.edit(embed=question_embed, view=self)
            except nextcord.NotFound:
                self.stop()

    def save_score(self):
        """Salva ou atualiza a pontuação do usuário no banco de dados SQLite."""
        conn = connect_db(self.db_path)
        if not conn:
            return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ranking (user_id INTEGER PRIMARY KEY, username TEXT, pontos INTEGER DEFAULT 0, last_played TEXT)")
                # Usa INSERT OR IGNORE e depois UPDATE para simplificar
                cur.execute("INSERT OR IGNORE INTO ranking (user_id, username, pontos) VALUES (?, ?, 0)", (self.user_id, self.username))
                # Atualiza a pontuação se a nova for maior E atualiza o nome e data
                cur.execute("UPDATE ranking SET pontos = MAX(pontos, ?), username = ?, last_played = ? WHERE user_id = ?", 
                            (self.score, self.username, datetime.utcnow().isoformat(), self.user_id))
        except sqlite3.Error as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [ERRO SQLite] Erro ao salvar pontuação do quiz: {e}")
        finally:
            conn.close()

# --- Forca --- 
class HangmanView(View):
    def __init__(self, interaction: Interaction, word: str, bot):
        super().__init__(timeout=180.0) # 3 minutos de timeout total
        self.interaction = interaction
        self.word = word.lower()
        self.guessed_letters = set()
        self.wrong_guesses = 0
        self.max_wrong_guesses = 6 # Número de estágios do boneco
        self.user_id = interaction.user.id
        self.bot = bot
        self.message = None
        self.update_view()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Apenas {self.interaction.user.mention} pode jogar esta partida de forca!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            timeout_embed = Embed(title="⏰ Tempo Esgotado!", description=f"Você demorou muito! A palavra era **{self.word}**.", color=Color.red())
            try:
                await self.message.edit(embed=timeout_embed, view=None)
            except nextcord.NotFound:
                pass
        self.stop()

    def get_display_word(self) -> str:
        """Retorna a palavra com letras adivinhadas e underscores."""
        return " ".join([letter if letter in self.guessed_letters else "\_" for letter in self.word])

    def get_hangman_stage(self) -> str:
        """Retorna a representação ASCII do boneco da forca."""
        stages = [
            # 0 erros
            """ 
               +---+
               |   |
                   |
                   |
                   |
                   |
            =========""",
            # 1 erro
            """ 
               +---+
               |   |
               O   |
                   |
                   |
                   |
            =========""",
            # 2 erros
            """ 
               +---+
               |   |
               O   |
               |   |
                   |
                   |
            =========""",
            # 3 erros
            """ 
               +---+
               |   |
               O   |
              /|   |
                   |
                   |
            =========""",
            # 4 erros
            """ 
               +---+
               |   |
               O   |
              /|\  |
                   |
                   |
            =========""",
            # 5 erros
            """ 
               +---+
               |   |
               O   |
              /|\  |
              /    |
                   |
            =========""",
            # 6 erros (fim)
            """ 
               +---+
               |   |
               O   |
              /|\  |
              / \  |
                   |
            ========="""
        ]
        return stages[min(self.wrong_guesses, len(stages) - 1)]

    def update_view(self):
        """Atualiza os botões do teclado."""
        self.clear_items()
        # Adiciona botões do alfabeto em linhas
        alphabet_rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
        for row in alphabet_rows:
            for letter in row:
                is_guessed = letter in self.guessed_letters
                style = ButtonStyle.secondary
                if is_guessed:
                    style = ButtonStyle.success if letter in self.word else ButtonStyle.danger
                
                button = Button(
                    label=letter.upper(),
                    style=style,
                    custom_id=f"hangman_{letter}",
                    disabled=is_guessed,
                    row=alphabet_rows.index(row) # Organiza em linhas
                )
                button.callback = self.letter_button_callback
                self.add_item(button)

    async def letter_button_callback(self, interaction: Interaction):
        """Processa o clique no botão de letra."""
        try:
            letter = interaction.data['custom_id'].split('_')[-1]
        except (IndexError, KeyError):
            await interaction.response.defer() # Ignora erro silenciosamente
            return
        
        if letter in self.guessed_letters:
            await interaction.response.defer() # Apenas ignora se já foi clicado
            return

        self.guessed_letters.add(letter)

        if letter not in self.word:
            self.wrong_guesses += 1

        # Atualiza a view (desabilita o botão clicado, muda cor)
        self.update_view()

        # Verifica condição de vitória ou derrota
        display_word_no_spaces = "".join([l if l in self.guessed_letters else "" for l in self.word])
        game_over = False
        result_embed = None

        if display_word_no_spaces == self.word:
            result_embed = Embed(title=f"{get_emoji(self.bot, 'celebrate')} Você Venceu!", description=f"Parabéns, você adivinhou a palavra **{self.word}**!", color=Color.green())
            game_over = True
        elif self.wrong_guesses >= self.max_wrong_guesses:
            result_embed = Embed(title=f"{get_emoji(self.bot, 'sad')} Você Perdeu!", description=f"Você foi enforcado! {get_emoji(self.bot, 'peek')} A palavra era **{self.word}**.", color=Color.red())
            game_over = True

        current_embed = self.create_game_embed()
        
        try:
            if game_over:
                # Adiciona o resultado ao embed final
                current_embed.title = result_embed.title
                current_embed.description = result_embed.description
                current_embed.color = result_embed.color
                for item in self.children:
                    if isinstance(item, Button): item.disabled = True
                await interaction.response.edit_message(embed=current_embed, view=None)
                self.stop()
            else:
                # Continua o jogo
                await interaction.response.edit_message(embed=current_embed, view=self)
        except nextcord.NotFound:
            self.stop()

    def create_game_embed(self) -> Embed:
        """Cria o embed do estado atual do jogo da forca."""
        embed = Embed(title=f"{get_emoji(self.bot, 'thinking')} Jogo da Forca", color=Color.dark_theme())
        hangman_art = self.get_hangman_stage()
        embed.description = f"Adivinhe a palavra:\n`{self.get_display_word()}`"
        embed.add_field(name="Desenho", value=f"```\n{hangman_art}\n```", inline=False)
        wrong_letters = sorted([l.upper() for l in self.guessed_letters if l not in self.word])
        embed.add_field(name=f"Letras Erradas ({len(wrong_letters)})", value=" ".join(wrong_letters) if wrong_letters else "Nenhuma", inline=False)
        embed.set_footer(text=f"Tentativas restantes: {self.max_wrong_guesses - self.wrong_guesses}")
        return embed

# --- Jogo da Velha (Tic Tac Toe) --- 
class TicTacToeButton(Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=ButtonStyle.secondary, label='\u200b', row=y) # Label invisível
        self.x = x
        self.y = y

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        view: TicTacToeView = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            await interaction.response.defer()
            return # Posição já jogada

        if view.current_player == view.X:
            if interaction.user != view.player1:
                await interaction.response.send_message(f"{get_emoji(view.bot, 'sad')} Não é sua vez, {interaction.user.mention}! Espere {view.player1.mention} jogar.", ephemeral=True)
                return
            self.style = ButtonStyle.danger
            self.label = 'X'
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            content = f"É a vez de {view.player2.mention} (O)"
        else:
            if interaction.user != view.player2:
                await interaction.response.send_message(f"{get_emoji(view.bot, 'sad')} Não é sua vez, {interaction.user.mention}! Espere {view.player2.mention} jogar.", ephemeral=True)
                return
            self.style = ButtonStyle.success
            self.label = 'O'
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            content = f"É a vez de {view.player1.mention} (X)"

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = f"{get_emoji(view.bot, 'celebrate')} {view.player1.mention} venceu!"
                view.update_stats(view.player1.id, view.player2.id)
            elif winner == view.O:
                content = f"{get_emoji(view.bot, 'celebrate')} {view.player2.mention} venceu!"
                view.update_stats(view.player2.id, view.player1.id)
            else:
                content = f"🤝 Empate!"
                view.update_stats(view.player1.id, view.player2.id, draw=True)

            for child in view.children:
                child.disabled = True
            view.stop()

        await interaction.response.edit_message(content=content, view=view)

class TicTacToeView(View):
    X = -1
    O = 1
    Tie = 2

    def __init__(self, player1: Member | User, player2: Member | User, bot):
        super().__init__(timeout=120.0) # 2 minutos para jogar
        self.player1 = player1
        self.player2 = player2
        self.bot = bot
        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        self.message = None

        # Adiciona os botões
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Permite apenas os dois jogadores interagirem
        if interaction.user.id not in (self.player1.id, self.player2.id):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Este jogo é entre {self.player1.mention} e {self.player2.mention}!", ephemeral=True)
            return False
        return True
        
    async def on_timeout(self):
        if self.message:
            content = f"⏰ Tempo esgotado! O jogo entre {self.player1.mention} e {self.player2.mention} foi cancelado."
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(content=content, view=self)
            except nextcord.NotFound:
                pass
        self.stop()

    def check_board_winner(self):
        # Verifica linhas
        for row in self.board:
            if all(s == self.X for s in row):
                return self.X
            if all(s == self.O for s in row):
                return self.O

        # Verifica colunas
        for col in range(3):
            if all(self.board[row][col] == self.X for row in range(3)):
                return self.X
            if all(self.board[row][col] == self.O for row in range(3)):
                return self.O

        # Verifica diagonais
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0:
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0:
            return self.board[0][2]

        # Verifica empate (se não houver mais 0)
        if all(all(s != 0 for s in row) for row in self.board):
            return self.Tie

        return None # Jogo continua
        
    def update_stats(self, winner_id: int, loser_id: int, draw: bool = False):
        """Atualiza as estatísticas do Jogo da Velha."""
        conn = connect_db(TTT_DB_PATH)
        if not conn:
            return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ttt_stats (user_id INTEGER PRIMARY KEY, username TEXT, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0)")
                
                ids_to_update = [winner_id, loser_id]
                for user_id in ids_to_update:
                    # Garante que o usuário existe
                    user = self.player1 if user_id == self.player1.id else self.player2
                    cur.execute("INSERT OR IGNORE INTO ttt_stats (user_id, username) VALUES (?, ?)", (user_id, user.name))
                    
                    if draw:
                        cur.execute("UPDATE ttt_stats SET draws = draws + 1, username = ? WHERE user_id = ?", (user.name, user_id))
                    elif user_id == winner_id:
                        cur.execute("UPDATE ttt_stats SET wins = wins + 1, username = ? WHERE user_id = ?", (user.name, user_id))
                    else: # loser
                        cur.execute("UPDATE ttt_stats SET losses = losses + 1, username = ? WHERE user_id = ?", (user.name, user_id))
        except sqlite3.Error as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [ERRO SQLite] Erro ao salvar estatísticas TTT: {e}")
        finally:
            conn.close()

# --- Connect 4 --- 
# (Implementação similar ao Jogo da Velha, mas com tabuleiro maior e lógica diferente)
# TODO: Implementar Connect 4 View e lógica

# --- Cog Principal --- 
class Jogos(commands.Cog):
    """Comandos para jogar diversos jogos com o bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.quiz_questions = load_json_data(QUIZ_QUESTIONS_FILE, DEFAULT_QUIZ_QUESTIONS)        self.hangman_words = load_json_data(HANGMAN_WORDS_FILE, DEFAULT_HANGMAN_WORDS)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Cog Jogos carregada.")
        print(f"[Jogos] {len(self.quiz_questions)} perguntas de quiz carregadas.")
        print(f"[Jogos] {len(self.hangman_words)} palavras da forca carregadas.")
    # --- Comandos Slash --- 

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="quiz", description="Inicia um quiz de anime!")
    @application_checks.cooldown(1, 15, bucket=nextcord.Buckets.user) # Cooldown de 15s por usuário
    async def quiz(self, interaction: Interaction, quantidade: int = SlashOption(name="perguntas", description="Número de perguntas (3-15)", min_value=3, max_value=15, default=5)):
        """Inicia um quiz interativo com perguntas sobre animes."""
        if not self.quiz_questions:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Nenhuma pergunta de quiz carregada!", ephemeral=True)
            return
            
        max_questions = len(self.quiz_questions)
        if quantidade > max_questions:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} Só tenho {max_questions} perguntas! Iniciando com {max_questions}.", ephemeral=True)
            quantidade = max_questions
            
        selected_quizzes = random.sample(self.quiz_questions, quantidade)
        
        initial_embed = Embed(
            title=f"🧠 Quiz - Pergunta 1/{quantidade}",
            description=selected_quizzes[0]['pergunta'],
            color=Color.blue()
        )
        if selected_quizzes[0].get('imagem'):
            initial_embed.set_image(url=selected_quizzes[0]['imagem'])
            
        view = QuizView(interaction, selected_quizzes, QUIZ_DB_PATH, self.bot)
        await interaction.response.send_message(embed=initial_embed, view=view)
        view.message = await interaction.original_message() # Guarda a mensagem para edição futura

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="quiz_ranking", description="Mostra o ranking do quiz.")
    async def quiz_ranking(self, interaction: Interaction, top: int = SlashOption(name="top", description="Quantos jogadores mostrar no ranking", default=10, min_value=1, max_value=25)):
        """Exibe os melhores jogadores do quiz."""
        conn = connect_db(QUIZ_DB_PATH)
        embed = Embed(title=f"🏆 Ranking do Quiz (Top {top})", color=Color.gold())
        if not conn:
            embed.description = f"{get_emoji(self.bot, 'sad')} Erro ao conectar ao banco de dados do ranking."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ranking (user_id INTEGER PRIMARY KEY, username TEXT, pontos INTEGER DEFAULT 0, last_played TEXT)")
                cur.execute("SELECT user_id, username, pontos FROM ranking WHERE pontos > 0 ORDER BY pontos DESC LIMIT ?", (top,))
                ranking_data = cur.fetchall()
                
                if not ranking_data:
                    embed.description = f"{get_emoji(self.bot, 'thinking')} Ninguém pontuou no quiz ainda! Use `/quiz` para começar."
                else:
                    rank_list = []
                    for i, row in enumerate(ranking_data):
                        user_id, username, pontos = row['user_id'], row['username'], row['pontos']
                        rank_emoji = ""
                        if i == 0: rank_emoji = "🥇 "
                        elif i == 1: rank_emoji = "🥈 "
                        elif i == 2: rank_emoji = "🥉 "
                        else: rank_emoji = f"`#{i+1}` "
                        # Tenta mencionar, mas usa o nome salvo se falhar
                        member = interaction.guild.get_member(user_id) if interaction.guild else None
                        user_display = member.mention if member else username # Nome salvo no DB
                        rank_list.append(f"{rank_emoji}{user_display}: **{pontos} pontos**")
                    embed.description = "\n".join(rank_list)
        except sqlite3.Error as e:
            print(f"[{datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}] [ERRO SQLite] Erro ao ler ranking do quiz: {e}")
            embed.description = f"{get_emoji(self.bot, 'sad')} Erro ao carregar o ranking."
        finally:
            conn.close()
            
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="forca", description="Jogue forca com o bot!")
    @application_checks.cooldown(1, 30, bucket=nextcord.Buckets.channel) # Cooldown de 30s por canal
    async def forca(self, interaction: Interaction):
        """Inicia um jogo interativo da forca."""
        if not self.hangman_words:
             await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não há palavras carregadas para o jogo da forca!", ephemeral=True)
             return
             
        word_to_guess = random.choice(self.hangman_words)
        # Garante que a palavra não seja muito longa (pode quebrar a UI)
        if len(word_to_guess) > 15:
            word_to_guess = random.choice([w for w in self.hangman_words if len(w) <= 15] or ["erro"])
            
        view = HangmanView(interaction, word_to_guess, self.bot)
        initial_embed = view.create_game_embed()
        await interaction.response.send_message(embed=initial_embed, view=view)
        view.message = await interaction.original_message()

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="ppt", description="Jogue Pedra, Papel ou Tesoura!")
    async def ppt(self, interaction: Interaction, escolha: str = SlashOption(name="sua_jogada", description="Escolha pedra, papel ou tesoura", choices={"Pedra 🗿": "pedra", "Papel 📄": "papel", "Tesoura ✂️": "tesoura"})):
        """Joga Pedra, Papel ou Tesoura contra o bot."""
        opcoes = {"pedra": "🗿", "papel": "📄", "tesoura": "✂️"}
        escolha_bot_key = random.choice(list(opcoes.keys()))
        escolha_bot_emoji = opcoes[escolha_bot_key]
        escolha_user_emoji = opcoes[escolha]

        embed = Embed(title=f"Pedra, Papel, Tesoura! {get_emoji(self.bot, 'peek')}", color=Color.random())
        embed.add_field(name=f"{interaction.user.display_name} jogou", value=escolha_user_emoji, inline=True)
        embed.add_field(name=f"{self.bot.user.name} jogou", value=escolha_bot_emoji, inline=True)

        if escolha == escolha_bot_key:
            resultado = f"🤝 Empate! Jogamos a mesma coisa!"
            embed.color = Color.light_grey()
        elif (escolha == "pedra" and escolha_bot_key == "tesoura") or \
             (escolha == "papel" and escolha_bot_key == "pedra") or \
             (escolha == "tesoura" and escolha_bot_key == "papel"):
            resultado = f"{get_emoji(self.bot, 'celebrate')} Você ganhou! Boa!"
            embed.color = Color.green()
        else:
            resultado = f"{get_emoji(self.bot, 'sad')} Você perdeu! Que pena!"
            embed.color = Color.red()
            
        embed.description = resultado
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="par_ou_impar", description="Jogue Par ou Ímpar!")
    async def par_ou_impar(self, interaction: Interaction, escolha: str = SlashOption(description="Você quer par ou ímpar?", choices={"Par": "par", "Ímpar": "impar"}), numero: int = SlashOption(description="Seu número (0-10)", min_value=0, max_value=10)):
        """Joga Par ou Ímpar contra o bot."""
        numero_bot = random.randint(0, 10)
        total = numero + numero_bot
        resultado_real = "par" if total % 2 == 0 else "impar"

        embed = Embed(title=f"Par ou Ímpar? {get_emoji(self.bot, 'thinking')}", color=Color.random())
        embed.add_field(name="Sua Escolha", value=escolha.capitalize(), inline=True)
        embed.add_field(name="Seu Número", value=str(numero), inline=True)
        embed.add_field(name="Número do Bot", value=str(numero_bot), inline=True)
        embed.add_field(name="Total", value=f"**{total}**", inline=True)
        embed.add_field(name="Resultado", value=resultado_real.capitalize(), inline=True)

        if resultado_real == escolha.lower():
            embed.description = f"{get_emoji(self.bot, 'sparkle_happy')} Você venceu! O total foi {resultado_real}!"
            embed.color = Color.green()
        else:
            embed.description = f"{get_emoji(self.bot, 'sad')} Você perdeu! O total foi {resultado_real}!"
            embed.color = Color.red()
            
        await interaction.response.send_message(embed=embed)

    # --- Jogo da Velha --- 
    @nextcord.slash_command(guild_ids=[SERVER_ID], name="jogo_da_velha", description="Desafie alguém para uma partida de Jogo da Velha!")
    @application_checks.cooldown(1, 60, bucket=nextcord.Buckets.channel) # Cooldown de 60s por canal
    async def jogo_da_velha(self, interaction: Interaction, oponente: Member = SlashOption(description="O usuário que você quer desafiar")):
        """Inicia uma partida de Jogo da Velha contra outro membro."""
        if oponente.bot:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não pode jogar contra um bot!", ephemeral=True)
            return
        if oponente.id == interaction.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} Você não pode jogar contra si mesmo!", ephemeral=True)
            return

        view = TicTacToeView(interaction.user, oponente, self.bot)
        await interaction.response.send_message(f"⭕ {oponente.mention}, você foi desafiado por {interaction.user.mention} para Jogo da Velha!\n❌ {interaction.user.mention} começa!", view=view)
        view.message = await interaction.original_message()
        
    @nextcord.slash_command(guild_ids=[SERVER_ID], name="jogo_da_velha_stats", description="Mostra suas estatísticas no Jogo da Velha.")
    async def jogo_da_velha_stats(self, interaction: Interaction, usuario: Member | User = SlashOption(name="usuario", description="Ver estatísticas de outro usuário (opcional)", required=False)):
        """Exibe as estatísticas de vitórias, derrotas e empates no Jogo da Velha."""
        target_user = usuario or interaction.user
        conn = connect_db(TTT_DB_PATH)
        embed = Embed(title=f"📊 Estatísticas Jogo da Velha - {target_user.display_name}", color=Color.blue())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        if not conn:
            embed.description = f"{get_emoji(self.bot, 'sad')} Erro ao conectar ao banco de dados."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ttt_stats (user_id INTEGER PRIMARY KEY, username TEXT, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0)")
                cur.execute("SELECT wins, losses, draws FROM ttt_stats WHERE user_id = ?", (target_user.id,))
                data = cur.fetchone()
                
                if not data:
                    embed.description = f"{get_emoji(self.bot, 'thinking')} {target_user.mention} ainda não jogou Jogo da Velha."
                else:
                    wins, losses, draws = data['wins'], data['losses'], data['draws']
                    total_games = wins + losses + draws
                    win_rate = (wins / total_games * 100) if total_games > 0 else 0
                    embed.add_field(name="🏆 Vitórias", value=str(wins), inline=True)
                    embed.add_field(name="💔 Derrotas", value=str(losses), inline=True)
                    embed.add_field(name="🤝 Empates", value=str(draws), inline=True)
                    embed.add_field(name="🎮 Total Jogos", value=str(total_games), inline=True)
                    embed.add_field(name="📈 Taxa Vit. (%)", value=f"{win_rate:.1f}%", inline=True)
        except sqlite3.Error as e:
            print(f"[{datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}] [ERRO SQLite] Erro ao ler estatísticas TTT: {e}")
            embed.description = f"{get_emoji(self.bot, 'sad')} Erro ao carregar as estatísticas."
        finally:
            conn.close()
            
        await interaction.response.send_message(embed=embed)

    # --- Outros Jogos Simples --- 

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="adivinhe_numero", description="Tente adivinhar o número que estou pensando (1-100)!",)
    @application_checks.cooldown(1, 10, bucket=nextcord.Buckets.user)
    async def adivinhe_numero(self, interaction: Interaction):
        """Inicia um mini-game interativo de adivinhar o número."""
        numero_secreto = random.randint(1, 100)
        tentativas = 0
        max_tentativas = 7 # Ajustável

        embed = Embed(title=f"{get_emoji(self.bot, 'thinking')} Adivinhe o Número!", 
                      description=f"Estou pensando em um número entre 1 e 100. Você tem {max_tentativas} tentativas!\nUse o botão abaixo para chutar.",
                      color=Color.purple())

        view = GuessNumberView(interaction.user, numero_secreto, max_tentativas, self.bot)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="cara_coroa", description="Jogue cara ou coroa!")
    async def cara_coroa(self, interaction: Interaction):
        """Lança uma moeda virtual."""
        resultado = random.choice([("Cara", "👑"), ("Coroa", "🪙")])
        embed = Embed(title=f"🪙 Cara ou Coroa? {get_emoji(self.bot, 'peek')}", 
                      description=f"A moeda girou, girou e caiu em: **{resultado[0]} {resultado[1]}**", 
                      color=Color.random())
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="roleta_russa", description="Tente a sorte na roleta russa (1/6 chance)! Cuidado!",)
    @application_checks.cooldown(1, 10, bucket=nextcord.Buckets.user)
    async def roleta_russa(self, interaction: Interaction):
        """Simula uma roleta russa com 1 bala em 6 câmaras."""
        await interaction.response.defer()
        msg = await interaction.followup.send(f"🔫 {interaction.user.mention} pega o revólver... {get_emoji(self.bot, 'thinking')}")
        await asyncio.sleep(1.5)
        await msg.edit(content=f"🔫 {interaction.user.mention} gira o tambor... {get_emoji(self.bot, 'peek')}")
        await asyncio.sleep(1.5)
        await msg.edit(content=f"🔫 {interaction.user.mention} aponta para a cabeça e... {get_emoji(self.bot, 'determined')}")
        await asyncio.sleep(2)
        
        if random.randint(1, 6) == 1:
            resultado = f"💥 BANG! {get_emoji(self.bot, 'sad')} Você perdeu! Mais sorte (ou azar?) da próxima vez."
            color = Color.red()
        else:
            resultado = f"*click* 🎉 Ufa! {get_emoji(self.bot, 'sparkle_happy')} Você sobreviveu! Por enquanto..."
            color = Color.green()
            
        embed = Embed(title="🔫 Roleta Russa", description=resultado, color=color)
        await msg.edit(content=None, embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="numero_maior", description="Veja quem escolhe o número maior (1-100)!")
    async def numero_maior(self, interaction: Interaction, numero: int = SlashOption(description="Seu número (1-100)", min_value=1, max_value=100)):
        """Compara seu número com um número aleatório do bot."""
        bot_num = random.randint(1, 100)
        embed = Embed(title=f"🎲 Número Maior {get_emoji(self.bot, 'determined')}", color=Color.random())
        embed.add_field(name="Sua Escolha", value=str(numero), inline=True)
        embed.add_field(name="Escolha do Bot", value=str(bot_num), inline=True)

        if numero > bot_num:
            resultado = f"{get_emoji(self.bot, 'celebrate')} Você venceu! Seu número foi maior!"
            embed.color = Color.green()
        elif numero < bot_num:
            resultado = f"{get_emoji(self.bot, 'sad')} Você perdeu! Meu número foi maior!"
            embed.color = Color.red()
        else:
            resultado = f"🤝 Empate! Escolhemos o mesmo número!"
            embed.color = Color.light_grey()
            
        embed.description = resultado
        await interaction.response.send_message(embed=embed)
        
    @nextcord.slash_command(guild_ids=[SERVER_ID], name="dado", description="Rola um ou mais dados com um número específico de lados.")
    async def dado(self, interaction: Interaction, 
                   quantidade: int = SlashOption(name="quantidade", description="Número de dados para rolar", default=1, min_value=1, max_value=25),
                   lados: int = SlashOption(name="lados", description="Número de lados de cada dado", default=6, min_value=2, max_value=100)):
        """Rola dados virtuais."""
        if quantidade == 1:
            resultado = random.randint(1, lados)
            embed = Embed(title=f"🎲 Rolando 1d{lados}", description=f"O resultado foi: **{resultado}**", color=Color.random())
        else:
            resultados = [random.randint(1, lados) for _ in range(quantidade)]
            total = sum(resultados)
            embed = Embed(title=f"🎲 Rolando {quantidade}d{lados}", color=Color.random())
            embed.add_field(name="Resultados Individuais", value=", ".join(map(str, resultados)), inline=False)
            embed.add_field(name="Total", value=f"**{total}**", inline=False)
            
        await interaction.response.send_message(embed=embed)

    # --- Tratamento de Erro de Cooldown --- 
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        # Trata especificamente erros de cooldown DENTRO desta cog
        if isinstance(error, application_checks.ApplicationCommandOnCooldown) and interaction.application_command.cog_name == self.__cog_name__:
            retry_after = round(error.retry_after)
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'sad')} Calma aí! {get_emoji(self.bot, 'peek')} Você precisa esperar **{retry_after} segundos** para usar o comando `/{interaction.application_command.name}` novamente.", 
                ephemeral=True
            )
            error.handled = True # Marca como tratado para não ir para handlers globais
        # Deixa outros erros passarem para handlers globais, se houver

# --- Views e Modals Auxiliares --- 

class GuessNumberView(View):
    def __init__(self, user: Member | User, secret_number: int, max_guesses: int, bot):
        super().__init__(timeout=120.0) # 2 minutos para adivinhar
        self.user = user
        self.secret_number = secret_number
        self.max_guesses = max_guesses
        self.guesses_made = 0
        self.bot = bot
        self.message = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Apenas {self.user.mention} pode chutar neste jogo!", ephemeral=True)
            return False
        return True
        
    async def on_timeout(self):
        if self.message:
            embed = Embed(title="⏰ Tempo Esgotado!", 
                          description=f"Você demorou demais! O número era **{self.secret_number}**.", 
                          color=Color.red())
            try:
                await self.message.edit(embed=embed, view=None)
            except nextcord.NotFound:
                pass
        self.stop()

    @nextcord.ui.button(label="Chutar Número", style=ButtonStyle.primary)
    async def guess_button(self, button: Button, interaction: Interaction):
        modal = GuessNumberModal(self.secret_number, self.max_guesses - self.guesses_made, self.bot)
        await interaction.response.send_modal(modal)
        
        # Espera o modal ser enviado
        await modal.wait()
        
        if modal.guess is None: # Modal fechado ou timeout
            return
            
        self.guesses_made += 1
        guess = modal.guess
        hint = modal.hint
        is_correct = modal.is_correct
        
        embed = Embed(title=f"{get_emoji(self.bot, 'thinking')} Adivinhe o Número!", color=Color.purple())
        embed.description = f"Seu chute: **{guess}**\n{hint}"
        embed.set_footer(text=f"Tentativas restantes: {self.max_guesses - self.guesses_made}")
        
        game_over = False
        if is_correct:
            embed.title = f"{get_emoji(self.bot, 'celebrate')} Você Acertou!"
            embed.description = f"Parabéns! Você adivinhou o número **{self.secret_number}** em {self.guesses_made} tentativas!"
            embed.color = Color.green()
            game_over = True
        elif self.guesses_made >= self.max_guesses:
            embed.title = f"{get_emoji(self.bot, 'sad')} Você Perdeu!"
            embed.description = f"Acabaram suas tentativas! O número era **{self.secret_number}**."
            embed.color = Color.red()
            game_over = True
            
        if game_over:
            self.stop()
            button.disabled = True # Desabilita o botão no final
            await self.message.edit(embed=embed, view=self if not game_over else None)
        else:
            await self.message.edit(embed=embed, view=self)

class GuessNumberModal(Modal):
    def __init__(self, secret_number: int, guesses_left: int, bot):
        super().__init__(title=f"Chute um número (Restam {guesses_left})")
        self.secret_number = secret_number
        self.bot = bot
        self.guess = None
        self.hint = ""
        self.is_correct = False

        self.number_input = TextInput(
            label="Seu chute (1-100)",
            placeholder="Digite um número",
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.number_input)

    async def callback(self, interaction: Interaction):
        try:
            guess_num = int(self.number_input.value)
            if not 1 <= guess_num <= 100:
                await interaction.response.send_message("Por favor, digite um número entre 1 e 100.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Entrada inválida. Por favor, digite apenas números.", ephemeral=True)
            return
            
        self.guess = guess_num
        if guess_num == self.secret_number:
            self.hint = f"{get_emoji(self.bot, 'sparkle_happy')} Correto!"
            self.is_correct = True
        elif guess_num < self.secret_number:
            self.hint = f"{get_emoji(self.bot, 'peek')} Muito baixo! Tente um número maior."
        else:
            self.hint = f"{get_emoji(self.bot, 'peek')} Muito alto! Tente um número menor."
            
        await interaction.response.defer() # Apenas fecha o modal, a view principal edita a mensagem
        self.stop()

# Função setup para carregar a cog
def setup(bot):
    """Adiciona a cog Jogos ao bot."""
    bot.add_cog(Jogos(bot))
