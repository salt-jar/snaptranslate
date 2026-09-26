# 截译 SnapTranslate v1.0.0

> 按下快捷键 → 框选屏幕上任意文字 → 自动识别 → 悬浮窗显示翻译结果。

一个常驻系统托盘的 **Windows 截图翻译工具**。文字识别**完全离线**（不联网也能把图上的字认出来），
翻译走多家免 Key 通道并带自动容错。**装完即用，不需要注册任何账号。**

---

## 📦 下载

| 文件 | 说明 |
| --- | --- |
| `SnapTranslate-win64.zip` | 免安装版，解压后双击 `SnapTranslate.exe` 即可运行 |
| `Source code (zip)` | 源码，需要自己 `python tools/install_deps.py` 装依赖 |

> 首次运行如果被 SmartScreen 拦下，选「更多信息 → 仍要运行」即可（程序没有代码签名）。

---

## ✨ 主要功能

- **截图即翻译** —— 全局快捷键唤出全屏框选，松开鼠标立刻出结果
- **完全离线的文字识别** —— RapidOCR（PP-OCRv4 + onnxruntime 本地推理），中英混排效果最好，不限量
- **零配置的翻译** —— 内置有道/Yandex/MyMemory 三家免 Key 通道，一个失败自动换下一个
- **可选的 AI 大模型翻译** —— 兼容 OpenAI 协议（DeepSeek / Kimi / 通义 / 智谱 / 硅基流动），填写 Key 后质量明显更好
- **高度可自定义的快捷键** —— 点一下输入框直接按新组合键即可录制；与 QQ / 微信的截图键冲突时自动降级到键盘钩子模式
- **贴心的交互细节** —— 框选时带放大镜和尺寸角标；方向键 1px 微调；选区可拖动、可缩放；支持全选整屏
- **重译上次区域** —— 屏幕内容变了（翻页、滚动）不用重新框选
- **翻译剪贴板** —— 复制一段文字，快捷键直接翻译
- **结果窗** —— 可置顶、可拖动、双语对照、一键复制、语音朗读、换引擎自动重译
- **桌面快捷方式 / 开机自启** —— 一键创建，程序内可直接切换
- **单实例运行** —— 重复启动会把命令转发给已运行的实例（再按快捷键直接截图）

---

## 🖥️ 效果

一次真实的识别结果（含中英混排、深色主题、彩色文字）：

```
原文                                      译文
截图翻译测试 ScreenshotTranslationTest  →  Screenshots ScreenshotTranslationTest translation test
第二行：小字号中文识别，包含数字 12345   →  Second line: Small-sized Chinese character recognition,
与符号 #@！。                              including the numbers 12345 and the symbol #@! .
快捷键 Ctrl+Alt+Z 触发截图翻译。        →  The shortcut key Ctrl+Alt+Z triggers the screenshot translation.
```

---

## 🚀 快速上手

1. 解压 `SnapTranslate-win64.zip`
2. 双击 `SnapTranslate.exe`（首次会打开设置窗口）
3. 按 **`Ctrl + Alt + Z`** 框选屏幕上要翻译的文字

| 默认快捷键 | 作用 |
| --- | --- |
| `Ctrl + Alt + Z` | 截图翻译 |
| `Ctrl + Alt + X` | 翻译剪贴板 |
| `Ctrl + Alt + C` | 重译上次区域 |

---

## ✅ 发布前的实测结果

| 项目 | 结果 |
| --- | --- |
| 全局快捷键 | 用 `SendInput` 模拟真实按键，`Ctrl+Alt+Z` / `Ctrl+Alt+X` 均正确触发 |
| 端到端链路 | 识别 → 翻译 → 显示 全通，免 Key 引擎 0.2~1.4s 出结果 |
| 识别准确率 | `12345`、`狐狸跳`、`Ctrl+Alt+Z` 全部认对（Windows 自带 OCR 会错成 `1234S`、`狐犭里眺`、`CtrI+AIt`） |
| 高 DPI 坐标 | 2560×1600 物理 / 1280×800 逻辑（缩放 200%），框选 520×320 精确裁出 1040×640 |
| 单实例转发 | 二次启动 970ms 转发命令后退出，主实例 0.4s 内响应 |
| 界面自检 | 结果窗 24 个控件、设置窗 5 个标签页，几何检查全部通过 |

---

## ⚠️ 已知限制

- **仅支持 Windows**（依赖 Win32 热键、GDI 抓屏、SAPI 朗读、WinRT OCR）
- 免费翻译接口有频率限制，量大时建议在设置里配置大模型 Key
- RapidOCR 中文模型会吞掉英文词间空格（已在汉字与西文交界处自动补齐，纯英文词间无法还原；可切换 Windows 自带 OCR）
- 多显示器**且各屏缩放比例不同**时，框选遮罩按主屏比例渲染，可能有轻微偏移
- Google 翻译在国内需要代理才能使用
- 程序无代码签名

---

## 🔧 从源码运行

```bat
python tools\install_deps.py     :: 依赖装进项目内的 vendor\（不污染系统环境）
python main.py                   :: 启动
```

详细说明、常见问题与实现要点见仓库根目录的 **README.md**。

---

## 🙏 致谢

- [RapidOCR](https://github.com/RapidAI/RapidOCR) / [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) —— 离线文字识别
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) —— 图形界面
- [mss](https://github.com/BoboTiG/python-mss) —— 屏幕抓取
- [pynput](https://github.com/moses-palmer/pynput) —— 键盘钩子

## 📄 License

[MIT](LICENSE)
