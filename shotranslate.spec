# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置。

在项目根目录执行：

    pyinstaller shotranslate.spec --noconfirm

或者直接双击「打包exe.bat」。

注意：
* 采用 onedir（一个文件夹）而不是 onefile：onnxruntime + OpenCV + PyQt5 体积很大，
  onefile 每次启动都要把几百 MB 解压到临时目录，启动要等十几秒。
* 系统里装的 matplotlib / scipy / pandas / tkinter 等与本程序无关，
  必须显式排除，否则会被连带打进去并显著增大体积。
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

ROOT = Path(SPECPATH).resolve()

# 依赖装在 vendor/，必须让 PyInstaller 进程本身也能 import 到，
# 否则下面的 collect_data_files() 会报
# "skipping data collection for module ... as it is not a package"。
sys.path.insert(0, str(ROOT / "vendor"))

binaries = []

datas = [
    (str(ROOT / "resources" / "icon.ico"), "resources"),
    (str(ROOT / "app" / "ocr" / "winocr.ps1"), "app/ocr"),
]

# RapidOCR 的 ONNX 模型是包内数据文件，必须一起带上。
# 不放心只靠 collect_data_files，这里再按固定路径显式加一遍——缺了模型
# 打出来的 exe 会正常启动，但一截图就提示"没有可用的 OCR 引擎"。
_rapid = ROOT / "vendor" / "rapidocr_onnxruntime"
if _rapid.is_dir():
    if (_rapid / "models").is_dir():
        datas.append((str(_rapid / "models"), "rapidocr_onnxruntime/models"))
    if (_rapid / "config.yaml").is_file():
        datas.append((str(_rapid / "config.yaml"), "rapidocr_onnxruntime"))

for pkg in ("rapidocr_onnxruntime",):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# ---- 离线翻译引擎 ----
# ctranslate2 与 sentencepiece 的原生库收集放在 hooks/ 下的自定义钩子里。
# 这里**不能**用 collect_data_files / collect_dynamic_libs：它们会在
# PyInstaller 进程内部 import 目标包，而该进程此时已加载 PyQt5，
# 再 import sentencepiece 会让子进程直接崩溃
# （SubprocessDiedError: exit code 3221225477 = 0xC0000005 访问违例）。
# 详见 hooks/hook-sentencepiece.py 里的说明。

hiddenimports = [
    "rapidocr_onnxruntime",
    "onnxruntime",
    "shapely",
    "pyclipper",
    "yaml",
    "cv2",
    "mss",
    "pynput",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    # 注意：这里**不列** ctranslate2 / sentencepiece。
    # 列在 hiddenimports 里会让 PyInstaller 去 import 它们以取 __file__，
    # 而该进程已加载 PyQt5 → 子进程崩溃。这两个包由
    # app/translate/local.py 里的函数级 import 被静态分析发现，
    # 原生库文件则由 hooks/ 下的自定义钩子收集。
    "PyQt5.QtNetwork",
    "PyQt5.QtTextToSpeech",
]
for pkg in ("rapidocr_onnxruntime", "shapely", "pyclipper"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

excludes = [
    "matplotlib", "scipy", "pandas", "tkinter", "IPython", "notebook",
    "nbformat", "rembg", "skimage", "pywebview", "pythonnet", "clr_loader",
    "PyQt5.QtWebEngineWidgets", "PyQt5.QtQml", "PyQt5.QtQuick",
    "PyQt5.Qt3DCore", "PyQt5.QtBluetooth", "PyQt5.QtDesigner",
    "PyQt5.QtHelp", "PyQt5.QtLocation", "PyQt5.QtMultimediaWidgets",
    "PyQt5.QtNfc", "PyQt5.QtOpenGL", "PyQt5.QtPositioning",
    "PyQt5.QtQuickWidgets", "PyQt5.QtRemoteObjects", "PyQt5.QtSensors",
    "PyQt5.QtSerialPort", "PyQt5.QtSql", "PyQt5.QtTest", "PyQt5.QtWebChannel",
    "PyQt5.QtWebSockets", "PyQt5.QtXml", "PyQt5.QtXmlPatterns",
    "pytest", "setuptools", "pip",
]

block_cipher = None

a = Analysis(
    [str(ROOT / "main.py")],
    # vendor/ 必须一起加进 pathex：依赖是装在那个目录里的，
    # PyInstaller 不知道 main.py 运行时会往 sys.path 里插它，
    # 少了这一条 mss / pynput / rapidocr 全都找不到。
    pathex=[str(ROOT), str(ROOT / "vendor")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(ROOT / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# 统一 MSVC 运行库：移除 PyQt5 自带的副本
#
# PyQt5 的 wheel 里带了一份 MSVCP140.dll 与 MSVCP140_1.dll，版本和其它原生扩展
# 用的**不是同一个**；而且 `_internal/PyQt5/Qt5/bin` 会被 PyInstaller 的 Qt
# 运行时钩子加进 DLL 搜索路径。结果是 onnxruntime / ctranslate2 / sentencepiece
# 这些扩展可能加载到不匹配的运行库，表现为：
#
#   * onnxruntime  -> ImportError: DLL load failed while importing
#                     onnxruntime_pybind11_state: 动态链接库(DLL)初始化例程失败
#   * sentencepiece -> 进程直接崩溃（0xC0000005 访问违例）
#
# 统一使用 `_internal` 根目录那一份即可。MSVCP140_1.dll 别处没有（只有
# ctranslate2/onnxruntime 的部分扩展需要），所以把它搬到根目录保留。
# ---------------------------------------------------------------------------
import os as _os

# 注意元组格式：Analysis.binaries 内部是 (目标名, 源路径, 类型)，
# 和 datas 的 (源路径, 目标目录) 不一样，写反了会报
# "ValueError: Resource '.' is not a valid file!"。
_msvc_from_qt = [
    entry for entry in a.binaries
    if "PyQt5" in entry[0] and "msvcp" in _os.path.basename(entry[0]).lower()
]
if _msvc_from_qt:
    a.binaries[:] = [entry for entry in a.binaries if entry not in _msvc_from_qt]
    for _dest, _src, _kind in _msvc_from_qt:
        if _os.path.basename(_dest).lower().startswith("msvcp140_1"):
            a.binaries.append((_os.path.basename(_dest), _src, _kind))
    print("[spec] 已从 PyQt5 中移除 %d 个 MSVC 运行库副本（统一用 _internal 根目录那份）"
          % len(_msvc_from_qt))

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SnapTranslate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "resources" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SnapTranslate",
)
