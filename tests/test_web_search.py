from unittest.mock import MagicMock, patch

from app.services.web_search import build_query, find_web_context

CLIENT = {
    "client_name": "Ada Lovelace",
    "portfolios": [
        {"holdings": [{"ticker": "AAPL"}, {"ticker": "MSFT"}]},
        {"holdings": [{"ticker": "AAPL"}]},  # duplicate ticker across portfolios
    ],
}


def test_query_is_prompt_plus_distinct_tickers() -> None:
    assert build_query("is my portfolio ok?", CLIENT) == "is my portfolio ok? AAPL MSFT"
    assert build_query("  fed rates  ", None) == "fed rates"


@patch("app.services.web_search.DDGS")
def test_results_are_mapped_to_title_url_snippet(ddgs: MagicMock) -> None:
    ddgs.return_value.text.return_value = [
        {"title": "Fed holds", "href": "https://x.test/a", "body": "The Fed held rates."},
    ]
    out = find_web_context("fed rates", CLIENT)
    assert out == [
        {"title": "Fed holds", "url": "https://x.test/a", "snippet": "The Fed held rates."}
    ]
    ddgs.return_value.text.assert_called_once_with("fed rates AAPL MSFT", max_results=3)


@patch("app.services.web_search.DDGS")
def test_search_failure_yields_empty_list(ddgs: MagicMock) -> None:
    ddgs.return_value.text.side_effect = RuntimeError("rate limited")
    assert find_web_context("anything", None) == []


@patch("app.services.web_search.DDGS")
def test_empty_prompt_skips_search(ddgs: MagicMock) -> None:
    assert find_web_context("   ", None) == []
    ddgs.assert_not_called()
