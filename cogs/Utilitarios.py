import os
import random
import secrets
import math
import asyncio
import aiohttp
import nextcord
from nextcord import Interaction, Embed, SlashOption
from nextcord.ext import commands
from nextcord import ui

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
        else:
            # Enviar para o canal atual se o canal de sugestões não existir
            await interaction.channel.send("⚠️ Canal #sugestoes não encontrado. Criando sugestão aqui:", embed=embed)

class EnqueteView(ui.View):
    def __init__(self, opcoes_lista):
        super().__init__(timeout=None)
        self.votos = {i: 0 for i in range(len(opcoes_lista))}
        self.opcoes = opcoes_lista
        self.votantes = set()
        
        # Adicionar botões com callbacks conectados corretamente
        for i, opcao in enumerate(opcoes_lista):
            button = ui.Button(label=opcao, custom_id=f"vote_{i}")
            button.callback = self.create_callback(i)
            self.add_item(button)
            
    def create_callback(self, index):
        async def callback(interaction: Interaction):
            # Verificar se o usuário já votou
            if interaction.user.id in self.votantes:
                await interaction.response.send_message("Você já votou nesta enquete!", ephemeral=True)
                return
                
            # Registrar voto
            self.votos[index] += 1
            self.votantes.add(interaction.user.id)
            
            await interaction.response.send_message(f"✅ Voto computado para: **{self.opcoes[index]}**", ephemeral=True)
            
        return callback

class Utilitarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quotes = [  # 25 citações
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
        self.curiosidades = [  # 25 curiosidades
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
        # Usar uma abordagem mais segura que eval()
        try:
            # Lista de operações permitidas
            allowed_names = {
                'abs': abs, 'round': round,
                'min': min, 'max': max,
                'sum': sum
            }
            
            # Adicionar funções matemáticas seguras
            for name in dir(math):
                if not name.startswith('_'):
                    allowed_names[name] = getattr(math, name)
                    
            # Compilar a expressão com restrições
            code = compile(expressao, "<string>", "eval")
            
            # Verificar se há nomes não permitidos
            for name in code.co_names:
                if name not in allowed_names:
                    raise NameError(f"O uso de '{name}' não é permitido")
                    
            # Avaliar a expressão com o dicionário restrito
            resultado = eval(code, {"__builtins__": {}}, allowed_names)
            await interaction.response.send_message(f"🧮 Resultado: `{resultado}`")
        except Exception as e:
            await interaction.response.send_message(f"❌ Expressão inválida: {str(e)}")

    @commands.slash_command(name="clima", description="Mostra o clima atual de uma cidade.")
    async def clima(self, interaction: Interaction, cidade: str):
        api_key = os.getenv("OPENWEATHER_API")
        if not api_key:
            await interaction.response.send_message("❌ API de clima não configurada.")
            return
            
        await interaction.response.defer()  # Adicionado para operações que podem demorar
        
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={api_key}&units=metric&lang=pt_br"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    if r.status != 200:
                        await interaction.followup.send("Cidade não encontrada.")
                        return
                        
                    data = await r.json()
                    embed = Embed(title=f"🌤️ Clima em {cidade.title()}", color=0x3498db)
                    embed.add_field(name="Temperatura", value=f"{data['main']['temp']}°C")
                    embed.add_field(name="Sensação", value=f"{data['main']['feels_like']}°C")
                    embed.add_field(name="Descrição", value=data['weather'][0]['description'].capitalize())
                    embed.add_field(name="Umidade", value=f"{data['main']['humidity']}%")
                    embed.add_field(name="Vento", value=f"{data['wind']['speed']} m/s")
                    
                    # Adicionar ícone do clima
                    icon_code = data['weather'][0]['icon']
                    embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon_code}@2x.png")
                    
                    await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao buscar clima: {str(e)}")

    @commands.slash_command(name="dado", description="Rola um dado com X lados")
    async def dado(self, interaction: Interaction, lados: int = SlashOption(description="Número de lados do dado", min_value=2, max_value=1000, default=6)):
        numero = random.randint(1, lados)
        await interaction.response.send_message(f"🎲 Você rolou um d{lados}: **{numero}**")

    @commands.slash_command(name="cronometro", description="Inicia um cronômetro temporizado")
    async def cronometro(self, interaction: Interaction, segundos: int = SlashOption(description="Duração em segundos", min_value=1, max_value=300)):
        if segundos > 60:
            await interaction.response.send_message(f"⏱️ Cronômetro iniciado por {segundos}s... Você será notificado quando terminar.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⏱️ Cronômetro iniciado por {segundos}s...")
            
        await asyncio.sleep(segundos)
        
        try:
            await interaction.followup.send(f"⏰ <@{interaction.user.id}> Tempo encerrado!")
        except Exception as e:
            print(f"Erro ao enviar notificação de cronômetro: {e}")

    @commands.slash_command(name="enquete", description="Cria uma enquete com até 5 opções")
    async def enquete(self, interaction: Interaction, pergunta: str, opcoes: str):
        opcoes_lista = [x.strip() for x in opcoes.split(",")][:5]
        if len(opcoes_lista) < 2:
            await interaction.response.send_message("Você precisa de pelo menos duas opções.", ephemeral=True)
            return
            
        embed = Embed(title="📊 Enquete", description=pergunta, color=0xf1c40f)
        for i, opcao in enumerate(opcoes_lista):
            embed.add_field(name=f"Opção {i+1}", value=opcao, inline=False)
            
        view = EnqueteView(opcoes_lista)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.slash_command(name="quote", description="Receba uma citação aleatória")
    async def quote(self, interaction: Interaction):
        await interaction.response.send_message(f"📜 *{random.choice(self.quotes)}*")

    @commands.slash_command(name="curiosidade", description="Veja uma curiosidade aleatória")
    async def curiosidade(self, interaction: Interaction):
        await interaction.response.send_message(f"🧠 {random.choice(self.curiosidades)}")

    @commands.slash_command(name="sugestao", description="Envie uma sugestão para o bot")
    async def sugestao(self, interaction: Interaction):
        await interaction.response.send_modal(SugestaoModal())

    @commands.slash_command(name="numero_aleatorio", description="Gera um número entre dois valores")
    async def numero_aleatorio(self, interaction: Interaction, 
                              minimo: int = SlashOption(description="Valor mínimo", default=1), 
                              maximo: int = SlashOption(description="Valor máximo", default=100)):
        if minimo >= maximo:
            await interaction.response.send_message("⚠️ O mínimo deve ser menor que o máximo.", ephemeral=True)
        else:
            await interaction.response.send_message(f"🎲 Número gerado: **{random.randint(minimo, maximo)}**")

    @commands.slash_command(name="senha", description="Gera uma senha aleatória segura")
    async def senha(self, interaction: Interaction, 
                   tamanho: int = SlashOption(description="Tamanho da senha", min_value=4, max_value=32, default=12),
                   incluir_maiusculas: bool = SlashOption(description="Incluir letras maiúsculas", default=True),
                   incluir_numeros: bool = SlashOption(description="Incluir números", default=True),
                   incluir_simbolos: bool = SlashOption(description="Incluir símbolos", default=True)):
        # Construir conjunto de caracteres com base nas opções
        caracteres = "abcdefghijklmnopqrstuvwxyz"
        if incluir_maiusculas:
            caracteres += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if incluir_numeros:
            caracteres += "0123456789"
        if incluir_simbolos:
            caracteres += "!@#$%^&*()-_=+[]{}|;:,.<>?"
            
        # Gerar senha
        senha = ''.join(secrets.choice(caracteres) for _ in range(tamanho))
        
        # Enviar como mensagem efêmera para maior segurança
        await interaction.response.send_message(f"🔐 Sua senha gerada: `{senha}`", ephemeral=True)

    @commands.slash_command(name="contagem", description="Faz uma contagem regressiva")
    async def contagem(self, interaction: Interaction, segundos: int = SlashOption(description="Duração em segundos", min_value=1, max_value=15)):
        await interaction.response.defer()
        msg = await interaction.followup.send(f"⏱️ Contagem iniciada: {segundos}s")
        
        for i in range(segundos - 1, 0, -1):
            await asyncio.sleep(1)
            await msg.edit(content=f"⏱️ {i}s...")
            
        await asyncio.sleep(1)
        await msg.edit(content="🎉 Tempo encerrado!")

    @commands.slash_command(name="github", description="Mostra info de um repositório do GitHub")
    async def github(self, interaction: Interaction, repositorio: str):
        await interaction.response.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.github.com/repos/{repositorio}") as r:
                    if r.status != 200:
                        await interaction.followup.send("❌ Repositório não encontrado.")
                        return
                        
                    data = await r.json()
                    embed = Embed(title=data['full_name'], description=data['description'], url=data['html_url'], color=0x3333ff)
                    
                    # Adicionar mais informações úteis
                    embed.add_field(name="⭐ Stars", value=data['stargazers_count'])
                    embed.add_field(name="🔀 Forks", value=data['forks_count'])
                    embed.add_field(name="👀 Watchers", value=data['watchers_count'])
                    embed.add_field(name="🔧 Linguagem", value=data['language'] or "N/A")
                    embed.add_field(name="🔄 Última atualização", value=data['updated_at'].split('T')[0])
                    
                    # Adicionar avatar do dono
                    if 'owner' in data and 'avatar_url' in data['owner']:
                        embed.set_thumbnail(url=data['owner']['avatar_url'])
                        
                    embed.set_footer(text="GitHub")
                    await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao buscar informações: {str(e)}")

    # Novo comando para tradução
    @commands.slash_command(name="traduzir", description="Traduz um texto para outro idioma")
    async def traduzir(self, interaction: Interaction, texto: str, idioma: str = SlashOption(
        description="Idioma de destino",
        choices={"Inglês": "en", "Espanhol": "es", "Francês": "fr", "Alemão": "de", "Italiano": "it", "Japonês": "ja"}
    )):
        await interaction.response.defer()
        
        try:
            api_key = os.getenv("TRANSLATION_API")
            if not api_key:
                # Simulação de tradução para demonstração (em produção, use uma API real)
                traducoes = {
                    "en": "This is a simulated translation (English)",
                    "es": "Esta es una traducción simulada (Español)",
                    "fr": "Ceci est une traduction simulée (Français)",
                    "de": "Dies ist eine simulierte Übersetzung (Deutsch)",
                    "it": "Questa è una traduzione simulata (Italiano)",
                    "ja": "これはシミュレートされた翻訳です (日本語)"
                }
                traducao = traducoes.get(idioma, "Tradução simulada")
                await interaction.followup.send(f"⚠️ API de tradução não configurada. Usando simulação:\n\n{traducao}")
            else:
                # Aqui você implementaria a chamada real para a API de tradução
                await interaction.followup.send(f"🌐 Texto traduzido para {idioma}:\n\n{texto} (tradução simulada)")
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao traduzir: {str(e)}")

def setup(bot):
    bot.add_cog(Utilitarios(bot))
