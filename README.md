# 🏆 象棋摆谱器 / Xiangqi Setup Tool

一个支持完整中国象棋规则、可保存与加载多种棋谱格式的桌面摆谱工具。  
A desktop tool for setting up and playing Xiangqi (Chinese Chess), with full rules and multi-format game save/load.

---

## ✨ 功能特点 / Features

- ♟ **完整规则**：支持将军、将死、合法走法判定  
  **Full Rules**: Supports check, checkmate, and legal move validation
- 🖥 **直观界面**：自动居中、缩放棋盘，支持点击走子  
  **Intuitive UI**: Auto-centering/scaling board, click-to-move
- 📜 **棋谱管理**：可滚动查看的回合列表（支持水平与垂直滚动条）  
  **Move List**: Scrollable with both vertical and horizontal scrollbars
- 💾 **多格式支持**：保存/加载 CBR、XQF、PGN、TXT、JSON  
  **Multi-format**: Save/load in CBR, XQF, PGN, TXT, JSON
- ↩ **常用功能**：悔棋、新局、跳转到指定回合  
  **Common Tools**: Undo, new game, jump to specific move
- 📦 **免安装运行**：可直接使用打包好的 exe 文件运行  
  **Standalone**: Run via packaged exe without installing Python

---

## 📥 安装与运行 / Installation & Run

### 方式 1：直接运行打包好的 exe（推荐）  
1. 从 [Releases](./releases) 下载最新版本的 `象棋摆谱器.exe`  
2. 双击运行（首次运行可能需要等待几秒）

### 方式 2：源码运行  
1. 安装 Python 3.8+  
2. 克隆本仓库：
   ```bash
   git clone https://github.com/你的用户名/xiangqi-setup-tool.git
   cd xiangqi-setup-tool
   ```
3. 安装依赖（仅使用 tkinter，无需额外第三方包）  
4. 运行：
   ```bash
   python main_fixed_v2-4.py
   ```

---

## 📖 使用方法 / Usage

1. **走子**：点击棋子 → 点击目标位置  
2. **悔棋**：撤销上一步操作  
3. **新局**：重置棋盘  
4. **跳转到回合**：快速回到某一步棋局面  
5. **保存/加载棋谱**：支持 CBR、XQF、PGN、TXT、JSON  
6. **窗口调整**：棋盘和棋谱栏随窗口自动调整并居中

---

## 🖼 截图 / Screenshots

> 这里可以放运行截图（在 GitHub 上传图片后会生成链接）

---

## 📌 后续计划 / Roadmap

- ✏ 棋谱注释与变着支持  
- 📂 扩展棋谱格式导入导出能力  
- 🤖 棋局分析与自动提示功能  

---

## 📜 License

本项目基于 MIT License 开源  
Licensed under the MIT License
