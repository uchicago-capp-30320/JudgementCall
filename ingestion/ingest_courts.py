"""
One-off ingestion functions to create court records.
Currently return pandas dataframes.

Sources:
- CourtListener API - https://www.courtlistener.com/api/rest/v4/courts/
- Web Archive NCSC Judicial Selection - http://web.archive.org/web/20211129172422/http://judicialselection.us/judicial_selection/methods/selection_of_judges.cfm?state=

"""

import os
import sys
from pathlib import Path
import requests
import lxml.html
import pandas as pd
import us
from collections import defaultdict

ARCHIVE_NCSC_URL = "http://web.archive.org/web/20211129172422/http://judicialselection.us/judicial_selection/methods/selection_of_judges.cfm?state="

CL_BASE_URL = "https://www.courtlistener.com/"
CL_COURTS = "api/rest/v4/courts/"

STATE_LEVEL_COURT_CODES = ["S", "SA", "ST", "SS", ""]
STATE_SC_COURT_CODE = "S"

COURT_LOOKUP_SHORT = {
    "AL": "ala",
    "AK": "alaska",
    "AZ": "ariz",
    "AR": "ark",
    "CA": "cal",
    "CO": "colo",
    "CT": "conn",
    "DE": "del",
    "FL": "fla",
    "GA": "ga",
    "HI": "haw",
    "ID": "idaho",
    "IL": "ill",
    "IN": "ind",
    "IA": "iowa",
    "KS": "kan",
    "KY": "ky",
    "LA": "la",
    "ME": "me",
    "MD": "md",
    "MA": "mass",
    "MI": "mich",
    "MN": "minn",
    "MS": "miss",
    "MO": "mo",
    "MT": "mont",
    "NE": "neb",
    "NV": "nev",
    "NH": "nh",
    "NJ": "nj",
    "NM": "nm",
    "NY": "ny",
    "NC": "nc",
    "ND": "nd",
    "OH": "ohio",
    "OK": "okla",
    "OR": "or",
    "PA": "pa",
    "RI": "ri",
    "SC": "sc",
    "SD": "sd",
    "TN": "tenn",
    "TX": "tex",
    "UT": "utah",
    "VT": "vt",
    "VA": "va",
    "WA": "wash",
    "WV": "wva",
    "WI": "wis",
    "WY": "wyo",
}
COURT_LOOKUP_LONG = {
    "Alabama": "ala",
    "Alaska": "alaska",
    "Arizona": "ariz",
    "Arkansas": "ark",
    "California": "cal",
    "Colorado": "colo",
    "Connecticut": "conn",
    "Delaware": "del",
    "Florida": "fla",
    "Georgia": "ga",
    "Hawaii": "haw",
    "Idaho": "idaho",
    "Illinois": "ill",
    "Indiana": "ind",
    "Iowa": "iowa",
    "Kansas": "kan",
    "Kentucky": "ky",
    "Louisiana": "la",
    "Maine": "me",
    "Maryland": "md",
    "Massachusetts": "mass",
    "Michigan": "mich",
    "Minnesota": "minn",
    "Mississippi": "miss",
    "Missouri": "mo",
    "Montana": "mont",
    "Nebraska": "neb",
    "Nevada": "nev",
    "New Hampshire": "nh",
    "New Jersey": "nj",
    "New Mexico": "nm",
    "New York": "ny",
    "North Carolina": "nc",
    "North Dakota": "nd",
    "Ohio": "ohio",
    "Oklahoma": "okla",
    "Oregon": "or",
    "Pennsylvania": "pa",
    "Rhode Island": "ri",
    "South Carolina": "sc",
    "South Dakota": "sd",
    "Tennessee": "tenn",
    "Texas": "tex",
    "Utah": "utah",
    "Vermont": "vt",
    "Virginia": "va",
    "Washington": "wash",
    "West Virginia": "wva",
    "Wisconsin": "wis",
    "Wyoming": "wyo",
}


"""
Scraper functions - return dataframes.
"""


def scrape_ncsc_archive():
    resp = requests.get(ARCHIVE_NCSC_URL)
    response = lxml.html.fromstring(resp.text)

    # state data dict format:
    # {"State_Name": {"Court_Name": {court data dict}}, "State_Name": {},...}
    state_data_dict = defaultdict(lambda: defaultdict(dict))
    state_source_dict = defaultdict(list)

    for item in response.xpath('//div[@id="content"]/*'):
        if item.tag in ["h2", "h3"]:
            continue
        # update the state
        elif item.tag == "div" and "yellow_box" in item.classes:
            state_str = item.xpath("h4/text()")[0]

        # get info for state
        elif item.tag == "table":
            state_data_str = item.text_content()
            state_data_list = [
                item for item in state_data_str.replace("\t", "").split("\n") if item != ""
            ]
            info_key = state_data_list[0]

            i = 1
            while i < len(state_data_list) - 1:
                court = state_data_list[i]
                info_value = state_data_list[i + 1]
                state_data_dict[state_str][court][info_key] = info_value
                i += 2

        elif item.tag == "p":
            note = item.text_content()
            state_source_dict[state_str].append(note.replace("\n", "").replace("\xa0", ""))

    state_data_flat_list = []
    for state, court_dict in state_data_dict.items():
        for court, info in court_dict.items():
            flat = {"State": state, "Court": court, **info, "Source": state_source_dict[state]}
            state_data_flat_list.append(flat)
    df = pd.DataFrame(state_data_flat_list)
    return df


def scrape_courtlistener_courts(api_token):
    courts_results = []
    page_url = CL_BASE_URL + CL_COURTS
    while page_url is not None:
        r = requests.get(page_url, headers={"Authorization": f"Token {api_token}"})
        print(r.status_code, page_url)
        response = r.json()
        results = response["results"]
        courts_results.extend(results)
        page_url = response["next"]
    df = pd.DataFrame(courts_results)
    return df


"""
Functions to create merge columns.
"""


def create_merged_courts_df():
    ncsc_file_path = Path("./data/courts/courts_ncsc.csv")
    cl_file_path = Path("./data/courts/courts_cl.csv")

    if ncsc_file_path.is_file():
        courts_ncsc = pd.read_csv(ncsc_file_path)
    else:
        print("NCSC file not found; scraping NCSC archive")
        courts_ncsc = scrape_ncsc_archive()
        courts_ncsc.to_csv(ncsc_file_path)

    if cl_file_path.is_file():
        courts_cl = pd.read_csv(cl_file_path)
    else:
        try:
            api_token = os.environ["CL_API_KEY"]
        except KeyError:
            print(
                "CourtListener API Key is not set. "
                "Set environment variable CL_API_KEY to your API key to continue."
            )
            return
        print("CL file not found; scraping CL")
        courts_cl = scrape_courtlistener_courts(api_token)
        courts_cl.to_csv(cl_file_path)

    def prep_ncsc_df(ncsc_df):
        """
        Creates columns necessary for merge on court type and state.
        """
        # create court_type column from Court column
        ncsc_df["Court"] = ncsc_df["Court"].str.strip(":")
        ncsc_df["court_type"] = ncsc_df["Court"]
        # necessary to match in Florida
        ncsc_df["court_type"] = ncsc_df["court_type"].apply(
            lambda s: "District Court of Appeal" if s == "District Courts of Appeal" else s
        )
        # nonideal but necessary to get matches in California
        ncsc_df["court_type"] = ncsc_df["court_type"].apply(
            lambda s: "Court of Appeal" if s == "Court of Appeals" else s
        )
        ncsc_df["state"] = ncsc_df["State"].map(us.states.mapping("name", "abbr"))

        return ncsc_df

    def get_ncsc_court_types():
        """
        Helper to get all court type strings that appear in the NCSC data.
        """
        ncsc_df = prep_ncsc_df(courts_ncsc)
        ncsc_court_types = ncsc_df["court_type"].unique()
        # list in reverse string-length order to get most specific match
        ncsc_court_types = sorted(list(ncsc_court_types), key=lambda s: -len(s))

        return ncsc_court_types

    ncsc_court_types = get_ncsc_court_types()

    def get_court_type(name):
        """
        Helper to pass to prep_cl_df to match court_type columns.
        """
        for court_type in ncsc_court_types:
            if court_type in name:
                return court_type

    def cl_get_extant_courts(cl_df, court_codes=None):
        """
        Remove defunct courts and filter by CL court codes.
        """
        # filter out defunct courts: past end date
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
        state_supreme_courts = cl_get_extant_courts(courts_cl, STATE_SC_COURT_CODE)
        cl_state_ids = state_supreme_courts["id"].unique()
        state_abbr = [state.abbr for state in us.states.STATES]
        cl_id_lookup = dict(zip(cl_state_ids, state_abbr))
        cl_id_lookup["col"] = "CO"
        cl_id_lookup["co"] = "CO"
        cl_id_lookup["wv"] = "WV"

        return cl_id_lookup

    cl_id_lookup = create_cl_id_lookup()

    def match_state_id(id):
        """
        Helper to pass to prep_cl_df to get US state abbr from id code.
        """
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
        all_state_courts["court_level"] = all_state_courts["jurisdiction"].map(
            {"S": "sup", "SA": "apl", "SS": "lwr", "ST": "lwr"}
        )
        cl_final = all_state_courts[
            ["id", "full_name", "court_level", "court_type", "state", "url"]
        ]
        return cl_final

    state_courts = cl_get_extant_courts(courts_cl, STATE_LEVEL_COURT_CODES)
    state_courts_db_cols = prep_cl_df(state_courts)
    ncsc_data = prep_ncsc_df(courts_ncsc)
    merged_df = state_courts_db_cols.merge(ncsc_data, how="left", on=["state", "court_type"])
    merged_df = merged_df.drop(["State", "Court"], axis=1)
    rename = {
        "id": "court_id",
        "full_name": "name",
        "Number of Judgeships": "bench_size",
        "Geographic Basis for Selection": "selection_jurisdiction",
        "Method of Selection (full term)": "selection_method",
        "Length of Subsequent Terms": "term_length",
    }
    merged_df = merged_df.rename(columns=rename)
    merged_df = merged_df.set_index("court_id")

    def get_selection_type(selection_method):
        if isinstance(selection_method, str):
            for selection_type in ["appointment", "nonpartisan election", "partisan election"]:
                if selection_type in selection_method:
                    return selection_type

    merged_df["selection_type"] = merged_df["selection_method"].apply(get_selection_type)
    merged_df["term_length"] = merged_df["term_length"].apply(
        lambda s: s.replace(" yrs", "").replace("yrs", "").replace(" years", "")
        if isinstance(s, str)
        else s
    )
    # the New Jersey exception
    merged_df["term_length"] = merged_df["term_length"].apply(
        lambda s: 7 if s == "until age 70" else s
    )
    numeric_fields = ["bench_size", "term_length"]

    for field in numeric_fields:
        merged_df[field] = merged_df[field].apply(
            lambda s: s.replace("*", "").replace("---", "") if isinstance(s, str) else s
        )

    return merged_df[
        [
            "name",
            # "state",
            "court_level",
            "court_type",
            "bench_size",
            "selection_jurisdiction",
            "selection_method",
            "selection_type",
            "term_length",
            "url",
        ]
    ]


MERGED_COURTS_PATH = Path("./data/courts/courts_merged.csv")


def get_courts_df():
    if MERGED_COURTS_PATH.is_file():
        merged_courts_df = pd.read_csv(MERGED_COURTS_PATH)
    else:
        print("Merged courts file not found; creating merged courts df")
        merged_courts_df = create_merged_courts_df()
        merged_courts_df.to_csv(MERGED_COURTS_PATH)

    return merged_courts_df


def main():
    courts_df = get_courts_df()
    print(courts_df.head())


if __name__ == "__main__":
    main()
