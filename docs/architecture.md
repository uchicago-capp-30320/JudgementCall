## Architecture

The Judgement Call project is aimed at informing voters about their judges by centralizing and synthesizing relevant information about existing judges, and candidates in judicial elections.

The project pulls data from a variety of sources to provide a centralized resource for voters in judicial elections. Our primary source for continuous data ingestion source is [CourtListener](https://www.courtlistener.com/), a legal research resource provided by [Free Law Project](https://free.law/).

### Data flow

Flow chart: https://canva.link/pjkpe01xag0fime

Some tables contain long-lived data, i.e. existing state courts, and will be constructed once and updated rarely. Tenure and person tables will be updated to fill in missing data and as a result of new elections and appointment. The primary flow of information through the project will be case and opinion data, which will be updated daily.

The flow of case and opinion data will be approximately:
Daily case scraper -> identify new cases -> match judges to existing tenure records -> use LLM to parse topic & individual judge opinions -> create case and opinion records

Our main educational page and “who are my judges?” page will query the tables directly to populate the views with data. The analysis page will both pull information directly from the tables, and will make calls to functions in the analysis module.

### Modules

#### Ingestion

The ingestion module contains both one-off scrapers used to create our long-lived datasets and continuous ingestion scrapers which (will) run nightly to update our case and opinion data.

- Case / Opinion
    -	CourtListener
    -	[State Case Database](https://statecourtreport.org/state-case-database)
        - `ingest_sc_cases.py` - daily ingestion

- Tenure / Person
    -	Wikipedia
        - to be implemented
    -	Ballotpedia
        - to be implemented
    -   [State Law Research Initiative](https://state-law-research.org/state-justices/)
        - `ingest_sc_judges.py` - low-frequency ingestion

- Court
    -   CourtListener: authoritative source for existing state level courts
    -   [Web archive of National Center for State Courts](http://web.archive.org/web/20211129172422/http://judicialselection.us/judicial_selection/methods/selection_of_judges.cfm?state="): one-off ingestion of court type, bench size, selection and retention methods
        - `ingest_courts_data.py`
        - `merge_courts_data.py`
    - Authoritative source: state constitutions

- Election / Candidacy
    -   There is no authoritative source on all state court elections; we can "guess" from tenure end dates and selection methods which courts have upcoming elections, and manually verify
    -   As a starting point, we have a list of upcoming elections sourced from Ballotpedia

Ingestion will also rely on merging data sources and processing tables:

-   Use of LLM tools (analyze court documents and extract information) to generate case and opinion tables
    - Currently being developed in `llm_processing.ipynb`

-   Generating tenure tables
    - To be implemented

-   Generating election and candidacy tables
    - To be implemented

#### Analysis

The analysis module will contain any functionality related to analysis of stored data, including calculation of judge similarity scores.

#### Front end

The website will create speed views using the generated tables through ingestion and back end analysis to respond to user queries on the front end.