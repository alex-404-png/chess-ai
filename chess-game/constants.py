# =============================================================================
# constants.py — Global settings for the entire chess application
# =============================================================================
# This file is the single source of truth for every "magic number" or color
# used across the project.  Changing a value here updates the whole game.

# ── Window / Board Geometry ──────────────────────────────────────────────────

SQUARE_SIZE   = 80          # pixels per board square
BOARD_SIZE    = SQUARE_SIZE * 8   # 640 px — the board itself
SIDEBAR_WIDTH = 240         # right-hand info panel
WINDOW_WIDTH  = BOARD_SIZE + SIDEBAR_WIDTH   # 880 px total
WINDOW_HEIGHT = BOARD_SIZE                    # 640 px

FPS = 60                    # frame-rate cap

# ── Colour Palette ───────────────────────────────────────────────────────────
# A dark "slate-and-gold" theme: deep squares, warm highlights.

# Board squares
LIGHT_SQUARE   = (240, 217, 181)   # classic warm cream
DARK_SQUARE    = ( 97, 117, 157)   # slate-blue (replaces generic brown)

# Highlights
HIGHLIGHT_SEL  = (255, 215,   0, 160)   # gold — selected piece (with alpha)
HIGHLIGHT_MOVE = ( 50, 205,  50, 130)   # lime-green — valid move dot
HIGHLIGHT_LAST = (205, 133,  63, 120)   # bronze — last move squares
HIGHLIGHT_CHK  = (220,  20,  60, 180)   # crimson — king in check

# Sidebar / UI
SIDEBAR_BG     = ( 22,  27,  34)   # near-black background
SIDEBAR_PANEL  = ( 33,  40,  50)   # slightly lighter card
ACCENT         = (255, 193,   7)   # amber — headings, active turn
TEXT_PRIMARY   = (240, 240, 240)   # near-white
TEXT_SECONDARY = (160, 174, 192)   # muted grey
BTN_NORMAL     = ( 52,  73, 102)   # button idle
BTN_HOVER      = ( 74, 105, 145)   # button hover
BTN_TEXT       = (240, 240, 240)

# Status colours
COLOR_CHECK    = (220,  80,  80)
COLOR_MATE     = (220,  50,  50)
COLOR_STALE    = (180, 180,  60)
COLOR_OK       = ( 80, 200, 120)

# ── Pieces ───────────────────────────────────────────────────────────────────

WHITE = "white"
BLACK = "black"

# Piece-type identifiers (single uppercase letters — easy to compare)
PAWN   = "P"
ROOK   = "R"
KNIGHT = "N"
BISHOP = "B"
QUEEN  = "Q"
KING   = "K"

# Unicode glyphs — drawn directly onto the board (no image files needed)
PIECE_SYMBOLS = {
    (WHITE, KING):   "♔",
    (WHITE, QUEEN):  "♕",
    (WHITE, ROOK):   "♖",
    (WHITE, BISHOP): "♗",
    (WHITE, KNIGHT): "♘",
    (WHITE, PAWN):   "♙",
    (BLACK, KING):   "♚",
    (BLACK, QUEEN):  "♛",
    (BLACK, ROOK):   "♜",
    (BLACK, BISHOP): "♝",
    (BLACK, KNIGHT): "♞",
    (BLACK, PAWN):   "♟",
}

# ── Piece Values (used by the AI evaluator) ──────────────────────────────────

PIECE_VALUES = {
    PAWN:   100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK:   500,
    QUEEN:  900,
    KING:   20000,
}

# ── AI Settings ─────────────────────────────────────────────────────────────

AI_EASY_DEPTH   = 1   # looks 1 move ahead
AI_MEDIUM_DEPTH = 3   # looks 3 moves ahead (respectable challenge)

# ── Fonts ────────────────────────────────────────────────────────────────────
# Font sizes; the actual pygame.font objects are created in main.py after
# pygame.init() has been called.

FONT_PIECE_SIZE   = 56   # piece glyph on board
FONT_LABEL_SIZE   = 14   # rank / file labels
FONT_UI_SIZE      = 16   # sidebar body text
FONT_HEADING_SIZE = 22   # sidebar headings
FONT_BTN_SIZE     = 15   # button labels
