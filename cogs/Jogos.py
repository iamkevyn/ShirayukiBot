import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Embed, ButtonStyle, SlashOption
from nextcord.ui import View, Button
import random
import sqlite3

class QuizView(View):
    def __init__(self, interaction, quizzes):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.quizzes = quizzes
        self.index = 0
        self.score = 0
        self.user_id = interaction.user.id
        self.username = interaction.user.name
        for opcao in self.quizzes[0]['opcoes']:
            self.add_item(Button(label=opcao, style=ButtonStyle.primary, custom_id=opcao))

    async def interaction_check(self, interaction: Interaction):
        return interaction.user.id == self.user_id

    async def on_timeout(self):
        await self.interaction.followup.send("⏰ Tempo esgotado!", ephemeral=True)

    async def callback(self, interaction: Interaction):
        resposta = interaction.data['custom_id']
        correta = self.quizzes[self.index]['resposta']
        if resposta == correta:
            self.score += 1
            feedback = "✅ Resposta correta!"
        else:
            feedback = f"❌ Resposta errada! A correta era **{correta}**."
        self.index += 1
        if self.index >= len(self.quizzes):
            embed = Embed(title="Resultado Final", description=f"Você acertou {self.score} de {len(self.quizzes)} perguntas.", color=0x2ecc71)
            self.salvar_pontuacao()
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            embed = Embed(title="🧠 Quiz Anime", description=self.quizzes[self.index]['pergunta'], color=0x3498db)
            embed.set_image(url=self.quizzes[self.index]['imagem'])
            self.clear_items()
            for opcao in self.quizzes[self.index]['opcoes']:
                self.add_item(Button(label=opcao, style=ButtonStyle.primary, custom_id=opcao))
            await interaction.response.edit_message(embed=embed, view=self)

    def salvar_pontuacao(self):
        con = sqlite3.connect("/mnt/data/quiz_ranking.db")
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS ranking (user_id INTEGER PRIMARY KEY, username TEXT, pontos INTEGER)")
        cur.execute("SELECT pontos FROM ranking WHERE user_id = ?", (self.user_id,))
        resultado = cur.fetchone()
        if resultado:
            if self.score > resultado[0]:
                cur.execute("UPDATE ranking SET pontos = ?, username = ? WHERE user_id = ?", (self.score, self.username, self.user_id))
        else:
            cur.execute("INSERT INTO ranking (user_id, username, pontos) VALUES (?, ?, ?)", (self.user_id, self.username, self.score))
        con.commit()
        con.close()

class JogosExtras(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
@nextcord.slash_command(name="pedra_papel_tesoura", description="Jogue Pedra, Papel ou Tesoura!")
async def pedra_papel_tesoura(self, interaction: Interaction, escolha: str = SlashOption(choices=["pedra", "papel", "tesoura"])):
    opcoes = ["pedra", "papel", "tesoura"]
    escolha_bot = random.choice(opcoes)
    if escolha == escolha_bot:
        resultado = "Empate!"
    elif (escolha == "pedra" and escolha_bot == "tesoura") or \
         (escolha == "papel" and escolha_bot == "pedra") or \
         (escolha == "tesoura" and escolha_bot == "papel"):
        resultado = "Você ganhou!"
    else:
        resultado = "Você perdeu!"
    await interaction.response.send_message(f"Você escolheu {escolha}, eu escolhi {escolha_bot}. {resultado}")

@nextcord.slash_command(name="par_ou_impar", description="Jogue Par ou Ímpar!")
async def par_ou_impar(self, interaction: Interaction, escolha: str = SlashOption(choices=["par", "ímpar"]), numero: int = SlashOption(min_value=1, max_value=10)):
    numero_bot = random.randint(1, 10)
    total = numero + numero_bot
    resultado = "par" if total % 2 == 0 else "ímpar"
    if resultado == escolha.lower():
        await interaction.response.send_message(f"Você escolheu {escolha} e jogou {numero}. Eu joguei {numero_bot}. Deu {resultado}. Você venceu!")
    else:
        await interaction.response.send_message(f"Você escolheu {escolha} e jogou {numero}. Eu joguei {numero_bot}. Deu {resultado}. Você perdeu!")

@nextcord.slash_command(name="dado", description="Jogue um dado de 6 lados!")
async def dado(self, interaction: Interaction):
    resultado = random.randint(1, 6)
    await interaction.response.send_message(f"🎲 Você tirou {resultado} no dado!")

@nextcord.slash_command(name="cara_ou_coroa", description="Jogue cara ou coroa!")
async def cara_ou_coroa(self, interaction: Interaction):
    resultado = random.choice(["cara", "coroa"])
    await interaction.response.send_message(f"A moeda caiu em: **{resultado.upper()}**!")

@nextcord.slash_command(name="roleta_russa", description="Tente a sorte na roleta russa!")
async def roleta_russa(self, interaction: Interaction):
    resultado = random.choice(["💥 BANG! Você perdeu!", "🎉 Ufa! Você sobreviveu!"])
    await interaction.response.send_message(resultado)

@nextcord.slash_command(name="jokenpo", description="Jogue pedra, papel ou tesoura com emojis!")
async def jokenpo(self, interaction: Interaction, escolha: str = SlashOption(choices=["✊", "🖐", "✌"])):
    opcoes = ["✊", "🖐", "✌"]
    bot_escolha = random.choice(opcoes)
    resultado = "Empate!"
    if (escolha == "✊" and bot_escolha == "✌") or \
       (escolha == "🖐" and bot_escolha == "✊") or \
       (escolha == "✌" and bot_escolha == "🖐"):
        resultado = "Você venceu!"
    elif escolha != bot_escolha:
        resultado = "Você perdeu!"
    await interaction.response.send_message(f"Você: {escolha} | Bot: {bot_escolha} → **{resultado}**")

@nextcord.slash_command(name="numero_maior", description="Veja quem escolhe o número maior!")
async def numero_maior(self, interaction: Interaction, numero: int = SlashOption(min_value=1, max_value=100)):
    bot_num = random.randint(1, 100)
    if numero > bot_num:
        resultado = "🎉 Você venceu!"
    elif numero < bot_num:
        resultado = "❌ Você perdeu!"
    else:
        resultado = "🤝 Empate!"
    await interaction.response.send_message(f"Você: {numero} | Bot: {bot_num}\n{resultado}")
    @nextcord.slash_command(name="forca", description="Jogue forca com o bot!")
    async def forca(self, interaction: Interaction):
        palavras = ["python", "discord", "anime", "programacao", "bot"]
        palavra = random.choice(palavras)
        exibida = ["_" for _ in palavra]
        await interaction.response.send_message(f"A palavra é: {' '.join(exibida)}\n(⚠ Este jogo ainda está em construção.)")

    @nextcord.slash_command(name="adivinhe_palavra", description="Adivinhe a palavra com dica")
    async def adivinhe_palavra(self, interaction: Interaction):
        palavras = [("tem orelhas grandes", "coelho"), ("gosta de peixe", "gato"), ("late", "cachorro")]
        dica, resposta = random.choice(palavras)
        await interaction.response.send_message(f"Dica: {dica}\n(⚠ Este jogo ainda está em construção)")

    @nextcord.slash_command(name="jogo_da_memoria", description="Teste sua memória com números")
    async def jogo_da_memoria(self, interaction: Interaction):
        numeros = [str(random.randint(0, 9)) for _ in range(5)]
        numeros_str = " ".join(numeros)
        await interaction.response.send_message(f"Memorize estes números: {numeros_str} (⚠ Jogo simplificado)")

    @nextcord.slash_command(name="cobrinha", description="Jogo da cobrinha (em breve)")
    async def cobrinha(self, interaction: Interaction):
        await interaction.response.send_message("🐍 Jogo da cobrinha está em construção.")

    @nextcord.slash_command(name="jogo_da_velha", description="Jogo da velha multijogador (em construção)")
    async def jogo_da_velha(self, interaction: Interaction):
        await interaction.response.send_message("🔧 Jogo da velha online será implementado em breve.")

    @nextcord.slash_command(name="stop_game", description="Jogo do Stop (em breve)")
    async def stop_game(self, interaction: Interaction):
        await interaction.response.send_message("🛑 Jogo do Stop está em construção.")

    @nextcord.slash_command(name="cara_ou_coroa_emoji", description="Cara ou coroa com emoji")
    async def cara_ou_coroa_emoji(self, interaction: Interaction):
        resultado = random.choice(["🪙 Cara", "🪙 Coroa"])
        await interaction.response.send_message(f"O resultado foi: **{resultado}**")

    @nextcord.slash_command(name="adivinha_cor", description="Tente adivinhar a cor que estou pensando!")
    async def adivinha_cor(self, interaction: Interaction, cor: str = SlashOption(description="Digite uma cor")):
        cores = ["vermelho", "azul", "verde", "amarelo", "roxo"]
        cor_certa = random.choice(cores)
        if cor.lower() == cor_certa:
            await interaction.response.send_message(f"🎉 Isso mesmo! A cor era {cor_certa}.")
        else:
            await interaction.response.send_message(f"❌ Errado! Eu estava pensando em {cor_certa}.")

    @nextcord.slash_command(name="palpite_anime", description="Tente adivinhar o anime pela dica!")
    async def palpite_anime(self, interaction: Interaction):
        dicas = [
            ("Sou um ninja que sonha em ser Hokage", "Naruto"),
            ("Tenho um irmão e buscamos a Pedra Filosofal", "Fullmetal Alchemist"),
            ("Meu cabelo é rosa e uso fogo", "Fairy Tail"),
        ]
        dica, resposta = random.choice(dicas)
        await interaction.response.send_message(f"Dica: {dica}\nQual é o anime? (⚠ Em construção)")

def setup(bot):
    bot.add_cog(JogosExtras(bot))
