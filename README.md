# SnapTranslate · 截译

> Press a hotkey → drag over any text on screen → offline OCR → floating translation window.

![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-4c8dff)
![python](https://img.shields.io/badge/python-3.10%2B-3776ab)
![license](https://img.shields.io/badge/license-MIT-4ec97a)

**English** | [简体中文](README.zh-CN.md)

A Windows screenshot translation tool that lives in the system tray.
Text recognition runs **fully offline** — no network needed to read the characters on screen —
while translation goes through several key-free providers with automatic failover.
Install it and it just works; **no account or API key required**.

---

## 1. Quick Start

### Option A — Download the prebuilt build (recommended)

Grab `SnapTranslate-win64.zip` from [Releases](../../releases/latest), extract it, and
double-click `SnapTranslate.exe`. No Python needed.

> Want every future tag to build automatically? Copy `ci/release.workflow.yml` in this
> repository to `.github/workflows/release.yml` (you can do it right on the GitHub web UI by
> creating the file and pasting the content). It is not placed under `.github/workflows/`
> by default because pushing files there requires the extra `workflow` OAuth scope, and
> GitHub rejects a plain `repo`-scoped token.

### Option B — Run from source

```bat
python tools\install_deps.py     :: installs deps into the local vendor\ directory
python main.py                   :: start
```

Or just double-click `安装依赖.bat` (**Install dependencies**), then `启动.bat` (**Launch**).
Optional: `创建桌面快捷方式.bat` (**Create desktop shortcut**) to get a desktop icon.

`tools/install_deps.py` downloads wheels straight from PyPI and unpacks them into `vendor/`,
so **pip is not required** and your system Python stays untouched. The whole folder is
portable — copy it anywhere.

### First run

The settings window opens automatically. Set your hotkeys, close it, and the app keeps
running in the tray (look for the blue **译** icon in the notification area).

---

## 2. Usage

### Default hotkeys

| Hotkey | Action |
| --- | --- |
| `Ctrl + Alt + Z` | **Screenshot & translate** (the main one) |
| `Ctrl + Alt + X` | Translate the clipboard |
| `Ctrl + Alt + C` | Re-translate the last selected region (handy after scrolling) |

All of them can be changed in **Settings → Hotkeys**: click the field and press a new
combination. It is recorded instantly.

### While selecting a region

| Input | Effect |
| --- | --- |
| Drag the mouse | Select the region to translate |
| Release the mouse | Start OCR + translation immediately |
| Drag inside the selection | Move it |
| Drag a corner / edge handle | Resize it |
| Arrow keys / `Shift` + arrow keys | Nudge by 1 px / 10 px |
| `Ctrl + A` | Select the whole screen |
| `Enter` | Confirm the current selection |
| Right-click / `Esc` | Cancel |

A **magnifier** follows the cursor, which makes it easy to line up on very small text.

### Result window

- **Copy translation** / **Copy both** — one click to the clipboard (the button flashes “copied”)
- **🔊 Speak** — read it aloud with the system voice
- **Re-run OCR** — re-capture the last region if the screen changed
- **Translate again** — after changing language or engine
- Changing the engine dropdown at the bottom **re-translates automatically**
- Drag the title bar to move the window; double-click it to snap back next to the capture
- `Esc` closes, `Ctrl + C` copies the translation, `Ctrl + R` re-translates

---

## 3. Translation engines

### No API key needed — works out of the box

| Engine | Coverage | Status |
| --- | --- | --- |
| **Youdao (key-free)** | Chinese ⇄ English | ✅ Best quality for that pair; rate-limited if you hammer it (built-in throttling + retry) |
| **Yandex (key-free)** | 20+ languages, long text | ✅ Stable — CN/EN/JP/KR/FR/DE/RU/ES and more |
| **MyMemory (key-free)** | Many languages | ✅ Last-resort fallback; 500-character limit per request, mediocre quality |
| Google (key-free) | Many languages | ⚠️ Needs a proxy in mainland China; implemented, but direct connections time out |

The default **“Smart”** mode automatically falls back to the next engine if one fails,
so normally you never have to care which one is being used.

### Bring your own key (higher quality)

Fill these in under **Settings → Translation engines**, then select the matching entry:

- **AI LLM translation (recommended)** — any OpenAI-compatible endpoint:
  `https://api.deepseek.com/v1` (DeepSeek), `https://api.moonshot.cn/v1` (Kimi),
  `https://dashscope.aliyuncs.com/compatible-mode/v1` (Qwen),
  `https://open.bigmodel.cn/api/paas/v4` (Zhipu GLM),
  `https://api.siliconflow.cn/v1` (SiliconFlow).
  LLM translation preserves formatting and terminology far better on long text.
- **Baidu Translate Open Platform** / **Youdao Zhiyun** — enter APPID and key.
- **Custom HTTP endpoint** — your own service or any API; the request body supports
  `{text}` `{from}` `{to}` placeholders.

### The “Auto” target language

The default target is **Auto**, which behaves like this:

- Foreign text → translated into Chinese;
- Text that is *already* Chinese → automatically translated into English instead
  (no more embarrassing “translation identical to source”).

The status bar tells you when this happened: *“source was already Chinese, auto-translated to English”*.

---

## 4. OCR engines

| Engine | Notes |
| --- | --- |
| **RapidOCR, offline** (default) | Runs locally, free and unlimited, best on mixed Chinese/English. First run takes ~3 s (loading models), then 0.3–1 s per capture |
| **Windows built-in OCR** | Zero extra dependencies. Lower accuracy (confuses `l`/`I` and `5`/`S`); Chinese output gets de-spaced automatically |
| **Tesseract OCR** | Appears automatically if Tesseract is installed on your system |

Tunable under **Settings → Text recognition**:

- **Upscale factor** (default 2×) — raising it is usually the quickest fix for small text;
- **Grayscale + contrast enhancement** — handles dark-theme screenshots automatically
  (light-on-dark gets inverted first);
- **Confidence threshold** — lower it to catch fainter text at the cost of more mistakes.

---

## 5. FAQ

**The hotkey does nothing?**
Most likely the combination is taken by another app (QQ uses `Ctrl+Alt+A`, WeChat uses
`Ctrl+Shift+A`). SnapTranslate automatically falls back to a low-level keyboard hook and
notifies you. Pick a different combination in **Settings → Hotkeys**; the status area shows
whether each binding actually took effect.

**Spaces between English words are missing from the OCR result?**
That is an inherent trait of the PaddleOCR Chinese recognition model (its training data does
not distinguish inter-word spaces). SnapTranslate inserts spaces at CJK/Latin boundaries
automatically, but spaces *between* Latin words cannot be recovered. Switch the OCR engine to
**Windows built-in OCR** in settings — it preserves English spacing much better.

**Translation fails or says it is rate-limited?**
The free endpoints have request limits. The app rotates to another engine automatically;
retry in a few seconds. For reliable heavy use, configure an LLM API key.

**The app seems stuck / how do I quit it properly?**
Right-click the tray icon → Quit, or run `python main.py --quit`.

**Something went wrong — where is the error?**
See `snaptranslate.log` next to the executable. It records the timing and errors of every
OCR and translation call.

**How do I reset everything?**
Delete `config.json`, or use **Settings → Restore defaults**.

---

## 6. Project layout

```
snaptranslate/
├── 启动.bat / 调试启动.bat          Launch (no console / with console)
├── 安装依赖.bat                     Install deps into vendor/
├── 创建桌面快捷方式.bat              Create desktop shortcut
├── 自检.bat                         Environment self-test
├── 打包exe.bat                      Build a standalone exe
├── main.py                          Entry point
├── shotranslate.spec                PyInstaller build spec
├── requirements.txt                 Dependency list (for pip users)
├── LICENSE                          MIT
├── RELEASE_NOTES.md                 GitHub Release body (bilingual)
├── README.zh-CN.md                  简体中文说明
├── .gitignore / .gitattributes      Ignore rules / line-ending policy
├── ci/release.workflow.yml          CI workflow template (see Quick Start)
├── config.json                      Your settings (generated on first run, not committed)
├── snaptranslate.log                Runtime log
├── vendor/                          Third-party deps (generated, not committed)
├── resources/icon.ico               App icon
├── app/
│   ├── paths.py          Paths, config dir, autostart
│   ├── config.py         Config load/save + defaults
│   ├── langs.py          Language codes and per-engine mappings
│   ├── theme.py          Dark / light stylesheets
│   ├── screen.py         Monitor enumeration, DPI mapping, screen capture
│   ├── overlay.py        Fullscreen selection overlay (magnifier, handles, nudging)
│   ├── hotkeys.py        Global hotkeys (Win32 RegisterHotKey + hook fallback)
│   ├── ocr/              Engines: base / rapid / winocr / tesseract / preprocess
│   ├── translate/        Engines: base / free / llm / official / custom
│   ├── pipeline.py       Background “OCR → translate” pipeline
│   ├── result_window.py  Floating result window
│   ├── settings_window.py Settings dialog
│   ├── tray.py           Tray icon and menu
│   ├── shortcut.py       Desktop shortcut creation
│   ├── single_instance.py Single instance + command forwarding
│   ├── speech.py         Text-to-speech
│   ├── cache.py          LRU cache
│   └── app_context.py    Wiring
└── tools/
    ├── install_deps.py   pip-free dependency installer
    ├── make_shortcut.py  CLI shortcut creation
    ├── build.py          Build script
    ├── make_icon.py      Icon generator
    ├── selftest.py       Env / OCR / translation self-test
    ├── gui_test.py       End-to-end smoke test
    ├── overlay_test.py   Coordinate mapping and selection tests
    └── ui_check.py       UI geometry self-check
```

---

## 7. Building a standalone exe

Double-click `打包exe.bat`, or run `python tools/build.py`. Output lands in
`dist\SnapTranslate\` — copy that whole folder to another machine and it runs as-is.

To also point the desktop shortcut at the built exe: `python tools\build.py --shortcut`.

> It produces a **folder**, not a single-file exe: onnxruntime + OpenCV + PyQt5 are large,
> and single-file mode would unpack hundreds of MB to a temp directory on every launch,
> adding ~10 s of startup time.

---

## 8. Implementation notes

These are all real problems hit while building this, recorded so they don't get re-broken:

1. **onnxruntime must be imported before Qt.**
   On Windows + PyQt5 5.15 + onnxruntime 1.27, creating `QApplication` first and then doing
   `import onnxruntime` raises
   `ImportError: DLL load failed while importing onnxruntime_pybind11_state: The DLL
   initialization routine failed`. Importing it first works perfectly. `main.py` therefore
   calls `app.ocr.warmup()` before creating the application.

2. **Logical coordinates and physical pixels must be tracked separately.**
   Qt's `QScreen.geometry()` is in **logical** units (affected by display scaling), while
   `mss` captures **physical** pixels. A 2560×1600 display looks like 1280×800 to Qt.
   The scale factor is **measured** as `physical width ÷ logical width` rather than assumed
   from any DPI API, so 125% / 150% / 200% all map correctly.

3. **Selection rectangles use half-open semantics.**
   Qt's `QRect(p1, p2)` is inclusive, so dragging from (100,100) to (620,420) yields
   521×321 — one pixel wider than the actual drag. `overlay.py` consistently uses
   `width = x1 - x0`, and `overlay_test.py` asserts it.

4. **Dependency installation does not rely on pip.**
   On some Windows setups `venv`'s `ensurepip` is broken, and certain sandboxes forbid
   writing into directories created by `tempfile.mkdtemp()` — which is exactly what pip
   uses. Hence `tools/install_deps.py`: download wheels from PyPI and unpack them with
   `zipfile`. It also guards against ABI traps such as free-threaded builds (`cp313t`).

5. **Single-instance uses a file queue, not a named pipe.**
   `QLocalServer` returns “access denied” in restricted environments, and once it fails the
   app can be launched unlimited times. Switching to `.ipc/instance.lock` (PID) plus
   `.ipc/queue/*.cmd` (command queue) removes the Qt dependency and the pipe permission
   problem — and lets the check happen **before** `QApplication` is created, so a second
   launch no longer spins up a whole GUI process. Forwarding latency is ~400 ms.

6. **PyInstaller needs `vendor/` on `pathex` and the OCR models listed explicitly.**
   Without them `collect_data_files('rapidocr_onnxruntime')` fails silently (a single
   `WARNING: ... is not a package`) and the 15.4 MB of ONNX models never make it into the
   bundle. The resulting exe starts fine, shows its tray icon, logs normally — and then says
   “no OCR engine available” the moment you press the hotkey.

---

## 9. Self-test

```bat
自检.bat                                   :: full check (deps / OCR / translation)
python tools\selftest.py --ocr             :: OCR only
python tools\selftest.py --translate       :: translation only
python tools\overlay_test.py               :: coordinate mapping and selection interaction
python tools\ui_check.py                   :: UI geometry (add --shot-dir to export screenshots)
python tools\gui_test.py                   :: end-to-end: OCR → translate → display
```

---

## 10. Version control & rollback

The project is a Git repository and every release is tagged, so rolling back is one command.

```bat
git log --oneline --decorate          :: history and tags
git tag                                :: list all version tags
git status                             :: current changes (config.json etc. are ignored)

:: --- three ways to go back ---

:: 1) just look at an old version (leaves your files alone)
git checkout v1.0.0

:: 2) undo an old change but keep history (safest)
git revert <commit>

:: 3) throw away everything and hard-reset to a tag (destructive)
git fetch --all
git reset --hard v1.0.0
```

Changed files but haven't committed yet:

```bat
git restore .                          :: discard all unstaged changes
git restore app/overlay.py             :: discard changes to one file
git clean -fd                          :: delete new untracked files (careful)
```

Releasing a new version:

```bat
git add -A
git commit -m "feat: custom target language"
git tag -a v1.1.0 -m "v1.1.0"
git push origin main --tags            :: tag push triggers the CI build & release
```

> **Not committed:** `vendor\` (100 MB+ of dependencies), `config.json`,
> `snaptranslate.log`, `.ipc\`, `.cache\`, `dist\`, `build\`, `__pycache__\` — see
> `.gitignore`. `vendor\` is rebuilt by `安装依赖.bat` on any machine.

---

## 11. Known limitations

- **Windows only** (uses Win32 hotkeys, GDI screen capture, SAPI speech, WinRT OCR).
- With multiple monitors **at different scaling factors**, the selection overlay renders at
  the primary monitor's ratio and may be slightly offset. Single monitor or uniform scaling
  is unaffected.
- Free translation endpoints are rate-limited; configure an LLM key for heavy use.
- The RapidOCR Chinese model drops spaces between English words (see FAQ).
- The binaries are not code-signed. If SmartScreen blocks the first run, choose
  “More info → Run anyway”.
