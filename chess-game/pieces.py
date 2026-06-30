# =============================================================================
# pieces.py — Chess piece classes and movement rules
# =============================================================================
# Each piece knows:
#   • its colour and type
#   • how to generate every PSEUDO-LEGAL move from its current square
#     (pseudo-legal = geometrically valid but may leave king in check)
#
# The Board class (board.py) filters out moves that leave the king in check,
# turning pseudo-legal moves into fully legal ones.

from constants import (
    WHITE, BLACK,
    PAWN, ROOK, KNIGHT, BISHOP, QUEEN, KING,
    PIECE_SYMBOLS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Base Piece
# ─────────────────────────────────────────────────────────────────────────────

class Piece:
    """Abstract base for all chess pieces."""

    def __init__(self, color: str, piece_type: str):
        self.color      = color        # WHITE or BLACK
        self.type       = piece_type   # PAWN, ROOK, …
        self.has_moved  = False        # tracks castling / pawn double-push eligibility
        self.symbol     = PIECE_SYMBOLS[(color, piece_type)]

    # Every subclass must implement this.
    def get_moves(self, row: int, col: int, board, attacks_only: bool = False) -> list[tuple[int,int]]:
        """
        Return list of (row, col) squares this piece can move to.

        attacks_only : when True, skip any logic that itself depends on
                        check-detection (e.g. castling for the King).
                        This breaks the mutual recursion between
                        square_attacked() <-> King.get_moves() <-> is_in_check().
        """
        raise NotImplementedError

    def __repr__(self):
        return f"{self.color[0].upper()}{self.type}"

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _in_bounds(r: int, c: int) -> bool:
        return 0 <= r < 8 and 0 <= c < 8

    def _is_enemy(self, r: int, c: int, board) -> bool:
        piece = board.grid[r][c]
        return piece is not None and piece.color != self.color

    def _is_empty(self, r: int, c: int, board) -> bool:
        return board.grid[r][c] is None

    def _slide(self, row, col, board, directions) -> list[tuple[int,int]]:
        """
        Generic sliding move generator for rooks, bishops, queens.
        Walks in each direction until hitting a wall, friendly, or enemy piece.
        """
        moves = []
        for dr, dc in directions:
            r, c = row + dr, col + dc
            while self._in_bounds(r, c):
                target = board.grid[r][c]
                if target is None:
                    moves.append((r, c))       # empty — keep sliding
                elif target.color != self.color:
                    moves.append((r, c))       # enemy — capture then stop
                    break
                else:
                    break                      # friendly — blocked
                r += dr
                c += dc
        return moves


# ─────────────────────────────────────────────────────────────────────────────
# Individual Pieces
# ─────────────────────────────────────────────────────────────────────────────

class Pawn(Piece):
    """
    Pawn movement:
    • Moves forward 1 square (or 2 from starting rank).
    • Captures diagonally forward.
    • En-passant is handled here; promotion is handled by the Board.
    """

    def __init__(self, color: str):
        super().__init__(color, PAWN)
        # White pawns move UP the board (decreasing row index in our grid).
        # Black pawns move DOWN (increasing row index).
        self.direction = -1 if color == WHITE else 1
        self.start_row =  6 if color == WHITE else 1

    def get_moves(self, row: int, col: int, board, attacks_only: bool = False) -> list[tuple[int,int]]:
        moves = []
        d = self.direction

        # ── Forward push ──────────────────────────────────────────────────
        r1 = row + d
        if self._in_bounds(r1, col) and self._is_empty(r1, col, board):
            moves.append((r1, col))
            # Double push from starting square
            r2 = row + 2 * d
            if row == self.start_row and self._is_empty(r2, col, board):
                moves.append((r2, col))

        # ── Diagonal captures ────────────────────────────────────────────
        for dc in (-1, 1):
            r, c = row + d, col + dc
            if self._in_bounds(r, c):
                if self._is_enemy(r, c, board):
                    moves.append((r, c))
                # En-passant square set by the board after a double-push
                elif (r, c) == board.en_passant_square:
                    moves.append((r, c))

        return moves


class Rook(Piece):
    """Rook: slides horizontally and vertically."""

    def __init__(self, color: str):
        super().__init__(color, ROOK)

    def get_moves(self, row, col, board, attacks_only=False):
        return self._slide(row, col, board, [(0,1),(0,-1),(1,0),(-1,0)])


class Knight(Piece):
    """Knight: L-shaped jumps, ignores intervening pieces."""

    def __init__(self, color: str):
        super().__init__(color, KNIGHT)

    def get_moves(self, row, col, board, attacks_only=False):
        offsets = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        moves = []
        for dr, dc in offsets:
            r, c = row + dr, col + dc
            if self._in_bounds(r, c):
                target = board.grid[r][c]
                if target is None or target.color != self.color:
                    moves.append((r, c))
        return moves


class Bishop(Piece):
    """Bishop: slides diagonally."""

    def __init__(self, color: str):
        super().__init__(color, BISHOP)

    def get_moves(self, row, col, board, attacks_only=False):
        return self._slide(row, col, board, [(1,1),(1,-1),(-1,1),(-1,-1)])


class Queen(Piece):
    """Queen: rook + bishop combined."""

    def __init__(self, color: str):
        super().__init__(color, QUEEN)

    def get_moves(self, row, col, board, attacks_only=False):
        directions = [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
        return self._slide(row, col, board, directions)


class King(Piece):
    """
    King: moves one square in any direction.
    Castling squares are added here; the Board validates path safety.
    """

    def __init__(self, color: str):
        super().__init__(color, KING)

    def get_moves(self, row, col, board, attacks_only=False):
        moves = []

        # ── Normal one-square moves ───────────────────────────────────────
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if self._in_bounds(r, c):
                    target = board.grid[r][c]
                    if target is None or target.color != self.color:
                        moves.append((r, c))

        # ── Castling ──────────────────────────────────────────────────────
        # Only when neither king nor rook has moved, and path is clear.
        # Skipped entirely when attacks_only=True: castling availability is
        # irrelevant for "can this piece attack square X" queries, and
        # checking it here would recurse into is_in_check() forever.
        if not attacks_only and not self.has_moved and not board.is_in_check(self.color):
            back_row = 7 if self.color == WHITE else 0

            # King-side (short) castling
            rook = board.grid[back_row][7]
            if (rook and rook.type == ROOK and not rook.has_moved
                    and board.grid[back_row][5] is None
                    and board.grid[back_row][6] is None
                    and not board.square_attacked(back_row, 5, self.color)
                    and not board.square_attacked(back_row, 6, self.color)):
                moves.append((back_row, 6))

            # Queen-side (long) castling
            rook = board.grid[back_row][0]
            if (rook and rook.type == ROOK and not rook.has_moved
                    and board.grid[back_row][1] is None
                    and board.grid[back_row][2] is None
                    and board.grid[back_row][3] is None
                    and not board.square_attacked(back_row, 3, self.color)
                    and not board.square_attacked(back_row, 2, self.color)):
                moves.append((back_row, 2))

        return moves


# ─────────────────────────────────────────────────────────────────────────────
# Factory helper — used by the Board when restoring or promoting
# ─────────────────────────────────────────────────────────────────────────────

def make_piece(color: str, piece_type: str) -> Piece:
    """Return a fresh Piece of the requested type and colour."""
    mapping = {
        PAWN:   Pawn,
        ROOK:   Rook,
        KNIGHT: Knight,
        BISHOP: Bishop,
        QUEEN:  Queen,
        KING:   King,
    }
    return mapping[piece_type](color)
