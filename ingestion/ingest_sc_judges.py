import lxml.html
import requests
import time
import uuid
import pandas as pd


def make_request(url):
    """
    Function makes request to url. If the request responds with a 429 status
    code, the request is made again after 2.5 seconds until. The process
    repeats until the response responds with a 200 code.
    """
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    acc = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    headers = {
        "User-Agent": user_agent,
        "Accept": acc,
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    resp = requests.get(url, headers=headers)

    if resp.status_code == 429:
        time.sleep(2.5)
        resp = make_request(url)
    elif resp.status_code == 200:
        return resp


def scrape_judge(url):
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


def scrape_main(url):
    main_page = lxml.html.fromstring(make_request(url).text)

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

    for i, name in enumerate(judge_names):
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


url = "https://state-law-research.org/state-justices/"

judge_pd = scrape_main(url)
