# Contributing to SnapTranslate / 参与贡献

Thanks for taking the time to improve SnapTranslate! Bug reports, translation-quality
observations, UI fixes, docs, and language additions are all welcome.
This guide is intentionally short; when in doubt, open an issue first.

感谢你愿意改进截译！Bug、翻译质量反馈、界面修复、文档和语言补充都欢迎。
这份指南尽量简短；拿不准时先开 Issue 讨论。

## Before you start / 开始之前

- For a small fix (typo, one-line bug, docs), just open a pull request.
- For a new feature, a refactor, or a dependency change, **open an issue first** so we can
  agree on scope. In particular, the project deliberately avoids heavyweight dependencies.
- Do not report security vulnerabilities in a public issue — see
  [SECURITY.md](.github/SECURITY.md).
- By participating you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

- 小修小补（错别字、单行 Bug、文档）可以直接提 PR。
- 新功能、重构或依赖变更请**先开 Issue** 对齐范围。项目会刻意控制依赖体积。
- 安全漏洞不要发公开 Issue，请按[安全政策](.github/SECURITY.md)处理。
- 参与本项目即表示同意遵守[行为准则](CODE_OF_CONDUCT.md)。

## Development setup / 开发环境

Requirements: **Windows 10/11**, Python **3.10+**. The app is PyQt5-based.

```bat
git clone https://github.com/salt-jar/snaptranslate.git
cd snaptranslate
python tools\install_deps.py      :: dependencies go into vendor\; no pip mutation
python main.py                    :: start from source
```

- `vendor/` is generated and **must not** be committed.
- `config.json`, `.ipc/`, `.cache/`, `models/`, `dist/`, and `build/` are runtime artifacts
  and are ignored by Git.
- For a headless UI check on CI-like machines:
  `set QT_QPA_PLATFORM=offscreen` and `set QT_QPA_FONTDIR=C:\Windows\Fonts`.

需要 **Windows 10/11** 与 **Python 3.10+**，界面基于 PyQt5。

```bat
python tools\install_deps.py      :: 依赖装进 vendor\，不改系统 Python
python main.py                    :: 从源码启动
```

- `vendor/` 是生成目录，**不要提交**。
- `config.json`、`.ipc/`、`.cache/`、`models/`、`dist/`、`build/` 都是运行时产物，已在
  `.gitignore` 中忽略。
- 无头环境跑界面自检时，可设置 `QT_QPA_PLATFORM=offscreen` 和
  `QT_QPA_FONTDIR=C:\Windows\Fonts`。

## Tests / 测试

Run the relevant checks before opening a PR:

```bat
python -m compileall -q app main.py tools
python tools\test_translation.py --no-net     :: chunking / glossary / language detection
python tools\test_languages.py                :: language registry and multi-target paths
python tools\ui_check.py --shot-dir .tmp\ui   :: geometry of every tab and window
python tools\overlay_test.py                  :: selection coordinates
python tools\gui_test.py                      :: end-to-end OCR → translate → display
```

Network-dependent tests are optional; note in the PR if you skipped them.
When touching OCR or the packaged build, also run:

```bat
python tools\build.py --clean
```

Then launch `dist\SnapTranslate\SnapTranslate.exe` and smoke-test OCR, translation, and the
settings window. (Maintainers use an additional local freeze-verification script that is not
part of the repository.)

提交 PR 前请跑相关检查。联网用例可选，跳过时请在 PR 里说明。
改到 OCR 或打包流程时，再跑打包，并启动打包版对 OCR、翻译和设置窗做冒烟测试。

## Code conventions / 代码约定

- Keep the import order in `main.py` intact: **native extensions (onnxruntime,
  sentencepiece, ctranslate2) before Qt**. Importing them after `QApplication` crashes on
  Windows.
- The local offline engine must never silently fall back to an online provider. Privacy is
  a product requirement, not an optimisation.
- Keep UI components consistent with the iOS-style theme in `app/theme.py` and
  `app/widgets.py`. If you add a custom-painted control, expose its colours through
  `ios_palette` rather than hard-coding them.
- No new heavy dependencies without an issue. The portable build is already ~414 MB.
- No secrets, API keys, personal paths, or captured private screenshots in commits.
- Comments and user-facing strings are in Chinese or bilingual; code identifiers are English.
- Use LF line endings; the repository has a `.gitattributes` policy.

- 保持 `main.py` 的导入顺序：**原生扩展先于 Qt**，否则 Windows 上会直接崩溃。
- 本地离线翻译**绝不**静默回退到在线引擎，隐私是产品约束。
- UI 遵循 `app/theme.py` / `app/widgets.py` 的 iOS 风格；自绘控件从 `ios_palette` 取色，
  不要硬编码颜色。
- 不引入体积大的新依赖，除非先在 Issue 里说明并达成一致。
- 不提交密钥、个人路径或包含隐私的截图。
- 注释和用户可见文案用中文或中英双语；代码标识符用英文。
- 使用 LF 换行，仓库已有 `.gitattributes` 规则。

## Pull requests / 拉取请求

1. Branch from `main`: `git checkout -b fix/short-description`.
2. Keep one logical change per PR. Rebase on `main` rather than merging if possible.
3. Fill in the pull request template, including test commands and results.
4. For UI changes, attach **light and dark** screenshots and mention any resize behaviour.
5. For translation changes, add a regression case to `tools/test_translation.py` or
   `tools/test_languages.py`.
6. Link the related issue (`Fixes #123`).

1. 从 `main` 拉分支，例如 `fix/short-description`。
2. 一个 PR 只做一件逻辑上的事；尽量 rebase，不要制造无意义的 merge。
3. 填好 PR 模板，写清测试命令和结果。
4. UI 改动请附**浅色和深色**截图，并说明尺寸/缩放行为。
5. 翻译逻辑改动请在 `tools/test_translation.py` 或 `tools/test_languages.py` 补回归用例。
6. 关联对应 Issue，例如 `Fixes #123`。

## Commit messages / 提交信息

Use a short imperative subject, optionally with a conventional prefix:
`fix(ui): keep footer visible on small screens`, `feat(translate): add X`, `docs: ...`.
Explain *why* in the body when the change is not obvious.

使用简短的祈使句标题，可带 conventional 前缀，例如
`fix(ui): 小屏下保持底部按钮可见`。原因不显然时请在正文说明。

## Licensing / 许可

By contributing, you agree that your contribution is licensed under the project's
[MIT License](LICENSE). Please only submit work you have the right to license.

参与贡献即表示你的贡献按项目的 [MIT 许可证](LICENSE) 授权。
请只提交你有权授权的内容。
