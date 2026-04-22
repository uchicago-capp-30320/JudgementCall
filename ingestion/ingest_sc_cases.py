import requests
import lxml.html
import time
import pandas as pd


def make_request(url: str):
    """
    Makes a request to the given url. If the request returns a 429 status code,
    the function waits 2.5 seconds and then repeats the request.
    """
    resp = requests.get(url)

    if resp.status_code == 429:
        time.sleep(2.5)
        resp = make_request(url)
    elif resp.status_code == 200:
        return resp


def scrape_case(case_url):
    """
    Given a partial url for a case, this function completes the url then
    makes a request on the completed url. It uses lxml.html to extract the
    following fields from a case:
    - docket_no (string: docket number for case)
    - title (string: title for the case)
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
        "docket_no": None,
        "title": None,
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

    return rd


def scrape_page(url, rd):
    """
    Function takes the url for a page, and a return dictionary with the
    structure:

    rd = {
        "docket_no": [],
        "title": [],
        "date": [],
        "type": [],
        "pending": [],
        "opinion_link": []
    }

    With the given url, the function requests the page displaying cases. It
    uses lxml.html to extract the url for each case displayed on the page. With
    each case url, it uses the scrape_case function to extract the case
    information. Iterating through each displayed case, the function returns
    a dictionary of lists containing the information for the cases.
    """
    root = lxml.html.fromstring(make_request(url).text)

    xp1 = "//h2[@class = 'card__heading']"
    xp2 = "//a[@class = 'card__heading__link']/@href"
    case_links = root.xpath(xp1 + xp2)

    for link in case_links:
        case_info = scrape_case(link)

        for field in rd.keys():
            rd[field].append(case_info[field])

    return rd


def next_page_url(url):
    """
    Given a url for a page displaying cases, it extracts the link to the next
    page. If there is no next page, it returns an empty string.
    """
    root = lxml.html.fromstring(make_request(url).text)

    rl = root.xpath("//a[@class = 'pager__link pager__link--next']/@href")

    if rl == []:
        return ""
    else:
        return rl[0]


def multi_page(start_url):
    """
    Given an initial page displaying cases, the function extracts the
    information for each case using the scrape_page function, it then uses
    the next_page_url function to extract the url for the next page. Finally,
    the function iterates through every available page, extracting case
    information for each case, until there is no more available page.
    """
    url = start_url
    url_base = "https://statecourtreport.org/state-case-database"

    rd = {"docket_no": [], "title": [], "date": [], "type": [], "pending": [], "opinion_link": []}

    while True:
        page_info = scrape_page(url, rd)

        url = url_base + next_page_url(url)
        rd = page_info

        if url == url_base:
            break

    return rd


def scrape_main(url):
    """
    Given the base url for State Search Database the function requests the url
    and uses lxml.html to extract the names and the codes for every case.
    It then generates an initial for each state using the state codes, and
    extracts all of the case information for each case's supreme court. At the
    end it returns a dictionary:

    rd = {
        "docket_no": [],
        "state": [],
        "title": [],
        "date": [],
        "type": [],
        "pending": [],
        "opinion_link": []
    }

    It is essentially the same data format as each case, except it adds a
    'state' field.
    """
    root = lxml.html.fromstring(make_request(url).text)
    url_base = "https://statecourtreport.org/state-case-database"

    xp1 = "//select[@id = 'edit-state']"
    xp2 = "//option[not(contains(@value, 'All'))]/@value"
    state_nos = root.xpath(xp1 + xp2)

    xp2 = "//option[not(contains(@value, 'All'))]/text()"
    state_names = root.xpath(xp1 + xp2)

    rd = {
        "docket_no": [],
        "state": [],
        "title": [],
        "date": [],
        "type": [],
        "pending": [],
        "opinion_link": [],
    }

    for i, state_code in enumerate(state_nos):
        length = 0
        state_url = url_base + f"?state={state_code}&issue=All&year=All"
        state_info = multi_page(state_url)

        for field in rd.keys():
            if field == "state":
                continue
            else:
                rd[field] += state_info[field]
                length = len(state_info[field])

        rd["state"] += [state_names[i]] * length

    return rd


cases_pd = scrape_main("https://statecourtreport.org/state-case-database")

case_df = pd.DataFrame(cases_pd)
case_df = case_df[not case_df["pending"]]
case_df = case_df.drop_duplicates().reset_index(drop=True)
