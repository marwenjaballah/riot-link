"""
Theme and styling definitions inspired by the Riot Games aesthetic.
"""

class Theme:
    # Colors
    BG_DARK = "#0d131a"
    SURFACE = "#151e28"
    SURFACE_HOVER = "#1c2836"
    CARD_BG = "#131b24"
    CARD_BORDER = "#223142"
    CARD_ACTIVE_BORDER = "#0ac8b9"

    ACCENT_RED = "#ff4655"
    ACCENT_RED_HOVER = "#e03b49"

    ACCENT_GOLD = "#c89b3c"
    ACCENT_GOLD_HOVER = "#dfb04d"

    ACCENT_CYAN = "#0ac8b9"
    ACCENT_CYAN_HOVER = "#18dfd0"

    TEXT_PRIMARY = "#f9fafb"
    TEXT_SECONDARY = "#94a3b8"
    TEXT_MUTED = "#64748b"

    STATUS_ACTIVE = "#10b981"
    STATUS_INACTIVE = "#6b7280"
    DANGER = "#ef4444"

    # Pre-set avatar colors
    AVATAR_COLORS = [
        ("#ff4655", "Riot Red"),
        ("#0ac8b9", "Hextech Cyan"),
        ("#c89b3c", "League Gold"),
        ("#8b5cf6", "Astral Violet"),
        ("#3b82f6", "Cobalt Blue"),
        ("#10b981", "Emerald Green"),
        ("#f59e0b", "Amber Orange"),
    ]

    # Pre-set tags
    TAG_OPTIONS = ["Main", "Smurf", "Ranked", "Casual", "Tournament", "Shared", "Alt"]

    # Tag styling (text_color, bg_color)
    TAG_STYLES = {
        "Main": ("#dfb04d", "#2d2415"),
        "Smurf": ("#a78bfa", "#261d3b"),
        "Ranked": ("#ff6b78", "#38181f"),
        "Casual": ("#2dd4bf", "#112e30"),
        "Tournament": ("#fbbf24", "#362610"),
        "Shared": ("#60a5fa", "#152438"),
        "Alt": ("#94a3b8", "#1e293b"),
    }
