#!/bin/bash
# SECURITY MANIFEST:
#   Environment variables accessed: none
#   External endpoints called: none
#   Local files read: SKILL.md (from script directory)
#   Local files written: SKILL.md to skill directories of detected AI tools
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_FILE="$SKILL_DIR/SKILL.md"

if [ ! -f "$SKILL_FILE" ]; then
  echo "错误: 找不到 SKILL.md 文件: $SKILL_FILE"
  exit 1
fi

installed=0

# --- OpenCode (全局) ---
OPENCODE_DIR="$HOME/.config/opencode/skills/cliany-site"
if command -v opencode >/dev/null 2>&1 || [ -d "$HOME/.config/opencode" ]; then
  mkdir -p "$OPENCODE_DIR"
  cp "$SKILL_FILE" "$OPENCODE_DIR/SKILL.md"
  echo "[OK] OpenCode (全局): $OPENCODE_DIR/SKILL.md"
  installed=$((installed + 1))
fi

# --- Claude Code / OpenClaw ---
CLAUDE_DIR="$HOME/.claude/skills/cliany-site"
if [ -d "$HOME/.claude" ] || command -v claude >/dev/null 2>&1; then
  mkdir -p "$CLAUDE_DIR"
  cp "$SKILL_FILE" "$CLAUDE_DIR/SKILL.md"
  echo "[OK] Claude Code: $CLAUDE_DIR/SKILL.md"
  installed=$((installed + 1))
fi

OPENCLAW_DIR="$HOME/.openclaw/skills/cliany-site"
if [ -d "$HOME/.openclaw" ] || command -v openclaw >/dev/null 2>&1; then
  mkdir -p "$OPENCLAW_DIR"
  cp "$SKILL_FILE" "$OPENCLAW_DIR/SKILL.md"
  echo "[OK] OpenClaw: $OPENCLAW_DIR/SKILL.md"
  installed=$((installed + 1))
fi

# --- Codex ---
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CODEX_DIR="$CODEX_HOME/skills/cliany-site"
if [ -d "$CODEX_HOME" ] || command -v codex >/dev/null 2>&1; then
  mkdir -p "$CODEX_DIR"
  cp "$SKILL_FILE" "$CODEX_DIR/SKILL.md"
  echo "[OK] Codex: $CODEX_DIR/SKILL.md"
  installed=$((installed + 1))
fi

# --- .agents 通用路径 ---
AGENTS_DIR="$HOME/.agents/skills/cliany-site"
if [ -d "$HOME/.agents" ]; then
  mkdir -p "$AGENTS_DIR"
  cp "$SKILL_FILE" "$AGENTS_DIR/SKILL.md"
  echo "[OK] .agents (通用): $AGENTS_DIR/SKILL.md"
  installed=$((installed + 1))
fi

# --- 结果 ---
echo ""
if [ "$installed" -eq 0 ]; then
  echo "未检测到已安装的 AI 编程工具。"
  echo ""
  echo "手动安装方法："
  echo "  OpenCode:   mkdir -p ~/.config/opencode/skills/cliany-site && cp SKILL.md ~/.config/opencode/skills/cliany-site/"
  echo "  Claude Code: mkdir -p ~/.claude/skills/cliany-site && cp SKILL.md ~/.claude/skills/cliany-site/"
  echo "  OpenClaw:   mkdir -p ~/.openclaw/skills/cliany-site && cp SKILL.md ~/.openclaw/skills/cliany-site/"
  echo "  Codex:      mkdir -p ~/.codex/skills/cliany-site && cp SKILL.md ~/.codex/skills/cliany-site/"
  exit 1
else
  echo "安装完成！共安装到 $installed 个工具。"
  echo "重启 AI 编程助手后即可使用 cliany-site skill。"
fi
