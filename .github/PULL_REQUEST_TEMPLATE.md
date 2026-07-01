## 描述 / Description

<!-- 描述这个 PR 做了什么，解决了什么问题 / What does this PR do? What problem does it solve? -->

关联 Issue / Related Issue: <!-- Closes #XXX or N/A -->

---

## 变更类型 / Type of Change

<!-- 勾选适用项 / Check all that apply -->

- [ ] 🐛 Bug 修复 / Bug fix
- [ ] ✨ 新功能 / New feature
- [ ] ♻️ 重构 / Refactoring (no functional changes)
- [ ] 📝 文档更新 / Documentation update
- [ ] 🔧 配置/依赖 / Configuration or dependency update
- [ ] 🧪 测试 / Tests only
- [ ] 其他 / Other: <!-- 请说明 / Please describe -->

---

## 测试 / Testing

<!-- 如何验证这个改动？/ How did you test this change? -->

- [ ] 本地运行相关 pytest 通过 / Ran relevant pytest locally
- [ ] 本地运行相关 `ruff check ...` 通过 / Ran relevant `ruff check ...`
- [ ] 如涉及真实案例库，已运行 `python scripts/validate_cases.py --strict`
- [ ] 如涉及发布脚本、发布文档或 CI gate，已运行 `python scripts/release_readiness.py --json`
- [ ] 如涉及 candidate promotion，PR 描述已贴出 `primary_next_task_runbook` 与 `doctor_preflight_evidence_fields`，并核对 `case_promotion_evidence_primary_runbook_steps` / hash 未漂移
- [ ] 如涉及默认 PR 门禁，已确认路径使用 `CLIANY_QA_OFFLINE=1`，不依赖真实 LLM key
- [ ] 手动测试了以下场景 / Manually tested the following scenarios:
  <!-- 描述测试场景 / Describe your test scenarios -->

---

## 提交前检查清单 / Pre-submission Checklist

- [ ] 改动范围与关联 Issue 或路线图目标一致 / Scope matches the related issue or roadmap goal
- [ ] 已按改动风险选择验证范围，而不是只跑无关测试 / Validation matches the changed area
- [ ] 文档已更新（如有必要）/ Documentation updated (if necessary)
- [ ] CHANGELOG 或 release draft 已更新（如有用户可见变化）/ CHANGELOG or release draft updated for user-visible changes
- [ ] 未提交 `~/.cliany-site/`、adapter/session/snapshot 运行时状态 / No runtime state committed
- [ ] 如有破坏性变更，已在描述中明确说明 / Breaking changes are clearly documented
