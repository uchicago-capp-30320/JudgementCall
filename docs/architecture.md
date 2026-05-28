## Architecture

The Judgement Call project is aimed at informing voters and citizens about their judges by centralizing and synthesizing relevant information about existing judges, and candidates in judicial elections.

The project pulls data from a variety of sources to provide a centralized resource for voters in judicial elections.

### Data acquisition and pre-processing

This section describes the procces through which real data is acquired, and processed on, as it enters the database. This operation occurs in two contexts:

1. *Initial ingestion*: this is the import that takes several hours to run and produces all of the data required to use the application.
2. *Continuous ingestion:* this is an import that runs every evening, updating the database with the latest information on cases.

The summary below provides is a high-level perspective of data acquist

#### Cases & individual opinions

Our information regarding the cases, and the individual opinions of each judge on a case, is acquired through a progression of webscraping and processing through Google's large language model (LLM) Gemini.

![Case and individual opinion flow](images/Case_and_Individual_Opinions.png)

#### Judges

The information regarding judges, ranging from tenure specifics to demographics, is acquired through a process of webscraping and record linkage.

![Judge flow](images/Judges_Person.png)

#### Elections & Candidates



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

Next in the ingestion process, also rely on merging data sources and processing tables:

-   Use of LLM tools (analyze court documents and extract information) to generate case and opinion tables
    - Currently being developed in `llm_processing.ipynb`

-   Generating tenure tables
    - To be implemented

-   Generating election and candidacy tables
    - To be implemented

A final step in ingestion will centralize the generation of every table except for cases and
opinions, which are updated daily, into a single script that can be run in the command line.

#### Analysis

The analysis module will contain any functionality related to analysis of stored data, including calculation of judge similarity scores.

#### Front end

The website will create speed views using the generated tables through ingestion and back end analysis to respond to user queries on the front end.