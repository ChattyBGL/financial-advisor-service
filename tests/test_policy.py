from app.services.policy import MAX_SECTIONS, find_policy_context, parse_sections

TEXT = """APEX FINANCIAL PARTNERS
Risk and Compliance Policy
SECTION 01
1. Compliance Auditing
Audits happen yearly.
RISK & COMPLIANCE POLICY \x7f 2026
CONFIDENTIAL \x7f INTERNAL USE ONLY
Page 6 of 205
SECTION 01 \x7f CONTINUED
Compliance Auditing
Findings are logged.
RISK & COMPLIANCE POLICY \x7f 2026
CONFIDENTIAL \x7f INTERNAL USE ONLY
Page 7 of 205
SECTION 02
2. Portfolio Diversification
No more than 25% in one stock.
SECTION 03
3. Employee Conduct
Be nice.
SECTION 04
4. Portfolio Diversification
Rebalance quarterly.
SECTION 05
5. Portfolio Diversification
Fifth.
SECTION 06
6. Portfolio Diversification
Sixth.
"""

SECTIONS = parse_sections(TEXT)


def test_parse_splits_on_section_headings_and_strips_continued() -> None:
    assert [s.number for s in SECTIONS] == [1, 2, 3, 4, 5, 6]
    assert SECTIONS[0].title == "Compliance Auditing"
    assert SECTIONS[0].body == "Audits happen yearly.\nFindings are logged."
    assert SECTIONS[1].as_text() == "2. Portfolio Diversification\nNo more than 25% in one stock."


def test_find_returns_whole_matching_sections_by_title() -> None:
    out = find_policy_context("What does the policy say about employee conduct?", SECTIONS)
    assert out == "3. Employee Conduct\nBe nice."


def test_find_caps_number_of_sections() -> None:
    out = find_policy_context("diversification rules", SECTIONS)
    numbers = [line for line in out.splitlines() if line.endswith("Portfolio Diversification")]
    assert len(numbers) == MAX_SECTIONS
    assert numbers == [f"{n}. Portfolio Diversification" for n in (2, 4, 5)]


def test_find_ignores_short_and_filler_words() -> None:
    assert find_policy_context("what is this about", SECTIONS) == ""
    assert find_policy_context("", SECTIONS) == ""


def test_find_without_match_is_empty() -> None:
    assert find_policy_context("cryptocurrency custody", SECTIONS) == ""
