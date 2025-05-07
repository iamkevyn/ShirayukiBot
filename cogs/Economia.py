# /home/ubuntu/ShirayukiBot/cogs/Economia.py
# Cog para o sistema de economia do bot.

import nextcord
from nextcord import Interaction, Embed, SlashOption, Color, Member, User, File, ButtonStyle
from nextcord.ext import commands, tasks, application_checks
from nextcord import ui # Boa prática importar ui diretamente
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
import asyncio

# Importar helper de emojis (usando placeholder como em Comandos.py)
# from utils.emojis import get_emoji
def get_emoji(bot, name):
    emoji_map = {
        "money": "💰", "clock": "⏰", "gift": "🎁", "sparkle_happy": "✨",
        "work": "💼", "crime": "🔪", "rob": "🎭", "bet": "🎰", "win": "🎉", "lose": "💸",
        "shop": "🛍️", "buy": "🛒", "sell": "🏷️", "inventory": "🎒", "use": "🔧",
        "trophy": "🏆", "admin": "👑", "error": "❌", "success": "✅", "warn": "⚠️",
        "sad": "😥", "happy_flower": "🌸", "hammer": "🔨", "trash": "🗑️",
        "gear": "⚙️", "info": "ℹ️", "dice": "🎲", "tools": "🛠️", "question": "❓",
        "music": "🎵", "interact": "🤝"
    }
    return emoji_map.get(name, "▫️")

# --- Configurações de Economia ---
CURRENCY_NAME = "Cristais Shirayuki"
CURRENCY_SYMBOL = "CS"
DATA_DIR = "/home/ubuntu/ShirayukiBot/data"
ECONOMY_FILE = os.path.join(DATA_DIR, "economy.json")
SHOP_FILE = os.path.join(DATA_DIR, "shop.json")

# Cooldowns (em segundos)
DAILY_COOLDOWN = 24 * 3600
WORK_COOLDOWN = 2 * 3600
CRIME_COOLDOWN = 5 * 60
ROB_COOLDOWN = 1 * 3600
BET_COOLDOWN = 30

# Valores
DAILY_MIN = 100
DAILY_MAX = 500
WORK_MIN = 50
WORK_MAX = 250
CRIME_SUCCESS_MIN = 100
CRIME_SUCCESS_MAX = 750
CRIME_FAIL_FINE_MIN = 50
CRIME_FAIL_FINE_MAX = 300
CRIME_SUCCESS_RATE = 0.60
ROB_SUCCESS_RATE = 0.40
ROB_MAX_PERCENTAGE = 0.10
ROB_FAIL_FINE_PERCENTAGE = 0.05

ADMIN_ROLE_ID = None 

# --- Funções Auxiliares --- 
def ensure_dir_exists(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Diretório criado: {directory}')

def load_json_data(file_path, default_data):
    ensure_dir_exists(file_path)
    if not os.path.exists(file_path):
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [AVISO] Arquivo {os.path.basename(file_path)} não encontrado. Criando com dados padrão.')
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [ERRO] Falha ao carregar {os.path.basename(file_path)}, usando dados padrão.")
        return default_data

def save_json_data(file_path, data):
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
        self.lock = asyncio.Lock()

    async def _get_user_data(self, user_id: int) -> dict:
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            self.data[user_id_str] = {
                "balance": 0,
                "inventory": [],
                "cooldowns": {},
                "stats": {"earned": 0, "spent": 0, "gambled": 0, "won": 0, "lost": 0, "stolen": 0, "robbed": 0}
            }
        self.data[user_id_str].setdefault("balance", 0)
        self.data[user_id_str].setdefault("inventory", [])
        self.data[user_id_str].setdefault("cooldowns", {})
        self.data[user_id_str].setdefault("stats", {"earned": 0, "spent": 0, "gambled": 0, "won": 0, "lost": 0, "stolen": 0, "robbed": 0})
        return self.data[user_id_str]

    async def save_data(self):
        async with self.lock:
            await asyncio.to_thread(save_json_data, self.file_path, self.data)

    async def get_balance(self, user_id: int) -> int:
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            return user_data["balance"]

    async def update_balance(self, user_id: int, amount: int, reason: str = "unknown") -> int:
        if amount == 0:
            return await self.get_balance(user_id)
            
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            user_data["balance"] += amount
            
            if user_data["balance"] < 0:
                amount -= user_data["balance"] 
                user_data["balance"] = 0
                
            stats = user_data["stats"]
            if amount > 0:
                stats["earned"] = stats.get("earned", 0) + amount
                if reason == "gamble_win": stats["won"] = stats.get("won", 0) + amount
                elif reason == "rob_success": stats["robbed"] = stats.get("robbed", 0) + amount
            else: 
                actual_spent = abs(amount)
                stats["spent"] = stats.get("spent", 0) + actual_spent
                if reason == "gamble_loss": stats["lost"] = stats.get("lost", 0) + actual_spent
                elif reason in ["rob_fail_fine", "crime_fail_fine"]: stats["lost"] = stats.get("lost", 0) + actual_spent
                elif reason == "stolen": stats["stolen"] = stats.get("stolen", 0) + actual_spent
                     
            if reason in ["gamble_win", "gamble_loss"]:
                 bet_amount = abs(amount) 
                 stats["gambled"] = stats.get("gambled", 0) + bet_amount
                 
            # Salvar após cada atualização de saldo para persistência imediata
            await asyncio.to_thread(save_json_data, self.file_path, self.data)
            return user_data["balance"]

    async def get_cooldown(self, user_id: int, command_name: str) -> float | None:
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            return user_data["cooldowns"].get(command_name)

    async def set_cooldown(self, user_id: int, command_name: str, duration: int):
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            expires_at = time.time() + duration
            user_data["cooldowns"][command_name] = expires_at
            # O save_data() será chamado pela função que usa set_cooldown, geralmente junto com update_balance.

    async def check_cooldown(self, user_id: int, command_name: str) -> int | None:
        expires_at = await self.get_cooldown(user_id, command_name)
        if expires_at and time.time() < expires_at:
            return int(expires_at - time.time())
        return None

    async def get_inventory(self, user_id: int) -> list:
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            return user_data["inventory"]

    async def add_item_to_inventory(self, user_id: int, item_id: str, item_name: str, quantity: int = 1):
        if quantity <= 0: return
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
                # Adiciona o nome do item ao inventário para facilitar a exibição
                inventory.append({"id": item_id, "name": item_name, "quantity": quantity})
            await asyncio.to_thread(save_json_data, self.file_path, self.data)

    async def remove_item_from_inventory(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        if quantity <= 0: return False
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
            
            if item_index == -1 or current_quantity < quantity: return False
                
            inventory[item_index]["quantity"] -= quantity
            if inventory[item_index]["quantity"] <= 0:
                del inventory[item_index]
                
            await asyncio.to_thread(save_json_data, self.file_path, self.data)
            return True
            
    async def get_item_quantity(self, user_id: int, item_id: str) -> int:
        async with self.lock:
            user_data = await self._get_user_data(user_id)
            inventory = user_data["inventory"]
            for item in inventory:
                if item.get("id") == item_id:
                    return item.get("quantity", 0)
            return 0

    async def get_all_data(self) -> dict:
         async with self.lock:
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

    async def add_shop_item(self, item_id: str, name: str, price: int, description: str, emoji: str = "📦", role_id: int | None = None, usable: bool = False, use_description: str | None = None) -> bool:
        item_id = item_id.lower()
        if not item_id or not name or price < 0: return False
        async with self.lock:
            self.items[item_id] = {
                "name": name,
                "price": price,
                "description": description,
                "emoji": emoji,
                "role_id": role_id,
                "usable": usable,
                "use_description": use_description # Descrição para o comando /usar
            }
            await asyncio.to_thread(save_json_data, self.file_path, self.items)
            return True

    async def remove_shop_item(self, item_id: str) -> bool:
        item_id = item_id.lower()
        async with self.lock:
            if item_id in self.items:
                del self.items[item_id]
                await asyncio.to_thread(save_json_data, self.file_path, self.items)
                return True
            return False

# --- Views para Loja e Inventário ---
class ShopView(ui.View):
    def __init__(self, bot, shop_manager: ShopManager, economy_manager: EconomyManager, current_page: int, total_pages: int, items_on_page: list):
        super().__init__(timeout=180)
        self.bot = bot
        self.shop_manager = shop_manager
        self.economy_manager = economy_manager
        self.current_page = current_page
        self.total_pages = total_pages
        self.items_on_page = items_on_page # Lista de (item_id, item_data)

        self._add_navigation_buttons()
        self._add_item_buttons()

    def _add_navigation_buttons(self):
        if self.current_page > 1:
            self.add_item(ui.Button(label="⬅️ Anterior", style=ButtonStyle.grey, custom_id="shop_prev_page"))
        if self.current_page < self.total_pages:
            self.add_item(ui.Button(label="Próxima ➡️", style=ButtonStyle.grey, custom_id="shop_next_page"))

    def _add_item_buttons(self):
        for item_id, item_data in self.items_on_page:
            # Usar o emoji do item se disponível, senão um padrão
            button_emoji = item_data.get("emoji", "🛒")
            self.add_item(ui.Button(label=f"{item_data['name']} ({item_data['price']}{CURRENCY_SYMBOL})",
                                     style=ButtonStyle.green, 
                                     custom_id=f"buy_{item_id}", 
                                     emoji=button_emoji, 
                                     row=(self.children.index(self.children[-1]) // 5) + 1 if self.children else 1 )) # Organiza em linhas

    async def _update_view(self, interaction: Interaction):
        # Esta função será chamada para recriar a view com a nova página
        # (A lógica de paginação e embed será feita no comando /loja)
        # Aqui, apenas desabilitamos os botões da view antiga se necessário
        for item_btn in self.children:
            if isinstance(item_btn, ui.Button):
                item_btn.disabled = True
        await interaction.message.edit(view=self) # Desabilita botões da view antiga

    @ui.button(label="Placeholder", custom_id="shop_prev_page") # Será reconfigurado em _add_navigation_buttons
    async def prev_page_button(self, button: ui.Button, interaction: Interaction):
        # A lógica de mudar de página e reenviar o embed/view está no comando /loja
        # Este callback é mais para o interaction_check e para o bot saber que o botão foi clicado
        # O comando /loja precisa ser chamado novamente com a página decrementada
        await interaction.response.defer() # Apenas acusa o recebimento
        # O comando /loja que chamou esta view deve tratar a lógica de paginação

    @ui.button(label="Placeholder", custom_id="shop_next_page") # Será reconfigurado em _add_navigation_buttons
    async def next_page_button(self, button: ui.Button, interaction: Interaction):
        await interaction.response.defer()

    # Os botões de compra serão tratados dinamicamente no comando /loja
    # através de um listener ou verificando o custom_id na interação principal da view.

class InventoryView(ui.View):
    def __init__(self, bot, economy_manager: EconomyManager, shop_manager: ShopManager, user_id: int, current_page: int, total_pages: int, items_on_page: list):
        super().__init__(timeout=180)
        self.bot = bot
        self.economy_manager = economy_manager
        self.shop_manager = shop_manager
        self.user_id = user_id
        self.current_page = current_page
        self.total_pages = total_pages
        self.items_on_page = items_on_page # Lista de (item_id, item_data_inventory, item_data_shop)

        self._add_navigation_buttons()
        self._add_item_buttons()

    def _add_navigation_buttons(self):
        if self.current_page > 1:
            self.add_item(ui.Button(label="⬅️ Anterior", style=ButtonStyle.grey, custom_id="inv_prev_page"))
        if self.current_page < self.total_pages:
            self.add_item(ui.Button(label="Próxima ➡️", style=ButtonStyle.grey, custom_id="inv_next_page"))

    def _add_item_buttons(self):
        for item_id, inv_item_data, shop_item_data in self.items_on_page:
            if shop_item_data and shop_item_data.get("usable"):
                button_emoji = shop_item_data.get("emoji", "🔧")
                self.add_item(ui.Button(label=f"Usar {shop_item_data["name"]}", 
                                         style=ButtonStyle.blurple, 
                                         custom_id=f"use_{item_id}", 
                                         emoji=button_emoji,
                                         row=(self.children.index(self.children[-1]) // 5) + 1 if self.children else 1))

    # Callbacks para navegação e uso de itens serão tratados no comando /inventario

# --- Cog Economia --- 
class Economia(commands.Cog):
    """Cog responsável pelos comandos do sistema de economia."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.currency_emoji = get_emoji(bot, "money") 
        self.economy_manager = EconomyManager(ECONOMY_FILE)
        self.shop_manager = ShopManager(SHOP_FILE)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Cog Economia carregada.")
        print(f"[Economia] Usando moeda: {CURRENCY_NAME} ({self.currency_emoji})")
        self.active_shop_views = {} # interaction.message.id: ShopView instance
        self.active_inventory_views = {}

    # --- Comandos Principais --- 

    @nextcord.slash_command(name="saldo", description=f"Verifique seu saldo de {CURRENCY_NAME}.")
    async def saldo(self, interaction: Interaction, usuario: Member | User = SlashOption(description="Ver o saldo de outro usuário (opcional)", required=False)):
        target_user = usuario or interaction.user
        balance = await self.economy_manager.get_balance(target_user.id)
        embed = Embed(
            title=f"{self.currency_emoji} Saldo de {target_user.display_name}",
            description=f"Saldo atual: **{balance:,} {CURRENCY_SYMBOL}**",
            color=target_user.color if isinstance(target_user, Member) else Color.blue()
        )
        if target_user.display_avatar:
            embed.set_thumbnail(url=target_user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="bolsa", description=f"Alias para /saldo. Verifica seu saldo de {CURRENCY_NAME}.")
    async def bolsa_alias(self, interaction: Interaction, usuario: Member | User = SlashOption(description="Ver o saldo de outro usuário (opcional)", required=False)):
        await self.saldo(interaction, usuario)

    @nextcord.slash_command(name="diario", description=f"Resgate seus {CURRENCY_NAME} diários!")
    async def diario(self, interaction: Interaction):
        user_id = interaction.user.id
        command_name = "daily"
        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
            hours, remainder = divmod(cooldown_left, 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(
                f"{get_emoji(self.bot, 'clock')} Você já resgatou seu prêmio diário! Tente novamente em **{int(hours)}h {int(minutes)}m**.",
                ephemeral=True
            )
            return

        amount = random.randint(DAILY_MIN, DAILY_MAX)
        new_balance = await self.economy_manager.update_balance(user_id, amount, reason="daily")
        await self.economy_manager.set_cooldown(user_id, command_name, DAILY_COOLDOWN)
        await self.economy_manager.save_data()
        embed = Embed(
            title=f"{get_emoji(self.bot, 'gift')} Resgate Diário!",
            description=f"{get_emoji(self.bot, 'sparkle_happy')} Você resgatou **{amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}**!",
            color=Color.gold()
        )
        embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="trabalhar", description="Trabalhe para ganhar alguns Cristais Shirayuki.")
    async def trabalhar(self, interaction: Interaction):
        user_id = interaction.user.id
        command_name = "work"
        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
            hours, remainder = divmod(cooldown_left, 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'clock')} Você precisa descansar mais um pouco! Tente novamente em **{int(hours)}h {int(minutes)}m**.", ephemeral=True)
            return

        amount = random.randint(WORK_MIN, WORK_MAX)
        new_balance = await self.economy_manager.update_balance(user_id, amount, reason="work")
        await self.economy_manager.set_cooldown(user_id, command_name, WORK_COOLDOWN)
        await self.economy_manager.save_data()
        
        trabalhos_sucesso = [
            f"Você ajudou a organizar a biblioteca da mansão e ganhou {amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}!",
            f"Depois de um dia polindo os talheres de prata, você recebeu {amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}.",
            f"Sua jardinagem impecável rendeu {amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}!",
            f"Você passou o dia catalogando artefatos antigos e foi recompensado com {amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}."
        ]
        embed = Embed(title=f"{get_emoji(self.bot, 'work')} Trabalho Concluído!", description=random.choice(trabalhos_sucesso), color=Color.green())
        embed.add_field(name="Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="crime", description="Tente um pequeno crime para ganhar Cristais. Cuidado, pode dar errado!")
    async def crime(self, interaction: Interaction):
        user_id = interaction.user.id
        command_name = "crime"
        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
            minutes, seconds = divmod(cooldown_left, 60)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'clock')} Você precisa esperar a poeira baixar! Tente novamente em **{int(minutes)}m {int(seconds)}s**.", ephemeral=True)
            return

        await self.economy_manager.set_cooldown(user_id, command_name, CRIME_COOLDOWN)
        if random.random() < CRIME_SUCCESS_RATE:
            amount = random.randint(CRIME_SUCCESS_MIN, CRIME_SUCCESS_MAX)
            new_balance = await self.economy_manager.update_balance(user_id, amount, reason="crime_success")
            crimes_sucesso = [
                f"Você furtou uma carteira recheada e conseguiu {amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}!",
                f"Sua lábia convenceu um nobre a te dar {amount:,} {self.currency_emoji} {CURRENCY_SYMBOL} por uma \"proteção\".",
                f"Um pequeno desvio de mercadorias rendeu {amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}."
            ]
            embed = Embed(title=f"{get_emoji(self.bot, 'crime')} Crime Bem-Sucedido!", description=random.choice(crimes_sucesso), color=Color.dark_orange())
        else:
            fine = random.randint(CRIME_FAIL_FINE_MIN, CRIME_FAIL_FINE_MAX)
            new_balance = await self.economy_manager.update_balance(user_id, -fine, reason="crime_fail_fine")
            crimes_falha = [
                f"Você foi pego tentando roubar e teve que pagar uma multa de {fine:,} {self.currency_emoji} {CURRENCY_SYMBOL}!",
                f"Um guarda te viu e você largou tudo para trás, perdendo {fine:,} {self.currency_emoji} {CURRENCY_SYMBOL} no processo.",
                f"Sua tentativa de enganar um comerciante falhou e você foi multado em {fine:,} {self.currency_emoji} {CURRENCY_SYMBOL}."
            ]
            embed = Embed(title=f"{get_emoji(self.bot, 'error')} Crime Falhou!", description=random.choice(crimes_falha), color=Color.red())
        
        embed.add_field(name="Saldo Atual", value=f"**{new_balance:,} {self.currency_emoji}**")
        await self.economy_manager.save_data()
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="roubar", description="Tente roubar Cristais de outro usuário. Arriscado!")
    @application_checks.guild_only()
    async def roubar(self, interaction: Interaction, vitima: Member = SlashOption(description="O membro que você tentará roubar.", required=True)):
        user_id = interaction.user.id
        target_id = vitima.id
        command_name = "rob"

        if user_id == target_id:
            await interaction.response.send_message("Você não pode roubar a si mesmo!", ephemeral=True)
            return
        if vitima.bot:
            await interaction.response.send_message("Você não pode roubar um bot!", ephemeral=True)
            return

        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
            hours, remainder = divmod(cooldown_left, 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(f"{get_emoji(self.bot, 'clock')} Você precisa planejar seu próximo golpe! Tente novamente em **{int(hours)}h {int(minutes)}m**.", ephemeral=True)
            return

        await self.economy_manager.set_cooldown(user_id, command_name, ROB_COOLDOWN)
        target_balance = await self.economy_manager.get_balance(target_id)
        user_balance = await self.economy_manager.get_balance(user_id)

        if target_balance < WORK_MIN: # Não vale a pena roubar quem tem muito pouco
            await interaction.response.send_message(f"{vitima.display_name} não tem {CURRENCY_NAME} suficientes para valer o risco.", ephemeral=True)
            return

        if random.random() < ROB_SUCCESS_RATE:
            amount_stolen = min(int(target_balance * ROB_MAX_PERCENTAGE), random.randint(WORK_MIN, WORK_MAX * 2)) # Limita o roubo
            amount_stolen = max(amount_stolen, 1) # Garante que pelo menos 1 seja roubado se possível
            
            await self.economy_manager.update_balance(user_id, amount_stolen, reason="rob_success")
            new_balance_user = await self.economy_manager.update_balance(target_id, -amount_stolen, reason="stolen")
            
            embed = Embed(title=f"{get_emoji(self.bot, 'rob')} Roubo Bem-Sucedido!", description=f"Você conseguiu roubar **{amount_stolen:,} {self.currency_emoji} {CURRENCY_SYMBOL}** de {vitima.mention}!", color=Color.dark_purple())
            embed.add_field(name=f"Seu Saldo", value=f"**{(user_balance + amount_stolen):,} {self.currency_emoji}**")
            embed.add_field(name=f"Saldo de {vitima.display_name}", value=f"**{new_balance_user:,} {self.currency_emoji}**")
        else:
            fine_amount = min(int(user_balance * ROB_FAIL_FINE_PERCENTAGE), random.randint(CRIME_FAIL_FINE_MIN, CRIME_FAIL_FINE_MAX))
            fine_amount = max(fine_amount, 1)
            new_balance_user = await self.economy_manager.update_balance(user_id, -fine_amount, reason="rob_fail_fine")
            embed = Embed(title=f"{get_emoji(self.bot, 'error')} Roubo Falhou!", description=f"Você foi pego tentando roubar {vitima.mention} e perdeu **{fine_amount:,} {self.currency_emoji} {CURRENCY_SYMBOL}**!", color=Color.red())
            embed.add_field(name="Seu Saldo", value=f"**{new_balance_user:,} {self.currency_emoji}**")
        
        await self.economy_manager.save_data()
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="apostar", description="Aposte seus Cristais em um jogo de sorte (50/50 chance).")
    async def apostar(self, interaction: Interaction, quantia: int = SlashOption(description="A quantidade de Cristais para apostar.", required=True)):
        user_id = interaction.user.id
        command_name = "bet"

        if quantia <= 0:
            await interaction.response.send_message("Você precisa apostar uma quantia positiva!", ephemeral=True)
            return

        user_balance = await self.economy_manager.get_balance(user_id)
        if quantia > user_balance:
            await interaction.response.send_message(f"Você não tem {quantia:,} {CURRENCY_SYMBOL} para apostar. Seu saldo é {user_balance:,} {CURRENCY_SYMBOL}.", ephemeral=True)
            return

        cooldown_left = await self.economy_manager.check_cooldown(user_id, command_name)
        if cooldown_left:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'clock')} Você precisa esperar um pouco antes de apostar de novo! Tente em **{cooldown_left}s**.", ephemeral=True)
            return

        await self.economy_manager.set_cooldown(user_id, command_name, BET_COOLDOWN)
        
        # Simula o jogo (50/50)
        ganhou = random.choice([True, False])

        if ganhou:
            new_balance = await self.economy_manager.update_balance(user_id, quantia, reason="gamble_win") # Ganha a quantia apostada
            embed = Embed(title=f"{get_emoji(self.bot, 'win')} Você Ganhou!", description=f"Parabéns! Você apostou {quantia:,} {self.currency_emoji} e ganhou!", color=Color.green())
        else:
            new_balance = await self.economy_manager.update_balance(user_id, -quantia, reason="gamble_loss") # Perde a quantia apostada
            embed = Embed(title=f"{get_emoji(self.bot, 'lose')} Você Perdeu!", description=f"Que pena! Você apostou {quantia:,} {self.currency_emoji} e perdeu.", color=Color.red())
        
        embed.add_field(name="Seu Novo Saldo", value=f"**{new_balance:,} {self.currency_emoji}**")
        await self.economy_manager.save_data()
        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="ranking", description="Mostra o ranking dos mais ricos do servidor.")
    @application_checks.guild_only() # Faz sentido ser por servidor
    async def ranking(self, interaction: Interaction):
        await interaction.response.defer()
        all_data = await self.economy_manager.get_all_data()
        
        # Filtra usuários do servidor atual e ordena por saldo
        guild_members_ids = {str(member.id) for member in interaction.guild.members}
        server_economy_data = []
        for user_id_str, data in all_data.items():
            if user_id_str in guild_members_ids:
                try:
                    member = interaction.guild.get_member(int(user_id_str)) # Tenta obter o membro para nome
                    if member: # Garante que o membro ainda está no servidor
                        server_economy_data.append({"id": int(user_id_str), "name": member.display_name, "balance": data.get("balance", 0)})
                except ValueError:
                    pass # ID inválido, ignora

        sorted_users = sorted(server_economy_data, key=lambda x: x["balance"], reverse=True)

        embed = Embed(title=f"{get_emoji(self.bot, 'trophy')} Ranking de Riqueza - {interaction.guild.name}", color=Color.gold())
        if not sorted_users:
            embed.description = "Ninguém tem {CURRENCY_NAME} neste servidor ainda!"
        else:
            description_lines = []
            for i, user_data in enumerate(sorted_users[:10]): # Top 10
                rank_emoji = ""
                if i == 0: rank_emoji = "🥇 "
                elif i == 1: rank_emoji = "🥈 "
                elif i == 2: rank_emoji = "🥉 "
                else: rank_emoji = f"**{i+1}.** "
                description_lines.append(f"{rank_emoji}{user_data['name']}: **{user_data['balance']:,} {CURRENCY_SYMBOL}**")
            embed.description = "\n".join(description_lines)
        
        await interaction.followup.send(embed=embed)

    # --- Comandos da Loja e Inventário ---
    async def _generate_shop_embed_and_view(self, interaction: Interaction, page: int = 1):
        all_items = await self.shop_manager.get_all_items()
        if not all_items:
            await interaction.response.send_message("A loja está vazia no momento!", ephemeral=True)
            return None, None

        items_per_page = 5 # Número de itens por página na loja (para botões)
        item_ids = list(all_items.keys())
        total_pages = (len(item_ids) + items_per_page - 1) // items_per_page
        page = max(1, min(page, total_pages))

        start_index = (page - 1) * items_per_page
        end_index = start_index + items_per_page
        items_on_page_ids = item_ids[start_index:end_index]
        
        items_on_page_data = [(item_id, all_items[item_id]) for item_id in items_on_page_ids]

        embed = Embed(title=f"{get_emoji(self.bot, 'shop')} Loja da Shirayuki - Página {page}/{total_pages}", color=Color.dark_theme())
        if not items_on_page_data:
            embed.description = "Nenhum item nesta página."
        else:
            desc_lines = []
            for item_id, item in items_on_page_data:
                desc_lines.append(f"{item.get('emoji', '📦')} **{item['name']}** - {item['price']:,} {CURRENCY_SYMBOL}\n*ID: `{item_id}` | {item['description']}*")
            embed.description = "\n\n".join(desc_lines)
        
        view = ShopView(self.bot, self.shop_manager, self.economy_manager, page, total_pages, items_on_page_data)
        return embed, view

    @nextcord.slash_command(name="loja", description="Veja os itens disponíveis para compra.")
    async def loja(self, interaction: Interaction, pagina: int = SlashOption(description="Número da página da loja", required=False, default=1)):
        embed, view = await self._generate_shop_embed_and_view(interaction, page=pagina)
        if embed and view:
            # Remove a view antiga se houver uma para esta interação/mensagem
            if interaction.message and interaction.message.id in self.active_shop_views:
                old_view = self.active_shop_views.pop(interaction.message.id)
                # Não precisa desabilitar botões aqui, pois a mensagem será editada com nova view
            
            if interaction.response.is_done():
                msg = await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)
                msg = await interaction.original_message() # Pega a mensagem enviada
            
            if msg: # Adiciona a nova view ativa
                 self.active_shop_views[msg.id] = view
        elif embed is None and view is None: # Loja vazia, já foi respondido
            pass
        else: # Algum erro inesperado
            if not interaction.response.is_done():
                 await interaction.response.send_message("Erro ao carregar a loja.", ephemeral=True)

    @commands.Cog.listener("on_interaction")
    async def on_shop_interaction(self, interaction: Interaction):
        if not interaction.message or not interaction.data or not interaction.data.get("custom_id"):
            return

        custom_id = interaction.data["custom_id"]
        
        # Lógica de Paginação da Loja
        if custom_id in ["shop_prev_page", "shop_next_page"]:
            if interaction.message.id not in self.active_shop_views:
                await interaction.response.send_message("Esta loja expirou ou não é mais válida.", ephemeral=True)
                return
            
            active_view: ShopView = self.active_shop_views[interaction.message.id]
            current_page = active_view.current_page
            new_page = current_page - 1 if custom_id == "shop_prev_page" else current_page + 1

            embed, new_view = await self._generate_shop_embed_and_view(interaction, page=new_page)
            if embed and new_view:
                # Desabilita botões da view antiga e remove da lista ativa
                for item_btn in active_view.children:
                    if isinstance(item_btn, ui.Button): item_btn.disabled = True
                await interaction.message.edit(view=active_view) # Salva a desabilitação
                del self.active_shop_views[interaction.message.id]

                await interaction.response.edit_message(embed=embed, view=new_view)
                self.active_shop_views[interaction.message.id] = new_view # Adiciona a nova view
            else:
                await interaction.response.send_message("Não foi possível carregar a página da loja.", ephemeral=True)
            return

        # Lógica de Compra de Itens
        if custom_id.startswith("buy_"):
            if interaction.message.id not in self.active_shop_views:
                await interaction.response.send_message("Esta loja expirou ou não é mais válida.", ephemeral=True)
                return

            item_id_to_buy = custom_id.split("_", 1)[1]
            item_data = await self.shop_manager.get_item(item_id_to_buy)

            if not item_data:
                await interaction.response.send_message("Este item não está mais disponível.", ephemeral=True)
                return

            user_balance = await self.economy_manager.get_balance(interaction.user.id)
            if user_balance < item_data["price"]:
                await interaction.response.send_message(f"Você não tem {CURRENCY_SYMBOL} suficientes! Você precisa de {item_data['price']:,}, mas tem {user_balance:,}.", ephemeral=True)
                return

            # Processa a compra
            await self.economy_manager.update_balance(interaction.user.id, -item_data["price"], reason="shop_purchase")
            await self.economy_manager.add_item_to_inventory(interaction.user.id, item_id_to_buy, item_data["name"])
            await self.economy_manager.save_data() # Garante que tudo seja salvo

            await interaction.response.send_message(f"{get_emoji(self.bot, 'buy')} Você comprou **{item_data['name']}** por {item_data['price']:,} {CURRENCY_SYMBOL}!", ephemeral=True)
            
            # Opcional: Atualizar a view da loja se a quantidade de itens mudar ou algo assim (não implementado aqui)
            return

    async def _generate_inventory_embed_and_view(self, interaction: Interaction, target_user: User | Member, page: int = 1):
        user_inventory = await self.economy_manager.get_inventory(target_user.id)
        if not user_inventory:
            embed = Embed(title=f"{get_emoji(self.bot, 'inventory')} Inventário de {target_user.display_name}", description="Seu inventário está vazio.", color=target_user.color if isinstance(target_user, Member) else Color.default())
            return embed, None

        items_per_page = 5 # Itens por página para botões de "usar"
        total_pages = (len(user_inventory) + items_per_page - 1) // items_per_page
        page = max(1, min(page, total_pages))

        start_index = (page - 1) * items_per_page
        end_index = start_index + items_per_page
        items_on_page_inv_data = user_inventory[start_index:end_index]
        
        # Pega dados da loja para os itens no inventário (nome, emoji, usabilidade)
        items_on_page_full_data = []
        for inv_item in items_on_page_inv_data:
            shop_item_data = await self.shop_manager.get_item(inv_item["id"])
            items_on_page_full_data.append((inv_item["id"], inv_item, shop_item_data))

        embed = Embed(title=f"{get_emoji(self.bot, 'inventory')} Inventário de {target_user.display_name} - Página {page}/{total_pages}", color=target_user.color if isinstance(target_user, Member) else Color.default())
        desc_lines = []
        for item_id, inv_item, shop_item in items_on_page_full_data:
            emoji = shop_item.get("emoji", "📦") if shop_item else "📦"
            name = shop_item.get("name", inv_item["id"]) if shop_item else inv_item["id"] # Usa nome da loja se disponível
            desc_lines.append(f"{emoji} **{name}** (ID: `{inv_item['id']}`) - Quantidade: {inv_item['quantity']}")
        embed.description = "\n".join(desc_lines) if desc_lines else "Nenhum item nesta página."
        
        view = InventoryView(self.bot, self.economy_manager, self.shop_manager, target_user.id, page, total_pages, items_on_page_full_data)
        return embed, view

    @nextcord.slash_command(name="inventario", description="Mostra seu inventário de itens.")
    async def inventario(self, interaction: Interaction, pagina: int = SlashOption(description="Número da página do inventário", required=False, default=1)):
        embed, view = await self._generate_inventory_embed_and_view(interaction, interaction.user, page=pagina)
        
        if interaction.message and interaction.message.id in self.active_inventory_views:
            old_view = self.active_inventory_views.pop(interaction.message.id)

        if interaction.response.is_done():
            msg = await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
            msg = await interaction.original_message()
        
        if msg and view: # Adiciona a nova view ativa se ela existir (não é None)
            self.active_inventory_views[msg.id] = view

    @commands.Cog.listener("on_interaction")
    async def on_inventory_interaction(self, interaction: Interaction):
        if not interaction.message or not interaction.data or not interaction.data.get("custom_id"):
            return

        custom_id = interaction.data["custom_id"]

        # Lógica de Paginação do Inventário
        if custom_id in ["inv_prev_page", "inv_next_page"]:
            if interaction.message.id not in self.active_inventory_views:
                await interaction.response.send_message("Este inventário expirou ou não é mais válido.", ephemeral=True)
                return
            
            active_view: InventoryView = self.active_inventory_views[interaction.message.id]
            current_page = active_view.current_page
            new_page = current_page - 1 if custom_id == "inv_prev_page" else current_page + 1

            # Precisamos do target_user para gerar o novo embed/view
            # Assumindo que o interaction.user é o dono do inventário para esta view
            embed, new_view = await self._generate_inventory_embed_and_view(interaction, interaction.user, page=new_page)
            if embed and new_view:
                for item_btn in active_view.children:
                    if isinstance(item_btn, ui.Button): item_btn.disabled = True
                await interaction.message.edit(view=active_view)
                del self.active_inventory_views[interaction.message.id]

                await interaction.response.edit_message(embed=embed, view=new_view)
                self.active_inventory_views[interaction.message.id] = new_view
            else:
                await interaction.response.send_message("Não foi possível carregar a página do inventário.", ephemeral=True)
            return

        # Lógica de Uso de Itens
        if custom_id.startswith("use_"):
            if interaction.message.id not in self.active_inventory_views:
                await interaction.response.send_message("Este inventário expirou ou não é mais válido.", ephemeral=True)
                return

            item_id_to_use = custom_id.split("_", 1)[1]
            shop_item_data = await self.shop_manager.get_item(item_id_to_use)

            if not shop_item_data or not shop_item_data.get("usable"):
                await interaction.response.send_message("Este item não pode ser usado ou não existe mais.", ephemeral=True)
                return

            has_item = await self.economy_manager.get_item_quantity(interaction.user.id, item_id_to_use) > 0
            if not has_item:
                await interaction.response.send_message("Você não possui este item para usar.", ephemeral=True)
                return

            # Processa o uso do item
            # Exemplo: dar um cargo se role_id estiver definido
            success_msg = f"{get_emoji(self.bot, 'use')} Você usou **{shop_item_data['name']}**!"
            if shop_item_data.get("use_description"):
                success_msg += f"\n{shop_item_data['use_description']}"
            
            action_taken = False
            if shop_item_data.get("role_id") and interaction.guild:
                try:
                    role_to_give = interaction.guild.get_role(shop_item_data["role_id"])
                    if role_to_give and isinstance(interaction.user, Member):
                        if role_to_give in interaction.user.roles:
                            success_msg = f"Você já possui o cargo {role_to_give.mention} fornecido por este item."
                        else:
                            await interaction.user.add_roles(role_to_give, reason=f"Uso do item {shop_item_data['name']}")
                            success_msg += f"\nVocê recebeu o cargo {role_to_give.mention}!"
                        action_taken = True
                    else:
                        success_msg = "Não foi possível encontrar o cargo associado a este item no servidor."
                except nextcord.Forbidden:
                    success_msg = "Não tenho permissão para dar cargos neste servidor."
                except Exception as e:
                    success_msg = f"Erro ao tentar dar o cargo: {e}"
                    print(f"[ERRO USO ITEM] {e}")
            
            # Remove o item do inventário se uma ação foi tomada ou se não é um item de cargo
            # (Pode-se adicionar lógica para itens consumíveis vs. permanentes aqui)
            if action_taken or not shop_item_data.get("role_id"):
                 await self.economy_manager.remove_item_from_inventory(interaction.user.id, item_id_to_use)
                 await self.economy_manager.save_data()

            await interaction.response.send_message(success_msg, ephemeral=True)
            
            # Atualiza a view do inventário
            active_view: InventoryView = self.active_inventory_views[interaction.message.id]
            embed, new_view = await self._generate_inventory_embed_and_view(interaction, interaction.user, page=active_view.current_page)
            if embed:
                for item_btn in active_view.children:
                    if isinstance(item_btn, ui.Button): item_btn.disabled = True
                await interaction.message.edit(view=active_view)
                del self.active_inventory_views[interaction.message.id]
                
                # Envia a nova mensagem de inventário (não edita a interação original do botão)
                # Isso é um pouco complicado porque a interação original do botão já foi respondida.
                # Idealmente, a mensagem original do /inventario seria editada.
                # Por simplicidade, vamos apenas assumir que o usuário pode rodar /inventario novamente.
                # Ou, se a interação original do /inventario ainda for válida:
                try:
                    original_inv_message = await interaction.channel.fetch_message(interaction.message.id)
                    await original_inv_message.edit(embed=embed, view=new_view)
                    if new_view: self.active_inventory_views[interaction.message.id] = new_view
                except (nextcord.NotFound, nextcord.HTTPException):
                     pass # Não foi possível editar a mensagem original
            return

    # --- Comandos de Administração de Economia ---
    @nextcord.slash_command(name="econadmin", description="Comandos de administração da economia.")
    async def econadmin(self, interaction: Interaction):
        pass # Este é um grupo de subcomandos

    @econadmin.subcommand(name="setbal", description="Define o saldo de um usuário.")
    @application_checks.has_role(ADMIN_ROLE_ID) # Ou use has_permissions
    async def econadmin_setbal(self, interaction: Interaction, 
                               usuario: Member = SlashOption(description="O usuário para modificar o saldo.", required=True),
                               quantia: int = SlashOption(description="A nova quantia de Cristais Shirayuki.", required=True)):
        if quantia < 0:
            await interaction.response.send_message("O saldo não pode ser negativo.", ephemeral=True)
            return
        
        # Para definir, precisamos calcular a diferença do saldo atual
        current_balance = await self.economy_manager.get_balance(usuario.id)
        amount_to_change = quantia - current_balance
        
        new_balance = await self.economy_manager.update_balance(usuario.id, amount_to_change, reason="admin_set")
        await self.economy_manager.save_data()
        await interaction.response.send_message(f"{get_emoji(self.bot, 'admin')} O saldo de {usuario.mention} foi definido para **{new_balance:,} {CURRENCY_SYMBOL}**.", ephemeral=True)

    @econadmin.subcommand(name="addbal", description="Adiciona Cristais ao saldo de um usuário.")
    @application_checks.has_role(ADMIN_ROLE_ID)
    async def econadmin_addbal(self, interaction: Interaction, 
                              usuario: Member = SlashOption(description="O usuário para adicionar saldo.", required=True),
                              quantia: int = SlashOption(description="A quantia de Cristais para adicionar.", required=True)):
        if quantia <= 0:
            await interaction.response.send_message("A quantia para adicionar deve ser positiva.", ephemeral=True)
            return
        new_balance = await self.economy_manager.update_balance(usuario.id, quantia, reason="admin_add")
        await self.economy_manager.save_data()
        await interaction.response.send_message(f"{get_emoji(self.bot, 'admin')} **{quantia:,} {CURRENCY_SYMBOL}** adicionados ao saldo de {usuario.mention}. Novo saldo: **{new_balance:,} {CURRENCY_SYMBOL}**.", ephemeral=True)

    @econadmin.subcommand(name="rembal", description="Remove Cristais do saldo de um usuário.")
    @application_checks.has_role(ADMIN_ROLE_ID)
    async def econadmin_rembal(self, interaction: Interaction, 
                              usuario: Member = SlashOption(description="O usuário para remover saldo.", required=True),
                              quantia: int = SlashOption(description="A quantia de Cristais para remover.", required=True)):
        if quantia <= 0:
            await interaction.response.send_message("A quantia para remover deve ser positiva.", ephemeral=True)
            return
        new_balance = await self.economy_manager.update_balance(usuario.id, -quantia, reason="admin_remove")
        await self.economy_manager.save_data()
        await interaction.response.send_message(f"{get_emoji(self.bot, 'admin')} **{quantia:,} {CURRENCY_SYMBOL}** removidos do saldo de {usuario.mention}. Novo saldo: **{new_balance:,} {CURRENCY_SYMBOL}**.", ephemeral=True)

    @econadmin.subcommand(name="resetuser", description="Reseta todos os dados de economia de um usuário.")
    @application_checks.has_role(ADMIN_ROLE_ID)
    async def econadmin_resetuser(self, interaction: Interaction, usuario: Member = SlashOption(description="O usuário para resetar.", required=True)):
        user_id_str = str(usuario.id)
        async with self.economy_manager.lock:
            if user_id_str in self.economy_manager.data:
                del self.economy_manager.data[user_id_str]
                await self.economy_manager.save_data()
                await interaction.response.send_message(f"{get_emoji(self.bot, 'admin')} Os dados de economia de {usuario.mention} foram resetados.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{usuario.mention} não possui dados de economia para resetar.", ephemeral=True)

    @econadmin.subcommand(name="addshopitem", description="Adiciona um novo item à loja.")
    @application_checks.has_role(ADMIN_ROLE_ID)
    async def econadmin_addshopitem(self, interaction: Interaction,
                                    item_id: str = SlashOption(description="ID único para o item (ex: 'espada_curta')", required=True),
                                    nome: str = SlashOption(description="Nome do item para exibição.", required=True),
                                    preco: int = SlashOption(description="Preço do item em Cristais.", required=True),
                                    descricao: str = SlashOption(description="Descrição do item.", required=True),
                                    emoji: str = SlashOption(description="Emoji para o item (opcional).", required=False, default="📦"),
                                    cargo_id: Optional[str] = SlashOption(description="ID do cargo a ser dado ao usar (opcional).", required=False),
                                    usavel: bool = SlashOption(description="Se o item pode ser usado com /usar (padrão: Não).", required=False, default=False),
                                    desc_uso: Optional[str] = SlashOption(description="Mensagem mostrada ao usar o item (opcional).", required=False)):
        if preco < 0:
            await interaction.response.send_message("O preço do item não pode ser negativo.", ephemeral=True)
            return
        
        role_id_int = None
        if cargo_id:
            try:
                role_id_int = int(cargo_id)
            except ValueError:
                await interaction.response.send_message("ID do Cargo inválido. Deve ser um número.", ephemeral=True)
                return

        success = await self.shop_manager.add_shop_item(item_id, nome, preco, descricao, emoji, role_id_int, usavel, desc_uso)
        if success:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'success')} Item **{nome}** (ID: `{item_id}`) adicionado/atualizado na loja!", ephemeral=True)
        else:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Falha ao adicionar item. Verifique os parâmetros.", ephemeral=True)

    @econadmin.subcommand(name="removeshopitem", description="Remove um item da loja.")
    @application_checks.has_role(ADMIN_ROLE_ID)
    async def econadmin_removeshopitem(self, interaction: Interaction, item_id: str = SlashOption(description="ID do item a ser removido.", required=True)):
        success = await self.shop_manager.remove_shop_item(item_id)
        if success:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'success')} Item com ID `{item_id}` removido da loja.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{get_emoji(self.bot, 'error')} Item com ID `{item_id}` não encontrado na loja.", ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(Economia(bot))
