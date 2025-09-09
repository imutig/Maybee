"""
Custom Emojis for Maybee Bot
Centralized management of Discord custom emoji IDs
"""

# =============================================================================
# COULEURS RECOMMANDÉES
# =============================================================================
# Utilisez ces couleurs pour créer des emojis cohérents avec le branding
CLASSIC = "#FAC10C"  # Jaune Maybee (couleur principale)
YELLOW = "#FAC10C"   # Jaune Maybee
GREEN = "#00FF00"    # Vert
RED = "#FF0000"      # Rouge
BLUE = "#0000FF"     # Bleu
PURPLE = "#800080"   # Violet
ORANGE = "#FFA500"   # Orange
PINK = "#FFC0CB"     # Rose
CYAN = "#00FFFF"     # Cyan
DISCORD_BLUE = "#5865F2"  # Bleu Discord

# =============================================================================
# EMOJIS PRINCIPAUX
# =============================================================================

# Logo et branding
MAYBEE_LOGO = "<:maybee_logo:1414987201556512798>"

# Cogs et configuration
YELLOW_COG = "<:yellow_cog:1414986658054537398>"
BLUE_COG = "<:blue_cog:1414992938479517758>"
GREEN_COG = "<:green_cog:1414992928576639089>"

# Navigation et interface
GLOBE = "<:globe:1414998591734415360>"
USERS = "<:users:1414998667642933420>"
TROPHY = "<:trophy:1414992767402377258>"
SHIELD = "<:shield:1414998279896432711>"
TICKET = "<:ticket:1414992808749826112>"

# Statistiques et analytics
CHART_BAR = "<:chart_bar:1414992863284170982>"
STATS = "<:stats:1414992822909669477>"
ANALYTICS = "<:analytics:1414992893978083561>"

# Commandes générales
PING = "<:ping:1415004517778329610>"
AVATAR = "<:avatar:1415004493468401877>"
INFO = "<:info:1414998888980680714>"

# Médailles et classements
GOLD_MEDAL = "<:gold_medal:1415007695148158976>"
SILVER_MEDAL = "<:silver_medal:1415007712948916476>"
BRONZE_MEDAL = "<:bronze_medal:1415007726458896384>"

# Système de niveaux et XP
TROPHY = "<:trophy:1414992767402377258>"
STAR = "<:star:1415004153410879570>"
GEM = "<:gem:1414992835454697584>"
FIRE = "<:fire:1414992852798148821>"
ARROW_UP = "<:arrow_up:1414992872650047640>"

# Système de tickets
TICKET_CREATE = "<:ticket_create:1414992794090733751>"
TICKET_CLOSE = "<:ticket_close:1414995441829019760>"
TICKET_DELETE = "<:ticket_delete:1414995451207483402>"

# Statuts et actions
SUCCESS = "<:success:1414998815374577886>"
ERROR = "<:error:1414998854805491712>"
WARNING = "<:warning:1414998326692155422>"
CLOCK = "<:clock:1414995496233337013>"
TRASH = "<:trash:1414995460229173440>"
CHECK = "<:check:1414995400783298732>"
CROSS = "<:cross:1414995413517340712>"

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_emoji(emoji_name: str) -> str:
    """
    Récupère un emoji par son nom
    
    Args:
        emoji_name: Nom de l'emoji (ex: 'MAYBEE_LOGO')
    
    Returns:
        String de l'emoji Discord ou emoji standard si non trouvé
    """
    return globals().get(emoji_name, "❓")

def update_emoji(emoji_name: str, emoji_id: str) -> bool:
    """
    Met à jour un emoji avec un nouvel ID
    
    Args:
        emoji_name: Nom de l'emoji à mettre à jour
        emoji_id: Nouvel ID Discord de l'emoji
    
    Returns:
        True si mis à jour avec succès, False sinon
    """
    if emoji_name in globals():
        globals()[emoji_name] = emoji_id
        return True
    return False

def list_emojis() -> dict:
    """
    Liste tous les emojis disponibles
    
    Returns:
        Dictionnaire des emojis {nom: valeur}
    """
    return {k: v for k, v in globals().items() 
            if isinstance(v, str) and (v.startswith('<:') or v in ['❓', '🥇', '🥈', '🥉', 'ℹ️'])}

# =============================================================================
# DOCUMENTATION
# =============================================================================
"""
UTILISATION:

1. Import des emojis:
   from custom_emojis import MAYBEE_LOGO, SUCCESS, ERROR

2. Utilisation dans les embeds:
   embed = discord.Embed(
       title=f"{MAYBEE_LOGO} Mon Titre",
       description=f"{SUCCESS} Opération réussie !"
   )

3. Mise à jour d'un emoji:
   update_emoji("MAYBEE_LOGO", "<:new_logo:123456789>")

4. Récupération dynamique:
   emoji = get_emoji("MAYBEE_LOGO")

CONVENTIONS DE NOMMAGE:
- UPPER_CASE pour les constantes
- Noms descriptifs (MAYBEE_LOGO, SUCCESS, ERROR)
- Groupes logiques (TICKET_*, STATS_*, etc.)

COULEURS RECOMMANDÉES:
- Utilisez CLASSIC (#FAC10C) pour les emojis principaux
- Utilisez les couleurs définies ci-dessus pour la cohérence
- Créez des versions colorées des emojis avant upload sur Discord
"""
