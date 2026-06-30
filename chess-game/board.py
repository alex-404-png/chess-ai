# =============================================================================
# board.py — Board state, legal-move generation, check / checkmate detection
# =============================================================================
# The Board is the "physics engine" of the chess game.  It holds the 8×8
# grid, applies / undoes moves, and answers questions like:
#   • Is this colour in check?
#   • Is this square attacked by the opponent?
#   • What are all legal moves for a given colour?
#   • Is it checkmate?  Stalemate?

import copy
from pieces import (
    Pawn, Rook, Knight, Bishop, Queen, King, make_piece
)
from constants import (
    WHITE, BLACK,
    PAWN, ROOK, KNIGHT, BISHOP, QUEEN, KING,
)


class Board:
    """
    Represents the complete chess-board state.

    Attributes
    ----------
    grid            : 8×8 list-of-lists, each cell is a Piece or None
    en_passant_square : (row, col) of the square where en-passant is legal,
                        or None if not available
    last_move       : ((from_r, from_c), (to_r, to_c)) for highlighting
    captured_pieces : list of captured Piece objects (for undo history)
    """

    def __init__(self):
        self.grid: list[list] = [[None] * 8 for _ in range(8)]
        self.en_passant_square: tuple | None = None
        self.last_move: tuple | None = None
        self._setup_pieces()

    # ─────────────────────────────────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_pieces(self):
        """Place all 32 pieces in their standard starting positions."""
        # Back-rank order
        back_rank = [ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK]

        for col, piece_type in enumerate(back_rank):
            self.grid[0][col] = make_piece(BLACK, piece_type)
            self.grid[7][col] = make_piece(WHITE, piece_type)

        for col in range(8):
            self.grid[1][col] = Pawn(BLACK)
            self.grid[6][col] = Pawn(WHITE)

    # ─────────────────────────────────────────────────────────────────────────
    # Move application
    # ─────────────────────────────────────────────────────────────────────────

    def apply_move(self, from_sq: tuple, to_sq: tuple) -> dict:
        """
        Move a piece from *from_sq* to *to_sq* and return an 'undo record'
        that can be passed to undo_move() to reverse the action.

        Handles: captures, en-passant, castling, pawn promotion (auto-queen).
        """
        fr, fc = from_sq
        tr, tc = to_sq
        piece  = self.grid[fr][fc]

        # Build the undo record BEFORE changing anything
        undo = {
            "from":           from_sq,
            "to":             to_sq,
            "piece":          piece,
            "captured":       self.grid[tr][tc],
            "en_passant":     self.en_passant_square,
            "piece_has_moved":piece.has_moved,
            "ep_captured":    None,   # filled in if this is an en-passant capture
            "rook_from":      None,   # filled in if castling
            "rook_to":        None,
            "rook_piece":     None,
        }

        # ── En-passant capture ───────────────────────────────────────────
        self.en_passant_square = None   # will be set below if a double-push occurs
        if piece.type == PAWN and (tr, tc) == undo["en_passant"]:
            ep_row = fr           # the captured pawn sits on the *same row* as the moving pawn
            undo["ep_captured"] = self.grid[ep_row][tc]
            self.grid[ep_row][tc] = None

        # ── Castling — move the rook as well ────────────────────────────
        if piece.type == KING and abs(tc - fc) == 2:
            back_row = fr
            if tc == 6:   # king-side
                rook_fc, rook_tc = 7, 5
            else:          # queen-side
                rook_fc, rook_tc = 0, 3
            rook = self.grid[back_row][rook_fc]
            undo["rook_from"]  = (back_row, rook_fc)
            undo["rook_to"]    = (back_row, rook_tc)
            undo["rook_piece"] = rook
            self.grid[back_row][rook_tc] = rook
            self.grid[back_row][rook_fc] = None
            rook.has_moved = True

        # ── Actually move the piece ──────────────────────────────────────
        self.grid[tr][tc] = piece
        self.grid[fr][fc] = None
        piece.has_moved = True

        # ── Double pawn push → set en-passant square ─────────────────────
        if piece.type == PAWN and abs(tr - fr) == 2:
            ep_row = (fr + tr) // 2
            self.en_passant_square = (ep_row, tc)

        # ── Pawn promotion (auto-promote to Queen) ───────────────────────
        promo_row = 0 if piece.color == WHITE else 7
        undo["promoted"] = False
        if piece.type == PAWN and tr == promo_row:
            self.grid[tr][tc] = make_piece(piece.color, QUEEN)
            self.grid[tr][tc].has_moved = True
            undo["promoted"] = True

        self.last_move = (from_sq, to_sq)
        return undo

    def undo_move(self, undo: dict):
        """Reverse a move using the record produced by apply_move()."""
        fr, fc = undo["from"]
        tr, tc = undo["to"]

        self.en_passant_square = undo["en_passant"]
        self.last_move = None

        # Restore the moving piece (handles promotion reversal automatically)
        self.grid[fr][fc] = undo["piece"]
        undo["piece"].has_moved = undo["piece_has_moved"]

        # Restore captured piece (or empty the target square)
        self.grid[tr][tc] = undo["captured"]

        # Restore en-passant captured pawn
        if undo["ep_captured"] is not None:
            self.grid[fr][tc] = undo["ep_captured"]

        # Restore castled rook
        if undo["rook_piece"] is not None:
            rf, rfc = undo["rook_from"]
            rt, rtc = undo["rook_to"]
            self.grid[rf][rfc] = undo["rook_piece"]
            self.grid[rt][rtc] = None
            undo["rook_piece"].has_moved = False   # rook hadn't moved before

    # ─────────────────────────────────────────────────────────────────────────
    # Check / attack detection
    # ─────────────────────────────────────────────────────────────────────────

    def square_attacked(self, row: int, col: int, defending_color: str) -> bool:
        """
        Return True if *any* enemy piece can move to (row, col).
        Used for check detection and castling path validation.
        """
        attacking_color = BLACK if defending_color == WHITE else WHITE
        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if piece and piece.color == attacking_color:
                    # Ask the piece for its pseudo-legal moves.
                    # attacks_only=True skips castling logic (which itself
                    # depends on check-detection) to avoid infinite recursion.
                    if (row, col) in piece.get_moves(r, c, self, attacks_only=True):
                        return True
        return False

    def is_in_check(self, color: str) -> bool:
        """Return True if *color*'s king is currently attacked."""
        # Find the king
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p and p.color == color and p.type == KING:
                    return self.square_attacked(r, c, color)
        return False   # should never happen in a valid game

    # ─────────────────────────────────────────────────────────────────────────
    # Legal-move generation (pseudo-legal filtered by check)
    # ─────────────────────────────────────────────────────────────────────────

    def get_legal_moves(self, row: int, col: int) -> list[tuple[int,int]]:
        """
        Return only moves that do NOT leave the moving side's king in check.
        """
        piece = self.grid[row][col]
        if piece is None:
            return []

        legal = []
        for move in piece.get_moves(row, col, self):
            undo = self.apply_move((row, col), move)
            if not self.is_in_check(piece.color):
                legal.append(move)
            self.undo_move(undo)

        return legal

    def all_legal_moves(self, color: str) -> list[tuple]:
        """
        Return every legal (from_sq, to_sq) pair available to *color*.
        Used by checkmate / stalemate detection and the AI.
        """
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p and p.color == color:
                    for dest in self.get_legal_moves(r, c):
                        moves.append(((r, c), dest))
        return moves

    # ─────────────────────────────────────────────────────────────────────────
    # Game-state queries
    # ─────────────────────────────────────────────────────────────────────────

    def is_checkmate(self, color: str) -> bool:
        """Checkmate: in check AND no legal moves."""
        return self.is_in_check(color) and len(self.all_legal_moves(color)) == 0

    def is_stalemate(self, color: str) -> bool:
        """Stalemate: NOT in check AND no legal moves."""
        return not self.is_in_check(color) and len(self.all_legal_moves(color)) == 0

    # ─────────────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────────────

    def get_piece(self, row: int, col: int):
        """Convenience accessor."""
        return self.grid[row][col]

    def copy(self):
        """Deep-copy the board (used by the AI for look-ahead searches)."""
        return copy.deepcopy(self)
