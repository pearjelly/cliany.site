from cliany_site.extract_quality import evaluate_extract_quality


def test_text_extract_quality_flags_empty_text():
    quality = evaluate_extract_quality("text", {"text": "  "})

    assert quality.ok is False
    assert quality.status == "empty"
    assert quality.issues == ["empty text"]


def test_list_extract_quality_accepts_complete_field_rows():
    quality = evaluate_extract_quality(
        "list",
        [
            {"title": "First", "url": "https://example.com/1"},
            {"title": "Second", "url": "https://example.com/2"},
        ],
        {"title": "h3", "url": "a@href"},
    )

    assert quality.ok is True
    assert quality.status == "ok"
    assert quality.row_count == 2
    assert quality.field_names == ["title", "url"]


def test_list_extract_quality_flags_blank_expected_fields():
    quality = evaluate_extract_quality(
        "list",
        [
            {"title": "First", "url": ""},
            {"title": "", "url": ""},
        ],
        {"title": "h3", "url": "a@href"},
    )

    assert quality.ok is False
    assert quality.status == "partial"
    assert "field is blank in 1/2 rows: title" in quality.issues
    assert "field is blank in all rows: url" in quality.issues


def test_table_extract_quality_flags_all_blank_rows():
    quality = evaluate_extract_quality("table", [["", " "], [None, ""]])

    assert quality.ok is False
    assert quality.status == "empty"
    assert quality.issues == ["all table rows are blank"]
