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
import time # Mantido para usos potenciais, embora não explicitamente usado em lógica crítica
from datetime import datetime, timedelta, timezone
import traceback # Para logging de erros

# Importar helper de emojis (usando placeholder como em outras cogs)
def get_emoji(bot, name):
    emoji_map = {
        "quiz": "🧠", "hangman": "🪢", "ttt": "🎲", "connect4": "🔴",
        "ranking": "🏆", "question": "❓", "correct": "✅", "wrong": "❌",
        "celebrate": "🎉", "thinking": "🤔", "sad": "😥", "error": "🔥",
        "stop": "🛑", "clock": "⏰", "joystick": "🕹️", "win": "👑", "draw": "🤝",
        "sparkle_happy": "✨"
    }
    return emoji_map.get(name, "▫️")

# --- Configurações --- 
DATA_DIR = "/home/ubuntu/ShirayukiBot/data"
QUIZ_DB_PATH = os.path.join(DATA_DIR, "quiz_ranking.db")
QUIZ_QUESTIONS_FILE = os.path.join(DATA_DIR, "quiz_questions.json")
HANGMAN_WORDS_FILE = os.path.join(DATA_DIR, "hangman_words.json")
TTT_DB_PATH = os.path.join(DATA_DIR, "ttt_stats.db")
CONNECT4_DB_PATH = os.path.join(DATA_DIR, "connect4_stats.db")

DEFAULT_QUIZ_QUESTIONS = [
    {
        "pergunta": "Quem é o protagonista de One Piece?",
        "opcoes": ["Zoro", "Luffy", "Naruto", "Ichigo"],
        "resposta": "Luffy",
        "imagem": "https://i.imgur.com/KqVqY9E.png" # Exemplo de URL de imagem funcional
    },
    {
        "pergunta": "Qual o nome do Bijuu selado dentro de Naruto Uzumaki?",
        "opcoes": ["Shukaku", "Matatabi", "Kurama", "Son Goku"],
        "resposta": "Kurama",
        "imagem": "https://i.imgur.com/nZapmcg.png"
    }
]
DEFAULT_HANGMAN_WORDS = ["python", "discord", "anime", "programacao", "bot", "shirayuki", "kawaii", "manga", "otaku"]

# --- Funções Auxiliares --- 
def ensure_dir_exists(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Diretório criado: {directory}")

def load_json_data(file_path, default_data):
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
    ensure_dir_exists(db_path)
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [ERRO SQLite] Erro ao conectar a {os.path.basename(db_path)}: {e}")
        return None

# --- Classe Base para Views de Jogos (Gerenciar estado ativo) ---
class BaseGameView(View):
    def __init__(self, interaction: Interaction, bot: commands.Bot, cog, game_type: str, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.bot = bot
        self.cog = cog
        self.game_type = game_type
        self.user_id = interaction.user.id
        self.message = None # Será definido após o envio da mensagem inicial

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Apenas {self.interaction.user.mention} pode interagir com este jogo!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            timeout_embed = Embed(title=f"{get_emoji(self.bot, 'clock')} Tempo Esgotado!", description="Você demorou muito para interagir.", color=Color.red())
            try:
                await self.message.edit(embed=timeout_embed, view=None)
            except nextcord.NotFound:
                pass # Mensagem já foi deletada ou inacessível
        self.stop() # Chama o stop da BaseGameView, que chama o stop da Cog

    def stop(self):
        if self.cog and hasattr(self.cog, 'active_games') and self.user_id in self.cog.active_games and self.game_type in self.cog.active_games[self.user_id]:
            self.cog.active_games[self.user_id].remove(self.game_type)
            if not self.cog.active_games[self.user_id]:
                del self.cog.active_games[self.user_id]
        super().stop()

# --- Quiz --- 
class QuizView(BaseGameView):
    def __init__(self, interaction: Interaction, quizzes: list, db_path: str, bot: commands.Bot, cog):
        super().__init__(interaction, bot, cog, "quiz", timeout=60.0)
        self.quizzes = quizzes
        self.db_path = db_path
        self.index = 0
        self.score = 0
        self.username = interaction.user.name
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        current_quiz = self.quizzes[self.index]
        options = current_quiz['opcoes'][:] # Copia a lista para não modificar a original
        random.shuffle(options)
        for i, option_text in enumerate(options):
            custom_id = f"quiz_opt_{i}" # ID mais simples
            button = Button(label=option_text, style=ButtonStyle.primary, custom_id=custom_id)
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: Interaction):
        selected_button_label = None
        for child in self.children:
            if isinstance(child, Button) and child.custom_id == interaction.data['custom_id']:
                selected_button_label = child.label
                break
        
        if selected_button_label is None:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Erro ao processar sua resposta.", ephemeral=True)
            return

        correct_answer = self.quizzes[self.index]['resposta']
        result_embed = Embed(color=Color.red())
        is_correct = (selected_button_label == correct_answer)

        if is_correct:
            self.score += 1
            result_embed.title = f"{get_emoji(self.bot, 'correct')} Resposta Correta!"
            result_embed.color = Color.green()
        else:
            result_embed.title = f"{get_emoji(self.bot, 'wrong')} Resposta Errada!"
            result_embed.description = f"A resposta correta era: **{correct_answer}**"

        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True
                if item.label == correct_answer:
                    item.style = ButtonStyle.success
                elif item.label == selected_button_label:
                    item.style = ButtonStyle.danger
        try:
            await interaction.response.edit_message(embed=result_embed, view=self)
        except nextcord.NotFound:
            self.stop()
            return
            
        await asyncio.sleep(2)

        self.index += 1
        if self.index >= len(self.quizzes):
            final_embed = Embed(title=f"{get_emoji(self.bot, 'celebrate')} Quiz Finalizado!", description=f"Sua pontuação: **{self.score}/{len(self.quizzes)}**", color=Color.gold())
            self.save_score()
            if self.message: await self.message.edit(embed=final_embed, view=None)
            self.stop()
        else:
            next_quiz = self.quizzes[self.index]
            question_embed = Embed(title=f"{get_emoji(self.bot, 'quiz')} Quiz - Pergunta {self.index + 1}/{len(self.quizzes)}", description=next_quiz['pergunta'], color=Color.blue())
            if next_quiz.get('imagem'):
                question_embed.set_image(url=next_quiz['imagem'])
            self.update_buttons()
            if self.message: await self.message.edit(embed=question_embed, view=self)

    def save_score(self):
        conn = connect_db(self.db_path)
        if not conn: return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ranking (user_id INTEGER PRIMARY KEY, username TEXT, pontos INTEGER DEFAULT 0, last_played TEXT)")
                cur.execute("INSERT OR IGNORE INTO ranking (user_id, username, pontos) VALUES (?, ?, 0)", (self.user_id, self.username))
                cur.execute("UPDATE ranking SET pontos = MAX(pontos, ?), username = ?, last_played = ? WHERE user_id = ?", 
                            (self.score, self.username, datetime.now(timezone.utc).isoformat(), self.user_id))
        except sqlite3.Error as e:
            print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [ERRO SQLite] Erro ao salvar pontuação do quiz: {e}")
        finally:
            if conn: conn.close()

# --- Forca (Hangman) --- 
class HangmanView(BaseGameView):
    def __init__(self, interaction: Interaction, word: str, bot: commands.Bot, cog):
        super().__init__(interaction, bot, cog, "forca", timeout=180.0)
        self.word = word.lower()
        self.guessed_letters = set()
        self.wrong_guesses = 0
        self.max_wrong_guesses = 6
        self.update_view_content()

    def get_display_word(self) -> str:
        return " ".join([letter if letter in self.guessed_letters else "\_" for letter in self.word])

    def get_hangman_stage(self) -> str:
        stages = [
            "```\n +---+\n |   |\n     |\n     |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n     |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n |   |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n/|   |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n/|\\  |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n/|\\  |\n/    |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n/|\\  |\n/ \\  |\n     |\n=========\n```"
        ]
        return stages[min(self.wrong_guesses, len(stages) - 1)]

    def update_view_content(self):
        self.clear_items()
        all_letters = "abcdefghijklmnopqrstuvwxyz"
        for i, letter in enumerate(all_letters):
            is_guessed = letter in self.guessed_letters
            style = ButtonStyle.secondary
            if is_guessed:
                style = ButtonStyle.success if letter in self.word else ButtonStyle.danger
            button = Button(label=letter.upper(), style=style, custom_id=f"hangman_{letter}", disabled=is_guessed, row=i // 7) # 7 botões por linha
            button.callback = self.letter_button_callback
            self.add_item(button)

    async def letter_button_callback(self, interaction: Interaction):
        letter = interaction.data['custom_id'].split('_')[-1]
        if letter in self.guessed_letters: # Deveria ser desabilitado, mas checa novamente
            await interaction.response.defer()
            return

        self.guessed_letters.add(letter)
        if letter not in self.word:
            self.wrong_guesses += 1

        display_word = self.get_display_word()
        hangman_art = self.get_hangman_stage()
        embed = Embed(title=f"{get_emoji(self.bot, 'hangman')} Jogo da Forca", color=Color.dark_theme())
        embed.description = f"{hangman_art}\n\nPalavra: `{display_word}`\nLetras erradas: {self.wrong_guesses}/{self.max_wrong_guesses}\nTentativas: `{' '.join(sorted(list(self.guessed_letters)))}`"

        game_over = False
        if "\_" not in display_word:
            embed.color = Color.green()
            embed.description += f"\n\n{get_emoji(self.bot, 'celebrate')} Parabéns, você venceu! A palavra era **{self.word}**."
            game_over = True
        elif self.wrong_guesses >= self.max_wrong_guesses:
            embed.color = Color.red()
            embed.description += f"\n\n{get_emoji(self.bot, 'sad')} Você perdeu! A palavra era **{self.word}**."
            game_over = True

        if game_over:
            self.update_view_content() # Atualiza para desabilitar todos os botões
            for item in self.children: item.disabled = True
            if self.message: await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
        else:
            self.update_view_content()
            if self.message: await interaction.response.edit_message(embed=embed, view=self)

# --- Jogo da Velha (Tic-Tac-Toe) --- 
class TicTacToeButton(Button):
    def __init__(self, x: int, y: int, bot):
        super().__init__(style=ButtonStyle.secondary, label="\u200b", row=y) # Label invisível
        self.x = x
        self.y = y
        self.bot = bot # Para get_emoji

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        view: TicTacToeView = self.view

        if interaction.user.id not in [view.player1.id, view.player2.id]:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não está participando deste jogo!", ephemeral=True)
            return
        if not view.is_current_player_turn(interaction.user):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} Não é sua vez de jogar!", ephemeral=True)
            return
        if view.board[self.y][self.x] is not None:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Este espaço já foi marcado!", ephemeral=True)
            return

        view.board[self.y][self.x] = view.current_player_symbol
        self.label = view.current_player_symbol
        self.style = ButtonStyle.success if view.current_player_symbol == "X" else ButtonStyle.danger
        self.disabled = True

        winner = view.check_for_winner()
        if winner:
            view.game_over(winner)
            await interaction.response.edit_message(embed=view.create_embed(), view=view)
        elif view.is_board_full():
            view.game_over("Empate")
            await interaction.response.edit_message(embed=view.create_embed(), view=view)
        else:
            view.switch_player()
            await interaction.response.edit_message(embed=view.create_embed(), view=view)

class TicTacToeView(BaseGameView):
    def __init__(self, interaction: Interaction, player1: Member | User, player2: Member | User, bot: commands.Bot, cog, db_path: str):
        super().__init__(interaction, bot, cog, "ttt", timeout=300.0) # 5 min timeout
        self.player1 = player1
        self.player2 = player2
        self.db_path = db_path
        self.current_player_id = player1.id
        self.current_player_symbol = "X"
        self.board = [[None for _ in range(3)] for _ in range(3)]
        self.winner = None
        self.message = None # Será definido após o envio da mensagem inicial

        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y, self.bot))

    def is_current_player_turn(self, user: Member | User) -> bool:
        return user.id == self.current_player_id

    def switch_player(self):
        self.current_player_id = self.player2.id if self.current_player_id == self.player1.id else self.player1.id
        self.current_player_symbol = "O" if self.current_player_symbol == "X" else "X"

    def check_for_winner(self) -> Member | User | None:
        lines = [
            # Horizontais
            [(0,0), (1,0), (2,0)], [(0,1), (1,1), (2,1)], [(0,2), (1,2), (2,2)],
            # Verticais
            [(0,0), (0,1), (0,2)], [(1,0), (1,1), (1,2)], [(2,0), (2,1), (2,2)],
            # Diagonais
            [(0,0), (1,1), (2,2)], [(0,2), (1,1), (2,0)]
        ]
        for line in lines:
            symbols_in_line = [self.board[y][x] for x, y in line]
            if symbols_in_line[0] is not None and all(s == symbols_in_line[0] for s in symbols_in_line):
                return self.player1 if symbols_in_line[0] == "X" else self.player2
        return None

    def is_board_full(self) -> bool:
        return all(all(cell is not None for cell in row) for row in self.board)

    def game_over(self, winner: Member | User | str):
        self.winner = winner
        for child in self.children:
            if isinstance(child, Button): child.disabled = True
        self.update_ttt_stats()
        self.stop() # Chama o stop da BaseGameView

    def create_embed(self) -> Embed:
        title = f"{get_emoji(self.bot, 'ttt')} Jogo da Velha: {self.player1.display_name} (X) vs {self.player2.display_name} (O)"
        if self.winner:
            if isinstance(self.winner, str) and self.winner == "Empate":
                description = f"{get_emoji(self.bot, 'draw')} O jogo empatou!"
                color = Color.light_grey()
            else:
                description = f"{get_emoji(self.bot, 'win')} {self.winner.mention} venceu o jogo!"
                color = Color.gold()
        else:
            current_player = self.player1 if self.current_player_id == self.player1.id else self.player2
            description = f"É a vez de {current_player.mention} ({self.current_player_symbol}) jogar."
            color = Color.blurple()
        
        embed = Embed(title=title, description=description, color=color)
        return embed

    def update_ttt_stats(self):
        conn = connect_db(self.db_path)
        if not conn: return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ttt_stats (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        wins INTEGER DEFAULT 0,
                        losses INTEGER DEFAULT 0,
                        draws INTEGER DEFAULT 0
                    )
                """)
                players_involved = [(self.player1.id, self.player1.name), (self.player2.id, self.player2.name)]
                for pid, pname in players_involved:
                    cur.execute("INSERT OR IGNORE INTO ttt_stats (user_id, username) VALUES (?, ?)", (pid, pname))
                    # Atualiza nome caso tenha mudado
                    cur.execute("UPDATE ttt_stats SET username = ? WHERE user_id = ?", (pname, pid))

                if isinstance(self.winner, (Member, User)):
                    winner_id = self.winner.id
                    loser_id = self.player1.id if self.winner.id == self.player2.id else self.player2.id
                    cur.execute("UPDATE ttt_stats SET wins = wins + 1 WHERE user_id = ?", (winner_id,))
                    cur.execute("UPDATE ttt_stats SET losses = losses + 1 WHERE user_id = ?", (loser_id,))
                elif self.winner == "Empate":
                    cur.execute("UPDATE ttt_stats SET draws = draws + 1 WHERE user_id = ?", (self.player1.id,))
                    cur.execute("UPDATE ttt_stats SET draws = draws + 1 WHERE user_id = ?", (self.player2.id,))
        except sqlite3.Error as e:
            print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [ERRO SQLite] Erro ao atualizar estatísticas do Jogo da Velha: {e}")
        finally:
            if conn: conn.close()

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Sobrescreve para permitir que qualquer um dos dois jogadores interaja, mas apenas na sua vez.
        if interaction.user.id not in [self.player1.id, self.player2.id]:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não está participando deste jogo!", ephemeral=True)
            return False
        # A checagem de turno é feita no callback do botão.
        return True

# --- Connect 4 (Lig 4) --- (Estrutura similar ao Jogo da Velha)
# (Implementação do Connect 4 omitida por brevidade, mas seguiria um padrão similar ao TicTacToeView)
# ... (Connect4Button, Connect4View, etc.)

# --- Cog Principal --- 
class Jogos(commands.Cog):
    """Comandos para iniciar diversos jogos interativos."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.quiz_questions = load_json_data(QUIZ_QUESTIONS_FILE, DEFAULT_QUIZ_QUESTIONS)
        self.hangman_words = load_json_data(HANGMAN_WORDS_FILE, DEFAULT_HANGMAN_WORDS)
        self.active_games = {} # {user_id: {game_type_set}}
        print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] Cog Jogos carregada.")

    def is_user_in_game(self, user_id: int, game_type: str = None) -> bool:
        if user_id in self.active_games:
            if game_type:
                return game_type in self.active_games[user_id]
            return bool(self.active_games[user_id]) # Retorna True se o usuário estiver em QUALQUER jogo
        return False

    def start_game_session(self, user_id: int, game_type: str):
        if user_id not in self.active_games:
            self.active_games[user_id] = set()
        self.active_games[user_id].add(game_type)

    @nextcord.slash_command(name="quiz", description="Inicia um quiz de conhecimentos gerais ou animes!")
    @application_checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def quiz(self, interaction: Interaction, 
                 num_perguntas: int = SlashOption(description="Número de perguntas (1-10)", default=5, min_value=1, max_value=10)):
        if self.is_user_in_game(interaction.user.id):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Você já está em um jogo! Termine o atual antes de começar outro.", ephemeral=True)
            return

        if not self.quiz_questions:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Nenhuma pergunta de quiz carregada. Tente mais tarde.", ephemeral=True)
            return
        
        selected_quizzes = random.sample(self.quiz_questions, min(num_perguntas, len(self.quiz_questions)))
        if not selected_quizzes:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Não há perguntas suficientes para iniciar o quiz com {num_perguntas} perguntas.", ephemeral=True)
            return

        self.start_game_session(interaction.user.id, "quiz")
        view = QuizView(interaction, selected_quizzes, QUIZ_DB_PATH, self.bot, self)
        
        first_quiz = selected_quizzes[0]
        embed = Embed(title=f"{get_emoji(self.bot, 'quiz')} Quiz - Pergunta 1/{len(selected_quizzes)}", description=first_quiz['pergunta'], color=Color.blue())
        if first_quiz.get('imagem'):
            embed.set_image(url=first_quiz['imagem'])
        
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message() # Salva a mensagem para edição

    @nextcord.slash_command(name="quizranking", description="Mostra o ranking do quiz.")
    async def quizranking(self, interaction: Interaction):
        conn = connect_db(QUIZ_DB_PATH)
        if not conn:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Não foi possível acessar o ranking no momento.", ephemeral=True)
            return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ranking (user_id INTEGER PRIMARY KEY, username TEXT, pontos INTEGER DEFAULT 0, last_played TEXT)")
                cur.execute("SELECT username, pontos FROM ranking ORDER BY pontos DESC LIMIT 10")
                rows = cur.fetchall()
            
            embed = Embed(title=f"{get_emoji(self.bot, 'ranking')} Ranking do Quiz", color=Color.gold())
            if not rows:
                embed.description = "Ninguém jogou o quiz ainda! Seja o primeiro!"
            else:
                desc = ""
                for i, row in enumerate(rows):
                    desc += f"**{i+1}.** {row['username']} - {row['pontos']} pontos\n"
                embed.description = desc
            await interaction.response.send_message(embed=embed)
        except sqlite3.Error as e:
            print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [ERRO SQLite] Erro ao buscar ranking do quiz: {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Erro ao buscar o ranking.", ephemeral=True)
        finally:
            if conn: conn.close()

    @nextcord.slash_command(name="forca", description="Jogue uma partida de Forca!")
    @application_checks.cooldown(1, 15, key=lambda i: (i.guild_id, i.user.id))
    async def forca(self, interaction: Interaction):
        if self.is_user_in_game(interaction.user.id):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Você já está em um jogo! Termine o atual antes de começar outro.", ephemeral=True)
            return
        
        if not self.hangman_words:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Nenhuma palavra carregada para o jogo da forca.", ephemeral=True)
            return
        
        word_to_guess = random.choice(self.hangman_words)
        self.start_game_session(interaction.user.id, "forca")
        view = HangmanView(interaction, word_to_guess, self.bot, self)

        embed = Embed(title=f"{get_emoji(self.bot, 'hangman')} Jogo da Forca", color=Color.dark_theme())
        embed.description = f"{view.get_hangman_stage()}\n\nPalavra: `{view.get_display_word()}`\nLetras erradas: {view.wrong_guesses}/{view.max_wrong_guesses}"
        
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()

    @nextcord.slash_command(name="jogodavelha", description="Desafie alguém para uma partida de Jogo da Velha!")
    @application_checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def jogodavelha(self, interaction: Interaction, oponente: Member = SlashOption(description="Quem você quer desafiar?", required=True)):
        if oponente.bot:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não pode jogar contra um bot!", ephemeral=True)
            return
        if oponente == interaction.user:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} Você não pode jogar contra si mesmo!", ephemeral=True)
            return
        if self.is_user_in_game(interaction.user.id, "ttt") or self.is_user_in_game(oponente.id, "ttt"):
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Um dos jogadores já está em uma partida de Jogo da Velha.", ephemeral=True)
            return

        self.start_game_session(interaction.user.id, "ttt")
        self.start_game_session(oponente.id, "ttt")
        
        view = TicTacToeView(interaction, interaction.user, oponente, self.bot, self, TTT_DB_PATH)
        embed = view.create_embed()
        await interaction.response.send_message(content=f"{oponente.mention}, você foi desafiado para um Jogo da Velha por {interaction.user.mention}!", embed=embed, view=view)
        view.message = await interaction.original_message()

    @nextcord.slash_command(name="tttstats", description="Mostra suas estatísticas do Jogo da Velha ou de outro usuário.")
    async def tttstats(self, interaction: Interaction, usuario: Member | User = SlashOption(description="De quem você quer ver as estatísticas? (Opcional)", required=False)):
        target_user = usuario or interaction.user
        conn = connect_db(TTT_DB_PATH)
        if not conn:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Não foi possível acessar as estatísticas no momento.", ephemeral=True)
            return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ttt_stats (user_id INTEGER PRIMARY KEY, username TEXT, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0)")
                cur.execute("SELECT username, wins, losses, draws FROM ttt_stats WHERE user_id = ?", (target_user.id,))
                row = cur.fetchone()
            
            embed = Embed(title=f"{get_emoji(self.bot, 'ranking')} Estatísticas do Jogo da Velha - {target_user.display_name}", color=Color.blue())
            if target_user.display_avatar: embed.set_thumbnail(url=target_user.display_avatar.url)

            if not row:
                embed.description = f"{target_user.mention} ainda não jogou nenhuma partida."
            else:
                embed.add_field(name="Vitórias", value=str(row['wins']))
                embed.add_field(name="Derrotas", value=str(row['losses']))
                embed.add_field(name="Empates", value=str(row['draws']))
                total_games = row['wins'] + row['losses'] + row['draws']
                win_rate = (row['wins'] / total_games * 100) if total_games > 0 else 0
                embed.add_field(name="Total de Jogos", value=str(total_games))
                embed.add_field(name="Taxa de Vitória", value=f"{win_rate:.2f}%")
            await interaction.response.send_message(embed=embed)
        except sqlite3.Error as e:
            print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [ERRO SQLite] Erro ao buscar estatísticas do Jogo da Velha: {e}")
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Erro ao buscar as estatísticas.", ephemeral=True)
        finally:
            if conn: conn.close()

    # Listener para erros de cooldown nos comandos de aplicação desta cog
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, application_checks.ApplicationCommandOnCooldown):
            # Verifica se o erro pertence a um comando desta cog
            if interaction.application_command and interaction.application_command.cog_name == self.qualified_name:
                retry_after_formatted = str(timedelta(seconds=int(error.retry_after))) # Formata para HH:MM:SS
                await interaction.response.send_message(
                    f"{get_emoji(self.bot, 'clock')} Ei, vá com calma! Você pode usar este comando novamente em **{retry_after_formatted}**.", 
                    ephemeral=True
                )
                return # Erro tratado
        
        # Para outros erros ou erros de cooldown de outras cogs, não faz nada aqui (deixa o listener global tratar, se houver)
        # Ou pode adicionar um log genérico se desejar
        # print(f"Erro não tratado na cog Jogos: {error} para comando {interaction.application_command.name if interaction.application_command else 'desconhecido'}")
        # traceback.print_exc()

def setup(bot: commands.Bot):
    bot.add_cog(Jogos(bot))
