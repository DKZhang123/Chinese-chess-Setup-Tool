# main_fixed_v2-3_updated.py
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog, simpledialog
import json, os, datetime, re
import chess_rules as xr
import draw_board as db


class XiangqiGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("象棋摆谱器 - 回合制简化版")
        self.root.minsize(600, 400)

        available_fonts = list(font.families())
        fam = next((f for f in db.PIECE_FONT_FAMILY_PREFERRED if f in available_fonts), available_fonts[0])
        self.piece_font = font.Font(family=fam, size=db.PIECE_FONT_SIZE, weight='bold')

        self.board = xr.Board()
        self.moves_list = []
        self.selected_sq = None

        self.offset_x = 0
        self.offset_y = 0

        self._build_ui()
        self.draw_board()

    def _build_ui(self):
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 棋盘区域
        self.board_frame = ttk.Frame(paned)
        self.canvas = tk.Canvas(self.board_frame, bg='#DEB887')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", self._on_resize)

        # 棋谱区域
        moves_frame = ttk.Frame(paned)
        ttk.Label(moves_frame, text="棋谱回合").pack(anchor=tk.W, padx=4, pady=(4,0))

        # ---- 将 Listbox 和滚动条放到同一个子框里（使滚动条"置于棋谱回合框中"） ----
        moves_box_frame = ttk.Frame(moves_frame, relief='flat')
        moves_box_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        v_scroll = ttk.Scrollbar(moves_box_frame, orient=tk.VERTICAL)
        h_scroll = ttk.Scrollbar(moves_box_frame, orient=tk.HORIZONTAL)

        self.moves_box = tk.Listbox(
            moves_box_frame,
            font=("SimHei", 12),
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            width=0,
            exportselection=False
        )
        # 把 listbox 与滚动条用 grid 布局紧凑放在 moves_box_frame 中
        self.moves_box.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # 允许 listbox 随父容器伸缩
        moves_box_frame.grid_rowconfigure(0, weight=1)
        moves_box_frame.grid_columnconfigure(0, weight=1)

        # 关联命令
        v_scroll.config(command=self.moves_box.yview)
        h_scroll.config(command=self.moves_box.xview)

        # 操作按钮
        ops = ttk.Frame(moves_frame)
        ops.pack(fill=tk.X, pady=4, padx=4)
        ttk.Button(ops, text="悔棋", command=self._undo).pack(fill=tk.X, pady=2)
        ttk.Button(ops, text="跳转到回合", command=self._goto_move_number).pack(fill=tk.X, pady=2)
        ttk.Button(ops, text="新局", command=self._new_game).pack(fill=tk.X, pady=2)
        ttk.Button(ops, text="保存棋谱", command=self._save_game).pack(fill=tk.X, pady=2)
        ttk.Button(ops, text="加载棋谱", command=self._load_game).pack(fill=tk.X, pady=2)

        paned.add(self.board_frame, weight=3)
        paned.add(moves_frame, weight=1)

        def enforce_min_width(event):
            try:
                sizes = paned.sashpos(0)
                total_width = paned.winfo_width()
                moves_width = total_width - sizes
                if moves_width < 150:
                    paned.sashpos(0, total_width - 150)
            except:
                pass
        paned.bind("<Configure>", enforce_min_width)

    def _on_resize(self, event):
        db.SQUARE_SIZE = min(
            max(20, (event.width - 2 * db.MARGIN) // db.BOARD_COLS),
            max(20, (event.height - 2 * db.MARGIN) // db.BOARD_ROWS)
        )
        board_width = (db.BOARD_COLS - 1) * db.SQUARE_SIZE + 2 * db.MARGIN
        board_height = (db.BOARD_ROWS - 1) * db.SQUARE_SIZE + 2 * db.MARGIN
        self.offset_x = (event.width - board_width) // 2
        self.offset_y = (event.height - board_height) // 2
        self.draw_board()

    def draw_board(self):
        for r in range(db.BOARD_ROWS):
            for c in range(db.BOARD_COLS):
                piece = self.board.piece_at((r, c))
                if piece is None:
                    db.board_data[r][c] = '.'
                else:
                    db.board_data[r][c] = piece.ptype.upper() if piece.color == 'r' else piece.ptype.lower()
        self.canvas.delete("all")
        db.draw_board(self.canvas, self.piece_font)

    def _on_canvas_click(self, event):
        sq = self._pixel_to_sq(event.x, event.y)
        if sq is None:
            return
        piece = self.board.piece_at(sq)
        if self.selected_sq is None:
            if piece and piece.color == self.board.side_to_move:
                self.selected_sq = sq
            return
        else:
            if sq == self.selected_sq:
                self.selected_sq = None
                return
            target_piece = self.board.piece_at(sq)
            if target_piece and target_piece.color == self.board.side_to_move:
                self.selected_sq = sq
                return
            mv = xr.Move(self.selected_sq, sq)
            legal = self.board.generate_legal_moves(self.board.side_to_move)
            matched = next((lm for lm in legal if lm.from_sq == mv.from_sq and lm.to_sq == mv.to_sq), None)
            if not matched:
                messagebox.showwarning("非法走子", "该走法不合法或会使自己被将。")
                self.selected_sq = None
                return
            self.board.make_move(matched)
            san = self._san_traditional(matched)
            self._append_move(san)
            self.selected_sq = None
            self.draw_board()
            self._refresh_moves_list()
            res = self.board.game_result()
            if res:
                if res.endswith('+'):
                    winner = '红方' if res.startswith('r') else '黑方'
                    messagebox.showinfo('对局结束', f'将死！胜者：{winner}')
                else:
                    messagebox.showinfo('对局结束', f'对局结束：{res}')

    def _pixel_to_sq(self, px, py):
        start_x = self.offset_x + db.MARGIN
        start_y = self.offset_y + db.MARGIN
        for r in range(db.BOARD_ROWS):
            for c in range(db.BOARD_COLS):
                cx = start_x + c * db.SQUARE_SIZE
                cy = start_y + r * db.SQUARE_SIZE
                if abs(px - cx) <= db.SQUARE_SIZE / 2 and abs(py - cy) <= db.SQUARE_SIZE / 2:
                    return (r, c)
        return None

    def _san_traditional(self, move: xr.Move) -> str:
        return self.board.move_to_chinese(move)

    def _append_move(self, san):
        if self.board.side_to_move == 'b':
            self.moves_list.append([san, ""])
        else:
            if self.moves_list:
                self.moves_list[-1][1] = san
            else:
                self.moves_list.append(["", san])

    def _refresh_moves_list(self):
        self.moves_box.delete(0, tk.END)
        for idx, (rmove, bmove) in enumerate(self.moves_list, start=1):
            line = f"{idx}. {rmove}  {bmove}"
            self.moves_box.insert(tk.END, line)

    def _undo(self):
        if not self.board.history:
            return
        self.board.undo_move()
        if self.board.side_to_move == 'r':
            if self.moves_list:
                self.moves_list[-1][1] = ""
        else:
            if self.moves_list:
                self.moves_list.pop()
        self.draw_board()
        self._refresh_moves_list()

    def _goto_move_number(self):
        txt = simpledialog.askinteger("跳转", "输入回合数：", parent=self.root)
        if not txt:
            return
        self.board = xr.Board()
        self.moves_list = self.moves_list[:txt - 1]
        for rmove, bmove in self.moves_list:
            if rmove:
                self._play_san(rmove)
            if bmove:
                self._play_san(bmove)
        self.draw_board()
        self._refresh_moves_list()

    def _new_game(self):
        if messagebox.askyesno("确认", "是否开始新局？", parent=self.root):
            self.board = xr.Board()
            self.moves_list.clear()
            self.selected_sq = None
            self.draw_board()
            self._refresh_moves_list()

    # ------------------------- 保存/加载：支持多格式 -------------------------
    def _save_game(self):
        filetypes = [
            ("CBR 棋谱", "*.cbr"),
            ("XQF 棋谱", "*.xqf"),
            ("PGN 棋谱", "*.pgn"),
            ("文本棋谱", "*.txt"),
            ("JSON 棋谱", "*.json"),
            ("所有文件", "*.*")
        ]
        fn = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=filetypes,
            parent=self.root
        )
        if not fn:
            return
        _, ext = os.path.splitext(fn)
        ext = ext.lower()
        try:
            if ext in ('.json', '.xqf', '.cbr'):
                # 保存与现有结构兼容的 JSON
                with open(fn, 'w', encoding='utf-8') as f:
                    json.dump({"moves": self.moves_list}, f, ensure_ascii=False, indent=2)
            elif ext == '.txt':
                with open(fn, 'w', encoding='utf-8') as f:
                    for idx, (rmove, bmove) in enumerate(self.moves_list, start=1):
                        line = f"{idx}. {rmove} {bmove}\n"
                        f.write(line)
            elif ext == '.pgn':
                # 生成一个很简单的 PGN 风格文本（非标准国际象棋 PGN，仅用于导出/交换）
                headers = [
                    f"[Event \"Local Game\"]",
                    f"[Date \"{datetime.date.today().strftime('%Y.%m.%d')}\"]",
                    f"[Result \"*\"]",
                    ""
                ]
                moves_tokens = []
                for idx, (rmove, bmove) in enumerate(self.moves_list, start=1):
                    if rmove:
                        moves_tokens.append(f"{idx}. {rmove}")
                    if bmove:
                        moves_tokens.append(f"{bmove}")
                body = ' '.join(moves_tokens) + ' *\n'
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(headers))
                    f.write(body)
            else:
                # 默认使用 json
                with open(fn, 'w', encoding='utf-8') as f:
                    json.dump({"moves": self.moves_list}, f, ensure_ascii=False, indent=2)
            messagebox.showinfo('保存成功', f'已保存：{fn}', parent=self.root)
        except Exception as e:
            messagebox.showerror('保存失败', str(e), parent=self.root)

    def _load_game(self):
        filetypes = [
            ("CBR 棋谱", "*.cbr"),
            ("XQF 棋谱", "*.xqf"),
            ("PGN 棋谱", "*.pgn"),
            ("文本棋谱", "*.txt"),
            ("JSON 棋谱", "*.json"),
            ("所有文件", "*.*")
        ]
        fn = filedialog.askopenfilename(filetypes=filetypes, parent=self.root)
        if not fn:
            return
        _, ext = os.path.splitext(fn)
        ext = ext.lower()
        try:
            if ext in ('.json', '.xqf', '.cbr'):
                with open(fn, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.moves_list = data.get('moves', [])
            elif ext == '.txt':
                moves = []
                with open(fn, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        # 形如: "1. 兵七进一 炮2平3" 或 "1. 兵七进一"
                        parts = line.split('.', 1)
                        if len(parts) == 2:
                            rest = parts[1].strip()
                        else:
                            rest = line
                        tokens = [t for t in rest.split() if t]
                        if not tokens:
                            continue
                        if len(tokens) == 1:
                            moves.append([tokens[0], ""])
                        else:
                            moves.append([tokens[0], tokens[1]])
                self.moves_list = moves
            elif ext == '.pgn':
                with open(fn, 'r', encoding='utf-8') as f:
                    text = f.read()
                # 去掉 header（方括号行），取 body
                body = '\n'.join([ln for ln in text.splitlines() if not ln.startswith('[')])
                # 移除结果符号
                body = body.replace('\n', ' ').strip()
                body = re.sub(r'\{[^}]*\}', '', body)  # 去掉注释 {...}
                tokens = [t for t in re.split(r'\s+', body) if t]
                moves = []
                cur = []
                for tok in tokens:
                    if re.match(r'^\d+\.$', tok):
                        continue
                    # 忽略星号等
                    if tok in ('*', '1-0', '0-1', '1/2-1/2'):
                        break
                    cur.append(tok)
                # cur 是一个按顺序的走子列表：['1.', '兵七进一', '炮2平3', '2.', '...']，但数字已去
                # 我们已清除数字，cur 应该只包含走子文本
                it = iter(cur)
                pairs = []
                tmp = []
                for tok in cur:
                    tmp.append(tok)
                # 将 tmp 按两步一组
                for i in range(0, len(tmp), 2):
                    rmove = tmp[i]
                    bmove = tmp[i+1] if i+1 < len(tmp) else ""
                    pairs.append([rmove, bmove])
                self.moves_list = pairs
            else:
                # 默认尝试 json
                with open(fn, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.moves_list = data.get('moves', [])

            # replay moves to board
            self.board = xr.Board()
            for rmove, bmove in self.moves_list:
                if rmove:
                    self._play_san(rmove)
                if bmove:
                    self._play_san(bmove)
            self.draw_board()
            self._refresh_moves_list()
            messagebox.showinfo('加载成功', f'已加载：{fn}', parent=self.root)
        except Exception as e:
            messagebox.showerror('加载失败', str(e), parent=self.root)

    def _play_san(self, san_str: str):
        # 尝试找到与 san_str 匹配的合法走子
        legal = self.board.generate_legal_moves(self.board.side_to_move)
        for mv in legal:
            if self.board.move_to_chinese(mv) == san_str:
                self.board.make_move(mv)
                return
        # 若未找到直接匹配，尝试更宽松的匹配（去掉前后空白）
        for mv in legal:
            if self.board.move_to_chinese(mv).strip() == san_str.strip():
                self.board.make_move(mv)
                return
        # 如果仍然找不到，抛出异常以便上层提示用户
        raise ValueError(f"无法在当前局面找到匹配的走法：{san_str}")


def main():
    root = tk.Tk()
    app = XiangqiGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
