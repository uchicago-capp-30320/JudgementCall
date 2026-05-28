# Judgement Call

**MISSION: SUPPORT INFORMED VOTING IN U.S. JUDICIAL ELECTIONS.**

State Supreme Court Justices are elected by popular vote in 21 states in the U.S., but it can be difficult for voters to evaluate candidates' qualifications and understand how they align with their values. Judicial selection methods also vary by state and court, making voter education in judicial elections even more challenging. Local organizations do incredible work to help inform voters – but because of the varied nature of judicial elections, not all voters have access to the same level of information.

Judgement Call aims to provide voters with the information they need to make informed decisions in judicial elections. We pull data from a variety of sources to provide a centralized resource for information on current state court judges and candidates for election. We also provide head-to-head comparisons and court level analysis to help you understand how judges in your state rule on the issues you care about.

## Application Overview

**Judge Lookup Page**:
Users can enter their state and county to see every judge who serves their jurisdiction. Each judge’s page includes basic demographic information as well as the cases they have presided over and how they ruled, helping people understand patterns in specific judges' decision‑making.

The judge lookup page also provides access to a court-level page, where users can get a better sense of the court as a whole: how long judges have been on the court and how similar rulings between judges are.

**Elections Page**:
The elections page lists upcoming elections in the user's jurisdiction, as well as candidates who are running for seats in those elections. The user can access basic party affiliation information on judicial candidates, as well as other demogrpahic information, if available. If the candidate is already a judge and running for re-election, users will be provided with the same information on cases they have presided over and how they ruled, as given during the judge lookup.

**Analytics Page**:
The analytics page zooms out to show broader trends across judges and courts. It highlights patterns in case types and judicial behavior across regions, giving more data‑interested users a view of how the system is functioning overall.

## Application Access

### Website
Please visit https://judgementcall.civic.garden/.

### Local Access
1. Add the repository to your local machine with `git clone`.
2. This repository utilizes uv to manage packages - run `uv sync` after the repository is added to your local machine.
3. Follow the directions in `docs/djangoguide.md` to obtain all relevant data and to re-ingest data if necessary.
4. Generate the website with `uv run python manage.py runserver` and follow the link given in the console.

_Please note that this data will not be as up-to-date as that provided by the website._

## File System Layout
- `analysis` - Scripts to generate analysis page figures and explorative visualizations.
- `apps/` - Parent directory for project apps.
- `apps/judgement-call/` - The main Judgement Call app directory. Contains the data models, views and tests for the web app.
- `apps/accounts/` - An app that defines the DJOK custom user model, compatible with `allauth` and `django.contrib.admin`.
- `config/` - Config directory for the Django project.
- `data/` - Data directory.
- `docs/` - Documentation on the architecture, endpoints, Django models, and Django app setup.
- `ingestion/` - Backend data ingestion functions to populate the project database.
- `static/` - Static CSS, images and JS files.
- `templates/` - Django frontend templates.
- `utils/` - Shared utility functions used across data processing scripts.

## Methodology

### Data Sources
Judgement Call aggregates information from multiple public and nonprofit sources.
- [CourtListener](https://www.courtlistener.com/) - for existing court data
- [State Case Database](https://statecourtreport.org/state-case-database) (State Court Report) - for state supreme court cases and decisions
- [State Law Research Initiative](https://state-law-research.org/state-justices/) (SLRI) - for judge demogrpahic information
- [Wikipedia](https://en.wikipedia.org/wiki/State_supreme_courts_in_the_United_States) - for biographical and tenure data
- [Ballotpedia](https://ballotpedia.org/State_judicial_elections,_2026) - for initial election lists

Because no single authoritative source exists for all state‑level judicial information, our system merges data across sources and fills gaps where possible.

### Data Ingestion and Processing

#### Case and Opinion Data
- Daily ingestion from State Case Database
- Identification of new cases and participating judges
- Use of LLM tools to extract:
    - Case topics
    - Case arguments, decisions, and court opinion
    - Rights implicated during cases
    - Individual judge opinions
    - Whether a judge concurred with or dissented from a court opinion

#### Tenure and Person Data
- Continous ingestion of SLRI and Wikipedia
- Identification of participating judges from case ingestion
- Identification of candidates from election ingestion

#### Court Data
- CourtListener as a source for court identities
- One-time ingestion of courts, court selection methods, and bench sizes

#### Election & Candidacy Data
- No authoritative national source exists
- We infer upcoming elections using:
    - Tenure end dates
    - Court selection methods
- Initial candidate lists sourced from Ballotpedia
- Manual verification where possible

### Analytical Framework
Judgement Call includes interpretive assessments of judicial behavior, including whether a judge’s decisions tend to protect or infringe individual rights. These assessments are generated through:
- Topic classification of cases by LLM
- Extraction of rights implicated by LLM
- Identification of judge‑specific opinions by LLM
- Internal scoring calculations that summarize right-protection/infringment tendencies

## Limitations and Disclaimers

### Data Completeness
- Some states publish limited or inconsistent judicial data
- No one judicial information site is wholly up-to-date and all-encompassing of necessary data
- Candidate information may be incomplete or unavailable

### Interpretation
- Rights‑based assessments are our own analytical judgments
- They are not official statements of any court or government entity
- Nothing on this site should be interpreted as:
    - A definitive statement of a judge’s legal philosophy
    - A substitute for official court records

Although we strive for accuracy, these limitations apply. Users should verify information independently before relying on this site.

## Team
- Riley Morrison
- Maggie Larson
- Liberto de Pablo
- Riley Kouns
- Callie Leone
- Alexandrea Harriott

## Attribution

Django project template: https://codeberg.org/jpt/djok

Radar chart for D3 v4+: Nadieh Bremer | Visual Cinnamon, updated by Ingo Kleiber