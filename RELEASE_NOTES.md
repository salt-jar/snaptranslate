<!-- ═══════════════════════════════════════════════════════════════════════
     SnapTranslate v1.1.0 — bilingual release notes
     语言切换 / Language:  English  ·  简体中文
     ═══════════════════════════════════════════════════════════════════════ -->

# SnapTranslate v1.1.0 · 截译

**English** &nbsp;·&nbsp; [简体中文](#简体中文)

---

## English

> Press a hotkey → drag over any text on screen → offline OCR → floating translation window.

### 🆕 What's new in v1.1.0

**Fully offline translation.** Download a language pack once, and from then on **your text
never leaves your computer** — the app makes no network requests at all while translating.

- **Local neural machine translation** running on your CPU (OPUS-MT via CTranslate2)
- **100 language packs** available; Chinese ⇄ English is ~70 MB per direction
- **No silent fallback to the cloud.** If you select local translation and the model fails,
  you get an error. Your text is *not* quietly sent to an online engine — choosing local
  translation is usually a privacy decision, and a silent fallback would cancel it.
- **Line structure preserved** — each line is translated as its own unit and batched in a
  single inference call, so multi-line screenshots don't collapse into one paragraph
- Download packs from *Settings → Translation engines → Manage offline packs*, or from the
  command line: `python tools\offline_pack.py --download zh-en en-zh`

**Also in this release**

- The language-pack index is fetched through multiple mirrors (jsDelivr CDN first), because
  `raw.githubusercontent.com` is unreliable in some regions
- `自检.bat` / `selftest.py` gained an offline-translation section that includes a
  privacy assertion (local mode must never produce an online fallback chain)

### 📦 Download

| File | Description |
| --- | --- |
| **`SnapTranslate-win64.zip`** | Portable build. Extract and run `SnapTranslate.exe`. **No Python required.** |
| `Source code (zip)` | Source. Run `python tools/install_deps.py` first. |

> If SmartScreen blocks the first launch, choose **More info → Run anyway** (the binary is not
> code-signed).

### ✨ Highlights

- **Screenshot → translation in one gesture** — global hotkey opens a fullscreen selector; releasing the mouse shows the result
- **Fully offline OCR** — RapidOCR (PP-OCRv4 on onnxruntime), best-in-class on mixed Chinese/English, unlimited and free
- **Fully offline translation (optional)** — language packs, zero network requests while translating
- **Zero-configuration online translation** — Youdao / Yandex / MyMemory built in, all key-free, with automatic failover
- **Optional LLM translation** — any OpenAI-compatible endpoint (DeepSeek, Kimi, Qwen, Zhipu, SiliconFlow)
- **Fully customizable hotkeys** — click the field and press a new combination; falls back to a keyboard hook when QQ / WeChat already own the keys
- **Thoughtful selection UX** — magnifier, size badge, 1-px arrow-key nudging, move & resize handles, select-whole-screen
- **Re-translate last region** — no need to re-select after scrolling or paging
- **Translate the clipboard** — copy text, press a hotkey, done
- **Result window** — always-on-top, draggable, side-by-side view, one-click copy, text-to-speech, engine switcher that re-translates instantly
- **Desktop shortcut / run at startup** — both one click away
- **Single instance** — launching again forwards the command to the running instance

### 🖥️ A real recognition result

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

**For offline translation:** *Settings → Translation engines → Manage offline packs* →
download Chinese ⇄ English → set the engine to **Local offline translation**.

### ✅ Verified before release

| Item | Result |
| --- | --- |
| Global hotkeys | Real keystrokes injected via `SendInput`; `Ctrl+Alt+Z` / `Ctrl+Alt+X` both fired correctly |
| End-to-end | OCR → translate → display all pass; online engines answer in 0.2–1.4 s |
| Offline translation | First call 401 ms (model load), then 37–60 ms per sentence; a 232-character paragraph in 0.27 s |
| Offline privacy | `engine=local` produces the candidate chain `['local']` — no online fallback exists |
| Offline round-trip | zh→en and en→zh both correct, line structure preserved (4 lines in → 4 lines out) |
| Offline E2E | OCR → local translation → display in 0.81 s |
| OCR accuracy | `12345`, `狐狸跳`, `Ctrl+Alt+Z` all correct (Windows built-in OCR gives `1234S`, `狐犭里眺`, `CtrI+AIt`) |
| HiDPI mapping | 2560×1600 physical / 1280×800 logical (200%); a 520×320 selection crops exactly 1040×640 |
| Single instance | Second launch forwards its command and exits in 970 ms |
| UI | Result window, settings, and language-pack manager all pass geometry checks |

### ⚠️ Known limitations

- **Windows only** (Win32 hotkeys, GDI capture, SAPI speech, WinRT OCR)
- Offline translation quality is below the online engines — it uses compact OPUS-MT models
  that run on CPU. Use it for privacy; use the online engines (or an LLM key) for polish.
- Offline language packs are English-centric: other pairs pivot through English
- Free translation endpoints are rate-limited
- The RapidOCR Chinese model drops spaces between English words (boundary spaces are restored automatically)
- With monitors at **different** scaling factors the overlay may be slightly offset
- The binary is not code-signed

### 🔧 Run from source

```bat
python tools\install_deps.py     :: installs into the local vendor\ directory
python main.py                   :: start
python tools\offline_pack.py --download zh-en en-zh   :: offline language packs
```

See **README.md** for the full guide, FAQ, and implementation notes.

### 🙏 Credits

- [RapidOCR](https://github.com/RapidAI/RapidOCR) / [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — offline text recognition
- [CTranslate2](https://github.com/OpenNMT/CTranslate2) / [OPUS-MT](https://github.com/Helsinki-NLP/Opus-MT) — offline translation models
- [Argos Translate](https://github.com/argosopentech/argos-translate) — language-pack format and index
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) — GUI
- [mss](https://github.com/BoboTiG/python-mss) — screen capture
- [pynput](https://github.com/moses-palmer/pynput) — keyboard hook fallback

### 📄 License

[MIT](LICENSE)

---

<a id="简体中文"></a>

## 简体中文

> 按下快捷键 → 框选屏幕上任意文字 → 自动识别 → 翻译结果悬浮窗。

### 🆕 v1.1.0 新增

**本地离线翻译。** 语言包下载一次，此后**你的文字永远不会离开这台电脑**——
翻译过程中程序不产生任何网络请求。

- **本地神经机器翻译**，在你的 CPU 上推理（CTranslate2 + OPUS-MT）
- 索引里**共 100 个语言包**；中英双向各约 70MB
- **不会偷偷回退到云端。** 选定本地翻译后，模型出错就报错，
  文本*不会*被静默发给在线引擎——用户选本地翻译通常就是为了隐私，
  静默兜底等于把这份保障悄悄取消。
- **保持行结构** —— 每一行作为独立单元翻译，并在**一次**推理调用里批量处理，
  多行截图不会被压成一整段
- 在「设置 → 翻译引擎 → 管理离线语言包」里下载，
  或用命令行：`python tools\offline_pack.py --download zh-en en-zh`

**本次还包含**

- 语言包索引走多个镜像（优先 jsDelivr CDN）——`raw.githubusercontent.com` 在部分地区很不稳定
- `自检.bat` / `selftest.py` 增加「本地离线翻译」一节，含一条隐私断言
  （本地模式的候选链里不允许出现在线引擎）

### 📦 下载

| 文件 | 说明 |
| --- | --- |
| **`SnapTranslate-win64.zip`** | 免安装版，解压后双击 `SnapTranslate.exe`，**不需要装 Python** |
| `Source code (zip)` | 源码，需要先执行 `python tools\install_deps.py` 装依赖 |

> 首次运行如果被 SmartScreen 拦下，选「更多信息 → 仍要运行」即可（程序没有代码签名）。

### ✨ 主要功能

- **一步截图即翻译** —— 全局快捷键唤出全屏框选，松开鼠标立刻出结果
- **完全离线的文字识别** —— RapidOCR（PP-OCRv4 + onnxruntime 本地推理），中英混排效果最好，不限量
- **完全离线的翻译（可选）** —— 下载语言包后翻译全程零网络请求
- **零配置的在线翻译** —— 内置有道 / Yandex / MyMemory 三家免 Key 通道，一个失败自动换下一个
- **可选的 AI 大模型翻译** —— 兼容 OpenAI 协议（DeepSeek / Kimi / 通义 / 智谱 / 硅基流动）
- **高度可自定义的快捷键** —— 点一下输入框直接按新组合键即可录制；与 QQ / 微信的截图键冲突时自动降级到键盘钩子模式
- **贴心的框选交互** —— 放大镜、尺寸角标、方向键 1px 微调、选区可拖动可缩放、支持全选整屏
- **重译上次区域** —— 屏幕内容变了（翻页、滚动）不用重新框选
- **翻译剪贴板** —— 复制一段文字，快捷键直接翻译
- **结果窗** —— 可置顶、可拖动、双语对照、一键复制、语音朗读、换引擎自动重译
- **桌面快捷方式 / 开机自启** —— 一键创建，程序内可直接切换
- **单实例运行** —— 重复启动会把命令转发给已运行的实例

### 🖥️ 一次真实的识别结果

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

**要用离线翻译**：设置 → 翻译引擎 → 管理离线语言包 → 下载「中文 ⇄ 英语」，
再把「翻译引擎」选为 **本地离线翻译**。

### ✅ 发布前的实测结果

| 项目 | 结果 |
| --- | --- |
| 全局快捷键 | 用 `SendInput` 注入真实按键，`Ctrl+Alt+Z` / `Ctrl+Alt+X` 均正确触发 |
| 端到端链路 | 识别 → 翻译 → 显示 全通，在线引擎 0.2~1.4s 出结果 |
| 离线翻译速度 | 首次 401ms（含加载模型），之后 37~60ms/句；232 字长文 0.27s |
| 离线隐私 | `engine=local` 的候选链为 `['local']`，不存在任何在线兜底 |
| 离线双向 | 中→英、英→中均正确，且**行结构保持**（4 行输入 → 4 行输出） |
| 离线全链路 | 识别 → 本地翻译 → 显示，端到端 0.81s |
| 识别准确率 | `12345`、`狐狸跳`、`Ctrl+Alt+Z` 全部认对（Windows 自带 OCR 会错成 `1234S`、`狐犭里眺`、`CtrI+AIt`） |
| 高 DPI 坐标 | 2560×1600 物理 / 1280×800 逻辑（缩放 200%），框选 520×320 精确裁出 1040×640 |
| 单实例转发 | 二次启动 970ms 转发命令后退出 |
| 界面 | 结果窗、设置窗、语言包管理窗几何自检全部通过 |

### ⚠️ 已知限制

- **仅支持 Windows**（依赖 Win32 热键、GDI 抓屏、SAPI 朗读、WinRT OCR）
- 离线翻译质量低于在线引擎——它用的是能在 CPU 上跑的紧凑型 OPUS-MT 模型。
  在意隐私就选它，在意质量就选在线引擎或配置大模型 Key。
- 离线语言包以英语为中心：其它语种之间需要经英语中转，会损失一点质量。
- 免费在线翻译接口有频率限制
- RapidOCR 中文模型会吞掉英文词间空格（汉字与西文交界处已自动补齐）
- 多显示器**且各屏缩放比例不同**时，框选遮罩按主屏比例渲染，可能有轻微偏移
- 程序无代码签名

### 🔧 从源码运行

```bat
python tools\install_deps.py     :: 依赖装进项目内的 vendor\ 目录
python main.py                   :: 启动
python tools\offline_pack.py --download zh-en en-zh   :: 下载离线语言包
```

详细说明、常见问题与实现要点见仓库根目录的 **README.zh-CN.md**。

### 🙏 致谢

- [RapidOCR](https://github.com/RapidAI/RapidOCR) / [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) —— 离线文字识别
- [CTranslate2](https://github.com/OpenNMT/CTranslate2) / [OPUS-MT](https://github.com/Helsinki-NLP/Opus-MT) —— 离线翻译模型
- [Argos Translate](https://github.com/argosopentech/argos-translate) —— 语言包格式与索引
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) —— 图形界面
- [mss](https://github.com/BoboTiG/python-mss) —— 屏幕抓取
- [pynput](https://github.com/moses-palmer/pynput) —— 键盘钩子兜底

### 📄 License

[MIT](LICENSE)
