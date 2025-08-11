import os
import PyInstaller.__main__

# 入口文件
main_script = "main_fixed_v2-4.py"

# 生成的程序名
app_name = "象棋摆谱器"

# 打包命令参数
PyInstaller.__main__.run([
    main_script,
    '--noconsole',                  # 不显示命令行窗口
    '--name', app_name,             # 程序名称
    '--onefile',                    # 单文件 exe（可选：不想用单文件可删掉）
    '--add-data', 'chess_rules.py;.',
    '--add-data', 'draw_board.py;.',
    '--clean',                      # 清理临时文件
    '--hidden-import', 'tkinter',   # 确保 tkinter 打包
])

print("\n打包完成！可执行文件在 dist/ 文件夹中。")
