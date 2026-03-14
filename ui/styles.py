# UI theme, colours, fonts

# Primary purple ramp (interactive elements, accents)
PRIMARY = "#534AB7"
PRIMARY_LIGHT = "#EEEDFE"
PRIMARY_DARK = "#3C3489"
PRIMARY_HOVER = "#6359C9"

# Background and surface colours
BG_DARK = "#1A1A2E"
BG_PANEL = "#222240"
BG_INPUT = "#2A2A4A"
SURFACE = "#2E2E50"
SURFACE_HOVER = "#36365E"

# Text colours
TEXT_PRIMARY = "#EAEAEA"
TEXT_SECONDARY = "#A0A0B8"
TEXT_MUTED = "#6E6E8A"

# Confidence colours (from Whisper scores)
CONF_HIGH = "#4ADE80"       # Green — high confidence
CONF_MEDIUM_FG = "#BA7517"  # Amber foreground
CONF_MEDIUM_UL = "#EF9F27"  # Amber underline
CONF_LOW_FG = "#A32D2D"     # Red foreground
CONF_LOW_UL = "#E24B4A"     # Red underline

# Speaker colours (three distinct ramps)
SPEAKER_COLOURS = [
    "#2DD4BF",  # Teal
    "#60A5FA",  # Blue
    "#F59E0B",  # Amber
    "#A78BFA",  # Violet
    "#FB7185",  # Rose
    "#34D399",  # Emerald
    "#FBBF24",  # Yellow
    "#818CF8",  # Indigo
]

# Status colours
SUCCESS = "#4ADE80"
WARNING = "#FBBF24"
ERROR = "#EF4444"


FONT_FAMILY = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"

# Font tuples for CustomTkinter: (family, size, weight)
FONT_HEADING = (FONT_FAMILY, 20, "bold")
FONT_SUBHEADING = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 12, "normal")
FONT_BODY_BOLD = (FONT_FAMILY, 12, "bold")
FONT_SMALL = (FONT_FAMILY, 10, "normal")
FONT_MONO = (FONT_FAMILY_MONO, 11, "normal")
FONT_TIMESTAMP = (FONT_FAMILY_MONO, 10, "normal")


# Window
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 750

# Panels
PANEL_PADDING = 12
PANEL_CORNER_RADIUS = 10

# Input screen
INPUT_DRAG_AREA_HEIGHT = 200
PROGRESS_BAR_HEIGHT = 20

# Output screen — panel proportions (weights for grid)
TRANSCRIPT_WEIGHT = 3    # Left panel takes 3/5 width
SIDEBAR_WEIGHT = 2       # Right panel takes 2/5 width
AUDIO_PLAYER_HEIGHT = 120

# Buttons
BTN_HEIGHT = 36
BTN_CORNER_RADIUS = 8

# Spacing
SPACING_SM = 6
SPACING_MD = 12
SPACING_LG = 20


CUSTOMTKINTER_THEME = "dark"
CUSTOMTKINTER_COLOUR_THEME = "blue"


def get_speaker_colour(index: int) -> str:
    """Return a speaker colour, cycling if more speakers than colours."""
    return SPEAKER_COLOURS[index % len(SPEAKER_COLOURS)]


def get_confidence_colour(score: float) -> dict:
    """Return foreground and underline colours based on confidence score."""
    if score >= 0.85:
        return {"fg": CONF_HIGH, "underline": None}
    elif score >= 0.6:
        return {"fg": CONF_MEDIUM_FG, "underline": CONF_MEDIUM_UL}
    else:
        return {"fg": CONF_LOW_FG, "underline": CONF_LOW_UL}
