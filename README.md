# 🏯 象棋摆谱器 (Xiangqi GUI)

一个基于 **Python + Tkinter** 的中国象棋摆谱与对局工具。  
A Chinese Chess (Xiangqi) study and notation tool built with **Python + Tkinter**.  

---

## ✨ 功能特性 (Features)
- 📌 **棋盘绘制 (Board Rendering)**  
  - 动态缩放、居中显示，支持中文棋子字体  
  - Dynamic scaling, centered display, Chinese character fonts  

- 📝 **棋谱管理 (Move List Management)**  
  - 单击棋谱任一步即可跳转局面  
  - Click any move to jump to that position  
  - 跳转后继续行棋会自动记录为 **变着**  
  - Continuing after a jump will be recorded as a **variation**  
  - 主线/变着自由切换（右下变着列表）  
  - Switch between mainline and variations (bottom-right list)  

- 💬 **注释支持 (Annotations)**  
  - 可针对任意一步棋添加文字说明  
  - Add comments to any move  

- 📚 **书签系统 (Bookmarks)**  
  - 快速定位棋局关键节点  
  - Quickly jump to key positions  

- 💾 **文件操作 (File Operations)**  
  - 导入/导出 JSON、TXT、PGN、XQF、CBR 格式  
  - Import/Export in JSON, TXT, PGN, XQF, CBR formats  
  - 最近打开文件管理  
  - Manage recently opened games  

- 🛡 **规则完善 (Rules Implemented)**  
  - 长将判负 (Lose by perpetual check)  
  - 长捉判负 (Lose by perpetual chase)  
  - **60 回合无吃子判和 (Draw after 60 moves without capture)**  

- 🎨 **界面优化 (UI Enhancements)**  
  - 支持左右翻转、红黑互换、棋谱属性编辑  
  - Flip board left/right, swap red/black, edit metadata  

---

## 🚀 使用方法 (How to Use)

### 方式一：直接运行 EXE (Option 1: Run Executable)
1. 前往 [Release 页面](../../releases) 下载最新的 **`Xiangqi.exe`**  
   Go to [Releases](../../releases) and download the latest **`Xiangqi.exe`**  
2. 双击运行，无需安装 Python 环境。  
   Run directly, no Python installation required.  

### 方式二：源码运行 (Option 2: Run from Source)
1. 安装 Python (>=3.9)  
   Install Python (>=3.9)  
2. 克隆仓库 / Clone repo:  
   ```bash
   git clone https://github.com/yourname/xiangqi.git
   cd xiangqi
   ```
3. 安装依赖（主要是 Tkinter，自带即可运行）  
   Install dependencies (Tkinter is included by default)  
4. 启动 / Run:  
   ```bash
   python main.py
   ```

---

## 🔧 开发者说明 (For Developers)
源码主要模块 (Main Modules):  
- `main.py`：入口文件，仅负责窗口启动  
  Entry point, starts the GUI window  
- `chess_rules.py`：棋局规则实现（含长将/长捉/60回合判和）  
  Xiangqi rules implementation (with long-check, long-chase, 60-move draw)  
- `draw_board.py`：棋盘与棋子绘制逻辑  
  Board and piece rendering logic  
- `xiangqi_ui_all.py`：整合 UI 界面（棋谱、注释、变着、菜单栏等）  
  Integrated UI (move list, annotations, variations, menu bar)  
- `build_exe.py`：基于 **PyInstaller** 的打包脚本  
  Packaging script using **PyInstaller**  

### 打包为 exe (Build Executable)
```bash
python build_exe.py
```
产物位于 / Output will be in:  
`dist/Xiangqi/Xiangqi.exe`

---

## 📦 Release 下载 (Releases)
- [➡️ 点击这里前往 Release 页面 / Go to Releases](../../releases)  
- 提供最新编译好的 `Xiangqi.exe`，直接运行即可体验  
- The latest compiled `Xiangqi.exe` is available, ready to run  

---

## 📜 License
MIT License.  
你可以自由修改和分发本项目，但请保留版权信息。  
You are free to modify and distribute this project, but please keep the license notice.  
