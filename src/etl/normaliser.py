import pandas as pd


def normalize_ticker(value):
    if pd.isna(value):
        return None
    return str(value).strip().upper()


def normalize_year(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    # Mar 2014 -> 2014-03
    if value.startswith("Mar "):
        return value[-4:] + "-03"

    # Dec 2012 -> 2012-12
    if value.startswith("Dec "):
        return value[-4:] + "-12"

    # Mar-23 -> 2023-03
    if value.startswith("Mar-"):
        return "20" + value[-2:] + "-03"

    # Dec-23 -> 2023-12
    if value.startswith("Dec-"):
        return "20" + value[-2:] + "-12"

    return value
