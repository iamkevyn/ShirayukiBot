# /home/ubuntu/ShirayukiBot/cogs/Economia.py
# Cog para o sistema de economia do bot.

import nextcord
from nextcord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta

# --- Configurações de Economia ---
CURRENCY_NAME = "Cristais Shirayuki" # Nome da moeda customizada
CURRENCY_EMOJI = "💎" # Emoji para a moeda (pode ser customizado depois)
DAILY_MIN_AMOUNT = 100
DAILY_MAX_AMOUNT = 500
DATA_FILE = "/home/ubuntu/ShirayukiBot/data/economy.json" # Arquivo para guardar dados dos usuários

# --- Emojis Customizados ---
EMOJI_SUCCESS = "<:8_:1366997164521164830>" # Emoji de sucesso
EMOJI_FAILURE = "<:1_:1366996823654535208>" # Emoji de falha/triste
EMOJI_INFO = "<:7_:1366997117410873404>"    # Emoji de informação/neutro
EMOJI_WAIT = "<:2_:1366996885398749254>"     # Emoji de espera
EMOJI_QUESTION = "<:6_:1366997079347429427>" # Emoji de dúvida/ajuda
EMOJI_WARN = "<:4_:1366996921297801216>"     # Emoji de aviso
EMOJI_CELEBRATE = "<:5_:1366997045445132360>" # Emoji de celebração (usado como moeda)
EMOJI_HAPPY = "<:3_:1366996904663322654>"     # Emoji feliz genérico

# Atualizando o emoji da moeda
CURRENCY_EMOJI = EMOJI_CELEBRATE

# --- Funções Auxiliares --- 
def load_economy_data():
    """Carrega os dados de economia do arquivo JSON."""
    if not os.path.exists(os.path.dirname(DATA_FILE)):
        os.makedirs(os.path.dirname(DATA_FILE))
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {} # Retorna dicionário vazio se o arquivo estiver corrompido

def save_economy_data(data):
    """Salva os dados de economia no arquivo JSON."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user_balance(user_id):
    """Retorna o saldo de um usuário."""
    data = load_economy_data()
    return data.get(str(user_id), {}).get("balance", 0)

def update_user_balance(user_id, amount):
    """Atualiza o saldo de um usuário (pode ser negativo para remover)."""
    data = load_economy_data()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {"balance": 0, "last_daily": None}
    data[user_id_str]["balance"] = data[user_id_str].get("balance", 0) + amount
    if data[user_id_str]["balance"] < 0:
        data[user_id_str]["balance"] = 0 # Saldo não pode ser negativo
    save_economy_data(data)
    return data[user_id_str]["balance"]

def get_last_daily(user_id):
    """Retorna a data/hora do último resgate diário."""
    data = load_economy_data()
    return data.get(str(user_id), {}).get("last_daily")

def set_last_daily(user_id, timestamp):
    """Define a data/hora do último resgate diário."""
    data = load_economy_data()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {"balance": 0, "last_daily": None}
    data[user_id_str]["last_daily"] = timestamp
    save_economy_data(data)

# --- Cog Economia ---
class Economia(commands.Cog):
    """Cog responsável pelos comandos do sistema de economia."""

    def __init__(self, bot):
        self.bot = bot
        print(f"[DIAGNÓSTICO] Cog Economia carregada.")
        # Garante que o diretório de dados exista
        if not os.path.exists(os.path.dirname(DATA_FILE)):
            os.makedirs(os.path.dirname(DATA_FILE))
            print(f"[INFO] Diretório de dados criado em: {os.path.dirname(DATA_FILE)}")

    @nextcord.slash_command(name="diario", description=f"Resgate seus {CURRENCY_NAME} diários!")
    async def diario(self, interaction: nextcord.Interaction):
        """Permite ao usuário resgatar uma quantia diária da moeda do bot."""
        user_id = interaction.user.id
        now = datetime.utcnow()
        last_daily_str = get_last_daily(user_id)

        if last_daily_str:
            last_daily_time = datetime.fromisoformat(last_daily_str)
            time_since_last = now - last_daily_time
            if time_since_last < timedelta(hours=24):
                time_left = timedelta(hours=24) - time_since_last
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                # TODO: Usar emoji customizado de falha
                await interaction.response.send_message(
                    f"{EMOJI_FAILURE} Você já resgatou seu prêmio diário! Tente novamente em {hours}h {minutes}m {seconds}s.",
                    ephemeral=True
                )
                return

        # Resgate permitido
        amount = random.randint(DAILY_MIN_AMOUNT, DAILY_MAX_AMOUNT)
        new_balance = update_user_balance(user_id, amount)
        set_last_daily(user_id, now.isoformat())

        # TODO: Usar emoji customizado de sucesso
        embed = nextcord.Embed(
            title="💰 Resgate Diário!",
            description=f"{EMOJI_SUCCESS} Você resgatou **{amount} {CURRENCY_EMOJI} {CURRENCY_NAME}**!\nSeu novo saldo é: **{new_balance} {CURRENCY_EMOJI}**",
            color=nextcord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="bolsa", description=f"Verifique seu saldo de {CURRENCY_NAME}.")
    async def bolsa(self, interaction: nextcord.Interaction, usuario: nextcord.Member = None):
        """Mostra o saldo de Cristais Shirayuki do usuário ou de outro membro."""
        target_user = usuario or interaction.user
        balance = get_user_balance(target_user.id)

        # TODO: Usar emoji customizado de informação
        embed = nextcord.Embed(
            title=f"Bolsa de {target_user.display_name}",
            description=f"{EMOJI_INFO} Saldo atual: **{balance} {CURRENCY_EMOJI} {CURRENCY_NAME}**",
            color=nextcord.Color.blue()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # Adicionar mais comandos de economia aqui (ex: transferir, rank, loja, etc.)
    # Lembre-se de usar os emojis customizados e expandir a funcionalidade.

# Função setup para carregar a cog
def setup(bot):
    bot.add_cog(Economia(bot))



    @nextcord.slash_command(name="transferir", description=f"Transfira {CURRENCY_NAME} para outro usuário.")
    async def transferir(self, interaction: nextcord.Interaction, usuario: nextcord.Member, quantia: int):
        """Permite transferir Cristais Shirayuki para outro membro."""
        sender_id = interaction.user.id
        recipient_id = usuario.id

        if sender_id == recipient_id:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Você não pode transferir {CURRENCY_NAME} para si mesmo!", ephemeral=True)
            return

        if quantia <= 0:
            await interaction.response.send_message(f"{EMOJI_FAILURE} A quantia a ser transferida deve ser positiva!", ephemeral=True)
            return

        sender_balance = get_user_balance(sender_id)

        if sender_balance < quantia:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Você não tem {CURRENCY_NAME} suficientes para realizar esta transferência. Saldo atual: {sender_balance} {CURRENCY_EMOJI}", ephemeral=True)
            return

        # Realiza a transferência
        update_user_balance(sender_id, -quantia)
        new_recipient_balance = update_user_balance(recipient_id, quantia)

        embed = nextcord.Embed(
            title=f"{EMOJI_SUCCESS} Transferência Realizada!",
            description=f"{interaction.user.mention} transferiu **{quantia} {CURRENCY_EMOJI} {CURRENCY_NAME}** para {usuario.mention}!",
            color=nextcord.Color.green()
        )
        embed.add_field(name=f"Saldo de {usuario.display_name}", value=f"{new_recipient_balance} {CURRENCY_EMOJI}", inline=False)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="ranking", description=f"Veja os usuários mais ricos em {CURRENCY_NAME}.")
    async def ranking(self, interaction: nextcord.Interaction, top: int = 10):
        """Mostra o ranking dos usuários com mais Cristais Shirayuki."""
        if top <= 0 or top > 25: # Limita o top para evitar embeds muito grandes
            await interaction.response.send_message(f"{EMOJI_WARN} Por favor, insira um número entre 1 e 25 para o top.", ephemeral=True)
            return

        data = load_economy_data()
        # Filtra usuários sem saldo ou com saldo 0 e ordena
        sorted_users = sorted(
            [(user_id, details.get("balance", 0)) for user_id, details in data.items() if details.get("balance", 0) > 0],
            key=lambda item: item[1],
            reverse=True
        )

        embed = nextcord.Embed(
            title=f"🏆 Ranking de {CURRENCY_NAME} (Top {min(top, len(sorted_users))})",
            color=nextcord.Color.gold()
        )

        if not sorted_users:
            embed.description = f"{EMOJI_INFO} Ainda não há ninguém no ranking. Use `/diario` para começar!"
        else:
            rank_list = []
            for i, (user_id, balance) in enumerate(sorted_users[:top]):
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    user_display = user.mention
                except nextcord.NotFound:
                    user_display = f"Usuário ID: {user_id} (Não encontrado)"
                except Exception as e:
                    print(f"Erro ao buscar usuário {user_id} para ranking: {e}")
                    user_display = f"Usuário ID: {user_id} (Erro)"
                
                rank_emoji = ""
                if i == 0: rank_emoji = "🥇 "
                elif i == 1: rank_emoji = "🥈 "
                elif i == 2: rank_emoji = "🥉 "
                else: rank_emoji = f"#{i+1} "
                
                rank_list.append(f"{rank_emoji}{user_display}: **{balance} {CURRENCY_EMOJI}**")
            
            embed.description = "\n".join(rank_list)

        await interaction.response.send_message(embed=embed)

    # --- Comandos Futuros para Expansão ---
    # - Loja (/loja): Listar itens à venda.
    # - Comprar (/comprar [item]): Comprar um item da loja.
    # - Inventário (/inventario): Ver itens comprados.
    # - Usar item (/usar [item]): Usar um item consumível ou equipável.
    # - Vender item (/vender [item]): Vender um item do inventário.
    # - Trabalhar (/trabalhar): Ganhar dinheiro com cooldown.
    # - Apostar (/apostar [quantia]): Jogo de azar simples.
    # - Doar (/doar [quantia]): Doar para um "banco" ou causa.
    # - Sistema de Juros/Banco: Depositar dinheiro para ganhar juros.
    # - Itens colecionáveis.




    # --- Sistema de Loja (Estrutura Inicial) ---
    # TODO: Mover itens para um arquivo de configuração JSON separado?
    shop_items = {
        "pocao_sorte": {"name": "Poção da Sorte", "price": 500, "description": "Aumenta sua chance em jogos de azar por 1 hora.", "emoji": "🍀"},
        "cor_nick_azul": {"name": "Cor de Nick Azul", "price": 1000, "description": "Permite alterar a cor do seu nick para azul (requer permissão do bot).", "emoji": "🔵"},
        "cargo_vip_bronze": {"name": "Cargo VIP Bronze", "price": 5000, "description": "Ganha acesso a um cargo VIP Bronze especial.", "emoji": "🥉", "role_id": None}, # TODO: Adicionar ID do cargo
        "item_raro_1": {"name": "Fragmento Estelar", "price": 10000, "description": "Um item colecionável raro.", "emoji": "✨"}
    }

    def add_item_to_inventory(self, user_id, item_id):
        """Adiciona um item ao inventário do usuário."""
        data = load_economy_data()
        user_id_str = str(user_id)
        if user_id_str not in data:
            data[user_id_str] = {"balance": 0, "last_daily": None, "inventory": []}
        if "inventory" not in data[user_id_str]:
            data[user_id_str]["inventory"] = []
        
        # Verifica se o item já existe e incrementa a quantidade, ou adiciona novo
        found = False
        for item in data[user_id_str]["inventory"]:
            if item.get("id") == item_id:
                item["quantity"] = item.get("quantity", 1) + 1
                found = True
                break
        if not found:
            data[user_id_str]["inventory"].append({"id": item_id, "quantity": 1})
            
        save_economy_data(data)

    def get_user_inventory(self, user_id):
        """Retorna o inventário de um usuário."""
        data = load_economy_data()
        return data.get(str(user_id), {}).get("inventory", [])

    @nextcord.slash_command(name="loja", description="Veja os itens disponíveis para compra.")
    async def loja(self, interaction: nextcord.Interaction):
        """Mostra os itens disponíveis na loja."""
        embed = nextcord.Embed(
            title=f"🛒 Loja de {CURRENCY_NAME}",
            description=f"Use `/comprar [item]` para adquirir um item. Seu saldo: {get_user_balance(interaction.user.id)} {CURRENCY_EMOJI}",
            color=nextcord.Color.purple()
        )

        if not self.shop_items:
            embed.description = f"{EMOJI_INFO} A loja está vazia no momento."
        else:
            for item_id, item_details in self.shop_items.items():
                embed.add_field(
                    name=f"{item_details.get('emoji', '')} {item_details['name']} ({item_id})",
                    value=f"> Preço: **{item_details['price']} {CURRENCY_EMOJI}**\n> {item_details['description']}",
                    inline=False
                )
            embed.set_footer(text="IDs dos itens estão entre parênteses.")

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="comprar", description="Compre um item da loja.")
    async def comprar(self, interaction: nextcord.Interaction, item_id: str):
        """Permite comprar um item da loja usando o ID do item."""
        item_id = item_id.lower() # Normaliza o ID para minúsculas
        user_id = interaction.user.id

        if item_id not in self.shop_items:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Item com ID `{item_id}` inválido. Use `/loja` para ver os itens disponíveis.", ephemeral=True)            return

        item_details = self.shop_items[item_id]
        item_price = item_details["price"]
        user_balance = get_user_balance(user_id)

        if user_balance < item_price:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Você não tem {CURRENCY_NAME} suficientes para comprar `{item_details['name']}`! Saldo atual: {user_balance} {CURRENCY_EMOJI}", ephemeral=True)            return

        # Realiza a compra
        update_user_balance(user_id, -item_price)
        self.add_item_to_inventory(user_id, item_id)

        # TODO: Implementar lógica adicional (ex: adicionar cargo)
        if item_details.get("role_id"):
            # Lógica para adicionar cargo ao usuário (requer permissões e ID do cargo)
            pass

        embed = nextcord.Embed(
            title=f"{EMOJI_SUCCESS} Compra Realizada!",
            description=f"Você comprou **{item_details['name']}** por **{item_price} {CURRENCY_EMOJI}**!",
            color=nextcord.Color.green()
        )
        embed.add_field(name="Novo Saldo", value=f"{get_user_balance(user_id)} {CURRENCY_EMOJI}")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="inventario", description="Veja os itens que você possui.")
    async def inventario(self, interaction: nextcord.Interaction, usuario: nextcord.Member = None):
        """Mostra o inventário de itens do usuário ou de outro membro."""
        target_user = usuario or interaction.user
        inventory = self.get_user_inventory(target_user.id)

        embed = nextcord.Embed(
            title=f"🎒 Inventário de {target_user.display_name}",
            color=nextcord.Color.orange()
        )

        if not inventory:
            embed.description = f"{EMOJI_INFO} Seu inventário está vazio. Use `/loja` e `/comprar` para adquirir itens!"
        else:
            inventory_list = []
            for item in inventory:
                item_id = item.get("id")
                quantity = item.get("quantity", 1)
                item_details = self.shop_items.get(item_id)
                if item_details:
                    inventory_list.append(f"{item_details.get('emoji', '')} **{item_details['name']}** (ID: {item_id}) - Quantidade: {quantity}")
                else:
                    inventory_list.append(f"❓ Item Desconhecido (ID: {item_id}) - Quantidade: {quantity}")
            embed.description = "\n".join(inventory_list)

        embed.set_thumbnail(url=target_user.display_avatar.url)
        await interaction.response.send_message(embed=embed)




    # --- Comandos Adicionais de Economia ---
    WORK_COOLDOWN = timedelta(hours=1) # Cooldown de 1 hora para trabalhar
    WORK_MIN_AMOUNT = 50
    WORK_MAX_AMOUNT = 250
    BET_MIN_AMOUNT = 10

    def get_last_work(self, user_id):
        """Retorna a data/hora do último trabalho."""
        data = load_economy_data()
        return data.get(str(user_id), {}).get("last_work")

    def set_last_work(self, user_id, timestamp):
        """Define a data/hora do último trabalho."""
        data = load_economy_data()
        user_id_str = str(user_id)
        if user_id_str not in data:
            # Cria entrada se não existir, embora update_user_balance geralmente já faça isso
            data[user_id_str] = {"balance": 0, "last_daily": None, "inventory": [], "last_work": None}
        if "last_work" not in data[user_id_str]: # Garante que a chave exista
             data[user_id_str]["last_work"] = None
        data[user_id_str]["last_work"] = timestamp
        save_economy_data(data)

    @nextcord.slash_command(name="trabalhar", description=f"Trabalhe para ganhar {CURRENCY_NAME}.")
    async def trabalhar(self, interaction: nextcord.Interaction):
        """Permite ao usuário trabalhar para ganhar uma quantia da moeda do bot (com cooldown)."""
        user_id = interaction.user.id
        now = datetime.utcnow()
        last_work_str = self.get_last_work(user_id)

        if last_work_str:
            last_work_time = datetime.fromisoformat(last_work_str)
            time_since_last = now - last_work_time
            if time_since_last < self.WORK_COOLDOWN:
                time_left = self.WORK_COOLDOWN - time_since_last
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                await interaction.response.send_message(
                    f"{EMOJI_WAIT} Você precisa descansar um pouco! Tente trabalhar novamente em {minutes}m {seconds}s.",
                    ephemeral=True
                )
                return

        # Trabalho permitido
        amount = random.randint(self.WORK_MIN_AMOUNT, self.WORK_MAX_AMOUNT)
        new_balance = update_user_balance(user_id, amount)
        self.set_last_work(user_id, now.isoformat())

        embed = nextcord.Embed(
            title="💼 Trabalho Concluído!",
            description=f"{EMOJI_HAPPY} Você trabalhou duro e ganhou **{amount} {CURRENCY_EMOJI} {CURRENCY_NAME}**!\nSeu novo saldo é: **{new_balance} {CURRENCY_EMOJI}**",
            color=nextcord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="apostar", description=f"Aposte seus {CURRENCY_NAME} em um jogo de cara ou coroa.")
    async def apostar(self, interaction: nextcord.Interaction, quantia: int, escolha: str = nextcord.SlashOption(description="Sua escolha", choices=["Cara", "Coroa"])):
        """Aposta uma quantia em um jogo de cara ou coroa (50% de chance)."""
        user_id = interaction.user.id

        if quantia < self.BET_MIN_AMOUNT:
            await interaction.response.send_message(f"{EMOJI_WARN} A aposta mínima é de {self.BET_MIN_AMOUNT} {CURRENCY_EMOJI}!", ephemeral=True)
            return

        user_balance = get_user_balance(user_id)
        if quantia > user_balance:
            await interaction.response.send_message(f"{EMOJI_FAILURE} Você não tem {CURRENCY_NAME} suficientes para apostar essa quantia. Saldo: {user_balance} {CURRENCY_EMOJI}", ephemeral=True)
            return

        # Jogo de Cara ou Coroa
        resultado = random.choice(["Cara", "Coroa"])
        ganhou = (escolha.lower() == resultado.lower())

        embed = nextcord.Embed(title="🪙 Cara ou Coroa?", color=nextcord.Color.dark_gold())
        embed.add_field(name="Sua Escolha", value=escolha, inline=True)
        embed.add_field(name="Resultado", value=resultado, inline=True)

        if ganhou:
            new_balance = update_user_balance(user_id, quantia)
            embed.description = f"{EMOJI_CELEBRATE} Parabéns! Você ganhou **{quantia} {CURRENCY_EMOJI} {CURRENCY_NAME}**!"
            embed.color = nextcord.Color.green()
        else:
            new_balance = update_user_balance(user_id, -quantia)
            embed.description = f"{EMOJI_FAILURE} Que pena! Você perdeu **{quantia} {CURRENCY_EMOJI} {CURRENCY_NAME}**."
            embed.color = nextcord.Color.red()

        embed.add_field(name="Novo Saldo", value=f"{new_balance} {CURRENCY_EMOJI}", inline=False)
        await interaction.response.send_message(embed=embed)
