# /home/ubuntu/ShirayukiBot/cogs/Interacoes.py
# Cog para comandos de interação social entre usuários.

import nextcord
from nextcord import Interaction, SlashOption, Embed, Color, Member, User
from nextcord.ext import commands
from nextcord.ui import View, Button
import random
import asyncio
from datetime import datetime, timedelta, timezone  # Corrigido: removido 'import' extra
import json
import os
import traceback

# Diretório para armazenar dados
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
INTERACTIONS_FILE = os.path.join(DATA_DIR, "interactions.json")

# Garante que o diretório de dados existe
os.makedirs(DATA_DIR, exist_ok=True)

# Carrega ou cria o arquivo de interações
def load_interactions_data():
    if os.path.exists(INTERACTIONS_FILE):
        try:
            with open(INTERACTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Falha ao carregar arquivo de interações: {e}")
            return {"users": {}, "last_updated": datetime.now(timezone.utc).isoformat()}
    else:
        default_data = {"users": {}, "last_updated": datetime.now(timezone.utc).isoformat()}
        save_interactions_data(default_data)
        return default_data

# Salva os dados de interações
def save_interactions_data(data):
    try:
        with open(INTERACTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar arquivo de interações: {e}")

# Lista de interações disponíveis
INTERACTIONS = {
    "abraçar": {
        "emoji": "🤗",
        "messages": [
            "{user} deu um abraço apertado em {target}!",
            "{user} abraçou {target} com carinho!",
            "{user} envolveu {target} em um abraço caloroso!"
        ],
        "gifs": [
            "https://media.giphy.com/media/u9BxQbM5bxvwY/giphy.gif",
            "https://media.giphy.com/media/PHZ7v9tfQu0w0/giphy.gif",
            "https://media.giphy.com/media/3M4NpbLCTxBqU/giphy.gif"
        ]
    },
    "beijar": {
        "emoji": "💋",
        "messages": [
            "{user} deu um beijo em {target}!",
            "{user} beijou {target} apaixonadamente!",
            "{user} plantou um beijo na bochecha de {target}!"
        ],
        "gifs": [
            "https://media.giphy.com/media/bGm9FuBCGg4SY/giphy.gif",
            "https://media.giphy.com/media/zkppEMFvRX5FC/giphy.gif",
            "https://media.giphy.com/media/G3va31oEEnIkM/giphy.gif"
        ]
    },
    "cumprimentar": {
        "emoji": "👋",
        "messages": [
            "{user} cumprimentou {target} com entusiasmo!",
            "{user} acenou para {target}!",
            "{user} deu um 'olá' animado para {target}!"
        ],
        "gifs": [
            "https://media.giphy.com/media/3og0IFrHkIglEOg8Ba/giphy.gif",
            "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
            "https://media.giphy.com/media/ASd0Ukj0y3qMM/giphy.gif"
        ]
    },
    "bater": {
        "emoji": "👊",
        "messages": [
            "{user} deu um soco em {target}! Isso deve ter doído!",
            "{user} bateu em {target}! Ai!",
            "{user} atacou {target} com toda força!"
        ],
        "gifs": [
            "https://media.giphy.com/media/l1J3G5lf06vi58EIE/giphy.gif",
            "https://media.giphy.com/media/3o7TKO3AC501Z6qRnG/giphy.gif",
            "https://media.giphy.com/media/DuVRadBbaX6A8/giphy.gif"
        ]
    },
    "cafuné": {
        "emoji": "✨",
        "messages": [
            "{user} fez um cafuné gostoso em {target}!",
            "{user} acariciou a cabeça de {target} com carinho!",
            "{user} fez carinho nos cabelos de {target}!"
        ],
        "gifs": [
            "https://media.giphy.com/media/ARSp9T7wwxNcs/giphy.gif",
            "https://media.giphy.com/media/109ltuoSQT212w/giphy.gif",
            "https://media.giphy.com/media/ye7OTQgwmVuVy/giphy.gif"
        ]
    },
    "dançar": {
        "emoji": "💃",
        "messages": [
            "{user} chamou {target} para dançar!",
            "{user} está dançando com {target}!",
            "{user} e {target} estão arrasando na pista de dança!"
        ],
        "gifs": [
            "https://media.giphy.com/media/l3q2DgVwYEKVAPm6c/giphy.gif",
            "https://media.giphy.com/media/26AHLNr8en8J3ovOo/giphy.gif",
            "https://media.giphy.com/media/3o7qE2VAxuXWeyvJIY/giphy.gif"
        ]
    },
    "highfive": {
        "emoji": "🙌",
        "messages": [
            "{user} deu um high five em {target}!",
            "{user} e {target} bateram as mãos em comemoração!",
            "{user} celebrou com {target} com um high five!"
        ],
        "gifs": [
            "https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif",
            "https://media.giphy.com/media/bp0fZr9JxsFwY/giphy.gif",
            "https://media.giphy.com/media/HX3lSnGXZnaWk/giphy.gif"
        ]
    },
    "cutucar": {
        "emoji": "👉",
        "messages": [
            "{user} cutucou {target}!",
            "{user} está incomodando {target} com cutucadas!",
            "{user} deu uma cutucada em {target} para chamar atenção!"
        ],
        "gifs": [
            "https://media.giphy.com/media/WPaIJN6EM9v0s/giphy.gif",
            "https://media.giphy.com/media/LkxUdPkwlIxAk/giphy.gif",
            "https://media.giphy.com/media/10MSCF1viNV7ry/giphy.gif"
        ]
    }
}

class InteractionView(View):
    def __init__(self, user, target, interaction_type):
        super().__init__(timeout=60)
        self.user = user
        self.target = target
        self.interaction_type = interaction_type
        self.responded = False
    
    async def on_timeout(self):
        if not self.responded:
            for item in self.children:
                item.disabled = True
            
            try:
                await self.message.edit(content=f"{self.target.mention} não respondeu ao {self.interaction_type} de {self.user.mention} a tempo.", view=self)
            except:
                pass
    
    @nextcord.ui.button(label="Retribuir", style=nextcord.ButtonStyle.primary)
    async def return_interaction(self, button: nextcord.ui.Button, interaction: Interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(f"Apenas {self.target.mention} pode retribuir esta interação.", ephemeral=True)
            return
        
        self.responded = True
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        # Cria uma nova interação invertendo user e target
        interaction_data = INTERACTIONS[self.interaction_type]
        message = random.choice(interaction_data["messages"]).format(user=self.target.mention, target=self.user.mention)
        gif = random.choice(interaction_data["gifs"])
        
        embed = Embed(
            title=f"{interaction_data['emoji']} {self.interaction_type.capitalize()} Retribuído!",
            description=message,
            color=Color.purple()
        )
        embed.set_image(url=gif)
        embed.set_footer(text=f"Interação retribuída por {self.target.display_name}")
        
        await interaction.followup.send(embed=embed)
        
        # Atualiza estatísticas
        await update_interaction_stats(self.target.id, self.user.id, self.interaction_type)
    
    @nextcord.ui.button(label="Recusar", style=nextcord.ButtonStyle.danger)
    async def decline_interaction(self, button: nextcord.ui.Button, interaction: Interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(f"Apenas {self.target.mention} pode recusar esta interação.", ephemeral=True)
            return
        
        self.responded = True
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(content=f"{self.target.mention} recusou o {self.interaction_type} de {self.user.mention}.", view=self)

async def update_interaction_stats(user_id, target_id, interaction_type):
    user_id = str(user_id)
    target_id = str(target_id)
    
    data = load_interactions_data()
    
    # Inicializa dados do usuário se não existirem
    if user_id not in data["users"]:
        data["users"][user_id] = {"sent": {}, "received": {}, "total_sent": 0, "total_received": 0}
    
    if target_id not in data["users"]:
        data["users"][target_id] = {"sent": {}, "received": {}, "total_sent": 0, "total_received": 0}
    
    # Atualiza estatísticas de envio para o usuário
    if interaction_type not in data["users"][user_id]["sent"]:
        data["users"][user_id]["sent"][interaction_type] = 0
    data["users"][user_id]["sent"][interaction_type] += 1
    data["users"][user_id]["total_sent"] += 1
    
    # Atualiza estatísticas de recebimento para o alvo
    if interaction_type not in data["users"][target_id]["received"]:
        data["users"][target_id]["received"][interaction_type] = 0
    data["users"][target_id]["received"][interaction_type] += 1
    data["users"][target_id]["total_received"] += 1
    
    # Atualiza timestamp
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    save_interactions_data(data)

class Interacoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        print("[INFO] Cog Interacoes carregada.")
    
    # Evento de erro em comandos de aplicação
    @commands.Cog.listener()  # Corrigido: usando commands.Cog.listener() em vez de nextcord.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        # Verifica se o erro é de um comando desta cog
        if hasattr(interaction, 'application_command'):
            try:
                # Verifica tipos específicos de erros
                if isinstance(error, commands.CommandOnCooldown):
                    await interaction.response.send_message(
                        f"⚠️ Este comando está em cooldown. Tente novamente em {error.retry_after:.1f} segundos.",
                        ephemeral=True
                    )
                else:
                    # Erro genérico
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                f"⚠️ Ocorreu um erro ao executar este comando: {str(error)}",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                f"⚠️ Ocorreu um erro ao executar este comando: {str(error)}",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"[ERRO INTERACAO] Erro ao enviar mensagem de erro: {e}")
                
                # Loga o erro para debug
                print(f"[ERRO INTERACAO] {error}")
                traceback.print_exception(type(error), error, error.__traceback__)
            except Exception as e:
                print(f"[ERRO INTERACAO] Erro ao tratar erro de comando: {e}")
    
    @nextcord.slash_command(
        name="interacao",
        description="Comandos de interação social com outros usuários."
    )
    async def interaction(self, interaction: Interaction):
        """Grupo de comandos de interação."""
        pass
    
    @interaction.subcommand(
        name="lista",
        description="Lista todas as interações disponíveis."
    )
    async def list_interactions(self, interaction: Interaction):
        """Lista todas as interações disponíveis."""
        embed = Embed(
            title="🤝 Interações Disponíveis",
            description="Aqui estão todas as interações que você pode usar com outros usuários:",
            color=Color.blue()
        )
        
        for name, data in INTERACTIONS.items():
            embed.add_field(
                name=f"{data['emoji']} {name.capitalize()}",
                value=f"Use `/interacao {name} @usuário` para interagir!",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    @interaction.subcommand(
        name="stats",
        description="Mostra suas estatísticas de interação."
    )
    async def interaction_stats(
        self,
        interaction: Interaction,
        usuario: User = SlashOption(
            name="usuario",
            description="Usuário para ver estatísticas (opcional, padrão: você mesmo)",
            required=False
        )
    ):
        """Mostra estatísticas de interação de um usuário."""
        target = usuario or interaction.user
        target_id = str(target.id)
        
        data = load_interactions_data()
        
        if target_id not in data["users"]:
            await interaction.response.send_message(f"{target.mention} ainda não tem estatísticas de interação.", ephemeral=True)
            return
        
        user_data = data["users"][target_id]
        
        embed = Embed(
            title=f"📊 Estatísticas de Interação de {target.display_name}",
            color=Color.gold()
        )
        
        # Estatísticas gerais
        embed.add_field(
            name="📤 Total Enviadas",
            value=str(user_data["total_sent"]),
            inline=True
        )
        embed.add_field(
            name="📥 Total Recebidas",
            value=str(user_data["total_received"]),
            inline=True
        )
        embed.add_field(
            name="📊 Proporção (Enviadas/Recebidas)",
            value=f"{user_data['total_sent'] / max(1, user_data['total_received']):.2f}",
            inline=True
        )
        
        # Interações enviadas
        if user_data["sent"]:
            sent_text = "\n".join([f"{INTERACTIONS[interaction_type]['emoji']} **{interaction_type.capitalize()}**: {count}" for interaction_type, count in sorted(user_data["sent"].items(), key=lambda x: x[1], reverse=True)])
            embed.add_field(
                name="📤 Interações Enviadas",
                value=sent_text,
                inline=False
            )
        
        # Interações recebidas
        if user_data["received"]:
            received_text = "\n".join([f"{INTERACTIONS[interaction_type]['emoji']} **{interaction_type.capitalize()}**: {count}" for interaction_type, count in sorted(user_data["received"].items(), key=lambda x: x[1], reverse=True)])
            embed.add_field(
                name="📥 Interações Recebidas",
                value=received_text,
                inline=False
            )
        
        # Interação favorita
        if user_data["sent"]:
            favorite_sent = max(user_data["sent"].items(), key=lambda x: x[1])
            embed.add_field(
                name="❤️ Interação Favorita (Enviada)",
                value=f"{INTERACTIONS[favorite_sent[0]]['emoji']} **{favorite_sent[0].capitalize()}**: {favorite_sent[1]} vezes",
                inline=True
            )
        
        if user_data["received"]:
            favorite_received = max(user_data["received"].items(), key=lambda x: x[1])
            embed.add_field(
                name="💝 Interação Favorita (Recebida)",
                value=f"{INTERACTIONS[favorite_received[0]]['emoji']} **{favorite_received[0].capitalize()}**: {favorite_received[1]} vezes",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    # Cria subcomandos dinâmicos para cada tipo de interação
    for interaction_name, interaction_data in INTERACTIONS.items():
        @interaction.subcommand(
            name=interaction_name,
            description=f"{interaction_data['emoji']} {interaction_name.capitalize()} outro usuário."
        )
        async def interaction_command(
            self,
            interaction: Interaction,
            usuario: Member = SlashOption(
                name="usuario",
                description="Usuário para interagir",
                required=True
            ),
            interaction_name=interaction_name,
            interaction_data=interaction_data
        ):
            """Comando de interação dinâmico."""
            # Verifica se o usuário está tentando interagir consigo mesmo
            if usuario.id == interaction.user.id:
                await interaction.response.send_message(f"Você não pode {interaction_name} a si mesmo!", ephemeral=True)
                return
            
            # Verifica cooldown (5 segundos por usuário por tipo de interação)
            cooldown_key = f"{interaction.user.id}:{interaction_name}:{usuario.id}"
            current_time = datetime.now(timezone.utc)
            
            if cooldown_key in self.cooldowns:
                time_diff = (current_time - self.cooldowns[cooldown_key]).total_seconds()
                if time_diff < 5:
                    await interaction.response.send_message(f"Aguarde {5 - int(time_diff)} segundos antes de {interaction_name} {usuario.mention} novamente.", ephemeral=True)
                    return
            
            self.cooldowns[cooldown_key] = current_time
            
            # Seleciona mensagem e gif aleatórios
            message = random.choice(interaction_data["messages"]).format(user=interaction.user.mention, target=usuario.mention)
            gif = random.choice(interaction_data["gifs"])
            
            # Cria embed
            embed = Embed(
                title=f"{interaction_data['emoji']} {interaction_name.capitalize()}!",
                description=message,
                color=Color.blue()
            )
            embed.set_image(url=gif)
            embed.set_footer(text=f"Interação iniciada por {interaction.user.display_name}")
            
            # Cria view para retribuir/recusar
            view = InteractionView(interaction.user, usuario, interaction_name)
            
            # Envia mensagem
            await interaction.response.send_message(embed=embed, view=view)
            
            # Salva a mensagem na view para poder editá-la no timeout
            view.message = await interaction.original_message()
            
            # Atualiza estatísticas
            await update_interaction_stats(interaction.user.id, usuario.id, interaction_name)

# Função setup para carregar a cog
def setup(bot):
    bot.add_cog(Interacoes(bot))
