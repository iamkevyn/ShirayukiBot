# /home/ubuntu/ShirayukiBot/utils/emojis.py

# Dicionário mapeando nomes descritivos para IDs de emojis personalizados
# Obtido da imagem fornecida pelo usuário
CUSTOM_EMOJIS = {
    "sad": 1366996823654535208,      # 1_
    "peek": 1366996885398749254,     # 2_
    "happy_flower": 1366996904663322654, # 3_
    "determined": 1366996921297801216, # 4_
    "blush_hands": 1366997045445132360, # 5_
    "sparkle_happy": 1366997079347429427, # 6_
    "thinking": 1366997117410873404,   # 7_
    "smug": 1366997164521164830       # 8_
}

# Função auxiliar para obter a string formatada do emoji para uso no Discord
def get_emoji(bot, name: str) -> str:
    """Retorna a string formatada de um emoji personalizado pelo nome ou um emoji padrão.

    Args:
        bot: A instância do bot para buscar o emoji.
        name: O nome descritivo do emoji (chave do dicionário CUSTOM_EMOJIS).

    Returns:
        A string formatada do emoji (ex: '<:nome:id>') ou um emoji padrão se não encontrado.
    """
    emoji_id = CUSTOM_EMOJIS.get(name)
    if emoji_id:
        emoji = bot.get_emoji(emoji_id)
        if emoji:
            return str(emoji)
    # Fallback para emojis padrão ou se o emoji personalizado não for encontrado
    fallback_emojis = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "loading": "⏳",
        "sad": "😢",
        "happy": "😊",
        "thinking": "🤔",
        "celebrate": "🎉",
        "question": "❓"
    }
    return fallback_emojis.get(name, "❓") # Retorna '❓' se nem o nome descritivo nem o fallback for encontrado

# Você pode adicionar mais funções utilitárias relacionadas a emojis aqui, se necessário.
