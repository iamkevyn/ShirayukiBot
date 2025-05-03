# /home/ubuntu/ShirayukiBot/cogs/Economia.py
# Cog para o sistema de economia do bot.

import nextcord
from nextcord import Interaction, Embed, SlashOption, Color, Member, User
from nextcord.ext import commands, tasks, application_checks
from nextcord import ui
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
import asyncio

# Importar helper de emojis
from utils.emojis import get_emoji

# --- Configurações de Economia ---
CURRENCY_NAME = "Cristais Shirayuki" # Nome da moeda customizada
CURRENCY_SYMBOL = "CS" # Símbolo curto
DATA_DIR = "/home/ubuntu/ShirayukiBot/data"
ECONOMY_FILE = os.path.join(DATA_DIR, "economy.json") # Arquivo para guardar dados dos usuários
SHOP_FILE = os.path.join(DATA_DIR, "shop.json") # Arquivo para itens da loja

# Cooldowns (em segundos)
DAILY_COOLDOWN = 24 * 3600 # 24 horas
WORK_COOLDOWN = 2 * 3600 # 2 horas
CRIME_COOLDOWN = 5 * 60 # 5 minutos
ROB_COOLDOWN = 1 * 3600 # 1 hora
BET_COOLDOWN = 30 # 30 segundos

# Valores
DAILY_MIN = 100
DAILY_MAX = 500
WORK_MIN = 50
WORK_MAX = 250
CRIME_SUCCESS_MIN = 100
CRIME_SUCCESS_MAX = 750
CRIME_FAIL_FINE_MIN = 50
CRIME_FAIL_FINE_MAX = 300
CRIME_SUCCESS_RATE = 0.60 # 60% chance de sucesso
ROB_SUCCESS_RATE = 0.40 # 40% chance de sucesso
ROB_MAX_PERCENTAGE = 0.10 # Rouba no máximo 10% do saldo da vítima
ROB_FAIL_FINE_PERCENTAGE = 0.05 # Multa de 5% do próprio saldo se falhar

# ID do cargo de admin (para comandos restritos) - Substituir pelo ID real se necessário
ADMIN_ROLE_ID = None # Ex: 123456789012345678

# --- Funções Auxiliares --- 
def ensure_dir_exists(file_path):
    """Garante que o diretório de um arquivo exista."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Diretório criado: {directory}')

def load_json_data(file_path, default_data):
    """Carrega dados de um arquivo JSON, criando-o com dados padrão se não existir."""
    ensure_dir_exists(file_path)
    if not os.path.exists(file_path):
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [AVISO] Arquivo {os.path.basename(file_path)} não encontrado. Criando com dados padrão.')
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [ERRO] Falha ao carregar {os.path.basename(file_path)}, usando dados padrão.")        return default_data

def save_json_data(file_path, data):
    """Salva dados em um arquivo JSON."""
    ensure_dir_exists(file_path)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [ERRO] Falha ao salvar {os.path.basename(file_path)}: {e}")

# --- Gerenciamento de Dados de Economia --- 
class EconomyManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = load_json_data(file_path, {})
        self.lock = asyncio.Lock() # Lock para evitar race conditions

    async def _get_user_data(self, user_id: int) -> dict:
        """Retorna os dados do usuário, criando se não existir."""
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            self.data[user_id_str] = {
                "balance": 0,
                "inventory": [],
                "cooldowns": {},
                "stats": {"earned": 0, "spent": 0, "gambled": 0, "won": 0, "lost": 0, "stolen": 0, "robbed": 0}
            }
        # Garante que todos os campos existam
        self.data[user_id_str].setdefault("balance", 0)
        self.data[user_id_str].setdefault("inventory", [])
        self.data[user_id_str].setdefault("cooldowns", {})
        self.data[user_id_str].setdefault("stats", {"earned": 0, "spent": 0, "gambled": 0, "won": 0, "lost": 0, "stolen": 0, "robbed": 0})
        return self.data[user_id_str]

    async def save_data(self):
        """Salva os dados de forma assíncrona e segura."""
        async with self.lock:
            await asyncio.to_thread(save_json_data, self.file_path, self.data)

    async def get_balance(self, user_id: int) -> int:
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            return user_data["balance"]

    async def update_balance(self, user_id: int, amount: int, reason: str = "unknown") -> int:
        """Atualiza o saldo de um usuário e registra estatísticas."""
        if amount == 0:
            return await self.get_balance(user_id)
            
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            original_balance = user_data["balance"]
            user_data["balance"] += amount
            
            # Garante que o saldo não seja negativo
            if user_data["balance"] < 0:
                amount -= user_data["balance"] # Ajusta o valor real da transação
                user_data["balance"] = 0
                
            # Atualiza estatísticas
            stats = user_data["stats"]
            if amount > 0:
                stats["earned"] = stats.get("earned", 0) + amount
                if reason == "gamble_win":
                    stats["won"] = stats.get("won", 0) + amount
                elif reason == "rob_success":
                    stats["robbed"] = stats.get("robbed", 0) + amount
            else: # amount < 0
                actual_spent = abs(amount)
                stats["spent"] = stats.get("spent", 0) + actual_spent
                if reason == "gamble_loss":
                    stats["lost"] = stats.get("lost", 0) + actual_spent
                elif reason == "rob_fail_fine" or reason == "crime_fail_fine":
                     stats["lost"] = stats.get("lost", 0) + actual_spent # Considera multas como perdas
                elif reason == "stolen":
                     stats["stolen"] = stats.get("stolen", 0) + actual_spent
                     
            # Atualiza a estatística de apostas (total apostado)
            if reason in ["gamble_win", "gamble_loss"]:
                 # Assume que a aposta foi o valor absoluto da mudança (precisa ser passado idealmente)
                 # Esta lógica é falha, o valor da aposta deveria ser passado explicitamente
                 # Por ora, vamos estimar baseado na perda/ganho
                 bet_amount = abs(amount) # Estimativa
                 stats["gambled"] = stats.get("gambled", 0) + bet_amount
                 
            await asyncio.to_thread(save_json_data, self.file_path, self.data) # Salva dentro do lock
            return user_data["balance"]

    async def get_cooldown(self, user_id: int, command_name: str) -> float | None:
        """Retorna o timestamp de quando o cooldown termina, ou None."""
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            return user_data["cooldowns"].get(command_name)

    async def set_cooldown(self, user_id: int, command_name: str, duration: int):
        """Define o cooldown para um comando."""
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            expires_at = time.time() + duration
            user_data["cooldowns"][command_name] = expires_at
            # Não salva aqui, salva junto com update_balance ou outra operação principal

    async def check_cooldown(self, user_id: int, command_name: str) -> int | None:
        """Verifica se um comando está em cooldown. Retorna segundos restantes ou None."""
        expires_at = await self.get_cooldown(user_id, command_name)
        if expires_at and time.time() < expires_at:
            return int(expires_at - time.time())
        return None

    async def get_inventory(self, user_id: int) -> list:
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            return user_data["inventory"]

    async def add_item(self, user_id: int, item_id: str, quantity: int = 1):
        """Adiciona um item ao inventário."""
        if quantity <= 0:
            return
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            inventory = user_data["inventory"]
            found = False
            for item in inventory:
                if item.get("id") == item_id:
                    item["quantity"] = item.get("quantity", 0) + quantity
                    found = True
                    break
            if not found:
                inventory.append({"id": item_id, "quantity": quantity})
            await asyncio.to_thread(save_json_data, self.file_path, self.data)

    async def remove_item(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """Remove um item do inventário. Retorna True se bem sucedido."""
        if quantity <= 0:
            return False
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            inventory = user_data["inventory"]
            item_index = -1
            current_quantity = 0
            for i, item in enumerate(inventory):
                if item.get("id") == item_id:
                    item_index = i
                    current_quantity = item.get("quantity", 0)
                    break
            
            if item_index == -1 or current_quantity < quantity:
                return False # Item não encontrado ou quantidade insuficiente
                
            inventory[item_index]["quantity"] -= quantity
            if inventory[item_index]["quantity"] <= 0:
                del inventory[item_index]
                
            await asyncio.to_thread(save_json_data, self.file_path, self.data)
            return True
            
    async def get_item_quantity(self, user_id: int, item_id: str) -> int:
        """Retorna a quantidade de um item específico no inventário."""
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            inventory = user_data["inventory"]
            for item in inventory:
                if item.get("id") == item_id:
                    return item.get("quantity", 0)
            return 0

    async def get_all_data(self) -> dict:
         """Retorna todos os dados de economia (para ranking, etc)."""
         async with self.lock:
             # Retorna uma cópia profunda para evitar modificações externas
             return json.loads(json.dumps(self.data))

# --- Gerenciamento da Loja --- 
class ShopManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.items = load_json_data(file_path, {})
        self.lock = asyncio.Lock()

    async def save_items(self):
        async with self.lock:
            await asyncio.to_thread(save_json_data, self.file_path, self.items)

    async def get_item(self, item_id: str) -> dict | None:
        async with self.lock:
            return self.items.get(item_id.lower())

    async def get_all_items(self) -> dict:
        async with self.lock:
            return json.loads(json.dumps(self.items))

    async def add_item(self, item_id: str, name: str, price: int, description: str, emoji: str = "📦", role_id: int | None = None, usable: bool = False) -> bool:
        """Adiciona ou atualiza um item na loja."""
        item_id = item_id.lower()
        if not item_id or not name or price < 0:
            return False
        async with self.lock:
            self.items[item_id] = {
                "name": name,
                "price": price,
                "description": description,
                "emoji": emoji,
                "role_id": role_id,
                "usable": usable
            }
            await asyncio.to_thread(save_json_data, self.file_path, self.items)
            return True

    async def remove_item(self, item_id: str) -> bool:
        """Remove um item da loja."""
        item_id = item_id.lower()
        async with self.lock:
            if item_id in self.items:
                del self.items[item_id]
                await asyncio.to_thread(save_json_data, self.file_path, self.items)
                return True
            return False

# --- Cog Economia --- 
class Economia(commands.Cog):
    """Cog responsável pelos comandos do sistema de economia."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.currency_emoji = get_emoji(bot, "money", default="💰") # Tenta pegar emoji custom, senão usa padrão
        self.economy_manager = EconomyManager(ECONOMY_FILE)
        self.shop_manager = ShopManager(SHOP_FILE)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Cog Economia carregada.")
        print(f"[Economia] Usando moeda: {CURRENCY_NAME} ({self.currency_emoji})")

    # --- Comandos Principais --- 

    @nextcord.slash_command(name="saldo", description=f"Verifique seu saldo de {CURRENCY_NAME}.")
    async def saldo(self, interaction: Interaction, usuario: Member | User = SlashOption(description="Ver o saldo de outro usuário (opcional)", required=False)):
        """Mostra o saldo de Cristais Shirayuki do usuário ou de outro membro."""
        target_user = usuario or interaction.user
        balance = await self.economy_manager.get_balance(target_user.id)

        embed = Embed(
            title=f"{self.currency_emoji} Saldo de {target_user.display_name}",
            description=f"Saldo atual: **{balance:,} {CURRENCY_SYMBOL}**",
            color=target_user.color if isinstance(target_user, Member) else Color.blue()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # Alias para /saldo
    @nextcord.slash_command(name="bolsa", description=f"Alias para /saldo. Verifica seu saldo de {CURRENCY_NAME}.")
    async def bolsa_alias(self, interaction: Interaction, usuario: Member | User = SlashOption(description="Ver o saldo de outro usuário (opcional)", required=False)):
        """Alias para /saldo."""
        await self.saldo(interaction, usuario)

    @nextcord.slash_command(name="diario", description=f"Resgate seus {CURRENCY_NAME} diários!")
    async def diario(self, interaction: Interaction):
        """Permite ao usuário resgatar uma quantia diária da moeda do bot."""
        user_id = interaction.user.id
        command_name = "daily"

        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
            hours, remainder = divmod(cooldown_left, 3600)
            minutes, seconds = divmod(remainder, 60)
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'clock')} Você já resgatou seu prêmio diário! Tente novamente em **{hours}h {minutes}m {seconds}s**.",
                ephemeral=True
            )
            return

        # Resgate permitido
        amount = random.randint(DAILY_MIN, DAILY_MAX)
        new_balance = await self.economy_manager.update_balance(user_id, amount, reason="daily")
        await self.economy_manager.set_cooldown(user_id, command_name, DAILY_COOLDOWN)
        await self.economy_manager.save_data() # Salva cooldown e saldo

        embed = Embed(
            title=f"{get_emoji(self.bot, 'gift')} Resgate Diário!",
            description=f"{get_emoji(self.bot, 'sparkle_happy')} Você resgatou **{amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}**!",
            color=Color.gold()
        )
        embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="transferir", description=f"Transfira {CURRENCY_NAME} para outro usuário.")
    async def transferir(self, interaction: Interaction, 
                       usuario: Member = SlashOption(description="O usuário para quem transferir"), 
                       quantia: int = SlashOption(description="A quantia a ser transferida", min_value=1)):
        """Permite transferir Cristais Shirayuki para outro membro."""
        sender = interaction.user
        recipient = usuario

        if sender.id == recipient.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode transferir {CURRENCY_SYMBOL} para si mesmo!", ephemeral=True)
            return
        if recipient.bot:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não pode transferir {CURRENCY_SYMBOL} para bots!", ephemeral=True)
            return

        sender_balance = await self.economy_manager.get_balance(sender.id)

        if sender_balance < quantia:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não tem {CURRENCY_SYMBOL} suficientes! Saldo atual: **{sender_balance:,} {self.currency_emoji}**", ephemeral=True)
            return

        # Confirmação
        view = ConfirmTransferView(sender, recipient, quantia, self.currency_emoji, CURRENCY_SYMBOL, self.economy_manager, self.bot)
        embed = Embed(
            title=f"{get_emoji(self.bot, 'thinking')} Confirmação de Transferência",
            description=f"Você tem certeza que deseja transferir **{quantia:,} {self.currency_emoji} {CURRENCY_SYMBOL}** para {recipient.mention}?",
            color=Color.orange()
        )
        embed.add_field(name="Seu Saldo Atual", value=f"{sender_balance:,} {self.currency_emoji}")
        embed.add_field(name="Seu Saldo Após", value=f"{sender_balance - quantia:,} {self.currency_emoji}")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        await view.wait()
        # A view cuidará da resposta final

    @nextcord.slash_command(name="ranking", description=f"Veja os usuários mais ricos em {CURRENCY_NAME}.")
    async def ranking(self, interaction: Interaction, pagina: int = SlashOption(description="Número da página do ranking", default=1, min_value=1)):
        """Mostra o ranking dos usuários com mais Cristais Shirayuki."""
        await interaction.response.defer()
        
        all_data = await self.economy_manager.get_all_data()
        # Filtra usuários sem saldo ou com saldo 0 e ordena
        sorted_users = sorted(
            [(user_id, details.get("balance", 0)) for user_id, details in all_data.items() if details.get("balance", 0) > 0],
            key=lambda item: item[1],
            reverse=True
        )

        items_per_page = 10
        total_pages = (len(sorted_users) + items_per_page - 1) // items_per_page
        if pagina > total_pages and total_pages > 0:
            pagina = total_pages # Vai para a última página se o número for muito alto
        elif pagina < 1:
             pagina = 1

        start_index = (pagina - 1) * items_per_page
        end_index = start_index + items_per_page
        current_page_users = sorted_users[start_index:end_index]

        embed = Embed(
            title=f"🏆 Ranking de {CURRENCY_NAME}",
            color=Color.gold()
        )

        if not sorted_users:
            embed.description = f"{get_emoji(self.bot, 'info')} Ainda não há ninguém no ranking. Use `/diario` para começar!"
        else:
            rank_list = []
            global_rank_start = start_index + 1
            for i, (user_id, balance) in enumerate(current_page_users):
                member = interaction.guild.get_member(int(user_id)) if interaction.guild else None
                user_display = member.mention if member else f"User ID: {user_id}"
                
                rank_num = global_rank_start + i
                rank_emoji = ""
                if rank_num == 1: rank_emoji = "🥇 "
                elif rank_num == 2: rank_emoji = "🥈 "
                elif rank_num == 3: rank_emoji = "🥉 "
                else: rank_emoji = f"`#{rank_num}` "
                
                rank_list.append(f"{rank_emoji}{user_display}: **{balance:,} {self.currency_emoji}**")
            
            embed.description = "\n".join(rank_list)
            embed.set_footer(text=f"Página {pagina}/{total_pages} | Total de {len(sorted_users)} jogadores no ranking")

        await interaction.followup.send(embed=embed)
        
    # Alias para /ranking
    @nextcord.slash_command(name="rank", description=f"Alias para /ranking. Veja os usuários mais ricos.")
    async def rank_alias(self, interaction: Interaction, pagina: int = SlashOption(description="Número da página do ranking", default=1, min_value=1)):
        """Alias para /ranking."""
        await self.ranking(interaction, pagina)

    # --- Comandos de Ganho/Perda --- 

    @nextcord.slash_command(name="trabalhar", description="Faça um trabalho rápido para ganhar alguns Cristais.")
    async def trabalhar(self, interaction: Interaction):
        """Permite ao usuário ganhar uma quantia aleatória de dinheiro com cooldown."""
        user_id = interaction.user.id
        command_name = "work"

        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
            hours, remainder = divmod(cooldown_left, 3600)
            minutes, seconds = divmod(remainder, 60)
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'clock')} Você precisa descansar! Seu próximo turno de trabalho começa em **{hours}h {minutes}m {seconds}s**.",
                ephemeral=True
            )
            return

        # Trabalho permitido
        amount = random.randint(WORK_MIN, WORK_MAX)
        new_balance = await self.economy_manager.update_balance(user_id, amount, reason="work")
        await self.economy_manager.set_cooldown(user_id, command_name, WORK_COOLDOWN)
        await self.economy_manager.save_data()

        # Mensagens de trabalho variadas
        work_messages = [
            f"Você trabalhou duro como programador e ganhou **{amount:,} {self.currency_emoji}**!",
            f"Após um longo dia na cafeteria, você recebeu **{amount:,} {self.currency_emoji}**.",
            f"Você ajudou a Shirayuki a organizar a biblioteca e ela te recompensou com **{amount:,} {self.currency_emoji}**! {get_emoji(self.bot, 'happy_flower')}",
            f"Sua stream bombou hoje! Você faturou **{amount:,} {self.currency_emoji}**.",
            f"Você entregou pizzas e ganhou **{amount:,} {self.currency_emoji}**."
        ]
        
        embed = Embed(
            title=f"{get_emoji(self.bot, 'work')} Trabalho Concluído!",
            description=random.choice(work_messages),
            color=Color.green()
        )
        embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="apostar", description="Aposte seus Cristais em um jogo de cara ou coroa!")
    async def apostar(self, interaction: Interaction, 
                      quantia: int = SlashOption(description="A quantia a ser apostada", min_value=10),
                      escolha: str = SlashOption(description="Sua escolha", choices={"Cara": "cara", "Coroa": "coroa"})):
        """Aposta uma quantia em cara ou coroa (50/50)."""
        user_id = interaction.user.id
        command_name = "bet"
        
        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
             await interaction.response.send_message(f"{get_emoji(self.bot, 'clock')} Calma nas apostas! Espere **{cooldown_left} segundos**.", ephemeral=True)
             return

        balance = await self.economy_manager.get_balance(user_id)
        if quantia > balance:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não tem **{quantia:,} {self.currency_emoji}** para apostar! Saldo: {balance:,} {self.currency_emoji}", ephemeral=True)
            return

        await interaction.response.defer()
        await self.economy_manager.set_cooldown(user_id, command_name, BET_COOLDOWN)
        
        resultado_real = random.choice(["cara", "coroa"])
        emoji_real = "👑" if resultado_real == "cara" else "🪙"
        
        embed = Embed(title=f"{get_emoji(self.bot, 'dice')} Aposta - Cara ou Coroa", color=Color.dark_gold())
        embed.add_field(name="Sua Escolha", value=escolha.capitalize(), inline=True)
        embed.add_field(name="Sua Aposta", value=f"{quantia:,} {self.currency_emoji}", inline=True)
        
        await asyncio.sleep(1) # Suspense
        embed.add_field(name="Resultado", value=f"**{resultado_real.capitalize()} {emoji_real}**", inline=True)

        if escolha == resultado_real:
            new_balance = await self.economy_manager.update_balance(user_id, quantia, reason="gamble_win")
            embed.description = f"{get_emoji(self.bot, 'celebrate')} **Você ganhou!** Você recebeu **{quantia:,} {self.currency_emoji}**!"
            embed.color = Color.green()
        else:
            new_balance = await self.economy_manager.update_balance(user_id, -quantia, reason="gamble_loss")
            embed.description = f"{get_emoji(self.bot, 'sad')} **Você perdeu!** Você perdeu **{quantia:,} {self.currency_emoji}**."
            embed.color = Color.red()
            
        embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**", inline=False)
        await self.economy_manager.save_data()
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="crime", description="Tente cometer um pequeno crime para ganhar dinheiro (arriscado!).")
    async def crime(self, interaction: Interaction):
        """Tenta a sorte em um crime para ganhar dinheiro, com chance de falha e multa."""
        user_id = interaction.user.id
        command_name = "crime"

        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'clock')} Você está sendo vigiado! Espere **{cooldown_left} segundos** antes de tentar outro crime.",
                ephemeral=True
            )
            return

        await interaction.response.defer()
        await self.economy_manager.set_cooldown(user_id, command_name, CRIME_COOLDOWN)
        await asyncio.sleep(1.5) # Suspense

        if random.random() < CRIME_SUCCESS_RATE:
            # Sucesso
            amount = random.randint(CRIME_SUCCESS_MIN, CRIME_SUCCESS_MAX)
            new_balance = await self.economy_manager.update_balance(user_id, amount, reason="crime_success")
            success_messages = [
                f"Você furtou uma carteira e encontrou **{amount:,} {self.currency_emoji}**!",
                f"Você hackeou um caixa eletrônico e conseguiu **{amount:,} {self.currency_emoji}**!",
                f"Você vendeu informações falsas e lucrou **{amount:,} {self.currency_emoji}**.",
                f"Você enganou um turista e ganhou **{amount:,} {self.currency_emoji}**."
            ]
            embed = Embed(title=f"{get_emoji(self.bot, 'money_fly')} Crime Bem-Sucedido!", description=random.choice(success_messages), color=Color.dark_green())
            embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        else:
            # Falha
            fine = random.randint(CRIME_FAIL_FINE_MIN, CRIME_FAIL_FINE_MAX)
            current_balance = await self.economy_manager.get_balance(user_id)
            fine = min(fine, current_balance) # Multa não pode ser maior que o saldo
            new_balance = await self.economy_manager.update_balance(user_id, -fine, reason="crime_fail_fine")
            fail_messages = [
                f"Você foi pego tentando roubar uma loja! Multa de **{fine:,} {self.currency_emoji}**.",
                f"A polícia te pegou no flagra! Você pagou **{fine:,} {self.currency_emoji}** de fiança.",
                f"Seu disfarce falhou miseravelmente. Você perdeu **{fine:,} {self.currency_emoji}**.",
                f"Você tropeçou e caiu durante a fuga, perdendo **{fine:,} {self.currency_emoji}**."
            ]
            embed = Embed(title=f"{get_emoji(self.bot, 'sad')} Crime Falhou!", description=random.choice(fail_messages), color=Color.dark_red())
            embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")

        await self.economy_manager.save_data()
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="roubar", description="Tente roubar Cristais de outro usuário (muito arriscado!).")
    async def roubar(self, interaction: Interaction, vitima: Member = SlashOption(description="O usuário que você tentará roubar")):
        """Tenta roubar dinheiro de outro usuário, com alta chance de falha e multa."""
        robber = interaction.user
        victim = vitima
        command_name = "rob"

        if robber.id == victim.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Você não pode roubar a si mesmo!", ephemeral=True)
            return
        if victim.bot:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não pode roubar bots! Eles não têm {CURRENCY_SYMBOL}.", ephemeral=True)
            return

        cooldown_left = await self.economy_manager.check_cooldown(robber.id, command_name)
        if cooldown_left:
            hours, rem = divmod(cooldown_left, 3600)
            mins, secs = divmod(rem, 60)
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'clock')} Você ainda está se recuperando do último roubo! Espere **{int(hours)}h {int(mins)}m {int(secs)}s**.",
                ephemeral=True
            )
            return

        robber_balance = await self.economy_manager.get_balance(robber.id)
        victim_balance = await self.economy_manager.get_balance(victim.id)

        if victim_balance < 100: # Não vale a pena roubar quem tem pouco
            await interaction.response.send_message(f"{get_emoji(self.bot, 'thinking')} {victim.mention} não tem {CURRENCY_SYMBOL} suficientes para valer o risco.", ephemeral=True)
            return
            
        min_robber_balance_for_fine = 50 # Saldo mínimo que o ladrão precisa ter para pagar multa
        if robber_balance < min_robber_balance_for_fine:
             await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você precisa ter pelo menos **{min_robber_balance_for_fine:,} {self.currency_emoji}** para tentar um roubo (caso precise pagar a multa!).", ephemeral=True)
             return

        await interaction.response.defer()
        await self.economy_manager.set_cooldown(robber.id, command_name, ROB_COOLDOWN)
        await asyncio.sleep(2) # Suspense

        if random.random() < ROB_SUCCESS_RATE:
            # Sucesso
            max_steal = int(victim_balance * ROB_MAX_PERCENTAGE)
            amount_stolen = random.randint(1, max(1, max_steal)) # Garante roubar pelo menos 1
            
            new_robber_balance = await self.economy_manager.update_balance(robber.id, amount_stolen, reason="rob_success")
            new_victim_balance = await self.economy_manager.update_balance(victim.id, -amount_stolen, reason="stolen")
            
            success_messages = [
                f"Você foi sorrateiro e roubou **{amount_stolen:,} {self.currency_emoji}** de {victim.mention}!",
                f"Num momento de distração, você pegou **{amount_stolen:,} {self.currency_emoji}** de {victim.mention}!",
                f"Sua lábia funcionou! {victim.mention} te deu **{amount_stolen:,} {self.currency_emoji}** sem perceber."
            ]
            embed = Embed(title=f"{get_emoji(self.bot, 'money_fly')} Roubo Bem-Sucedido!", description=random.choice(success_messages), color=Color.dark_green())
            embed.add_field(name=f"Seu Novo Saldo", value=f"**{new_robber_balance:,} {self.currency_emoji}**", inline=True)
            embed.add_field(name=f"Saldo de {victim.display_name}", value=f"**{new_victim_balance:,} {self.currency_emoji}**", inline=True)
        else:
            # Falha
            fine = int(robber_balance * ROB_FAIL_FINE_PERCENTAGE)
            fine = max(10, fine) # Multa mínima de 10
            fine = min(fine, robber_balance) # Não pode perder mais do que tem
            
            new_robber_balance = await self.economy_manager.update_balance(robber.id, -fine, reason="rob_fail_fine")
            
            fail_messages = [
                f"{victim.mention} te viu chegando e chamou a segurança! Você foi multado em **{fine:,} {self.currency_emoji}**.",
                f"Você tropeçou e fez barulho. {victim.mention} te pegou! Multa de **{fine:,} {self.currency_emoji}**.",
                f"Seu plano falhou! Você teve que pagar **{fine:,} {self.currency_emoji}** para não ser preso."
            ]
            embed = Embed(title=f"{get_emoji(self.bot, 'sad')} Roubo Falhou!", description=random.choice(fail_messages), color=Color.dark_red())
            embed.add_field(name=f"Seu Novo Saldo", value=f"**{new_robber_balance:,} {self.currency_emoji}**")

        await self.economy_manager.save_data()
        await interaction.followup.send(embed=embed)

    # --- Comandos da Loja --- 

    @nextcord.slash_command(name="loja", description="Veja os itens disponíveis para compra.")
    async def loja(self, interaction: Interaction):
        """Mostra os itens disponíveis na loja."""
        await interaction.response.defer()
        items = await self.shop_manager.get_all_items()
        user_balance = await self.economy_manager.get_balance(interaction.user.id)
        
        embed = Embed(
            title=f"🛒 Loja de {CURRENCY_NAME}",
            description=f"Use `/comprar [item_id]` para adquirir. Seu saldo: **{user_balance:,} {self.currency_emoji}**",
            color=Color.purple()
        )

        if not items:
            embed.description += f"\n\n{get_emoji(self.bot, 'info')} A loja está vazia no momento."
        else:
            sorted_items = sorted(items.items(), key=lambda item: item[1].get("price", 0))
            for item_id, item_details in sorted_items:
                embed.add_field(
                    name=f"{item_details.get('emoji', '📦')} {item_details.get('name', 'Item Desconhecido')} (`{item_id}`)",
                    value=f"> Preço: **{item_details.get('price', 0):,} {self.currency_emoji}**\n> {item_details.get('description', 'Sem descrição.')}",
                    inline=False
                )
            embed.set_footer(text="Use o ID entre parênteses (``) para comprar.")

        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="comprar", description="Compre um item da loja.")
    async def comprar(self, interaction: Interaction, item_id: str = SlashOption(description="O ID do item a ser comprado (veja na /loja)")):
        """Permite comprar um item da loja usando o ID do item."""
        item_id_lower = item_id.lower()
        user_id = interaction.user.id

        item_details = await self.shop_manager.get_item(item_id_lower)
        if not item_details:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Item com ID `{item_id}` inválido. Use `/loja` para ver os IDs corretos.", ephemeral=True)
            return

        item_price = item_details.get("price", 0)
        user_balance = await self.economy_manager.get_balance(user_id)

        if user_balance < item_price:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Você não tem {CURRENCY_SYMBOL} suficientes! Saldo: {user_balance:,} {self.currency_emoji} | Preço: {item_price:,} {self.currency_emoji}", ephemeral=True)
            return

        # Realiza a compra
        new_balance = await self.economy_manager.update_balance(user_id, -item_price, reason="purchase")
        await self.economy_manager.add_item(user_id, item_id_lower, 1)
        # Salva ambos (saldo e inventário)
        await self.economy_manager.save_data()

        # Lógica adicional pós-compra (ex: adicionar cargo)
        role_id_to_add = item_details.get("role_id")
        role_added_message = ""
        if role_id_to_add and interaction.guild and isinstance(interaction.user, Member):
            role = interaction.guild.get_role(role_id_to_add)
            if role:
                try:
                    await interaction.user.add_roles(role, reason=f"Comprou item {item_id} na loja")
                    role_added_message = f"\n{get_emoji(self.bot, 'sparkle')} O cargo {role.mention} foi adicionado a você!"
                except nextcord.Forbidden:
                    role_added_message = f"\n{get_emoji(self.bot, 'warn')} Não consegui adicionar o cargo {role.name}. Verifique minhas permissões."
                except Exception as e:
                    role_added_message = f"\n{get_emoji(self.bot, 'sad')} Erro ao adicionar o cargo {role.name}: {e}"
            else:
                 role_added_message = f"\n{get_emoji(self.bot, 'warn')} O cargo associado a este item (ID: {role_id_to_add}) não foi encontrado no servidor."

        embed = Embed(
            title=f"{get_emoji(self.bot, 'gift')} Compra Realizada!",
            description=f"Você comprou **{item_details.get('emoji', '')} {item_details.get('name', item_id)}** por **{item_price:,} {self.currency_emoji}**!{role_added_message}",
            color=Color.green()
        )
        embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="inventario", description="Veja os itens que você possui.")
    async def inventario(self, interaction: Interaction, usuario: Member | User = SlashOption(description="Ver o inventário de outro usuário (opcional)", required=False)):
        """Mostra o inventário de itens do usuário ou de outro membro."""
        target_user = usuario or interaction.user
        inventory_list = await self.economy_manager.get_inventory(target_user.id)

        embed = Embed(
            title=f"🎒 Inventário de {target_user.display_name}",
            color=target_user.color if isinstance(target_user, Member) else Color.orange()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)

        if not inventory_list:
            embed.description = f"{get_emoji(self.bot, 'info')} O inventário está vazio. Use `/loja` e `/comprar` para adquirir itens!"
        else:
            inventory_desc = []
            items_details = await self.shop_manager.get_all_items() # Pega detalhes dos itens da loja
            for item_data in inventory_list:
                item_id = item_data.get("id")
                quantity = item_data.get("quantity", 0)
                if quantity <= 0: continue # Ignora itens com quantidade zero ou negativa
                
                item_shop_details = items_details.get(item_id, {})
                item_name = item_shop_details.get("name", f"Item ID: {item_id}")
                item_emoji = item_shop_details.get("emoji", "❓")
                inventory_desc.append(f"{item_emoji} **{item_name}** (ID: `{item_id}`) - Quantidade: **{quantity}**")
            
            if not inventory_desc:
                 embed.description = f"{get_emoji(self.bot, 'info')} O inventário está vazio."
            else:
                 embed.description = "\n".join(inventory_desc)

        await interaction.response.send_message(embed=embed)
        
    # TODO: Comando /usar [item_id]
    # TODO: Comando /vender [item_id]

    # --- Comandos de Administração --- 
    # Decorator para verificar se o usuário tem permissão de admin (cargo ou permissão)
    def is_admin():
        async def predicate(interaction: Interaction) -> bool:
            if isinstance(interaction.user, Member):
                 # Verifica se tem permissão de Administrador OU se tem o cargo de admin definido
                if interaction.user.guild_permissions.administrator: 
                    return True
                if ADMIN_ROLE_ID and any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
                    return True
            # Permite o dono do bot sempre
            if await interaction.client.is_owner(interaction.user):
                 return True
                 
            await interaction.response.send_message(f"{get_emoji(interaction.client, 'sad')} Você não tem permissão para usar este comando.", ephemeral=True)
            return False
        return application_checks.check(predicate)

    @nextcord.slash_command(name="eco_admin", description="[Admin] Gerencia a economia dos usuários.")
    @is_admin()
    async def eco_admin(self, interaction: Interaction):
        pass # Comando base para subcomandos

    @eco_admin.subcommand(name="set", description="[Admin] Define o saldo de um usuário.")
    async def eco_admin_set(self, interaction: Interaction, 
                            usuario: Member | User = SlashOption(description="O usuário a ter o saldo modificado"), 
                            quantia: int = SlashOption(description="A nova quantia exata", min_value=0)):
        user_id = usuario.id
        current_balance = await self.economy_manager.get_balance(user_id)
        amount_change = quantia - current_balance # Calcula a diferença para registrar stats corretamente
        
        new_balance = await self.economy_manager.update_balance(user_id, amount_change, reason="admin_set")
        await self.economy_manager.save_data()
        
        embed = Embed(title=f"{get_emoji(self.bot, 'admin')} Saldo Definido (Admin)", color=Color.orange())
        embed.description = f"O saldo de {usuario.mention} foi definido para **{new_balance:,} {self.currency_emoji}**."
        embed.set_footer(text=f"Comando executado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @eco_admin.subcommand(name="give", description="[Admin] Adiciona saldo a um usuário.")
    async def eco_admin_give(self, interaction: Interaction, 
                             usuario: Member | User = SlashOption(description="O usuário a receber saldo"), 
                             quantia: int = SlashOption(description="A quantia a ser adicionada", min_value=1)):
        user_id = usuario.id
        new_balance = await self.economy_manager.update_balance(user_id, quantia, reason="admin_give")
        await self.economy_manager.save_data()
        
        embed = Embed(title=f"{get_emoji(self.bot, 'admin')} Saldo Adicionado (Admin)", color=Color.green())
        embed.description = f"**{quantia:,} {self.currency_emoji}** foram adicionados a {usuario.mention}."
        embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        embed.set_footer(text=f"Comando executado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @eco_admin.subcommand(name="take", description="[Admin] Remove saldo de um usuário.")
    async def eco_admin_take(self, interaction: Interaction, 
                             usuario: Member | User = SlashOption(description="O usuário a perder saldo"), 
                             quantia: int = SlashOption(description="A quantia a ser removida", min_value=1)):
        user_id = usuario.id
        current_balance = await self.economy_manager.get_balance(user_id)
        amount_to_remove = min(quantia, current_balance) # Não pode remover mais do que o usuário tem
        
        new_balance = await self.economy_manager.update_balance(user_id, -amount_to_remove, reason="admin_take")
        await self.economy_manager.save_data()
        
        embed = Embed(title=f"{get_emoji(self.bot, 'admin')} Saldo Removido (Admin)", color=Color.red())
        embed.description = f"**{amount_to_remove:,} {self.currency_emoji}** foram removidos de {usuario.mention}."
        embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        embed.set_footer(text=f"Comando executado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @eco_admin.subcommand(name="reset", description="[Admin] Reseta a economia de um usuário (saldo e inventário!).")
    async def eco_admin_reset(self, interaction: Interaction, usuario: Member | User = SlashOption(description="O usuário a ter a economia resetada")):
        user_id_str = str(usuario.id)
        async with self.economy_manager.lock:
            if user_id_str in self.economy_manager.data:
                self.economy_manager.data[user_id_str] = {
                    "balance": 0,
                    "inventory": [],
                    "cooldowns": {},
                    "stats": {"earned": 0, "spent": 0, "gambled": 0, "won": 0, "lost": 0, "stolen": 0, "robbed": 0}
                }
                await self.economy_manager.save_data()
                msg = f"A economia de {usuario.mention} foi resetada com sucesso."
                color = Color.orange()
            else:
                msg = f"{usuario.mention} não possui dados de economia para resetar."
                color = Color.light_grey()
                
        embed = Embed(title=f"{get_emoji(self.bot, 'admin')} Economia Resetada (Admin)", description=msg, color=color)
        embed.set_footer(text=f"Comando executado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="loja_admin", description="[Admin] Gerencia os itens da loja.")
    @is_admin()
    async def loja_admin(self, interaction: Interaction):
        pass # Comando base

    @loja_admin.subcommand(name="add", description="[Admin] Adiciona ou atualiza um item na loja.")
    async def loja_admin_add(self, interaction: Interaction,
                             item_id: str = SlashOption(description="ID único do item (ex: pocao_vida)"),
                             nome: str = SlashOption(description="Nome do item a ser exibido"),
                             preco: int = SlashOption(description="Preço do item", min_value=0),
                             descricao: str = SlashOption(description="Descrição do item"),
                             emoji: str = SlashOption(description="Emoji para o item (opcional)", default="📦"),
                             cargo_id: str = SlashOption(name="id_cargo_associado", description="ID do cargo a ser dado na compra (opcional)", required=False),
                             usavel: bool = SlashOption(name="item_usavel", description="Se o item pode ser usado com /usar (opcional)", default=False)
                             ):
        role_id_int = None
        if cargo_id:
            try:
                role_id_int = int(cargo_id)
            except ValueError:
                await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} ID do Cargo inválido. Deve ser um número.", ephemeral=True)
                return
                
        success = await self.shop_manager.add_item(item_id, nome, preco, descricao, emoji, role_id_int, usavel)
        if success:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Item `{item_id}` adicionado/atualizado na loja com sucesso!", ephemeral=True)
        else:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'sad')} Falha ao adicionar item. Verifique os dados.", ephemeral=True)

    @loja_admin.subcommand(name="remove", description="[Admin] Remove um item da loja.")
    async def loja_admin_remove(self, interaction: Interaction, item_id: str = SlashOption(description="ID do item a ser removido")):
        success = await self.shop_manager.remove_item(item_id)
        if success:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'happy_flower')} Item `{item_id}` removido da loja com sucesso!", ephemeral=True)
        else:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Item `{item_id}` não encontrado na loja.", ephemeral=True)

    # --- Tratamento de Erro de Cooldown --- 
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        # Trata especificamente erros de cooldown DENTRO desta cog
        if isinstance(error, application_checks.ApplicationCommandOnCooldown) and interaction.application_command.cog_name == self.__cog_name__:
            # Cooldowns já são tratados dentro de cada comando com mensagem específica
            # Apenas marca como tratado para evitar logs desnecessários
            try:
                error.handled = True 
            except AttributeError:
                pass 
        elif isinstance(error, application_checks.CheckFailure) and interaction.application_command.cog_name == self.__cog_name__:
             # Erros de permissão (como do @is_admin) já enviam mensagem
             # Apenas marca como tratado
             try:
                error.handled = True 
             except AttributeError:
                pass
        # Deixa outros erros passarem

# --- Views Auxiliares --- 
class ConfirmTransferView(ui.View):
    def __init__(self, sender: User | Member, recipient: User | Member, amount: int, currency_emoji: str, currency_symbol: str, economy_manager: EconomyManager, bot):
        super().__init__(timeout=60.0)
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.currency_emoji = currency_emoji
        self.currency_symbol = currency_symbol
        self.economy_manager = economy_manager
        self.bot = bot
        self.confirmed = False

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Só o remetente pode confirmar/cancelar
        if interaction.user.id != self.sender.id:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'warn')} Apenas {self.sender.mention} pode confirmar esta transferência.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if not self.confirmed:
            for item in self.children:
                item.disabled = True
            timeout_embed = Embed(title="Transferência Cancelada", description="Você demorou muito para confirmar.", color=Color.red())
            try:
                # Edita a mensagem original (que era efêmera)
                await self.message.edit(embed=timeout_embed, view=self)
            except (nextcord.NotFound, AttributeError):
                pass # Mensagem não existe mais ou não foi definida

    @ui.button(label="Confirmar", style=ButtonStyle.green)
    async def confirm_button(self, button: ui.Button, interaction: Interaction):
        self.confirmed = True
        button.disabled = True
        self.children[1].disabled = True # Desabilita o botão Cancelar
        
        # Verifica saldo novamente antes de transferir (pode ter mudado)
        sender_balance = await self.economy_manager.get_balance(self.sender.id)
        if sender_balance < self.amount:
            error_embed = Embed(title="Transferência Falhou", description=f"{get_emoji(self.bot, 'sad')} Seu saldo mudou e você não tem mais {self.currency_symbol} suficientes!", color=Color.red())
            await interaction.response.edit_message(embed=error_embed, view=self)
            self.stop()
            return
            
        # Realiza a transferência
        await self.economy_manager.update_balance(self.sender.id, -self.amount, reason="transfer_sent")
        new_recipient_balance = await self.economy_manager.update_balance(self.recipient.id, self.amount, reason="transfer_received")
        await self.economy_manager.save_data()

        success_embed = Embed(
            title=f"{get_emoji(self.bot, 'happy_flower')} Transferência Realizada!",
            description=f"Você transferiu **{self.amount:,} {self.currency_emoji} {self.currency_symbol}** para {self.recipient.mention}!",
            color=Color.green()
        )
        success_embed.add_field(name=f"Saldo de {self.recipient.display_name}", value=f"{new_recipient_balance:,} {self.currency_emoji}", inline=False)
        await interaction.response.edit_message(embed=success_embed, view=None) # Remove botões após sucesso
        self.stop()

    @ui.button(label="Cancelar", style=ButtonStyle.red)
    async def cancel_button(self, button: ui.Button, interaction: Interaction):
        self.confirmed = False # Garante que on_timeout não edite se cancelado manualmente
        for item in self.children:
            item.disabled = True
        cancel_embed = Embed(title="Transferência Cancelada", description="A transferência foi cancelada.", color=Color.greyple())
        await interaction.response.edit_message(embed=cancel_embed, view=self)
        self.stop()

# Função setup para carregar a cog
def setup(bot):
    """Adiciona a cog Economia ao bot."""
    bot.add_cog(Economia(bot))
