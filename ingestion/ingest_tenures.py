import sys
import httpx
import lxml.html
import time
import csv
import pandas as pd

# 122 pa3
ALLOWED_DOMAIN = "https://en.wikipedia.org/wiki/"


def make_link_absolute(path):
    """
    Given a relative URL like "/abc/def" or "?page=2"
    and a complete URL like "https://example.com/1/2/3" this function will
    combine the two yielding a URL like "https://example.com/abc/def"

    Parameters:
        * rel_url:      a URL or fragment
        * current_url:  a complete URL used to make the request that
                        contained a link to rel_url

    Returns:
        A full URL with protocol & domain that refers to rel_url.
    """

    return ALLOWED_DOMAIN + path


# 122 pa3
REQUEST_DELAY = 0.1


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


# 122 web scrpaing lab
def get_parse_html(url):
    """
    Return the HTML for a given committee from the FEC website.
    """

    resp = make_request(url)
    html = resp.text
    root = lxml.html.fromstring(html)

    return root


def scrape_page(root, state):
    """
    Given the html text of a page, extract the info from the table of judges.
    """

    # Get the entire table, headers (th) and data (td)
    table = root.cssselect("table.wikitable.sortable tbody")[0]

    # Extract just the header values
    header_row = table.cssselect("tr th")
    header = []
    for th in header_row:
        text = th.text_content().strip()
        header.append(text)

    # Make a data column for state
    header.append("State")

    # Extract the table data
    rows = []
    for tr in table.cssselect("tr"):
        cells = tr.cssselect("td")
        if not cells:
            continue  # skip the header row

        row = []
        for td in cells:
            row.append(td.text_content().strip())

        # Add given state for each row
        row.append(state)

        rows.append(row)

    return header, rows


def run_scraper(state, path):
    url = make_link_absolute(path)
    root = get_parse_html(url)
    return scrape_page(root, state)


def make_path(state):
    fix = state.replace(" ", "_")
    return f"{fix}_Supreme_Court"


def main():
    all_dfs = []
    states_to_scrape = ["Alaska", "Wisconsin", "Texas"]

    for state in states_to_scrape:
        header, rows = run_scraper(state, make_path(state))
        df = pd.DataFrame(rows, columns=header)
        all_dfs.append(df)

    big_df = pd.concat(all_dfs, ignore_index=True)
    print(big_df.head())


if __name__ == "__main__":
    main()
