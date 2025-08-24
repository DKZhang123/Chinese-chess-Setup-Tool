# build_exe.py
import os
import sys
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "Xiangqi"

SPEC_TEXT = r'''
from PyInstaller.utils.hooks import collect_submodules
hidden = collect_submodules('tkinter')
block_cipher = None
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('xiangqi_ui_all.py', '.'),
        ('chess_rules.py', '.'),
        ('draw_board.py', '.'),
    ],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='Xiangqi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='Xiangqi'
)
'''

def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "pyinstaller"])

def main():
    ensure_pyinstaller()
    spec = HERE / "main.spec"
    spec.write_text(SPEC_TEXT, encoding="utf-8")
    # 清理旧产物
    for d in ("build", "dist"):
        p = HERE / d
        if p.exists():
            shutil.rmtree(p)
    # 打包
    subprocess.check_call([sys.executable, "-m", "PyInstaller", str(spec)])
    print("\n✅ 构建完成：", HERE / "dist" / f"{NAME}" / f"{NAME}.exe")
    print("（如需单文件，可将 SPEC 改成 EXE(..., console=False) + --onefile 方案。）")

if __name__ == "__main__":
    main()
