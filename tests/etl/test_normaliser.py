import pytest
from src.etl.normaliser import normalize_year, normalize_ticker

# ---------------- normalize_year (20 tests) ----------------

@pytest.mark.parametrize(
    "input_year, expected",
    [
        ("Mar 2014", "2014-03"),
        ("Mar 2015", "2015-03"),
        ("Mar 2016", "2016-03"),
        ("Mar 2017", "2017-03"),
        ("Mar 2018", "2018-03"),
        ("Mar 2019", "2019-03"),
        ("Mar 2020", "2020-03"),
        ("Mar 2021", "2021-03"),
        ("Mar 2022", "2022-03"),
        ("Mar 2023", "2023-03"),
        ("Dec 2012", "2012-12"),
        ("Dec 2013", "2013-12"),
        ("Dec 2014", "2014-12"),
        ("Dec 2015", "2015-12"),
        ("Mar-23", "2023-03"),
        ("Mar-24", "2024-03"),
        ("Dec-23", "2023-12"),
        ("Dec-24", "2024-12"),
        ("TTM", "TTM"),
        (None, None),
    ]
)
def test_normalize_year(input_year, expected):
    assert normalize_year(input_year) == expected


# ---------------- normalize_ticker (15 tests) ----------------

@pytest.mark.parametrize(
    "ticker, expected",
    [
        ("abb", "ABB"),
        (" ABB ", "ABB"),
        ("tcs", "TCS"),
        ("reliance", "RELIANCE"),
        ("wipro", "WIPRO"),
        ("infy", "INFY"),
        ("hdfcbank", "HDFCBANK"),
        ("icicibank", "ICICIBANK"),
        ("zomato", "ZOMATO"),
        ("vedl", "VEDL"),
        ("vbl", "VBL"),
        ("", ""),
        ("  ", ""),
        (123, "123"),
        (None, None),
    ]
)
def test_normalize_ticker(ticker, expected):
    assert normalize_ticker(ticker) == expected