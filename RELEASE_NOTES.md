<!-- ═══════════════════════════════════════════════════════════════════════
     SnapTranslate v1.0.0 — bilingual release notes
     语言切换 / Language:  English  ·  简体中文
     ═══════════════════════════════════════════════════════════════════════ -->

# SnapTranslate v1.0.0 · 截译

**English** &nbsp;·&nbsp; [简体中文](#简体中文)

---

## English

> Press a hotkey → drag over any text on screen → offline OCR → floating translation window.

A **Windows screenshot translation tool** that lives in the system tray. Text recognition runs
**fully offline** (no network needed to read the characters), while translation goes through
several key-free providers with automatic failover. **Install and it just works — no account,
no API key.**

### 📦 Download

| File | Description |
| --- | --- |
| **`SnapTranslate-win64.zip`** | Portable build (122 MB). Extract and run `SnapTranslate.exe`. **No Python required.** |
| `Source code (zip)` | Source. Run `python tools/install_deps.py` first. |

> If SmartScreen blocks the first launch, choose **More info → Run anyway** (the binary is not
> code-signed).

### ✨ Highlights

- **Screenshot → translation in one gesture** — global hotkey opens a fullscreen selector; releasing the mouse shows the result
- **Fully offline OCR** — RapidOCR (PP-OCRv4 on onnxruntime), best-in-class on mixed Chinese/English, unlimited and free
- **Zero-configuration translation** — Youdao / Yandex / MyMemory built in, all key-free, with automatic failover if one fails
- **Optional LLM translation** — any OpenAI-compatible endpoint (DeepSeek, Kimi, Qwen, Zhipu, SiliconFlow)
- **Fully customizable hotkeys** — click the field and press a new combination; falls back to a keyboard hook when QQ / WeChat already own the keys
- **Thoughtful selection UX** — magnifier, size badge, 1-px arrow-key nudging, move & resize handles, select-whole-screen
- **Re-translate last region** — no need to re-select after scrolling or paging
- **Translate the clipboard** — copy text, press a hotkey, done
- **Result window** — always-on-top, draggable, side-by-side view, one-click copy, text-to-speech, engine switcher that re-translates instantly
- **Desktop shortcut / run at startup** — both one click away
- **Single instance** — launching again forwards the command to the running instance

### 🖥️ A real recognition result

Mixed Chinese/English, dark theme, coloured text, all in one capture:

```
Source                                          Translation
截图翻译测试 ScreenshotTranslationTest      →    Screenshots ScreenshotTranslationTest translation test
第二行：小字号中文识别，包含数字 12345      →    Second line: Small-sized Chinese character recognition,
与符号 #@！。                                    including the numbers 12345 and the symbol #@! .
快捷键 Ctrl+Alt+Z 触发截图翻译。            →    The shortcut key Ctrl+Alt+Z triggers the screenshot translation.
```

### 🚀 Quick start

1. Extract `SnapTranslate-win64.zip`
2. Run `SnapTranslate.exe` (the settings window opens on first start)
3. Press **`Ctrl + Alt + Z`** and drag over any text

| Default hotkey | Action |
| --- | --- |
| `Ctrl + Alt + Z` | Screenshot & translate |
| `Ctrl + Alt + X` | Translate the clipboard |
| `Ctrl + Alt + C` | Re-translate the last region |

### ✅ Verified before release

| Item | Result |
| --- | --- |
| Global hotkeys | Real keystrokes injected via `SendInput`; `Ctrl+Alt+Z` / `Ctrl+Alt+X` both fired correctly |
| End-to-end | OCR → translate → display all pass; key-free engines answer in 0.2–1.4 s |
| OCR accuracy | `12345`, `狐狸跳`, `Ctrl+Alt+Z` all correct (Windows built-in OCR gives `1234S`, `狐犭里眺`, `CtrI+AIt`) |
| HiDPI mapping | 2560×1600 physical / 1280×800 logical (200%); a 520×320 selection crops exactly 1040×640 |
| Single instance | Second launch forwards its command and exits in 970 ms; the running instance reacts within 0.4 s |
| Packaged build | Frozen exe verified end-to-end: “OCR 2 blocks / 43 chars in 1.18 s”, then translated in 1.16 s |
| UI | Result window 24 widgets, settings 5 tabs — all geometry checks pass |

### ⚠️ Known limitations

- **Windows only** (Win32 hotkeys, GDI capture, SAPI speech, WinRT OCR)
- Free translation endpoints are rate-limited; configure an LLM key for heavy use
- The RapidOCR Chinese model drops spaces between English words (spaces at CJK/Latin boundaries are restored automatically; switch to Windows OCR if you need exact English spacing)
- With monitors at **different** scaling factors the overlay renders at the primary monitor's ratio and may be slightly offset
- Google Translate needs a proxy in mainland China
- The binary is not code-signed

### 🔧 Run from source

```bat
python tools\install_deps.py     :: installs into the local vendor\ directory
python main.py                   :: start
```

See **README.md** for the full guide, FAQ, and implementation notes.

### 🙏 Credits

- [RapidOCR](https://github.com/RapidAI/RapidOCR) / [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — offline text recognition
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) — GUI
- [mss](https://github.com/BoboTiG/python-mss) — screen capture
- [pynput](https://github.com/moses-palmer/pynput) — keyboard hook fallback

### 📄 License

[MIT](LICENSE)

---

<a id="简体中文"></a>

## 简体中文

> 按下快捷键 → 框选屏幕上任意文字 → 自动识别 → 翻译结果悬浮窗。

一个常驻系统托盘的 **Windows 截图翻译工具**。文字识别**完全离线**（不联网也能把图上的字认出来），
翻译走多家免 Key 通道并带自动容错。**装完即用，不需要注册任何账号、不需要 API Key。**

### 📦 下载

| 文件 | 说明 |
| --- | --- |
| **`SnapTranslate-win64.zip`** | 免安装版（122 MB），解压后双击 `SnapTranslate.exe`，**不需要装 Python** |
| `Source code (zip)` | 源码，需要先执行 `python tools/install_deps.py` 装依赖 |

> 首次运行如果被 SmartScreen 拦下，选「更多信息 → 仍要运行」即可（程序没有代码签名）。

### ✨ 主要功能

- **一步截图即翻译** —— 全局快捷键唤出全屏框选，松开鼠标立刻出结果
- **完全离线的文字识别** —— RapidOCR（PP-OCRv4 + onnxruntime 本地推理），中英混排效果最好，不限量
- **零配置的翻译** —— 内置有道 / Yandex / MyMemory 三家免 Key 通道，一个失败自动换下一个
- **可选的 AI 大模型翻译** —— 兼容 OpenAI 协议（DeepSeek / Kimi / 通义 / 智谱 / 硅基流动）
- **高度可自定义的快捷键** —— 点一下输入框直接按新组合键即可录制；与 QQ / 微信的截图键冲突时自动降级到键盘钩子模式
- **贴心的框选交互** —— 放大镜、尺寸角标、方向键 1px 微调、选区可拖动可缩放、支持全选整屏
- **重译上次区域** —— 屏幕内容变了（翻页、滚动）不用重新框选
- **翻译剪贴板** —— 复制一段文字，快捷键直接翻译
- **结果窗** —— 可置顶、可拖动、双语对照、一键复制、语音朗读、换引擎自动重译
- **桌面快捷方式 / 开机自启** —— 一键创建，程序内可直接切换
- **单实例运行** —— 重复启动会把命令转发给已运行的实例

### 🖥️ 一次真实的识别结果

中英混排 + 深色主题 + 彩色文字，同一次截图内全部正确识别：

```
原文                                      译文
截图翻译测试 ScreenshotTranslationTest  →  Screenshots ScreenshotTranslationTest translation test
第二行：小字号中文识别，包含数字 12345   →  Second line: Small-sized Chinese character recognition,
与符号 #@！。                              including the numbers 12345 and the symbol #@! .
快捷键 Ctrl+Alt+Z 触发截图翻译。        →  The shortcut key Ctrl+Alt+Z triggers the screenshot translation.
```

### 🚀 快速上手

1. 解压 `SnapTranslate-win64.zip`
2. 双击 `SnapTranslate.exe`（首次会打开设置窗口）
3. 按 **`Ctrl + Alt + Z`** 框选屏幕上要翻译的文字

| 默认快捷键 | 作用 |
| --- | --- |
| `Ctrl + Alt + Z` | 截图翻译 |
| `Ctrl + Alt + X` | 翻译剪贴板 |
| `Ctrl + Alt + C` | 重译上次区域 |

### ✅ 发布前的实测结果

| 项目 | 结果 |
| --- | --- |
| 全局快捷键 | 用 `SendInput` 注入真实按键，`Ctrl+Alt+Z` / `Ctrl+Alt+X` 均正确触发 |
| 端到端链路 | 识别 → 翻译 → 显示 全通，免 Key 引擎 0.2~1.4s 出结果 |
| 识别准确率 | `12345`、`狐狸跳`、`Ctrl+Alt+Z` 全部认对（Windows 自带 OCR 会错成 `1234S`、`狐犭里眺`、`CtrI+AIt`） |
| 高 DPI 坐标 | 2560×1600 物理 / 1280×800 逻辑（缩放 200%），框选 520×320 精确裁出 1040×640 |
| 单实例转发 | 二次启动 970ms 转发命令后退出，主实例 0.4s 内响应 |
| 打包产物 | 冻结版 exe 实测：「识别 2 个文本块 / 43 字符，1.18s」→「翻译 1.16s」 |
| 界面 | 结果窗 24 个控件、设置窗 5 个标签页，几何自检全部通过 |

### ⚠️ 已知限制

- **仅支持 Windows**（依赖 Win32 热键、GDI 抓屏、SAPI 朗读、WinRT OCR）
- 免费翻译接口有频率限制，量大时建议在设置里配置大模型 Key
- RapidOCR 中文模型会吞掉英文词间空格（汉字与西文交界处已自动补齐，纯英文词间无法还原；可切换 Windows 自带 OCR）
- 多显示器**且各屏缩放比例不同**时，框选遮罩按主屏比例渲染，可能有轻微偏移
- Google 翻译在国内需要代理才能使用
- 程序无代码签名

### 🔧 从源码运行

```bat
python tools\install_deps.py     :: 依赖装进项目内的 vendor\ 目录
python main.py                   :: 启动
```

详细说明、常见问题与实现要点见仓库根目录的 **README.zh-CN.md**。

### 🙏 致谢

- [RapidOCR](https://github.com/RapidAI/RapidOCR) / [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) —— 离线文字识别
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) —— 图形界面
- [mss](https://github.com/BoboTiG/python-mss) —— 屏幕抓取
- [pynput](https://github.com/moses-palmer/pynput) —— 键盘钩子兜底

### 📄 License

[MIT](LICENSE)
