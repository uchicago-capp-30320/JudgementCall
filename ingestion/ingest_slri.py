import lxml.html
import curl_cffi
import time
import uuid
import pandas as pd
from tqdm import tqdm
from pathlib import Path

# Path for data
# Directory of the current script (ingestion/)
BASE_DIR = Path(__file__).resolve().parent

# Path to the data/ folder and make sure it exists
DATA_DIR = BASE_DIR.parent / "data" / "judges"
DATA_DIR.mkdir(exist_ok=True)

# Final CSV path
OUTPUT_CSV = DATA_DIR / "slri.csv"


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


def scrape_judge(url: str):
    """
    This function takese the url for a individual judge's page on SLRI and
    extracts items from the about list like the gender, party, race, etc.
    Returns a dictionary where each key, value, pair is an item's name, and its
    corresponding value.
    """
    j_page = lxml.html.fromstring(make_request(url).text)
    r_d = {}

    xp1 = "//div[@class = 'judge-info']//div[@class = 'about-list']"
    xp2 = "//div[@class = 'about-list-item']//h3/text()"
    item_titles = j_page.xpath(xp1 + xp2)

    xp1 = "//div[@class = 'judge-info']//div[@class = 'about-list']"
    xp2 = "//div[@class = 'about-list-item']//p/text()"
    items = j_page.xpath(xp1 + xp2)

    for i, title in enumerate(item_titles):
        r_d[title.lower()] = items[i].replace("\t", "").strip().lower()

    return r_d


def scrape_main(url: str) -> pd.DataFrame:
    """
    Function takes the url for the SLRI page on state justices and iterates
    through each judge page, iteratively building a pandas dataframe where
    each field is a judge item and each row is a judge.
    """
    main_page = lxml.html.fromstring(make_request(url).text)

    # Extract judge links to iterate through
    xp1 = "//section[@filter = 'judge']//"
    xp2 = "a[contains(@href, 'judge')]//@href"
    judge_links = main_page.xpath(xp1 + xp2)

    xp1 = "//section[@filter = 'judge']//a[contains(@href, 'judge')]//"
    xp2 = "div[@class = 'module--content module--content-post']"
    xp3 = "//h2[@class = 'title']/text()"
    judge_names = main_page.xpath(xp1 + xp2 + xp3)

    xp1 = "//div[@class = 'about-icons']"
    xp2 = "//div[@class = 'about-icon' and @data-type = 'state']"
    xp3 = "//span[not(contains(@class, 'sr-only'))]/text()"
    judge_states = main_page.xpath(xp1 + xp2 + xp3)

    judge_fields = [
        "gender",
        "party",
        "race",
        "professional experience",
        "election type",
        "term start",
        "term end",
        "next election date",
    ]

    judge_pd = {"JID": [], "name": [], "state": []}

    for field in judge_fields:
        judge_pd[field] = []

    # Iterating through judges and populating dictionary
    for i, name in tqdm(enumerate(judge_names)):
        judge_pd["name"].append(name)
        judge_pd["JID"].append(uuid.uuid4())
        judge_pd["state"].append(judge_states[i])

        judge_dic = scrape_judge(judge_links[i])

        if judge_dic == {}:
            break

        for field in judge_fields:
            if field not in judge_dic:
                data = pd.NA
            else:
                data = judge_dic[field]

            judge_pd[field].append(data)

    return pd.DataFrame(judge_pd)


if __name__ == "__main__":
    url = "https://state-law-research.org/state-justices/"
    judge_pd = scrape_main(url)
    judge_pd.to_csv(OUTPUT_CSV)
