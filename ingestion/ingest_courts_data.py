"""
One-off ingestion functions to create court records.
Currently return pandas dataframes - TBD on final output!

Sources:
- CourtListener API - https://www.courtlistener.com/api/rest/v4/courts/
- Web Archive NCSC Judicial Selection - http://web.archive.org/web/20151022190427/http://www.judicialselection.us/judicial_selection/methods/selection_of_judges.cfm?state=

"""

import sys
import pandas as pd
import requests
import lxml.html
from collections import defaultdict

ARCHIVE_NCSC_URL = "http://web.archive.org/web/20211129172422/http://judicialselection.us/judicial_selection/methods/selection_of_judges.cfm?state="

CL_BASE_URL = "https://www.courtlistener.com/"
CL_COURTS = "api/rest/v4/courts/"
API_TOKEN = "REPLACE WITH YOUR API TOKEN"


def scrape_ncsc_archive():
    r = requests.get(ARCHIVE_NCSC_URL)
    response = lxml.html.fromstring(r.text)

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


def ingest_courtlistener(api_token):
    courts_results = []
    page_url = CL_BASE_URL + CL_COURTS
    while page_url is not None:
        r = requests.get(page_url, headers={"Authorization": f"Token {api_token}"})
        print(page_url, r.status_code)
        response = r.json()
        results = response["results"]
        courts_results.extend(results)
        page_url = response["next"]

    df = pd.DataFrame(courts_results)
    return df


def main():
    args = sys.argv[1:]
    if args[0] == "to_csv":
        if args[1] == "ncsc":
            print("Save NCSC data to CSV...")
            ncsc_df = scrape_ncsc_archive()
            ncsc_df.to_csv("courts_ncsc.csv")
            print("Saved to courts_ncsc.csv")
        if args[1] == "cl":
            print("Save CourtListener data to CSV...")
            if args[2]:
                api = args[2]
                cl_df = ingest_courtlistener(api)
                cl_df.to_csv("courts_cl.csv")
                print("Saved to courts_cl.csv")
            else:
                print("API key ?")

    print(
        "This is the main function for ingest_courts_data.py.\n"
        "Run 'ingest_courts_data.py to_csv ncsc' to create NCSC CSV file.\n"
        "Run 'ingest_courts_data.py to_csv cl YOUR_API_KEY' to create CL CSV file."
    )


if __name__ == "__main__":
    main()
