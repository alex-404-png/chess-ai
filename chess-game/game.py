# =============================================================================
# game.py — High-level game state: turns, undo history, status messages
# =============================================================================
# The Game class sits between the UI (main.py) and the Board / AI layers.
# It knows:
#   • whose turn it is
#   • which piece the user has selected
#   • the full undo history (a stack of board "undo records")
#   • whether the game is over and why
#   • what status message to display in the sidebar

from board import Board
from ai import ChessAI
from constants import WHITE, BLACK

import threading


class Game:
    """Orchestrates a full chess game between a human (White) and an AI (Black)."""

    def __init__(self, difficulty: str = "medium"):
        self._lock = threading.Lock()
        self.difficulty = difficulty
        self._reset(difficulty)

    # ─────────────────────────────────────────────────────────────────────────
    # Setup / reset
    # ─────────────────────────────────────────────────────────────────────────

    def _reset(self, difficulty: str):
        self.board = Board()
        self.turn = WHITE
        self.selected = None
        self.legal_moves = []
        self._history = []
        self.game_over = False
        self.winner = None
        self.ai_thinking = False
        self.difficulty = difficulty
        self.ai = ChessAI(difficulty)
        self._update_status()

    def restart(self):
        """Start a brand-new game (keeps the current difficulty)."""
        with self._lock:
            self._reset(self.difficulty)

    def set_difficulty(self, difficulty: str):
        """Change AI difficulty and restart."""
        with self._lock:
            self._reset(difficulty)

    # ─────────────────────────────────────────────────────────────────────────
    # Human input handling
    # ─────────────────────────────────────────────────────────────────────────

    def handle_click(self, row: int, col: int) -> bool:
        """Process a board click from the human player.

        Returns True if a move was made (so the caller can trigger AI).
        """
        with self._lock:
            if self.game_over or self.turn != WHITE or self.ai_thinking:
                return False

            clicked_piece = self.board.get_piece(row, col)

            # Case 1: a piece is already selected
            if self.selected is not None:
                if (row, col) in self.legal_moves:
                    self._make_move(self.selected, (row, col))
                    self.selected = None
                    self.legal_moves = []
                    return True

                if clicked_piece and clicked_piece.color == WHITE:
                    self.selected = (row, col)
                    self.legal_moves = self.board.get_legal_moves(row, col)
                else:
                    self.selected = None
                    self.legal_moves = []

                return False

            # Case 2: nothing selected yet
            if clicked_piece and clicked_piece.color == WHITE:
                self.selected = (row, col)
                self.legal_moves = self.board.get_legal_moves(row, col)

            return False

    # ─────────────────────────────────────────────────────────────────────────
    # AI turn
    # ─────────────────────────────────────────────────────────────────────────

    def do_ai_move(self):
        """Ask the AI for its best move and apply it."""
        with self._lock:
            if self.game_over or self.turn != BLACK:
                return

            move = self.ai.get_best_move(self.board)
            if move:
                self._make_move(move[0], move[1])
            else:
                self.game_over = True
                self.winner = None
                self._update_status()

    # ─────────────────────────────────────────────────────────────────────────
    # Undo
    # ─────────────────────────────────────────────────────────────────────────

    def undo(self):
        """Undo the last two half-moves (one full move: White then Black)."""
        with self._lock:
            if self.game_over:
                self.game_over = False
                self.winner = None

            for _ in range(2):
                if self._history:
                    undo_record = self._history.pop()
                    self.board.undo_move(undo_record)
                    self.turn = WHITE if self.turn == BLACK else BLACK

            self.selected = None
            self.legal_moves = []
            self.turn = WHITE
            self._update_status()

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _make_move(self, from_sq: tuple, to_sq: tuple):
        undo_record = self.board.apply_move(from_sq, to_sq)
        self._history.append(undo_record)

        # Switch turn
        self.turn = BLACK if self.turn == WHITE else WHITE
        self._update_status()

    def _update_status(self):
        """Compute sidebar status string and game-over flags."""
        if self.board.is_checkmate(self.turn):
            self.game_over = True
            self.winner = BLACK if self.turn == WHITE else WHITE
            winner_name = "Black (AI)" if self.winner == BLACK else "White"
            self.status = f"Checkmate! {winner_name} wins!"

        elif self.board.is_stalemate(self.turn):
            self.game_over = True
            self.winner = None
            self.status = "Stalemate! It's a draw."

        elif self.board.is_in_check(self.turn):
            turn_name = "White" if self.turn == WHITE else "Black"
            self.status = f"{turn_name} is in CHECK!"

        elif self.ai_thinking:
            self.status = "AI is thinking…"

        else:
            turn_name = "White (You)" if self.turn == WHITE else "Black (AI)"
            self.status = f"{turn_name}'s turn"

