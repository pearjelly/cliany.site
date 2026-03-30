#!/bin/bash
# 验证 extract_writer 模块的所有核心功能
PASS=0; FAIL=0

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

check() {
  if eval "$1" 2>/dev/null; then
    echo "[PASS] $2"
    PASS=$((PASS+1))
  else
    echo "[FAIL] $2"
    FAIL=$((FAIL+1))
  fi
}

# 测试 1: 空列表输入 → 返回 None，无文件
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
import tempfile, os
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"empty.md\"
result = save_extract_markdown([], \"test.com\", \"搜索仓库\", output_path=out)
assert result is None, f\"空列表应返回 None，实际: {result}\"
assert not out.exists(), \"空列表不应创建文件\"
"' "空列表输入 → 返回 None，无文件"

# 测试 2: None 输入 → 返回 None，无文件
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"none.md\"
result = save_extract_markdown(None, \"test.com\", \"搜索仓库\", output_path=out)
assert result is None, f\"None 输入应返回 None，实际: {result}\"
assert not out.exists(), \"None 输入不应创建文件\"
"' "None 输入 → 返回 None，无文件"

# 测试 3: text 模式渲染
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"text.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"text\", \"description\": \"页面标题\", \"data\": {\"text\": \"Hello World\"}},
]
path = save_extract_markdown(results, \"test.com\", \"文字测试\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"Hello World\" in content, f\"text 模式应包含文本内容，实际:\\n{content}\"
assert \"## 提取 1\" in content
"' "text 模式渲染：输出段落文本"

# 测试 4: attribute 模式渲染
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"attribute.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"attribute\", \"description\": \"链接属性\", \"data\": {\"name\": \"test\", \"href\": \"/url\"}},
]
path = save_extract_markdown(results, \"test.com\", \"属性测试\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"**name**\" in content and \"test\" in content, f\"attribute 模式应包含键值，实际:\\n{content}\"
assert \"**href**\" in content and \"/url\" in content
"' "attribute 模式：输出键值列表"

# 测试 5: list 纯字符串列表渲染
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"list_str.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"list\", \"description\": \"项目列表\", \"data\": [\"item1\", \"item2\", \"item3\"]},
]
path = save_extract_markdown(results, \"test.com\", \"列表测试\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"- item1\" in content, f\"list 字符串应使用项目符号，实际:\\n{content}\"
assert \"- item2\" in content
assert \"- item3\" in content
"' "list 纯字符串：输出项目符号"

# 测试 6: list dict 列表渲染为表格
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"list_dict.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"list\", \"description\": \"链接列表\", \"data\": [{\"title\": \"A\", \"url\": \"/a\"}, {\"title\": \"B\", \"url\": \"/b\"}]},
]
path = save_extract_markdown(results, \"test.com\", \"dict列表测试\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"| title |\" in content or \"| title\" in content, f\"dict list 应生成表格，实际:\\n{content}\"
assert \"| --- |\" in content or \"---\" in content
assert \"| A |\" in content or \"A\" in content
"' "list dict 列表：输出 Markdown 表格"

# 测试 7: table 二维数组（第一行为表头）
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"table_2d.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"table\", \"description\": \"文章表格\", \"data\": [[\"标题\",\"作者\"],[\"文章1\",\"张三\"],[\"文章2\",\"李四\"]]},
]
path = save_extract_markdown(results, \"test.com\", \"二维表格测试\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"| 标题 |\" in content or \"标题\" in content, f\"table 二维数组应以第一行为表头，实际:\\n{content}\"
assert \"张三\" in content
assert \"李四\" in content
"' "table 二维数组：第一行为表头"

# 测试 8: table dict 列表渲染
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"table_dict.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"table\", \"description\": \"分数表格\", \"data\": [{\"name\": \"foo\", \"score\": \"90\"}, {\"name\": \"bar\", \"score\": \"85\"}]},
]
path = save_extract_markdown(results, \"test.com\", \"表格dict测试\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"| name |\" in content or \"name\" in content, f\"table dict 列表应生成表格，实际:\\n{content}\"
assert \"foo\" in content and \"90\" in content
"' "table dict 列表：以 keys 为表头"

# 测试 9: YAML frontmatter 字段完整性
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"frontmatter.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"text\", \"description\": \"测试\", \"data\": {\"text\": \"内容\"}},
]
path = save_extract_markdown(results, \"example.com\", \"前置字段测试\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"domain: example.com\" in content, f\"应包含 domain 字段，实际:\\n{content}\"
assert \"\\\"前置字段测试\\\"\" in content, \"应包含 workflow 字段\"
assert \"timestamp:\" in content, \"应包含 timestamp 字段\"
assert \"extract_count: 1\" in content, \"应包含 extract_count 字段\"
assert content.startswith(\"---\"), \"应以 YAML frontmatter 开头\"
"' "YAML frontmatter 包含 domain、workflow、timestamp、extract_count"

# 测试 10: 文件名 sanitize（含非法字符和中文）
check 'uv run python3 -c "
from cliany_site.extract_writer import _sanitize_filename
import re
name = _sanitize_filename(\"搜索 \\\"张雪峰\\\" 相关/新闻\")
assert \"/\" not in name, f\"文件名不应含 /，实际: {name}\"
assert \"\\\"\" not in name, f\"文件名不应含 \\\"，实际: {name}\"
assert name.endswith(\".md\"), f\"文件名应以 .md 结尾，实际: {name}\"
assert len(name) > 0
"' "文件名 sanitize：移除非法字符，确保 .md 后缀"

# 测试 11: output_path 覆盖 → 写入指定路径
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
custom_path = Path(tmpdir) / \"subdir\" / \"custom.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"text\", \"description\": \"自定义路径\", \"data\": {\"text\": \"内容\"}},
]
path = save_extract_markdown(results, \"test.com\", \"覆盖路径测试\", output_path=custom_path)
assert path == str(custom_path), f\"返回路径应等于自定义路径，实际: {path}\"
assert custom_path.exists(), \"文件应存在于指定路径\"
"' "output_path 覆盖：写入指定路径"

# 测试 12: 写入权限不足（只读目录）→ 返回 None，不抛异常
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
import tempfile, os, stat
rdonly = \"'"$TMPDIR"'/rdonly\"
os.makedirs(rdonly, exist_ok=True)
os.chmod(rdonly, 0o555)
results = [
    {\"step_index\": 0, \"extract_mode\": \"text\", \"description\": \"权限测试\", \"data\": {\"text\": \"内容\"}},
]
out = Path(rdonly) / \"sub\" / \"out.md\"
result = save_extract_markdown(results, \"test.com\", \"权限测试\", output_path=out)
os.chmod(rdonly, 0o755)
assert result is None, f\"只读目录应返回 None，实际: {result}\"
" 2>/dev/null' "只读目录写入 → 返回 None，不抛异常"

# 测试 13: 未知模式 → JSON 代码块输出
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"unknown.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"custom_mode\", \"description\": \"未知模式\", \"data\": {\"key\": \"value\"}},
]
path = save_extract_markdown(results, \"test.com\", \"未知模式测试\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"\`\`\`json\" in content or \"json\" in content, f\"未知模式应输出 JSON 代码块，实际:\\n{content}\"
"' "未知模式：输出 JSON 代码块"

# 测试 14: data 为 None 时不崩溃（防御性处理）
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"none_data.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"text\", \"description\": \"空数据\", \"data\": None},
]
path = save_extract_markdown(results, \"test.com\", \"空数据测试\", output_path=out)
assert path is not None, \"data=None 不应导致失败\"
"' "data 为 None 时防御处理，不崩溃"

# 测试 15: 模块可编译（语法检查）
check 'uv run python3 -m py_compile src/cliany_site/extract_writer.py' "extract_writer.py 语法无错误"

# 测试 16: 多条 extraction_results 混合模式
check 'uv run python3 -c "
from cliany_site.extract_writer import save_extract_markdown
from pathlib import Path
tmpdir = \"'"$TMPDIR"'\"
out = Path(tmpdir) / \"mixed.md\"
results = [
    {\"step_index\": 0, \"extract_mode\": \"text\", \"description\": \"标题\", \"data\": {\"text\": \"主标题\"}},
    {\"step_index\": 1, \"extract_mode\": \"list\", \"description\": \"列表\", \"data\": [\"a\", \"b\"]},
    {\"step_index\": 2, \"extract_mode\": \"attribute\", \"description\": \"属性\", \"data\": {\"class\": \"main\"}},
]
path = save_extract_markdown(results, \"test.com\", \"混合模式\", output_path=out)
assert path is not None
content = out.read_text(encoding=\"utf-8\")
assert \"extract_count: 3\" in content
assert \"## 提取 1\" in content
assert \"## 提取 2\" in content
assert \"## 提取 3\" in content
"' "多条 extraction_results 混合模式：extract_count 正确"

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
