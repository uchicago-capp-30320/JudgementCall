import requests
import lxml.html
from pypdf import PdfReader
import pandas as pd
import time
from google import genai
from pathlib import Path
from google.genai import types, errors
import os
import us
from datetime import datetime

from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict, get_type_hints

case_df = pd.read_csv("../data/cases_scdb.csv")
case_df = case_df[case_df["opinion_link"].str.contains("https", na=False)]
judge_pd = pd.read_csv("../data/judges_slri.csv")


# Manually enumerate rights here, but
# programmatically create dataframe columns with these names later
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


class IndividualOpinion(BaseModel):
    judge_name: str = Field(description="The full name of the judge giving an opinion.")
    ruling: str = Field(
        description='"concur" or "dissent" or "other" based on how this judge ruled,'
    )
    description: str = Field(
        description="An extremely brief description of the judge's own opinion on the case."
    )


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
        try:
            genai_resp = client.models.generate_content(
                model=model_id,
                contents=[types.Part.from_bytes(data=resp, mime_type="application/pdf"), prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": Case.model_json_schema(),
                },
            )
            return Case.model_validate_json(genai_resp.text).model_dump()

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
    num_cases = len(case_df)
    model_id = client_info["model_id"]
    client = client_info["client"]

    file_dic = {}
    for i in range(num_cases):
        print(f"Querying case {i}")
        docket_no = case_df.iloc[i]["docket_no"].replace(" ", "-")
        state = case_df.iloc[i]["state"]
        date = str(datetime.strptime(case_df.iloc[i]["date"], "%B %d, %Y"))[:10].replace("-", "/")
        pdf_link = case_df.iloc[i]["opinion_link"]

        case_ref = "_".join([docket_no, state, date])

        opinion_resp = read_opinion(pdf_link, model_id, client, prompt_start)

        file_dic[case_ref] = {}
        file_dic[case_ref]["pdf_link"] = pdf_link
        file_dic[case_ref]["response"] = opinion_resp

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
        "description": [],
        "plaintiff_argument": [],
        "defendant_argument": [],
        "decision_outcome": [],
        "decision_winner": [],
        # "decision_status": [],
    }
    rights_enumerated_list = list(get_type_hints(RightsDict).keys())
    rights_enumerated_dict = {right: [] for right in rights_enumerated_list}
    case_table = case_table | rights_enumerated_dict

    num_cases = len(case_df)

    for i in range(num_cases):
        docket_no = case_df.iloc[i]["docket_no"].replace(" ", "-")
        case_table["docket_no"].append(docket_no)
        state = case_df.iloc[i]["state"]
        case_table["state"].append(state)
        date = str(datetime.strptime(case_df.iloc[i]["date"], "%B %d, %Y"))[:10].replace("-", "/")
        case_table["date"].append(date)

        title = case_df.iloc[i]["title"]
        case_table["title"].append(title)
        type = case_df.iloc[i]["type"]
        case_table["type"].append(type)

        case_id = "_".join([docket_no, state, date])
        case_table["case_id"].append(case_id)

        response = case_dic[case_id]["response"]
        case_table["description"].append(response["issue_debate"])
        case_table["plaintiff_argument"].append(response["plaintiff_argument"])
        case_table["defendant_argument"].append(response["defendant_argument"])
        case_table["decision_outcome"].append(response["decision_outcome"])
        case_table["decision_winner"].append(response["decision_winner"])

        rights_affected = response["rights_affected"]
        for right in rights_enumerated_list:
            case_table[right].append(rights_affected[right])

        # status = ~case_df.iloc[i]["pending"]  # Negate, "not pending" means "decided"
        # case_table["decision_status"].append(status)

    return pd.DataFrame(case_table)


def produce_tables(
    case_df: pd.DataFrame,
    prompt_path: str = "../ingestion/prompt.txt",
    model_id: str = "gemini-2.5-flash",
):
    """
    Inputs:
    - case_df: pd.DataFrame
    - judge_df: pd.DataFrame
    - prompt_path: str

    Outputs:
    - rd: dict
    - llm_run_metadata: dict

    This function takes dataframes of cases and judges, and iterates state
    by state to iteratively create the opinion and case tables. Returns
    each in a dictionary.
    """
    states = case_df["state"].sort_values().unique()

    opinions = []
    cases = []

    for state in states:
        state_cases = case_df[case_df["state"] == state]

        case_dic = apply_model(state_cases, prompt_path, model_id)

        opinions.append(state_opinion_table(case_dic))
        cases.append(state_case_table(state_cases, case_dic))

    rd = {"opinion_table": pd.concat(opinions), "case_table": pd.concat(cases)}

    # Also return JSON metadata on this LLM batch run
    with open(prompt_path, "r") as prompt_file:
        prompt = prompt_file.read()
    llm_run_metadata = {
        "timestamp": datetime.today(),
        "model_id": model_id,
        "cases_processed": rd["case_table"]["case_id"].tolist(),
        "prompt_start": prompt,
    }

    return rd, llm_run_metadata
