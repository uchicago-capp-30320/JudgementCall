"""
Script to scrape wikipedia supreme court and court of last resort pages
"""

import sys
import httpx
import lxml.html
import time
import csv
import pandas as pd
import re
from datetime import datetime, timezone

# Constants for scraping
ALLOWED_DOMAIN = "https://en.wikipedia.org/wiki/"
REQUEST_DELAY = 0.1

# For scraping - wikipedia columns that need mapping
COLUMN_MAP = {
    "Name": "name",
    "Justice": "name",
    "Born": "birth_date",
    "Start": "start_date",
    "Start date": "start_date",
    "Joined": "start_date",
    "Term ends": "end_date",
    "Mandatory retirement": "mandatory_retirement",
    "Chief term": "chief_term",
    "Chief": "chief_term",
    "Party": "ticket_party",
    "Appointer": "appointer_name",
    "Appointed by": "appointer_name",
    "Law school": "law_school",
}

# For dataframe - which columns we expect to see
EXPECTED_COLUMNS = [
    "state",
    "court",
    "name",
    "birth_date",
    "start_date",
    "end_date",
    "mandatory_retirement",
    "chief_justice",
    "chief_term",
    "ticket_party",
    "appointer_name",
    "appointer_party",
    "law_school",
    # "selection_type",
    "source_url",
    "scraped_at",
]

# States to scrape
states = [
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "Colorado",
    "Connecticut",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Michigan",
    "Minnesota",
    "Missouri",
    "Montana",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Pennsylvania",
    "Rhode Island",
    "South Dakota",
    "Texas",
    "Utah",
    "Vermont",
    "Washington",
    "Wyoming",
]


########## BASE SCRAPER ##########


def make_link_absolute(path):
    """
    Given a relative URL like "/abc/def" adds allowed_domin
    """

    return ALLOWED_DOMAIN + path


def make_request(url):
    """
    Make a request to `url` and return the raw response.

    This function ensure that the domain matches what is expected
    and that the rate limit is obeyed.
    """

    # check if URL starts with an allowed domain name
    for domain in ALLOWED_DOMAIN:
        if url.startswith(domain):
            break
    else:
        # note: this else is indented correctly, it is a less-commonly used
        # for-else statement.  the condition is only met if the for loop
        # *never* breaks, i.e. no domains match
        raise ValueError(f"can not fetch {url}, must be in {ALLOWED_DOMAIN}")
    time.sleep(REQUEST_DELAY)
    print(f"Fetching {url}")

    # https://www.scraperapi.com/blog/headers-and-cookies-for-web-scraping/
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.47"
        )
    }

    resp = httpx.get(url, headers=headers)
    resp.raise_for_status()
    return resp


def get_parse_html(url):
    """
    Return the HTML for a given website.
    """

    resp = make_request(url)
    html = resp.text
    root = lxml.html.fromstring(html)

    return root


def scrape_page(root, state, url, scraped_at):
    """
    Given the html text of a page, extract the info from the table of judges.
    """

    # Get name of court
    page_title = root.cssselect("title")[0].text_content().strip()
    page_title = page_title.replace(" - Wikipedia", "")

    # Get the entire table, headers (th) and data (td)
    table = root.cssselect("table.wikitable.sortable tbody")[0]

    # Extract just the header values
    header_row = table.cssselect("tr th")
    header = []
    for th in header_row:
        text = th.text_content().strip()
        header.append(text)

    # Make a data column for state and court name
    header.append("state")
    header.append("court")
    header.append("source_url")
    header.append("scraped_at")

    # Extract the table data
    rows = []
    for tr in table.cssselect("tr"):
        cells = tr.cssselect("td")
        if not cells:
            continue  # skip the header row

        row = []
        for td in cells:
            ## need to handle merged cell
            text = td.text_content().strip()

            # detect colspan
            colspan = td.get("colspan")
            if colspan is None:
                colspan = 1
            else:
                colspan = int(colspan)

            # append the value colspan times
            for _ in range(colspan):
                row.append(text)

        # Add given state for each row
        row.append(state)
        row.append(page_title)
        row.append(url)
        row.append(scraped_at)

        rows.append(row)

    return header, rows


def run_scraper(state, path):
    url = make_link_absolute(path)
    scraped_at = datetime.now(timezone.utc).isoformat()  # UTC ISO timestamp
    root = get_parse_html(url)
    return scrape_page(root, state, url, scraped_at)


########## CLEANING/EXTRACTION OF SCRAPED DATA ##########


def extract_name_and_chief_status(raw_name, seat_value=None):
    # Normalize raw_name
    if raw_name is None:
        return None, False

    if not isinstance(raw_name, str):
        raw_name = str(raw_name)

    name = raw_name.strip()
    name_lower = name.lower()

    # Handle vacancies
    if name_lower == "vacant":
        return None, False

    # Detect chief justice from name
    is_chief_from_name = "chief justice" in name_lower

    # Detect vice chief justice (should not count as chief justice)
    is_vice_chief = "vice chief justice" in name_lower

    # Detect associate chief justice (should not count as chief justice)
    is_associate_chief = "associate chief justice" in name_lower

    # Detect chief justice from seat/position column
    is_chief_from_seat = False
    if seat_value:
        seat_lower = str(seat_value).lower()
        is_chief_from_seat = "chief justice" in seat_lower

    # Combine rules
    is_chief = (
        is_chief_from_name and not (is_vice_chief or is_associate_chief)
    ) or is_chief_from_seat

    # Clean name
    cleaned = (
        name.replace("Vice Chief Justice", "")
        .replace("Associate Chief Justice", "")
        .replace("Chief Justice", "")
        .replace("Presiding Justice", "")
        .replace("Presiding Judge", "")
        .replace("Senior Associate Justice", "")
        .replace(",", "")
        .strip()
    )

    return cleaned, is_chief


def split_appointer(value):
    if not isinstance(value, str) or value.strip() == "":
        return None, None

    # Match patterns like "Ron DeSantis (R)"
    match = re.match(r"^(.*?)\s*\((.*?)\)$", value.strip())
    if match:
        name = match.group(1).strip()
        party = match.group(2).strip()
        return name, party

    # If no party is present
    return value.strip(), None


def clean_cell(value):
    if not isinstance(value, str):
        return value

    # Remove CSS stuff like ".mw-parser-output ..."
    value = re.sub(r"\.mw-parser-output.*", "", value)

    # Remove bracketed footnotes [a], [19], [citation needed]
    value = re.sub(r"\[[^\]]*\]", "", value)

    # Remove age, ex. (age 68), (age 62–63), (age 62-63)
    value = re.sub(r"\(age[^)]*\)", "", value, flags=re.IGNORECASE)

    # Remove hidden birthdate, ex. (1963-04-26)
    value = re.sub(r"\(\d{4}-\d{2}-\d{2}\)", "", value)

    # Normalize whitespace
    value = value.strip()

    # Normalize placeholders
    if value in {"", "-", "–", "—", "N/a", "n/a", "NA", "—N/a", "—N/A"}:
        return None

    return value


def normalize_df(df, state, path):
    # Standardize column names
    df = df.rename(columns=COLUMN_MAP)

    # Make sure expected columns exist
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Clean name and detect chief justice status
    df["person_clean"], df["chief_justice"] = zip(
        *df.apply(
            lambda row: extract_name_and_chief_status(
                raw_name=row.get("name"), seat_value=row.get("Seat") or row.get("Position")
            ),
            axis=1,
        )
    )

    # Remove vacancies
    df = df[df["person_clean"].notna()]

    # Replace person column with cleaned version
    df["name"] = df["person_clean"]
    df = df.drop(columns=["person_clean"])

    # Extract appointer name and party
    df["appointer_name"], df["appointer_party"] = zip(*df["appointer_name"].apply(split_appointer))

    # Return df for Tenure and Person table creation
    return df[
        [
            "state",
            "court",
            "name",
            "birth_date",
            "start_date",
            "end_date",
            "mandatory_retirement",
            "chief_justice",
            "chief_term",
            "ticket_party",
            "appointer_name",
            "appointer_party",
            "law_school",
            # "selection_type",
            "source_url",
            "scraped_at",
        ]
    ]


########## RUNNING SCRAPER ##########
def make_path(state):
    fix = state.replace(" ", "_")
    return f"{fix}_Supreme_Court"


def main():
    states_to_scrape = {state: [make_path(state)] for state in states}

    states_to_scrape["Georgia"] = ["Supreme_Court_of_Georgia_(U.S._state)"]

    states_to_scrape["Texas"] = ["Supreme_Court_of_Texas", "Texas_Court_of_Criminal_Appeals"]

    all_dfs = []

    for state, paths in states_to_scrape.items():
        for path in paths:
            header, rows = run_scraper(state, path)

            # Clean cells
            header = [clean_cell(h) for h in header]
            cleaned_rows = [[clean_cell(cell) for cell in row] for row in rows]

            # Clean/extract data
            df = pd.DataFrame(cleaned_rows, columns=header)
            normalized = normalize_df(df, state, path)

            # Save all to aggregated df
            all_dfs.append(normalized)

    big_df = pd.concat(all_dfs, ignore_index=True)

    big_df.to_csv("wikipedia.csv", index=False)


if __name__ == "__main__":
    main()
