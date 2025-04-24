# COG Utilitários com 12 comandos úteis

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, Embed, ui
import random
import secrets
import math
import aiohttp

class SugestaoModal(ui.Modal):
    def __init__(self):
        super().__init__("Sugestão para o bot")
        self.titulo = ui.TextInput(label="Título da sugestão", placeholder="Digite aqui...", required=True, max_length=100)
        self.descricao = ui.TextInput(label="Descrição", style=nextcord.TextInputStyle.paragraph, placeholder="Explique sua sugestão", required=True, max_length=300)
        self.add_item(self.titulo)
        self.add_item(self.descricao)

    async def callback(self, interaction: Interaction):
        embed = Embed(title="📩 Nova Sugestão Recebida", color=0x2ecc71)
        embed.add_field(name="Título", value=self.titulo.value, inline=False)
        embed.add_field(name="Descrição", value=self.descricao.value, inline=False)
        embed.set_footer(text=f"Enviado por {interaction.user}")
        await interaction.response.send_message("Sugestão enviada com sucesso!", ephemeral=True)
        canal_logs = nextcord.utils.get(interaction.guild.text_channels, name="sugestoes")
        if canal_logs:
            await canal_logs.send(embed=embed)

class Utilitarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quotes = [
            "A persistência realiza o impossível.",
            "O sucesso é a soma de pequenos esforços repetidos todos os dias.",
            "Não sabendo que era impossível, foi lá e fez.",
            "Coragem é resistência ao medo, domínio do medo, e não ausência do medo.",
            "Grandes mentes discutem ideias; mentes medianas discutem eventos; mentes pequenas discutem pessoas.",
            "Seja a mudança que você quer ver no mundo.",
            "A vida é 10% o que acontece com você e 90% como você reage.",
            "A melhor maneira de prever o futuro é criá-lo.",
            "Você nunca será velho demais para definir outro objetivo ou sonhar um novo sonho.",
            "A mente que se abre a uma nova ideia jamais voltará ao seu tamanho original.",
            "Tudo o que um sonho precisa para ser realizado é alguém que acredite que ele possa ser realizado.",
            "Só se pode alcançar um grande êxito quando nos mantemos fiéis a nós mesmos.",
            "O sucesso nasce do querer, da determinação e persistência em se chegar a um objetivo.",
            "A única maneira de fazer um excelente trabalho é amar o que você faz.",
            "Você é mais forte do que pensa.",
            "Acredite no seu potencial.",
            "A sua única limitação é aquela que você aceita.",
            "Transforme seus obstáculos em aprendizado.",
            "Não pare até se orgulhar.",
            "Desistir não é uma opção.",
            "O melhor ainda está por vir.",
            "Você está exatamente onde precisa estar.",
            "Pequenos passos também te levam ao destino.",
            "A ação é o antídoto do medo.",
            "Você não precisa ser perfeito, só persistente."
        ]

        self.curiosidades = [
            "Polvos têm três corações e sangue azul.",
            "O corpo humano brilha no escuro (mas nossos olhos não percebem).",
            "O mel nunca estraga.",
            "Bananas são tecnicamente frutas vermelhas.",
            "Existem mais estrelas no universo do que grãos de areia na Terra.",
            "Os cavalos-marinhos são os únicos animais onde os machos engravidam.",
            "A Terra não é perfeitamente redonda.",
            "Formigas não dormem.",
            "O cérebro humano é mais ativo à noite do que durante o dia.",
            "O DNA humano e o da banana são 60% parecidos.",
            "Os flamingos nascem cinzas.",
            "O tubarão é mais velho que as árvores.",
            "Existe um tipo de água viva imortal.",
            "O corpo humano tem ouro (em pequenas quantidades).",
            "O nariz humano pode detectar mais de 1 trilhão de odores.",
            "As abelhas podem reconhecer rostos humanos.",
            "Cada pessoa tem uma impressão de língua única.",
            "A Lua já teve atmosfera.",
            "O sol representa 99,86% da massa do sistema solar.",
            "O kiwi é uma ave, não só uma fruta.",
            "O dia em Vênus é mais longo que o ano.",
            "Os olhos da lula gigante são do tamanho de bolas de basquete.",
            "Existe uma ilha dentro de um lago dentro de uma ilha dentro de um lago dentro de uma ilha.",
            "Os dragões-de-komodo podem se reproduzir sem acasalamento.",
            "O calor do núcleo da Terra é tão intenso quanto a superfície do Sol."
        ]

    @commands.slash_command(name="calculadora", description="Resolve uma expressão matemática básica.")
    async def calculadora(self, interaction: Interaction, expressao: str):
        try:
            resultado = eval(expressao, {"__builtins__": None, "math": math}, {})
            await interaction.response.send_message(f"🧮 Resultado: `{resultado}`")
        except Exception:
            await interaction.response.send_message("❌ Expressão inválida.")

    @commands.slash_command(name="clima", description="Mostra o clima atual de uma cidade.")
    async def clima(self, interaction: Interaction, cidade: str):
        api_key = os.getenv("OPENWEATHER_API")
        url = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={api_key}&units=metric&lang=pt_br"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                data = await r.json()
                if data.get("cod") != 200:
                    await interaction.response.send_message("Cidade não encontrada.")
                    return
                embed = Embed(title=f"🌤️ Clima em {cidade.title()}", color=0x3498db)
                embed.add_field(name="Temperatura", value=f"{data['main']['temp']}°C")
                embed.add_field(name="Descrição", value=data['weather'][0]['description'].capitalize())
                embed.add_field(name="Umidade", value=f"{data['main']['humidity']}%")
                await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="dado", description="Rola um dado com X lados")
    async def dado(self, interaction: Interaction, lados: int = 6):
        if lados <= 1:
            await interaction.response.send_message("Número de lados inválido.")
        else:
            numero = random.randint(1, lados)
            await interaction.response.send_message(f"🎲 Você rolou: **{numero}**")

    @commands.slash_command(name="cronometro", description="Inicia um cronômetro temporizado")
    async def cronometro(self, interaction: Interaction, segundos: int):
        await interaction.response.send_message(f"⏱️ Cronômetro iniciado por {segundos}s...")
        await asyncio.sleep(segundos)
        await interaction.followup.send("⏰ Tempo encerrado!")

    @commands.slash_command(name="enquete", description="Cria uma enquete com até 5 opções")
    async def enquete(self, interaction: Interaction, pergunta: str, opcoes: str):
        opcoes_lista = [x.strip() for x in opcoes.split(",")][:5]
        if len(opcoes_lista) < 2:
            await interaction.response.send_message("Você precisa de pelo menos duas opções.")
            return
        embed = Embed(title="📊 Enquete", description=pergunta, color=0xf1c40f)
        botoes = ui.View()
        for i, opcao in enumerate(opcoes_lista):
            btn = ui.Button(label=opcao, custom_id=f"vote_{i}")
            async def votar_callback(inter, index=i):
                await inter.response.send_message(f"✅ Voto computado para: **{opcoes_lista[index]}**", ephemeral=True)
            btn.callback = votar_callback
            botoes.add_item(btn)
        await interaction.response.send_message(embed=embed, view=botoes)

    @commands.slash_command(name="github", description="Mostra info de um repositório do GitHub")
    async def github(self, interaction: Interaction, repositorio: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/repos/{repositorio}") as r:
                if r.status != 200:
                    await interaction.response.send_message("❌ Repositório não encontrado.")
                    return
                data = await r.json()
                embed = Embed(title=data['full_name'], description=data['description'], url=data['html_url'], color=0x3333ff)
                embed.add_field(name="⭐ Stars", value=data['stargazers_count'])
                embed.add_field(name="🔀 Forks", value=data['forks_count'])
                embed.set_footer(text="GitHub")
                await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="contagem", description="Faz uma contagem regressiva")
    async def contagem(self, interaction: Interaction, segundos: int):
        if segundos > 15:
            await interaction.response.send_message("⚠️ Limite de 15 segundos.")
            return
        msg = await interaction.response.send_message(f"Contagem iniciada: {segundos}s")
        for i in range(segundos - 1, 0, -1):
            await asyncio.sleep(1)
            await msg.edit(content=f"{i}s...")
        await asyncio.sleep(1)
        await msg.edit(content="🎉 Tempo encerrado!")

    @commands.slash_command(name="quote", description="Receba uma citação aleatória")
    async def quote(self, interaction: Interaction):
        await interaction.response.send_message(f"📜 *{random.choice(self.quotes)}*")

    @commands.slash_command(name="numero_aleatorio", description="Gera um número entre dois valores")
    async def numero_aleatorio(self, interaction: Interaction, minimo: int, maximo: int):
        if minimo >= maximo:
            await interaction.response.send_message("⚠️ O mínimo deve ser menor que o máximo.")
        else:
            await interaction.response.send_message(f"🎲 Número gerado: {random.randint(minimo, maximo)}")

    @commands.slash_command(name="sugestao", description="Envie uma sugestão para o bot")
    async def sugestao(self, interaction: Interaction):
        await interaction.response.send_modal(SugestaoModal())

    @commands.slash_command(name="senha", description="Gera uma senha aleatória segura")
    async def senha(self, interaction: Interaction, tamanho: int = 12):
        if tamanho < 4 or tamanho > 32:
            await interaction.response.send_message("Escolha um tamanho entre 4 e 32 caracteres.")
            return
        caracteres = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"
        senha = ''.join(secrets.choice(caracteres) for _ in range(tamanho))
        await interaction.response.send_message(f"🔐 Sua senha gerada: `{senha}`")

    @commands.slash_command(name="curiosidade", description="Veja uma curiosidade aleatória")
    async def curiosidade(self, interaction: Interaction):
        await interaction.response.send_message(f"🧠 {random.choice(self.curiosidades)}")

def setup(bot):
    bot.add_cog(Utilitarios(bot))
