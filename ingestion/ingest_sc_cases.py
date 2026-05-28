import curl_cffi
import lxml.html
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
import random

# This webscraping script includes random waiting times to avoid bot detection
# protections in the State Case Database website.

EXISTING_CASES_PATH = Path(__file__).parent.parent / "data" / "cases_scdb.csv"


def generate_case_id(docket_no, court, date):
    """
    This function generates a case ID that will be used as a primary key in
    our database. These IDs combine a case's docket number, court, and date.
    """
    docket_no = docket_no.replace(" ", "-")
    court = "-".join(court.split(" "))
    date = str(datetime.strptime(date, "%B %d, %Y"))[:10].replace("-", "/")
    case_id = "_".join([docket_no, court, date])

    return case_id


def make_request(url):
    """
    Function makes request to url. If the request responds with a 429 status
    code, or a Connection Error the request is made again after an iteratively-
    growing wait time. If the wait time exceeds 1 minute, the code either
    raises a Connection Error or a Runtime Error.
    """
    # Initialize wait time at 10 seconds
    wait_time = 10

    while True:
        try:
            # Redirects set to safe mode to avoid security in the request
            resp = curl_cffi.get(url, impersonate="chrome", allow_redirects="safe")

            if resp.status_code == 200:
                return resp

            elif resp.status_code == 429:
                if wait_time > 60:
                    print("Wait time larger than one minute, aborting")
                    raise RuntimeError

                print(f"Ran into 429 error, waiting for {wait_time} seconds")
                time.sleep(wait_time)
                wait_time += 1

        except curl_cffi.exceptions.ConnectionError as ce:
            if wait_time > 60:
                print("Wait time larger than one minute, aborting")
                raise ce

            print(f"Ran into connection error, waiting for {wait_time} seconds")
            time.sleep(wait_time)
            wait_time += 1


def scrape_case(case_url) -> dict:
    """
    Inputs:
    - case_url: str (the URL for a case page on SCDB)

    Output:
    - rd: dict (a dictionary containing all of the relevant case information.)

    After making the request this function parses out the following fields
    from a case:
    - case_id (string: generated from other fields)
    - docket_no (string: docket number for case)
    - title (string: title for the case)
    - state (string: the state for the case state Supreme Court)
    - date (datetime: if the case is pending then it's the date of the latest
            docuemnt, if the case is decided it's the date of the opinion)
    - type (string: category for the case, e.g., Criminal Law)
    - pending (bool: True if the case is pending, False otherwise)
    - opinion_link (string: the url to download the pdf of the opinion
                    document)

    The function returns a dictionary containing the extracted information.
    """
    url = "https://statecourtreport.org" + case_url
    root = lxml.html.fromstring(make_request(url).text)

    rd = {
        "case_id": None,
        "docket_no": None,
        "title": None,
        "state": None,
        "date": None,
        "type": None,
        "pending": None,
        "opinion_link": None,
    }

    xp1 = "//div[@class = 'field field--name-field-docket-number "
    xp2 = "field--type-string field--label-inline clearfix']"
    xp3 = "//div[@class = 'field__item']/text()"
    docket_no = root.xpath(xp1 + xp2 + xp3)[0]
    rd["docket_no"] = docket_no

    xp1 = "//div[@class = 'case-header__inner']"
    xp2 = "//div[@class = 'case-header__left']"
    xp3 = "//h1[@class = 'h1']//span/text()"
    title = root.xpath(xp1 + xp2 + xp3)[0]
    rd["title"] = title

    xp1 = "//div[@class = 'state-icon__icon-tooltip'"
    xp2 = " and @role = 'tooltip']/text()"
    state = root.xpath(xp1 + xp2)
    if state != []:
        rd["state"] = state[0].replace("\n", "").strip()

    xp1 = "//div[@class = 'field field--name-field-date "
    xp2 = "field--type-datetime field--label-inline clearfix']"
    xp3 = "//div[@class = 'field__item']//time/text()"
    date = root.xpath(xp1 + xp2 + xp3)[0]

    xp1 = "//div[@class = 'card card--opinion grid__item']"
    xp2 = "[.//li[@class = 'tags__item tags__item--opinion tags__item--' and "
    xp3 = "contains(text(), 'Opinion')]]//div[@class = 'date']//time/text()"
    opinion_date = root.xpath(xp1 + xp2 + xp3)

    if opinion_date != []:
        rd["date"] = opinion_date[0]
    else:
        rd["date"] = date

    xp1 = "//ul[@class = 'tags']//li[contains(@class, 'tags__item--primary')]"
    xp2 = "//a/text()"
    case_type = root.xpath(xp1 + xp2)
    if case_type == []:
        rd["type"] = None
    else:
        rd["type"] = case_type[0].replace("\n", "").strip()

    xp1 = "//div[@class = 'case-header__wrapper']"
    xp2 = "//div[@class = 'case-header']//ul[@class = 'tags']"
    xp3 = "//li[@class = 'tags__item tags__item--status']/text()"
    pending = root.xpath(xp1 + xp2 + xp3)
    if pending == []:
        rd["pending"] = False
    else:
        rd["pending"] = True

    xp1 = "//div[@class = 'card card--opinion grid__item']"
    xp2 = "[.//li[@class = 'tags__item tags__item--opinion tags__item--' and"
    xp3 = " contains(text(), 'Opinion')]]"
    xp4 = "//a[@class = 'card__heading__link']/@href"
    opinion_link = root.xpath(xp1 + xp2 + xp3 + xp4)
    if opinion_link != []:
        base_url = "https://statecourtreport.org"
        rd["opinion_link"] = base_url + opinion_link[0]

    rd["case_id"] = generate_case_id(rd["docket_no"], rd["state"], rd["date"])

    return rd


def page_meta_data(url):
    """
    Inputs:
    - url: str (the URL for a standard SCDB page showing multiple cases)

    Outputs:
    - pd.DataFrame() (the metadata from the cases on a page)
    - next_page_url: str (if there is a URL for the next page, it is returned
                          as a string, otherwise as None)

    This function takes a page URL for a standard SCDB page showing multiple
    cases and extracts the information from each case than can be extracted
    without going into the case page.
    """
    root = lxml.html.fromstring(make_request(url).text)

    xp1 = "//h2[@class = 'card__heading']"
    xp2 = "//a[@class = 'card__heading__link']/@href"
    case_links = root.xpath(xp1 + xp2)

    xp1 = "//div[@class = 'card card--case grid__item']"

    titles = root.xpath(xp1 + "//a[@class = 'card__heading__link']//span/text()")

    states = root.xpath(xp1 + "//div[@class = 'state-icon__icon-tooltip']/text()")
    states = [st_name.replace("\n", "").strip() for st_name in states]

    dates = root.xpath(xp1 + "//time/text()")

    case_types = []
    grid_cards = root.xpath(xp1)
    for card in grid_cards:
        query_result = card.xpath(".//a[@class = 'link'][1]/text()")
        if query_result == []:
            case_types.append(None)
        else:
            case_types.append(query_result[0].replace("\n", "").strip())

    rd = {
        "case_link": case_links,
        "case_title": titles,
        "case_state": states,
        "case_date": dates,
        "case_type": case_types,
    }

    next_url = root.xpath("//a[@class = 'pager__link pager__link--next']/@href")

    if next_url == []:
        next_page_url = None
    else:
        next_page_url = next_url[0]

    return pd.DataFrame(rd), next_page_url


def check_if_exists(
    title: str, state: str, date: str, case_type: str, existing_cases: pd.DataFrame
):
    """
    Inputs:
    - title: str (the title for a case)
    - state: str (the state for a case)
    - date: str (the date for a case)
    - type: str (a cases type as determined by SCDB)
    - existing_cases: pd.DataFrame (the existing cases in cases_scdb.csv)

    Output:
    - r_bool: bool (True if there is exists a row in the existing cases
                    that has all of the inputted characteristics)
    """
    r_bool = False

    if existing_cases is not None:
        return (
            (existing_cases["title"] == title)
            & (existing_cases["state"] == state)
            & (existing_cases["date"] == date)
            & (existing_cases["type"] == case_type)
        ).any()

    return r_bool


def scrape_page(url, rd, incremental=False, existing_cases=None, seen_cases=None):
    """
    Inputs:
    - url: str (the URL for a page displaying many cases on SCDB)
    - rd: dict (a dictionary with standard field to be added on to)
    - incremental: bool (indicator for whether a page scrape is in the context
                        of an incremental webscrape)
    - existing_cases: pd.DataFrame (set to None on default, but if not None
                                    will equal a dataframe with existing cases
                                    found inside of cases_scdb.csv)
    - seen_cases: set (a set containing tuples of cases that have been in seen
                        in a webscraping session)

    Outputs:
    - rd: dict (contains)
    - seen_cases (a set containing all of the cases that have been seen in the
                  webscraping session along with new cases that were seen on
                  the page)

    The function requests the page displaying cases, and scrapes each case on
    the page. If a webscrape is incremental it will only do so if a case's
    identifiable data from the main page is not already in cases_scdb.csv.
    """
    # Extract page metadata
    meta_data, next_page_url = page_meta_data(url)

    for index, row in meta_data.iterrows():
        case_tuple = (row["case_title"], row["case_state"], row["case_date"], row["case_type"])
        already_exists = check_if_exists(
            row["case_title"], row["case_state"], row["case_date"], row["case_type"], existing_cases
        )

        # Skip a case if it has already been recorded in previous webscrapes
        if incremental and already_exists:
            print(f"The case {row['case_title']} is already in the database.")
            continue

        # Skip a case if it has already been seen in this current run
        elif incremental and (case_tuple in seen_cases):
            print(f"The case {row['case_title']} as already been scraped.")
            continue

        wait_time = random.uniform(5, 20)
        print(f"Waiting for {round(wait_time, 1)} before scraping {row['case_title']}")
        time.sleep(wait_time)
        case_info = scrape_case(row["case_link"])

        if incremental and (seen_cases is not None):
            seen_cases.add(case_tuple)

        for field in rd.keys():
            rd[field].append(case_info[field])

    return rd, next_page_url, seen_cases


def multi_page(start_url, incremental=False, existing_cases=None):
    """
    Inputs:
    - start_url: str (the URL of the first page)
    - incremental: bool (indicator for whether a page scrape is in the context
                        of an incremental webscrape)
    - existing_cases: pd.DataFrame (set to None on default, but if not None
                                    will equal a dataframe with existing cases
                                    found inside of cases_scdb.csv)

    Output:
    - pd.DataFrame (a complete data set with all of the cases that were scraped
                    after iterating through each page)

    Given an initial page displaying cases, the function extracts the
    information for each case using the scrape_page function, it then uses
    the next_page_url to scrape the next page. Finally, the function iterates
    through every available page, extracting case information for each case,
    until there is no more available page.
    """
    url = start_url
    url_base = "https://statecourtreport.org/state-case-database"

    rd = {
        "case_id": [],
        "docket_no": [],
        "title": [],
        "state": [],
        "date": [],
        "type": [],
        "pending": [],
        "opinion_link": [],
    }

    print("Beginning webscraping of State Case Database...")
    if incremental:
        seen_cases = set()
    else:
        seen_cases = None
    page_num = 1
    while True:
        if page_num != 1:
            wait_time = random.uniform(30, 50)
            print(f"Waiting for {round(wait_time, 1)} seconds before next page scrape")
            time.sleep(wait_time)

        page_info, next_page_url, seen_cases = scrape_page(
            url, rd, incremental, existing_cases, seen_cases
        )
        print(f"Scraped page {page_num}")

        if next_page_url is None:
            print("State Case Database webscrape complete!")
            break

        if incremental:
            url = start_url + f"&page={page_num}"
        else:
            url = url_base + next_page_url

        rd = page_info
        page_num += 1

    return pd.DataFrame(rd)


def handle_duplicate_id(input_df: pd.DataFrame, series_name: str):
    """
    Inputs:
    - input_df: pd.DataFrame (the dataframe where duplicates need to be
    handled)
    - series_name: str (the name of the dataframe column that has duplicates)

    Outputs:
    - input_df: pd.DataFrame (the input dataframe except that unique values
                              in the given column are handled)

    Combinations of docket number, court, and date, are sometimes not enough
    to uniquely differentiate cases. To ensure IDs are unique before they go
    into the database, this function differentiates unique duplicate IDs by
    adding a number (e.g., 1, 2, 3).
    """
    input_df = input_df.reset_index(drop=True)
    id_series = input_df[series_name].copy()
    dupes = id_series[id_series.duplicated()]

    if not dupes.empty:
        for dupe_id in dupes.unique():
            dupe_locations = id_series[id_series == dupe_id].index.to_list()

            for attachment, index in enumerate(dupe_locations):
                if attachment != 0:
                    id_series.at[index] = dupe_id + f"_{attachment}"

    input_df[series_name] = id_series
    return input_df


def scrape_scdb(write_on=True, incremental=False):
    """
    Inputs:
    - write_on: bool (toggled on to write a .csv file with the updated cases)
    - incremental: bool (indicator for whether a page scrape is in the context
                        of an incremental webscrape)

    Outputs:
    - (case_df / full_cases): pd.DataFrame (returned if the webscrape is
                                            incremental or not)
    """
    if incremental:
        url = f"https://statecourtreport.org/state-case-database?state=All&issue=All&year={datetime.now().year}"
        existing_cases = pd.read_csv(EXISTING_CASES_PATH)
    else:
        url = "https://statecourtreport.org/state-case-database"
        existing_cases = None

    case_df = multi_page(url, incremental, existing_cases)

    # Dropping non-decided cases, and cases with no opinion documents
    pending_cases = case_df[case_df["pending"]]
    print(f"Dropped {len(pending_cases)} non-decided cases:")
    print(pending_cases)
    case_df = case_df[~case_df["pending"]]

    no_doc_cases = case_df[~case_df["opinion_link"].str.contains("https", na=False)]
    print(f"Dropped {len(no_doc_cases)} cases with missing opinion documents:")
    print(no_doc_cases)
    case_df = case_df[case_df["opinion_link"].str.contains("https", na=False)]

    # Handling duplicates and duplicate IDs
    case_df = case_df.drop_duplicates(keep="first").reset_index(drop=True)

    # Writing csv file
    path = Path(__file__).parent.parent / "data" / "cases_scdb.csv"
    if incremental:
        existing_cases = pd.read_csv(path)
        full_cases = pd.concat([case_df, existing_cases])
        full_cases = full_cases.drop_duplicates(keep="first").reset_index(drop=True)
        full_cases = handle_duplicate_id(full_cases, "case_id")
        if write_on:
            full_cases.to_csv(path, index=False)
        return full_cases
    else:
        case_df = handle_duplicate_id(case_df, "case_id")
        if write_on:
            case_df.to_csv(path, index=False)
        return case_df


if __name__ == "__main__":
    scrape_scdb()
