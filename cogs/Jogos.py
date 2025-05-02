# /home/ubuntu/ShirayukiBot/cogs/Jogos.py
# Cog para comandos de jogos diversos.

import nextcord
from nextcord import Interaction, Embed, ButtonStyle, Color, SlashOption, Member
from nextcord.ui import View, Button, Select
from nextcord.ext import commands
import random
import sqlite3
import asyncio
import os
import json # Para carregar perguntas do quiz

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
QUIZ_DB_PATH = "/home/ubuntu/ShirayukiBot/data/quiz_ranking.db"
QUIZ_QUESTIONS_FILE = "/home/ubuntu/ShirayukiBot/data/quiz_questions.json"
HANGMAN_WORDS_FILE = "/home/ubuntu/ShirayukiBot/data/hangman_words.json"

# --- Funções Auxiliares --- 
def ensure_dir_exists(file_path):
    """Garante que o diretório de um arquivo exista."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"[INFO] Diretório criado: {directory}")

def load_json_data(file_path, default_data):
    """Carrega dados de um arquivo JSON, criando-o com dados padrão se não existir."""
    ensure_dir_exists(file_path)
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"[ERRO] Falha ao carregar {file_path}, usando dados padrão.")
        return default_data

# --- Views e Componentes para Jogos ---

# --- Quiz --- 
class QuizView(View):
    def __init__(self, interaction: Interaction, quizzes: list, db_path: str):
        super().__init__(timeout=60.0) # Timeout de 60 segundos por pergunta
        self.interaction = interaction
        self.quizzes = quizzes
        self.db_path = db_path
        self.index = 0
        self.score = 0
        self.user_id = interaction.user.id
        self.username = interaction.user.name
        self.message = None # Para editar a mensagem depois
        self.update_buttons()

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Permite apenas que o usuário original interaja
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJI_WARN} Apenas {self.interaction.user.mention} pode responder a este quiz!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            timeout_embed = Embed(title="⏰ Tempo Esgotado!", description="Você demorou muito para responder.", color=Color.red())
            await self.message.edit(embed=timeout_embed, view=None)
        self.stop()

    def update_buttons(self):
        """Limpa e atualiza os botões para a pergunta atual."""
        self.clear_items()
        current_quiz = self.quizzes[self.index]
        options = current_quiz['opcoes']
        random.shuffle(options) # Embaralha as opções
        for i, option in enumerate(options):
            button = Button(label=option, style=ButtonStyle.primary, custom_id=f"quiz_{i}_{option[:80]}") # Limita tamanho do custom_id
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: Interaction):
        """Processa a resposta do botão."""
        # Extrai a opção do custom_id (ignorando o prefixo e índice)
        selected_option = interaction.data['custom_id'].split('_', 2)[-1]
        correct_answer = self.quizzes[self.index]['resposta']

        result_embed = Embed(color=Color.red())
        if selected_option == correct_answer:
            self.score += 1
            result_embed.title = f"{EMOJI_SUCCESS} Resposta Correta!"
            result_embed.color = Color.green()
        else:
            result_embed.title = f"{EMOJI_FAILURE} Resposta Errada!"
            result_embed.description = f"A resposta correta era: **{correct_answer}**"

        # Desabilita botões e mostra o resultado brevemente
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True
                if item.label == correct_answer:
                    item.style = ButtonStyle.success
                elif item.label == selected_option:
                    item.style = ButtonStyle.danger
        await interaction.response.edit_message(embed=result_embed, view=self)
        await asyncio.sleep(2) # Pausa para mostrar o resultado

        # Avança para a próxima pergunta ou finaliza
        self.index += 1
        if self.index >= len(self.quizzes):
            # Fim do Quiz
            final_embed = Embed(
                title=f"{EMOJI_CELEBRATE} Quiz Finalizado!",
                description=f"Sua pontuação: **{self.score}/{len(self.quizzes)}**",
                color=Color.gold()
            )
            self.save_score()
            await self.message.edit(embed=final_embed, view=None)
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
            await self.message.edit(embed=question_embed, view=self)

    def save_score(self):
        """Salva ou atualiza a pontuação do usuário no banco de dados SQLite."""
        ensure_dir_exists(self.db_path)
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ranking (user_id INTEGER PRIMARY KEY, username TEXT, pontos INTEGER DEFAULT 0)")
                # Usa INSERT OR IGNORE e depois UPDATE para simplificar
                cur.execute("INSERT OR IGNORE INTO ranking (user_id, username, pontos) VALUES (?, ?, 0)", (self.user_id, self.username))
                # Atualiza a pontuação se a nova for maior
                cur.execute("UPDATE ranking SET pontos = MAX(pontos, ?), username = ? WHERE user_id = ?", (self.score, self.username, self.user_id))
                con.commit()
        except sqlite3.Error as e:
            print(f"[ERRO SQLite] Erro ao salvar pontuação do quiz: {e}")

# --- Forca --- 
class HangmanView(View):
    def __init__(self, interaction: Interaction, word: str):
        super().__init__(timeout=180.0) # 3 minutos de timeout total
        self.interaction = interaction
        self.word = word.lower()
        self.guessed_letters = set()
        self.wrong_guesses = 0
        self.max_wrong_guesses = 6 # Número de estágios do boneco
        self.user_id = interaction.user.id
        self.message = None
        self.update_view()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJI_WARN} Apenas {self.interaction.user.mention} pode jogar esta partida de forca!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            timeout_embed = Embed(title="⏰ Tempo Esgotado!", description=f"Você demorou muito! A palavra era **{self.word}**.", color=Color.red())
            await self.message.edit(embed=timeout_embed, view=None)
        self.stop()

    def get_display_word(self) -> str:
        """Retorna a palavra com letras adivinhadas e underscores."""
        return " ".join([letter if letter in self.guessed_letters else "\_" for letter in self.word])

    def get_hangman_stage(self) -> str:
        """Retorna a representação ASCII do boneco da forca."""
        stages = [
            """ 
               +---+
               |   |
                   |
                   |
                   |
                   |
            =========""",
            """ 
               +---+
               |   |
               O   |
                   |
                   |
                   |
            =========""",
            """ 
               +---+
               |   |
               O   |
               |   |
                   |
                   |
            =========""",
            """ 
               +---+
               |   |
               O   |
              /|   |
                   |
                   |
            =========""",
            """ 
               +---+
               |   |
               O   |
              /|\  |
                   |
                   |
            =========""",
            """ 
               +---+
               |   |
               O   |
              /|\  |
              /    |
                   |
            =========""",
            """ 
               +---+
               |   |
               O   |
              /|\  |
              / \  |
                   |
            ========="""
        ]
        return stages[self.wrong_guesses]

    def update_view(self):
        """Atualiza os botões do teclado."""
        self.clear_items()
        # Adiciona botões do alfabeto
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        for letter in alphabet:
            button = Button(
                label=letter.upper(),
                style=ButtonStyle.secondary if letter not in self.guessed_letters else (ButtonStyle.success if letter in self.word else ButtonStyle.danger),
                custom_id=f"hangman_{letter}",
                disabled=(letter in self.guessed_letters)
            )
            button.callback = self.letter_button_callback
            self.add_item(button)

    async def letter_button_callback(self, interaction: Interaction):
        """Processa o clique no botão de letra."""
        letter = interaction.data['custom_id'].split('_')[-1]
        
        if letter in self.guessed_letters:
            await interaction.response.defer() # Apenas ignora se já foi clicado
            return

        self.guessed_letters.add(letter)

        if letter not in self.word:
            self.wrong_guesses += 1

        # Atualiza a view (desabilita o botão clicado)
        self.update_view()

        # Verifica condição de vitória ou derrota
        display_word_no_spaces = "".join([letter if letter in self.guessed_letters else "" for letter in self.word])
        game_over = False
        result_embed = None

        if display_word_no_spaces == self.word:
            result_embed = Embed(title=f"{EMOJI_CELEBRATE} Você Venceu!", description=f"Parabéns, você adivinhou a palavra **{self.word}**!", color=Color.green())
            game_over = True
        elif self.wrong_guesses >= self.max_wrong_guesses:
            result_embed = Embed(title=f"{EMOJI_FAILURE} Você Perdeu!", description=f"Você foi enforcado! A palavra era **{self.word}**.", color=Color.red())
            game_over = True

        if game_over:
            for item in self.children:
                 if isinstance(item, Button): item.disabled = True
            hangman_art = self.get_hangman_stage()
            result_embed.add_field(name="Palavra", value=f"`{self.get_display_word()}`", inline=False)
            result_embed.add_field(name="Desenho", value=f"```\n{hangman_art}\n```", inline=False)
            await interaction.response.edit_message(embed=result_embed, view=self if not game_over else None)
            if game_over: self.stop()
        else:
            # Continua o jogo
            game_embed = self.create_game_embed()
            await interaction.response.edit_message(embed=game_embed, view=self)

    def create_game_embed(self) -> Embed:
        """Cria o embed do estado atual do jogo da forca."""
        embed = Embed(title="🤔 Jogo da Forca", color=Color.dark_theme())
        hangman_art = self.get_hangman_stage()
        embed.description = f"Adivinhe a palavra:\n`{self.get_display_word()}`"
        embed.add_field(name="Desenho", value=f"```\n{hangman_art}\n```", inline=False)
        wrong_letters = sorted([l for l in self.guessed_letters if l not in self.word])
        embed.add_field(name=f"Erradas ({len(wrong_letters)})", value=" ".join(wrong_letters) if wrong_letters else "Nenhuma", inline=False)
        embed.set_footer(text=f"Tentativas restantes: {self.max_wrong_guesses - self.wrong_guesses}")
        return embed

# --- Cog Principal --- 
class Jogos(commands.Cog):
    """Comandos para jogar diversos jogos com o bot."""
    def __init__(self, bot):
        self.bot = bot
        self.quiz_questions = load_json_data(QUIZ_QUESTIONS_FILE, self.get_default_quiz_questions())
        self.hangman_words = load_json_data(HANGMAN_WORDS_FILE, self.get_default_hangman_words())
        print(f"[DIAGNÓSTICO] Cog Jogos carregada.")
        print(f"[Jogos] {len(self.quiz_questions)} perguntas de quiz carregadas.")
        print(f"[Jogos] {len(self.hangman_words)} palavras da forca carregadas.")

    def get_default_quiz_questions(self):
        # Retorna algumas perguntas padrão caso o arquivo não exista
        return [
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
                "pergunta": "Em 'Attack on Titan', qual o nome do protagonista principal?",
                "opcoes": ["Levi Ackerman", "Mikasa Ackerman", "Armin Arlert", "Eren Yeager"],
                "resposta": "Eren Yeager",
                "imagem": "https://static.wikia.nocookie.net/shingekinokyojin/images/a/a1/Eren_Yeager_Anime_Infobox.png/revision/latest?cb=20210315183633&path-prefix=pt-br"
            }
        ]

    def get_default_hangman_words(self):
         # Retorna algumas palavras padrão caso o arquivo não exista
        return ["python", "discord", "anime", "programacao", "bot", "shirayuki", "kawaii", "manga", "otaku"]

    # --- Comandos Slash --- 

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="quiz", description="Inicia um quiz de anime!")
    async def quiz(self, interaction: Interaction, quantidade: int = SlashOption(name="perguntas", description="Número de perguntas (máx 10)", min_value=3, max_value=10, default=5)):
        """Inicia um quiz interativo com perguntas sobre animes."""
        if quantidade > len(self.quiz_questions):
            await interaction.response.send_message(f"{EMOJI_WARN} Não tenho tantas perguntas ({quantidade})! O máximo é {len(self.quiz_questions)}.", ephemeral=True)
            return
            
        selected_quizzes = random.sample(self.quiz_questions, quantidade)
        
        initial_embed = Embed(
            title=f"🧠 Quiz - Pergunta 1/{quantidade}",
            description=selected_quizzes[0]['pergunta'],
            color=Color.blue()
        )
        if selected_quizzes[0].get('imagem'):
            initial_embed.set_image(url=selected_quizzes[0]['imagem'])
            
        view = QuizView(interaction, selected_quizzes, QUIZ_DB_PATH)
        await interaction.response.send_message(embed=initial_embed, view=view)
        view.message = await interaction.original_message() # Guarda a mensagem para edição futura

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="quiz_ranking", description="Mostra o ranking do quiz.")
    async def quiz_ranking(self, interaction: Interaction, top: int = SlashOption(default=10, min_value=1, max_value=25)):
        """Exibe os melhores jogadores do quiz."""
        ensure_dir_exists(QUIZ_DB_PATH)
        embed = Embed(title=f"🏆 Ranking do Quiz (Top {top})", color=Color.gold())
        try:
            with sqlite3.connect(QUIZ_DB_PATH) as con:
                cur = con.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS ranking (user_id INTEGER PRIMARY KEY, username TEXT, pontos INTEGER DEFAULT 0)")
                cur.execute("SELECT user_id, username, pontos FROM ranking ORDER BY pontos DESC LIMIT ?", (top,))
                ranking_data = cur.fetchall()
                
                if not ranking_data:
                    embed.description = f"{EMOJI_INFO} Ninguém jogou o quiz ainda! Use `/quiz` para começar."
                else:
                    rank_list = []
                    for i, (user_id, username, pontos) in enumerate(ranking_data):
                        rank_emoji = ""
                        if i == 0: rank_emoji = "🥇 "
                        elif i == 1: rank_emoji = "🥈 "
                        elif i == 2: rank_emoji = "🥉 "
                        else: rank_emoji = f"#{i+1} "
                        # Tenta mencionar, mas usa o nome salvo se falhar
                        try:
                            user = await self.bot.fetch_user(user_id)
                            user_display = user.mention
                        except:
                            user_display = username # Nome salvo no DB
                        rank_list.append(f"{rank_emoji}{user_display}: **{pontos} pontos**")
                    embed.description = "\n".join(rank_list)
        except sqlite3.Error as e:
            print(f"[ERRO SQLite] Erro ao ler ranking do quiz: {e}")
            embed.description = f"{EMOJI_FAILURE} Erro ao carregar o ranking."
            
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="forca", description="Jogue forca com o bot!")
    async def forca(self, interaction: Interaction):
        """Inicia um jogo interativo da forca."""
        if not self.hangman_words:
             await interaction.response.send_message(f"{EMOJI_FAILURE} Não há palavras carregadas para o jogo da forca!", ephemeral=True)
             return
             
        word_to_guess = random.choice(self.hangman_words)
        view = HangmanView(interaction, word_to_guess)
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

        embed = Embed(title=f"Pedra, Papel, Tesoura!", color=Color.random())
        embed.add_field(name=f"{interaction.user.display_name} jogou", value=escolha_user_emoji, inline=True)
        embed.add_field(name=f"{self.bot.user.name} jogou", value=escolha_bot_emoji, inline=True)

        if escolha == escolha_bot_key:
            resultado = f"🤝 Empate!" 
            embed.color = Color.light_grey()
        elif (escolha == "pedra" and escolha_bot_key == "tesoura") or \
             (escolha == "papel" and escolha_bot_key == "pedra") or \
             (escolha == "tesoura" and escolha_bot_key == "papel"):
            resultado = f"{EMOJI_CELEBRATE} Você ganhou!"
            embed.color = Color.green()
        else:
            resultado = f"{EMOJI_FAILURE} Você perdeu!"
            embed.color = Color.red()
            
        embed.description = resultado
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="par_ou_impar", description="Jogue Par ou Ímpar!")
    async def par_ou_impar(self, interaction: Interaction, escolha: str = SlashOption(description="Você quer par ou ímpar?", choices={"Par": "par", "Ímpar": "impar"}), numero: int = SlashOption(description="Seu número (1-10)", min_value=1, max_value=10)):
        """Joga Par ou Ímpar contra o bot."""
        numero_bot = random.randint(1, 10)
        total = numero + numero_bot
        resultado_real = "par" if total % 2 == 0 else "impar"

        embed = Embed(title="Par ou Ímpar?", color=Color.random())
        embed.add_field(name="Sua Escolha", value=escolha.capitalize(), inline=True)
        embed.add_field(name="Seu Número", value=str(numero), inline=True)
        embed.add_field(name="Número do Bot", value=str(numero_bot), inline=True)
        embed.add_field(name="Total", value=str(total), inline=True)
        embed.add_field(name="Resultado", value=resultado_real.capitalize(), inline=True)

        if resultado_real == escolha.lower():
            embed.description = f"{EMOJI_SUCCESS} Você venceu!"
            embed.color = Color.green()
        else:
            embed.description = f"{EMOJI_FAILURE} Você perdeu!"
            embed.color = Color.red()
            
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="adivinhe_numero", description="Tente adivinhar o número que estou pensando (1-100)!",) 
    async def adivinhe_numero(self, interaction: Interaction):
        """Inicia um mini-game de adivinhar o número."""
        # TODO: Implementar view para adivinhação interativa com dicas
        numero_secreto = random.randint(1, 100)
        await interaction.response.send_message(f"{EMOJI_QUESTION} Estou pensando em um número entre 1 e 100... (WIP: Jogo interativo em breve! O número era {numero_secreto})", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="cara_coroa", description="Jogue cara ou coroa!")
    async def cara_coroa(self, interaction: Interaction):
        """Lança uma moeda virtual."""
        resultado = random.choice(["Cara

👑", "Coroa 🪙"])
        embed = Embed(title="🪙 Cara ou Coroa?", description=f"A moeda caiu em: **{resultado}**", color=Color.random())
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="roleta_russa", description="Tente a sorte na roleta russa (1/6 chance)!")
    async def roleta_russa(self, interaction: Interaction):
        """Simula uma roleta russa com 1 bala em 6 câmaras."""
        await interaction.response.defer()
        await asyncio.sleep(1) # Suspense...
        if random.randint(1, 6) == 1:
            resultado = f"💥 BANG! {EMOJI_FAILURE} Você perdeu!"
            color = Color.red()
        else:
            resultado = f"🎉 Ufa! {EMOJI_SUCCESS} Você sobreviveu!"
            color = Color.green()
        embed = Embed(title="🔫 Roleta Russa", description=resultado, color=color)
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="numero_maior", description="Veja quem escolhe o número maior (1-100)!")
    async def numero_maior(self, interaction: Interaction, numero: int = SlashOption(description="Seu número", min_value=1, max_value=100)):
        """Compara seu número com um número aleatório do bot."""
        bot_num = random.randint(1, 100)
        embed = Embed(title="🎲 Número Maior", color=Color.random())
        embed.add_field(name="Sua Escolha", value=str(numero), inline=True)
        embed.add_field(name="Escolha do Bot", value=str(bot_num), inline=True)

        if numero > bot_num:
            resultado = f"{EMOJI_CELEBRATE} Você venceu!"
            embed.color = Color.green()
        elif numero < bot_num:
            resultado = f"{EMOJI_FAILURE} Você perdeu!"
            embed.color = Color.red()
        else:
            resultado = f"🤝 Empate!"
            embed.color = Color.light_grey()
            
        embed.description = resultado
        await interaction.response.send_message(embed=embed)

    # --- Adicionar mais jogos --- 
    # - Jogo da Velha (Tic Tac Toe) interativo
    # - Connect 4 interativo
    # - Campo Minado
    # - Blackjack (21)
    # - Caça-níqueis (Slot Machine)
    # - Anagrama
    # - Wordle

# Função setup para carregar a cog
def setup(bot):
    """Adiciona a cog Jogos ao bot."""
    bot.add_cog(Jogos(bot))
