# -*- coding: utf-8 -*-
"""
新的 main.py
职责最小化：仅负责启动 Tk 窗口、加载拆分后的界面模块（ui.main_ui），
并确保 chess_rules.py 与 draw_board.py 被正常导入使用。
"""
import tkinter as tk
import chess_rules  # noqa: F401
import draw_board   # noqa: F401
from xiangqi_ui_all import XiangqiGUI



def main():
    root = tk.Tk()
    app = XiangqiGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
