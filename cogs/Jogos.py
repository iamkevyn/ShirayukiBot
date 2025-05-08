# /home/ubuntu/ShirayukiBot/cogs/Jogos.py
# Cog para comandos de jogos diversos.

import nextcord
from nextcord import Interaction, Embed, ButtonStyle, Color, SlashOption, Member, SelectOption, User
from nextcord.ui import View, Button, Select, Modal, TextInput
from nextcord.ext import commands # Removido application_checks, adicionado commands para cooldown
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
        print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Diretório criado: {directory}")

def load_json_data(file_path, default_data):
    ensure_dir_exists(file_path)
    if not os.path.exists(file_path):
        print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [AVISO] Arquivo {os.path.basename(file_path)} não encontrado. Criando com dados padrão.")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO] Falha ao carregar {os.path.basename(file_path)}, usando dados padrão.")
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
            await interaction.response.send_message(f"{get_emoji(self.bot, "sad")} Apenas {self.interaction.user.mention} pode interagir com este jogo!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            timeout_embed = Embed(title=f"{get_emoji(self.bot, "clock")} Tempo Esgotado!", description="Você demorou muito para interagir.", color=Color.red())
            try:
                await self.message.edit(embed=timeout_embed, view=None)
            except nextcord.NotFound:
                pass # Mensagem já foi deletada ou inacessível
        self.stop() # Chama o stop da BaseGameView, que chama o stop da Cog

    def stop(self):
        if self.cog and hasattr(self.cog, "active_games") and self.user_id in self.cog.active_games and self.game_type in self.cog.active_games[self.user_id]:
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
        options = current_quiz["opcoes"][:] # Copia a lista para não modificar a original
        random.shuffle(options)
        for i, option_text in enumerate(options):
            custom_id = f"quiz_opt_{i}" # ID mais simples
            button = Button(label=option_text, style=ButtonStyle.primary, custom_id=custom_id)
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: Interaction):
        selected_button_label = None
        for child in self.children:
            if isinstance(child, Button) and child.custom_id == interaction.data["custom_id"]:
                selected_button_label = child.label
                break
        
        if selected_button_label is None:
            await interaction.response.send_message(f"{get_emoji(self.bot, "error")} Erro ao processar sua resposta.", ephemeral=True)
            return

        correct_answer = self.quizzes[self.index]["resposta"]
        result_embed = Embed(color=Color.red())
        is_correct = (selected_button_label == correct_answer)

        if is_correct:
            self.score += 1
            result_embed.title = f"{get_emoji(self.bot, "correct")} Resposta Correta!"
            result_embed.color = Color.green()
        else:
            result_embed.title = f"{get_emoji(self.bot, "wrong")} Resposta Errada!"
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
            final_embed = Embed(title=f"{get_emoji(self.bot, "celebrate")} Quiz Finalizado!", description=f"Sua pontuação: **{self.score}/{len(self.quizzes)}**", color=Color.gold())
            self.save_score()
            if self.message: await self.message.edit(embed=final_embed, view=None)
            self.stop()
        else:
            next_quiz = self.quizzes[self.index]
            question_embed = Embed(title=f"{get_emoji(self.bot, "quiz")} Quiz - Pergunta {self.index + 1}/{len(self.quizzes)}", description=next_quiz["pergunta"], color=Color.blue())
            if next_quiz.get("imagem"):
                question_embed.set_image(url=next_quiz["imagem"])
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
            print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO SQLite] Erro ao salvar pontuação do quiz: {e}")
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
        return " ".join([letter if letter in self.guessed_letters else "\\_" for letter in self.word])

    def get_hangman_stage(self) -> str:
        stages = [
            "```\n +---+\n |   |\n     |\n     |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n     |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n |   |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n/|   |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n/|\\\\  |\n     |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n/|\\\\  |\n/    |\n     |\n=========\n```",
            "```\n +---+\n |   |\n O   |\n/|\\\\  |\n/ \\\\  |\n     |\n=========\n```"
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
        letter = interaction.data["custom_id"].split("_")[-1]
        if letter in self.guessed_letters: # Deveria ser desabilitado, mas checa novamente
            await interaction.response.defer()
            return

        self.guessed_letters.add(letter)
        if letter not in self.word:
            self.wrong_guesses += 1

        display_word = self.get_display_word()
        hangman_art = self.get_hangman_stage()
        embed = Embed(title=f"{get_emoji(self.bot, "hangman")} Jogo da Forca", color=Color.dark_theme())
        embed.description = f"{hangman_art}\n\nPalavra: `{display_word}`\nLetras erradas: {self.wrong_guesses}/{self.max_wrong_guesses}\nTentativas: `{{" ".join(sorted(list(self.guessed_letters)))}}`"

        game_over = False
        if "\\_" not in display_word:
            embed.color = Color.green()
            embed.description += f"\n\n{get_emoji(self.bot, "celebrate")} Parabéns, você venceu! A palavra era **{self.word}**."
            game_over = True
        elif self.wrong_guesses >= self.max_wrong_guesses:
            embed.color = Color.red()
            embed.description += f"\n\n{get_emoji(self.bot, "sad")} Você perdeu! A palavra era **{self.word}**."
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
            await interaction.response.send_message(f"{get_emoji(self.bot, "sad")} Você não está participando deste jogo!", ephemeral=True)
            return
        if not view.is_current_player_turn(interaction.user):
            await interaction.response.send_message(f"{get_emoji(self.bot, "thinking")} Não é sua vez de jogar!", ephemeral=True)
            return
        if view.board[self.y][self.x] is not None:
            await interaction.response.send_message(f"{get_emoji(self.bot, "error")} Este espaço já foi marcado!", ephemeral=True)
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

    def check_for_winner(self) -> str | None:
        # Checar linhas e colunas
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] and self.board[i][0] is not None:
                return self.board[i][0]
            if self.board[0][i] == self.board[1][i] == self.board[2][i] and self.board[0][i] is not None:
                return self.board[0][i]
        # Checar diagonais
        if self.board[0][0] == self.board[1][1] == self.board[2][2] and self.board[0][0] is not None:
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] and self.board[0][2] is not None:
            return self.board[0][2]
        return None

    def is_board_full(self) -> bool:
        return all(all(cell is not None for cell in row) for row in self.board)

    def game_over(self, winner_symbol: str | None):
        self.winner = winner_symbol
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        self.save_ttt_stats(winner_symbol)
        self.stop()

    def create_embed(self) -> Embed:
        title = f"{get_emoji(self.bot, "ttt")} Jogo da Velha: {self.player1.display_name} (X) vs {self.player2.display_name} (O)"
        color = Color.blurple()
        description = ""

        if self.winner:
            if self.winner == "Empate":
                title = f"{get_emoji(self.bot, "draw")} Jogo da Velha - Empate!"
                description = f"{self.player1.mention} e {self.player2.mention} empataram!"
                color = Color.gold()
            else:
                winner_player = self.player1 if self.winner == "X" else self.player2
                title = f"{get_emoji(self.bot, "win")} Jogo da Velha - {winner_player.display_name} Venceu!"
                description = f"Parabéns, {winner_player.mention}!"
                color = Color.green() if winner_player == self.player1 else Color.red()
        else:
            current_player_mention = self.player1.mention if self.current_player_id == self.player1.id else self.player2.mention
            description = f"É a vez de {current_player_mention} ({self.current_player_symbol}) jogar."
        
        embed = Embed(title=title, description=description, color=color)
        return embed

    def save_ttt_stats(self, winner_symbol: str | None):
        conn = connect_db(self.db_path)
        if not conn: return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ttt_stats (user_id INTEGER PRIMARY KEY, username TEXT, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0)")
                
                players_data = [
                    (self.player1.id, self.player1.name),
                    (self.player2.id, self.player2.name)
                ]
                for pid, pname in players_data:
                    cur.execute("INSERT OR IGNORE INTO ttt_stats (user_id, username) VALUES (?, ?)", (pid, pname))

                if winner_symbol == "X": # Player 1 (X) venceu
                    cur.execute("UPDATE ttt_stats SET wins = wins + 1, username = ? WHERE user_id = ?", (self.player1.name, self.player1.id))
                    cur.execute("UPDATE ttt_stats SET losses = losses + 1, username = ? WHERE user_id = ?", (self.player2.name, self.player2.id))
                elif winner_symbol == "O": # Player 2 (O) venceu
                    cur.execute("UPDATE ttt_stats SET wins = wins + 1, username = ? WHERE user_id = ?", (self.player2.name, self.player2.id))
                    cur.execute("UPDATE ttt_stats SET losses = losses + 1, username = ? WHERE user_id = ?", (self.player1.name, self.player1.id))
                elif winner_symbol == "Empate":
                    cur.execute("UPDATE ttt_stats SET draws = draws + 1, username = ? WHERE user_id = ?", (self.player1.name, self.player1.id))
                    cur.execute("UPDATE ttt_stats SET draws = draws + 1, username = ? WHERE user_id = ?", (self.player2.name, self.player2.id))
        except sqlite3.Error as e:
            print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO SQLite] Erro ao salvar estatísticas do Jogo da Velha: {e}")
        finally:
            if conn: conn.close()

    async def on_timeout(self):
        if not self.winner: # Se o jogo não terminou por vitória/empate
            timeout_player = self.player1 if self.current_player_id == self.player1.id else self.player2
            embed = Embed(title=f"{get_emoji(self.bot, "clock")} Jogo da Velha - Tempo Esgotado!", 
                          description=f"{timeout_player.mention} demorou muito para jogar. O jogo foi cancelado.", 
                          color=Color.orange())
            for child in self.children:
                if isinstance(child, Button):
                    child.disabled = True
            if self.message: 
                try: await self.message.edit(embed=embed, view=self)
                except nextcord.NotFound: pass
        self.stop()

# --- Connect 4 --- (Simplificado, sem persistência de estado entre reinícios do bot)
class Connect4Button(Button):
    def __init__(self, column: int, bot):
        super().__init__(style=ButtonStyle.secondary, label=str(column + 1), row=0)
        self.column = column
        self.bot = bot

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        view: Connect4View = self.view

        if interaction.user.id not in [view.player1.id, view.player2.id]:
            await interaction.response.send_message(f"{get_emoji(self.bot, "sad")} Você não está participando deste jogo!", ephemeral=True)
            return
        if not view.is_current_player_turn(interaction.user):
            await interaction.response.send_message(f"{get_emoji(self.bot, "thinking")} Não é sua vez de jogar!", ephemeral=True)
            return
        
        row = view.drop_piece(self.column)
        if row is None: # Coluna cheia
            await interaction.response.send_message(f"{get_emoji(self.bot, "error")} Esta coluna está cheia! Escolha outra.", ephemeral=True)
            return

        # Atualizar o botão da coluna se ela ficar cheia
        if view.board[0][self.column] is not None:
            self.disabled = True

        winner = view.check_for_winner(row, self.column)
        if winner:
            view.game_over(winner)
            await interaction.response.edit_message(content=view.get_board_display(), embed=view.create_embed(), view=view)
        elif view.is_board_full():
            view.game_over("Empate")
            await interaction.response.edit_message(content=view.get_board_display(), embed=view.create_embed(), view=view)
        else:
            view.switch_player()
            await interaction.response.edit_message(content=view.get_board_display(), embed=view.create_embed(), view=view)

class Connect4View(BaseGameView):
    ROWS = 6
    COLS = 7
    PLAYER_SYMBOLS = {1: "🔴", 2: "🟡"} # Player 1 é Vermelho, Player 2 é Amarelo
    EMPTY_SLOT = "⚪"

    def __init__(self, interaction: Interaction, player1: Member | User, player2: Member | User, bot: commands.Bot, cog, db_path: str):
        super().__init__(interaction, bot, cog, "connect4", timeout=600.0) # 10 min timeout
        self.player1 = player1
        self.player2 = player2
        self.db_path = db_path
        self.current_player_id = player1.id
        self.current_player_num = 1 # Player 1 começa
        self.board = [[self.EMPTY_SLOT for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.winner = None # Pode ser 1, 2 ou "Empate"
        self.message = None

        for col in range(self.COLS):
            self.add_item(Connect4Button(col, self.bot))

    def is_current_player_turn(self, user: Member | User) -> bool:
        return user.id == self.current_player_id

    def switch_player(self):
        self.current_player_num = 2 if self.current_player_num == 1 else 1
        self.current_player_id = self.player2.id if self.current_player_id == self.player1.id else self.player1.id

    def drop_piece(self, col: int) -> int | None: # Retorna a linha onde a peça caiu, ou None se a coluna estiver cheia
        for r in range(self.ROWS - 1, -1, -1): # Começa de baixo para cima
            if self.board[r][col] == self.EMPTY_SLOT:
                self.board[r][col] = self.PLAYER_SYMBOLS[self.current_player_num]
                return r
        return None # Coluna cheia

    def check_for_winner(self, row: int, col: int) -> int | None: # Retorna o número do jogador vencedor ou None
        player_symbol = self.PLAYER_SYMBOLS[self.current_player_num]

        # Horizontal
        count = 0
        for c_offset in range(-3, 4):
            c_check = col + c_offset
            if 0 <= c_check < self.COLS and self.board[row][c_check] == player_symbol:
                count += 1
                if count == 4: return self.current_player_num
            else:
                count = 0
        
        # Vertical
        count = 0
        for r_offset in range(-3, 4):
            r_check = row + r_offset
            if 0 <= r_check < self.ROWS and self.board[r_check][col] == player_symbol:
                count += 1
                if count == 4: return self.current_player_num
            else:
                count = 0

        # Diagonal (positiva /)
        count = 0
        for i in range(-3, 4):
            r_check, c_check = row + i, col + i
            if 0 <= r_check < self.ROWS and 0 <= c_check < self.COLS and self.board[r_check][c_check] == player_symbol:
                count += 1
                if count == 4: return self.current_player_num
            else:
                count = 0

        # Diagonal (negativa \)
        count = 0
        for i in range(-3, 4):
            r_check, c_check = row + i, col - i
            if 0 <= r_check < self.ROWS and 0 <= c_check < self.COLS and self.board[r_check][c_check] == player_symbol:
                count += 1
                if count == 4: return self.current_player_num
            else:
                count = 0
        return None

    def is_board_full(self) -> bool:
        return all(self.board[0][c] != self.EMPTY_SLOT for c in range(self.COLS))

    def game_over(self, winner_num_or_draw: int | str):
        self.winner = winner_num_or_draw
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        self.save_connect4_stats(winner_num_or_draw)
        self.stop()

    def get_board_display(self) -> str:
        return "\n".join([" ".join(row) for row in self.board])

    def create_embed(self) -> Embed:
        title = f"{get_emoji(self.bot, "connect4")} Connect 4: {self.player1.display_name} ({self.PLAYER_SYMBOLS[1]}) vs {self.player2.display_name} ({self.PLAYER_SYMBOLS[2]})"
        color = Color.dark_blue()
        description = ""

        if self.winner:
            if self.winner == "Empate":
                title = f"{get_emoji(self.bot, "draw")} Connect 4 - Empate!"
                description = f"{self.player1.mention} e {self.player2.mention} empataram!"
                color = Color.gold()
            else: # winner é o número do jogador (1 ou 2)
                winner_player = self.player1 if self.winner == 1 else self.player2
                title = f"{get_emoji(self.bot, "win")} Connect 4 - {winner_player.display_name} Venceu!"
                description = f"Parabéns, {winner_player.mention}!"
                color = Color.red() if self.winner == 1 else Color.gold() # Vermelho para P1, Amarelo para P2
        else:
            current_player_obj = self.player1 if self.current_player_num == 1 else self.player2
            current_player_symbol_emoji = self.PLAYER_SYMBOLS[self.current_player_num]
            description = f"É a vez de {current_player_obj.mention} ({current_player_symbol_emoji}) jogar."
        
        embed = Embed(title=title, description=description, color=color)
        return embed

    def save_connect4_stats(self, winner_num_or_draw: int | str):
        conn = connect_db(self.db_path)
        if not conn: return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS connect4_stats (user_id INTEGER PRIMARY KEY, username TEXT, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0)")
                
                players_data = [
                    (self.player1.id, self.player1.name),
                    (self.player2.id, self.player2.name)
                ]
                for pid, pname in players_data:
                    cur.execute("INSERT OR IGNORE INTO connect4_stats (user_id, username) VALUES (?, ?)", (pid, pname))

                if isinstance(winner_num_or_draw, int):
                    winner_id = self.player1.id if winner_num_or_draw == 1 else self.player2.id
                    loser_id = self.player2.id if winner_num_or_draw == 1 else self.player1.id
                    winner_name = self.player1.name if winner_num_or_draw == 1 else self.player2.name
                    loser_name = self.player2.name if winner_num_or_draw == 1 else self.player1.name

                    cur.execute("UPDATE connect4_stats SET wins = wins + 1, username = ? WHERE user_id = ?", (winner_name, winner_id))
                    cur.execute("UPDATE connect4_stats SET losses = losses + 1, username = ? WHERE user_id = ?", (loser_name, loser_id))
                elif winner_num_or_draw == "Empate":
                    cur.execute("UPDATE connect4_stats SET draws = draws + 1, username = ? WHERE user_id = ?", (self.player1.name, self.player1.id))
                    cur.execute("UPDATE connect4_stats SET draws = draws + 1, username = ? WHERE user_id = ?", (self.player2.name, self.player2.id))
        except sqlite3.Error as e:
            print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO SQLite] Erro ao salvar estatísticas do Connect 4: {e}")
        finally:
            if conn: conn.close()

    async def on_timeout(self):
        if not self.winner:
            timeout_player = self.player1 if self.current_player_num == 1 else self.player2
            embed = Embed(title=f"{get_emoji(self.bot, "clock")} Connect 4 - Tempo Esgotado!", 
                          description=f"{timeout_player.mention} demorou muito para jogar. O jogo foi cancelado.", 
                          color=Color.orange())
            for child in self.children:
                if isinstance(child, Button):
                    child.disabled = True
            if self.message: 
                try: await self.message.edit(content=self.get_board_display(), embed=embed, view=self)
                except nextcord.NotFound: pass
        self.stop()

# --- Cog Principal --- 
class Jogos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games = {} # {user_id: ["quiz", "forca", ...]}
        self.quiz_questions = load_json_data(QUIZ_QUESTIONS_FILE, DEFAULT_QUIZ_QUESTIONS)
        self.hangman_words = load_json_data(HANGMAN_WORDS_FILE, DEFAULT_HANGMAN_WORDS)
        print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Cog Jogos carregada.")
        print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] {len(self.quiz_questions)} perguntas de quiz carregadas.")
        print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] {len(self.hangman_words)} palavras para forca carregadas.")

    def cog_unload(self):
        # Tentar parar views ativas se necessário, embora o bot desligando deva fazer isso
        for user_id, games in list(self.active_games.items()): # list() para evitar erro de modificação durante iteração
            for game_type in list(games): # list() para evitar erro de modificação durante iteração
                # A lógica de stop na BaseGameView já remove da lista
                # Encontrar a view e chamar stop() nela pode ser complexo sem referência direta
                # Por agora, apenas limpamos o registro
                if game_type in self.active_games.get(user_id, []):
                    self.active_games[user_id].remove(game_type)
                if not self.active_games.get(user_id, []):
                    del self.active_games[user_id]
        print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Cog Jogos descarregada.")

    def is_user_in_game(self, user_id: int, game_type: str = None) -> bool:
        if user_id in self.active_games:
            if game_type:
                return game_type in self.active_games[user_id]
            return bool(self.active_games[user_id]) # Retorna True se o usuário estiver em QUALQUER jogo
        return False

    def start_game_session(self, user_id: int, game_type: str):
        if user_id not in self.active_games:
            self.active_games[user_id] = []
        if game_type not in self.active_games[user_id]:
            self.active_games[user_id].append(game_type)

    async def send_error_embed(self, interaction: Interaction, title: str, description: str):
        embed = Embed(title=f"{get_emoji(self.bot, "sad")} {title}", description=description, color=Color.red())
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Comandos de Jogos --- 
    @nextcord.slash_command(name="quiz", description="Inicia um quiz de conhecimentos gerais ou sobre animes!")
    @commands.cooldown(1, 30, commands.BucketType.user) # CORRIGIDO: Usar commands.cooldown
    async def quiz_command(self, interaction: Interaction, 
                           num_perguntas: int = SlashOption(description="Número de perguntas (1-10, padrão 5).", default=5, min_value=1, max_value=10)):
        if self.is_user_in_game(interaction.user.id):
            await self.send_error_embed(interaction, "Jogo em Andamento", "Você já está em um jogo! Termine-o antes de iniciar outro.")
            return
        if not self.quiz_questions:
            await self.send_error_embed(interaction, "Sem Perguntas", "Não há perguntas de quiz carregadas no momento.")
            return

        self.start_game_session(interaction.user.id, "quiz")
        
        # Selecionar N perguntas aleatórias
        if num_perguntas > len(self.quiz_questions):
            num_perguntas = len(self.quiz_questions)
        selected_quizzes = random.sample(self.quiz_questions, num_perguntas)

        view = QuizView(interaction, selected_quizzes, QUIZ_DB_PATH, self.bot, self)
        first_quiz = selected_quizzes[0]
        embed = Embed(title=f"{get_emoji(self.bot, "quiz")} Quiz - Pergunta 1/{num_perguntas}", description=first_quiz["pergunta"], color=Color.blue())
        if first_quiz.get("imagem"):
            embed.set_image(url=first_quiz["imagem"])
        
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()

    @nextcord.slash_command(name="quizranking", description="Mostra o ranking do quiz.")
    async def quiz_ranking(self, interaction: Interaction):
        conn = connect_db(QUIZ_DB_PATH)
        if not conn:
            await self.send_error_embed(interaction, "Erro de Banco de Dados", "Não foi possível conectar ao banco de dados do ranking.")
            return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ranking (user_id INTEGER PRIMARY KEY, username TEXT, pontos INTEGER DEFAULT 0, last_played TEXT)")
                cur.execute("SELECT username, pontos FROM ranking ORDER BY pontos DESC LIMIT 10")
                rows = cur.fetchall()
            
            if not rows:
                embed = Embed(title=f"{get_emoji(self.bot, "ranking")} Ranking do Quiz", description="Ninguém jogou o quiz ainda! Seja o primeiro!", color=Color.gold())
            else:
                embed = Embed(title=f"{get_emoji(self.bot, "ranking")} Top 10 - Ranking do Quiz", color=Color.gold())
                description = ""
                for i, row_data in enumerate(rows):
                    username = row_data["username"]
                    pontos = row_data["pontos"]
                    rank_emoji = ""
                    if i == 0: rank_emoji = "🥇 "
                    elif i == 1: rank_emoji = "🥈 "
                    elif i == 2: rank_emoji = "🥉 "
                    description += f"{rank_emoji}**{i+1}. {username}** - {pontos} pontos\n"
                embed.description = description
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except sqlite3.Error as e:
            await self.send_error_embed(interaction, "Erro de Banco de Dados", f"Erro ao buscar ranking: {e}")
            print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO SQLite] Erro ao buscar ranking do quiz: {e}")
        finally:
            if conn: conn.close()

    @nextcord.slash_command(name="forca", description="Joga uma partida de Forca!")
    @commands.cooldown(1, 60, commands.BucketType.user) # CORRIGIDO: Usar commands.cooldown
    async def forca_command(self, interaction: Interaction):
        if self.is_user_in_game(interaction.user.id):
            await self.send_error_embed(interaction, "Jogo em Andamento", "Você já está em um jogo! Termine-o antes de iniciar outro.")
            return
        if not self.hangman_words:
            await self.send_error_embed(interaction, "Sem Palavras", "Não há palavras para o jogo da forca carregadas.")
            return

        self.start_game_session(interaction.user.id, "forca")
        word_to_guess = random.choice(self.hangman_words)
        view = HangmanView(interaction, word_to_guess, self.bot, self)
        
        embed = Embed(title=f"{get_emoji(self.bot, "hangman")} Jogo da Forca", color=Color.dark_theme())
        embed.description = f"{view.get_hangman_stage()}\n\nPalavra: `{view.get_display_word()}`\nLetras erradas: {view.wrong_guesses}/{view.max_wrong_guesses}\nTentativas: ` `"
        
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()

    @nextcord.slash_command(name="jogodavelha", description="Desafie alguém para uma partida de Jogo da Velha!")
    @commands.cooldown(1, 60, commands.BucketType.user) # CORRIGIDO: Usar commands.cooldown
    async def jogodavelha_command(self, interaction: Interaction, 
                                  oponente: Member = SlashOption(description="O usuário que você quer desafiar.", required=True)):
        if self.is_user_in_game(interaction.user.id, "ttt") or self.is_user_in_game(oponente.id, "ttt"):
            await self.send_error_embed(interaction, "Jogo em Andamento", "Você ou seu oponente já estão em um jogo da velha! Termine-o antes.")
            return
        if oponente == interaction.user:
            await self.send_error_embed(interaction, "Jogar Sozinho?", "Você não pode se desafiar para o jogo da velha!")
            return
        if oponente.bot:
            await self.send_error_embed(interaction, "Desafiar Bot?", "Você não pode desafiar um bot para o jogo da velha!")
            return

        # View de Confirmação do Desafio
        confirm_view = View(timeout=60.0)
        confirm_message = None

        async def confirm_callback(button_interaction: Interaction):
            nonlocal confirm_message
            if button_interaction.user.id != oponente.id:
                await button_interaction.response.send_message(f"{get_emoji(self.bot, "sad")} Apenas {oponente.mention} pode aceitar ou recusar.", ephemeral=True)
                return
            
            for item in confirm_view.children: item.disabled = True
            
            if button_interaction.data["custom_id"] == "accept_ttt":
                self.start_game_session(interaction.user.id, "ttt")
                self.start_game_session(oponente.id, "ttt")
                
                game_view = TicTacToeView(interaction, interaction.user, oponente, self.bot, self, TTT_DB_PATH)
                game_embed = game_view.create_embed()
                await button_interaction.response.edit_message(content=f"{get_emoji(self.bot, "joystick")} Jogo da Velha Iniciado!", embed=game_embed, view=game_view)
                game_view.message = await button_interaction.original_message()
            else: # Recusou
                await button_interaction.response.edit_message(content=f"{get_emoji(self.bot, "sad")} {oponente.mention} recusou o desafio de Jogo da Velha.", embed=None, view=None)
            confirm_view.stop()

        async def timeout_callback():
            nonlocal confirm_message
            if confirm_message: # Se a mensagem ainda existe
                for item in confirm_view.children: item.disabled = True
                try:
                    await confirm_message.edit(content=f"{get_emoji(self.bot, "clock")} {oponente.mention} não respondeu ao desafio de Jogo da Velha a tempo.", embed=None, view=confirm_view)
                except nextcord.NotFound:
                    pass
            confirm_view.stop()

        accept_button = Button(label="Aceitar", style=ButtonStyle.green, custom_id="accept_ttt")
        reject_button = Button(label="Recusar", style=ButtonStyle.red, custom_id="reject_ttt")
        accept_button.callback = confirm_callback
        reject_button.callback = confirm_callback
        confirm_view.on_timeout = timeout_callback
        confirm_view.add_item(accept_button)
        confirm_view.add_item(reject_button)

        await interaction.response.send_message(f"{oponente.mention}, você foi desafiado para uma partida de Jogo da Velha por {interaction.user.mention}! Você aceita?", view=confirm_view)
        confirm_message = await interaction.original_message()

    @nextcord.slash_command(name="connect4", description="Desafie alguém para uma partida de Connect 4 (Ligue 4)!")
    @commands.cooldown(1, 60, commands.BucketType.user) # CORRIGIDO: Usar commands.cooldown
    async def connect4_command(self, interaction: Interaction, 
                               oponente: Member = SlashOption(description="O usuário que você quer desafiar.", required=True)):
        if self.is_user_in_game(interaction.user.id, "connect4") or self.is_user_in_game(oponente.id, "connect4"):
            await self.send_error_embed(interaction, "Jogo em Andamento", "Você ou seu oponente já estão em um jogo de Connect 4! Termine-o antes.")
            return
        if oponente == interaction.user:
            await self.send_error_embed(interaction, "Jogar Sozinho?", "Você não pode se desafiar para o Connect 4!")
            return
        if oponente.bot:
            await self.send_error_embed(interaction, "Desafiar Bot?", "Você não pode desafiar um bot para o Connect 4!")
            return

        confirm_view = View(timeout=60.0)
        confirm_message = None

        async def confirm_callback(button_interaction: Interaction):
            nonlocal confirm_message
            if button_interaction.user.id != oponente.id:
                await button_interaction.response.send_message(f"{get_emoji(self.bot, "sad")} Apenas {oponente.mention} pode aceitar ou recusar.", ephemeral=True)
                return
            
            for item in confirm_view.children: item.disabled = True
            
            if button_interaction.data["custom_id"] == "accept_c4":
                self.start_game_session(interaction.user.id, "connect4")
                self.start_game_session(oponente.id, "connect4")
                
                game_view = Connect4View(interaction, interaction.user, oponente, self.bot, self, CONNECT4_DB_PATH)
                game_embed = game_view.create_embed()
                await button_interaction.response.edit_message(content=f"{get_emoji(self.bot, "joystick")} Connect 4 Iniciado!\n{game_view.get_board_display()}", embed=game_embed, view=game_view)
                game_view.message = await button_interaction.original_message()
            else: # Recusou
                await button_interaction.response.edit_message(content=f"{get_emoji(self.bot, "sad")} {oponente.mention} recusou o desafio de Connect 4.", embed=None, view=None)
            confirm_view.stop()

        async def timeout_callback():
            nonlocal confirm_message
            if confirm_message:
                for item in confirm_view.children: item.disabled = True
                try:
                    await confirm_message.edit(content=f"{get_emoji(self.bot, "clock")} {oponente.mention} não respondeu ao desafio de Connect 4 a tempo.", embed=None, view=confirm_view)
                except nextcord.NotFound:
                    pass
            confirm_view.stop()

        accept_button = Button(label="Aceitar", style=ButtonStyle.green, custom_id="accept_c4")
        reject_button = Button(label="Recusar", style=ButtonStyle.red, custom_id="reject_c4")
        accept_button.callback = confirm_callback
        reject_button.callback = confirm_callback
        confirm_view.on_timeout = timeout_callback
        confirm_view.add_item(accept_button)
        confirm_view.add_item(reject_button)

        await interaction.response.send_message(f"{oponente.mention}, você foi desafiado para uma partida de Connect 4 por {interaction.user.mention}! Você aceita?", view=confirm_view)
        confirm_message = await interaction.original_message()

    @nextcord.slash_command(name="rankingjogos", description="Mostra o ranking de um jogo específico.")
    async def ranking_jogos(self, interaction: Interaction,
                            jogo: str = SlashOption(description="Escolha o jogo para ver o ranking.", choices={"Quiz": "quiz", "Jogo da Velha": "ttt", "Connect 4": "connect4"}, required=True)):
        db_path = None
        table_name = None
        game_name_display = ""

        if jogo == "quiz":
            db_path = QUIZ_DB_PATH
            table_name = "ranking"
            game_name_display = "Quiz"
            score_column = "pontos"
        elif jogo == "ttt":
            db_path = TTT_DB_PATH
            table_name = "ttt_stats"
            game_name_display = "Jogo da Velha"
            score_column = "wins" # Pode adicionar W/L/D ratio depois
        elif jogo == "connect4":
            db_path = CONNECT4_DB_PATH
            table_name = "connect4_stats"
            game_name_display = "Connect 4"
            score_column = "wins"
        else:
            await self.send_error_embed(interaction, "Jogo Inválido", "O jogo selecionado não é válido.")
            return

        conn = connect_db(db_path)
        if not conn:
            await self.send_error_embed(interaction, "Erro de Banco de Dados", f"Não foi possível conectar ao banco de dados do ranking de {game_name_display}.")
            return
        
        try:
            with conn:
                cur = conn.cursor()
                # Verificar se a tabela existe
                cur.execute(f"SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"{table_name}\"")
                if not cur.fetchone():
                    await interaction.response.send_message(embed=Embed(title=f"{get_emoji(self.bot, "ranking")} Ranking de {game_name_display}", description=f"Ninguém jogou {game_name_display} ainda!", color=Color.gold()), ephemeral=True)
                    return

                # Para TTT e Connect4, podemos querer um ranking mais elaborado (ex: W-L-D)
                if jogo in ["ttt", "connect4"]:
                    cur.execute(f"SELECT username, wins, losses, draws FROM {table_name} ORDER BY wins DESC, losses ASC LIMIT 10")
                    rows = cur.fetchall()
                    if not rows:
                        embed_desc = f"Ninguém jogou {game_name_display} ainda!"
                    else:
                        embed_desc = ""
                        for i, row_data in enumerate(rows):
                            rank_emoji = "🥇 " if i == 0 else ("🥈 " if i == 1 else ("🥉 " if i == 2 else ""))
                            embed_desc += f"{rank_emoji}**{i+1}. {row_data["username"]}** - V: {row_data["wins"]}, D: {row_data["losses"]}, E: {row_data["draws"]}\n"
                else: # Quiz
                    cur.execute(f"SELECT username, {score_column} FROM {table_name} ORDER BY {score_column} DESC LIMIT 10")
                    rows = cur.fetchall()
                    if not rows:
                        embed_desc = f"Ninguém jogou {game_name_display} ainda!"
                    else:
                        embed_desc = ""
                        for i, row_data in enumerate(rows):
                            rank_emoji = "🥇 " if i == 0 else ("🥈 " if i == 1 else ("🥉 " if i == 2 else ""))
                            embed_desc += f"{rank_emoji}**{i+1}. {row_data["username"]}** - {row_data[score_column]} {("pontos" if jogo == "quiz" else "vitórias")}\n"
                
                embed = Embed(title=f"{get_emoji(self.bot, "ranking")} Top 10 - Ranking de {game_name_display}", description=embed_desc, color=Color.gold())
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except sqlite3.Error as e:
            await self.send_error_embed(interaction, "Erro de Banco de Dados", f"Erro ao buscar ranking de {game_name_display}: {e}")
            print(f"[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [ERRO SQLite] Erro ao buscar ranking de {game_name_display}: {e}")
        finally:
            if conn: conn.close()

    # Listener para erros de comando de aplicação (específico para esta cog, se necessário)
    # @commands.Cog.listener()
    # async def on_application_command_error(self, interaction: Interaction, error: Exception):
    #     # Se o erro for de cooldown, tratar aqui
    #     if isinstance(error, commands.CommandOnCooldown) or isinstance(error, application_checks.ApplicationCooldown): # Adicionado ApplicationCooldown
    #         # Formatar o tempo restante de forma amigável
    #         retry_after_formatted = str(timedelta(seconds=int(error.retry_after))).split(".")[0] # Formata para HH:MM:SS
    #         await self.send_error_embed(interaction, "Comando em Cooldown", f"Este comando está em cooldown. Tente novamente em **{retry_after_formatted}**.")
    #         return
        
    #     # Para outros erros, pode deixar o handler global (se houver) ou tratar aqui
    #     print(f"[ERRO JOGOS COG] Erro não tratado no comando {interaction.application_command.qualified_name if interaction.application_command else "desconhecido"}: {error}")
    #     traceback.print_exc()
    #     await self.send_error_embed(interaction, "Erro Inesperado no Jogo", "Ocorreu um erro inesperado. Tente novamente mais tarde.")

def setup(bot):
    bot.add_cog(Jogos(bot))
