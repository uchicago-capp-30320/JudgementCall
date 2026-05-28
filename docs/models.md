This is a guide (data dictionary) to JudgementCall's data tables.

**Legend**
* PK: Primary key
* FK: Foreign key
* R: Required attribute, cannot be null in a record (assumed for PK and FK)
* enumerated: Limited to the values listed in "Description"

The tables are as follows.
- [Court](#court)
- [CountyToCourt](#countytocourt)
- [Tenure](#tenure)
- [Person](#person)
- [Election](#election)
- [Candidacy](#candidacy)
- [Alias](#alias)
- [CaseProcessingRun](#caseprocessingrun)
- [Case](#case)
- [IndividualOpinion](#individualopinion)

# Court

This contains the current, mostly immutable characteristics of each Court in the US. The table *does not* account for or track historic changes to court structure (e.g. a Constitutional Initiative changes Montana State Supreme Court elections from non-partisan to partisan.) Historic changes such as these are few and far between, enough so that they can be addressed *ad hoc* between election cycles.

NB: Attributes from `initial_term_length` up to and including `notes` will be mostly, if not entirely, empty in the initial 10-week development period of this project. These attributes are maintained in anticipation of many exceptions and nuances across geographies, court levels, and changes to state constitutions over time.

| Name                           | Type                   | Description                                                                                                          |
|--------------------------------|------------------------|----------------------------------------------------------------------------------------------------------------------|
| id                             | Int (PK)               | Default auto-incremented integer identifier                                                                          |
| court_id                       | String (R)             | Abbreviated unique court identifier from CourtListener                                                               |
| name                           | String (R)             | Full, readable name of court                                                                                         |
| court_level                    | String (enumerated)    | Jurisdiction level of court, in descending order of authority: `Supreme Court`, `Appellate Court`, and `Lower Court` |
| court_type                     | String (R)             | More detailed court-level info, such as distinguishing between Texas' criminal and civil supreme courts              |
| bench_size                     | Int                    | Number of judges sitting on this court, by law                                                                       |
| selection_type                 | String (R, enumerated) | How judges get into this court: `partisan election`, `nonpartisan election`, `appointment`, `elected by legislature` |
| selection_method               | String                 | Details on how this court's `selection_type` is implemented (e.g. part by partisan election, part by retention)      |
| selection_jurisdiction         | String (enumerated)    | Geographic division of court: `statewide`, `district`, `circuit`                                                     |
| term_length                    | Int                    | Number of years a judge serves in a full term on this court, by law                                                  |
| initial_term_length            | String                 | Length of term in years for a judge's first election to this court                                                   |
| retention_method               | String                 | Details on implementation of retention method, if relevant                                                           |
| subsequent_term_length         | String                 | Length of term in years for a judge's election to this court after their initial term                                |
| interim_selection_method       | String                 | How seat vacancies are filled in this court                                                                          |
| interim_term_length            | String                 | Length of term in years for interrim judicial selections / appointments                                              |
| chief_justice_selection_method | String                 | If different from other judges, selection method for chief justice                                                   |
| chief_justice_term_length      | String                 | If different from other judges, term length of chief justice                                                         |
| qualifications                 | String                 | Additional, miscellaneous requirements for membership on this court                                                  |
| constitutional_reference       | String                 | Reference or citation to passage in this court's state constitution that defines the court                           |
| notes                          | String                 | Any final nuances of this court not detailed by other attributes                                                     |
| url                            | String (URL)           | Link to this court's official website                                                                                |

# CountyToCourt

This contains the many-to-many crosswalk relation between counties and courts. Every county belongs to a particular Supreme Court and many other lower courts. Each court at any level has jurisdiction in many counties.

| Name   | Type             | Description                                                                               |
|--------|------------------|-------------------------------------------------------------------------------------------|
| id     | Int (PK)         | Default auto-incremented integer identifier                                               |
| court  | String (R)       | Abbreviated court name identifier, as in [Court](#court).                                 |
| state  | USStateField (R) | `django-localflavor` form field, validated against known US state names and abbreviations |
| county | String (R)       | Full county name, formatted as "<COUNTY NAME> County, <STATE NAME> for disambiguation     |
| fips   | String (R)       | 5-digit string, where first 2 digits identify state and last 3 digits identify county     |

# Tenure

This contains information on individual tenures, or "judgeships." A Tenure is considered a particular instance of a Person holding office as a judge on a Court. A Person can hold office in many courts throughout their career, and they can be a candidate in an Election despite having never having a Tenure (i.e. never having held judicial office). Hence, Tenure and Person are modeled as separate tables.

Note that `start_date` is the only required date, as some Tenures are historical (completed) and others are current (no `end_date` yet).

| Name            | Type                   | Description                                                                                  |
|-----------------|------------------------|----------------------------------------------------------------------------------------------|
| id              | Int (PK)               | Default auto-incremented integer identifier                                                  |
| court           | String (FK Court)      | Court at which the person who held this Tenure served                                        |
| person          | Int (FK Person)        | Person who held this Tenure                                                                  |
| start_date      | Date (R)               | Date on which this Tenure took office                                                        |
| end_date        | Date                   | Date of: retirement, end of term, removal, death in office, etc.                             |
| selection_type  | String (R, enumerated) | As in [Court](#court), but specific to selection types at the time of this Tenure's election |
| ticket_party    | String (enumerated)    | Political affiliation: `republican`, `democrat`, `independent`, `other`, `unknown`           |
| appointer_name  | String                 | Name of Person who appointed this Tenure to office                                           |
| appointer_party | String (enumerated)    | Political affiliation of appointer, as in `ticket_party`                                     |
| chief_justice   | Boolean (R)            | `True` if this Tenure is the Chief Justice of their Court                                    |
| source_url      | String (URL)           | URL from which this Tenure's data was web-scraped                                            |
| scraped_at      | DateTime               | Date of retrieval for this web-scraped Tenure data                                           |

# Person

This contains (mostly) immutable characteristics of a Person, whether they are a judge or not. A Person's `party_registration` reflects their current party affiliation as a voter, so it does not necessarily match every `ticket_party` record in their Tenure or Candidate histories.

| Name                    | Type       | Description                                                                                 |
|-------------------------|------------|---------------------------------------------------------------------------------------------|
| id                      | Int (PK)   | Default auto-incremented integer identifier                                                 |
| name_canonical          | String (R) | Full name of Person, "canonical" for purposes of name-matching against [Aliases](#alias)    |
| birth_date              | Date       | Date of birth                                                                               |
| gender                  | String     | Stated gender                                                                               |
| race                    | String     | Stated race                                                                                 |
| party_registration      | String     | Registered political affiliation as a voter. Options as in [Tenure](#tenure) `ticket_party` |
| professional_experience | String     | Short description of work history                                                           |
| law_school              | String     | Name of law school attended                                                                 |
| age                     | Int        | Age in years                                                                                |
| current_tenure          | Tenure     | Current [Tenure](#tenure) object associated with this Person, if it exists                  |

# Election

This contains information on Court seats up for Election. Each row in this table represents one seat, so one election cycle in a Court can have multiple rows.
This information might alternatively be modeled as two separate tables, Election and ElectionSeat, where one Election is associated with many ElectionSeats.

| Name            | Type                | Description                                                                      |
|-----------------|---------------------|----------------------------------------------------------------------------------|
| id              | Int (PK)            | Default auto-incremented integer identifier                                      |
| election_id     | String              | String of concatenated court id, election date, and seat number in this Election |
| court           | String (FK Court)   | Key to join judicial race to its Court                                           |
| election_date   | Date (R)            | Election day                                                                     |
| filing_deadline | Date                | Deadline to file for candidacy in this race                                      |
| election_type   | String (enumerated) | Election method, from `partisan election`, `nonpartisan election`, `retention`   |
| incumbent       | String (FK Tenure)  | Name of current holder of this seat up for election                              |

# Candidacy

This contains information on a Person's bids for judicial office. This table is similar to the Tenure table, as
one Person record can have many Candidacies, or even none (e.g. if they were appointed, or if they joined the court before our data collection began).

| Name     | Type                 | Description                                       |
|----------|----------------------|---------------------------------------------------|
| id       | Int (PK)             | Default auto-incremented integer identifier       |
| person   | String (FK Alias)    | Alias of the Person running during this Candidacy |
| election | String (FK Election) | Election id associated with this Candidacy        |

# Alias

This contains all alternate spellings and variations of the names of Persons, as they appear "raw" in Tenure, Candidacy, and IndividualOpinion data.
Judges and Persons may choose to write their names differently (e.g. "Jim" becomes "James"), and their names may be entered into records with typos
(e.g. "Bidegaray" becomes "Biidegaray"). Before records are linked by foreign key, many Aliases must be matched to a `canonical_name` for a Person.

| Name    | Type               | Description                                                                              |
|---------|--------------------|------------------------------------------------------------------------------------------|
| id      | Int (PK)           | Default auto-incremented integer identifier                                              |
| alias   | String             | Person name ingested as-is                                                               |
| tenure  | Tenure (FK Tenure) | Tenure where this Alias was listed as the name, if an associated Tenure exists           |
| court   | Court (FK Court)   | Court of the Case where this Alias was listed as the name, if an associated court exists |
| matched | Boolean            | True if `tenure` exists                                                                  |


# CaseProcessingRun

This contains metadata on each time a batch of Case documents submitted for LLM processing. The `timestamp` alone is enough to identify
a CaseProcessingRun due to resource constraints only allowing for several test runs and one full run in the initial 10-week development
period.

| Name                | Type               | Description                                                                                                  |
|---------------------|--------------------|--------------------------------------------------------------------------------------------------------------|
| id                  | Int (PK)           | Default auto-incremented integer identifier                                                                  |
| timestamp           | Date               | Date of the start of the processing run                                                                      |
| prompt_start        | String             | Prompt template introducing the task and output structure. To be appended with a link to a Case pdf document |
| model_id            | String (R)         | LLM model, defaulting to "gemini-2.5-flash"                                                                  |
| skips               | String (TextField) | List of IDs of documents skipped by processing run due to exceptions or improperly structured output         |
| avg_case_query_time | Float              | Average LLM processing time per document, in seconds                                                         |

# Case

This contains details of court cases. Technical details on Cases are extracted from PDFs using an LLM, marked with (LLM) in the Description.
In the initial 10-week development period of this project, only decided Cases appear in this table. The documents referenced in each Case
record are brief summary opinion documents for the Court's final ruling.

The `case_type` enumerated values are: "Civil Rights", "Economic and Labor Rights", "Voting Rights and Elections", "Criminal Law", "Environment", "Judicial Selection and Administration", "Education", "Speech and Religion", "Civil Due Process", "Reproductive Rights", "Torts and Liability", "Judicial Interpretation", "Election 2024". The `case_type` values are distinct from (but often related to) the 12 LLM-generated topic flags.

| Name                    | Type                 | Description                                                                                                                |
|-------------------------|----------------------|----------------------------------------------------------------------------------------------------------------------------|
| id                      | Int (PK)             | Default auto-incremented integer identifier                                                                                |
| case_id                 | String               | String of case docket number, state, and decision date (YYYY/MM/DD), all concatenated by "_"                               |
| court                   | String (FK Court)    | Court id of Court where this Case was filed                                                                                |
| docket_no               | String (R)           | Identifying string unique to Case within its Court                                                                         |
| case_type               | String (enumerated)  | Case type categories from State Case Database. Distinguishes criminal from civil cases                                     |
| case_title              | String (R)           | Standard case title, often in form "\<Plaintiff\> v. <Defendant\>" but formatted otherwise for various case types          |
| description             | String (R)           | Summary of the dispute before the court (LLM)                                                                              |
| decision_status         | Boolean (R)          | Whether Court has issued an Opinion                                                                                        |
| decision_outcome        | String               | Summary of how the Court ruled with the plaintiff, defendant, or otherwise (LLM)                                           |
| decision_date           | Date                 | Date final opinion was issued                                                                                              |
| environment             | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on environmental rights, or `NA` if Case not applicable (LLM)           |
| consumers               | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on consumer rights, or `NA` if Case not applicable (LLM)                |
| reproductive_rights     | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on reproductive rights, or `NA` if Case not applicable (LLM)            |
| democratic_norms        | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on democratic norms, or `NA` if Case not applicable (LLM)               |
| free_press              | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on free press, or `NA` if Case not applicable (LLM)                     |
| public_health           | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on public health, or `NA` if Case not applicable (LLM)                  |
| separation_church_state | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on separation of church and state, or `NA` if Case not applicable (LLM) |
| voting_access           | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on voting access, or `NA` if Case not applicable (LLM)                  |
| public_education        | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on public education, or `NA` if Case not applicable (LLM)               |
| free_speech             | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on free speech, or `NA` if Case not applicable (LLM)                    |
| privacy                 | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on privacy, or `NA` if Case not applicable (LLM)                        |
| worker_rights           | String (enumerated)  | Whether Court's opinion `protected` or `infringed` on worker rights, or `NA` if Case not applicable (LLM)                  |
| document_url            | String (URL)         | Link to pdf document containing final decision                                                                             |
| case_processing_run     | FK CaseProcessingRun | CaseProcessingRun that generated the LLM data in this Case record                                                          |


# IndividualOpinion

This contains information on how an individual judge ruled in a Case. The term "opinion" is technically reserved for the opinion of the entire Court's majority ruling, so these records are named IndividualOpinions. A single judge's `ruling` here can be combined with the LLM-generated `protected`/`infringed` flags in the Case table to recover a judge's stance in a given Case. Additionally, the `description` field allows for reporting further nuance, such as when a judge concurs, but issues their own argument that differs from their peers' argument.

| Name        | Type                   | Description                                                                                   |
|-------------|------------------------|-----------------------------------------------------------------------------------------------|
| id          | Int (PK)               | Default auto-incremented integer identifier                                                   |
| case        | Int (FK Case)          | Key to join individual ruling with its Case context                                           |
| tenure      | Int (FK Tenure)        | Key to join individual ruling with Judge that made it                                         |
| description | String (R)             | Text of judge's opinion                                                                       |
| ruling      | String (R, enumerated) | How judge ruled in terms of full court's opinion: `concur`, `dissent`, `other` (e.g. recusal) |
