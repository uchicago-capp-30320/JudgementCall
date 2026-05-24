import requests
import lxml.html
import pandas as pd
import time
from google import genai
from google.genai import types, errors
import os
import us
import json
import hashlib

from ingestion.ingest_sc_cases import scrape_scdb
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, TypedDict, get_type_hints

QUERY_TIMES = []
SKIPS = {"case_id": [], "num_skips": 0}


# Creating the data structure for Gemini output after analyzing a case
# Create a dictionary enumerating the rights potentially affected by a case
class RightsDict(BaseModel):
    environment: str = Field(
        description="The effect of the court's decision on environmental rights"
    )
    consumers: str = Field(description="The effect of the court's decision on consumer rights")
    reproductive_rights: str = Field(
        description="The effect of the court's decision on reproductive rights"
    )
    democratic_norms: str = Field(
        description="The effect of the court's decision on democratic norms"
    )
    free_press: str = Field(
        description="The effect of the court's decision on the right to free press"
    )
    public_health: str = Field(description="The effect of the court's decision on public health")
    separation_church_state: str = Field(
        description="The effect of the court's decision on separation of church and state"
    )
    voting_access: str = Field(description="The effect of the court's decision on voting rights")
    public_education: str = Field(
        description="The effect of the court's decision on the right to public education"
    )
    free_speech: str = Field(
        description="The effect of the court's decision on the right to free speech"
    )
    privacy: str = Field(description="The effect of the court's decision on privacy rights")
    worker_rights: str = Field(description="The effect of the court's decision on worker rights")


# Create a dictionary for an individual opinion
class IndividualOpinion(BaseModel):
    judge_name: str = Field(description="The full name of the judge giving an opinion.")
    ruling: str = Field(
        description='"concur" or "dissent" or "other" based on how this judge ruled,'
    )
    description: str = Field(
        description="An extremely brief description of the judge's own opinion on the case."
    )


# Create a dictionary for a case containing the rights dictionary and individual opinion dictionary
class Case(BaseModel):
    issue_debate: str = Field(
        description='A phrase starting with "Whether" that summarizes '
        "the main issue being debated in the case"
    )
    plaintiff_argument: str = Field(
        description="Briefly, the plaintiff's stance on the debate issue"
    )
    defendant_argument: str = Field(
        description="Briefly, the defendant's stance on the debate issue"
    )
    decision_outcome: str = Field(
        description="The court's final decision for the case whether "
        "they ruled with the plaintiff or not."
    )
    decision_winner: str = Field(
        description='The party that the court sided with ("plaintiff","defendant","other").'
    )
    rights_affected: RightsDict
    judge_opinions: List[IndividualOpinion]


def read_opinion(pdf_link: str, model_id: str, client: genai.Client, prompt: str):
    """
    Inputs:
    - pdf_link: string
    - model_id: string
    - client: genai.Client
    - prompt: str

    Outputs:
    - dict

    Function makes a request to the content from a pdf url and prompts it into
    Gemini through the inputted gemini client. Returns a dictionary following
    the structure of the Case class defined outside of the function.

    If the LLM call runs into a server error due to high demand, the function
    waits between 5 seconds and 1 minute before trying again.
    """
    resp = requests.get(pdf_link).content
    wait_time = 5

    while True:
        start = datetime.now()
        try:
            genai_resp = client.models.generate_content(
                model=model_id,
                contents=[types.Part.from_bytes(data=resp, mime_type="application/pdf"), prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": Case.model_json_schema(),
                    "temperature": 0,
                },
            )
            structured_output = Case.model_validate_json(genai_resp.text).model_dump()
            end = datetime.now()
            time_diff = (end - start).total_seconds()
            QUERY_TIMES.append(time_diff)
            return structured_output
        # Server errors with Gemini occur when a model is experiencing high
        # demand. Pausing and waiting before querying again.
        except errors.ServerError as e:
            print("Ran into server error due to high demand")
            print(f"Waiting for {wait_time} seconds before calling again")
            time.sleep(wait_time)
            wait_time += 1

            if wait_time > 60:
                print("Wait time exceeds 1 minute")
                raise e


def analyze_state_cases(case_df: pd.DataFrame, prompt_start: str, client_info: dict):
    """
    Inputs:
    - case_df: pd.Dataframe,
    - prompt_start: str,
    - client_info: dict

    Outputs:
    - file_dic: dict

    Function creates the full prompt by taking the prompt start (extracted)
    from .txt file and joins it with the string version of the judge
    dataframe. It then extract the information about the client, the model id
    and gemini client.
    """
    model_id = client_info["model_id"]
    client = client_info["client"]

    file_dic = {}
    for index, row in case_df.iterrows():
        print(f"Querying case no. {index + 1}: {row['title']}")

        pdf_link = row["opinion_link"]
        case_id = row["case_id"]

        try:
            opinion_resp = read_opinion(pdf_link, model_id, client, prompt_start)
        except (ValidationError, errors.ClientError):
            message = f"{row['title']} - Skipped because LLM output"
            message += "did not follow enforced data structure"
            print(message)
            SKIPS["num_skips"] += 1
            SKIPS["case_id"].append(case_id)
            continue

        file_dic[case_id] = {}
        file_dic[case_id]["pdf_link"] = pdf_link
        file_dic[case_id]["response"] = opinion_resp

    return file_dic


def apply_model(
    case_df: pd.DataFrame,
    prompt_path: str,
    model_id: str = "gemini-2.5-flash",
):
    """
    Inputs:
    - case_df: pd.Dataframe,
    - prompt_path: str,
    - model_id: str

    Outputs:
    - case_dic: dict

    This function extracts the fixed part of the prompt by reading the .txt
    file, and it initializes the Gemini model by using the API key. It then
    calls analyze_cases() returns its output.
    """
    with open(prompt_path, "r") as prompt_file:
        prompt_start = prompt_file.read()

    load_dotenv(find_dotenv())

    gemini_key = os.getenv("GEMINI_API_KEY")
    client_info = {"model_id": model_id, "client": genai.Client(api_key=gemini_key)}

    case_dic = analyze_state_cases(case_df, prompt_start, client_info)

    return case_dic


def state_opinion_table(case_dic: dict):
    """
    Inputs:
    - case_dic: dict (the output of apply_model())

    Outputs:
    - pd.DataFrame

    This function converst the output from apply_model() into an opinion
    table with three columns:
    - case_id
    - name
    - opinion
    """
    opinion_table = {"case_id": [], "name": [], "description": [], "ruling": []}

    for key in case_dic.keys():
        opinions = case_dic[key]["response"]
        num_opinions = len(opinions["judge_opinions"])

        for i in range(num_opinions):
            opinion_table["case_id"].append(key)

            judge_name = opinions["judge_opinions"][i]["judge_name"]
            opinion_table["name"].append(judge_name)

            description = opinions["judge_opinions"][i]["description"]
            opinion_table["description"].append(description)

            ruling = opinions["judge_opinions"][i]["ruling"]
            opinion_table["ruling"].append(ruling)

    return pd.DataFrame(opinion_table)


def state_case_table(case_df: pd.DataFrame, case_dic: dict):
    """
    Inputs:
    - case_df: pd.DataFrame
    - case_dic: dict

    Outputs:
    - pd.DataFrame

    This function takes a dataframe of cases, and compines it with the output
    of apply_model() to create a complete case table that includes case
    decisions and political dimensions.
    """
    case_table = {
        "case_id": [],
        "docket_no": [],
        "title": [],
        "state": [],
        "date": [],
        "type": [],
        "opinion_link": [],
        "description": [],
        "plaintiff_argument": [],
        "defendant_argument": [],
        "decision_outcome": [],
        "decision_winner": [],
    }
    rights_enumerated_list = list(get_type_hints(RightsDict).keys())
    rights_enumerated_dict = {right: [] for right in rights_enumerated_list}
    case_table = case_table | rights_enumerated_dict

    for index, row in case_df.iterrows():
        date = str(datetime.strptime(row["date"], "%B %d, %Y"))[:10]

        if row["case_id"] not in case_dic:
            continue

        case_table["docket_no"].append(row["docket_no"])
        case_table["state"].append(row["state"])
        case_table["date"].append(date)
        case_table["title"].append(row["title"])
        case_table["type"].append(row["type"])
        case_table["opinion_link"].append(row["opinion_link"])
        case_table["case_id"].append(row["case_id"])

        response = case_dic[row["case_id"]]["response"]
        case_table["description"].append(response["issue_debate"])
        case_table["plaintiff_argument"].append(response["plaintiff_argument"])
        case_table["defendant_argument"].append(response["defendant_argument"])
        case_table["decision_outcome"].append(response["decision_outcome"])
        case_table["decision_winner"].append(response["decision_winner"])

        rights_affected = response["rights_affected"]
        for right in rights_enumerated_list:
            case_table[right].append(rights_affected[right])

    return pd.DataFrame(case_table)


def produce_tables(
    case_df: pd.DataFrame,
    prompt_path: Path = Path(__file__).parent / "prompt.txt",
    model_id: str = "gemini-2.5-flash",
    use_existing: bool = True,
    write_on: bool = True,
):
    """
    Inputs:
    - case_df: pd.DataFrame
    - prompt_path: str
    - model_id: str
    - use_existing: bool
    - write_on: bool

    Outputs:
    - rd: dict

    This function takes dataframes of cases and judges, and iterates state
    by state to iteratively create the opinion and case tables. Returns
    each in a dictionary.
    """
    states = case_df["state"].sort_values().unique()
    cases_list = []
    opinion_list = []
    cases_path = Path(__file__).parent.parent / "data" / "cases"
    cases_path.mkdir(parents=True, exist_ok=True)
    case_files = [file.name.replace(".csv", "") for file in cases_path.iterdir()]
    opinions_path = Path(__file__).parent.parent / "data" / "opinions"
    opinions_path.mkdir(parents=True, exist_ok=True)
    opinion_files = [file.name.replace(".csv", "") for file in opinions_path.iterdir()]

    for state in states:
        print(f"Analyzing cases and opinions for {state}")
        if (state in case_files) and (state in opinion_files) and use_existing:
            case_table = cases_path / (state + ".csv")
            cases = pd.read_csv(case_table)
            opinion_table = opinions_path / (state + ".csv")
            opinions = pd.read_csv(opinion_table)
        else:
            court_cases = case_df[case_df["state"] == state]
            case_dic = apply_model(court_cases, prompt_path, model_id)
            cases = state_case_table(court_cases, case_dic)
            opinions = state_opinion_table(case_dic)

            if write_on:
                file_path = Path(__file__).parent.parent / "data" / "cases" / (state + ".csv")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                cases.to_csv(file_path, index=False)

                file_path = Path(__file__).parent.parent / "data" / "opinions" / (state + ".csv")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                opinions.to_csv(file_path, index=False)

        cases_list.append(cases)
        opinion_list.append(opinions)

        print(f"Analyzed {len(cases)} cases for {state}")

    # Creating total tables
    total_cases = pd.concat(cases_list)
    total_opinions = pd.concat(opinion_list)
    if write_on:
        file_path = Path(__file__).parent.parent / "data" / "cases" / "total_cases.csv"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        total_cases.to_csv(file_path, index=False)

        file_path = Path(__file__).parent.parent / "data" / "opinions" / "total_opinions.csv"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        total_opinions.to_csv(file_path, index=False)

    # Also write JSON metadata on this LLM batch run
    with open(prompt_path, "r") as prompt_file:
        prompt = prompt_file.read()

    try:
        avg_query_time = sum(QUERY_TIMES) / len(QUERY_TIMES)
    except ZeroDivisionError:
        avg_query_time = 0

    llm_run_metadata = {
        "timestamp": datetime.today().strftime("%m-%d-%Y"),
        "model_id": model_id,
        "cases_processed": total_cases["case_id"].tolist(),
        "prompt_start": prompt,
        "skips": SKIPS,
        "avg_case_query_time": avg_query_time,
    }
    meta_path = (
        Path(__file__).parent.parent
        / "data"
        / "run_metadata"
        / f"llm_run_{llm_run_metadata['timestamp']}.json"
    )
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w") as md:
        json.dump(llm_run_metadata, md)

    rd = {"case_table": total_cases, "individual_opinion_table": total_opinions}
    return rd, llm_run_metadata


if __name__ == "__main__":
    case_df = scrape_scdb()

    prompt_path = Path(__file__).parent.parent / "ingestion" / "prompt.txt"

    start = datetime.now()
    print("Getting cases and opinions for main analysis...")
    produce_tables(case_df, use_existing=False)
    end = datetime.now()
    time_diff = (end - start).total_seconds() / 60
    print(f"Ingestion complete after {round(time_diff, 2)} minutes.")
