"""
SPACEJAM ("Spatial Judge Analaysis in Metric Space" (or, "by Maggie"))
This module contains functions to generate data for Multi-Dimensional Scaling (MDS) analysis of
judge voting records which appear on the Analysis page of the site.
"""

import pandas as pd
from sklearn.manifold import MDS
from apps.judgement_call.models import Court, IndividualOpinion
from functools import cache

MDS_CONFIG = {"n_components": 2, "metric_mds": True, "n_init": 1, "init": "random"}


@cache
def query_similarity_df(court_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Queries database to create judge voting history similarity dataframe and context dataframe.
    Input: court_id (matching court_id in Court)
    Output: tuple of (similarity df, context df)
    - Dataframe where each row is one judge's ruling on one case for the given court
    - Context dataframe including judge details
    """
    court = Court.objects.get(court_id=court_id)
    qset = IndividualOpinion.objects.filter(
        case__court=court, case__decision_status=True, judge_alias__tenure__isnull=False
    )
    if not qset:
        return (None, None)
    similarity_df = pd.DataFrame(
        list(
            IndividualOpinion.objects.filter(
                case__court=court, case__decision_status=True, judge_alias__tenure__isnull=False
            ).values(
                "case",
                "judge_alias",
                "judge_alias__tenure",
                "judge_alias__tenure__person__name_canonical",
                "judge_alias__tenure__ticket_party",
                "judge_alias__tenure__appointer_party",
                "judge_alias__tenure__court__selection_type",
                "ruling",
                "case__case_type",
            )
        )
    )
    colname_map = {
        "case": "case",
        "judge_alias__tenure": "judge",
        "judge_alias__tenure__person__name_canonical": "judge_name",
        "ruling": "ruling_verbose",
        "case__case_type": "case_type",
        "judge_alias__tenure__ticket_party": "ticket_party",
        "judge_alias__tenure__appointer_party": "appointer_party",
        "judge_alias__tenure__court__selection_type": "selection_type",
    }
    similarity_df = similarity_df[colname_map.keys()].rename(colname_map, axis=1)

    similarity_df["ruling"] = similarity_df["ruling_verbose"].apply(
        lambda x: 1 if x == "concur" else -1 if x == "dissent" else 0
    )

    context_df = (
        similarity_df.groupby(
            ["judge", "judge_name", "ticket_party", "appointer_party", "selection_type"]
        )
        .agg({"case": "count"})
        .reset_index()
    )

    return similarity_df, context_df


def pivot_similarity_df(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Performs a pivot on the judge ruling dataframe to create a feature matrix.
    Input: dataframe where each row is one judge's ruling on one case for the given court
    Output: feature matrix dataframe
    """
    try:  # Debugging - TODO: more robust checks on data validity
        df = df.pivot(index="case", columns="judge_name", values="ruling")
    except (ValueError, AttributeError) as e:
        print(f"Error: {e}\nCouldn't pivot similarity dataframe.")
        return None
    nona_df = df.fillna(1)
    feat_mat = nona_df.transpose()
    return feat_mat


def mds_embedding(feat_mat: pd.DataFrame) -> pd.DataFrame:
    """
    Apply sklearn MDS embedding method to the feature matrix.
    Input: feature matrix
    Output: dataframe of judge names and projected x-y coordinates
    """
    embedding = MDS(**MDS_CONFIG)
    x_transformed = embedding.fit_transform(feat_mat)
    x, y = x_transformed.transpose()
    coords = pd.DataFrame({"judge_name": feat_mat.index, "x": x, "y": y})

    return coords


def make_df_to_plot(coords: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    """
    Merge coords with context for plotting.
    """
    judges_mds = coords.merge(context, on="judge_name")
    return judges_mds


@cache
def make_plot(court_id: str) -> pd.DataFrame | None:
    """
    Applies the processing pipeline to voting history for a specific court.
    """
    df, context = query_similarity_df(court_id)
    feat_mat = pivot_similarity_df(df)
    if feat_mat is not None:
        coords = mds_embedding(feat_mat)
        plot_df = make_df_to_plot(coords, context)
        return plot_df
    else:
        return None
