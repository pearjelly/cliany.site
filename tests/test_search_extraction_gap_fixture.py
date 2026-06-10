from html.parser import HTMLParser
from pathlib import Path

from cliany_site.extract_quality import evaluate_extract_quality

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "search_extraction_gap.html"


class SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name: value or "" for name, value in attrs}
        classes = set(attrs_dict.get("class", "").split())
        if tag == "article" and "result-card" in classes:
            self._current = {"title": "", "url": "", "snippet": ""}
            return
        if self._current is None:
            return
        if tag == "h2" and "result-title" in classes:
            self._capture = "title"
        elif tag == "a" and "result-link" in classes:
            self._current["url"] = attrs_dict.get("href", "")
            self._capture = "title"
        elif tag == "p" and "result-snippet" in classes:
            self._capture = "snippet"

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self._current is not None:
            self.rows.append({key: value.strip() for key, value in self._current.items()})
            self._current = None
            self._capture = None
        elif tag in {"h2", "a", "p"}:
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._capture:
            self._current[self._capture] += data


def _extract_fixture_rows() -> list[dict[str, str]]:
    parser = SearchResultParser()
    parser.feed(FIXTURE.read_text(encoding="utf-8"))
    return parser.rows


def test_search_extraction_gap_fixture_reproduces_partial_quality():
    rows = _extract_fixture_rows()

    quality = evaluate_extract_quality(
        "list",
        rows,
        {"title": ".result-title", "url": ".result-link@href", "snippet": ".result-snippet"},
    )

    assert rows == [
        {"title": "Alpha README", "url": "https://example.com/alpha", "snippet": "包含 README 和安装说明。"},
        {"title": "Beta issue tracker", "url": "", "snippet": "标题可见，但缺少链接 href。"},
        {"title": "Gamma docs", "url": "https://example.com/gamma", "snippet": ""},
    ]
    assert quality.ok is False
    assert quality.status == "partial"
    assert quality.row_count == 3
    assert "field is blank in 1/3 rows: url" in quality.issues
    assert "field is blank in 1/3 rows: snippet" in quality.issues
