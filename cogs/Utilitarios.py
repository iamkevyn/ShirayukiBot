# /home/ubuntu/ShirayukiBot/cogs/Utilitarios.py
# Cog para comandos utilitários diversos.

import os
import random
import secrets
import math
import asyncio
import aiohttp
import nextcord
from nextcord import Interaction, Embed, SlashOption, Color, File
from nextcord.ext import commands, tasks
from nextcord import ui
import datetime
import pytz # Para fusos horários
import qrcode # Para gerar QR codes
from io import BytesIO
# from googletrans import Translator # Considerar alternativa ou API paga

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
REMINDERS_FILE = "/home/ubuntu/ShirayukiBot/data/reminders.json"
SUGGESTIONS_CHANNEL_NAME = "sugestoes" # Nome do canal para enviar sugestões
DEFAULT_TIMEZONE = "America/Sao_Paulo"

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

def save_json_data(file_path, data):
    """Salva dados em um arquivo JSON."""
    ensure_dir_exists(file_path)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"[ERRO] Falha ao salvar {file_path}: {e}")

# --- Views e Modals --- 

class SugestaoModal(ui.Modal):
    def __init__(self, suggestions_channel_name: str):
        super().__init__("Sugestão para o Bot")
        self.suggestions_channel_name = suggestions_channel_name
        self.titulo = ui.TextInput(label="Título da sugestão", placeholder="Ex: Novo comando de música", required=True, max_length=100)
        self.descricao = ui.TextInput(label="Descrição detalhada", style=nextcord.TextInputStyle.paragraph, placeholder="Explique sua ideia, como funcionaria, etc.", required=True, max_length=1000)
        self.add_item(self.titulo)
        self.add_item(self.descricao)

    async def callback(self, interaction: Interaction):
        embed = Embed(title=f"{EMOJI_INFO} Nova Sugestão Recebida", color=Color.green())
        embed.add_field(name="Título", value=self.titulo.value, inline=False)
        embed.add_field(name="Descrição", value=self.descricao.value, inline=False)
        embed.set_footer(text=f"Enviado por {interaction.user.display_name} ({interaction.user.id})")
        embed.timestamp = datetime.datetime.utcnow()

        await interaction.response.send_message(f"{EMOJI_SUCCESS} Sugestão enviada com sucesso! Obrigado pela sua contribuição.", ephemeral=True)
        
        # Tenta encontrar o canal de sugestões
        canal_logs = nextcord.utils.get(interaction.guild.text_channels, name=self.suggestions_channel_name)
        if canal_logs:
            try:
                await canal_logs.send(embed=embed)
            except nextcord.Forbidden:
                 await interaction.followup.send(f"{EMOJI_FAILURE} Não tenho permissão para enviar a sugestão no canal #{self.suggestions_channel_name}.", ephemeral=True)
            except Exception as e:
                 await interaction.followup.send(f"{EMOJI_FAILURE} Erro ao enviar sugestão para #{self.suggestions_channel_name}: {e}", ephemeral=True)
        else:
            # Se não encontrar, avisa o usuário (não envia no canal atual para evitar spam)
            await interaction.followup.send(f"{EMOJI_WARN} Canal #{self.suggestions_channel_name} não encontrado neste servidor. A sugestão foi registrada, mas não pude enviá-la para o canal específico.", ephemeral=True)
            # Opcional: Logar a sugestão em outro lugar ou para o dono do bot via DM
            print(f"[Sugestão] {interaction.user}: {self.titulo.value} - {self.descricao.value}")

class EnqueteView(ui.View):
    def __init__(self, pergunta: str, opcoes_lista: list):
        super().__init__(timeout=None) # Enquetes não expiram por padrão
        self.pergunta = pergunta
        self.opcoes = opcoes_lista
        self.votos = {i: 0 for i in range(len(opcoes_lista))}
        self.votantes = set() # Guarda IDs de quem já votou
        self.message = None # Referência à mensagem da enquete
        self.update_buttons()

    def update_buttons(self):
        """Atualiza os botões com a contagem de votos."""
        self.clear_items()
        total_votos = sum(self.votos.values())
        for i, opcao in enumerate(self.opcoes):
            label = f"{opcao} ({self.votos[i]})"
            button = ui.Button(label=label, custom_id=f"vote_{i}", style=ButtonStyle.primary)
            button.callback = self.create_callback(i)
            self.add_item(button)
        # Adiciona botão para finalizar (opcional, talvez só para o criador?)
        # finish_button = ui.Button(label="Finalizar Enquete", custom_id="finish_poll", style=ButtonStyle.danger)
        # finish_button.callback = self.finish_poll_callback
        # self.add_item(finish_button)

    def create_callback(self, index: int):
        """Cria a função de callback para um botão de voto específico."""
        async def callback(interaction: Interaction):
            user_id = interaction.user.id
            if user_id in self.votantes:
                await interaction.response.send_message(f"{EMOJI_WARN} Você já votou nesta enquete!", ephemeral=True)
                return

            self.votos[index] += 1
            self.votantes.add(user_id)
            self.update_buttons() # Atualiza contagem nos botões
            
            # Atualiza o embed com os resultados
            embed = self.create_poll_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            # Confirmação efêmera para o votante
            await interaction.followup.send(f"{EMOJI_SUCCESS} Seu voto para **{self.opcoes[index]}** foi registrado!", ephemeral=True)
            
        return callback

    # async def finish_poll_callback(self, interaction: Interaction):
    #     # TODO: Adicionar verificação se o usuário é o criador da enquete
    #     embed = self.create_poll_embed(final=True)
    #     await interaction.response.edit_message(embed=embed, view=None)
    #     self.stop()

    def create_poll_embed(self, final: bool = False) -> Embed:
        """Cria o embed da enquete com os resultados atuais."""
        title = f"📊 Enquete{' Finalizada' if final else ''}"
        embed = Embed(title=title, description=self.pergunta, color=Color.blue())
        total_votos = sum(self.votos.values())
        
        resultados = []
        for i, opcao in enumerate(self.opcoes):
            votos_opcao = self.votos[i]
            percentual = (votos_opcao / total_votos * 100) if total_votos > 0 else 0
            resultados.append(f"**{opcao}**: {votos_opcao} voto{'s' if votos_opcao != 1 else ''} ({percentual:.1f}%)")
            
        embed.add_field(name="Resultados", value="\n".join(resultados) if resultados else "Nenhum voto ainda.", inline=False)
        embed.set_footer(text=f"Total de votos: {total_votos}")
        return embed

# --- Cog Utilitarios --- 
class Utilitarios(commands.Cog):
    """Comandos utilitários diversos para o dia a dia."""
    def __init__(self, bot):
        self.bot = bot
        self.reminders = load_json_data(REMINDERS_FILE, [])
        self.quotes = self.load_default_quotes()
        self.curiosidades = self.load_default_curiosidades()
        self.check_reminders.start() # Inicia a task de verificação de lembretes
        print(f"[DIAGNÓSTICO] Cog Utilitarios carregada.")
        print(f"[Utilitarios] {len(self.reminders)} lembretes carregados.")

    def cog_unload(self):
        """Para a task quando o cog é descarregado."""
        self.check_reminders.cancel()

    def load_default_quotes(self):
        # Retorna lista de citações padrão
        return [
            "A persistência realiza o impossível.", "O sucesso é a soma de pequenos esforços repetidos todos os dias.",
            "Não sabendo que era impossível, foi lá e fez.", "Coragem é resistência ao medo, domínio do medo, e não ausência do medo.",
            "Grandes mentes discutem ideias; mentes medianas discutem eventos; mentes pequenas discutem pessoas.",
            "Seja a mudança que você quer ver no mundo.", "A vida é 10% o que acontece com você e 90% como você reage.",
            "A melhor maneira de prever o futuro é criá-lo.", "Você nunca será velho demais para definir outro objetivo ou sonhar um novo sonho.",
            "A mente que se abre a uma nova ideia jamais voltará ao seu tamanho original.", "Tudo o que um sonho precisa para ser realizado é alguém que acredite que ele possa ser realizado.",
            "Só se pode alcançar um grande êxito quando nos mantemos fiéis a nós mesmos.", "O sucesso nasce do querer, da determinação e persistência em se chegar a um objetivo.",
            "A única maneira de fazer um excelente trabalho é amar o que você faz.", "Você é mais forte do que pensa.",
            "Acredite no seu potencial.", "A sua única limitação é aquela que você aceita.",
            "Transforme seus obstáculos em aprendizado.", "Não pare até se orgulhar.", "Desistir não é uma opção.",
            "O melhor ainda está por vir.", "Você está exatamente onde precisa estar.",
            "Pequenos passos também te levam ao destino.", "A ação é o antídoto do medo.", "Você não precisa ser perfeito, só persistente."
        ]

    def load_default_curiosidades(self):
        # Retorna lista de curiosidades padrão
        return [
            "Polvos têm três corações e sangue azul.", "O corpo humano brilha no escuro (mas nossos olhos não percebem).",
            "O mel nunca estraga.", "Bananas são tecnicamente frutas vermelhas.", "Existem mais estrelas no universo do que grãos de areia na Terra.",
            "Os cavalos-marinhos são os únicos animais onde os machos engravidam.", "A Terra não é perfeitamente redonda.",
            "Formigas não dormem.", "O cérebro humano é mais ativo à noite do que durante o dia.", "O DNA humano e o da banana são 60% parecidos.",
            "Os flamingos nascem cinzas.", "O tubarão é mais velho que as árvores.", "Existe um tipo de água viva imortal.",
            "O corpo humano tem ouro (em pequenas quantidades).", "O nariz humano pode detectar mais de 1 trilhão de odores.",
            "As abelhas podem reconhecer rostos humanos.", "Cada pessoa tem uma impressão de língua única.", "A Lua já teve atmosfera.",
            "O sol representa 99,86% da massa do sistema solar.", "O kiwi é uma ave, não só uma fruta.",
            "O dia em Vênus é mais longo que o ano.", "Os olhos da lula gigante são do tamanho de bolas de basquete.",
            "Existe uma ilha dentro de um lago dentro de uma ilha dentro de um lago dentro de uma ilha.",
            "Os dragões-de-komodo podem se reproduzir sem acasalamento.", "O calor do núcleo da Terra é tão intenso quanto a superfície do Sol."
        ]

    # --- Task de Lembretes --- 
    @tasks.loop(seconds=30) # Verifica a cada 30 segundos
    async def check_reminders(self):
        now = datetime.datetime.utcnow().timestamp()
        reminders_to_remove = []
        reminders_updated = False

        for i, reminder in enumerate(self.reminders):
            if reminder["timestamp"] <= now:
                try:
                    user = await self.bot.fetch_user(reminder["user_id"])
                    channel = await self.bot.fetch_channel(reminder["channel_id"])
                    
                    embed = Embed(title=f"{EMOJI_INFO} Lembrete!", description=reminder["message"], color=Color.orange())
                    embed.set_footer(text=f"Lembrete criado em: {datetime.datetime.fromtimestamp(reminder['created_at'], tz=pytz.utc).strftime('%d/%m/%Y %H:%M:%S UTC')}")
                    
                    # Tenta enviar no canal original, se falhar, tenta DM
                    try:
                        await channel.send(content=user.mention, embed=embed)
                    except (nextcord.Forbidden, nextcord.NotFound):
                        try:
                            await user.send(content=f"Lembrete do servidor/canal `{reminder['guild_id'] or 'DM'}/{reminder['channel_id']}`:", embed=embed)
                        except (nextcord.Forbidden, nextcord.HTTPException):
                            print(f"[ERRO Lembrete] Falha ao enviar lembrete para {user.id} (canal {reminder['channel_id']} e DM)")
                            
                    reminders_to_remove.append(i)
                    reminders_updated = True
                except Exception as e:
                    print(f"[ERRO Lembrete] Erro ao processar lembrete {i}: {e}")
                    # Considerar remover lembretes com erro persistente?
                    # reminders_to_remove.append(i)
                    # reminders_updated = True

        # Remove lembretes concluídos (iterando de trás para frente para evitar problemas de índice)
        if reminders_updated:
            for index in sorted(reminders_to_remove, reverse=True):
                del self.reminders[index]
            save_json_data(REMINDERS_FILE, self.reminders)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready() # Espera o bot estar pronto

    # --- Comandos Slash --- 

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="lembrete", description="Define um lembrete para você.")
    async def lembrete(self, interaction: Interaction, 
                       tempo: str = SlashOption(description="Tempo até o lembrete (ex: 10s, 5m, 2h, 1d)"), 
                       mensagem: str = SlashOption(description="A mensagem do lembrete")):
        """Agenda uma mensagem para ser enviada após um tempo especificado."""
        try:
            seconds = 0
            num = int(tempo[:-1])
            unit = tempo[-1].lower()
            if unit == 's': seconds = num
            elif unit == 'm': seconds = num * 60
            elif unit == 'h': seconds = num * 3600
            elif unit == 'd': seconds = num * 86400
            else: raise ValueError("Unidade de tempo inválida (use s, m, h, d)")

            if seconds <= 0:
                 raise ValueError("O tempo deve ser positivo.")
            if seconds > 30 * 86400: # Limite de 30 dias
                 raise ValueError("O tempo máximo para lembretes é de 30 dias.")

            future_timestamp = datetime.datetime.utcnow().timestamp() + seconds
            created_at = datetime.datetime.utcnow().timestamp()
            
            reminder_data = {
                "user_id": interaction.user.id,
                "channel_id": interaction.channel.id,
                "guild_id": interaction.guild.id if interaction.guild else None,
                "timestamp": future_timestamp,
                "message": mensagem,
                "created_at": created_at
            }
            self.reminders.append(reminder_data)
            save_json_data(REMINDERS_FILE, self.reminders)

            future_dt = datetime.datetime.fromtimestamp(future_timestamp, tz=pytz.utc)
            await interaction.response.send_message(f"{EMOJI_SUCCESS} Lembrete definido! Você será lembrado sobre "{mensagem}" em <t:{int(future_timestamp)}:R> (<t:{int(future_timestamp)}:f>).", ephemeral=True)

        except ValueError as e:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Formato de tempo inválido: {e}. Use números seguidos de s, m, h ou d (ex: 10m, 2h).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Erro ao definir lembrete: {e}", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="calculadora", description="Resolve uma expressão matemática básica.")
    async def calculadora(self, interaction: Interaction, expressao: str = SlashOption(description="A expressão a ser calculada")):
        """Calcula o resultado de uma expressão matemática simples."""
        try:
            allowed_chars = "0123456789+-*/(). "
            if not all(c in allowed_chars for c in expressao):
                raise ValueError("Expressão contém caracteres não permitidos.")
            
            # Avaliação segura (alternativa ao eval complexo)
            # Nota: Isso é muito limitado. Para algo mais robusto, uma biblioteca de parsing é necessária.
            # Considerar usar numexpr ou similar se precisar de mais funções.
            resultado = eval(expressao, {'__builtins__': {}}, {}) # Eval muito restrito
            
            await interaction.response.send_message(f"{EMOJI_SUCCESS} Resultado: `{expressao} = {resultado}`")
        except Exception as e:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Não foi possível calcular a expressão: `{e}`. Use apenas números e operadores básicos (+, -, *, /).", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="clima", description="Mostra o clima atual de uma cidade.")
    async def clima(self, interaction: Interaction, cidade: str = SlashOption(description="Nome da cidade")):
        """Busca e exibe informações meteorológicas de uma cidade usando OpenWeatherMap."""
        api_key = os.getenv("OPENWEATHER_API") # Certifique-se de definir esta variável de ambiente!
        if not api_key:
            await interaction.response.send_message(f"{EMOJI_FAILURE} A funcionalidade de clima não está configurada no momento (API Key ausente).", ephemeral=True)
            return
            
        await interaction.response.defer()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={api_key}&units=metric&lang=pt_br"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    data = await r.json()
                    if r.status != 200:
                        error_message = data.get("message", "Erro desconhecido")
                        await interaction.followup.send(f"{EMOJI_FAILURE} Não foi possível encontrar a cidade "{cidade}". ({error_message.capitalize()})", ephemeral=True)
                        return
                        
                    embed = Embed(title=f"🌤️ Clima em {data['name']}, {data['sys']['country']}", color=Color.blue())
                    temp = data['main']['temp']
                    feels_like = data['main']['feels_like']
                    description = data['weather'][0]['description'].capitalize()
                    humidity = data['main']['humidity']
                    wind_speed = data['wind']['speed']
                    icon_code = data['weather'][0]['icon']
                    
                    embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon_code}@2x.png")
                    embed.add_field(name="Condição", value=description, inline=True)
                    embed.add_field(name="🌡️ Temperatura", value=f"{temp}°C", inline=True)
                    embed.add_field(name="🤔 Sensação Térmica", value=f"{feels_like}°C", inline=True)
                    embed.add_field(name="💧 Umidade", value=f"{humidity}%", inline=True)
                    embed.add_field(name="💨 Vento", value=f"{wind_speed} m/s", inline=True)
                    # Adicionar mais dados se desejar (pressão, visibilidade, nascer/pôr do sol)
                    sunrise_ts = data['sys']['sunrise']
                    sunset_ts = data['sys']['sunset']
                    embed.add_field(name="☀️ Nascer do Sol", value=f"<t:{sunrise_ts}:t>", inline=True)
                    embed.add_field(name="🌙 Pôr do Sol", value=f"<t:{sunset_ts}:t>", inline=True)
                    
                    embed.set_footer(text="Dados fornecidos por OpenWeatherMap")
                    embed.timestamp = datetime.datetime.fromtimestamp(data['dt'], tz=pytz.utc)
                    
                    await interaction.followup.send(embed=embed)
        except aiohttp.ClientError as e:
             await interaction.followup.send(f"{EMOJI_FAILURE} Erro de conexão ao buscar dados do clima: {e}", ephemeral=True)
        except Exception as e:
            print(f"[ERRO Clima] {e}")
            await interaction.followup.send(f"{EMOJI_FAILURE} Ocorreu um erro inesperado ao buscar o clima.", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="dado", description="Rola um ou mais dados com X lados.")
    async def dado(self, interaction: Interaction, 
                   quantidade: int = SlashOption(description="Número de dados", default=1, min_value=1, max_value=25),
                   lados: int = SlashOption(description="Número de lados do dado", default=6, min_value=2, max_value=1000)):
        """Rola um ou mais dados e mostra os resultados individuais e a soma."""
        if quantidade == 1:
            resultado = random.randint(1, lados)
            await interaction.response.send_message(f"🎲 Você rolou um d{lados}: **{resultado}**")
        else:
            rolagens = [random.randint(1, lados) for _ in range(quantidade)]
            soma = sum(rolagens)
            rolagens_str = ", ".join(map(str, rolagens))
            if len(rolagens_str) > 1000:
                rolagens_str = rolagens_str[:997] + "..."
            embed = Embed(title=f"🎲 Rolagem de {quantidade}d{lados}", color=Color.random())
            embed.add_field(name="Resultados Individuais", value=f"`{rolagens_str}`", inline=False)
            embed.add_field(name="Soma Total", value=f"**{soma}**", inline=False)
            await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="cronometro", description="Inicia um cronômetro regressivo.")
    async def cronometro(self, interaction: Interaction, segundos: int = SlashOption(description="Duração em segundos", min_value=1, max_value=600)):
        """Inicia uma contagem regressiva e notifica o usuário ao final."""
        end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=segundos)
        await interaction.response.send_message(f"⏱️ Cronômetro iniciado! Termina em <t:{int(end_time.timestamp())}:R>.", ephemeral=(segundos > 60))
        
        await asyncio.sleep(segundos)
        
        try:
            # Tenta responder à interação original se ainda for válida, senão envia mensagem normal
            await interaction.followup.send(f"⏰ {interaction.user.mention}, seu cronômetro de {segundos}s terminou!", allowed_mentions=nextcord.AllowedMentions(users=True))
        except nextcord.NotFound:
             # Se a interação expirou, tenta enviar no canal
             try:
                 await interaction.channel.send(f"⏰ {interaction.user.mention}, seu cronômetro de {segundos}s terminou!", allowed_mentions=nextcord.AllowedMentions(users=True))
             except Exception as e:
                 print(f"[ERRO Cronometro] Falha ao notificar {interaction.user.id} no canal {interaction.channel.id}: {e}")
        except Exception as e:
            print(f"[ERRO Cronometro] Falha ao notificar {interaction.user.id}: {e}")

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="enquete", description="Cria uma enquete interativa com botões.")
    async def enquete(self, interaction: Interaction, 
                      pergunta: str = SlashOption(description="A pergunta da enquete"), 
                      opcoes: str = SlashOption(description="As opções separadas por vírgula (máx 10)")):
        """Cria uma enquete onde usuários podem votar clicando em botões."""
        opcoes_lista = [op.strip() for op in opcoes.split(',') if op.strip()][:10] # Limita a 10 opções
        if len(opcoes_lista) < 2:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Você precisa fornecer pelo menos duas opções válidas separadas por vírgula.", ephemeral=True)
            return
            
        view = EnqueteView(pergunta, opcoes_lista)
        initial_embed = view.create_poll_embed()
        await interaction.response.send_message(embed=initial_embed, view=view)
        view.message = await interaction.original_message() # Guarda a mensagem para edição

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="quote", description="Receba uma citação inspiradora aleatória.")
    async def quote(self, interaction: Interaction):
        """Exibe uma citação motivacional ou filosófica aleatória."""
        embed = Embed(description=f"*“{random.choice(self.quotes)}”*

 color=Color.purple())
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="curiosidade", description="Receba uma curiosidade aleatória.")
    async def curiosidade(self, interaction: Interaction):
        """Exibe um fato interessante ou curioso aleatório."""
        embed = Embed(title=f"{EMOJI_QUESTION} Você Sabia?", description=random.choice(self.curiosidades), color=Color.teal())
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="sugestao", description="Envie uma sugestão para melhorar o bot.")
    async def sugestao(self, interaction: Interaction):
        """Abre um modal para o usuário enviar uma sugestão detalhada."""
        await interaction.response.send_modal(SugestaoModal(SUGGESTIONS_CHANNEL_NAME))

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="numero_aleatorio", description="Gera um número aleatório entre dois valores.")
    async def numero_aleatorio(self, interaction: Interaction, 
                              minimo: int = SlashOption(description="Valor mínimo", default=1), 
                              maximo: int = SlashOption(description="Valor máximo", default=100)):
        """Gera um número inteiro aleatório dentro de um intervalo especificado."""
        if minimo >= maximo:
            await interaction.response.send_message(f"{EMOJI_FAILURE} O valor mínimo (`{minimo}`) deve ser estritamente menor que o valor máximo (`{maximo}`).", ephemeral=True)
        else:
            resultado = random.randint(minimo, maximo)
            await interaction.response.send_message(f"🎲 Número aleatório entre {minimo} e {maximo}: **{resultado}**")

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="senha", description="Gera uma senha aleatória segura.")
    async def senha(self, interaction: Interaction, 
                   tamanho: int = SlashOption(description="Tamanho da senha", min_value=8, max_value=64, default=16),
                   incluir_maiusculas: bool = SlashOption(description="Incluir letras maiúsculas?", default=True),
                   incluir_numeros: bool = SlashOption(description="Incluir números?", default=True),
                   incluir_simbolos: bool = SlashOption(description="Incluir símbolos?", default=True)):
        """Gera uma senha aleatória segura e a envia por mensagem efêmera."""
        caracteres = "abcdefghijklmnopqrstuvwxyz"
        if incluir_maiusculas:
            caracteres += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if incluir_numeros:
            caracteres += "0123456789"
        if incluir_simbolos:
            caracteres += "!@#$%^&*()-_=+[]{}\|;:",.<>/?~"
            
        if not caracteres:
             await interaction.response.send_message(f"{EMOJI_FAILURE} Você deve incluir pelo menos um tipo de caractere para gerar a senha!", ephemeral=True)
             return
             
        senha_gerada = ".join(secrets.choice(caracteres) for _ in range(tamanho))
        
        embed = Embed(title="🔐 Senha Gerada", description=f"Sua senha segura de {tamanho} caracteres está abaixo:", color=Color.dark_grey())
        embed.add_field(name="Senha", value=f"`{senha_gerada}`")
        embed.set_footer(text="Esta mensagem é visível apenas para você.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="contagem", description="Faz uma contagem regressiva no chat.")
    async def contagem(self, interaction: Interaction, segundos: int = SlashOption(description="Duração em segundos", min_value=1, max_value=10)):
        """Realiza uma contagem regressiva visível no canal."""
        await interaction.response.defer()
        msg = await interaction.followup.send(f"⏱️ Contagem regressiva iniciando em **{segundos}**...")
        
        for i in range(segundos, 0, -1):
            await asyncio.sleep(1)
            await msg.edit(content=f"⏱️ **{i}**...")
            
        await asyncio.sleep(1)
        await msg.edit(content=f"{EMOJI_CELEBRATE} Contagem finalizada! {EMOJI_HAPPY}")

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="github", description="Mostra informações de um repositório do GitHub.")
    async def github(self, interaction: Interaction, repositorio: str = SlashOption(description="Nome do repositório (ex: usuario/repo)")):
        """Busca e exibe informações sobre um repositório público no GitHub."""
        await interaction.response.defer()
        url = f"https://api.github.com/repos/{repositorio}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    if r.status == 404:
                        await interaction.followup.send(f"{EMOJI_FAILURE} Repositório `{repositorio}` não encontrado ou privado.", ephemeral=True)
                        return
                    elif r.status != 200:
                        await interaction.followup.send(f"{EMOJI_FAILURE} Erro ao buscar informações do GitHub (Status: {r.status}). Tente novamente mais tarde.", ephemeral=True)
                        return
                        
                    data = await r.json()
                    embed = Embed(title=f"<:github:ID_EMOJI_GITHUB> {data["full_name"]}", description=data["description"] or "Sem descrição.", url=data["html_url"], color=0x24292e) # Cor do GitHub
                    
                    embed.add_field(name="⭐ Estrelas", value=f"{data["stargazers_count"]:,}", inline=True)
                    embed.add_field(name="🍴 Forks", value=f"{data["forks_count"]:,}", inline=True)
                    embed.add_field(name="👀 Observadores", value=f"{data["watchers_count"]:,}", inline=True)
                    embed.add_field(name="🔧 Linguagem Principal", value=data["language"] or "N/A", inline=True)
                    embed.add_field(name="⚖️ Licença", value=data["license"]["name"] if data.get("license") else "Nenhuma", inline=True)
                    embed.add_field(name="⚠️ Issues Abertas", value=f"{data["open_issues_count"]:,}", inline=True)
                    
                    created_ts = int(datetime.datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")).timestamp())
                    updated_ts = int(datetime.datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")).timestamp())
                    embed.add_field(name="📅 Criado em", value=f"<t:{created_ts}:f> (<t:{created_ts}:R>)", inline=False)
                    embed.add_field(name="🔄 Última Atualização", value=f"<t:{updated_ts}:f> (<t:{updated_ts}:R>)", inline=False)
                    
                    if data.get("owner") and data["owner"].get("avatar_url"):
                        embed.set_thumbnail(url=data["owner"]["avatar_url"])
                        
                    embed.set_footer(text="Informações via API do GitHub")
                    await interaction.followup.send(embed=embed)
        except aiohttp.ClientError as e:
             await interaction.followup.send(f"{EMOJI_FAILURE} Erro de conexão ao buscar dados do GitHub: {e}", ephemeral=True)
        except Exception as e:
            print(f"[ERRO GitHub] {e}")
            await interaction.followup.send(f"{EMOJI_FAILURE} Ocorreu um erro inesperado ao buscar informações do repositório.", ephemeral=True)

    @nextcord.slash_command(guild_ids=[SERVER_ID], name="qrcode", description="Gera um QR Code para um texto ou link.")
    async def qrcode_cmd(self, interaction: Interaction, data: str = SlashOption(description="O texto ou link para gerar o QR Code")):
        """Cria uma imagem de QR Code a partir do texto fornecido."""
        await interaction.response.defer()
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            
            # Salva a imagem em um buffer de bytes
            buffer = BytesIO()
            img.save(buffer, "PNG")
            buffer.seek(0)
            
            file = File(buffer, filename="qrcode.png")
            embed = Embed(title=" Geração de QR Code", color=Color.dark_blue())
            embed.description = f"QR Code gerado para: `{data}`"
            embed.set_image(url="attachment://qrcode.png")
            embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, file=file)
        except Exception as e:
            print(f"[ERRO QRCode] {e}")
            await interaction.followup.send(f"{EMOJI_FAILURE} Ocorreu um erro ao gerar o QR Code.", ephemeral=True)

    # --- Adicionar mais utilitários ---
    # - Tradutor (requer API ou biblioteca robusta)
    # - Dicionário
    # - Conversor de unidades (moeda, temperatura, etc.)
    # - Pesquisa de imagens
    # - Lembrete periódico (ex: a cada X horas)
    # - Sorteio

# Função setup para carregar a cog
def setup(bot):
    """Adiciona a cog Utilitarios ao bot."""
    # Instalar dependências se necessário (ex: qrcode, pytz)
    # Idealmente, isso estaria no requirements.txt
    try:
        import qrcode
        import pytz
    except ImportError:
        print("[ALERTA] Dependências `qrcode` ou `pytz` não encontradas. Instale-as com `pip install qrcode[pil] pytz` para funcionalidade completa da cog Utilitarios.")
        # Poderia tentar instalar aqui, mas é melhor gerenciar pelo requirements.txt
        # os.system("pip install qrcode[pil] pytz") 
    bot.add_cog(Utilitarios(bot))
