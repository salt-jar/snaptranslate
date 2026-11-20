## Summary / 概要

<!-- What does this PR change, and why? / 这个 PR 改了什么，为什么？ -->

Fixes #

## Type of change / 变更类型

- [ ] Bug fix / 修复 Bug
- [ ] New feature / 新功能
- [ ] Translation / OCR quality / 翻译或识别质量
- [ ] UI / accessibility / 界面或无障碍
- [ ] Documentation / 文档
- [ ] Build / packaging / 打包
- [ ] Refactor / chore / 重构或杂项

## What changed / 具体改动

<!-- A short bullet list is enough. / 简短要点即可。 -->

-

## Testing / 测试

Commands run and results:

```bat
python -m compileall -q app main.py tools
python tools\test_translation.py --no-net
python tools\test_languages.py
python tools\ui_check.py --shot-dir .tmp\ui
```

- [ ] Offline tests pass / 离线测试通过
- [ ] Network-dependent tests run (or explain why skipped) / 联网测试已跑或说明跳过原因
- [ ] Tested with the portable build (if packaging changed) / 打包改动已用冻结版验证

## Screenshots / 截图

<!-- Required for UI changes: light and dark, plus resized windows if relevant. -->
<!-- UI 改动必填：浅色 + 深色；涉及缩放请附调整大小后的截图。 -->

| Light / 浅色 | Dark / 深色 |
| --- | --- |
|  |  |

## Checklist / 检查清单

- [ ] One logical change; branch rebased on `main` / 一个逻辑变更，已 rebase 到 `main`
- [ ] No secrets, API keys, personal paths or private screenshots / 不含密钥、个人路径或隐私截图
- [ ] Local translation still never falls back to an online engine / 本地翻译仍然不会静默联网
- [ ] Tests or regression cases added where appropriate / 已补测试或回归用例
- [ ] Docs updated for user-facing changes / 用户可见改动已更新文档
- [ ] I agree to license this contribution under the MIT License / 同意按 MIT 许可证授权
- [ ] I followed the [Code of Conduct](../CODE_OF_CONDUCT.md) / 遵守[行为准则](../CODE_OF_CONDUCT.md)
