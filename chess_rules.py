# xiangqi_rules.py
# -*- coding: utf-8 -*-
"""
象棋规则模块
提供 Board、Move 等类与 API，供 GUI 主程序调用。
作者：自动生成（包含中文注释）
说明：
- 棋盘坐标：rows 0..9 (0 为最上，9 为最下)，cols 0..8 (0 为最左)
- 黑方（'b'）在上，红方（'r'）在下。红方向上移动（row-1），黑方向下移动（row+1）。
- 棋子内部类型使用英文简写，外部显示使用中文（在 CHINESE_NAME 中映射）。
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Iterable, Dict

# 常量
ROWS = 10
COLS = 9

# 棋子类型简写（内部使用）
PIECE_TYPES = ('R', 'N', 'B', 'A', 'K', 'C', 'P')  # 车,马,象/相,士/仕,将/帅,炮,卒/兵

# 中文显示名称（按颜色区分）
CHINESE_NAME = {
    ('r', 'R'): '车', ('r', 'N'): '马', ('r', 'B'): '相', ('r', 'A'): '仕', ('r', 'K'): '帅', ('r', 'C'): '炮', ('r', 'P'): '兵',
    ('b', 'R'): '車', ('b', 'N'): '馬', ('b', 'B'): '象', ('b', 'A'): '士', ('b', 'K'): '將', ('b', 'C'): '炮', ('b', 'P'): '卒',
}

# 汉字数字表（用于生成汉字列号或步数）
CN_NUM = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']

# Palace（九宫）坐标范围
PALACE_BLACK_ROWS = range(0, 3)   # 黑方九宫 0..2
PALACE_RED_ROWS = range(7, 10)    # 红方九宫 7..9
PALACE_COLS = range(3, 6)         # 列 3..5

def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < ROWS and 0 <= c < COLS

@dataclass
class Piece:
    """棋子：包含颜色和值（类型）"""
    color: str  # 'r' 或 'b'
    ptype: str  # 'R','N','B','A','K','C','P'

    def __repr__(self):
        return f"{self.color}{self.ptype}"

@dataclass
class Move:
    """走法：起点、终点，可选注释、变着标记"""
    from_sq: Tuple[int, int]
    to_sq: Tuple[int, int]
    promote: Optional[str] = None  # 象棋通常不用升变，保留字段
    comment: str = ""             # 走法注释
    is_variation: bool = False    # 是否为变着（供 GUI 标记）

    def __repr__(self):
        return f"Move({self.from_sq}->{self.to_sq})"

class Board:
    """
    棋盘类
    - board: 二维数组，元素为 Piece 或 None
    - history: 保存 (move, captured_piece, prev_side) 以支持撤销
    """
    def __init__(self, startpos: bool = True):
        # 初始化空棋盘
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.side_to_move: str = 'r'  # 红先默认
        self.history: List[Tuple[Move, Optional[Piece], str]] = []  # (move, captured, side_before)
        if startpos:
            self.set_start_position()

    def set_start_position(self):
        """设置标准起始局面（简洁版本）"""
        # 清空
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        # 黑方主力（第0行）
        top = [
            ('R',0),('N',1),('B',2),('A',3),('K',4),('A',5),('B',6),('N',7),('R',8)
        ]
        for ptype, c in top:
            self.board[0][c] = Piece('b', ptype)
        # 黑炮（第2行，列 1 和 7）
        self.board[2][1] = Piece('b', 'C')
        self.board[2][7] = Piece('b', 'C')
        # 黑兵（第3行，列 0,2,4,6,8） ——卒
        for c in (0,2,4,6,8):
            self.board[3][c] = Piece('b', 'P')

        # 红方主力（第9行）
        bot = [
            ('R',0),('N',1),('B',2),('A',3),('K',4),('A',5),('B',6),('N',7),('R',8)
        ]
        for ptype, c in bot:
            self.board[9][c] = Piece('r', ptype)
        # 红炮（第7行）
        self.board[7][1] = Piece('r', 'C')
        self.board[7][7] = Piece('r', 'C')
        # 红兵（第6行）
        for c in (0,2,4,6,8):
            self.board[6][c] = Piece('r', 'P')

        self.side_to_move = 'r'
        self.history.clear()

    def piece_at(self, sq: Tuple[int,int]) -> Optional[Piece]:
        r,c = sq
        if not in_bounds(r,c): return None
        return self.board[r][c]

    def set_piece(self, sq: Tuple[int,int], piece: Optional[Piece]):
        r,c = sq
        if not in_bounds(r,c): return
        self.board[r][c] = piece

    def find_king(self, color: str) -> Optional[Tuple[int,int]]:
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p and p.color == color and p.ptype == 'K':
                    return (r,c)
        return None

    def generate_legal_moves(self, color: Optional[str] = None) -> List[Move]:
        if color is None:
            color = self.side_to_move
        pseudo = self.generate_pseudo_legal_moves(color)
        legal = []
        for mv in pseudo:
            captured = self.make_move(mv)
            in_check = self.is_in_check(color)
            self.undo_move()
            if not in_check:
                legal.append(mv)
        return legal

    def generate_pseudo_legal_moves(self, color: Optional[str] = None) -> List[Move]:
        if color is None:
            color = self.side_to_move
        moves: List[Move] = []
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p and p.color == color:
                    moves.extend(self._moves_for_piece((r,c), p))
        return moves

    def _moves_for_piece(self, sq: Tuple[int,int], piece: Piece) -> List[Move]:
        r,c = sq
        ptype = piece.ptype
        color = piece.color
        moves: List[Move] = []

        def can_capture(to_r, to_c):
            if not in_bounds(to_r,to_c): return False
            tp = self.board[to_r][to_c]
            return tp is None or tp.color != color

        if ptype == 'R' or ptype == 'C':
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr, nc = r+dr, c+dc
                while in_bounds(nr,nc):
                    if ptype == 'R':
                        if self.board[nr][nc] is None:
                            moves.append(Move((r,c),(nr,nc)))
                        else:
                            if self.board[nr][nc].color != color:
                                moves.append(Move((r,c),(nr,nc)))
                            break
                    else:
                        if self.board[nr][nc] is None:
                            moves.append(Move((r,c),(nr,nc)))
                            nr += dr; nc += dc
                            continue
                        else:
                            blocker_r, blocker_c = nr, nc
                            nr2, nc2 = blocker_r + dr, blocker_c + dc
                            while in_bounds(nr2,nc2):
                                if self.board[nr2][nc2] is not None:
                                    if self.board[nr2][nc2].color != color:
                                        moves.append(Move((r,c),(nr2,nc2)))
                                    break
                                nr2 += dr; nc2 += dc
                            break
                    nr += dr; nc += dc

        elif ptype == 'N':
            knight_steps = [
                ((-2,-1),(-1,0)), ((-2,1),(-1,0)),
                ((2,-1),(1,0)), ((2,1),(1,0)),
                ((-1,-2),(0,-1)), ((1,-2),(0,-1)),
                ((-1,2),(0,1)), ((1,2),(0,1)),
            ]
            for (dr,dc),(leg_dr,leg_dc) in knight_steps:
                leg_r, leg_c = r + leg_dr, c + leg_dc
                to_r, to_c = r + dr, c + dc
                if not in_bounds(to_r,to_c): continue
                if in_bounds(leg_r,leg_c) and self.board[leg_r][leg_c] is not None:
                    continue
                if can_capture(to_r,to_c):
                    moves.append(Move((r,c),(to_r,to_c)))

        elif ptype == 'B':
            directions = [(-2,-2),(-2,2),(2,-2),(2,2)]
            for dr,dc in directions:
                to_r, to_c = r+dr, c+dc
                eye_r, eye_c = r+dr//2, c+dc//2
                if not in_bounds(to_r,to_c): continue
                if piece.color == 'r' and to_r < 5:
                    pass_ok = False
                elif piece.color == 'b' and to_r > 4:
                    pass_ok = False
                else:
                    pass_ok = True
                if not pass_ok: continue
                if in_bounds(eye_r,eye_c) and self.board[eye_r][eye_c] is not None:
                    continue
                if can_capture(to_r,to_c):
                    moves.append(Move((r,c),(to_r,to_c)))

        elif ptype == 'A':
            for dr,dc in ((-1,-1),(-1,1),(1,-1),(1,1)):
                to_r,to_c = r+dr,c+dc
                if not in_bounds(to_r,to_c): continue
                if piece.color == 'r':
                    if to_r not in PALACE_RED_ROWS or to_c not in PALACE_COLS:
                        continue
                else:
                    if to_r not in PALACE_BLACK_ROWS or to_c not in PALACE_COLS:
                        continue
                if can_capture(to_r,to_c):
                    moves.append(Move((r,c),(to_r,to_c)))

        elif ptype == 'K':
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                to_r,to_c = r+dr,c+dc
                if not in_bounds(to_r,to_c): continue
                if piece.color == 'r':
                    if to_r not in PALACE_RED_ROWS or to_c not in PALACE_COLS:
                        continue
                else:
                    if to_r not in PALACE_BLACK_ROWS or to_c not in PALACE_COLS:
                        continue
                if can_capture(to_r,to_c):
                    moves.append(Move((r,c),(to_r,to_c)))

        elif ptype == 'P':
            if piece.color == 'r':
                forward = -1
                river_crossed = r < 5
            else:
                forward = 1
                river_crossed = r > 4

            to_r, to_c = r + forward, c
            if in_bounds(to_r,to_c) and can_capture(to_r,to_c):
                moves.append(Move((r,c),(to_r,to_c)))
            if river_crossed:
                for dc in (-1,1):
                    to_r, to_c = r, c+dc
                    if in_bounds(to_r,to_c) and can_capture(to_r,to_c):
                        moves.append(Move((r,c),(to_r,to_c)))

        return moves

    def make_move(self, move: Move) -> Optional[Piece]:
        fr = move.from_sq; to = move.to_sq
        piece = self.piece_at(fr)
        if piece is None:
            raise ValueError(f"来源格没有棋子: {fr}")
        captured = self.piece_at(to)
        side_before = self.side_to_move
        self.set_piece(to, piece)
        self.set_piece(fr, None)
        self.history.append((move, captured, side_before))
        self.side_to_move = 'b' if self.side_to_move == 'r' else 'r'
        return captured

    def undo_move(self):
        if not self.history:
            return
        move, captured, side_before = self.history.pop()
        fr = move.from_sq; to = move.to_sq
        piece = self.piece_at(to)
        self.set_piece(fr, piece)
        self.set_piece(to, captured)
        self.side_to_move = side_before

    def is_in_check(self, color: str) -> bool:
        king_sq = self.find_king(color)
        if king_sq is None:
            return True
        opponent = 'b' if color == 'r' else 'r'
        for mv in self.generate_pseudo_legal_moves(opponent):
            if mv.to_sq == king_sq:
                return True
        opp_king_sq = self.find_king(opponent)
        if opp_king_sq:
            kr, kc = king_sq
            ork, okc = opp_king_sq
            if kc == okc:
                step = 1 if ork > kr else -1
                r = kr + step
                blocked = False
                while r != ork:
                    if self.board[r][kc] is not None:
                        blocked = True
                        break
                    r += step
                if not blocked:
                    return True
        return False

    def is_checkmate(self, color: str) -> bool:
        moves = self.generate_legal_moves(color)
        if not moves and self.is_in_check(color):
            return True
        return False

    def game_result(self) -> Optional[str]:
        if self.is_checkmate('r'):
            return 'b+'
        if self.is_checkmate('b'):
            return 'r+'
        if not self.generate_legal_moves('r'):
            return 'b-'
        if not self.generate_legal_moves('b'):
            return 'r-'
        return None

    def board_fen(self) -> str:
        rows = []
        for r in range(ROWS):
            empty = 0
            row_s = []
            for c in range(COLS):
                p = self.board[r][c]
                if p is None:
                    empty += 1
                else:
                    if empty:
                        row_s.append(str(empty)); empty = 0
                    code = p.ptype if p.color == 'r' else p.ptype.lower()
                    row_s.append(code)
            if empty:
                row_s.append(str(empty))
            rows.append(''.join(row_s))
        return '/'.join(rows) + f" {self.side_to_move}"

    def pretty_print(self):
        for r in range(ROWS):
            row_elems = []
            for c in range(COLS):
                p = self.board[r][c]
                if p is None:
                    row_elems.append('・')
                else:
                    row_elems.append(CHINESE_NAME.get((p.color,p.ptype), repr(p)))
            print(' '.join(row_elems))
        print(f"轮：{'红' if self.side_to_move=='r' else '黑'}")
        res = self.game_result()
        if res:
            print("局势：", res)

    def move_to_chinese(self, move: Move) -> str:
        """
        红方列号用汉字，黑方列号用数字；
        同列多子时加“前”/“后”消歧。
        对马(N)、相/象(B)、士/仕(A) 不使用“平”，始终用“进/退”+目标列号。
        """
        def col_label(c: int, color: str, use_cn: bool) -> str:
            num = (9 - c) if color == 'r' else (c + 1)
            return CN_NUM[num] if use_cn else str(num)

        if not self.history:
            piece = self.piece_at(move.from_sq)
        else:
            last_move, _, _ = self.history[-1]
            piece = self.piece_at(last_move.to_sq)
        if not piece:
            return f"{move.from_sq}->{move.to_sq}"

        name = CHINESE_NAME.get((piece.color, piece.ptype), piece.ptype)
        fr = move.from_sq
        to = move.to_sq
        use_cn = (piece.color == 'r')

        same_col_pieces = []
        for r in range(ROWS):
            p = self.board[r][fr[1]]
            if p and p.color == piece.color and p.ptype == piece.ptype:
                same_col_pieces.append((r, fr[1]))
        prefix = ""
        if len(same_col_pieces) > 1:
            if piece.color == 'r':
                same_col_pieces.sort(key=lambda sq: sq[0])
                prefix = "前" if fr == same_col_pieces[0] else "后"
            else:
                same_col_pieces.sort(key=lambda sq: sq[0], reverse=True)
                prefix = "前" if fr == same_col_pieces[0] else "后"

        from_col = col_label(fr[1], piece.color, use_cn)
        to_col = col_label(to[1], piece.color, use_cn)
        diff = to[0] - fr[0]

        if piece.ptype in ('N','B','A'):
            action = '进' if (diff < 0 and piece.color == 'r') or (diff > 0 and piece.color == 'b') else '退'
            return f"{prefix}{name}{from_col}{action}{to_col}"
        elif piece.ptype in ('R','K'):
            if fr[1] == to[1]:
                step = abs(diff)
                action = '进' if (diff < 0 and piece.color == 'r') or (diff > 0 and piece.color == 'b') else '退'
                step_label = CN_NUM[step] if use_cn else str(step)
                return f"{prefix}{name}{from_col}{action}{step_label}"
            else:
                return f"{prefix}{name}{from_col}平{to_col}"
        elif piece.ptype in ('C','P'):
            if fr[1] == to[1]:
                step = abs(diff)
                action = '进' if (diff < 0 and piece.color == 'r') or (diff > 0 and piece.color == 'b') else '退'
                step_label = CN_NUM[step] if use_cn else str(step)
                return f"{prefix}{name}{from_col}{action}{step_label}"
            else:
                return f"{prefix}{name}{from_col}平{to_col}"
        else:
            return f"{prefix}{name}{from_col}-{to_col}"

if __name__ == "__main__":
    b = Board()
    print("初始局面 FEN:", b.board_fen())
    b.pretty_print()
    moves = b.generate_pseudo_legal_moves('r')
    print("红方伪合法走法数：", len(moves))
    legal = b.generate_legal_moves('r')
    print("红方合法走法数：", len(legal))
    if legal:
        m = legal[0]
        print("尝试第一步：", m)
        captured = b.make_move(m)
        print("走子后的棋谱表示：", b.move_to_chinese(m))
        b.pretty_print()
        b.undo_move()
        b.pretty_print()
