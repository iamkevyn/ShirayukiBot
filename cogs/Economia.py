from typing import Optional # ADICIONADO PARA CORRIGIR NameError
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
                self.add_item(ui.Button(label=f"Usar {shop_item_data['name']}", 
                                         style=ButtonStyle.blurple, 
                                         custom_id=f"use_{item_id}", 
                                         emoji=button_emoji,
                                         row=(self.children.index(self.children[-1]) // 5) + 1 if self.children else 1))

# --- Cog Principal de Economia ---
class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.economy_manager = EconomyManager(ECONOMY_FILE)
        self.shop_manager = ShopManager(SHOP_FILE)
        self.daily_check.start()
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Cog Economia carregada.')

    def cog_unload(self):
        self.daily_check.cancel()
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Cog Economia descarregada.')

    async def send_error_embed(self, interaction: Interaction, title: str, description: str):
        embed = Embed(title=f"{get_emoji(self.bot, 'error')} {title}", description=description, color=Color.red())
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def send_success_embed(self, interaction: Interaction, title: str, description: str):
        embed = Embed(title=f"{get_emoji(self.bot, 'success')} {title}", description=description, color=Color.green())
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def send_info_embed(self, interaction: Interaction, title: str, description: str, fields: list = None):
        embed = Embed(title=f"{get_emoji(self.bot, 'info')} {title}", description=description, color=Color.blue())
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Comandos de Economia ---
    @nextcord.slash_command(name="saldo", description="Verifica seu saldo ou o de outro usuário.")
    async def saldo(self, interaction: Interaction, usuario: Optional[Member] = SlashOption(description="Usuário para verificar o saldo (opcional).", required=False)):
        target_user = usuario or interaction.user
        balance = await self.economy_manager.get_balance(target_user.id)
        emoji_money = get_emoji(self.bot, "money")
        embed = Embed(title=f"{emoji_money} Saldo de {target_user.display_name}", 
                        description=f"Você possui **{balance} {CURRENCY_SYMBOL}**.", 
                        color=Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="daily", description=f"Colete seus {CURRENCY_NAME} diários!")
    async def daily(self, interaction: Interaction):
        user_id = interaction.user.id
        cooldown_remaining = await self.economy_manager.check_cooldown(user_id, "daily")
        emoji_clock = get_emoji(self.bot, "clock")
        if cooldown_remaining:
            await self.send_error_embed(interaction, "Cooldown Ativo", f"{emoji_clock} Você já coletou seu daily. Tente novamente em **{timedelta(seconds=cooldown_remaining)}**.")
            return

        amount = random.randint(DAILY_MIN, DAILY_MAX)
        await self.economy_manager.update_balance(user_id, amount, reason="daily_collection")
        await self.economy_manager.set_cooldown(user_id, "daily", DAILY_COOLDOWN)
        emoji_gift = get_emoji(self.bot, "gift")
        await self.send_success_embed(interaction, "Daily Coletado!", f"{emoji_gift} Você coletou **{amount} {CURRENCY_SYMBOL}**! Volte em 24 horas.")

    @nextcord.slash_command(name="trabalhar", description="Trabalhe para ganhar alguns Cristais Shirayuki.")
    async def trabalhar(self, interaction: Interaction):
        user_id = interaction.user.id
        cooldown_remaining = await self.economy_manager.check_cooldown(user_id, "work")
        emoji_clock = get_emoji(self.bot, "clock")
        if cooldown_remaining:
            await self.send_error_embed(interaction, "Cooldown Ativo", f"{emoji_clock} Você já trabalhou recentemente. Tente novamente em **{timedelta(seconds=cooldown_remaining)}**.")
            return

        amount = random.randint(WORK_MIN, WORK_MAX)
        await self.economy_manager.update_balance(user_id, amount, reason="work_payment")
        await self.economy_manager.set_cooldown(user_id, "work", WORK_COOLDOWN)
        emoji_work = get_emoji(self.bot, "work")
        await self.send_success_embed(interaction, "Trabalho Concluído!", f"{emoji_work} Você trabalhou e ganhou **{amount} {CURRENCY_SYMBOL}**.")

    @nextcord.slash_command(name="crime", description="Tente um crime arriscado para ganhar (ou perder) Cristais.")
    async def crime(self, interaction: Interaction):
        user_id = interaction.user.id
        cooldown_remaining = await self.economy_manager.check_cooldown(user_id, "crime")
        emoji_clock = get_emoji(self.bot, "clock")
        if cooldown_remaining:
            await self.send_error_embed(interaction, "Cooldown Ativo", f"{emoji_clock} Você já cometeu um crime recentemente. Tente novamente em **{timedelta(seconds=cooldown_remaining)}**.")
            return

        await self.economy_manager.set_cooldown(user_id, "crime", CRIME_COOLDOWN)
        emoji_crime = get_emoji(self.bot, "crime")
        emoji_sad = get_emoji(self.bot, "sad")

        if random.random() < CRIME_SUCCESS_RATE:
            amount = random.randint(CRIME_SUCCESS_MIN, CRIME_SUCCESS_MAX)
            await self.economy_manager.update_balance(user_id, amount, reason="crime_success")
            await self.send_success_embed(interaction, "Crime Bem-Sucedido!", f"{emoji_crime} Você cometeu um crime e lucrou **{amount} {CURRENCY_SYMBOL}**!")
        else:
            fine = random.randint(CRIME_FAIL_FINE_MIN, CRIME_FAIL_FINE_MAX)
            current_balance = await self.economy_manager.get_balance(user_id)
            fine_taken = min(fine, current_balance) # Não pode perder mais do que tem
            await self.economy_manager.update_balance(user_id, -fine_taken, reason="crime_fail_fine")
            if fine_taken > 0:
                await self.send_error_embed(interaction, "Crime Falhou!", f"{emoji_sad} Você foi pego e multado em **{fine_taken} {CURRENCY_SYMBOL}**.")
            else:
                await self.send_error_embed(interaction, "Crime Falhou!", f"{emoji_sad} Você foi pego, mas não tinha {CURRENCY_SYMBOL} para serem multados.")

    @nextcord.slash_command(name="roubar", description="Tente roubar Cristais de outro usuário.")
    async def roubar(self, interaction: Interaction, 
                     vitima: Member = SlashOption(description="Usuário que você tentará roubar.", required=True)):
        robber_id = interaction.user.id
        victim_id = vitima.id

        if robber_id == victim_id:
            await self.send_error_embed(interaction, "Ação Inválida", "Você não pode roubar de si mesmo.")
            return
        
        if vitima.bot:
            await self.send_error_embed(interaction, "Ação Inválida", "Você não pode roubar de um bot.")
            return

        cooldown_remaining = await self.economy_manager.check_cooldown(robber_id, "rob")
        emoji_clock = get_emoji(self.bot, "clock")
        if cooldown_remaining:
            await self.send_error_embed(interaction, "Cooldown Ativo", f"{emoji_clock} Você já tentou um roubo recentemente. Tente novamente em **{timedelta(seconds=cooldown_remaining)}**.")
            return

        await self.economy_manager.set_cooldown(robber_id, "rob", ROB_COOLDOWN)
        
        victim_balance = await self.economy_manager.get_balance(victim_id)
        if victim_balance < 100: # Mínimo para valer a pena roubar
            await self.send_error_embed(interaction, "Alvo Pobre", f"{vitima.display_name} não tem {CURRENCY_SYMBOL} suficientes para serem roubados.")
            return

        emoji_rob = get_emoji(self.bot, "rob")
        emoji_sad = get_emoji(self.bot, "sad")

        if random.random() < ROB_SUCCESS_RATE:
            max_stealable = int(victim_balance * ROB_MAX_PERCENTAGE)
            amount_stolen = random.randint(1, max(1, max_stealable)) # Garante que roube pelo menos 1 se max_stealable for > 0
            
            await self.economy_manager.update_balance(robber_id, amount_stolen, reason="rob_success")
            await self.economy_manager.update_balance(victim_id, -amount_stolen, reason="stolen")
            await self.send_success_embed(interaction, "Roubo Bem-Sucedido!", f"{emoji_rob} Você roubou **{amount_stolen} {CURRENCY_SYMBOL}** de {vitima.mention}!")
        else:
            robber_balance = await self.economy_manager.get_balance(robber_id)
            fine = int(robber_balance * ROB_FAIL_FINE_PERCENTAGE)
            fine_taken = min(fine, robber_balance)
            await self.economy_manager.update_balance(robber_id, -fine_taken, reason="rob_fail_fine")
            if fine_taken > 0:
                await self.send_error_embed(interaction, "Roubo Falhou!", f"{emoji_sad} Você foi pego tentando roubar {vitima.mention} e perdeu **{fine_taken} {CURRENCY_SYMBOL}**.")
            else:
                 await self.send_error_embed(interaction, "Roubo Falhou!", f"{emoji_sad} Você foi pego tentando roubar {vitima.mention}, mas não tinha {CURRENCY_SYMBOL} para serem multados.")

    @nextcord.slash_command(name="apostar", description="Aposte seus Cristais Shirayuki!")
    async def apostar(self, interaction: Interaction, 
                      valor: int = SlashOption(description="Quantidade de Cristais para apostar.", required=True)):
        user_id = interaction.user.id

        if valor <= 0:
            await self.send_error_embed(interaction, "Valor Inválido", "Você deve apostar uma quantidade positiva de Cristais.")
            return

        current_balance = await self.economy_manager.get_balance(user_id)
        if valor > current_balance:
            await self.send_error_embed(interaction, "Saldo Insuficiente", f"Você não tem **{valor} {CURRENCY_SYMBOL}** para apostar. Seu saldo é **{current_balance} {CURRENCY_SYMBOL}**.")
            return
        
        cooldown_remaining = await self.economy_manager.check_cooldown(user_id, "bet")
        emoji_clock = get_emoji(self.bot, "clock")
        if cooldown_remaining:
            await self.send_error_embed(interaction, "Cooldown Ativo", f"{emoji_clock} Você já apostou recentemente. Tente novamente em **{timedelta(seconds=cooldown_remaining)}**.")
            return
        
        await self.economy_manager.set_cooldown(user_id, "bet", BET_COOLDOWN)

        # Simples jogo de 50/50
        emoji_win = get_emoji(self.bot, "win")
        emoji_lose = get_emoji(self.bot, "lose")
        emoji_dice = get_emoji(self.bot, "dice")

        await interaction.response.defer(ephemeral=True)
        await asyncio.sleep(1) # Pequena pausa para suspense

        if random.random() < 0.48: # Chance de ganhar um pouco menor que 50% para a "casa"
            await self.economy_manager.update_balance(user_id, valor, reason="gamble_win")
            await self.send_success_embed(interaction, f"{emoji_dice} Você Ganhou!", f"{emoji_win} Parabéns! Você apostou **{valor} {CURRENCY_SYMBOL}** e ganhou! Seu novo saldo é **{current_balance + valor} {CURRENCY_SYMBOL}**.")
        else:
            await self.economy_manager.update_balance(user_id, -valor, reason="gamble_loss")
            await self.send_error_embed(interaction, f"{emoji_dice} Você Perdeu!", f"{emoji_lose} Que pena! Você apostou **{valor} {CURRENCY_SYMBOL}** e perdeu. Seu novo saldo é **{current_balance - valor} {CURRENCY_SYMBOL}**.")

    @nextcord.slash_command(name="loja", description="Mostra os itens disponíveis para compra.")
    async def loja(self, interaction: Interaction, pagina: int = SlashOption(description="Número da página da loja.", required=False, default=1)):
        all_items_dict = await self.shop_manager.get_all_items()
        if not all_items_dict:
            await self.send_info_embed(interaction, "Loja Vazia", "Ainda não há itens na loja.")
            return

        items_per_page = 5 # Máximo de 5 botões de item por linha na view, mais botões de navegação
        item_ids = list(all_items_dict.keys())
        total_items = len(item_ids)
        total_pages = (total_items + items_per_page - 1) // items_per_page

        if not 1 <= pagina <= total_pages and total_pages > 0:
            await self.send_error_embed(interaction, "Página Inválida", f"Por favor, insira um número de página entre 1 e {total_pages}.")
            return
        
        start_index = (pagina - 1) * items_per_page
        end_index = start_index + items_per_page
        current_item_ids_on_page = item_ids[start_index:end_index]
        
        items_on_page_data = [] # Lista de (item_id, item_data)
        description_parts = []
        for item_id in current_item_ids_on_page:
            item_data = all_items_dict[item_id]
            items_on_page_data.append((item_id, item_data))
            emoji = item_data.get("emoji", "📦")
            description_parts.append(f"{emoji} **{item_data['name']}** - {item_data['price']} {CURRENCY_SYMBOL}\n*ID: `{item_id}`* | {item_data['description']}")
        
        embed_description = "\n\n".join(description_parts) if description_parts else "Nenhum item nesta página."

        embed = Embed(title=f"{get_emoji(self.bot, 'shop')} Loja de Itens - Página {pagina}/{total_pages}", 
                        description=embed_description, 
                        color=Color.purple())
        embed.set_footer(text=f"Use /comprar <id_do_item> para adquirir um item.")

        view = ShopView(self.bot, self.shop_manager, self.economy_manager, pagina, total_pages, items_on_page_data)
        
        if interaction.response.is_done():
            # Se a interação já foi respondida (ex: por um botão da view anterior)
            await interaction.edit_original_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @nextcord.slash_command(name="comprar", description="Compra um item da loja.")
    async def comprar(self, interaction: Interaction, 
                      item_id: str = SlashOption(description="ID do item que você quer comprar.", required=True), 
                      quantidade: int = SlashOption(description="Quantidade a comprar (padrão 1).", required=False, default=1)):
        item_id = item_id.lower()
        if quantidade <= 0:
            await self.send_error_embed(interaction, "Quantidade Inválida", "A quantidade deve ser maior que zero.")
            return

        item_data = await self.shop_manager.get_item(item_id)
        if not item_data:
            await self.send_error_embed(interaction, "Item Não Encontrado", f"O item com ID `{item_id}` não existe na loja.")
            return

        total_cost = item_data["price"] * quantidade
        user_balance = await self.economy_manager.get_balance(interaction.user.id)

        if user_balance < total_cost:
            await self.send_error_embed(interaction, "Saldo Insuficiente", 
                                      f"Você precisa de **{total_cost} {CURRENCY_SYMBOL}** para comprar {quantidade}x '{item_data['name']}', mas você só tem **{user_balance} {CURRENCY_SYMBOL}**.")
            return

        await self.economy_manager.update_balance(interaction.user.id, -total_cost, reason="item_purchase")
        await self.economy_manager.add_item_to_inventory(interaction.user.id, item_id, item_data["name"], quantidade)
        
        emoji_buy = get_emoji(self.bot, "buy")
        await self.send_success_embed(interaction, "Compra Realizada!", 
                                    f"{emoji_buy} Você comprou {quantidade}x **{item_data['name']}** por **{total_cost} {CURRENCY_SYMBOL}**.")

    @nextcord.slash_command(name="inventario", description="Mostra os itens que você possui.")
    async def inventario(self, interaction: Interaction, pagina: int = SlashOption(description="Número da página do inventário.", required=False, default=1)):
        user_id = interaction.user.id
        inventory_list = await self.economy_manager.get_inventory(user_id)

        if not inventory_list:
            await self.send_info_embed(interaction, "Inventário Vazio", "Você não possui nenhum item.")
            return

        items_per_page = 5 # Similar à loja, para botões de "usar"
        total_items = len(inventory_list)
        total_pages = (total_items + items_per_page - 1) // items_per_page

        if not 1 <= pagina <= total_pages and total_pages > 0:
            await self.send_error_embed(interaction, "Página Inválida", f"Por favor, insira um número de página entre 1 e {total_pages}.")
            return
        
        start_index = (pagina - 1) * items_per_page
        end_index = start_index + items_per_page
        current_items_on_page_inv = inventory_list[start_index:end_index]

        items_on_page_data_for_view = [] # (item_id, inv_item_data, shop_item_data)
        description_parts = []
        for inv_item in current_items_on_page_inv:
            item_id = inv_item["id"]
            shop_item_data = await self.shop_manager.get_item(item_id) # Pega dados da loja para emoji e usabilidade
            items_on_page_data_for_view.append((item_id, inv_item, shop_item_data))
            
            emoji = shop_item_data.get("emoji", "🎒") if shop_item_data else "🎒"
            item_name = inv_item.get("name", item_id) # Usa nome do inventário, fallback para ID
            description_parts.append(f"{emoji} **{item_name}** (ID: `{item_id}`) - Quantidade: {inv_item['quantity']}")

        embed_description = "\n".join(description_parts) if description_parts else "Nenhum item nesta página."

        embed = Embed(title=f"{get_emoji(self.bot, 'inventory')} Inventário de {interaction.user.display_name} - Página {pagina}/{total_pages}", 
                        description=embed_description, 
                        color=Color.orange())
        embed.set_footer(text="Itens usáveis podem ter um botão para /usar.")
        
        view = InventoryView(self.bot, self.economy_manager, self.shop_manager, user_id, pagina, total_pages, items_on_page_data_for_view)

        if interaction.response.is_done():
            await interaction.edit_original_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @nextcord.slash_command(name="usar", description="Usa um item do seu inventário.")
    async def usar(self, interaction: Interaction, item_id: str = SlashOption(description="ID do item que você quer usar.", required=True)):
        item_id = item_id.lower()
        user_id = interaction.user.id

        item_in_inventory_quantity = await self.economy_manager.get_item_quantity(user_id, item_id)
        if item_in_inventory_quantity <= 0:
            await self.send_error_embed(interaction, "Item Não Encontrado", f"Você não possui o item com ID `{item_id}` no seu inventário.")
            return

        shop_item_data = await self.shop_manager.get_item(item_id)
        if not shop_item_data or not shop_item_data.get("usable"):
            await self.send_error_embed(interaction, "Item Não Usável", f"O item '{shop_item_data.get('name', item_id) if shop_item_data else item_id}' não pode ser usado.")
            return

        # Lógica de uso do item
        # Exemplo: Dar um cargo se role_id estiver definido
        role_id_to_give = shop_item_data.get("role_id")
        success_message = shop_item_data.get("use_description", f"Você usou **{shop_item_data['name']}** com sucesso!")
        action_taken = False

        if role_id_to_give:
            try:
                role_id_int = int(role_id_to_give)
                role = interaction.guild.get_role(role_id_int)
                if role and isinstance(interaction.user, Member):
                    if role not in interaction.user.roles:
                        await interaction.user.add_roles(role, reason=f"Usou o item {item_id} da loja.")
                        success_message += f" Você recebeu o cargo {role.mention}!"
                        action_taken = True
                    else:
                        success_message += " Você já possui o cargo associado."
                        action_taken = True # Considera ação tomada mesmo que já tenha o cargo
                elif not role:
                    await self.send_error_embed(interaction, "Erro ao Usar Item", f"O cargo associado ao item (ID: {role_id_int}) não foi encontrado no servidor.")
                    return # Não consome o item se o cargo não existe
            except ValueError:
                 await self.send_error_embed(interaction, "Erro de Configuração do Item", f"O ID do cargo ({role_id_to_give}) para o item {item_id} não é um número válido.")
                 return
            except nextcord.Forbidden:
                await self.send_error_embed(interaction, "Permissão Negada", f"Não tenho permissão para dar o cargo {role.name if role else 'desconhecido'}. Verifique minhas permissões.")
                return
            except Exception as e:
                print(f"Erro ao dar cargo pelo item {item_id}: {e}")
                await self.send_error_embed(interaction, "Erro Inesperado", f"Ocorreu um erro ao tentar dar o cargo. Tente novamente mais tarde.")
                return
        else:
            # Se não há role_id, mas o item é usável, apenas envia a mensagem de sucesso padrão
            action_taken = True 

        if action_taken:
            removed = await self.economy_manager.remove_item_from_inventory(user_id, item_id, 1)
            if removed:
                emoji_use = get_emoji(self.bot, "use")
                await self.send_success_embed(interaction, "Item Usado!", f"{emoji_use} {success_message}")
            else:
                # Isso não deveria acontecer se a verificação de quantidade foi feita antes
                await self.send_error_embed(interaction, "Erro ao Usar", "Não foi possível remover o item do seu inventário após o uso.")
        else:
            # Se nenhuma ação específica foi tomada (ex: item usável sem role_id e sem use_description customizada)
            # e não houve erro, mas também não houve uma "ação" clara além de consumir.
            # Poderia ser um item que só tem um efeito passivo ou é consumido sem feedback explícito além da remoção.
            # Neste caso, se o item foi configurado como usável mas não tem role_id nem use_description, 
            # ainda assim removemos e damos uma mensagem genérica.
            removed = await self.economy_manager.remove_item_from_inventory(user_id, item_id, 1)
            if removed:
                 await self.send_success_embed(interaction, "Item Consumido", f"Você consumiu **{shop_item_data['name']}**.")
            else:
                await self.send_error_embed(interaction, "Erro ao Consumir", "Não foi possível remover o item do seu inventário.")

    @nextcord.slash_command(name="ranking", description="Mostra o ranking dos mais ricos do servidor.")
    async def ranking(self, interaction: Interaction, top_n: int = SlashOption(description="Número de usuários no topo (padrão 10).", required=False, default=10)):
        if top_n <= 0 or top_n > 25:
            await self.send_error_embed(interaction, "Valor Inválido", "O número de usuários no ranking deve ser entre 1 e 25.")
            return

        all_data = await self.economy_manager.get_all_data()
        if not all_data:
            await self.send_info_embed(interaction, "Ranking Vazio", "Ainda não há dados de economia para mostrar um ranking.")
            return

        # Filtrar apenas usuários do servidor atual e que não sejam bots
        guild_members_data = []
        for user_id_str, data in all_data.items():
            try:
                user_id_int = int(user_id_str)
                member = interaction.guild.get_member(user_id_int)
                if member and not member.bot:
                    guild_members_data.append((member.display_name, data.get("balance", 0)))
            except ValueError:
                continue # Ignora IDs não numéricos
        
        if not guild_members_data:
            await self.send_info_embed(interaction, "Ranking Vazio", "Nenhum usuário deste servidor com dados de economia encontrado.")
            return

        sorted_users = sorted(guild_members_data, key=lambda x: x[1], reverse=True)
        top_users = sorted_users[:top_n]

        embed = Embed(title=f"{get_emoji(self.bot, 'trophy')} Ranking de Riqueza - Top {len(top_users)}", color=Color.gold())
        description = ""
        for i, (name, balance) in enumerate(top_users):
            description += f"**{i+1}.** {name} - {balance} {CURRENCY_SYMBOL}\n"
        
        if not description:
            description = "Ninguém no ranking ainda."
            
        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Comandos de Administração de Economia ---
    @nextcord.slash_command(name="eco_admin", description="Comandos de administração da economia.")
    async def eco_admin(self, interaction: Interaction):
        pass # Este é um grupo de subcomandos

    @eco_admin.subcommand(name="dar", description="Dá Cristais para um usuário.")
    @application_checks.has_permissions(administrator=True) # Ou uma role específica
    async def eco_admin_dar(self, interaction: Interaction, 
                            usuario: Member = SlashOption(description="Usuário para dar os Cristais.", required=True), 
                            valor: int = SlashOption(description="Quantidade de Cristais a dar.", required=True)):
        if valor <= 0:
            await self.send_error_embed(interaction, "Valor Inválido", "A quantidade deve ser positiva.")
            return
        
        await self.economy_manager.update_balance(usuario.id, valor, reason="admin_give")
        await self.send_success_embed(interaction, "Cristais Adicionados", f"**{valor} {CURRENCY_SYMBOL}** foram adicionados à conta de {usuario.mention}.")

    @eco_admin.subcommand(name="remover", description="Remove Cristais de um usuário.")
    @application_checks.has_permissions(administrator=True)
    async def eco_admin_remover(self, interaction: Interaction, 
                                usuario: Member = SlashOption(description="Usuário para remover os Cristais.", required=True), 
                                valor: int = SlashOption(description="Quantidade de Cristais a remover.", required=True)):
        if valor <= 0:
            await self.send_error_embed(interaction, "Valor Inválido", "A quantidade deve ser positiva.")
            return
        
        current_balance = await self.economy_manager.get_balance(usuario.id)
        amount_to_remove = min(valor, current_balance) # Não pode remover mais do que tem

        await self.economy_manager.update_balance(usuario.id, -amount_to_remove, reason="admin_remove")
        await self.send_success_embed(interaction, "Cristais Removidos", f"**{amount_to_remove} {CURRENCY_SYMBOL}** foram removidos da conta de {usuario.mention}.")

    @eco_admin.subcommand(name="definir", description="Define o saldo de Cristais de um usuário.")
    @application_checks.has_permissions(administrator=True)
    async def eco_admin_definir(self, interaction: Interaction, 
                                usuario: Member = SlashOption(description="Usuário para definir o saldo.", required=True), 
                                valor: int = SlashOption(description="Novo saldo de Cristais.", required=True)):
        if valor < 0:
            await self.send_error_embed(interaction, "Valor Inválido", "O saldo não pode ser negativo.")
            return
        
        current_balance = await self.economy_manager.get_balance(usuario.id)
        change_amount = valor - current_balance
        await self.economy_manager.update_balance(usuario.id, change_amount, reason="admin_set")
        await self.send_success_embed(interaction, "Saldo Definido", f"O saldo de {usuario.mention} foi definido para **{valor} {CURRENCY_SYMBOL}**.")

    @eco_admin.subcommand(name="resetar_usuario", description="Reseta todos os dados de economia de um usuário.")
    @application_checks.has_permissions(administrator=True)
    async def eco_admin_resetar_usuario(self, interaction: Interaction, 
                                        usuario: Member = SlashOption(description="Usuário para resetar os dados.", required=True)):
        user_id_str = str(usuario.id)
        async with self.economy_manager.lock:
            if user_id_str in self.economy_manager.data:
                del self.economy_manager.data[user_id_str]
                await self.economy_manager.save_data()
                await self.send_success_embed(interaction, "Dados Resetados", f"Todos os dados de economia de {usuario.mention} foram resetados.")
            else:
                await self.send_error_embed(interaction, "Usuário Não Encontrado", f"{usuario.mention} não possui dados de economia para resetar.")

    @eco_admin.subcommand(name="resetar_cooldown", description="Reseta um cooldown específico para um usuário.")
    @application_checks.has_permissions(administrator=True)
    async def eco_admin_resetar_cooldown(self, interaction: Interaction,
                                         usuario: Member = SlashOption(description="Usuário para resetar o cooldown.", required=True),
                                         comando: str = SlashOption(description="Nome do comando do cooldown (ex: daily, work, crime, rob, bet).", required=True)):
        comando = comando.lower()
        valid_commands = ["daily", "work", "crime", "rob", "bet"]
        if comando not in valid_commands:
            await self.send_error_embed(interaction, "Comando Inválido", f"O nome do comando deve ser um dos seguintes: {', '.join(valid_commands)}.")
            return

        async with self.economy_manager.lock:
            user_data = await self.economy_manager._get_user_data(usuario.id)
            if comando in user_data["cooldowns"]:
                del user_data["cooldowns"][comando]
                await self.economy_manager.save_data()
                await self.send_success_embed(interaction, "Cooldown Resetado", f"O cooldown do comando `{comando}` para {usuario.mention} foi resetado.")
            else:
                await self.send_error_embed(interaction, "Cooldown Não Encontrado", f"{usuario.mention} não está em cooldown para o comando `{comando}`.")

    # --- Comandos de Administração da Loja ---
    @eco_admin.subcommand(name="additemloja", description="Adiciona um novo item à loja.")
    @application_checks.has_permissions(administrator=True)
    async def eco_admin_additemloja(self, interaction: Interaction,
                                    item_id: str = SlashOption(description="ID único para o item (ex: 'poco_xp').", required=True),
                                    nome: str = SlashOption(description="Nome do item para exibição.", required=True),
                                    preco: int = SlashOption(description="Preço do item em Cristais.", required=True),
                                    descricao: str = SlashOption(description="Descrição do item.", required=True),
                                    emoji: Optional[str] = SlashOption(description="Emoji para o item (opcional).", required=False, default="📦"),
                                    cargo_id: Optional[str] = SlashOption(description="ID do cargo a ser dado ao usar (opcional).", required=False),
                                    usavel: Optional[bool] = SlashOption(description="Se o item é usável com /usar (padrão: Falso).", required=False, default=False),
                                    desc_uso: Optional[str] = SlashOption(description="Descrição do que acontece ao usar o item (opcional).", required=False)):
        item_id = item_id.lower()
        if preco < 0:
            await self.send_error_embed(interaction, "Preço Inválido", "O preço do item não pode ser negativo.")
            return
        
        role_id_int = None
        if cargo_id:
            try:
                role_id_int = int(cargo_id)
            except ValueError:
                await self.send_error_embed(interaction, "ID de Cargo Inválido", "O ID do cargo fornecido não é um número válido.")
                return

        success = await self.shop_manager.add_shop_item(item_id, nome, preco, descricao, emoji, role_id_int, usavel, desc_uso)
        if success:
            await self.send_success_embed(interaction, "Item Adicionado à Loja", f"O item **{nome}** (ID: `{item_id}`) foi adicionado à loja por {preco} {CURRENCY_SYMBOL}.")
        else:
            await self.send_error_embed(interaction, "Erro ao Adicionar Item", "Não foi possível adicionar o item. Verifique os parâmetros.")

    @eco_admin.subcommand(name="remitemloja", description="Remove um item da loja.")
    @application_checks.has_permissions(administrator=True)
    async def eco_admin_remitemloja(self, interaction: Interaction, item_id: str = SlashOption(description="ID do item a ser removido.", required=True)):
        item_id = item_id.lower()
        success = await self.shop_manager.remove_shop_item(item_id)
        if success:
            await self.send_success_embed(interaction, "Item Removido da Loja", f"O item com ID `{item_id}` foi removido da loja.")
        else:
            await self.send_error_embed(interaction, "Item Não Encontrado", f"O item com ID `{item_id}` não foi encontrado na loja.")

    # --- Task para limpar cooldowns antigos (opcional, mas bom para performance a longo prazo) ---
    @tasks.loop(hours=24) # Roda uma vez por dia
    async def daily_check(self):
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Executando daily_check para limpar cooldowns expirados...')
        current_time = time.time()
        users_to_save = set()

        async with self.economy_manager.lock:
            all_data = self.economy_manager.data
            for user_id_str, user_data in list(all_data.items()): # Usar list() para permitir modificação durante iteração
                if "cooldowns" in user_data:
                    cooldowns = user_data["cooldowns"]
                    for command_name, expires_at in list(cooldowns.items()): # Usar list() aqui também
                        if current_time >= expires_at:
                            del cooldowns[command_name]
                            users_to_save.add(user_id_str)
        
        if users_to_save:
            await self.economy_manager.save_data()
            print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Cooldowns expirados limpos para {len(users_to_save)} usuários.')
        else:
            print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Nenhum cooldown expirado para limpar.')

    @daily_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()
        print(f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}] [INFO] Daily check aguardando o bot ficar pronto...')

    # Listener para interações de botões da loja e inventário
    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type == nextcord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            
            # Lógica para botões da Loja
            if custom_id.startswith("buy_"):
                item_id_to_buy = custom_id.split("_", 1)[1]
                # Deferir para evitar "Interaction failed"
                await interaction.response.defer(ephemeral=True, with_message=False) 
                
                item_data = await self.shop_manager.get_item(item_id_to_buy)
                if not item_data:
                    await self.send_error_embed(interaction, "Item Não Encontrado", f"O item com ID `{item_id_to_buy}` não existe mais na loja.")
                    return

                total_cost = item_data["price"] # Compra de 1 unidade pelo botão
                user_balance = await self.economy_manager.get_balance(interaction.user.id)

                if user_balance < total_cost:
                    await self.send_error_embed(interaction, "Saldo Insuficiente", 
                                              f"Você precisa de **{total_cost} {CURRENCY_SYMBOL}** para comprar '{item_data['name']}', mas você só tem **{user_balance} {CURRENCY_SYMBOL}**.")
                    return

                await self.economy_manager.update_balance(interaction.user.id, -total_cost, reason="item_purchase_button")
                await self.economy_manager.add_item_to_inventory(interaction.user.id, item_id_to_buy, item_data["name"], 1)
                
                emoji_buy = get_emoji(self.bot, "buy")
                await self.send_success_embed(interaction, "Compra Realizada!", 
                                            f"{emoji_buy} Você comprou 1x **{item_data['name']}** por **{total_cost} {CURRENCY_SYMBOL}**.")
                # Opcional: Atualizar a view da loja se quiser desabilitar o botão ou algo assim
                # Isso pode ser complexo se a view original foi enviada por /loja e não por este listener.

            elif custom_id == "shop_prev_page":
                # A view original foi enviada por /loja. Precisamos recriar o comando.
                # Pegar a página atual da mensagem original (se possível) ou assumir.
                # Esta é uma limitação de views persistentes sem estado armazenado na view.
                # Para simplificar, vamos apenas acusar o recebimento. O usuário terá que rodar /loja <pagina-1>
                # Ou, idealmente, o comando /loja deveria lidar com a interação do botão diretamente.
                # Para este exemplo, vamos assumir que o comando /loja será chamado novamente pelo usuário.
                # No entanto, para uma melhor UX, o comando /loja deveria ser mais interativo.
                
                # Tentativa de extrair a página atual do embed da mensagem original
                if interaction.message and interaction.message.embeds:
                    embed_title = interaction.message.embeds[0].title
                    if embed_title and "Página" in embed_title:
                        try:
                            parts = embed_title.split("Página ")[1].split("/")
                            current_page_from_embed = int(parts[0])
                            if current_page_from_embed > 1:
                                # Recriar o comando /loja com a página anterior
                                # Isso requer que o comando /loja possa ser chamado internamente ou que a view seja mais inteligente
                                # Para este exemplo, vamos apenas deferir e pedir ao usuário para usar o comando.
                                await interaction.response.defer() # Deferir para não dar erro
                                # Idealmente: await self.loja(interaction, pagina=current_page_from_embed - 1)
                                # Mas isso pode causar problemas se a interação original do /loja já foi respondida.
                                # A melhor forma é o comando /loja original lidar com a interação do botão.
                                # Como a view é recriada a cada chamada de /loja, o botão da view antiga não deveria mais funcionar.
                                # Se a view é persistente, ela precisa de mais lógica.
                                # Para o propósito deste exemplo, vamos assumir que o usuário re-executará o comando.
                                # O defer() acima é para o caso do botão ainda estar ativo.
                                # Se a view é recriada a cada página, o defer não é estritamente necessário aqui
                                # pois o botão clicado é da view antiga.
                                # A lógica de paginação real está no comando /loja ao receber o parâmetro 'pagina'.
                                # A view ShopView é recriada a cada chamada de /loja.
                                # O botão aqui é mais um placeholder para a lógica que deveria estar no comando.
                                # Vamos apenas acusar o recebimento.
                                # O ideal é que o comando /loja que criou a view também lide com os botões de navegação.
                                # Como a view é recriada, o botão da view antiga não deveria mais funcionar.
                                # Se a view é persistente, ela precisa de mais lógica.
                                # Para o propósito deste exemplo, vamos assumir que o usuário re-executará o comando.
                                # O defer() acima é para o caso do botão ainda estar ativo.
                                # Se a view é recriada a cada página, o defer não é estritamente necessário aqui
                                # pois o botão clicado é da view antiga.
                                # A lógica de paginação real está no comando /loja ao receber o parâmetro 'pagina'.
                                # A view ShopView é recriada a cada chamada de /loja.
                                # O botão aqui é mais um placeholder para a lógica que deveria estar no comando.
                                # Vamos apenas acusar o recebimento.
                                pass # A lógica de paginação está no comando /loja
                        except Exception as e:
                            print(f"Erro ao tentar paginar loja (prev): {e}")
                            pass # Ignora se não conseguir extrair
                await interaction.response.defer() # Apenas para garantir que a interação seja acusada

            elif custom_id == "shop_next_page":
                # Mesma lógica do prev_page
                if interaction.message and interaction.message.embeds:
                    embed_title = interaction.message.embeds[0].title
                    if embed_title and "Página" in embed_title:
                        try:
                            parts = embed_title.split("Página ")[1].split("/")
                            current_page_from_embed = int(parts[0])
                            total_pages_from_embed = int(parts[1])
                            if current_page_from_embed < total_pages_from_embed:
                                # await self.loja(interaction, pagina=current_page_from_embed + 1)
                                pass
                        except Exception as e:
                            print(f"Erro ao tentar paginar loja (next): {e}")
                            pass
                await interaction.response.defer()
            
            # Lógica para botões do Inventário
            elif custom_id.startswith("use_"):
                item_id_to_use = custom_id.split("_", 1)[1]
                await interaction.response.defer(ephemeral=True, with_message=False)
                
                # Re-chamar a lógica do comando /usar
                # Isso é um pouco redundante, mas garante consistência.
                # Idealmente, a lógica de uso seria uma função auxiliar chamada por ambos.
                await self.usar_item_from_interaction(interaction, item_id_to_use)

            elif custom_id == "inv_prev_page":
                # Lógica similar à da loja para paginação do inventário
                await interaction.response.defer()

            elif custom_id == "inv_next_page":
                await interaction.response.defer()

    async def usar_item_from_interaction(self, interaction: Interaction, item_id: str):
        # Esta é uma refatoração da lógica do comando /usar para ser chamada pelo listener do botão
        item_id = item_id.lower()
        user_id = interaction.user.id

        item_in_inventory_quantity = await self.economy_manager.get_item_quantity(user_id, item_id)
        if item_in_inventory_quantity <= 0:
            await self.send_error_embed(interaction, "Item Não Encontrado", f"Você não possui o item com ID `{item_id}` no seu inventário.")
            return

        shop_item_data = await self.shop_manager.get_item(item_id)
        if not shop_item_data or not shop_item_data.get("usable"):
            await self.send_error_embed(interaction, "Item Não Usável", f"O item '{shop_item_data.get('name', item_id) if shop_item_data else item_id}' não pode ser usado.")
            return

        role_id_to_give = shop_item_data.get("role_id")
        success_message = shop_item_data.get("use_description", f"Você usou **{shop_item_data['name']}** com sucesso!")
        action_taken = False

        if role_id_to_give:
            try:
                role_id_int = int(role_id_to_give)
                role = interaction.guild.get_role(role_id_int)
                if role and isinstance(interaction.user, Member):
                    if role not in interaction.user.roles:
                        await interaction.user.add_roles(role, reason=f"Usou o item {item_id} da loja.")
                        success_message += f" Você recebeu o cargo {role.mention}!"
                        action_taken = True
                    else:
                        success_message += " Você já possui o cargo associado."
                        action_taken = True
                elif not role:
                    await self.send_error_embed(interaction, "Erro ao Usar Item", f"O cargo associado ao item (ID: {role_id_int}) não foi encontrado no servidor.")
                    return
            except ValueError:
                 await self.send_error_embed(interaction, "Erro de Configuração do Item", f"O ID do cargo ({role_id_to_give}) para o item {item_id} não é um número válido.")
                 return
            except nextcord.Forbidden:
                await self.send_error_embed(interaction, "Permissão Negada", f"Não tenho permissão para dar o cargo {role.name if role else 'desconhecido'}. Verifique minhas permissões.")
                return
            except Exception as e:
                print(f"Erro ao dar cargo pelo item {item_id}: {e}")
                await self.send_error_embed(interaction, "Erro Inesperado", f"Ocorreu um erro ao tentar dar o cargo. Tente novamente mais tarde.")
                return
        else:
            action_taken = True 

        if action_taken:
            removed = await self.economy_manager.remove_item_from_inventory(user_id, item_id, 1)
            if removed:
                emoji_use = get_emoji(self.bot, "use")
                await self.send_success_embed(interaction, "Item Usado!", f"{emoji_use} {success_message}")
            else:
                await self.send_error_embed(interaction, "Erro ao Usar", "Não foi possível remover o item do seu inventário após o uso.")
        else:
            removed = await self.economy_manager.remove_item_from_inventory(user_id, item_id, 1)
            if removed:
                 await self.send_success_embed(interaction, "Item Consumido", f"Você consumiu **{shop_item_data['name']}**.")
            else:
                await self.send_error_embed(interaction, "Erro ao Consumir", "Não foi possível remover o item do seu inventário.")

def setup(bot):
    bot.add_cog(Economia(bot))
