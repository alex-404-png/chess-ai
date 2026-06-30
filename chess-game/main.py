# =============================================================================
# main.py — Pygame entry point: rendering loop + event handling
# =============================================================================
# Run this file to start the game:   python main.py
#
# Responsibilities:
#   • Initialise Pygame and create the window
#   • Draw the board, pieces, highlights, and sidebar each frame
#   • Route mouse clicks to the Game logic
#   • Run the AI in a background thread so the UI stays responsive
#   • Draw "AI is thinking…" while the thread is alive

import threading
import pygame
import sys

from game      import Game
from constants import (
    SQUARE_SIZE, BOARD_SIZE, SIDEBAR_WIDTH, WINDOW_WIDTH, WINDOW_HEIGHT, FPS,
    WHITE, BLACK,
    LIGHT_SQUARE, DARK_SQUARE,
    HIGHLIGHT_SEL, HIGHLIGHT_MOVE, HIGHLIGHT_LAST, HIGHLIGHT_CHK,
    SIDEBAR_BG, SIDEBAR_PANEL, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY,
    BTN_NORMAL, BTN_HOVER, BTN_TEXT,
    COLOR_CHECK, COLOR_MATE, COLOR_STALE, COLOR_OK,
    FONT_PIECE_SIZE, FONT_LABEL_SIZE, FONT_UI_SIZE, FONT_HEADING_SIZE, FONT_BTN_SIZE,
    PIECE_SYMBOLS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Renderer
# ─────────────────────────────────────────────────────────────────────────────

class Renderer:
    """Handles all Pygame drawing.  Completely separate from game logic."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self._init_fonts()
        # Transparent overlay surface for alpha-blended highlights
        self.overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)

    def _init_fonts(self):
        """
        Try to load a system font that supports Unicode chess glyphs.
        Fall back to Pygame's default if none are found.
        """
        # Fonts with known good Unicode glyph coverage (cross-platform)
        candidates = [
            "segoeuisymbol", "segoeui",          # Windows
            "applesymbols", "helvetica",          # macOS
            "dejavusans", "notosans", "freesans",  # Linux
        ]
        found = None
        for name in candidates:
            f = pygame.font.match_font(name)
            if f:
                found = f
                break

        def _font(size, bold=False):
            if found:
                return pygame.font.Font(found, size)
            return pygame.font.SysFont(None, size, bold=bold)

        self.font_piece   = _font(FONT_PIECE_SIZE)
        self.font_label   = _font(FONT_LABEL_SIZE)
        self.font_ui      = _font(FONT_UI_SIZE)
        self.font_heading = _font(FONT_HEADING_SIZE, bold=True)
        self.font_btn     = _font(FONT_BTN_SIZE, bold=True)

    # ── Main draw call ──────────────────────────────────────────────────────

    def draw(self, game: Game, btn_hover: str | None):
        """Render one complete frame."""
        # Prevent AI thread from mutating the board mid-frame
        with game._lock:
            self.screen.fill(SIDEBAR_BG)
            self._draw_board(game)
            self._draw_sidebar(game, btn_hover)
            pygame.display.flip()


    # ── Board ───────────────────────────────────────────────────────────────

    def _draw_board(self, game: Game):
        board = game.board

        for r in range(8):
            for c in range(8):
                # ── Square background ─────────────────────────────────────
                color = LIGHT_SQUARE if (r + c) % 2 == 0 else DARK_SQUARE
                rect  = pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE,
                                    SQUARE_SIZE, SQUARE_SIZE)
                pygame.draw.rect(self.screen, color, rect)

                # ── Last-move highlight ───────────────────────────────────
                if board.last_move:
                    (lr, lc), (tr, tc) = board.last_move
                    if (r, c) in ((lr, lc), (tr, tc)):
                        self._blit_alpha(r, c, HIGHLIGHT_LAST)

                # ── Selected piece highlight ──────────────────────────────
                if game.selected == (r, c):
                    self._blit_alpha(r, c, HIGHLIGHT_SEL)

                # ── Valid-move dots ───────────────────────────────────────
                if (r, c) in game.legal_moves:
                    piece_here = board.get_piece(r, c)
                    if piece_here:
                        # capture — ring outline
                        cx = c * SQUARE_SIZE + SQUARE_SIZE // 2
                        cy = r * SQUARE_SIZE + SQUARE_SIZE // 2
                        pygame.draw.circle(self.screen, (50, 205, 50), (cx, cy),
                                           SQUARE_SIZE // 2 - 4, 5)
                    else:
                        # empty square — small filled dot
                        self._draw_move_dot(r, c)

                # ── Check highlight on king ───────────────────────────────
                piece = board.get_piece(r, c)
                if piece and piece.type == "K":
                    if board.is_in_check(piece.color):
                        self._blit_alpha(r, c, HIGHLIGHT_CHK)

                # ── Piece glyph ───────────────────────────────────────────
                if piece:
                    self._draw_piece(piece, r, c)

        # ── Rank and file labels ──────────────────────────────────────────
        self._draw_labels()

    def _blit_alpha(self, row, col, rgba):
        """Draw a semi-transparent coloured overlay on a square."""
        self.overlay.fill(rgba)
        self.screen.blit(self.overlay, (col * SQUARE_SIZE, row * SQUARE_SIZE))

    def _draw_move_dot(self, row, col):
        """Small circle in the centre of an empty target square."""
        cx = col * SQUARE_SIZE + SQUARE_SIZE // 2
        cy = row * SQUARE_SIZE + SQUARE_SIZE // 2
        dot_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(dot_surf, (50, 205, 50, 140), (SQUARE_SIZE//2, SQUARE_SIZE//2), 12)
        self.screen.blit(dot_surf, (col * SQUARE_SIZE, row * SQUARE_SIZE))

    def _draw_piece(self, piece, row, col):
        """Render the Unicode glyph, centred on its square."""
        # Shadow (dark offset) for readability on both light and dark squares
        shadow_color = (30, 30, 30)
        main_color   = (255, 255, 255) if piece.color == WHITE else (20, 20, 20)

        glyph = piece.symbol
        cx = col * SQUARE_SIZE + SQUARE_SIZE // 2
        cy = row * SQUARE_SIZE + SQUARE_SIZE // 2

        shadow_surf = self.font_piece.render(glyph, True, shadow_color)
        piece_surf  = self.font_piece.render(glyph, True, main_color)

        sr = shadow_surf.get_rect(center=(cx + 2, cy + 2))
        pr = piece_surf.get_rect(center=(cx, cy))

        self.screen.blit(shadow_surf, sr)
        self.screen.blit(piece_surf,  pr)

    def _draw_labels(self):
        """Rank numbers (1-8) and file letters (a-h) on the board edge."""
        files = "abcdefgh"
        for i in range(8):
            # File letters along the bottom
            lbl = self.font_label.render(files[i], True, TEXT_SECONDARY)
            self.screen.blit(lbl, (i * SQUARE_SIZE + SQUARE_SIZE - 14,
                                   BOARD_SIZE - 16))
            # Rank numbers on the left
            lbl = self.font_label.render(str(8 - i), True, TEXT_SECONDARY)
            self.screen.blit(lbl, (4, i * SQUARE_SIZE + 4))

    # ── Sidebar ─────────────────────────────────────────────────────────────

    def _draw_sidebar(self, game: Game, btn_hover: str | None):
        sx = BOARD_SIZE   # x-offset for everything in the sidebar

        # Background
        pygame.draw.rect(self.screen, SIDEBAR_BG,
                         (sx, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT))

        y = 20
        # ── Title ────────────────────────────────────────────────────────
        self._sb_text("♔  CHESS", sx + 20, y, self.font_heading, ACCENT)
        y += 40

        # Thin separator line
        pygame.draw.line(self.screen, SIDEBAR_PANEL,
                         (sx + 10, y), (sx + SIDEBAR_WIDTH - 10, y), 1)
        y += 14

        # ── Status card ──────────────────────────────────────────────────
        card_rect = pygame.Rect(sx + 10, y, SIDEBAR_WIDTH - 20, 64)
        pygame.draw.rect(self.screen, SIDEBAR_PANEL, card_rect, border_radius=8)

        # Colour the status text based on game state
        if game.game_over:
            txt_color = COLOR_MATE if game.winner else COLOR_STALE
        elif "CHECK" in game.status:
            txt_color = COLOR_CHECK
        elif game.ai_thinking:
            txt_color = ACCENT
        else:
            txt_color = COLOR_OK if game.turn == WHITE else TEXT_SECONDARY

        # Wrap long status messages
        words   = game.status.split()
        lines   = []
        current = ""
        for w in words:
            test = (current + " " + w).strip()
            if self.font_ui.size(test)[0] < SIDEBAR_WIDTH - 40:
                current = test
            else:
                lines.append(current)
                current = w
        lines.append(current)

        ly = y + 10
        for line in lines[:2]:
            self._sb_text(line, sx + 20, ly, self.font_ui, txt_color)
            ly += 20

        y += 80

        # ── Difficulty badge ──────────────────────────────────────────────
        self._sb_text("DIFFICULTY", sx + 20, y, self.font_label, TEXT_SECONDARY)
        y += 18
        diff_text = game.difficulty.upper()
        diff_col  = (100, 210, 100) if game.difficulty == "easy" else (255, 160, 60)
        self._sb_text(diff_text, sx + 20, y, self.font_ui, diff_col)
        y += 36

        pygame.draw.line(self.screen, SIDEBAR_PANEL,
                         (sx + 10, y), (sx + SIDEBAR_WIDTH - 10, y), 1)
        y += 16

        # ── Material count ────────────────────────────────────────────────
        self._sb_text("CAPTURED", sx + 20, y, self.font_label, TEXT_SECONDARY)
        y += 18
        white_cap, black_cap = self._count_material(game.board)
        self._sb_text(f"White  {white_cap:+d}", sx + 20, y, self.font_ui, TEXT_PRIMARY)
        y += 22
        self._sb_text(f"Black  {black_cap:+d}", sx + 20, y, self.font_ui, TEXT_SECONDARY)
        y += 36

        pygame.draw.line(self.screen, SIDEBAR_PANEL,
                         (sx + 10, y), (sx + SIDEBAR_WIDTH - 10, y), 1)
        y += 16

        # ── Buttons ───────────────────────────────────────────────────────
        btn_y = y
        self._draw_button("Restart",  sx + 14, btn_y,       btn_hover == "restart")
        self._draw_button("Undo",     sx + 14, btn_y + 50,  btn_hover == "undo")

        diff_label = "→ Medium" if game.difficulty == "easy" else "→ Easy"
        self._draw_button(diff_label, sx + 14, btn_y + 100, btn_hover == "diff")

        y = btn_y + 160
        pygame.draw.line(self.screen, SIDEBAR_PANEL,
                         (sx + 10, y), (sx + SIDEBAR_WIDTH - 10, y), 1)
        y += 16

        # ── How-to-play ───────────────────────────────────────────────────
        self._sb_text("HOW TO PLAY", sx + 20, y, self.font_label, TEXT_SECONDARY)
        y += 18
        tips = [
            "Click a piece to select it.",
            "Green dots = valid moves.",
            "Click a dot to move.",
            "Undo reverses one full move.",
        ]
        for tip in tips:
            self._sb_text(f"• {tip}", sx + 20, y, self.font_label, TEXT_SECONDARY)
            y += 16

    def _sb_text(self, text, x, y, font, color):
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def _draw_button(self, label: str, x: int, y: int, hover: bool):
        rect = pygame.Rect(x, y, SIDEBAR_WIDTH - 28, 38)
        color = BTN_HOVER if hover else BTN_NORMAL
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        surf = self.font_btn.render(label, True, BTN_TEXT)
        sr   = surf.get_rect(center=rect.center)
        self.screen.blit(surf, sr)

    @staticmethod
    def _count_material(board) -> tuple[int, int]:
        """
        Return (white_advantage, black_advantage) as material delta.
        Positive means that colour leads in material points.
        """
        from constants import PIECE_VALUES
        white_mat = black_mat = 0
        for r in range(8):
            for c in range(8):
                p = board.grid[r][c]
                if p and p.type != "K":
                    if p.color == WHITE:
                        white_mat += PIECE_VALUES[p.type]
                    else:
                        black_mat += PIECE_VALUES[p.type]
        diff = white_mat - black_mat
        return (diff, -diff)

    # ── Hit-test helpers (used by the event loop) ────────────────────────────

    def get_board_square(self, mx, my) -> tuple | None:
        """Convert mouse position to (row, col), or None if outside board."""
        if mx < 0 or mx >= BOARD_SIZE or my < 0 or my >= BOARD_SIZE:
            return None
        return my // SQUARE_SIZE, mx // SQUARE_SIZE

    def get_btn_at(self, mx, my) -> str | None:
        """Return button id at (mx, my), or None."""
        sx = BOARD_SIZE
        # Approximate button areas (must match _draw_sidebar coordinates)
        # We store button y-offsets relative to sidebar; easier to recompute.
        btn_top = (
            20 + 40 + 14 + 64 + 80 + 36 + 16 + 36 + 22 + 36 + 16  # all above buttons
        )
        buttons = [
            ("restart", pygame.Rect(sx + 14, btn_top,       SIDEBAR_WIDTH - 28, 38)),
            ("undo",    pygame.Rect(sx + 14, btn_top + 50,  SIDEBAR_WIDTH - 28, 38)),
            ("diff",    pygame.Rect(sx + 14, btn_top + 100, SIDEBAR_WIDTH - 28, 38)),
        ]
        for name, rect in buttons:
            if rect.collidepoint(mx, my):
                return name
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Chess")
    clock    = pygame.time.Clock()

    game     = Game(difficulty="medium")
    renderer = Renderer(screen)

    ai_thread: threading.Thread | None = None
    btn_hover: str | None = None

    def start_ai_thread():
        """Kick off the AI computation in a background thread."""
        nonlocal ai_thread
        with game._lock:
            game.ai_thinking = True
            game._update_status()


        def _run():
            game.do_ai_move()
            game.ai_thinking = False
            game._update_status()

        ai_thread = threading.Thread(target=_run, daemon=True)
        ai_thread.start()

    while True:
        clock.tick(FPS)
        mx, my = pygame.mouse.get_pos()

        # ── Events ───────────────────────────────────────────────────────
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEMOTION:
                btn_hover = renderer.get_btn_at(mx, my)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btn = renderer.get_btn_at(mx, my)

                if btn == "restart":
                    # Don't touch board while AI thread is active
                    if not game.ai_thinking:
                        game.restart()
                        ai_thread = None


                elif btn == "undo":
                    if not game.ai_thinking:
                        game.undo()

                elif btn == "diff":
                    if not game.ai_thinking:
                        new_diff = "easy" if game.difficulty == "medium" else "medium"
                        game.set_difficulty(new_diff)
                        ai_thread = None


                else:
                    # Board click
                    sq = renderer.get_board_square(mx, my)
                    if sq:
                        moved = game.handle_click(*sq)
                        if moved and not game.game_over:
                            start_ai_thread()

        # ── Render ───────────────────────────────────────────────────────
        renderer.draw(game, btn_hover)


if __name__ == "__main__":
    main()
