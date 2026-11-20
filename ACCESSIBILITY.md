# Accessibility Statement / 无障碍声明

SnapTranslate is a small Windows desktop utility maintained by a single developer.
Accessibility is an ongoing effort, not a certification. This statement describes what
currently works, what is known to be incomplete, and how to report a barrier.

截译是一个由个人维护的 Windows 桌面小工具。无障碍是一个持续改进的目标，不是认证。
本文说明目前可用的能力、已知不足，以及如何反馈障碍。

## Current support / 当前支持

### Display and layout / 显示与布局

- **High DPI**: the UI uses Qt's high-DPI scaling and is usable at 100%–200%+ scaling.
- **Resizable windows**: the settings window, offline-pack manager, and result window have
  drag handles in the bottom-right corner. Window sizes are remembered.
- **Scrollable settings**: every settings page scrolls, so content remains reachable in a
  small window or at large font sizes.
- **Font size**: Settings → Appearance adjusts the base UI text size from 9 to 22 px.
- **Light and dark themes**: Settings → Appearance. The result window follows the theme.
- **Minimum sizes**: the settings window is 700×560 logical px; the result window is
  600–1000 px wide. The result window height follows its content and never pushes the action
  bar off-screen.

- **高 DPI**：使用 Qt 高 DPI 缩放，100%–200%+ 缩放下可用。
- **窗口可缩放**：设置窗、离线语言包窗、结果窗右下角都有拖拽手柄，尺寸会被记住。
- **设置页可滚动**：所有设置页都有滚动条，小窗口或大字号下仍能访问到底部按钮。
- **字号可调**：设置 → 外观，基础字号 9–22 px。
- **浅色 / 深色主题**：设置 → 外观；结果窗跟随主题。
- **最小尺寸**：设置窗 700×560 逻辑像素；结果窗宽度 600–1000 像素，高度随内容自适应，
  底部按钮不会被挤出屏幕。

### Keyboard / 键盘

- Global hotkeys: `Ctrl + Alt + Z` (capture), `Ctrl + Alt + X` (clipboard),
  `Ctrl + Alt + C` (repeat). All can be remapped in Settings → Hotkeys.
- Region selection: arrow keys nudge by 1 px; `Shift + arrows` by 10 px; `Ctrl + A`
  selects the whole screen; `Enter` confirms; `Esc` / right-click cancels.
- Result window: `Esc` closes, `Ctrl + C` copies the translation, `Ctrl + R` re-translates.
- Settings: standard `Tab` / `Shift + Tab` navigation; switches toggle with `Space`;
  editable language pickers accept typed names/codes.

- 全局快捷键：`Ctrl + Alt + Z` 截图、`Ctrl + Alt + X` 剪贴板、`Ctrl + Alt + C` 重译；
  均可在「设置 → 快捷键」中修改。
- 框选：方向键 1px 微调，`Shift + 方向键` 10px，`Ctrl + A` 全屏，`Enter` 确认，
  `Esc` / 右键取消。
- 结果窗：`Esc` 关闭、`Ctrl + C` 复制译文、`Ctrl + R` 重新翻译。
- 设置：标准 `Tab` / `Shift + Tab` 导航；开关用空格切换；语言下拉框可直接输入名称或代码。

### Screen readers / 屏幕阅读器

Most inputs, buttons, combos, and text areas are native Qt widgets and expose standard
roles, names, and states to Windows UI Automation. Several decorative/custom-painted
controls (the animated switch, segmented tab bar, activity indicator, and resize grips) are
drawn manually and may have limited or no announced role/value. This is a known gap.

大部分输入框、按钮、下拉框和文本区是原生 Qt 控件，会向 Windows UI Automation 暴露标准
角色、名称和状态。少数自绘控件（滑动开关、分段标签、加载指示器、缩放手柄）可能无法被
屏幕阅读器正确朗读——这是已知不足。

### Motion and colour / 动效与配色

- Switch animation is short (~170 ms); the loading spinner rotates while a request is active.
- There is currently **no “reduce motion” setting**.
- Focus is indicated with an accent-coloured outline on inputs, buttons, and switches.
- Colour contrast has been designed against the iOS palette but has **not** been formally
  audited against WCAG.

- 开关动画约 170ms；加载指示器在请求期间旋转。
- 目前**没有「减少动态效果」开关**。
- 输入框、按钮和开关有强调色焦点轮廓。
- 配色按 iOS 调色板设计，但**尚未**按 WCAG 正式审计。

## Known limitations / 已知限制

1. Custom-painted switches and segmented tabs do not publish accessible names/values yet.
2. Region selection starts from a mouse drag; keyboard users can nudge or select the whole
   screen, but cannot create an arbitrary rectangle from the keyboard alone.
3. The overlay magnifier and size badge are visual aids only.
4. “Reduce motion” is not implemented.
5. OCR language coverage depends on the bundled RapidOCR models; text in unsupported
   scripts may not be recognised even though translation supports more languages.
6. The binary is not code-signed; SmartScreen warnings are a known limitation.

1. 自绘开关和分段标签尚未提供无障碍名称/值。
2. 框选从鼠标拖动开始；键盘可以微调或全选屏幕，但不能仅靠键盘创建任意选区。
3. 遮罩上的放大镜和尺寸角标只是视觉辅助。
4. 尚未实现「减少动态效果」。
5. OCR 语言覆盖取决于内置 RapidOCR 模型；即使翻译支持某语言，对应文字也可能识别不了。
6. 程序没有代码签名，SmartScreen 提示属于已知限制。

## Reporting an accessibility barrier / 反馈无障碍障碍

Open a GitHub issue with the **accessibility** label:

<https://github.com/salt-jar/snaptranslate/issues/new/choose>

Please include:

- Windows version and display scaling (e.g. Windows 11, 150%).
- Assistive technology used (NVDA / Narrator / Magnifier / high-contrast mode, etc.).
- What you tried, what happened, and what you expected.
- Whether it reproduces in both light and dark themes.
- A screenshot only if it contains no private information.

If the barrier also reveals a security or privacy problem, use the
[security policy](.github/SECURITY.md) instead.

请开一个带 **accessibility** 标签的 GitHub Issue，并尽量提供：
Windows 版本与缩放比例、使用的辅助技术（NVDA / 讲述人 / 放大镜 / 高对比度等）、
操作步骤与预期、是否在浅色和深色主题下都能复现、以及不含隐私的截图。

如果障碍同时涉及安全或隐私问题，请改用[安全政策](.github/SECURITY.md)。

## Roadmap / 后续计划

- Add accessible names/roles/values to the custom switch and segmented tabs.
- Add a “reduce motion” preference.
- Audit the main windows with NVDA and Windows Narrator.
- Improve keyboard-only region selection.

- 为自绘开关和分段标签补充无障碍名称/角色/值；
- 增加「减少动态效果」选项；
- 用 NVDA 和 Windows 讲述人审计主要窗口；
- 改进纯键盘框选。
