import nextcord
from nextcord import Interaction, Embed, ButtonStyle
from nextcord.ui import View, Button
from nextcord.ext import commands, application_commands
import random
import sqlite3
import asyncio

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

    @nextcord.slash_command(name="quiz", description="Inicia um quiz de anime!")
    async def quiz(self, interaction: Interaction):
        quizzes = [
            {
                "pergunta": "Quem é o protagonista de One Piece?",
                "opcoes": ["Zoro", "Luffy", "Naruto", "Ichigo"],
                "resposta": "Luffy",
                "imagem": "https://static.wikia.nocookie.net/onepiece/images/0/0f/Monkey_D._Luffy_Anime_Pre_Timeskip_Infobox.png"
            },
            {
                "pergunta": "Qual desses é um Pokémon tipo fogo?",
                "opcoes": ["Bulbasaur", "Squirtle", "Charmander", "Pikachu"],
                "resposta": "Charmander",
                "imagem": "https://assets.pokemon.com/assets/cms2/img/pokedex/full/004.png"
            },
        ]
        embed = Embed(title="🧠 Quiz Anime", description=quizzes[0]["pergunta"], color=0x3498db)
        embed.set_image(url=quizzes[0]["imagem"])
        await interaction.response.send_message(embed=embed, view=QuizView(interaction, quizzes))

    @nextcord.slash_command(name="forca", description="Jogue forca com o bot!")
    async def forca(self, interaction: Interaction):
        palavras = ["python", "discord", "anime", "programacao", "bot"]
        palavra = random.choice(palavras)
        exibida = ["_" for _ in palavra]
        await interaction.response.send_message(f"A palavra é: {' '.join(exibida)}")
(⚠ Este jogo ainda está em construção.)")

    @nextcord.slash_command(name="pedra_papel_tesoura", description="Jogue Pedra, Papel ou Tesoura!")
    async def pedra_papel_tesoura(self, interaction: Interaction, escolha: str = SlashOption(choices=["pedra", "papel", "tesoura"])):
        opcoes = ["pedra", "papel", "tesoura"]
        escolha_bot = random.choice(opcoes)
        if escolha == escolha_bot:
            resultado = "Empate!"
        elif (escolha == "pedra" and escolha_bot == "tesoura") or              (escolha == "papel" and escolha_bot == "pedra") or              (escolha == "tesoura" and escolha_bot == "papel"):
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

    @nextcord.slash_command(name="numero_maior", description="Veja quem escolhe o número maior!")
    async def numero_maior(self, interaction: Interaction, numero: int = SlashOption(min_value=1, max_value=100)):
        bot_num = random.randint(1, 100)
        if numero > bot_num:
            resultado = "🎉 Você venceu!"
        elif numero < bot_num:
            resultado = "❌ Você perdeu!"
        else:
            resultado = "🤝 Empate!"
        await interaction.response.send_message(f"Você: {numero} | Bot: {bot_num}
{resultado}")

def setup(bot):
    bot.add_cog(JogosExtras(bot))
