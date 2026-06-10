# tests/fixtures/

存放测试用固定数据文件（fixtures）。

## 文件列表

- `metadata.v2.sample.json`：符合 metadata schema v2 的最小合法样本，用于 test_metadata.py
- `search_extraction_gap.html`：搜索结果抽取 known-gap 的最小 HTML 复现，用于固定 partial 字段缺失质量判断

## 约定

- 每个 fixture 文件名需在此 README 中注册
- 不存放任何包含真实凭证的数据
- 不存放超过 100KB 的文件（使用 tmp_path 动态生成大数据）
