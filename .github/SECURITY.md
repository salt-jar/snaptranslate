# Security Policy / 安全政策

## Supported versions / 支持的版本

| Version | Supported |
| --- | --- |
| 1.3.x | ✅ Security fixes |
| 1.2.x | ⚠️ Best effort (critical issues only) |
| < 1.2 | ❌ Unsupported |

The portable ZIP is the official binary distribution. Source builds are supported on a
best-effort basis.

| 版本 | 支持情况 |
| --- | --- |
| 1.3.x | ✅ 提供安全修复 |
| 1.2.x | ⚠️ 仅尽力处理严重问题 |
| < 1.2 | ❌ 不再支持 |

免安装 ZIP 是官方二进制分发方式；源码构建按尽力而为处理。

## Reporting a vulnerability / 报告漏洞

**Please do not open a public issue for security problems.**
**请不要为安全问题开公开 Issue。**

Use GitHub's private vulnerability reporting:

1. Open <https://github.com/salt-jar/snaptranslate/security/advisories/new>.
2. Describe the issue and include a proof of concept if possible.
3. Do **not** attach real API keys, tokens, personal data, or private screenshots.

If private reporting is unavailable, contact the maintainer
[@salt-jar](https://github.com/salt-jar) through the public contact information on their
GitHub profile and keep the initial message short. We will arrange a private channel.

请使用 GitHub 的私密漏洞报告：

1. 打开 <https://github.com/salt-jar/snaptranslate/security/advisories/new>；
2. 描述问题，条件允许时附上最小复现；
3. **不要**附带真实的 API Key、令牌、个人数据或私人截图。

如果私密报告入口不可用，请通过维护者 [@salt-jar](https://github.com/salt-jar)
GitHub 主页的公开联系方式联系，并保持首条消息简短，我们会安排私密渠道。

### What to include / 请提供

- Affected version (Settings → About) and Windows version.
- How you installed it (portable ZIP or source).
- Steps to reproduce, expected behaviour, and actual behaviour.
- The smallest proof of concept you can share.
- Relevant log excerpts with secrets and personal paths removed.

- 受影响版本（设置 → 关于）和 Windows 版本；
- 安装方式（免安装 ZIP 或源码）；
- 复现步骤、预期行为、实际行为；
- 尽量小的 PoC；
- 相关日志片段（请先删除密钥和个人路径）。

## Response / 响应时间

- Initial acknowledgement: within **3 business days**.
- Triage and severity assessment: within **7 business days** where possible.
- Fix and disclosure: coordinated with the reporter; no fixed deadline is promised, but we
  will keep you informed.

- 初次确认：**3 个工作日内**；
- 定级与评估：尽可能在 **7 个工作日内**；
- 修复与公开：与报告者协调，不承诺固定期限，但会同步进展。

Please give us a reasonable window to fix the issue before public disclosure. We will
credit reporters who want to be credited.

请在公开披露前给我们合理的修复时间。愿意署名的报告者会被致谢。

## Scope / 范围

In scope:

- The application code in this repository (`app/`, `main.py`, `tools/`).
- The portable build published in GitHub Releases.
- Handling of API keys in `config.json` and the settings UI.
- Local translation's "no network requests" privacy guarantee.
- OCR/translation input handling that could lead to code execution, data exfiltration, or
  unintended network requests.

Out of scope:

- Vulnerabilities in third-party services (Youdao, Yandex, MyMemory, Google, Baidu, LLM
  providers) — report those to the service owner.
- Issues that require the attacker to already have code execution or administrator rights.
- Social engineering, physical access, and denial-of-service through unrealistic input sizes.
- Missing code signing / SmartScreen warnings (known limitation, documented in README).

范围内：应用代码、官方免安装构建、API Key 处理、本地翻译的“零网络请求”承诺、
以及可能导致代码执行/数据外泄/意外联网的输入处理。

范围外：第三方翻译服务自身的漏洞、需要已有代码执行权限的问题、社会工程、物理访问、
不切实际超大输入造成的拒绝服务，以及缺少代码签名（README 已列为已知限制）。

## Safe harbor / 安全港

We will not pursue legal action against researchers who:

- make a good-faith effort to avoid privacy violations, data loss, and service disruption;
- only test against their own installation and data;
- report the issue privately and give us reasonable time to fix it before disclosure.

对于善意研究（避免侵犯隐私/破坏数据/中断服务、只测试自己的安装和数据、私下报告并
给予合理修复时间）的安全研究者，我们不会采取法律行动。
