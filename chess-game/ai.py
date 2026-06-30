# =============================================================================
# ai.py — AI opponent using Minimax with Alpha-Beta Pruning
# =============================================================================
# The AI always plays as BLACK.
#
# Difficulty levels (set in constants.py):
#   Easy   → depth 1  (looks 1 half-move ahead; makes random-ish choices)
#   Medium → depth 3  (looks 3 half-moves ahead; solid but beatable)
#
# How it works:
#   1. generate all legal moves for Black
#   2. recursively simulate each move (and White's replies, and Black's
#      replies to those, …) up to *depth* half-moves
#   3. score the resulting position with evaluate_board()
#   4. Black maximises; White minimises → choose the best move for Black
#
# Alpha-Beta Pruning cuts off branches that can never be chosen, making the
# search fast enough for depth-3 in normal game positions.

import random
from board import Board
from constants import (
    WHITE, BLACK,
    PAWN, ROOK, KNIGHT, BISHOP, QUEEN, KING,
    PIECE_VALUES,
    AI_EASY_DEPTH, AI_MEDIUM_DEPTH,
)


# ─────────────────────────────────────────────────────────────────────────────
# Positional bonus tables
# ─────────────────────────────────────────────────────────────────────────────
# These 8×8 tables add a small bonus (or penalty) depending on WHERE a piece
# stands.  They encourage sensible opening play without needing an opening book.
# Values are from Black's perspective (row 0 = Black's back rank).
# We flip them vertically for White.

# fmt: off
_PAWN_TABLE = [
    [  0,   0,   0,   0,   0,   0,   0,   0],
    [ 50,  50,  50,  50,  50,  50,  50,  50],
    [ 10,  10,  20,  30,  30,  20,  10,  10],
    [  5,   5,  10,  25,  25,  10,   5,   5],
    [  0,   0,   0,  20,  20,   0,   0,   0],
    [  5,  -5, -10,   0,   0, -10,  -5,   5],
    [  5,  10,  10, -20, -20,  10,  10,   5],
    [  0,   0,   0,   0,   0,   0,   0,   0],
]

_KNIGHT_TABLE = [
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20,   0,   0,   0,   0, -20, -40],
    [-30,   0,  10,  15,  15,  10,   0, -30],
    [-30,   5,  15,  20,  20,  15,   5, -30],
    [-30,   0,  15,  20,  20,  15,   0, -30],
    [-30,   5,  10,  15,  15,  10,   5, -30],
    [-40, -20,   0,   5,   5,   0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
]

_BISHOP_TABLE = [
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10,   0,   0,   0,   0,   0,   0, -10],
    [-10,   0,   5,  10,  10,   5,   0, -10],
    [-10,   5,   5,  10,  10,   5,   5, -10],
    [-10,   0,  10,  10,  10,  10,   0, -10],
    [-10,  10,  10,  10,  10,  10,  10, -10],
    [-10,   5,   0,   0,   0,   0,   5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20],
]

_ROOK_TABLE = [
    [  0,   0,   0,   0,   0,   0,   0,   0],
    [  5,  10,  10,  10,  10,  10,  10,   5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [  0,   0,   0,   5,   5,   0,   0,   0],
]

_QUEEN_TABLE = [
    [-20, -10, -10,  -5,  -5, -10, -10, -20],
    [-10,   0,   0,   0,   0,   0,   0, -10],
    [-10,   0,   5,   5,   5,   5,   0, -10],
    [ -5,   0,   5,   5,   5,   5,   0,  -5],
    [  0,   0,   5,   5,   5,   5,   0,  -5],
    [-10,   5,   5,   5,   5,   5,   0, -10],
    [-10,   0,   5,   0,   0,   0,   0, -10],
    [-20, -10, -10,  -5,  -5, -10, -10, -20],
]

_KING_MID_TABLE = [
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -20, -20, -20, -20, -10],
    [ 20,  20,   0,   0,   0,   0,  20,  20],
    [ 20,  30,  10,   0,   0,  10,  30,  20],
]
# fmt: on

POSITION_TABLES = {
    PAWN:   _PAWN_TABLE,
    KNIGHT: _KNIGHT_TABLE,
    BISHOP: _BISHOP_TABLE,
    ROOK:   _ROOK_TABLE,
    QUEEN:  _QUEEN_TABLE,
    KING:   _KING_MID_TABLE,
}


# ─────────────────────────────────────────────────────────────────────────────
# Static board evaluator
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_board(board: Board) -> int:
    """
    Evaluate the board from Black's perspective.
    Positive = good for Black, negative = good for White.

    Score = material + positional bonus
    """
    score = 0
    for r in range(8):
        for c in range(8):
            piece = board.grid[r][c]
            if piece is None:
                continue

            # Material value
            value = PIECE_VALUES[piece.type]

            # Positional bonus from lookup table
            table = POSITION_TABLES[piece.type]
            if piece.color == BLACK:
                # Black's table rows already match the grid orientation
                pos_bonus = table[r][c]
                score += value + pos_bonus
            else:
                # Mirror vertically for White
                pos_bonus = table[7 - r][c]
                score -= value + pos_bonus

    return score


# ─────────────────────────────────────────────────────────────────────────────
# Minimax with Alpha-Beta Pruning
# ─────────────────────────────────────────────────────────────────────────────

def minimax(board: Board, depth: int, alpha: int, beta: int,
            maximizing: bool) -> int:
    """
    Recursively evaluate positions.

    Parameters
    ----------
    board      : current board state (will be mutated then restored)
    depth      : how many more half-moves to look ahead
    alpha      : best score Black has found so far (starts at -∞)
    beta       : best score White has found so far (starts at +∞)
    maximizing : True when it's Black's turn (Black maximises)

    Returns the evaluation score for this subtree.
    """
    current_color = BLACK if maximizing else WHITE

    # ── Terminal / leaf node ─────────────────────────────────────────────
    if depth == 0:
        return evaluate_board(board)

    all_moves = board.all_legal_moves(current_color)

    if not all_moves:
        # Checkmate or stalemate
        if board.is_in_check(current_color):
            # The side to move is mated — very bad for them
            return -99999 if maximizing else 99999
        return 0   # stalemate

    # ── Recursive search ─────────────────────────────────────────────────
    if maximizing:   # Black's turn → maximise
        best = -99999
        for from_sq, to_sq in all_moves:
            undo = board.apply_move(from_sq, to_sq)
            score = minimax(board, depth - 1, alpha, beta, False)
            board.undo_move(undo)
            best  = max(best, score)
            alpha = max(alpha, best)
            if beta <= alpha:
                break   # ← Beta cut-off (White won't allow this line)
        return best
    else:            # White's turn → minimise
        best = 99999
        for from_sq, to_sq in all_moves:
            undo = board.apply_move(from_sq, to_sq)
            score = minimax(board, depth - 1, alpha, beta, True)
            board.undo_move(undo)
            best = min(best, score)
            beta = min(beta, best)
            if beta <= alpha:
                break   # ← Alpha cut-off (Black won't allow this line)
        return best


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

class ChessAI:
    """
    Wrapper that picks a difficulty level and exposes a single method:
    get_best_move(board) → (from_sq, to_sq)
    """

    def __init__(self, difficulty: str = "medium"):
        """
        difficulty : "easy"   → depth 1
                     "medium" → depth 3
        """
        if difficulty == "easy":
            self.depth = AI_EASY_DEPTH
        else:
            self.depth = AI_MEDIUM_DEPTH

    def get_best_move(self, board: Board) -> tuple | None:
        """
        Return the best (from_sq, to_sq) for Black, or None if no moves exist.
        """
        all_moves = board.all_legal_moves(BLACK)
        if not all_moves:
            return None

        # ── Depth-1 (Easy) uses a tiny random tie-break so it's not robotic ──
        random.shuffle(all_moves)

        best_score = -99999
        best_move  = all_moves[0]

        for from_sq, to_sq in all_moves:
            undo  = board.apply_move(from_sq, to_sq)
            score = minimax(board, self.depth - 1, -99999, 99999, False)
            board.undo_move(undo)

            if score > best_score:
                best_score = score
                best_move  = (from_sq, to_sq)

        return best_move
