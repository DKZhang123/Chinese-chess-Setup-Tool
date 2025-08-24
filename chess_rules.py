# xiangqi_rules.py
# -*- coding: utf-8 -*-
"""
在原实现基础上新增：
1) 长将过滤
2) 长捉过滤
3) 60 回合无吃子判和（120 ply）
说明：不改变 history 的三元组结构，新增 _meta_history 并在生成合法走法时试走检测。
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Iterable, Dict

# ===== 原常量与工具函数（保持不变） =====
ROWS = 10
COLS = 9
PIECE_TYPES = ('R', 'N', 'B', 'A', 'K', 'C', 'P')
CHINESE_NAME = {
    ('r', 'R'): '车', ('r', 'N'): '马', ('r', 'B'): '相', ('r', 'A'): '仕', ('r', 'K'): '帅', ('r', 'C'): '炮', ('r', 'P'): '兵',
    ('b', 'R'): '車', ('b', 'N'): '馬', ('b', 'B'): '象', ('b', 'A'): '士', ('b', 'K'): '將', ('b', 'C'): '炮', ('b', 'P'): '卒',
}
CN_NUM = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
PALACE_BLACK_ROWS = range(0, 3)
PALACE_RED_ROWS   = range(7, 10)
PALACE_COLS       = range(3, 6)

def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < ROWS and 0 <= c < COLS

# ======= 新增：为棋子增加稳定的唯一 id，便于“长捉”跟踪 =======
_g_next_pid = 1
def _next_pid() -> int:
    global _g_next_pid
    pid = _g_next_pid
    _g_next_pid += 1
    return pid

@dataclass
class Piece:
    color: str  # 'r' 或 'b'
    ptype: str  # 'R','N','B','A','K','C','P'
    pid: int = 0  # 新增：唯一 id（创建时自动分配）

    def __post_init__(self):
        if not self.pid:
            self.pid = _next_pid()

    def __repr__(self):
        return f"{self.color}{self.ptype}"

@dataclass
class Move:
    from_sq: Tuple[int, int]
    to_sq: Tuple[int, int]
    promote: Optional[str] = None
    comment: str = ""
    is_variation: bool = False

    def __repr__(self):
        return f"Move({self.from_sq}->{self.to_sq})"

class Board:
    def __init__(self, startpos: bool = True):
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.side_to_move: str = 'r'
        # 保持不变：history 仍是三元组 (move, captured_piece, prev_side)
        self.history: List[Tuple[Move, Optional[Piece], str]] = []
        # 新增：与 history 同步的元信息栈，不改变原 history 结构
        # 每元素：{"moved_pid":int, "captured":bool, "gave_check":bool,
        #          "chase_pair":(attacker_pid,target_pid)|None, "prev_halfmove":int}
        self._meta_history: List[Dict] = []
        # 新增：连续无吃子的半步计数（ply）
        self.halfmove_clock: int = 0
        if startpos:
            self.set_start_position()

    def set_start_position(self):
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        # 黑方
        top = [('R',0),('N',1),('B',2),('A',3),('K',4),('A',5),('B',6),('N',7),('R',8)]
        for ptype, c in top:
            self.board[0][c] = Piece('b', ptype)
        self.board[2][1] = Piece('b', 'C'); self.board[2][7] = Piece('b', 'C')
        for c in (0,2,4,6,8):
            self.board[3][c] = Piece('b', 'P')
        # 红方
        bot = [('R',0),('N',1),('B',2),('A',3),('K',4),('A',5),('B',6),('N',7),('R',8)]
        for ptype, c in bot:
            self.board[9][c] = Piece('r', ptype)
        self.board[7][1] = Piece('r', 'C'); self.board[7][7] = Piece('r', 'C')
        for c in (0,2,4,6,8):
            self.board[6][c] = Piece('r', 'P')

        self.side_to_move = 'r'
        self.history.clear()
        self._meta_history.clear()
        self.halfmove_clock = 0

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

    # ======= 新增：攻击判断（仅用于“长捉”标记） =======
    def _squares_attacked_by_piece(self, from_sq: Tuple[int,int], piece: Piece) -> List[Tuple[int,int]]:
        """返回该棋子此刻可直接吃到的格（忽略长将/长捉规则，仅依当前局面）。"""
        r,c = from_sq
        moves: List[Move] = []
        # 借用原伪合法生成，但只收集“可吃子”终点
        def add_if_capture(mr, mc):
            if in_bounds(mr,mc):
                tp = self.board[mr][mc]
                return tp is not None and tp.color != piece.color
            return False

        # 复用 _moves_for_piece 的核心判定
        ptype = piece.ptype
        attacked: List[Tuple[int,int]] = []
        if ptype in ('R','C'):
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr, nc = r+dr, c+dc
                jumped = False
                while in_bounds(nr,nc):
                    if self.board[nr][nc] is None:
                        if ptype == 'R':
                            pass
                        else:
                            nr += dr; nc += dc
                            continue
                    else:
                        if ptype == 'R':
                            if self.board[nr][nc].color != piece.color:
                                attacked.append((nr,nc))
                            break
                        else:
                            # 炮隔一个子打
                            nr2, nc2 = nr+dr, nc+dc
                            while in_bounds(nr2,nc2):
                                if self.board[nr2][nc2] is not None:
                                    if self.board[nr2][nc2].color != piece.color:
                                        attacked.append((nr2,nc2))
                                    break
                                nr2 += dr; nc2 += dc
                            break
                    nr += dr; nc += dc
        elif ptype == 'N':
            steps = [
                ((-2,-1),(-1,0)), ((-2,1),(-1,0)),
                ((2,-1),(1,0)), ((2,1),(1,0)),
                ((-1,-2),(0,-1)), ((1,-2),(0,-1)),
                ((-1,2),(0,1)), ((1,2),(0,1)),
            ]
            for (dr,dc),(lr,lc) in steps:
                leg_r, leg_c = r+lr, c+lc
                tr, tc = r+dr, c+dc
                if not in_bounds(tr,tc): continue
                if in_bounds(leg_r,leg_c) and self.board[leg_r][leg_c] is not None:
                    continue
                tp = self.board[tr][tc]
                if tp is not None and tp.color != piece.color:
                    attacked.append((tr,tc))
        elif ptype == 'B':
            for dr,dc in ((-2,-2),(-2,2),(2,-2),(2,2)):
                tr,tc = r+dr, c+dc
                er,ec = r+dr//2, c+dc//2
                if not in_bounds(tr,tc): continue
                if piece.color == 'r' and tr < 5: continue
                if piece.color == 'b' and tr > 4: continue
                if self.board[er][ec] is not None: continue
                tp = self.board[tr][tc]
                if tp is not None and tp.color != piece.color:
                    attacked.append((tr,tc))
        elif ptype == 'A':
            for dr,dc in ((-1,-1),(-1,1),(1,-1),(1,1)):
                tr,tc = r+dr,c+dc
                if not in_bounds(tr,tc): continue
                if piece.color == 'r':
                    if tr not in PALACE_RED_ROWS or tc not in PALACE_COLS: continue
                else:
                    if tr not in PALACE_BLACK_ROWS or tc not in PALACE_COLS: continue
                tp = self.board[tr][tc]
                if tp is not None and tp.color != piece.color:
                    attacked.append((tr,tc))
        elif ptype == 'K':
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                tr,tc = r+dr,c+dc
                if not in_bounds(tr,tc): continue
                if piece.color == 'r':
                    if tr not in PALACE_RED_ROWS or tc not in PALACE_COLS: continue
                else:
                    if tr not in PALACE_BLACK_ROWS or tc not in PALACE_COLS: continue
                tp = self.board[tr][tc]
                if tp is not None and tp.color != piece.color:
                    attacked.append((tr,tc))
        elif ptype == 'P':
            forward = -1 if piece.color == 'r' else 1
            # 前
            tr,tc = r+forward, c
            if in_bounds(tr,tc):
                tp = self.board[tr][tc]
                if tp is not None and tp.color != piece.color:
                    attacked.append((tr,tc))
            # 过河后左右
            river_crossed = (r < 5) if piece.color == 'r' else (r > 4)
            if river_crossed:
                for dc in (-1,1):
                    tr,tc = r, c+dc
                    if in_bounds(tr,tc):
                        tp = self.board[tr][tc]
                        if tp is not None and tp.color != piece.color:
                            attacked.append((tr,tc))
        return attacked

    def generate_legal_moves(self, color: Optional[str] = None) -> List[Move]:
        if color is None:
            color = self.side_to_move
        pseudo = self.generate_pseudo_legal_moves(color)
        legal: List[Move] = []
        for mv in pseudo:
            captured = self.make_move(mv)
            in_check = self.is_in_check(color)
            # 新增：长将/长捉检测（只对当前试走方）
            long_check = self._is_long_check_after_last_move(color)
            long_chase = self._is_long_chase_after_last_move(color)
            self.undo_move()
            if not in_check and not long_check and not long_chase:
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

    # ===== 原 _moves_for_piece 保持不变（略去注释） =====
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

    # ====== 核心：make_move/undo_move 中同步维护元信息与 halfmove_clock ======
    def make_move(self, move: Move) -> Optional[Piece]:
        fr = move.from_sq; to = move.to_sq
        piece = self.piece_at(fr)
        if piece is None:
            raise ValueError(f"来源格没有棋子: {fr}")
        captured = self.piece_at(to)
        side_before = self.side_to_move

        # 执行走子
        self.set_piece(to, piece)
        self.set_piece(fr, None)
        self.history.append((move, captured, side_before))
        self.side_to_move = 'b' if self.side_to_move == 'r' else 'r'

        # 检测“是否将军”与“是否形成追（攻击同一目标）”
        opponent = side_before if side_before != self.side_to_move else ('b' if side_before=='r' else 'r')
        gave_check = self.is_in_check(self.side_to_move)  # 走完后对手是否被将军
        # 计算 chase_pair：如果此步未吃子，且“该动子此刻直接攻击到某个对手棋”
        chase_pair = None
        if captured is None:
            attacked = self._squares_attacked_by_piece(to, piece)
            # 选一个最自然的目标（若有多枚被同一动子攻击，选任意一个即可用于“同目标”跟踪）
            if attacked:
                tr, tc = attacked[0]
                tp = self.board[tr][tc]
                if tp is not None and tp.color != piece.color:
                    chase_pair = (piece.pid, tp.pid)

        # halfmove 维护
        prev_half = self.halfmove_clock
        if captured is None:
            self.halfmove_clock += 1
        else:
            self.halfmove_clock = 0

        # 记录元信息
        self._meta_history.append({
            "moved_pid": piece.pid,
            "captured": captured is not None,
            "gave_check": gave_check,
            "chase_pair": chase_pair,
            "prev_halfmove": prev_half,
            "moved_color": side_before,
        })

        return captured

    def undo_move(self):
        if not self.history:
            return
        # 恢复原来三元组
        move, captured, side_before = self.history.pop()
        fr = move.from_sq; to = move.to_sq
        piece = self.piece_at(to)
        self.set_piece(fr, piece)
        self.set_piece(to, captured)
        self.side_to_move = side_before
        # 恢复元信息与 halfmove
        if self._meta_history:
            meta = self._meta_history.pop()
            self.halfmove_clock = meta["prev_halfmove"]

    # ======= 不变：is_in_check / is_checkmate / board_fen / pretty_print / move_to_chinese =======
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

    # ======= 新增：60 回合无吃子判和 =======
    def is_60_move_rule_draw(self) -> bool:
        return self.halfmove_clock >= 120  # 120 ply = 60 回合

    def game_result(self) -> Optional[str]:
        # 先检查和棋规则
        if self.is_60_move_rule_draw():
            return 'd'  # 和棋（可按需改为 '1/2-1/2(60)'）
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
        # —— 关键：先看 to_sq（兼容“先走后记”），取不到再看 from_sq（兼容“先记后走”）
        piece = self.piece_at(move.to_sq)
        if piece is None:
            piece = self.piece_at(move.from_sq)
        if piece is None:
            # 兜底：仍然给坐标，避免异常
            return f"{move.from_sq}->{move.to_sq}"

        def col_label(c: int, color: str, use_cn: bool) -> str:
            num = (9 - c) if color == 'r' else (c + 1)
            return CN_NUM[num] if use_cn else str(num)

        name = CHINESE_NAME.get((piece.color, piece.ptype), piece.ptype)
        fr = move.from_sq
        to = move.to_sq
        use_cn = (piece.color == 'r')

        # 同列同子判别“前/后”
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

        if piece.ptype in ('N', 'B', 'A'):
            action = '进' if (diff < 0 and piece.color == 'r') or (diff > 0 and piece.color == 'b') else '退'
            return f"{prefix}{name}{from_col}{action}{to_col}"
        elif piece.ptype in ('R', 'K'):
            if fr[1] == to[1]:
                step = abs(diff)
                action = '进' if (diff < 0 and piece.color == 'r') or (diff > 0 and piece.color == 'b') else '退'
                step_label = CN_NUM[step] if use_cn else str(step)
                return f"{prefix}{name}{from_col}{action}{step_label}"
            else:
                return f"{prefix}{name}{from_col}平{to_col}"
        elif piece.ptype in ('C', 'P'):
            if fr[1] == to[1]:
                step = abs(diff)
                action = '进' if (diff < 0 and piece.color == 'r') or (diff > 0 and piece.color == 'b') else '退'
                step_label = CN_NUM[step] if use_cn else str(step)
                return f"{prefix}{name}{from_col}{action}{step_label}"
            else:
                return f"{prefix}{name}{from_col}平{to_col}"
        else:
            return f"{prefix}{name}{from_col}-{to_col}"

    # ======= 新增：长将/长捉逻辑（内部与便于调用的外部方法） =======
    def _is_long_check_after_last_move(self, moved_color: str, threshold: int = 3) -> bool:
        """假设已经完成一次试走：判断“最近一次走子”是否使 moved_color 达到连续将军阈值。"""
        if not self._meta_history:
            return False
        # 最近一次必须给将
        if not self._meta_history[-1]["gave_check"] or self._meta_history[-1]["moved_color"] != moved_color:
            return False
        # 回溯统计：该颜色是否“每次轮到自己都在将军”，连续次数 >= threshold
        cnt = 0
        # 遍历从尾到头，交替颜色，数该侧最近连续的“自己回合给将”
        for i in range(len(self._meta_history)-1, -1, -1):
            m = self._meta_history[i]
            if m["moved_color"] == moved_color:
                if m["gave_check"]:
                    cnt += 1
                else:
                    break
            else:
                # 对手回合，跳过但不打断连续性（我们只关注“自己每回合是否都在将军”）
                continue
            if cnt >= threshold:
                return True
        return False

    def _is_long_chase_after_last_move(self, moved_color: str, threshold: int = 3) -> bool:
        """假设已经完成一次试走：判断“最近一次走子”是否使 moved_color 达到连续长捉阈值。"""
        if not self._meta_history:
            return False
        last = self._meta_history[-1]
        if last["moved_color"] != moved_color or last["chase_pair"] is None:
            return False
        target_pair = last["chase_pair"]  # (attacker_pid, target_pid)
        cnt = 0
        # 遍历并要求：该颜色最近每一次自己的回合，都出现同一 (attacker,target) 的追击
        for i in range(len(self._meta_history)-1, -1, -1):
            m = self._meta_history[i]
            if m["moved_color"] == moved_color:
                if m["chase_pair"] == target_pair:
                    cnt += 1
                else:
                    break
            else:
                continue
            if cnt >= threshold:
                return True
        return False

    # —— 对外便捷查询（不改变状态；内部做试走/回退） ——
    def is_long_check_if(self, move: Move, threshold: int = 3) -> bool:
        color = self.side_to_move
        self.make_move(move)
        flag = self._is_long_check_after_last_move(color, threshold)
        self.undo_move()
        return flag

    def is_long_chase_if(self, move: Move, threshold: int = 3) -> bool:
        color = self.side_to_move
        self.make_move(move)
        flag = self._is_long_chase_after_last_move(color, threshold)
        self.undo_move()
        return flag
