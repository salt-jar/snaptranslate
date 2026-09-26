# 截译 · SnapTranslate

> 按下快捷键 → 框选屏幕上任意文字 → 自动识别 → 翻译结果悬浮窗。

![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-4c8dff)
![python](https://img.shields.io/badge/python-3.10%2B-3776ab)
![license](https://img.shields.io/badge/license-MIT-4ec97a)

[English](README.md) | **简体中文**

一个常驻系统托盘的 Windows 截图翻译工具。**完全离线识别**（不需要联网就能把图上的字认出来），
翻译走多家免 Key 通道并带自动容错，装完即用，**不用注册任何账号、不需要 API Key**。

---

## 一、快速开始

### 方式 A：直接下载免安装版（推荐）

到 [Releases](../../releases/latest) 下载 `SnapTranslate-win64.zip`，解压后双击 `SnapTranslate.exe` 即可，
**不需要装 Python**。

> 想让以后每次打标签都自动构建 exe？把仓库里的 `ci/release.workflow.yml`
> 复制到 `.github/workflows/release.yml` 即可（可直接在 GitHub 网页上新建文件粘贴内容）。
> 之所以没有默认放在 `.github/workflows/`，是因为往那里推送文件需要 token 具备额外的
> `workflow` 权限，普通 `repo` 权限会被 GitHub 拒绝。

### 方式 B：从源码运行

```bat
python tools\install_deps.py     :: 依赖装进项目内的 vendor\ 目录
python main.py                   :: 启动
```

也可以直接双击 **`安装依赖.bat`** → **`启动.bat`**；
想要桌面图标再双击 **`创建桌面快捷方式.bat`**。

`tools/install_deps.py` 直接从 PyPI 下载 wheel 解包到 `vendor/`，
所以**不需要 pip**，也不会污染系统 Python。整个文件夹可以随便拷贝，绿色便携。

### 首次运行

程序会自动打开设置窗口。**设置好快捷键后就可以关掉它**，程序会继续在托盘里运行
（右下角出现蓝底白字的「译」图标）。

---

## 二、怎么用

### 默认快捷键

| 快捷键 | 作用 |
| --- | --- |
| `Ctrl + Alt + Z` | **截图翻译**（最常用） |
| `Ctrl + Alt + X` | 翻译剪贴板里的文字 |
| `Ctrl + Alt + C` | 重译上次框选的区域（屏幕内容变了时很好用） |

快捷键都可以在「设置 → 快捷键」里点一下输入框、直接按下新组合键来修改，即录即生效。

### 框选时的操作

| 操作 | 效果 |
| --- | --- |
| 拖动鼠标 | 框选要翻译的区域 |
| 松开鼠标 | 立即开始识别并翻译 |
| 按住选区拖动 | 移动选区 |
| 拖四角/四边的小方块 | 缩放选区 |
| 方向键 / `Shift`+方向键 | 每次微调 1px / 10px |
| `Ctrl + A` | 全选整个屏幕 |
| `Enter` | 确认当前选区 |
| 右键 / `Esc` | 取消 |

框选时右下角有**放大镜**，方便精确对齐小字。

### 结果窗口

- **复制译文** / **复制双语** —— 一键进剪贴板，按钮会变成「已复制 ✓」
- **🔊 朗读** —— 用系统语音念出来
- **重新识别** —— 屏幕内容变了，重抓上次区域
- **重新翻译** —— 换语言或换引擎后重翻
- 底部的引擎下拉框**换一个引擎会自动重译**
- 标题栏可拖动整个窗口，双击标题栏回到截图位置
- `Esc` 关闭，`Ctrl + C` 复制译文，`Ctrl + R` 重新翻译

---

## 三、翻译引擎

### 完全离线：文本不出本机（隐私优先）

| 引擎 | 语言覆盖 | 说明 |
| --- | --- | --- |
| **本地离线翻译** | 索引里 100 个语言包，其它语种经英语中转 | ✅ 用 OPUS-MT 模型在你的 CPU 上跑。**下载完语言包之后，全程不产生任何网络请求** |

在「设置 → 翻译引擎」里把引擎选成 **本地离线翻译**，再点「管理离线语言包…」下载对应语言包。
中英双向各约 70MB，下完之后翻译完全在本机完成。

> **这个模式永远不会回退到在线引擎。** 本地模型出错就报错，绝不会偷偷把文本发到服务器。
> 这是刻意设计的：用户选本地翻译通常就是为了隐私，静默兜底等于把这份保障悄悄取消了。

也可以用命令行批量下载：

```bat
python tools\offline_pack.py --available            :: 列出可下载的语言包
python tools\offline_pack.py --installed            :: 查看已安装
python tools\offline_pack.py --download zh-en en-zh :: 中英双向
```

或者直接双击 **`下载离线语言包.bat`**。

语言包索引走了多个镜像（优先 jsDelivr CDN），因为 `raw.githubusercontent.com`
在部分地区很不稳定。

### 免 Key，开箱即用（在线）

| 引擎 | 语言覆盖 | 实测 |
| --- | --- | --- |
| **有道翻译（免 Key）** | 中 ⇄ 英 | ✅ 质量最好，但请求过快会被短暂限流（程序内置节流 + 自动重试） |
| **Yandex 翻译（免 Key）** | 20+ 语种，长文本友好 | ✅ 稳定，支持中日韩法德俄西等 |
| **MyMemory（免 Key）** | 多语种 | ✅ 兜底用，单次上限 500 字符、质量一般 |
| Google 翻译（免 Key） | 多语种 | ⚠️ 国内需要代理，代码已实现但直连超时 |

默认的**「智能选择」**会在一个引擎失败时自动换下一个，所以正常情况下你不需要关心用哪个。

### 需要自己申请 Key（质量更高）

在「设置 → 翻译引擎」里填写即可，填完把「翻译引擎」切成对应项：

- **AI 大模型翻译（推荐）** —— 兼容 OpenAI 协议的服务都能填：
  `https://api.deepseek.com/v1`（DeepSeek）、`https://api.moonshot.cn/v1`（Kimi）、
  `https://dashscope.aliyuncs.com/compatible-mode/v1`（通义）、
  `https://open.bigmodel.cn/api/paas/v4`（智谱）、`https://api.siliconflow.cn/v1`（硅基流动）。
  大模型翻译能保留原文格式和专业术语，长文本效果明显更好。
- **百度翻译开放平台** / **有道智云** —— 填写 APPID、密钥。
- **自定义 HTTP 接口** —— 自建服务或其它 API，请求体支持 `{text}` `{from}` `{to}` 占位。

### 目标语言选「自动」

默认目标语言是**「自动」**，行为是：

- 原文是外文 → 译成中文；
- 原文本来就是中文 → 自动改译成英文（不会出现"译文和原文一模一样"的尴尬）。

状态栏会提示「原文已是中文，已自动译为英文」。

### 翻译质量上的几个处理

下面几件事都是实测发现具体问题之后加上的，不是"看起来应该做"：

| 处理 | 原来会出的问题 |
| --- | --- |
| **保持行结构** | 截图是多行的。文本一旦超过单次请求上限（有道 1400 字符），切分逻辑会把换行符一起吃掉，实测 **30 行被压成 1 行** |
| **中英混排按行处理** | 只把需要翻译的行送出去，已经是中文的行原样保留。原来整段丢给引擎，中文行被白翻一遍，还会触发"反向翻译"导致**目标选中文、输出却是英文** |
| **代码与术语保护** | `config.json` 被译成 `config。json`（句点变全角，路径直接失效）、`PP-OCRv4` 被拆成 `pp - ocv4`、`ONNX Runtime` 被译成 `ONNX运行时`。现在译前替换成占位符、译后原样换回 |
| **自定义术语表** | 在「设置 → 翻译引擎 → 术语表」里按 `源=译` 写，例如 `量化=quantization`；只写一个词表示保持原样 |

> 这些处理都有回归测试守着（`python tools\test_translation.py`，62 项断言），
> 改动翻译链路后跑一遍就知道有没有退化。

---

## 四、文字识别（OCR）

| 引擎 | 说明 |
| --- | --- |
| **RapidOCR 离线识别**（默认） | 本地运行、免费无限量，中英混排效果最好。首次识别约 3 秒（加载模型），之后通常 0.3～1 秒 |
| **Windows 自带 OCR** | 零额外依赖的兜底方案。精度一般（容易把 `l` 认成 `I`、`5` 认成 `S`），中文结果会自动去掉多余空格 |
| **Tesseract OCR** | 如果你系统里装过 Tesseract 就会自动出现在列表里 |

在「设置 → 文字识别」里可以调：

- **放大倍数**（默认 2 倍）—— 小字号截图识别不准时，调大它通常立刻见效；
- **灰度 + 对比度增强** —— 自动处理深色主题截图（浅字深底会先反色）；
- **置信度阈值** —— 调低能识别到更淡的字，但更容易出错。

---

## 五、常见问题

**Q：按快捷键没反应？**
多半是组合键被别的软件占了（QQ 的 `Ctrl+Alt+A`、微信的 `Ctrl+Shift+A` 等都很有名）。
程序会自动改用键盘钩子模式并弹出提示。到「设置 → 快捷键」换一个组合键即可，状态区会显示每个键是否生效。

**Q：识别结果里英文字母之间的空格丢了？**
这是 PaddleOCR 中文识别模型的固有特性（中文语料训练时不区分词间空格）。程序已在汉字与西文交界处自动补空格，
但纯英文单词之间无法还原。这种情况可以在设置里把识别引擎换成 **Windows 自带 OCR**，它对英文空格保留得更好。

**Q：翻译失败 / 提示限流？**
免费接口有频率限制。程序会自动换引擎，稍等几秒再试即可。要稳定使用建议配置一个大模型 Key。

**Q：程序没反应了/想彻底关掉？**
右键托盘图标 → 退出；或者命令行执行 `python main.py --quit`。

**Q：出错了去哪里看原因？**
看程序目录下的 `snaptranslate.log`，里面记录了每次识别、翻译的耗时和错误。

**Q：想重置所有设置？**
删掉 `config.json`，或点「设置 → 恢复默认」。

---

## 六、目录结构

```
snaptranslate/
├── 启动.bat / 调试启动.bat          启动（无控制台 / 带控制台）
├── 安装依赖.bat                     安装依赖到 vendor/
├── 创建桌面快捷方式.bat
├── 自检.bat                         环境体检
├── 下载离线语言包.bat                下载离线翻译语言包
├── 打包exe.bat                      打包成免安装 exe
├── main.py                          程序入口
├── shotranslate.spec                PyInstaller 打包配置
├── requirements.txt                 依赖清单（给习惯 pip 的人）
├── LICENSE                          MIT 许可证
├── RELEASE_NOTES.md                 GitHub Release 正文（中英双语）
├── README.md / README.zh-CN.md      英文 / 中文说明
├── .gitignore / .gitattributes      版本库忽略规则 / 行尾规范
├── ci/release.workflow.yml          自动打包发布的工作流模板（启用方法见「快速开始」）
├── config.json                      你的设置（首次运行自动生成，不进版本库）
├── snaptranslate.log                运行日志（排查问题看这里）
├── vendor/                          第三方依赖（由安装脚本生成，不进版本库）
├── models/offline/                  离线翻译语言包（程序内下载）
├── resources/icon.ico               程序图标
├── app/
│   ├── paths.py          路径、配置目录、开机自启
│   ├── config.py         配置读写与默认值
│   ├── langs.py          语言代码与各家引擎的映射
│   ├── theme.py          深色 / 浅色样式表
│   ├── screen.py         显示器枚举、DPI 换算、抓屏
│   ├── overlay.py        全屏框选遮罩（放大镜、把手、微调）
│   ├── hotkeys.py        全局快捷键（Win32 热键 + 键盘钩子兜底）
│   ├── ocr/              识别引擎：base / rapid / winocr / tesseract / preprocess
│   ├── translate/        翻译引擎：base / free / local / llm / official / custom
│   │                     + langdetect（按字符系统判语种）/ glossary（术语保护）
│   ├── offline.py        离线语言包索引、下载与安装
│   ├── offline_dialog.py 离线语言包管理界面
│   ├── pipeline.py       「识别 → 翻译」后台线程流水线
│   ├── result_window.py  结果悬浮窗
│   ├── settings_window.py 设置窗口
│   ├── tray.py           托盘图标与菜单
│   ├── shortcut.py       创建桌面快捷方式
│   ├── single_instance.py 单实例 + 命令行转发
│   ├── speech.py         语音朗读
│   ├── cache.py          LRU 缓存
│   └── app_context.py    总装
└── tools/
    ├── install_deps.py   无 pip 依赖安装器
    ├── make_shortcut.py  命令行创建快捷方式
    ├── build.py          打包脚本
    ├── make_icon.py      生成图标
    ├── offline_pack.py   离线语言包命令行工具
    ├── selftest.py       环境 / OCR / 翻译 / 离线自检
    ├── test_translation.py 翻译链路回归测试（62 项断言）
    ├── diagnose_translation.py 翻译质量诊断（按失效模式分组的用例）
    ├── gui_test.py       端到端冒烟测试
    ├── overlay_test.py   坐标换算与框选交互测试
    └── ui_check.py       界面几何自检
```

---

## 七、打包成免安装 exe

双击 **`打包exe.bat`**，产物在 `dist\SnapTranslate\`，整个文件夹拷到别的电脑就能用。

想同时把桌面快捷方式指向 exe：`python tools\build.py --shortcut`。

> 采用「一个文件夹」而不是单文件 exe：onnxruntime + OpenCV + PyQt5 体积较大，
> 单文件模式每次启动都要解压几百 MB，要等十几秒。

---

## 八、实现上的几个关键点

这几点都是实际调试中踩过的坑，记录一下便于后续维护：

1. **onnxruntime 必须在 Qt 之前导入。**
   实测（Windows + PyQt5 5.15 + onnxruntime 1.27）如果先创建了 `QApplication`，
   再 `import onnxruntime` 会抛
   `ImportError: DLL load failed while importing onnxruntime_pybind11_state: 动态链接库(DLL)初始化例程失败`。
   反过来先导入则完全正常。因此 `main.py` 里在创建应用之前先调用 `app.ocr.warmup()`。

2. **逻辑坐标与物理像素必须分开算。**
   Qt 的 `QScreen.geometry()` 是**逻辑**坐标（受系统缩放影响），
   `mss` 抓到的是**物理**像素。2560×1600 的屏幕在 Qt 眼里只有 1280×800。
   缩放比例由「物理宽 ÷ 逻辑宽」**实测得出**，不假设任何 DPI 参数，
   所以 125% / 150% / 200% 缩放都不会错位。

3. **选区矩形统一用「左闭右开」语义。**
   Qt 的 `QRect(p1, p2)` 是闭区间，从 (100,100) 拖到 (620,420) 会得到 521×321，
   比实际拖动多 1 像素。`overlay.py` 全程用 `宽 = x1 - x0`，`overlay_test.py` 会验证这一点。

4. **依赖安装不依赖 pip。**
   部分 Windows 环境下 `venv` 的 `ensurepip` 是坏的，而且某些沙箱会禁止
   `tempfile.mkdtemp()` 创建的目录被写入——pip 正好依赖它。
   因此写了 `tools/install_deps.py`：直接从 PyPI 下载 wheel 并用 zipfile 解包，
   还额外校验了 free-threaded 构建（`cp313t`）这种 ABI 陷阱。

5. **单实例用文件队列而不是命名管道。**
   `QLocalServer` 在受限环境里会返回「拒绝访问」，一旦失败就能无限多开。
   改成 `.ipc/instance.lock`（记录 PID）+ `.ipc/queue/*.cmd`（命令队列）后，
   不依赖 Qt、不受管道权限限制，而且可以在创建 `QApplication` **之前**就判断出
   「已有实例」，避免白启动一个完整的 GUI 进程。转发延迟约 400ms。

6. **PyInstaller 需要把 `vendor/` 加进 `pathex`，并显式收集 OCR 模型。**
   少了这两条，`collect_data_files('rapidocr_onnxruntime')` 会**静默失败**
   （只打一行 `WARNING: ... is not a package`），15.4MB 的 ONNX 模型全都不进包。
   结果是：exe 能正常启动、托盘图标正常、日志正常，一按快捷键却提示「没有可用的 OCR 引擎」。

7. **sentencepiece 与 CTranslate2 打不开含中文的路径。**
   它们的 C++ 文件 API 用的是窄字符，模型放在含中文的目录下会直接报
   `NOT_FOUND: "D:\...\翻译软件\models\...\sentencepiece.model": No such file or directory`
   ——文件明明存在，Python 也读得到，但 C++ 层打不开。
   规避办法：路径不是纯 ASCII 时，临时 `os.chdir()` 到模型目录、只用相对文件名
   （`model`、`sentencepiece.model`）加载。两个库都是在构造时把模型读进内存，
   所以切换工作目录的窗口很短；但 `os.chdir` 是进程级的，必须加锁。

8. **离线翻译不用 argostranslate。**
   argostranslate 除了要拉 spacy / stanza / minisbd 一大串依赖（约 150MB），
   运行期还会联网下载句子切分模型——对「本地安全翻译」来说不可接受。
   语言包本身就是「CTranslate2 模型目录 + sentencepiece 分词器」的 zip，
   直接依赖 `ctranslate2` + `sentencepiece`（44MB）自己实现即可，
   而且下载完语言包后**全程零网络请求**。

9. **术语保护用的占位符格式是实测选出来的，`[[n]]` 不行。**
   有道在占位符**独立成行**时会原样放行，一旦**嵌在句子里**就会把它包成
   `[b[n]]`（b 是它的加粗标记）；离线引擎则会把 `[[0]]` 截断成 `[[0]`。
   行为还不稳定——同一句话两次结果可能不同。
   在出问题的那句话上反复测，`{n}` 是唯一稳定存活的写法。
   即便如此仍做了三层兜底：兼容已知变形 → 只替换确实存在的槽位
   （避免误伤译文里原有的括号数字）→ 清掉被拆碎的残骸。

10. **换行符与句号是两回事。**
    旧的分段正则 `(?<=[。！？!?…；;\.])\s*` 里的 `\s*` 会把句号**后面**的换行
    一并吃掉，长文本重新拼接后行结构全丢。改成只在行边界切分、
    调用方用 `"\n".join()` 拼回即可。
    另外花括号保护规则必须排在自动保护规则的**第一位**——
    占位符本身就是 `{n}` 的形状，排在后面会把自己刚生成的占位符再遮一遍。

---

## 九、自检与测试

```bat
自检.bat                                   :: 完整自检（依赖 / OCR / 翻译）
python tools\selftest.py --ocr             :: 只测识别
python tools\selftest.py --translate       :: 只测翻译
python tools\overlay_test.py               :: 坐标换算与框选交互
python tools\ui_check.py                   :: 界面几何自检（可加 --shot-dir 导出截图）
python tools\gui_test.py                   :: 端到端：识别→翻译→显示
```

---

## 十、版本管理与回退

项目已初始化为 Git 仓库，发布版本都打了标签，随时可以回退。

```bat
git log --oneline --decorate          :: 看提交历史与标签
git tag                                :: 列出所有版本标签
git status                             :: 看当前改动（config.json 等运行产物已被忽略）

:: —— 回退的三种方式 ——

:: 1) 只想看看旧版本长什么样（不改动当前文件）
git checkout v1.0.0

:: 2) 回到旧版本之后继续开发（会新建一个提交，历史保留，最安全）
git revert <commit>

:: 3) 彻底丢弃当前所有改动，硬回退到某个版本（危险，未提交的改动会丢失）
git fetch --all
git reset --hard v1.0.0
```

改了代码但还没提交、想反悔：

```bat
git restore .                          :: 丢弃所有未提交的修改
git restore app/overlay.py             :: 只丢弃某个文件
git clean -fd                          :: 删掉新增的未跟踪文件（小心）
```

发布新版本：

```bat
git add -A
git commit -m "feat: 支持自定义目标语言"
git tag -a v1.1.0 -m "v1.1.0"
git push origin main --tags            :: 推送后 CI（若已启用）会自动构建并发布 Release
```

> **哪些文件不进版本库**：`vendor\`（100MB+ 依赖）、`config.json`、`snaptranslate.log`、
> `.ipc\`、`.cache\`、`dist\`、`build\`、`__pycache__\` —— 规则见 `.gitignore`。
> 其中 `vendor\` 换台电脑后运行 `安装依赖.bat` 就能重建。

---

## 十一、已知限制

- 仅支持 Windows（依赖 Win32 热键、GDI 抓屏、SAPI 朗读、WinRT OCR）。
- 离线翻译的质量低于在线引擎——它用的是能在 CPU 上跑的紧凑型 OPUS-MT 模型。
  在意隐私就选它，在意质量就选在线引擎或配置大模型 Key。
- 离线语言包以英语为中心：其它语种之间需要经英语中转，会损失一点质量。
- 多显示器**且各屏缩放比例不同**时，框选遮罩按主屏比例渲染，可能有轻微偏移；单屏或统一缩放不受影响。
- 免费翻译接口有频率限制，量大时建议配置大模型 Key。
- RapidOCR 中文模型会吞掉英文词间空格（见常见问题）。
- 程序没有代码签名，首次运行如果被 SmartScreen 拦下，选「更多信息 → 仍要运行」即可。
