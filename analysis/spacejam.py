import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import altair as alt
from sklearn.manifold import MDS
from sklearn.cluster import KMeans
from ingestion.ingest_courts import COURT_LOOKUP_LONG
from apps.judgement_call.models import Court, IndividualOpinion
from functools import cache

MDS_CONFIG = {"n_components": 2, "metric_mds": True, "n_init": 1, "init": "random"}


@cache
def query_similarity_df(court_id):
    court = Court.objects.get(court_id=court_id)
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
    print(similarity_df.groupby(["case", "judge_name", "ruling"]).count())

    return similarity_df, context_df


def pivot_similarity_df(df):
    try:
        df = df.pivot(index="case", columns="judge_name", values="ruling")
    except ValueError as e:
        print(f"Error: {e}")
        return None
    nona_df = df.fillna(1)
    feat_mat = nona_df.transpose()
    return feat_mat


def mds_embedding(feat_mat):
    embedding = MDS(**MDS_CONFIG)
    x_transformed = embedding.fit_transform(feat_mat)
    x, y = x_transformed.transpose()
    coords = pd.DataFrame({"judge_name": feat_mat.index, "x": x, "y": y})

    return coords


def make_df_to_plot(coords, context):
    judges_mds = coords.merge(context, on="judge_name")
    return judges_mds


@cache
def make_plot(court_id):
    # court_id = COURT_LOOKUP_LONG[state]

    df, context = query_similarity_df(court_id)
    feat_mat = pivot_similarity_df(df)
    if feat_mat is not None:
        coords = mds_embedding(feat_mat)
        plot_df = make_df_to_plot(coords, context)
        print(plot_df)
        return plot_df
    else:
        return None

    # alt.Chart(plot_df, title=f"{court_id} Judge Similarity").mark_circle(size=60).encode(
    #     x=alt.X("x", axis=None),
    #     y=alt.Y("y", axis=None),
    #     color="appointer_party",
    #     tooltip=["judge_name"],
    # ).interactive()
