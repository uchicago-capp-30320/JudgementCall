import pandas as pd
import us
from ingestion.ingest_courts import COURT_LOOKUP_SHORT

fips_to_code = us.states.mapping("fips", "abbr")


def counties_csv_to_df():
    return pd.read_csv("./data/united-states.csv")


def make_county_to_court_df():
    df = counties_csv_to_df()
    df = df.rename(
        columns={"FIPS State and County Codes": "fips", "Geographic area name": "county"}
    )
    df = df[["fips", "county"]]
    df["fips"] = df["fips"].astype(str).apply(lambda s: s.zfill(5))
    df["state"] = df["fips"].str[:2]
    df = df[df["state"] != "00"]
    df["state"] = df["state"].apply(lambda x: fips_to_code.get(x))
    df["court"] = df["state"].apply(lambda x: COURT_LOOKUP_SHORT.get(x))
    df.dropna(inplace=True)
    return df
