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
from pathlib import Path

# Path for data
# Directory of the current script (ingestion/)
BASE_DIR = Path(__file__).resolve().parent

# Path to the data/ folder and make sure it exists
DATA_DIR = BASE_DIR.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Final CSV path
OUTPUT_CSV = DATA_DIR / "wikipedia.csv"

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
    "Term Ends": "end_date",
    "Mandatory retirement": "mandatory_retirement",
    "Chief term": "chief_term",
    "Chief": "chief_term",
    "Party": "ticket_party",
    "Appointer": "appointer_name",
    "Appointed by": "appointer_name",
    "Law school": "law_school",
    "Law School": "law_school",
}

# For scraping - choosing correct Wikipedia table
REQUIRED_ANY = ["start", "start date", "joined"]
REQUIRED_ALL = ["law school"]

FORBIDDEN = [
    "vacator",
    "reason",
    "vacancy date",
    "replacing",
    "image",
    "active retirement",
    "active start",
    "active end",
]

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
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Washington",
    "West Virginia",
    "Wisconsin",
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


def clean_header(text):
    text = text.lower().strip()
    text = re.sub(r"\[[^\]]*\]", "", text)  # remove footnotes [a], [1], etc.
    text = text.replace("–", "-")
    text = " ".join(text.split())
    return text


def is_correct_table(table):
    # Extract and clean headers
    headers = [clean_header(th.text_content()) for th in table.cssselect("tr th")]

    header_text = " ".join(headers)

    # Must contain at least one of REQUIRED_ANY
    if not any(req in header_text for req in REQUIRED_ANY):
        return False

    # Must contain all REQUIRED_ALL
    if not all(req in header_text for req in REQUIRED_ALL):
        return False

    # Must NOT contain any forbidden keyword
    if any(bad in header_text for bad in FORBIDDEN):
        return False

    return True


def scrape_page(root, state, url, scraped_at):
    """
    Given the html text of a page, extract the info from the table of judges.
    """

    # Get name of court
    page_title = root.cssselect("title")[0].text_content().strip()
    page_title = page_title.replace(" - Wikipedia", "")

    # Get the entire table, headers (th) and data (td)
    # May be multiple tables depending on page
    tables = root.cssselect("table.wikitable.sortable tbody")

    table = None
    for t in tables:
        if is_correct_table(t):
            table = t
            break

    if table is None:
        raise ValueError(f"No matching table found for {url}")

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


def extract_name_and_chief_status(raw_name, seat_value=None, position_value=None):
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

    # Find chief justice from name
    is_chief_from_name = "chief justice" in name_lower

    # Find titles with chief justice but should not count as chief justice
    is_vice_chief = "vice chief justice" in name_lower
    is_associate_chief = "associate chief justice" in name_lower
    is_deputy_chief = "deputy chief justice" in name_lower

    # Find chief justice from seat/position column
    is_chief_from_seat = False
    for val in (seat_value, position_value):
        if val:
            lower = str(val).lower()
            if "chief justice" in lower:
                is_chief_from_seat = True
                break

    # Combine rules
    is_chief = (
        is_chief_from_name and not (is_vice_chief or is_associate_chief or is_deputy_chief)
    ) or is_chief_from_seat

    # Clean name
    cleaned = (
        name.replace("Vice Chief Justice", "")
        .replace("Associate Chief Justice", "")
        .replace("Deputy Chief Justice", "")
        .replace("Chief Justice", "")
        .replace("Presiding Justice", "")
        .replace("Vice Presiding Judge", "")
        .replace("Presiding Judge", "")
        .replace("Senior Associate Justice", "")
        .replace("Justice pro tempore", "")
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
    df["name_clean"], df["chief_justice"] = zip(
        *df.apply(
            lambda row: extract_name_and_chief_status(
                raw_name=row.get("name"),
                seat_value=row.get("Seat"),
                position_value=row.get("Position"),
            ),
            axis=1,
        )
    )

    # Remove vacancies
    df = df[df["name_clean"].notna()]

    # Replace person column with cleaned version
    df["name"] = df["name_clean"]
    df = df.drop(columns=["name_clean"])

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

    # Adding in states with slightly different urls
    states_to_scrape["Georgia"] = ["Supreme_Court_of_Georgia_(U.S._state)"]
    states_to_scrape["Maine"] = ["Maine_Supreme_Judicial_Court"]
    states_to_scrape["Texas"] = ["Supreme_Court_of_Texas", "Texas_Court_of_Criminal_Appeals"]
    states_to_scrape["Massachusetts"] = ["Massachusetts_Supreme_Judicial_Court"]
    states_to_scrape["New York"] = ["New_York_Court_of_Appeals"]
    states_to_scrape["Oklahoma"] = ["Oklahoma_Supreme_Court", "Oklahoma_Court_of_Criminal_Appeals"]
    states_to_scrape["West Virginia"] = ["Supreme_Court_of_Appeals_of_West_Virginia"]

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

    big_df.to_csv(OUTPUT_CSV, index=False)


if __name__ == "__main__":
    main()
