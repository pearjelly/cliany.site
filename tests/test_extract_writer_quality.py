from cliany_site.extract_writer import _format_markdown


def test_extract_markdown_includes_quality_status_for_valid_rows():
    markdown = _format_markdown(
        [
            {
                "description": "搜索结果",
                "extract_mode": "list",
                "fields": {"title": "h3", "url": "a@href"},
                "data": [{"title": "cliany-site", "url": "https://example.com"}],
            }
        ],
        "example.com",
        "搜索 cliany-site",
    )

    assert "**质量：** ok" in markdown
    assert "| title | url |" in markdown


def test_extract_markdown_includes_quality_issues_for_empty_fields():
    markdown = _format_markdown(
        [
            {
                "description": "搜索结果",
                "extract_mode": "list",
                "fields": {"title": "h3", "url": "a@href"},
                "data": [{"title": "", "url": ""}],
            }
        ],
        "example.com",
        "搜索 cliany-site",
    )

    assert "**质量：** empty" in markdown
    assert "> 质量问题：all rows are blank；" in markdown
    assert "field is blank in all rows: title" in markdown
    assert "field is blank in all rows: url" in markdown
