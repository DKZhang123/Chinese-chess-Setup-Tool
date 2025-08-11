import tkinter as tk
from tkinter import font as tkfont

# ==== 棋盘与界面参数 ====
SQUARE_SIZE = 64  # 这个会被 main.py 动态修改
BOARD_ROWS = 10
BOARD_COLS = 9
MARGIN = 30
PIECE_FONT_FAMILY_PREFERRED = ['SimHei', '黑体', 'Microsoft YaHei', 'Arial']
PIECE_FONT_SIZE = 28  # 初始值，动态变化

# 棋子中文名称
PIECE_NAMES = {
    'K': '帅', 'k': '将',
    'A': '仕', 'a': '士',
    'B': '相', 'b': '象',
    'N': '马', 'n': '马',
    'R': '车', 'r': '车',
    'C': '炮', 'c': '炮',
    'P': '兵', 'p': '卒',
    '.': '.'
}

# 棋盘数据
board_data = [
    list('r n b a k a b n r'.split()),
    list('. . . . . . . . .'.split()),
    list('. c . . . . . c .'.split()),
    list('p . p . p . p . p'.split()),
    list('. . . . . . . . .'.split()),
    list('. . . . . . . . .'.split()),
    list('P . P . P . P . P'.split()),
    list('. C . . . . . C .'.split()),
    list('. . . . . . . . .'.split()),
    list('R N B A K A B N R'.split()),
]

def draw_board(canvas, piece_font=None):
    """绘制棋盘和棋子，支持动态缩放和居中"""
    canvas.delete('all')

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    board_width = (BOARD_COLS - 1) * SQUARE_SIZE + 2 * MARGIN
    board_height = (BOARD_ROWS - 1) * SQUARE_SIZE + 2 * MARGIN

    # 计算居中偏移
    offset_x = (canvas_width - board_width) // 2
    offset_y = (canvas_height - board_height) // 2

    # 动态调整字体大小
    if piece_font is None:
        available_fonts = list(tkfont.families())
        fam = next((f for f in PIECE_FONT_FAMILY_PREFERRED if f in available_fonts), available_fonts[0])
        size = max(10, int(SQUARE_SIZE * 0.44))
        piece_font = tkfont.Font(family=fam, size=size, weight='bold')
    else:
        size = max(10, int(SQUARE_SIZE * 0.44))
        piece_font.configure(size=size)

    # 外框
    x1 = offset_x + MARGIN
    y1 = offset_y + MARGIN
    x2 = x1 + (BOARD_COLS - 1) * SQUARE_SIZE
    y2 = y1 + (BOARD_ROWS - 1) * SQUARE_SIZE
    canvas.create_rectangle(x1, y1, x2, y2, outline='#8B4513', width=3)

    # 横线
    for r in range(BOARD_ROWS):
        y = y1 + r * SQUARE_SIZE
        canvas.create_line(x1, y, x2, y, fill='#8B4513', width=2)

    # 竖线（河界断开）
    for c in range(BOARD_COLS):
        x = x1 + c * SQUARE_SIZE
        if c == 0 or c == BOARD_COLS - 1:
            canvas.create_line(x, y1, x, y2, fill='#8B4513', width=2)
        else:
            canvas.create_line(x, y1, x, y1 + 4 * SQUARE_SIZE, fill='#8B4513', width=2)
            canvas.create_line(x, y1 + 5 * SQUARE_SIZE, x, y2, fill='#8B4513', width=2)

    # 九宫斜线
    canvas.create_line(x1 + 3 * SQUARE_SIZE, y1, x1 + 5 * SQUARE_SIZE, y1 + 2 * SQUARE_SIZE, fill='#8B4513', width=2)
    canvas.create_line(x1 + 5 * SQUARE_SIZE, y1, x1 + 3 * SQUARE_SIZE, y1 + 2 * SQUARE_SIZE, fill='#8B4513', width=2)
    canvas.create_line(x1 + 3 * SQUARE_SIZE, y1 + 7 * SQUARE_SIZE, x1 + 5 * SQUARE_SIZE, y1 + 9 * SQUARE_SIZE, fill='#8B4513', width=2)
    canvas.create_line(x1 + 5 * SQUARE_SIZE, y1 + 7 * SQUARE_SIZE, x1 + 3 * SQUARE_SIZE, y1 + 9 * SQUARE_SIZE, fill='#8B4513', width=2)

    # 楚河汉界
    canvas.create_text(x1 + 2 * SQUARE_SIZE, y1 + 4.5 * SQUARE_SIZE, text='楚河', font=piece_font, fill='#8B0000')
    canvas.create_text(x1 + 6 * SQUARE_SIZE, y1 + 4.5 * SQUARE_SIZE, text='汉界', font=piece_font, fill='#8B0000')

    # 棋子
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            ch = board_data[r][c]
            if ch != '.':
                name = PIECE_NAMES.get(ch, ch)
                cx = x1 + c * SQUARE_SIZE
                cy = y1 + r * SQUARE_SIZE
                rad = SQUARE_SIZE * 0.42
                if ch.isupper():  # 红子
                    canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill='#FFF8DC', outline='red', width=2)
                    canvas.create_text(cx, cy, text=name, font=piece_font, fill='red')
                else:  # 黑子
                    canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill='black', outline='black', width=2)
                    canvas.create_text(cx, cy, text=name, font=piece_font, fill='white')


if __name__ == '__main__':
    root = tk.Tk()
    root.title("象棋棋盘绘制示例")
    canvas = tk.Canvas(root, bg='#DEB887')
    canvas.pack(padx=10, pady=8, fill=tk.BOTH, expand=True)

    available_fonts = list(tkfont.families())
    fam = next((f for f in PIECE_FONT_FAMILY_PREFERRED if f in available_fonts), available_fonts[0])
    piece_font = tkfont.Font(family=fam, size=PIECE_FONT_SIZE, weight='bold')

    def on_resize(event):
        global SQUARE_SIZE
        SQUARE_SIZE = min(
            max(20, (event.width - 2 * MARGIN) // BOARD_COLS),
            max(20, (event.height - 2 * MARGIN) // BOARD_ROWS)
        )
        draw_board(canvas, piece_font)

    root.bind("<Configure>", on_resize)
    draw_board(canvas, piece_font)
    root.mainloop()
