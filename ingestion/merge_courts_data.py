"""
Merge courts data from CourtListener and archived NCSC page. 
Will probably combine this with ingest_courts_data.py, keeping separate for now!
"""

import pandas as pd
import us
import ingest_courts_data

CL_DF = pd.read_csv("courts_cl.csv")
NCSC_DF = pd.read_csv("courts_ncsc.csv")
#CL_DF = ingest_courts_data.ingest_courtlistener()
#NCSC_DF = ingest_courts_data.scrape_ncsc_archive()

def prep_ncsc_df(ncsc_df):
    """
    Creates columns necessary for merge on court type and state.
    """
    # create court_type column from Court column
    ncsc_df["Court"] = ncsc_df["Court"].str.strip(":")
    ncsc_df["court_type"] = ncsc_df["Court"]
    # necessary to match in Florida
    ncsc_df["court_type"] = ncsc_df["court_type"].apply(lambda s: "District Court of Appeal" if s == "District Courts of Appeal" else s)
    # nonideal but necessary to get matches in California
    ncsc_df["court_type"] = ncsc_df["court_type"].apply(lambda s: "Court of Appeal" if s == "Court of Appeals" else s) 
    ncsc_df["state"] = ncsc_df["State"].map(us.states.mapping("name", "abbr"))

    return ncsc_df

def get_ncsc_court_types():
    """
    Helper to get all court type strings that appear in the NCSC data.
    """
    ncsc_df = prep_ncsc_df(NCSC_DF)
    ncsc_court_types = ncsc_df["court_type"].unique()
    # list in reverse string-length order to get most specific match
    ncsc_court_types = sorted(list(ncsc_court_types), key = lambda s: -len(s))

    return ncsc_court_types

def get_court_type(name):
    """
    Helper to pass to prep_cl_df to match court_type columns.
    """
    ncsc_court_types = get_ncsc_court_types()
    for court_type in ncsc_court_types:
        if court_type in name:
            return court_type


STATE_LEVEL_COURT_CODES = ["S", "SA", "ST", "SS", ""]
STATE_SC_COURT_CODE = "S"

def cl_get_extant_courts(cl_df, court_codes=None):
    """
    Remove defunct courts and filter by CL court codes. 
    """
    # filter out defunct courts: past end date or no start date
    cl_df = cl_df[(cl_df["end_date"].isna()) & (cl_df["start_date"].notna())]
    # filter to court_codes
    if isinstance(court_codes, str):
        cl_df = cl_df[cl_df["jurisdiction"] == court_codes]
    elif isinstance(court_codes, list):
        cl_df = cl_df[cl_df["jurisdiction"].isin(court_codes)]
    return cl_df


def create_cl_id_lookup():
    """
    Uses CL list of state supreme courts to get a lookup dictionary to 
    match courts to states on CL id; will probably be replaced by a better 
    CL id parsing system at some point!
    """
    state_supreme_courts = cl_get_extant_courts(CL_DF, STATE_SC_COURT_CODE)
    cl_state_ids = state_supreme_courts["id"].unique()
    state_abbr = [state.abbr for state in us.states.STATES]
    cl_id_lookup = dict(zip(cl_state_ids, state_abbr))
    cl_id_lookup["col"] = "CO"
    cl_id_lookup["co"] = "CO"
    cl_id_lookup["wv"] = "WV"
    
    return cl_id_lookup

def match_state_id(id):
    """
    Helper to pass to prep_cl_df to get US state abbr from id code.
    """
    cl_id_lookup = create_cl_id_lookup()
    state_ids_reversed = reversed(cl_id_lookup.keys())
    for st_id in state_ids_reversed:
        if id.startswith(st_id):
            return cl_id_lookup[st_id]
        

def prep_cl_df(all_state_courts):
    """
    Creates columns necessary for merge on court type and state.
    """
    all_state_courts["state"] = all_state_courts["id"].apply(match_state_id)
    all_state_courts["court_type"] = all_state_courts["full_name"].apply(get_court_type)
    all_state_courts["court_level"] = all_state_courts["jurisdiction"].map({"S": "sup", "SA": "apl", "SS": "lwr", "ST": "lwr"})
    cl_final = all_state_courts[["id", "full_name", "court_level", "court_type", "state", "url"]]
    return cl_final


def merge_ncsc_to_cl_df():
    """
    Merges NCSC and CL data.
    """
    state_courts = cl_get_extant_courts(CL_DF, STATE_LEVEL_COURT_CODES)
    state_courts_db_cols = prep_cl_df(state_courts)
    ncsc_data = prep_ncsc_df(NCSC_DF)
    merged_df = state_courts_db_cols.merge(ncsc_data, how='left', on=['state', 'court_type'])
    merged_df = merged_df.drop(["State", "Court"], axis=1)
    merged_df = merged_df.set_index("id")
    return merged_df


def main():
    merged_df = merge_ncsc_to_cl_df()
    print(merged_df.head())

    print("This is the main function for merge_courts_data.py.")


if __name__ == "__main__":
    main()
