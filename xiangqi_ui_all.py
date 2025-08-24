# -*- coding: utf-8 -*-
"""
整合版（含“变着=主线切换器”）：
- 在无变着版基础上，新增 Variation / VariationManager 与 VariationPanel
- “跳转后继续行棋=变着”，主线不变；右下“变着列表”仅用于切换主线
- 双击变着或点击“应用为主线”将从该步开始用所选变着覆盖主线之后的着法
- 文件读写仍以主线为准（不保存变着），窗口布局不变
依赖：chess_rules.py（作为 xr 导入）、draw_board.py（作为 db 导入）
"""

import os, re, json, sys, subprocess, datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import tkinter as tk
from tkinter import ttk, font, messagebox, filedialog, simpledialog

import chess_rules as xr
import draw_board as db


# ======================= 变着数据结构 =======================
@dataclass
class Variation:
    """某一步（pivot_ply，从1开始）的一个变着序列（中文记谱SAN列表）"""
    var_id: int
    name: str
    san_moves: List[str]

@dataclass
class VariationManager:
    """
    变着管理：{ pivot_ply(int) : List[Variation] }
    - pivot_ply = 被替换的那“一步”的编号（从1开始计半步：红1=1，黑1=2，红2=3，……）
    - 主线不存树；应用变着 = 主线[:pivot-1] + var.san_moves
    """
    variations: Dict[int, List[Variation]] = field(default_factory=dict)
    _next_var_id: int = 1

    def add(self, pivot_ply: int, san_seq: List[str], name: Optional[str] = None) -> int:
        if pivot_ply not in self.variations:
            self.variations[pivot_ply] = []
        var_id = self._next_var_id
        self._next_var_id += 1
        if not name:
            name = san_seq[0] if san_seq else f"变着{var_id}"
        self.variations[pivot_ply].append(Variation(var_id, name, list(san_seq)))
        return var_id

    def list(self, pivot_ply: int) -> List[Variation]:
        return self.variations.get(pivot_ply, [])

    def get(self, pivot_ply: int, var_id: int) -> Optional[Variation]:
        for v in self.variations.get(pivot_ply, []):
            if v.var_id == var_id:
                return v
        return None

    def remove(self, pivot_ply: int, var_id: int) -> bool:
        vs = self.variations.get(pivot_ply, [])
        before = len(vs)
        self.variations[pivot_ply] = [v for v in vs if v.var_id != var_id]
        return len(self.variations[pivot_ply]) != before


# ======================= state_utils.py =======================
APP_STATE_DIR = os.path.join(os.path.expanduser("~"), ".xiangqi_app")
RECENT_JSON = os.path.join(APP_STATE_DIR, "recent_games.json")
BOOKMARK_JSON = os.path.join(APP_STATE_DIR, "bookmarks.json")


def ensure_state_dir():
    os.makedirs(APP_STATE_DIR, exist_ok=True)


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, obj):
    try:
        ensure_state_dir()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ======================= menubar.py =======================
def create_menubar(gui):
    menubar = tk.Menu(gui.root)

    # ================= 文件 =================
    file_menu = tk.Menu(menubar, tearoff=False)
    file_menu.add_command(label="新建(N)", command=gui.new_game)
    file_menu.add_command(label="新建向导(W)...", command=gui.new_game_wizard)
    file_menu.add_command(label="新建到新窗口(Y)", command=lambda: gui.spawn_new_window(new_game=True))
    file_menu.add_separator()
    file_menu.add_command(label="打开(O)...", command=gui.load_game)
    file_menu.add_command(label="打开到新窗口(Z)...", command=lambda: gui.spawn_new_window(open_dialog=True))
    file_menu.add_separator()
    file_menu.add_command(label="保存(S)", command=gui.save_quick)
    file_menu.add_command(label="另存为(E/F)...", command=gui.save_game)
    file_menu.add_separator()
    file_menu.add_command(label="棋谱属性(P)...", command=gui.edit_properties)
    file_menu.add_command(label="删除当前棋谱(D)", command=gui.delete_current_game)
    file_menu.add_separator()
    file_menu.add_command(label="打开前一局(←)", command=lambda: gui.open_recent_shift(-1))
    file_menu.add_command(label="打开后一局(→)", command=lambda: gui.open_recent_shift(+1))

    gui.recent_submenu = tk.Menu(file_menu, tearoff=False)
    gui.refresh_recent_submenu()
    file_menu.add_cascade(label="最近打开(H)", menu=gui.recent_submenu)
    file_menu.add_separator()
    file_menu.add_command(label="退出(X)", command=gui.on_close)
    menubar.add_cascade(label="文件(F)", menu=file_menu)

    # ================= 编辑 =================
    edit_menu = tk.Menu(menubar, tearoff=False)
    edit_menu.add_command(label="撤销(U)    Ctrl+Z", command=gui.undo)
    edit_menu.add_command(label="重做(R)    Ctrl+Y", command=gui.redo)
    edit_menu.add_separator()
    edit_menu.add_command(label="复制棋谱文本(Q)", command=gui.copy_moves_text)
    edit_menu.add_command(label="复制 FEN", command=gui.copy_fen)
    edit_menu.add_command(label="导出棋盘图形(PS)...", command=gui.export_canvas_ps)
    edit_menu.add_separator()
    edit_menu.add_command(label="删除最后一步(Del)", command=gui.delete_last_move)
    edit_menu.add_command(label="左右交换(M)", command=gui.flip_left_right)
    edit_menu.add_command(label="红黑对调(A)", command=gui.swap_red_black)
    menubar.add_cascade(label="编辑(E)", menu=edit_menu)

    # ================= 书签 =================
    bm_menu = tk.Menu(menubar, tearoff=False)
    bm_menu.add_command(label="添加书签(M)", command=gui.bookmark_add)
    bm_menu.add_command(label="管理书签...", command=gui.bookmark_manage)
    bm_menu.add_command(label="跳转到书签...", command=gui.bookmark_jump)
    menubar.add_cascade(label="书签(M)", menu=bm_menu)

    # ================= 帮助 =================
    help_menu = tk.Menu(menubar, tearoff=False)
    help_menu.add_command(label="关于", command=gui.about)
    menubar.add_cascade(label="帮助(H)", menu=help_menu)

    return menubar


# ======================= board_canvas.py =======================
class BoardCanvas:
    """左侧棋盘画布 + 交互逻辑。"""

    def __init__(self, gui, parent):
        self.gui = gui
        self.frame = tk.Frame(parent)
        self.canvas = tk.Canvas(self.frame, bg='#DEB887')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 事件绑定
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Configure>", self._on_resize)

    # ---------- 绘制与高亮 ----------
    def draw_board(self):
        for r in range(db.BOARD_ROWS):
            for c in range(db.BOARD_COLS):
                piece = self.gui.board.piece_at((r, c))
                db.board_data[r][c] = '.' if piece is None else (
                    piece.ptype.upper() if piece.color == 'r' else piece.ptype.lower()
                )
        self.canvas.delete("all")
        db.draw_board(self.canvas, self.gui.piece_font)

    def clear_highlights(self):
        self.canvas.delete("sel"); self.canvas.delete("hint"); self.canvas.delete("hover")

    def update_highlights(self):
        self.clear_highlights()
        M, S = db.MARGIN, db.SQUARE_SIZE
        x1 = self.gui.offset_x + M
        y1 = self.gui.offset_y + M

        def center_of(rc):
            r, c = rc
            return (x1 + c * S, y1 + r * S)

        if self.gui.selected_sq is not None:
            cx, cy = center_of(self.gui.selected_sq)
            rad = S * 0.34
            self.canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                    outline="#CC0000", width=3, tag="sel")
        for tr in self.gui.legal_targets:
            cx, cy = center_of(tr)
            rad = S * 0.1
            tp = self.gui.board.piece_at(tr)
            if tp is None:
                self.canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                        fill="#2ecc71", outline="", tag="hint")
            else:
                self.canvas.create_oval(cx - rad*1.5, cy - rad*1.5, cx + rad*1.5, cy + rad*1.5,
                                        outline="#2ecc71", width=3, tag="hint")

    # ---------- 事件 ----------
    def _on_motion(self, e):
        _ = self._pixel_to_sq(e.x, e.y)
        self.update_highlights()

    def _on_click(self, event):
        sq = self._pixel_to_sq(event.x, event.y)
        if sq is None:
            return
        piece = self.gui.board.piece_at(sq)

        # 1) 选择
        if self.gui.selected_sq is None:
            if piece and piece.color == self.gui.board.side_to_move:
                self.gui.set_selection(sq)
            else:
                self.gui.set_selection(None)
            return

        # 2) 已选再点：切换/尝试走子
        if sq == self.gui.selected_sq:
            self.gui.set_selection(None)
            return
        if piece and piece.color == self.gui.board.side_to_move:
            self.gui.set_selection(sq)
            return

        # 合法性
        if sq in self.gui.legal_targets:
            mv = xr.Move(self.gui.selected_sq, sq)
            legal = self.gui.board.generate_legal_moves(self.gui.board.side_to_move)
            matched = next((lm for lm in legal if lm.from_sq == mv.from_sq and lm.to_sq == mv.to_sq), None)
            if not matched:
                messagebox.showwarning("非法走子", "该走法不合法或会使自己被将。")
                self.gui.set_selection(None)
                return

            # —— 先生成SAN，后落子 —— #
            san = self.gui.san_traditional(matched)
            self.gui.board.make_move(matched)

            # 交给GUI做“主线/变招”的记账
            self.gui.record_move_played(san)

            # 刷新
            self.gui.set_selection(None)
            self.draw_board()
            self.update_highlights()
            self.gui.refresh_moves_list()

            res = self.gui.board.game_result()
            if res:
                if res.endswith('+'):
                    winner = '红方' if res.startswith('r') else '黑方'
                    messagebox.showinfo('对局结束', f'将死！胜者：{winner}')
                else:
                    messagebox.showinfo('对局结束', f'对局结束：{res}')
            return

        self.gui.set_selection(None)

    # ---------- 缩放与像素↔格子 ----------
    def _on_resize(self, event):
        db.SQUARE_SIZE = min(
            max(20, (event.width - 2 * db.MARGIN) // db.BOARD_COLS),
            max(20, (event.height - 2 * db.MARGIN) // db.BOARD_ROWS)
        )
        board_width = (db.BOARD_COLS - 1) * db.SQUARE_SIZE + 2 * db.MARGIN
        board_height = (db.BOARD_ROWS - 1) * db.SQUARE_SIZE + 2 * db.MARGIN
        self.gui.offset_x = (event.width - board_width) // 2
        self.gui.offset_y = (event.height - board_height) // 2

        self.draw_board()
        self.update_highlights()

    def _pixel_to_sq(self, px, py):
        start_x = self.gui.offset_x + db.MARGIN
        start_y = self.gui.offset_y + db.MARGIN
        for r in range(db.BOARD_ROWS):
            for c in range(db.BOARD_COLS):
                cx = start_x + c * db.SQUARE_SIZE
                cy = start_y + r * db.SQUARE_SIZE
                if abs(px - cx) <= db.SQUARE_SIZE / 2 and abs(py - cy) <= db.SQUARE_SIZE / 2:
                    return (r, c)
        return None


# ======================= moves_panel.py =======================
class MovesPanel:
    """
    右侧左下：主线棋谱列表（两行一回合）
    - 单击/回车/双击：跳转到对应半步（ply）
    - 展示数据来自 GUI.get_display_moves()（当前主线）
    """
    def __init__(self, gui, parent):
        self.gui = gui
        self.frame = ttk.Frame(parent)

        ttk.Label(self.frame, text="主线棋谱", font=("Microsoft YaHei", 10, "bold")).pack(anchor=tk.W, padx=6, pady=(6, 2))

        box = ttk.Frame(self.frame)
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.listbox = tk.Listbox(
            box, font=("Courier New", 12),
            exportselection=False
        )
        vbar = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=vbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.index_to_ply = []  # 行索引 -> ply（可能为 None）

        self.listbox.bind("<<ListboxSelect>>", self._jump)
        self.listbox.bind("<Return>", self._jump)
        self.listbox.bind("<Double-Button-1>", self._jump)

    def refresh(self):
        self.listbox.delete(0, tk.END)
        self.index_to_ply.clear()

        moves_pairs = self.gui.get_display_moves()

        for idx, (rmove, bmove) in enumerate(moves_pairs, start=1):
            rmove = rmove or ""
            bmove = bmove or ""
            prefix = f"{idx}.  "

            # 红走行
            self.listbox.insert(tk.END, f"{prefix}{rmove}")
            ply_red = (2 * (idx - 1) + 1) if rmove else None
            self.index_to_ply.append(ply_red)

            # 黑走行
            self.listbox.insert(tk.END, f"{' ' * len(prefix)}{bmove}")
            ply_black = (2 * (idx - 1) + 2) if bmove else None
            self.index_to_ply.append(ply_black)

        self.listbox.see(tk.END)

    def _jump(self, _evt=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        row = int(sel[0])
        if 0 <= row < len(self.index_to_ply):
            ply = self.index_to_ply[row]
            if ply is not None:
                self.gui.on_move_row_selected(ply)

    def select_ply(self, ply: int):
        if ply <= 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.see(0)
            return
        move_idx = (ply - 1) // 2 + 1
        is_black = (ply % 2 == 0)
        row = (move_idx - 1) * 2 + (1 if is_black else 0)
        row = max(0, min(row, self.listbox.size() - 1))
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(row)
        self.listbox.see(row)


# ======================= variations_panel.py =======================
class VariationPanel:
    """右下“变着列表”（仅用于切换主线；双击应用）"""
    def __init__(self, gui, parent):
        self.gui = gui
        self.frame = ttk.Frame(parent)

        self.lbl = ttk.Label(self.frame, text="变着列表（第 ? 步）", font=("Microsoft YaHei", 10, "bold"))
        self.lbl.pack(anchor=tk.W, padx=6, pady=(6, 2))

        box = ttk.Frame(self.frame)
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.listbox = tk.Listbox(box, font=("Microsoft YaHei", 11), exportselection=False)
        vbar = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=vbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        btns = ttk.Frame(self.frame)
        btns.pack(fill=tk.X, padx=6, pady=(0, 8))
        ttk.Button(btns, text="应用为主线", command=self._apply_selected).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="删除", command=self._delete_selected).pack(side=tk.RIGHT, padx=4)

        self.listbox.bind("<Double-Button-1>", lambda e: self._apply_selected())

        self._cur_pivot = None   # 当前面板显示的 pivot_ply

    def refresh_for_pivot(self, pivot_ply: int):
        """根据 pivot_ply （从1开始）刷新变着列表"""
        self._cur_pivot = pivot_ply
        self.listbox.delete(0, tk.END)
        self.lbl.config(text=f"变着列表（第 {pivot_ply} 步）")
        vs = self.gui.var_mgr.list(pivot_ply)
        for v in vs:
            self.listbox.insert(tk.END, f"[{v.var_id}] {v.name}")

    def _selected_var_id(self) -> Optional[int]:
        sel = self.listbox.curselection()
        if not sel:
            return None
        text = self.listbox.get(sel[0])
        try:
            return int(text.split(']')[0].lstrip('['))
        except Exception:
            return None

    def _apply_selected(self):
        var_id = self._selected_var_id()
        if var_id is None or self._cur_pivot is None:
            return
        self.gui.apply_variation_by_id(self._cur_pivot, var_id)

    def _delete_selected(self):
        var_id = self._selected_var_id()
        if var_id is None or self._cur_pivot is None:
            return
        if messagebox.askyesno("删除变着", "确认删除选中变着？", parent=self.gui.root):
            if self.gui.var_mgr.remove(self._cur_pivot, var_id):
                self.refresh_for_pivot(self._cur_pivot)


# ======================= file_ops.py（略注：仍仅保存主线） =======================
class FileOps:
    def __init__(self, gui):
        self.gui = gui
        self.recent_files = read_json(RECENT_JSON, [])
        self.recent_index = -1

    # ---- 最近文件 ----
    def add_recent(self, path):
        if not path:
            return
        abspath = os.path.abspath(path)
        self.recent_files = [p for p in [abspath] + self.recent_files if p and os.path.exists(p)]
        uniq = []
        for p in self.recent_files:
            if p not in uniq:
                uniq.append(p)
        self.recent_files = uniq[:12]
        write_json(RECENT_JSON, self.recent_files)
        self.gui.refresh_recent_submenu()

    def refresh_recent_submenu(self):
        self.gui.recent_submenu.delete(0, 'end')
        if not self.recent_files:
            self.gui.recent_submenu.add_command(label="（空）", state='disabled')
            return
        for idx, p in enumerate(self.recent_files):
            disp = p if len(p) < 60 else ("..." + p[-57:])
            self.gui.recent_submenu.add_command(
                label=f"{idx+1}. {disp}",
                command=lambda pp=p, i=idx: self.open_recent_at(pp, i)
            )

    def open_recent_at(self, path, index):
        if not os.path.exists(path):
            messagebox.showwarning("提示", "文件不存在，已从‘最近’列表移除。")
            self.recent_files = [p for p in self.recent_files if p != path]
            write_json(RECENT_JSON, self.recent_files)
            self.gui.refresh_recent_submenu()
            return
        self.load_game_from_path(path)
        self.recent_index = index

    def open_recent_shift(self, delta):
        if not self.recent_files:
            messagebox.showinfo("提示", "暂无最近文件。")
            return
        if self.recent_index == -1:
            self.recent_index = 0
        self.recent_index = (self.recent_index + delta) % len(self.recent_files)
        self.open_recent_at(self.recent_files[self.recent_index], self.recent_index)

    # ---- 新建/打开/保存 ----
    def new_game(self):
        if messagebox.askyesno("确认", "是否开始新局？", parent=self.gui.root):
            self.gui.new_game()

    def new_game_wizard(self):
        title = simpledialog.askstring("新建向导", "棋谱标题：", parent=self.gui.root) or ""
        author = simpledialog.askstring("新建向导", "作者：", parent=self.gui.root) or ""
        side = simpledialog.askstring("新建向导", "先行方（r=红 / b=黑，默认红）：", parent=self.gui.root) or "r"
        self.gui.new_game()
        self.gui.metadata["title"] = title
        self.gui.metadata["author"] = author
        self.gui.board.side_to_move = 'r' if side.lower() != 'b' else 'b'
        self.gui.root.title(f"象棋摆谱器 - {self.gui.metadata['title'] or '新局'}")
        self.gui.mark_dirty()

    def spawn_new_window(self, new_game=False, open_dialog=False):
        exe = sys.executable
        main_py = os.path.join(os.path.dirname(__file__) if "__file__" in globals() else os.getcwd(), "main.py")
        main_py = os.path.abspath(main_py)
        args = [exe, main_py]
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(args, creationflags=subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen(args)
        except Exception as e:
            messagebox.showerror("错误", f"无法启动新窗口：{e}")
            return
        if open_dialog:
            messagebox.showinfo("提示", "已打开新窗口，请在新窗口中执行‘文件-打开’。")

    def save_quick(self):
        if 0 <= self.recent_index < len(self.recent_files):
            path = self.recent_files[self.recent_index]
            self.save_to_path(path)
        else:
            self.save_game()

    def save_game(self):
        filetypes = [
            ("JSON 棋谱（主线+注释）", "*.json"),
            ("文本棋谱（主线）", "*.txt"),
            ("PGN 棋谱（主线）", "*.pgn"),
            ("CBR 棋谱", "*.cbr"),
            ("XQF 棋谱", "*.xqf"),
            ("所有文件", "*.*"),
        ]
        fn = filedialog.asksaveasfilename(defaultextension=".json", filetypes=filetypes, parent=self.gui.root)
        if not fn:
            return
        self.save_to_path(fn)
        self.add_recent(fn)
        self.recent_index = self.recent_files.index(os.path.abspath(fn))

    def save_to_path(self, fn):
        _, ext = os.path.splitext(fn)
        ext = ext.lower()
        try:
            if ext in ('.json', '.xqf', '.cbr'):
                data = {
                    "moves": self.gui.moves_list,                    # 仅主线
                    "meta": self.gui.metadata,
                    "comments": {str(k): v for k, v in self.gui.comments.items()},
                }
                write_json(fn, data)

            elif ext == '.txt':
                with open(fn, 'w', encoding='utf-8') as f:
                    for idx, (rmove, bmove) in enumerate(self.gui.moves_list, start=1):
                        r = rmove or ""
                        b = bmove or ""
                        prefix = f"{idx}.  "
                        f.write(f"{prefix}{r}\n")
                        f.write(f"{' ' * len(prefix)}{b}\n")

            elif ext == '.pgn':
                headers = [
                    f"[Event \"Local Game\"]",
                    f"[Date \"{datetime.date.today().strftime('%Y.%m.%d')}\"]",
                    f"[Result \"*\"]",
                    ""
                ]
                tokens = []
                for idx, (rmove, bmove) in enumerate(self.gui.moves_list, start=1):
                    if rmove:
                        tokens.append(f"{idx}. {rmove}")
                    if bmove:
                        tokens.append(f"{bmove}")
                body = ' '.join(tokens) + ' *\n'
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(headers))
                    f.write(body)

            else:
                data = {"moves": self.gui.moves_list, "meta": self.gui.metadata}
                write_json(fn, data)

            self.gui.clear_dirty()
            messagebox.showinfo('保存成功', f'已保存：{fn}', parent=self.gui.root)
        except Exception as e:
            messagebox.showerror('保存失败', str(e), parent=self.gui.root)

    def load_game(self):
        filetypes = [
            ("JSON 棋谱（主线+注释）", "*.json"),
            ("文本棋谱", "*.txt"),
            ("PGN 棋谱", "*.pgn"),
            ("CBR 棋谱", "*.cbr"),
            ("XQF 棋谱", "*.xqf"),
            ("所有文件", "*.*"),
        ]
        fn = filedialog.askopenfilename(filetypes=filetypes, parent=self.gui.root)
        if not fn:
            return
        self.load_game_from_path(fn)
        self.add_recent(fn)
        self.recent_index = self.recent_files.index(os.path.abspath(fn))

    def load_game_from_path(self, fn):
        _, ext = os.path.splitext(fn)
        ext = ext.lower()
        try:
            if ext in ('.json', '.xqf', '.cbr'):
                with open(fn, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.gui.moves_list = data.get('moves', [])
                self.gui.metadata = data.get('meta', {"title": "", "author": "", "remark": ""})
                raw_comm = data.get('comments', {})
                self.gui.comments = {int(k): v for k, v in raw_comm.items()}

            elif ext == '.txt':
                moves = []
                with open(fn, 'r', encoding='utf-8') as f:
                    raw_lines = [ln.rstrip("\n") for ln in f]
                i = 0
                n = len(raw_lines)
                while i < n:
                    line = raw_lines[i].strip()
                    if not line:
                        i += 1; continue
                    m = re.match(r'^(\d+)\.\s+(.*)$', line)
                    if m:
                        rmove = (m.group(2) or "").strip()
                        bmove = ""
                        j = i + 1
                        while j < n and raw_lines[j].strip() == "":
                            j += 1
                        if j < n:
                            nxt = raw_lines[j].strip()
                            if not re.match(r'^\d+\.\s+', nxt):
                                bmove = nxt
                                i = j + 1
                            else:
                                i = i + 1
                        else:
                            i = i + 1
                        moves.append([rmove, bmove])
                        continue
                    parts = line.split('.', 1)
                    rest = parts[1].strip() if len(parts) == 2 else line
                    tokens = [t for t in rest.split() if t]
                    if tokens:
                        if len(tokens) == 1: moves.append([tokens[0], ""])
                        else: moves.append([tokens[0], tokens[1]])
                    i += 1
                self.gui.moves_list = moves
                self.gui.metadata = {"title": os.path.basename(fn), "author": "", "remark": ""}
                self.gui.comments = {}

            elif ext == '.pgn':
                with open(fn, 'r', encoding='utf-8') as f:
                    text = f.read()
                body = '\n'.join([ln for ln in text.splitlines() if not ln.startswith('[')])
                body = body.replace('\\n', ' ').strip()
                body = re.sub(r'\{[^}]*\}', '', body)
                tokens = [t for t in re.split(r'\s+', body) if t]
                cur = []
                for tok in tokens:
                    if re.match(r'^\d+\.$', tok): continue
                    if tok in ('*', '1-0', '0-1', '1/2-1/2'): break
                    cur.append(tok)
                pairs = []
                for i in range(0, len(cur), 2):
                    rmove = cur[i]
                    bmove = cur[i+1] if i+1 < len(cur) else ""
                    pairs.append([rmove, bmove])
                self.gui.moves_list = pairs
                self.gui.metadata = {"title": os.path.basename(fn), "author": "", "remark": ""}
                self.gui.comments = {}

            else:
                with open(fn, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.gui.moves_list = data.get('moves', [])
                self.gui.metadata = data.get('meta', {"title": "", "author": "", "remark": ""})
                self.gui.comments = {}

            # 重放到棋盘（主线）
            self.gui.board = xr.Board()
            for rmove, bmove in self.gui.moves_list:
                if rmove: self.gui._play_san_force(rmove)
                if bmove: self.gui._play_san_force(bmove)

            # 复位状态/界面
            self.gui._current_selected_ply = len(self.gui.board.history)
            self.gui._building_var = None
            self.gui.board_canvas.draw_board()
            self.gui.set_selection(None)
            self.gui.refresh_moves_list()
            self.gui._refresh_note_editor()
            self.gui.refresh_variations_box()  # 刷新当前步的变着列表
            self.gui.root.title(f"象棋摆谱器 - {self.gui.metadata.get('title') or os.path.basename(fn)}")
            self.gui.clear_dirty()
            messagebox.showinfo('加载成功', f'已加载：{fn}', parent=self.gui.root)
        except Exception as e:
            messagebox.showerror('加载失败', str(e), parent=self.gui.root)


# ======================= bookmark_ops.py =======================
class BookmarkOps:
    def __init__(self, gui):
        self.gui = gui
        self.bookmarks = read_json(BOOKMARK_JSON, {})  # {file_key: [{name, ply}, ...]}

    def file_key(self):
        if 0 <= self.gui.file_ops.recent_index < len(self.gui.file_ops.recent_files):
            return os.path.abspath(self.gui.file_ops.recent_files[self.gui.file_ops.recent_index])
        return f"__MEM__:{self.gui.metadata.get('title','新局')}"

    def current_ply(self):
        return len(self.gui.board.history)

    def bookmark_add(self):
        name = simpledialog.askstring("添加书签", "书签名称：", parent=self.gui.root)
        if not name:
            return
        fk = self.file_key()
        self.bookmarks.setdefault(fk, [])
        self.bookmarks[fk].append({"name": name, "ply": self.current_ply()})
        write_json(BOOKMARK_JSON, self.bookmarks)
        messagebox.showinfo("成功", "书签已添加。")

    def bookmark_manage(self):
        fk = self.file_key()
        num = len(self.bookmarks.get(fk, []))
        messagebox.showinfo("书签", f"当前棋谱共有 {num} 个书签。")

    def bookmark_jump(self):
        fk = self.file_key()
        items = self.bookmarks.get(fk, [])
        if not items:
            messagebox.showinfo("提示", "暂无书签。")
            return
        idx = simpledialog.askinteger("跳转到书签", f"共有 {len(items)} 个书签，输入序号(1~{len(items)})：", parent=self.gui.root)
        if not idx or not (1 <= idx <= len(items)):
            return
        ply = items[idx-1]["ply"]
        self._restore_to_ply(ply)

    def _restore_to_ply(self, ply):
        self.gui.board = xr.Board()
        cur = 0
        for rmove, bmove in self.gui.moves_list:
            if cur >= ply:
                break
            r = rmove if rmove else ""
            b = bmove if bmove else ""
            if r:
                if cur >= ply:
                    break
                self.gui.play_san(r)
                cur += 1
                if cur > ply:
                    break
            if b:
                if cur >= ply:
                    break
                self.gui.play_san(b)
                cur += 1
        self.gui.board_canvas.draw_board()
        self.gui.set_selection(None)
        self.gui.refresh_moves_list()
        self.gui.refresh_variations_box()
        self.gui.mark_dirty()


# ======================= transforms.py =======================
class Transforms:
    def __init__(self, gui):
        self.gui = gui

    def flip_left_right(self):
        new_board = xr.Board()
        new_board.history.clear()
        for r in range(10):
            for c in range(9):
                p = self.gui.board.piece_at((r, c))
                if p:
                    new_board.set_piece((r, 8 - c), xr.Piece(p.color, p.ptype, pid=p.pid))
                else:
                    new_board.set_piece((r, 8 - c), None)
        new_board.side_to_move = self.gui.board.side_to_move
        self.gui.board = new_board
        self.gui.board_canvas.draw_board()
        self.gui.set_selection(None)
        self.gui.refresh_moves_list()
        self.gui.refresh_variations_box()
        self.gui.mark_dirty()

    def swap_red_black(self):
        new_board = xr.Board()
        new_board.history.clear()
        for r in range(10):
            for c in range(9):
                p = self.gui.board.piece_at((r, c))
                if p:
                    new_color = 'b' if p.color == 'r' else 'r'
                    new_board.set_piece((9 - r, 8 - c), xr.Piece(new_color, p.ptype, pid=p.pid))
                else:
                    new_board.set_piece((9 - r, 8 - c), None)
        new_board.side_to_move = 'b' if self.gui.board.side_to_move == 'r' else 'r'
        self.gui.board = new_board
        self.gui.board_canvas.draw_board()
        self.gui.set_selection(None)
        self.gui.refresh_moves_list()
        self.gui.refresh_variations_box()
        self.gui.mark_dirty()


# ======================= main_ui.py（XiangqiGUI） =======================
class XiangqiGUI:
    """
    主组合类：XiangqiGUI（含“变着=主线切换器”）
    - 右侧：上=棋谱属性；下=左右分栏（左=主线棋谱；右=垂直分栏：上=注释，下=变着列表）
    """
    def __init__(self, root: tk.Tk):
        # —— 基本窗口 ——
        self.root = root
        self.root.title("象棋摆谱器")
        self.root.minsize(980, 640)

        # 未保存标志 + 退出拦截
        self._dirty = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 棋子字体（棋盘用）
        available_fonts = list(font.families())
        fam = next((f for f in db.PIECE_FONT_FAMILY_PREFERRED if f in available_fonts), available_fonts[0])
        self.piece_font = font.Font(family=fam, size=db.PIECE_FONT_SIZE, weight='bold')

        # 规则与主线数据
        self.board = xr.Board()
        self.moves_list: List[List[str]] = []          # 主线：[[红, 黑], ...]
        self.metadata = {"title": "", "author": "", "remark": ""}

        # 注释：{ ply(int): "注释文本" }
        self.comments: Dict[int, str] = {}

        # 变着
        self.var_mgr = VariationManager()
        self._building_var: Optional[Tuple[int, int]] = None  # (pivot_ply, var_id) 当前“录制中的变着”

        # 视图/交互状态
        self.selected_sq = None
        self.legal_targets = []
        self.offset_x = 0
        self.offset_y = 0

        # 当前注释/当前选择的半步
        self._current_selected_ply: Optional[int] = None

        # 子模块
        self.file_ops = FileOps(self)
        self.bm_ops = BookmarkOps(self)
        self.transforms = Transforms(self)

        # ===== 布局：左棋盘 + 右综合面板 =====
        root_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        root_paned.pack(fill=tk.BOTH, expand=True)

        # 左：棋盘
        self.board_canvas = BoardCanvas(self, root_paned)
        root_paned.add(self.board_canvas.frame, weight=3)

        # 右：上属性 + 下（左主线棋谱 | 右：上注释 + 下变着）
        right_paned = ttk.PanedWindow(root_paned, orient=tk.VERTICAL)
        root_paned.add(right_paned, weight=2)

        # 右-上：属性
        self.attr_frame = self._build_attr_frame(right_paned)
        right_paned.add(self.attr_frame, weight=1)

        # 右-下：左右分栏
        lower_paned = ttk.PanedWindow(right_paned, orient=tk.HORIZONTAL)
        right_paned.add(lower_paned, weight=3)

        # 左下：主线棋谱
        self.moves_panel = MovesPanel(self, lower_paned)
        lower_paned.add(self.moves_panel.frame, weight=1)

        # 右下：垂直分栏（上=注释 下=变着列表）
        right_bottom = ttk.PanedWindow(lower_paned, orient=tk.VERTICAL)
        lower_paned.add(right_bottom, weight=1)

        self.notes_frame = self._build_notes_frame(right_bottom)
        right_bottom.add(self.notes_frame, weight=3)

        self.vari_panel = VariationPanel(self, right_bottom)
        right_bottom.add(self.vari_panel.frame, weight=2)

        # 菜单栏
        self.recent_submenu = None
        self.root.config(menu=create_menubar(self))

        # 初次绘制
        self.board_canvas.draw_board()
        self.board_canvas.update_highlights()
        self.refresh_moves_list()
        self._refresh_note_editor()
        self.refresh_variations_box()

        # 快捷键
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

    # =================== 展示层：主线 ===================
    def get_display_moves(self):
        return self.moves_list

    # ================= 右上：属性 =================
    def _build_attr_frame(self, parent):
        frm = ttk.Frame(parent)
        ttk.Label(frm, text="棋谱属性", font=("Microsoft YaHei", 11, "bold")).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
        ttk.Label(frm, text="标题：").grid(row=1, column=0, sticky="e", padx=6, pady=2)
        ttk.Label(frm, text="作者：").grid(row=2, column=0, sticky="e", padx=6, pady=2)
        ttk.Label(frm, text="说明：").grid(row=3, column=0, sticky="ne", padx=6, pady=2)

        self.var_title = tk.StringVar(value=self.metadata.get("title", ""))
        self.var_author = tk.StringVar(value=self.metadata.get("author", ""))

        ent_title = ttk.Entry(frm, textvariable=self.var_title, width=38)
        ent_author = ttk.Entry(frm, textvariable=self.var_author, width=38)
        ent_title.grid(row=1, column=1, sticky="we", padx=6, pady=2)
        ent_author.grid(row=2, column=1, sticky="we", padx=6, pady=2)

        self.txt_remark = tk.Text(frm, width=44, height=4)
        self.txt_remark.insert("1.0", self.metadata.get("remark", ""))
        self.txt_remark.grid(row=3, column=1, sticky="we", padx=6, pady=2)

        def save_attr():
            self.metadata["title"] = self.var_title.get().strip()
            self.metadata["author"] = self.var_author.get().strip()
            self.metadata["remark"] = self.txt_remark.get("1.0", "end").strip()
            self.root.title(f"象棋摆谱器 - {self.metadata.get('title') or '未命名'}")
            self.mark_dirty()

        ttk.Button(frm, text="保存属性", command=save_attr).grid(row=4, column=1, sticky="e", padx=6, pady=(4, 8))
        frm.columnconfigure(1, weight=1)
        return frm

    # ================= 右下：注释 =================
    def _build_notes_frame(self, parent):
        frm = ttk.Frame(parent)
        ttk.Label(frm, text="注释（针对所选半步）", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", padx=6, pady=(6, 2))
        self.txt_note = tk.Text(frm, width=40, height=8)
        self.txt_note.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, padx=6, pady=(0, 8))
        ttk.Button(btns, text="保存注释", command=self._save_current_note).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="清空", command=lambda: self.txt_note.delete("1.0", "end")).pack(side=tk.RIGHT, padx=4)
        return frm

    def _refresh_note_editor(self):
        ply = self._current_selected_ply
        self.txt_note.delete("1.0", "end")
        if ply is None:
            return
        txt = self.comments.get(ply, "")
        if txt:
            self.txt_note.insert("1.0", txt)

    def _save_current_note(self):
        ply = self._current_selected_ply
        if ply is None:
            messagebox.showinfo("提示", "请先在棋谱中选择一个半步。")
            return
        self.comments[ply] = self.txt_note.get("1.0", "end").strip()
        self.mark_dirty()
        messagebox.showinfo("成功", f"已保存注释（ply={ply}）。")

    # ================= 小工具 =================
    def mark_dirty(self):
        self._dirty = True

    def clear_dirty(self):
        self._dirty = False

    # ================= 规则封装 =================
    def san_traditional(self, move: xr.Move) -> str:
        return self.board.move_to_chinese(move)

    def append_move_mainline(self, san):
        """主线追加（红黑交替；以 board.side_to_move 的下一手来判断）"""
        if self.board.side_to_move == 'b':
            self.moves_list.append([san, ""])
        else:
            if self.moves_list:
                self.moves_list[-1][1] = san
            else:
                self.moves_list.append(["", san])

    def refresh_moves_list(self):
        self.moves_panel.refresh()

    def set_selection(self, sq):
        self.selected_sq = sq
        if sq is None:
            self.legal_targets = []
            self.board_canvas.update_highlights()
            return
        legal = self.board.generate_legal_moves(self.board.side_to_move)
        self.legal_targets = [mv.to_sq for mv in legal if mv.from_sq == sq]
        self.board_canvas.update_highlights()

    # —— 记谱规范化（用于稳健匹配） ——
    def _normalize_san(self, s: str) -> str:
        if not s:
            return ""
        t = s.strip().replace(" ", "")
        full_to_half = str.maketrans("０１２３４５６７８９", "0123456789")
        t = t.translate(full_to_half)
        zh_digit_map = {"零": "0", "〇": "0", "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
                        "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
        for k, v in zh_digit_map.items():
            t = t.replace(k, v)
        rep = {"車": "车", "馬": "马", "傌": "马", "砲": "炮", "將": "将", "帥": "帅", "士": "仕"}
        for k, v in rep.items():
            t = t.replace(k, v)
        return t

    def play_san(self, san_str: str):
        target = self._normalize_san(san_str)
        legal = self.board.generate_legal_moves(self.board.side_to_move)
        for mv in legal:
            cand = self.board.move_to_chinese(mv)
            if cand == san_str or self._normalize_san(cand) == target or \
               self._normalize_san(cand).replace(".", "") == target.replace(".", ""):
                self.board.make_move(mv)
                return
        raise ValueError(f"无法在当前局面找到匹配的走法：{san_str}")

    def _play_san_force(self, san_str: str):
        try:
            self.play_san(san_str)
        except Exception:
            pass

    # ================= 撤销/跳转 =================
    def undo(self):
        if not self.board.history:
            return
        self.board.undo_move()
        self.board_canvas.draw_board()
        self.set_selection(None)
        self.refresh_moves_list()
        self.refresh_variations_box()
        self.mark_dirty()

    def delete_last_move(self):
        self.undo()

    def redo(self):
        messagebox.showinfo('提示', '暂未实现 Redo 功能。')

    def restore_to_ply(self, ply: int):
        """将棋局恢复到给定半步数（以“主线”为准）"""
        self.board = xr.Board()
        cur = 0
        for rmove, bmove in self.moves_list:
            if cur >= ply: break
            if rmove:
                if cur >= ply: break
                self._play_san_force(rmove); cur += 1
            if bmove:
                if cur >= ply: break
                self._play_san_force(bmove); cur += 1

        self._current_selected_ply = ply
        self._building_var = None            # 切换选择时，结束正在录制的变着
        self.board_canvas.draw_board()
        self.set_selection(None)
        self.refresh_moves_list()
        self._refresh_note_editor()
        self._select_moves_row_for_ply(ply)
        self.refresh_variations_box()

    def on_move_row_selected(self, ply: int):
        self.restore_to_ply(ply)

    def _select_moves_row_for_ply(self, ply: int):
        try:
            self.moves_panel.select_ply(ply)
        except Exception:
            pass

    # =================== 变着核心 ===================
    def _mainline_san_flat(self) -> List[str]:
        flat = []
        for rmove, bmove in self.moves_list:
            if rmove: flat.append(rmove)
            if bmove: flat.append(bmove)
        return flat

    def _apply_variation_to_mainline(self, pivot_ply: int, v: Variation, jump_to_end=False):
        """
        主线 := 主线[:pivot-1] + v.san_moves
        pivot_ply 从 1 开始；通常切换后跳到 pivot_ply 位置
        """
        old_flat = self._mainline_san_flat()
        new_flat = old_flat[:pivot_ply - 1] + list(v.san_moves)

        # 还原回 pair 结构
        new_pairs: List[Tuple[str, str]] = []
        it = iter(new_flat)
        for r in it:
            b = next(it, "")
            new_pairs.append([r, b])
        self.moves_list = new_pairs

        # 切换后定位
        if jump_to_end:
            tgt_ply = len(new_flat)
        else:
            tgt_ply = min(pivot_ply, len(new_flat))
        self.restore_to_ply(tgt_ply)

    def refresh_variations_box(self, pivot_ply: Optional[int] = None):
        if pivot_ply is None:
            # “当前步”的下一步为变着点
            base = self._current_selected_ply or 0
            pivot_ply = base + 1
        self.vari_panel.refresh_for_pivot(pivot_ply)

    def apply_variation_by_id(self, pivot_ply: int, var_id: int):
        v = self.var_mgr.get(pivot_ply, var_id)
        if not v:
            return
        self._apply_variation_to_mainline(pivot_ply, v, jump_to_end=False)
        self._building_var = None  # 应用后结束录制
        self.mark_dirty()

    def record_move_played(self, san: str):
        """
        由 BoardCanvas 在 make_move 后调用。
        逻辑：
        - 若当前选择 ply 位于主线末尾 => 直接追加到主线
        - 否则 => 录入为“当前步+1”的变着（若已有录制中的变着，则追加到该变着）
        """
        prev_sel = self._current_selected_ply
        if prev_sel is None:
            prev_sel = len(self._mainline_san_flat())
        flat_len = len(self._mainline_san_flat())

        if prev_sel == flat_len:
            # 在末尾继续：主线追加
            self.append_move_mainline(san)
            self._current_selected_ply = len(self.board.history)
            self._select_moves_row_for_ply(self._current_selected_ply)
            self.refresh_variations_box()
            self.mark_dirty()
            # 末尾走子 → 不是变着，结束任何录制
            self._building_var = None
            return

        # —— 非末尾：录为“变着” —— #
        pivot = prev_sel + 1  # 变着从下一步开始
        if self._building_var and self._building_var[0] == pivot:
            # 继续向同一条变着追加
            cur_var = self.var_mgr.get(pivot, self._building_var[1])
            if cur_var:
                cur_var.san_moves.append(san)
        else:
            # 新建一条变着
            var_id = self.var_mgr.add(pivot, [san], name=san)
            self._building_var = (pivot, var_id)

        # 更新右下变着列表（显示当前 pivot 的备选）
        self.refresh_variations_box(pivot_ply=pivot)
        self._current_selected_ply = len(self.board.history)
        self._select_moves_row_for_ply(self._current_selected_ply)
        # 注意：主线不变，等待用户从变着列表中选择切换
        self.mark_dirty()

    # ================= 菜单委托 =================
    # 文件
    def new_game(self):
        self.board = xr.Board()
        self.moves_list.clear()
        self.comments.clear()
        self.var_mgr = VariationManager()
        self._building_var = None
        self.metadata = {"title": "", "author": "", "remark": ""}
        self.selected_sq = None
        self.legal_targets = []
        self._current_selected_ply = None

        self.board_canvas.draw_board()
        self.board_canvas.update_highlights()
        self.refresh_moves_list()
        self._refresh_note_editor()
        self.refresh_variations_box()
        self.root.title("象棋摆谱器 - 新局")
        self.clear_dirty()

    def new_game_wizard(self):
        self.file_ops.new_game_wizard()

    def spawn_new_window(self, **kwargs):
        self.file_ops.spawn_new_window(**kwargs)

    def save_quick(self):
        self.file_ops.save_quick()

    def save_game(self):
        self.file_ops.save_game()

    def load_game(self):
        self.file_ops.load_game()

    def load_game_from_path(self, fn):
        self.file_ops.load_game_from_path(fn)

    def edit_properties(self):
        self.file_ops.edit_properties()

    def delete_current_game(self):
        self.file_ops.delete_current_game()

    def export_canvas_ps(self):
        self.file_ops.export_canvas_ps()

    def copy_fen(self):
        self.file_ops.copy_fen()

    def copy_moves_text(self):
        self.file_ops.copy_moves_text()

    def add_recent(self, path):
        self.file_ops.add_recent(path)

    def refresh_recent_submenu(self):
        self.file_ops.refresh_recent_submenu()

    def open_recent_at(self, path, index):
        self.file_ops.open_recent_at(path, index)

    def open_recent_shift(self, delta):
        self.file_ops.open_recent_shift(delta)

    # 书签
    def bookmark_add(self):
        self.bm_ops.bookmark_add()

    def bookmark_manage(self):
        self.bm_ops.bookmark_manage()

    def bookmark_jump(self):
        self.bm_ops.bookmark_jump()

    # 变换
    def flip_left_right(self):
        self.transforms.flip_left_right()

    def swap_red_black(self):
        self.transforms.swap_red_black()

    # 其它
    def about(self):
        messagebox.showinfo(
            "About",
            "Chinese Chess Learning\n"
            "- 单击棋谱任一步即可跳转到该局面\n"
            "- 跳转后继续行棋会记录为该步的“变着”（主线不改）\n"
            "- 右下变着列表用于切换主线（双击或点击“应用为主线”）"
        )

    # 退出
    def on_close(self):
        if self._dirty:
            ans = messagebox.askyesnocancel("未保存的更改", "是否保存当前更改？")
            if ans is None:
                return
            if ans:
                self.save_quick()
        self.root.destroy()


# ========== 方便外部导入 ==========
__all__ = ["XiangqiGUI"]
